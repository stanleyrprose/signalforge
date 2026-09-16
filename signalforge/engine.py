from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .acquisition_contract import ProcessingFailure, request_reason
from .acquisition_runtime import acquire_local_bytes, acquire_provider_bytes, record_processing
from .config import Registry, db_path, evidence_root
from .db import connect, migrate
from .http import fetch_bytes, fetch_bytes_cloudrity_d1n
from .mpt import SitemapEntry
from .source_adapters import adapter_for
from .worker_context import load_worker_context


Fetcher = Callable[..., bytes]


class EngineError(RuntimeError):
    pass


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


_OUTAGE_BACKOFF_FAILURES = {
    "CONNECT_TIMEOUT",
    "DNS_FAILURE",
    "HTTP_429",
    "HTTP_5XX",
}


def _latest_acquisition_failure(conn, scheduler_run_id: str) -> str | None:  # type: ignore[no-untyped-def]
    row = conn.execute(
        """
        SELECT a.acquisition_failure_class
        FROM acquisition_attempts a
        JOIN acquisition_requests r ON r.request_id=a.request_id
        WHERE r.scheduler_run_id=?
          AND a.status='FAILED'
          AND a.acquisition_failure_class IS NOT NULL
        ORDER BY a.started_at DESC, a.attempt_number DESC
        LIMIT 1
        """,
        (scheduler_run_id,),
    ).fetchone()
    return str(row[0]) if row is not None else None


def _failure_retry_delay_seconds(
    source: dict[str, object],
    *,
    failure_class: str | None,
    consecutive_failures_after: int,
) -> int:
    base = int(source["retry_interval_seconds"])
    if failure_class not in _OUTAGE_BACKOFF_FAILURES:
        return base

    raw_cap = source.get("recovery_slo_seconds")
    if isinstance(raw_cap, int) and raw_cap > 0:
        cap = max(base, raw_cap)
    else:
        cap = max(base, int(source.get("poll_interval_seconds", base)))

    tier = max(0, (consecutive_failures_after - 1) // 3)
    multiplier = 1 << min(tier, 8)
    return min(base * multiplier, cap)


def _material_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


_ATTACHMENT_ENRICHMENT_FIELDS = {
    "deadline",
    "deadline_time",
    "deadline_kind",
    "deadline_evidence",
    "tender_opening_date",
    "tender_opening_time",
    "tender_opening_evidence",
    "attachment_policy",
    "detail_completeness",
}


def _initial_attachment_enrichment_only(conn, *, source: dict, tender) -> bool:  # type: ignore[no-untyped-def]
    attachment_policy = source.get("attachment_policy") or {}
    if attachment_policy.get("suppress_signal_on_initial_attachment_enrichment") is not True:
        return False
    existing = conn.execute(
        "SELECT payload_json FROM canonical_items WHERE canonical_key=?",
        (tender.canonical_key,),
    ).fetchone()
    if existing is None:
        return False
    try:
        previous = json.loads(str(existing["payload_json"]))
    except json.JSONDecodeError:
        return False
    if not isinstance(previous, dict):
        return False
    if previous.get("attachment_policy") != "METADATA_ONLY_NON_BLOCKING":
        return False
    if previous.get("detail_completeness") != "HTML_EVENT_SCOPE_PDF_DEADLINE_UNPARSED":
        return False
    current = tender.payload()
    previous_business = {key: value for key, value in previous.items() if key not in _ATTACHMENT_ENRICHMENT_FIELDS}
    current_business = {key: value for key, value in current.items() if key not in _ATTACHMENT_ENRICHMENT_FIELDS}
    return previous_business == current_business


_LISTING_SEMANTIC_ENRICHMENT_FIELDS = {
    "deadline",
    "deadline_time",
    "deadline_kind",
    "deadline_evidence",
    "semantic_version",
}


def _listing_semantic_transition_only(conn, *, source: dict, tender) -> bool:  # type: ignore[no-untyped-def]
    migration = source.get("listing_semantic_migration") or {}
    if not isinstance(migration, dict) or migration.get("suppress_signal") is not True:
        return False
    from_version = migration.get("from_version")
    to_version = migration.get("to_version")
    if not isinstance(from_version, int) or not isinstance(to_version, int) or from_version >= to_version:
        return False
    existing = conn.execute(
        "SELECT payload_json FROM canonical_items WHERE canonical_key=?",
        (tender.canonical_key,),
    ).fetchone()
    if existing is None:
        return False
    try:
        previous = json.loads(str(existing["payload_json"]))
    except json.JSONDecodeError:
        return False
    if not isinstance(previous, dict) or previous.get("semantic_version") != from_version:
        return False
    current = tender.payload()
    if current.get("semantic_version") != to_version:
        return False
    previous_business = {key: value for key, value in previous.items() if key not in _LISTING_SEMANTIC_ENRICHMENT_FIELDS}
    current_business = {key: value for key, value in current.items() if key not in _LISTING_SEMANTIC_ENRICHMENT_FIELDS}
    return previous_business == current_business


def _source_state(conn, source_id: str):  # type: ignore[no-untyped-def]
    return conn.execute("SELECT * FROM source_state WHERE source_id=?", (source_id,)).fetchone()


def _baseline_candidates(entries: list[SitemapEntry], *, now: datetime, source: dict) -> list[SitemapEntry]:
    cutoff = now - timedelta(days=int(source["baseline_lookback_days"]))
    limit = int(source["baseline_detail_limit"])
    by_url = {entry.url: entry for entry in entries}
    seeds = [by_url[url] for url in source.get("bootstrap_seed_urls", []) if url in by_url]
    seed_urls = {entry.url for entry in seeds}
    recent = [
        entry
        for entry in entries
        if entry.url not in seed_urls
        and (_parse_iso(entry.lastmod) or datetime.min.replace(tzinfo=UTC)) >= cutoff
    ]
    recent.sort(key=lambda entry: entry.lastmod or "", reverse=True)
    return (seeds + recent)[:limit]


def _upsert_discovery_snapshot(
    conn,  # type: ignore[no-untyped-def]
    source_id: str,
    entries: list[SitemapEntry],
    observed_at: str,
    *,
    baseline: bool,
) -> None:
    for entry in entries:
        existing = conn.execute(
            "SELECT fetched_lastmod,pending_since_at,suppress_signal_once FROM discovery_items WHERE source_id=? AND url=?",
            (source_id, entry.url),
        ).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO discovery_items(
                    source_id,url,lastmod,fetched_lastmod,pending_since_at,suppress_signal_once,
                    first_seen_at,last_seen_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    source_id,
                    entry.url,
                    entry.lastmod,
                    None,
                    observed_at,
                    int(baseline),
                    observed_at,
                    observed_at,
                ),
            )
            continue

        fetched_lastmod = existing["fetched_lastmod"]
        pending_since = existing["pending_since_at"]
        suppress_once = int(existing["suppress_signal_once"] or 0)
        if fetched_lastmod != entry.lastmod:
            pending_since = pending_since or observed_at
        else:
            pending_since = None
        conn.execute(
            """
            UPDATE discovery_items
            SET lastmod=?,last_seen_at=?,pending_since_at=?,suppress_signal_once=?
            WHERE source_id=? AND url=?
            """,
            (entry.lastmod, observed_at, pending_since, suppress_once, source_id, entry.url),
        )


