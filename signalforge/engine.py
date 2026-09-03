from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from .config import Registry, db_path, evidence_root
from .db import connect, migrate
from .http import fetch_bytes
from .mpt import SitemapEntry, parse_sitemap, parse_tender_detail
from .worker_context import load_worker_context


Fetcher = Callable[..., bytes]


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


def _material_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


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


def _write_evidence(source_id: str, html: bytes, digest: str, root: Path | None = None) -> Path:
    target_root = root or evidence_root()
    directory = target_root / source_id
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{digest}.html"
    if not target.exists():
        tmp = target.with_suffix(".html.part")
        tmp.write_bytes(html)
        tmp.replace(target)
        target.chmod(0o640)
    return target


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
    existing = conn.execute(
        "SELECT content_hash FROM canonical_items WHERE canonical_key=?",
        (tender.canonical_key,),
    ).fetchone()
    changed = existing is None or str(existing["content_hash"]) != content_hash
    if existing is None:
        conn.execute(
            """
            INSERT INTO canonical_items(
                canonical_key,source_id,reference_no,project_name,publication_date,deadline,location,url,
                content_hash,evidence_sha256,payload_json,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                tender.canonical_key,
                source_id,
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
            UPDATE canonical_items SET reference_no=?,project_name=?,publication_date=?,deadline=?,location=?,url=?,
                content_hash=?,evidence_sha256=?,payload_json=?,updated_at=? WHERE canonical_key=?
            """,
            (
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
    tenders = 0
    detail_errors = 0
    details_attempted = 0
    details_succeeded = 0
    health_probe = False
    backlog_remaining = 0
    try:
        sitemap_bytes = fetcher(
            str(source["discovery_url"]),
            timeout=int(source["request_timeout_seconds"]),
            max_bytes=int(source["request_max_bytes"]),
        )
        sitemap_hash = hashlib.sha256(sitemap_bytes).hexdigest()
        entries = parse_sitemap(sitemap_bytes)

        with connect(database) as conn, conn:
            _upsert_discovery_snapshot(conn, source_id, entries, observed_at, baseline=baseline)
            if baseline:
                candidates = _baseline_candidates(entries, now=now, source=source)
                _acknowledge_baseline_exclusions(conn, source_id, entries, candidates)
            else:
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

        if not baseline and not any(entry.url in known_tender_urls for entry in candidates):
            health_policy = source.get("health_policy") or {}
            probe_interval = int(health_policy.get("parse_probe_interval_seconds", 3600))
            latest_parse_at = _parse_iso(latest_parse_row[0]) if latest_parse_row else None
            probe_due = latest_parse_at is None or (now - latest_parse_at).total_seconds() >= probe_interval
            if probe_due and len(candidates) < int(source["delta_detail_limit"]):
                by_url = {entry.url: entry for entry in entries}
                selected_urls = {entry.url for entry in candidates}
                for seed_url in source.get("bootstrap_seed_urls", []):
                    probe_entry = by_url.get(str(seed_url))
                    if probe_entry is not None and probe_entry.url not in selected_urls:
                        candidates.append(probe_entry)
                        health_probe = True
                        break

        delay = max(0, int(source["request_delay_ms"])) / 1000.0
        for index, entry in enumerate(candidates):
            expected_tender = entry.url in known_tender_urls
            if expected_tender:
                details_attempted += 1
            if index and delay:
                sleeper(delay)
            try:
                html = fetcher(
                    entry.url,
                    timeout=int(source["request_timeout_seconds"]),
                    max_bytes=int(source["request_max_bytes"]),
                )
                tender = parse_tender_detail(html, entry.url)
            except Exception:
                detail_errors += 1
                continue

            fetched += 1
            evidence_digest = hashlib.sha256(html).hexdigest()
            with connect(database) as conn, conn:
                discovery = conn.execute(
                    "SELECT suppress_signal_once FROM discovery_items WHERE source_id=? AND url=?",
                    (source_id, entry.url),
                ).fetchone()
                suppress_once = bool(discovery and int(discovery["suppress_signal_once"] or 0))
                conn.execute(
                    """
                    UPDATE discovery_items
                    SET content_hash=?,last_fetched_at=?,fetched_lastmod=lastmod,pending_since_at=NULL,
                        suppress_signal_once=0
                    WHERE source_id=? AND url=?
                    """,
                    (evidence_digest, observed_at, source_id, entry.url),
                )

            if tender is None:
                continue
            tenders += 1
            if expected_tender:
                details_succeeded += 1
            _write_evidence(source_id, html, evidence_digest, evidence)
            with connect(database) as conn, conn:
                conn.execute(
                    "UPDATE discovery_items SET canonical_key=? WHERE source_id=? AND url=?",
                    (tender.canonical_key, source_id, entry.url),
                )
                changed, signals = _upsert_tender(
                    conn,
                    source_id=source_id,
                    tender=tender,
                    observed_at=observed_at,
                    suppress_signal=baseline or suppress_once,
                    evidence_digest=evidence_digest,
                )
            changed_count += int(changed)
            signals_created += signals

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
                    details_attempted=?,details_succeeded=?,tenders_parsed=?,error=?
                WHERE app_run_id=?
                """,
                (
                    observed_at, changed_count, signals_created, backlog_remaining, details_attempted,
                    details_succeeded, tenders, warning, app_run_id,
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
            "tenders": tenders,
            "details_attempted": details_attempted,
            "details_succeeded": details_succeeded,
            "health_probe": health_probe,
            "changed": changed_count,
            "signals_created": signals_created,
            "backlog_remaining": backlog_remaining,
            "next_due_at": next_due,
        }
    except Exception as exc:
        retry_due = _iso(now + timedelta(seconds=int(source["retry_interval_seconds"])))
        error = f"{type(exc).__name__}: {exc}"[:300]
        with connect(database) as conn:
            existing = _source_state(conn, source_id)
            existing_failures = int(existing["consecutive_failures"] or 0) if existing is not None else 0
            backlog_remaining, _oldest_pending = _pending_summary(conn, source_id)
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
                    existing_failures + 1,
                    outage_start,
                    outage_end,
                    observed_at,
                ),
            )
            conn.execute(
                """
                UPDATE scheduler_runs
                SET finished_at=?,status='FAILED',changed=?,signals_created=?,backlog_remaining=?,
                    details_attempted=?,details_succeeded=?,tenders_parsed=?,error=?
                WHERE app_run_id=?
                """,
                (
                    observed_at, changed_count, signals_created, backlog_remaining, details_attempted,
                    details_succeeded, tenders, error, app_run_id,
                ),
            )
        raise


def run_due(**kwargs) -> dict[str, object]:  # type: ignore[no-untyped-def]
    registry = kwargs.pop("registry", None) or Registry.load()
    results = []
    for source_id, _source in registry.enabled_sources():
        results.append(run_source(source_id, registry=registry, **kwargs))
    failures = [item for item in results if item.get("status") == "FAILED"]
    return {"status": "FAILED" if failures else "SUCCESS", "results": results}
