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


def _previous_discovery(conn, source_id: str) -> dict[str, tuple[str | None, str | None]]:  # type: ignore[no-untyped-def]
    return {
        str(row["url"]): (row["lastmod"], row["last_fetched_at"])
        for row in conn.execute("SELECT url,lastmod,last_fetched_at FROM discovery_items WHERE source_id=?", (source_id,))
    }


def _select_candidates(
    entries: list[SitemapEntry],
    previous: dict[str, tuple[str | None, str | None]],
    *,
    baseline: bool,
    now: datetime,
    source: dict,
) -> list[SitemapEntry]:
    if baseline:
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
    changed = [
        entry
        for entry in entries
        if entry.url not in previous
        or previous[entry.url][0] != entry.lastmod
        or previous[entry.url][1] is None
    ]
    changed.sort(key=lambda entry: entry.lastmod or "", reverse=True)
    return changed[: int(source["delta_detail_limit"])]


def _upsert_discovery_snapshot(conn, source_id: str, entries: list[SitemapEntry], observed_at: str) -> None:  # type: ignore[no-untyped-def]
    for entry in entries:
        conn.execute(
            """
            INSERT INTO discovery_items(source_id,url,lastmod,first_seen_at,last_seen_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(source_id,url) DO UPDATE SET lastmod=excluded.lastmod,last_seen_at=excluded.last_seen_at
            """,
            (source_id, entry.url, entry.lastmod, observed_at, observed_at),
        )


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
    baseline: bool,
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
    if changed and not baseline:
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
        previous = _previous_discovery(conn, source_id)

    app_run_id = str(uuid.uuid4())
    trigger_id = f"poll:{source_id}:{int(now.timestamp()) // int(source['poll_interval_seconds'])}"
    with connect(database) as conn, conn:
        conn.execute(
            """
            INSERT INTO scheduler_runs(app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,status,baseline)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (app_run_id, trigger_id, "poll", source_id, str(worker["run_id"]), observed_at, "RUNNING", int(baseline)),
        )

    changed_count = 0
    signals_created = 0
    fetched = 0
    tenders = 0
    detail_errors = 0
    try:
        sitemap_bytes = fetcher(
            str(source["discovery_url"]),
            timeout=int(source["request_timeout_seconds"]),
            max_bytes=int(source["request_max_bytes"]),
        )
        sitemap_hash = hashlib.sha256(sitemap_bytes).hexdigest()
        entries = parse_sitemap(sitemap_bytes)
        candidates = _select_candidates(entries, previous, baseline=baseline, now=now, source=source)

        with connect(database) as conn, conn:
            _upsert_discovery_snapshot(conn, source_id, entries, observed_at)

        delay = max(0, int(source["request_delay_ms"])) / 1000.0
        for index, entry in enumerate(candidates):
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
                conn.execute(
                    "UPDATE discovery_items SET content_hash=?,last_fetched_at=? WHERE source_id=? AND url=?",
                    (evidence_digest, observed_at, source_id, entry.url),
                )
            if tender is None:
                continue
            tenders += 1
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
                    baseline=baseline,
                    evidence_digest=evidence_digest,
                )
            changed_count += int(changed)
            signals_created += signals

        if candidates and fetched == 0 and detail_errors == len(candidates):
            raise RuntimeError("all bounded detail candidates failed")
        warning = f"detail_errors={detail_errors}" if detail_errors else None
        next_due = _iso(now + timedelta(seconds=int(source["poll_interval_seconds"])))
        with connect(database) as conn, conn:
            conn.execute(
                """
                INSERT INTO source_state(source_id,baseline_complete,sitemap_hash,last_success_at,next_due_at,last_error,updated_at)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET baseline_complete=1,sitemap_hash=excluded.sitemap_hash,
                    last_success_at=excluded.last_success_at,next_due_at=excluded.next_due_at,last_error=excluded.last_error,updated_at=excluded.updated_at
                """,
                (source_id, 1, sitemap_hash, observed_at, next_due, warning, observed_at),
            )
            conn.execute(
                """
                UPDATE scheduler_runs SET finished_at=?,status='SUCCESS',changed=?,signals_created=?,error=?
                WHERE app_run_id=?
                """,
                (observed_at, changed_count, signals_created, warning, app_run_id),
            )
        return {
            "source_id": source_id,
            "status": "SUCCESS",
            "baseline": baseline,
            "worker_run_id": worker["run_id"],
            "app_run_id": app_run_id,
            "discovered": len(entries),
            "candidates": len(candidates),
            "fetched": fetched,
            "detail_errors": detail_errors,
            "tenders": tenders,
            "changed": changed_count,
            "signals_created": signals_created,
            "next_due_at": next_due,
        }
    except Exception as exc:
        retry_due = _iso(now + timedelta(seconds=int(source["retry_interval_seconds"])))
        error = f"{type(exc).__name__}: {exc}"[:300]
        with connect(database) as conn, conn:
            conn.execute(
                """
                INSERT INTO source_state(source_id,baseline_complete,next_due_at,last_error,updated_at)
                VALUES (?,?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET next_due_at=excluded.next_due_at,last_error=excluded.last_error,updated_at=excluded.updated_at
                """,
                (source_id, int(not baseline), retry_due, error, observed_at),
            )
            conn.execute(
                "UPDATE scheduler_runs SET finished_at=?,status='FAILED',changed=?,signals_created=?,error=? WHERE app_run_id=?",
                (observed_at, changed_count, signals_created, error, app_run_id),
            )
        raise


def run_due(**kwargs) -> dict[str, object]:  # type: ignore[no-untyped-def]
    registry = kwargs.pop("registry", None) or Registry.load()
    results = []
    for source_id, _source in registry.enabled_sources():
        results.append(run_source(source_id, registry=registry, **kwargs))
    failures = [item for item in results if item.get("status") == "FAILED"]
    return {"status": "FAILED" if failures else "SUCCESS", "results": results}