def _schedule_detail_parser_replay(
    conn,  # type: ignore[no-untyped-def]
    *,
    source_id: str,
    source: dict,
    adapter,  # type: ignore[no-untyped-def]
    entries: list[SitemapEntry],
    observed_at: str,
) -> int:
    """Re-open bounded historical zero-item parses after an explicit parser migration.

    This is intentionally opt-in and fail-closed. It only replays URLs that are still
    present in the current issuer discovery surface, have never produced a canonical
    item, were successfully processed as zero items by the configured old parser, and
    have not already been successfully processed by the configured new parser.
    """
    migration = source.get("detail_parser_replay_migration") or {}
    if not isinstance(migration, dict):
        return 0
    if migration.get("zero_items_only") is not True or migration.get("suppress_signal_once") is not True:
        return 0
    from_version = migration.get("from_version")
    to_version = migration.get("to_version")
    if not isinstance(from_version, str) or not from_version:
        return 0
    if not isinstance(to_version, str) or not to_version or to_version == from_version:
        return 0
    if str(adapter.detail_parser_version) != to_version:
        return 0

    scheduled = 0
    for entry in entries:
        discovery = conn.execute(
            """
            SELECT canonical_key,lastmod,fetched_lastmod,pending_since_at
            FROM discovery_items
            WHERE source_id=? AND url=?
            """,
            (source_id, entry.url),
        ).fetchone()
        if discovery is None or discovery["canonical_key"] is not None:
            continue
        # Only reopen rows that the old parser actually acknowledged at this same issuer revision.
        if discovery["fetched_lastmod"] != discovery["lastmod"]:
            continue
        old_zero = conn.execute(
            """
            SELECT 1
            FROM processing_records AS p
            JOIN evidence_envelopes AS e ON e.evidence_id=p.evidence_id
            WHERE p.source_id=? AND p.parser_version=? AND p.status='SUCCESS' AND p.items_found=0
              AND (e.requested_url=? OR e.final_url=?)
            LIMIT 1
            """,
            (source_id, from_version, entry.url, entry.url),
        ).fetchone()
        if old_zero is None:
            continue
        already_replayed = conn.execute(
            """
            SELECT 1
            FROM processing_records AS p
            JOIN evidence_envelopes AS e ON e.evidence_id=p.evidence_id
            WHERE p.source_id=? AND p.parser_version=? AND p.status='SUCCESS'
              AND (e.requested_url=? OR e.final_url=?)
            LIMIT 1
            """,
            (source_id, to_version, entry.url, entry.url),
        ).fetchone()
        if already_replayed is not None:
            continue
        conn.execute(
            """
            UPDATE discovery_items
            SET pending_since_at=COALESCE(pending_since_at,?), suppress_signal_once=1
            WHERE source_id=? AND url=? AND canonical_key IS NULL
            """,
            (observed_at, source_id, entry.url),
        )
        scheduled += 1
    return scheduled


def _acknowledge_baseline_exclusions(
    conn,  # type: ignore[no-untyped-def]
    source_id: str,
    entries: list[SitemapEntry],
    candidates: list[SitemapEntry],
) -> None:
    selected = {entry.url for entry in candidates}
    for entry in entries:
        if entry.url in selected:
            continue
        conn.execute(
            """
            UPDATE discovery_items
            SET fetched_lastmod=lastmod,pending_since_at=NULL,suppress_signal_once=0
            WHERE source_id=? AND url=?
            """,
            (source_id, entry.url),
        )


def _pending_candidates(conn, source_id: str, limit: int) -> list[SitemapEntry]:  # type: ignore[no-untyped-def]
    return [
        SitemapEntry(str(row["url"]), row["lastmod"])
        for row in conn.execute(
            """
            SELECT url,lastmod
            FROM discovery_items
            WHERE source_id=? AND pending_since_at IS NOT NULL
            ORDER BY COALESCE(lastmod,'') DESC,pending_since_at ASC,url ASC
            LIMIT ?
            """,
            (source_id, limit),
        )
    ]


def _pending_summary(conn, source_id: str) -> tuple[int, str | None]:  # type: ignore[no-untyped-def]
    row = conn.execute(
        "SELECT COUNT(*) AS count,MIN(pending_since_at) AS oldest FROM discovery_items WHERE source_id=? AND pending_since_at IS NOT NULL",
        (source_id,),
    ).fetchone()
    return int(row["count"]), row["oldest"]


def _recovery_context(state, now: datetime, source: dict, *, baseline: bool) -> tuple[bool, str | None, str | None]:  # type: ignore[no-untyped-def]
    if baseline or state is None:
        return False, None, None
    if state["recovery_window_start"] and state["recovery_window_end"]:
        return True, str(state["recovery_window_start"]), str(state["recovery_window_end"])

    interval = timedelta(seconds=int(source["poll_interval_seconds"]))
    next_due = _parse_iso(state["next_due_at"])
    if next_due is None or now < next_due + interval:
        return False, None, None
    last_reconciliation = _parse_iso(state["last_successful_reconciliation_at"]) or _parse_iso(state["last_success_at"])
    window_start = _iso(last_reconciliation) if last_reconciliation is not None else str(state["next_due_at"] or _iso(now - interval))
    return True, window_start, _iso(now)


def _write_evidence(
    source_id: str,
    payload: bytes,
    digest: str,
    root: Path | None = None,
    *,
    suffix: str = ".html",
) -> Path:
    if suffix not in {".html", ".pdf"}:
        raise ValueError(f"unsupported evidence suffix: {suffix}")
    target_root = root or evidence_root()
    directory = target_root / source_id
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{digest}{suffix}"
    if not target.exists():
        tmp = target.with_suffix(f"{suffix}.part")
        tmp.write_bytes(payload)
        tmp.replace(target)
        target.chmod(0o640)
    return target


def _actionable_deadline_utc(payload: dict[str, object]) -> datetime | None:
    raw_deadline = payload.get("deadline")
    if not isinstance(raw_deadline, str) or not raw_deadline:
        return None
    try:
        if "T" in raw_deadline:
            parsed = datetime.fromisoformat(raw_deadline.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return None
            return parsed.astimezone(UTC)
        deadline_time = payload.get("deadline_time")
        if deadline_time in (None, ""):
            # Date-only issuer deadlines are eligible only against the start of
            # that Myanmar calendar date. This is a conservative lower bound
            # used for reconciliation eligibility/sorting; it is never written
            # back as an invented deadline time.
            parsed = datetime.fromisoformat(f"{raw_deadline}T00:00:00+06:30")
            return parsed.astimezone(UTC)
        if not isinstance(deadline_time, str) or len(deadline_time) != 5 or deadline_time[2] != ":":
            return None
        parsed = datetime.fromisoformat(f"{raw_deadline}T{deadline_time}:00+06:30")
        return parsed.astimezone(UTC)
    except ValueError:
        return None


def _reconcile_actionable_baseline_signals(
    conn,  # type: ignore[no-untyped-def]
    *,
    source_id: str,
    source: dict,
    now: datetime,
    observed_at: str,
) -> int:
    policy = source.get("actionable_baseline_signal_policy") or {}
    if policy.get("enabled") is not True:
        return 0
    min_remaining = int(policy["min_remaining_seconds"])
    max_signals = int(policy["max_signals_per_run"])
    eligible: list[tuple[datetime, str, dict[str, object]]] = []
    for row in conn.execute(
        "SELECT canonical_key,payload_json FROM canonical_items WHERE source_id=? AND item_kind='TENDER'",
        (source_id,),
    ):
        if conn.execute(
            "SELECT 1 FROM signals WHERE source_id=? AND canonical_key=? LIMIT 1",
            (source_id, row["canonical_key"]),
        ).fetchone() is not None:
            continue
        try:
            payload = json.loads(str(row["payload_json"]))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        business_stage = payload.get("business_stage")
        if business_stage not in (None, "", "OPPORTUNITY"):
            continue
        deadline = _actionable_deadline_utc(payload)
        if deadline is None or (deadline - now).total_seconds() < min_remaining:
            continue
        eligible.append((deadline, str(row["canonical_key"]), payload))

    promoted = 0
    for _deadline, canonical_key, payload in sorted(eligible, key=lambda item: (item[0], item[1]))[:max_signals]:
        signal_payload = _json(
            {
                "signal_type": "NEW",
                "signal_reason": "ACTIONABLE_BASELINE_RECONCILIATION",
                "canonical_key": canonical_key,
                **payload,
            }
        )
        cursor = conn.execute(
            """
            INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json)
            SELECT ?,?,?,?,?,?
            WHERE NOT EXISTS(
                SELECT 1 FROM signals WHERE source_id=? AND canonical_key=?
            )
            """,
            (
                str(uuid.uuid4()), source_id, canonical_key, "NEW", observed_at, signal_payload,
                source_id, canonical_key,
            ),
        )
        promoted += max(0, int(cursor.rowcount or 0))
    return promoted


def _upsert_tender(
    conn,  # type: ignore[no-untyped-def]
    *,
    source_id: str,
    tender,
    observed_at: str,
    suppress_signal: bool,
    evidence_digest: str,
) -> tuple[bool, int]:
    payload = tender.payload()
    payload_json = _json(payload)
    content_hash = _material_hash(payload)
    item_kind = str(getattr(tender, "item_kind", "TENDER"))
    if item_kind not in {"TENDER", "REGULATORY_NOTICE", "AUCTION_NOTICE"}:
        raise EngineError(f"unsupported canonical item kind: {item_kind}")
    title = str(getattr(tender, "title", tender.project_name))
    existing = conn.execute(
        "SELECT content_hash FROM canonical_items WHERE canonical_key=?",
        (tender.canonical_key,),
    ).fetchone()
    changed = existing is None or str(existing["content_hash"]) != content_hash
    if existing is None:
        conn.execute(
            """
            INSERT INTO canonical_items(
                canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,
                content_hash,evidence_sha256,payload_json,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                tender.canonical_key,
                source_id,
                item_kind,
                title,
                tender.reference_no,
                tender.project_name,
                tender.publication_date,
                tender.deadline,
                tender.location,
                tender.url,
                content_hash,
                evidence_digest,
                payload_json,
                observed_at,
                observed_at,
            ),
        )
    elif changed:
        conn.execute(
            """
            UPDATE canonical_items SET item_kind=?,title=?,reference_no=?,project_name=?,publication_date=?,deadline=?,location=?,url=?,
                content_hash=?,evidence_sha256=?,payload_json=?,updated_at=? WHERE canonical_key=?
            """,
            (
                item_kind,
                title,
                tender.reference_no,
                tender.project_name,
                tender.publication_date,
                tender.deadline,
                tender.location,
                tender.url,
                content_hash,
                evidence_digest,
                payload_json,
                observed_at,
                tender.canonical_key,
            ),
        )
    else:
        conn.execute(
            "UPDATE canonical_items SET evidence_sha256=?,url=?,updated_at=? WHERE canonical_key=?",
            (evidence_digest, tender.url, observed_at, tender.canonical_key),
        )

    signal_count = 0
    if changed and not suppress_signal:
        signal_type = "NEW" if existing is None else "UPDATED"
        signal_payload = _json({"signal_type": signal_type, "canonical_key": tender.canonical_key, **payload})
        conn.execute(
            "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), source_id, tender.canonical_key, signal_type, observed_at, signal_payload),
        )
        signal_count = 1
    return changed, signal_count


def _acquire_source_bytes(
    *,
    source: dict,
    database: Path,
    scheduler_run_id: str,
    source_id: str,
    reason: str,
    target_kind: str,
    url: str,
    expected_content_types: list[str],
    observed_at: str,
    fetcher: Fetcher,
):
    common = {
        "database": database,
        "scheduler_run_id": scheduler_run_id,
        "source_id": source_id,
        "source_policy_version": int(source["source_policy_version"]),
        "reason": reason,
        "egress_profile": str(source["egress_profile"]),
        "target_kind": target_kind,
        "url": url,
        "timeout_seconds": int(source["request_timeout_seconds"]),
        "max_bytes": int(source["request_max_bytes"]),
        "expected_content_types": expected_content_types,
        "observed_at": observed_at,
    }
    engine = source.get("engine")
    if engine == "direct_http":
        effective_fetcher = fetcher
        if source.get("http_fetch_profile") == "cloudrity_d1n_v1" and fetcher is fetch_bytes:
            effective_fetcher = fetch_bytes_cloudrity_d1n
        return acquire_local_bytes(**common, fetcher=effective_fetcher)
    if engine == "provider":
        roles = source.get("provider_target_roles") or {}
        target_role = roles.get(target_kind)
        if not isinstance(target_role, str) or not target_role:
            raise EngineError(f"provider target role missing for {source_id} {target_kind}")
        return acquire_provider_bytes(
            **common,
            target_role=target_role,
            capability=str(source.get("provider_capability", "C0_FETCH")),
        )
    raise EngineError(f"unsupported source engine: {source_id}")


def run_source(
    source_id: str,
    *,
    registry: Registry | None = None,
    now: datetime | None = None,
    fetcher: Fetcher = fetch_bytes,
    sleeper: Callable[[float], None] = time.sleep,
    force: bool = False,
    database: Path | None = None,
    evidence: Path | None = None,
    worker_context: dict | None = None,
    trigger_kind_override: str | None = None,
) -> dict[str, object]:
    registry = registry or Registry.load()
    source = registry.source(source_id)
    adapter = adapter_for(source_id, source)
    now = (now or datetime.now(UTC)).astimezone(UTC)
    observed_at = _iso(now)
    database = database or db_path()
    migrate(database)
    worker = worker_context or load_worker_context()

    with connect(database) as conn:
        state = _source_state(conn, source_id)
        if not force and state is not None:
            due = _parse_iso(state["next_due_at"])
            if due is not None and due > now:
                return {"source_id": source_id, "status": "NOT_DUE", "next_due_at": state["next_due_at"]}
        baseline = state is None or int(state["baseline_complete"]) == 0
        recovery, outage_start, outage_end = _recovery_context(state, now, source, baseline=baseline)

    app_run_id = str(uuid.uuid4())
    if trigger_kind_override is not None and trigger_kind_override != "MANUAL":
        raise EngineError("unsupported trigger kind override")
    trigger_kind = trigger_kind_override or ("RECONCILIATION" if recovery else "POLL")
    trigger_id = (
        f"manual:{source_id}:{app_run_id}"
        if trigger_kind == "MANUAL"
        else f"{trigger_kind.lower()}:{source_id}:{int(now.timestamp()) // int(source['poll_interval_seconds'])}"
    )
    with connect(database) as conn, conn:
        conn.execute(
            """
            INSERT INTO scheduler_runs(
                app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,status,baseline,
                recovery,outage_window_start,outage_window_end
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                app_run_id,
                trigger_id,
                trigger_kind,
                source_id,
                str(worker["run_id"]),
                observed_at,
                "RUNNING",
                int(baseline),
                int(recovery),
                outage_start,
                outage_end,
            ),
        )

    changed_count = 0
    signals_created = 0
    fetched = 0
    items_parsed = 0
    tenders_parsed = 0
    detail_errors = 0
    details_attempted = 0
    details_succeeded = 0
    health_probe = False
    health_probe_url: str | None = None
    backlog_remaining = 0
    try:
        sitemap_capture = _acquire_source_bytes(
            source=source,
            database=database,
            scheduler_run_id=app_run_id,
            source_id=source_id,
            reason=request_reason(trigger_kind),
            target_kind="DISCOVERY",
            url=str(source["discovery_url"]),
            expected_content_types=list(adapter.discovery_content_types),
            observed_at=observed_at,
            fetcher=fetcher,
        )
        sitemap_bytes = sitemap_capture.payload
        sitemap_hash = sitemap_capture.sha256
        # Evidence retention is tied to acquisition success, not parser success.
        # Assurance must be able to replay zero-item and parser-failure outcomes.
        _write_evidence(source_id, sitemap_bytes, sitemap_hash, evidence)

        if adapter.parse_discovery_records is not None:
            try:
                discovery_records = adapter.parse_discovery_records(sitemap_bytes, str(source["discovery_url"]))
            except Exception:
                record_processing(
                    database=database,
                    capture=sitemap_capture,
                    source_id=source_id,
                    observed_at=observed_at,
                    parser_version=adapter.discovery_parser_version,
                    normalizer_version=adapter.normalizer_version,
                    canonicalizer_version=adapter.canonicalizer_version,
                    status="FAILED",
                    items_found=0,
                    canonical_items=0,
                    signals_created=0,
                    failure=ProcessingFailure.HTML_PARSE_FAILURE,
                )
                raise

            items_parsed = len(discovery_records)
            tenders_parsed = sum(
                1 for item in discovery_records if str(getattr(item, "item_kind", "TENDER")) == "TENDER"
            )
            listing_changed = 0
            listing_signals = 0
            try:
                with connect(database) as conn, conn:
                    for item in discovery_records:
                        listing_semantic_transition = _listing_semantic_transition_only(
                            conn, source=source, tender=item
                        )
                        changed, signals = _upsert_tender(
                            conn,
                            source_id=source_id,
                            tender=item,
                            observed_at=observed_at,
                            suppress_signal=baseline or listing_semantic_transition,
                            evidence_digest=sitemap_hash,
                        )
                        listing_changed += int(changed)
                        listing_signals += signals
            except Exception:
                record_processing(
                    database=database,
                    capture=sitemap_capture,
                    source_id=source_id,
                    observed_at=observed_at,
                    parser_version=adapter.discovery_parser_version,
                    normalizer_version=adapter.normalizer_version,
                    canonicalizer_version=adapter.canonicalizer_version,
                    status="FAILED",
                    items_found=len(discovery_records),
                    canonical_items=0,
                    signals_created=0,
                    failure=ProcessingFailure.CANONICAL_VALIDATION_FAILURE,
                )
                raise

            record_processing(
                database=database,
                capture=sitemap_capture,
                source_id=source_id,
                observed_at=observed_at,
                parser_version=adapter.discovery_parser_version,
                normalizer_version=adapter.normalizer_version,
                canonicalizer_version=adapter.canonicalizer_version,
                status="SUCCESS",
                items_found=len(discovery_records),
                canonical_items=len(discovery_records),
                signals_created=listing_signals,
            )
            changed_count += listing_changed
            signals_created += listing_signals
            backlog_remaining = 0
            next_due = _iso(now + timedelta(seconds=int(source["poll_interval_seconds"])))

            with connect(database) as conn, conn:
                if not baseline:
                    signals_created += _reconcile_actionable_baseline_signals(
                        conn,
                        source_id=source_id,
                        source=source,
                        now=now,
                        observed_at=observed_at,
                    )
                conn.execute(
                    """
                    INSERT INTO source_state(
                        source_id,baseline_complete,sitemap_hash,last_snapshot_at,last_success_at,
                        last_successful_reconciliation_at,next_due_at,last_error,consecutive_failures,
                        recovery_window_start,recovery_window_end,updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(source_id) DO UPDATE SET
                        baseline_complete=1,
                        sitemap_hash=excluded.sitemap_hash,
                        last_snapshot_at=excluded.last_snapshot_at,
                        last_success_at=excluded.last_success_at,
                        last_successful_reconciliation_at=excluded.last_success_at,
                        next_due_at=excluded.next_due_at,
                        last_error=NULL,
                        consecutive_failures=0,
                        recovery_window_start=NULL,
                        recovery_window_end=NULL,
                        updated_at=excluded.updated_at
                    """,
                    (
                        source_id, 1, sitemap_hash, observed_at, observed_at, observed_at, next_due,
                        None, 0, None, None, observed_at,
                    ),
                )
                conn.execute(
                    """
                    UPDATE scheduler_runs
                    SET finished_at=?,status='SUCCESS',changed=?,signals_created=?,backlog_remaining=0,
                        details_attempted=0,details_succeeded=0,tenders_parsed=?,items_parsed=?,error=NULL
                    WHERE app_run_id=?
                    """,
                    (observed_at, changed_count, signals_created, tenders_parsed, items_parsed, app_run_id),
                )

            return {
                "source_id": source_id,
                "status": "SUCCESS",
                "baseline": baseline,
                "recovery": recovery,
                "trigger_type": trigger_kind,
                "outage_window_start": outage_start,
                "outage_window_end": outage_end,
                "worker_run_id": worker["run_id"],
                "app_run_id": app_run_id,
                "discovered": len(discovery_records),
                "candidates": 0,
                "fetched": 0,
                "detail_errors": 0,
                "items": items_parsed,
                "tenders": tenders_parsed,
                "details_attempted": 0,
                "details_succeeded": 0,
                "health_probe": False,
                "changed": changed_count,
                "signals_created": signals_created,
                "backlog_remaining": 0,
                "next_due_at": next_due,
                "listing_complete": True,
            }

        try:
            entries = adapter.parse_discovery(sitemap_bytes)
        except Exception:
            record_processing(
                database=database,
                capture=sitemap_capture,
                source_id=source_id,
                observed_at=observed_at,
                parser_version=adapter.discovery_parser_version,
                normalizer_version="discovery-v1",
                canonicalizer_version="none",
                status="FAILED",
                items_found=0,
                canonical_items=0,
                signals_created=0,
                failure=ProcessingFailure.PROCESSING_UNKNOWN,
            )
            raise
        record_processing(
            database=database,
            capture=sitemap_capture,
            source_id=source_id,
            observed_at=observed_at,
            parser_version=adapter.discovery_parser_version,
            normalizer_version="discovery-v1",
            canonicalizer_version="none",
            status="SUCCESS",
            items_found=len(entries),
            canonical_items=0,
            signals_created=0,
        )

        with connect(database) as conn, conn:
            _upsert_discovery_snapshot(conn, source_id, entries, observed_at, baseline=baseline)
            if baseline:
                candidates = _baseline_candidates(entries, now=now, source=source)
                _acknowledge_baseline_exclusions(conn, source_id, entries, candidates)
            else:
                _schedule_detail_parser_replay(
                    conn,
                    source_id=source_id,
                    source=source,
                    adapter=adapter,
                    entries=entries,
                    observed_at=observed_at,
                )
                candidates = _pending_candidates(conn, source_id, int(source["delta_detail_limit"]))

        known_tender_urls = set(str(url) for url in source.get("bootstrap_seed_urls", []))
        with connect(database) as conn:
            known_tender_urls.update(
                str(row[0])
                for row in conn.execute(
                    "SELECT url FROM discovery_items WHERE source_id=? AND canonical_key IS NOT NULL",
                    (source_id,),
                )
            )
            latest_parse_row = conn.execute(
                "SELECT started_at FROM scheduler_runs WHERE source_id=? AND details_attempted>0 ORDER BY started_at DESC LIMIT 1",
                (source_id,),
            ).fetchone()

        if source.get("discovery_is_tender_only") is True:
            known_tender_urls.update(entry.url for entry in entries)

        if not baseline and not any(entry.url in known_tender_urls for entry in candidates):
            health_policy = source.get("health_policy") or {}
            probe_interval = int(health_policy.get("parse_probe_interval_seconds", 3600))
            latest_parse_at = _parse_iso(latest_parse_row[0]) if latest_parse_row else None
            probe_due = latest_parse_at is None or (now - latest_parse_at).total_seconds() >= probe_interval
            if probe_due and len(candidates) < int(source["delta_detail_limit"]):
                by_url = {entry.url: entry for entry in entries}
                selected_urls = {entry.url for entry in candidates}
                probe_urls: list[str] = []
                if source.get("discovery_is_tender_only") is True:
                    probe_urls.extend(
                        entry.url for entry in sorted(entries, key=lambda item: item.lastmod or "", reverse=True)
                    )
                probe_urls.extend(str(url) for url in source.get("bootstrap_seed_urls", []))
                for probe_url in probe_urls:
                    probe_entry = by_url.get(probe_url)
                    if probe_entry is not None and probe_entry.url not in selected_urls:
                        candidates.append(probe_entry)
                        health_probe = True
                        health_probe_url = probe_entry.url
                        break

        delay = max(0, int(source["request_delay_ms"])) / 1000.0
        for index, entry in enumerate(candidates):
            expected_tender = entry.url in known_tender_urls
            if expected_tender:
                details_attempted += 1
            if index and delay:
                sleeper(delay)
            try:
                detail_capture = _acquire_source_bytes(
                    source=source,
                    database=database,
                    scheduler_run_id=app_run_id,
                    source_id=source_id,
                    reason=request_reason(trigger_kind, health_probe=entry.url == health_probe_url),
                    target_kind="HTML",
                    url=entry.url,
                    expected_content_types=["text/html"],
                    observed_at=observed_at,
                    fetcher=fetcher,
                )
            except Exception:
                detail_errors += 1
                continue

            html = detail_capture.payload
            evidence_digest = detail_capture.sha256
            processing_capture = detail_capture
            attachment_captures = []
            attachment_payloads: list[tuple[str, bytes]] = []
            # Preserve the acquired detail before attachment extraction or parsing.
            _write_evidence(source_id, html, detail_capture.sha256, evidence)

            if adapter.extract_detail_attachments is not None:
                attachment_policy = source.get("attachment_policy") or {}
                required_count = int(attachment_policy.get("required_primary_attachments", 0))
                max_count = int(attachment_policy.get("max_primary_attachments", 0))
                if attachment_policy.get("fetch_in_primary_pipeline") is not True or max_count < 1:
                    detail_errors += 1
                    continue
                try:
                    attachment_urls = adapter.extract_detail_attachments(html, entry.url)
                except Exception:
                    detail_errors += 1
                    continue
                if len(attachment_urls) < required_count or len(attachment_urls) > max_count:
                    detail_errors += 1
                    continue
                if attachment_policy.get("same_origin_only") is True:
                    detail_origin = urlparse(entry.url)
                    same_origin = all(
                        (lambda parsed: (
                            parsed.scheme == detail_origin.scheme
                            and parsed.hostname == detail_origin.hostname
                            and (parsed.port or (443 if parsed.scheme == "https" else 80))
                            == (detail_origin.port or (443 if detail_origin.scheme == "https" else 80))
                        ))(urlparse(attachment_url))
                        for attachment_url in attachment_urls
                    )
                    if not same_origin:
                        detail_errors += 1
                        continue
                try:
                    for attachment_url in attachment_urls:
                        attachment_capture = _acquire_source_bytes(
                            source=source,
                            database=database,
                            scheduler_run_id=app_run_id,
                            source_id=source_id,
                            reason=request_reason(trigger_kind, health_probe=entry.url == health_probe_url),
                            target_kind="PDF",
                            url=attachment_url,
                            expected_content_types=["application/pdf"],
                            observed_at=observed_at,
                            fetcher=fetcher,
                        )
                        attachment_captures.append(attachment_capture)
                        attachment_payloads.append((attachment_url, attachment_capture.payload))
                        _write_evidence(
                            source_id,
                            attachment_capture.payload,
                            attachment_capture.sha256,
                            evidence,
                            suffix=".pdf",
                        )
                except Exception:
                    if required_count > 0:
                        detail_errors += 1
                        continue
                    attachment_captures.clear()
                    attachment_payloads.clear()
                if len(attachment_captures) == 1:
                    processing_capture = attachment_captures[0]
                    evidence_digest = processing_capture.sha256

            try:
                if adapter.parse_detail_with_attachments is not None:
                    parsed_tenders = adapter.parse_detail_with_attachments(html, entry.url, attachment_payloads)
                else:
                    parsed_tenders = adapter.parse_detail(html, entry.url)
            except Exception:
                record_processing(
                    database=database,
                    capture=processing_capture,
                    source_id=source_id,
                    observed_at=observed_at,
                    parser_version=adapter.detail_parser_version,
                    normalizer_version=adapter.normalizer_version,
                    canonicalizer_version=adapter.canonicalizer_version,
                    status="FAILED",
                    items_found=0,
                    canonical_items=0,
                    signals_created=0,
                    failure=(
                        ProcessingFailure.PDF_PARSE_FAILURE
                        if adapter.parse_detail_with_attachments is not None
                        else ProcessingFailure.HTML_PARSE_FAILURE
                    ),
                )
                detail_errors += 1
                continue

            fetched += 1
            with connect(database) as conn, conn:
                discovery = conn.execute(
                    "SELECT suppress_signal_once,content_hash FROM discovery_items WHERE source_id=? AND url=?",
                    (source_id, entry.url),
                ).fetchone()
                suppress_once = bool(discovery and int(discovery["suppress_signal_once"] or 0))
                evidence_unchanged = bool(
                    not attachment_captures
                    and discovery
                    and discovery["content_hash"]
                    and str(discovery["content_hash"]) == detail_capture.sha256
                )
                conn.execute(
                    """
                    UPDATE discovery_items
                    SET content_hash=?,last_fetched_at=?,fetched_lastmod=lastmod,pending_since_at=NULL,
                        suppress_signal_once=0
                    WHERE source_id=? AND url=?
                    """,
                    (evidence_digest, observed_at, source_id, entry.url),
                )

            if not parsed_tenders:
                record_processing(
                    database=database,
                    capture=processing_capture,
                    source_id=source_id,
                    observed_at=observed_at,
                    parser_version=adapter.detail_parser_version,
                    normalizer_version=adapter.normalizer_version,
                    canonicalizer_version=adapter.canonicalizer_version,
                    status="SUCCESS",
                    items_found=0,
                    canonical_items=0,
                    signals_created=0,
                )
                continue

            items_parsed += len(parsed_tenders)
            tenders_parsed += sum(
                1 for item in parsed_tenders if str(getattr(item, "item_kind", "TENDER")) == "TENDER"
            )
            if expected_tender:
                details_succeeded += 1
            detail_changed = 0
            detail_signals = 0
            try:
                with connect(database) as conn, conn:
                    canonical_marker = parsed_tenders[0].canonical_key if len(parsed_tenders) == 1 else None
                    conn.execute(
                        "UPDATE discovery_items SET canonical_key=? WHERE source_id=? AND url=?",
                        (canonical_marker, source_id, entry.url),
                    )
                    for tender in parsed_tenders:
                        initial_attachment_enrichment = bool(
                            attachment_captures
                            and _initial_attachment_enrichment_only(conn, source=source, tender=tender)
                        )
                        changed, signals = _upsert_tender(
                            conn,
                            source_id=source_id,
                            tender=tender,
                            observed_at=observed_at,
                            suppress_signal=(
                                baseline or suppress_once or evidence_unchanged or initial_attachment_enrichment
                            ),
                            evidence_digest=evidence_digest,
                        )
                        detail_changed += int(changed)
                        detail_signals += signals
            except Exception:
                record_processing(
                    database=database,
                    capture=processing_capture,
                    source_id=source_id,
                    observed_at=observed_at,
                    parser_version=adapter.detail_parser_version,
                    normalizer_version=adapter.normalizer_version,
                    canonicalizer_version=adapter.canonicalizer_version,
                    status="FAILED",
                    items_found=len(parsed_tenders),
                    canonical_items=0,
                    signals_created=0,
                    failure=ProcessingFailure.CANONICAL_VALIDATION_FAILURE,
                )
                raise
            record_processing(
                database=database,
                capture=processing_capture,
                source_id=source_id,
                observed_at=observed_at,
                parser_version=adapter.detail_parser_version,
                normalizer_version=adapter.normalizer_version,
                canonicalizer_version=adapter.canonicalizer_version,
                status="SUCCESS",
                items_found=len(parsed_tenders),
                canonical_items=len(parsed_tenders),
                signals_created=detail_signals,
            )
            changed_count += detail_changed
            signals_created += detail_signals

        if candidates and fetched == 0 and detail_errors == len(candidates):
            raise RuntimeError("all bounded detail candidates failed")

        with connect(database) as conn:
            backlog_remaining, _oldest_pending = _pending_summary(conn, source_id)

        warning = f"detail_errors={detail_errors}" if detail_errors else None
        next_delay = int(source["retry_interval_seconds"] if backlog_remaining else source["poll_interval_seconds"])
        next_due = _iso(now + timedelta(seconds=next_delay))
        reconciliation_complete = backlog_remaining == 0
        recovery_window_start = None if reconciliation_complete else outage_start
        recovery_window_end = None if reconciliation_complete else outage_end

        with connect(database) as conn, conn:
            if not baseline:
                signals_created += _reconcile_actionable_baseline_signals(
                    conn,
                    source_id=source_id,
                    source=source,
                    now=now,
                    observed_at=observed_at,
                )
            conn.execute(
                """
                INSERT INTO source_state(
                    source_id,baseline_complete,sitemap_hash,last_snapshot_at,last_success_at,
                    last_successful_reconciliation_at,next_due_at,last_error,consecutive_failures,
                    recovery_window_start,recovery_window_end,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET
                    baseline_complete=1,
                    sitemap_hash=excluded.sitemap_hash,
                    last_snapshot_at=excluded.last_snapshot_at,
                    last_success_at=excluded.last_success_at,
                    last_successful_reconciliation_at=CASE
                        WHEN ? THEN excluded.last_success_at
                        ELSE source_state.last_successful_reconciliation_at
                    END,
                    next_due_at=excluded.next_due_at,
                    last_error=excluded.last_error,
                    consecutive_failures=0,
                    recovery_window_start=excluded.recovery_window_start,
                    recovery_window_end=excluded.recovery_window_end,
                    updated_at=excluded.updated_at
                """,
                (
                    source_id,
                    1,
                    sitemap_hash,
                    observed_at,
                    observed_at,
                    observed_at if reconciliation_complete else None,
                    next_due,
                    warning,
                    0,
                    recovery_window_start,
                    recovery_window_end,
                    observed_at,
                    int(reconciliation_complete),
                ),
            )
            conn.execute(
                """
                UPDATE scheduler_runs
                SET finished_at=?,status='SUCCESS',changed=?,signals_created=?,backlog_remaining=?,
                    details_attempted=?,details_succeeded=?,tenders_parsed=?,items_parsed=?,error=?
                WHERE app_run_id=?
                """,
                (
                    observed_at, changed_count, signals_created, backlog_remaining, details_attempted,
                    details_succeeded, tenders_parsed, items_parsed, warning, app_run_id,
                ),
            )

        return {
            "source_id": source_id,
            "status": "SUCCESS",
            "baseline": baseline,
            "recovery": recovery,
            "trigger_type": trigger_kind,
            "outage_window_start": outage_start,
            "outage_window_end": outage_end,
            "worker_run_id": worker["run_id"],
            "app_run_id": app_run_id,
            "discovered": len(entries),
            "candidates": len(candidates),
            "fetched": fetched,
            "detail_errors": detail_errors,
            "items": items_parsed,
            "tenders": tenders_parsed,
            "details_attempted": details_attempted,
            "details_succeeded": details_succeeded,
            "health_probe": health_probe,
            "changed": changed_count,
            "signals_created": signals_created,
            "backlog_remaining": backlog_remaining,
            "next_due_at": next_due,
        }
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"[:300]
        with connect(database) as conn:
            existing = _source_state(conn, source_id)
            existing_failures = int(existing["consecutive_failures"] or 0) if existing is not None else 0
            backlog_remaining, _oldest_pending = _pending_summary(conn, source_id)
            acquisition_failure = _latest_acquisition_failure(conn, app_run_id)
        consecutive_failures_after = existing_failures + 1
        retry_delay_seconds = _failure_retry_delay_seconds(
            source,
            failure_class=acquisition_failure,
            consecutive_failures_after=consecutive_failures_after,
        )
        retry_due = _iso(now + timedelta(seconds=retry_delay_seconds))
        with connect(database) as conn, conn:
            conn.execute(
                """
                INSERT INTO source_state(
                    source_id,baseline_complete,next_due_at,last_error,consecutive_failures,
                    recovery_window_start,recovery_window_end,updated_at
                ) VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET
                    next_due_at=excluded.next_due_at,
                    last_error=excluded.last_error,
                    consecutive_failures=excluded.consecutive_failures,
                    recovery_window_start=COALESCE(source_state.recovery_window_start,excluded.recovery_window_start),
                    recovery_window_end=COALESCE(source_state.recovery_window_end,excluded.recovery_window_end),
                    updated_at=excluded.updated_at
                """,
                (
                    source_id,
                    int(not baseline),
                    retry_due,
                    error,
                    consecutive_failures_after,
                    outage_start,
                    outage_end,
                    observed_at,
                ),
            )
            conn.execute(
                """
                UPDATE scheduler_runs
                SET finished_at=?,status='FAILED',changed=?,signals_created=?,backlog_remaining=?,
                    details_attempted=?,details_succeeded=?,tenders_parsed=?,items_parsed=?,error=?
                WHERE app_run_id=?
                """,
                (
                    observed_at, changed_count, signals_created, backlog_remaining, details_attempted,
                    details_succeeded, tenders_parsed, items_parsed, error, app_run_id,
                ),
            )
        raise


def run_due(**kwargs) -> dict[str, object]:  # type: ignore[no-untyped-def]
    registry = kwargs.pop("registry", None) or Registry.load()
    results = []
    for source_id, _source in registry.enabled_sources():
        try:
            results.append(run_source(source_id, registry=registry, **kwargs))
        except Exception as exc:
            results.append(
                {
                    "source_id": source_id,
                    "status": "FAILED",
                    "error": f"{type(exc).__name__}: {exc}"[:300],
                }
            )
    failures = [item for item in results if item.get("status") == "FAILED"]
    return {"status": "FAILED" if failures else "SUCCESS", "results": results}
