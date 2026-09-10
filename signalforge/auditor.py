from __future__ import annotations

import html
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from xml.etree import ElementTree

from .config import Registry, db_path
from .http import fetch_bytes, fetch_bytes_cloudrity_d1n

AUDITOR_VERSION = 1
DEFAULT_SIGNAL_LOOKBACK_HOURS = 24
DEFAULT_MPT_LOOKBACK_DAYS = 7
DEFAULT_MPT_PAGE_LIMIT = 30
ATOM_SITEMAP_URL = "https://www.atom.com.mm/sitemap.xml"

Fetcher = Callable[..., bytes]


@contextmanager
def _read_connection(path: Path):  # type: ignore[no-untyped-def]
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    try:
        yield conn
    finally:
        conn.close()


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _text(payload: bytes) -> str:
    parser = _TextParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    return " ".join(" ".join(parser.parts).split())


def _normalize_url(value: str) -> str:
    parsed = urlparse(value)
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


def _severity_rank(value: str) -> int:
    return {"GREEN": 0, "YELLOW": 1, "RED": 2}.get(value, 2)


def _source_health(conn, source_id: str, policy: dict[str, object], now: datetime) -> dict[str, object]:  # type: ignore[no-untyped-def]
    row = conn.execute("SELECT * FROM source_state WHERE source_id=?", (source_id,)).fetchone()
    if row is None:
        return {"source_health": "RED", "reason_code": "SOURCE_NOT_INITIALIZED"}

    health_policy = policy.get("health_policy")
    assert isinstance(health_policy, dict)
    last_success = _parse_iso(row["last_success_at"])
    freshness_age = max(0, int((now - last_success).total_seconds())) if last_success else None
    freshness_yellow = int(health_policy["freshness_yellow_seconds"])
    freshness_red = int(health_policy["freshness_red_seconds"])
    if freshness_age is None or freshness_age > freshness_red:
        freshness_health = "RED"
    elif freshness_age > freshness_yellow:
        freshness_health = "YELLOW"
    else:
        freshness_health = "GREEN"

    failures = int(row["consecutive_failures"] or 0)
    fetch_yellow = int(health_policy["fetch_yellow_failures"])
    fetch_red = int(health_policy["fetch_red_failures"])
    if failures >= fetch_red:
        fetch_health = "RED"
    elif failures >= fetch_yellow or row["last_error"]:
        fetch_health = "YELLOW"
    else:
        fetch_health = "GREEN"

    pending = conn.execute(
        "SELECT COUNT(*) AS count,MIN(pending_since_at) AS oldest FROM discovery_items WHERE source_id=? AND pending_since_at IS NOT NULL",
        (source_id,),
    ).fetchone()
    backlog = int(pending["count"])
    oldest = _parse_iso(pending["oldest"])
    recovery_slo = int(policy.get("recovery_slo_seconds", 1800))
    oldest_age = max(0, int((now - oldest).total_seconds())) if oldest else 0
    if backlog == 0:
        recovery_health = "GREEN"
    elif oldest_age <= recovery_slo:
        recovery_health = "YELLOW"
    else:
        recovery_health = "RED"

    parse_window = int(health_policy["parse_window_runs"])
    parse_sample_source = str(health_policy.get("parse_sample_source", "DETAIL_SCHEDULER"))
    if parse_sample_source == "BUSINESS_PROCESSING":
        rows = conn.execute(
            "SELECT status FROM processing_records WHERE source_id=? AND canonicalizer_version!='none' ORDER BY finished_at DESC LIMIT ?",
            (source_id, parse_window),
        ).fetchall()
        attempts = len(rows)
        successes = sum(1 for item in rows if str(item["status"]) == "SUCCESS")
    else:
        rows = conn.execute(
            "SELECT details_attempted,details_succeeded FROM scheduler_runs WHERE source_id=? AND details_attempted>0 ORDER BY started_at DESC LIMIT ?",
            (source_id, parse_window),
        ).fetchall()
        attempts = sum(int(item["details_attempted"] or 0) for item in rows)
        successes = sum(int(item["details_succeeded"] or 0) for item in rows)
    minimum = int(health_policy["parse_min_attempts"])
    ratio = successes / attempts if attempts else None
    if attempts < minimum:
        parse_health = "GREEN"
    elif ratio is not None and ratio < float(health_policy["parse_red_ratio"]):
        parse_health = "RED"
    elif ratio is not None and ratio < float(health_policy["parse_yellow_ratio"]):
        parse_health = "YELLOW"
    else:
        parse_health = "GREEN"

    components = {
        "fetch": fetch_health,
        "freshness": freshness_health,
        "parse": parse_health,
        "recovery": recovery_health,
    }
    overall = max(components.values(), key=_severity_rank)
    reason = next((name for name, state in components.items() if state == overall and state != "GREEN"), "OK")
    return {
        "source_health": overall,
        "reason_code": reason.upper() if reason != "OK" else "OK",
        "components": components,
        "consecutive_failures": failures,
        "last_success_at": row["last_success_at"],
        "freshness_age_seconds": freshness_age,
        "recovery_backlog": backlog,
        "parse_attempts": attempts,
        "parse_successes": successes,
    }


def _health_findings(conn, registry: Registry, now: datetime) -> tuple[list[dict[str, object]], dict[str, object]]:  # type: ignore[no-untyped-def]
    findings: list[dict[str, object]] = []
    snapshots: list[dict[str, object]] = []
    for source_id, policy in registry.enabled_sources():
        snapshot = _source_health(conn, source_id, policy, now)
        snapshots.append({"source_id": source_id, **snapshot})
        state = str(snapshot["source_health"])
        if state != "GREEN":
            findings.append(
                {
                    "type": "HEALTH_ALERT",
                    "severity": state,
                    "source_id": source_id,
                    "code": f"SOURCE_{snapshot['reason_code']}",
                    "summary": f"{source_id} source health is {state}",
                    "details": snapshot,
                }
            )
    return findings, {
        "checked_sources": len(snapshots),
        "non_green_sources": sum(1 for item in snapshots if item["source_health"] != "GREEN"),
        "sources": snapshots,
    }


def _mytel_official_keys(payload: bytes) -> tuple[set[str], list[dict[str, object]]]:
    decoded = json.loads(payload)
    rows = decoded.get("data") if isinstance(decoded, dict) else None
    if not isinstance(rows, list):
        raise ValueError("MYTEL official feed missing data list")
    keys: set[str] = set()
    records: list[dict[str, object]] = []
    ref_re = re.compile(r"(?P<num>\d{1,3})\s*/\s*(?P<year>20\d{2})\s*/\s*MYTEL\b", re.I)
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw = html.unescape(f"{row.get('name') or ''}\n{row.get('content') or ''}")
        lowered = raw.lower()
        if "telecom international myanmar" not in lowered or "mytel" not in lowered:
            continue
        match = ref_re.search(raw)
        if match is None:
            continue
        key = f"mytel:{int(match.group('num'))}-{match.group('year')}"
        keys.add(key)
        records.append(
            {
                "canonical_key": key,
                "source_post_id": row.get("id"),
                "created_at": row.get("created_at"),
                "name": re.sub(r"\s+", " ", str(row.get("name") or "")).strip()[:240],
            }
        )
    return keys, records


def _mpt_recent_urls(sitemap: bytes, *, now: datetime, lookback_days: int, page_limit: int) -> list[str]:
    root = ElementTree.fromstring(sitemap)
    cutoff = now - timedelta(days=lookback_days)
    candidates: list[tuple[datetime, str]] = []
    for node in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
        loc = node.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        lastmod = node.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
        if not loc or not lastmod:
            continue
        parsed = urlparse(loc.strip())
        if parsed.hostname not in {"mpt.com.mm", "www.mpt.com.mm"} or not parsed.path.startswith("/en/"):
            continue
        modified = _parse_iso(lastmod.strip())
        if modified is None or modified < cutoff:
            continue
        candidates.append((modified, loc.strip()))
    candidates.sort(reverse=True)
    seen: set[str] = set()
    urls: list[str] = []
    for _modified, url in candidates:
        normalized = _normalize_url(url)
        if normalized in seen:
            continue
        seen.add(normalized)
        urls.append(url)
        if len(urls) >= page_limit:
            break
    return urls


def _mpt_tender_like(payload: bytes) -> bool:
    normalized = _text(payload).lower()
    return "reference no" in normalized and "project name" in normalized


def _coverage_findings(
    conn,  # type: ignore[no-untyped-def]
    registry: Registry,
    now: datetime,
    *,
    fetcher: Fetcher,
    mytel_fetcher: Fetcher,
    mpt_lookback_days: int,
    mpt_page_limit: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    findings: list[dict[str, object]] = []
    summary: dict[str, object] = {}

    # MYTEL: independent identity extraction from the official feed; no production parser reuse.
    mytel = registry.source("S41")
    try:
        payload = mytel_fetcher(
            str(mytel["discovery_url"]),
            timeout=int(mytel["request_timeout_seconds"]),
            max_bytes=int(mytel["request_max_bytes"]),
        )
        official_keys, records = _mytel_official_keys(payload)
        db_keys = {str(row[0]) for row in conn.execute("SELECT canonical_key FROM canonical_items WHERE source_id='S41'")}
        missing = sorted(official_keys - db_keys)
        record_by_key = {str(item["canonical_key"]): item for item in records}
        for key in missing:
            findings.append(
                {
                    "type": "COVERAGE_GAP",
                    "severity": "RED",
                    "source_id": "S41",
                    "code": "MYTEL_OFFICIAL_RFP_NOT_CANONICAL",
                    "summary": f"Official MYTEL RFP {key} is missing from SignalForge canonical state",
                    "likely_layer": "DISCOVERY_OR_PARSER",
                    "official": record_by_key.get(key),
                }
            )
        summary["S41"] = {"status": "PASS" if not missing else "GAP", "official_keys": len(official_keys), "canonical_keys": len(db_keys), "missing": missing}
    except Exception as exc:
        findings.append(
            {
                "type": "HEALTH_ALERT",
                "severity": "YELLOW",
                "source_id": "S41",
                "code": "AUDITOR_MYTEL_RECONCILIATION_FAILED",
                "summary": "Auditor could not independently reconcile the MYTEL official feed",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        summary["S41"] = {"status": "CHECK_FAILED"}

    # MPT: independently inspect a bounded recent official sitemap head for tender-like pages.
    mpt = registry.source("S13")
    try:
        sitemap = fetcher(
            str(mpt["discovery_url"]),
            timeout=int(mpt["request_timeout_seconds"]),
            max_bytes=int(mpt["request_max_bytes"]),
        )
        recent_urls = _mpt_recent_urls(sitemap, now=now, lookback_days=mpt_lookback_days, page_limit=mpt_page_limit)
        canonical_urls = {
            _normalize_url(str(row[0]))
            for row in conn.execute("SELECT url FROM canonical_items WHERE source_id='S13'")
            if row[0]
        }
        discovery_urls = {
            _normalize_url(str(row[0]))
            for row in conn.execute("SELECT url FROM discovery_items WHERE source_id='S13'")
            if row[0]
        }
        tender_like = 0
        missing_count = 0
        page_errors = 0
        for url in recent_urls:
            try:
                page = fetcher(url, timeout=int(mpt["request_timeout_seconds"]), max_bytes=int(mpt["request_max_bytes"]))
            except Exception:
                page_errors += 1
                continue
            if not _mpt_tender_like(page):
                continue
            tender_like += 1
            normalized = _normalize_url(url)
            if normalized in canonical_urls:
                continue
            missing_count += 1
            likely = "DISCOVERY" if normalized not in discovery_urls else "PARSER_OR_CANONICAL"
            findings.append(
                {
                    "type": "COVERAGE_GAP",
                    "severity": "RED",
                    "source_id": "S13",
                    "code": "MPT_RECENT_TENDER_PAGE_NOT_CANONICAL",
                    "summary": "Recent official MPT tender-like page is missing from canonical state",
                    "url": url,
                    "likely_layer": likely,
                }
            )
        summary["S13"] = {
            "status": "PASS" if missing_count == 0 and page_errors == 0 else ("GAP" if missing_count else "PARTIAL"),
            "recent_sitemap_pages_checked": len(recent_urls),
            "tender_like_pages": tender_like,
            "missing": missing_count,
            "page_fetch_errors": page_errors,
            "lookback_days": mpt_lookback_days,
        }
        if page_errors:
            findings.append(
                {
                    "type": "HEALTH_ALERT",
                    "severity": "YELLOW",
                    "source_id": "S13",
                    "code": "AUDITOR_MPT_PAGE_CHECK_PARTIAL",
                    "summary": f"Auditor could not inspect {page_errors} recent MPT sitemap pages",
                }
            )
    except Exception as exc:
        findings.append(
            {
                "type": "HEALTH_ALERT",
                "severity": "YELLOW",
                "source_id": "S13",
                "code": "AUDITOR_MPT_RECONCILIATION_FAILED",
                "summary": "Auditor could not independently reconcile the MPT official sitemap head",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        summary["S13"] = {"status": "CHECK_FAILED"}

    return findings, summary


def _atom_surface_findings(fetcher: Fetcher) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Detect an official sitemap trigger without claiming it is a tender."""

    try:
        payload = fetcher(ATOM_SITEMAP_URL, timeout=30, max_bytes=2_000_000)
        root = ElementTree.fromstring(payload)
        terms = re.compile(r"(?:^|[-_/])(tender|procurement|rfp|rfq)(?:$|[-_/])", re.I)
        candidates: list[str] = []
        for node in root.iter():
            if not str(node.tag).endswith("loc") or not node.text:
                continue
            url = node.text.strip()
            parsed = urlparse(url)
            if parsed.hostname not in {"atom.com.mm", "www.atom.com.mm", "business.atom.com.mm"}:
                continue
            if terms.search(parsed.path):
                candidates.append(url)
        candidates = sorted(set(candidates))
        if not candidates:
            return [], {"status": "NO_TRIGGER", "sitemap_url": ATOM_SITEMAP_URL, "candidate_urls": []}
        finding = {
            "type": "SURFACE_TRIGGER",
            "severity": "YELLOW",
            "source_id": "S42",
            "code": "ATOM_PUBLIC_PROCUREMENT_SURFACE_CANDIDATE",
            "summary": "ATOM official sitemap now contains procurement-like public URLs; reopen the deferred source audit",
            "urls": candidates[:20],
        }
        return [finding], {"status": "REVIEW", "sitemap_url": ATOM_SITEMAP_URL, "candidate_urls": candidates[:20]}
    except Exception as exc:
        finding = {
            "type": "HEALTH_ALERT",
            "severity": "YELLOW",
            "source_id": "S42",
            "code": "AUDITOR_ATOM_SURFACE_CHECK_FAILED",
            "summary": "Auditor could not inspect the deferred ATOM official sitemap",
            "error": f"{type(exc).__name__}: {exc}",
        }
        return [finding], {"status": "CHECK_FAILED", "sitemap_url": ATOM_SITEMAP_URL}


def _deadline_findings(conn) -> tuple[list[dict[str, object]], dict[str, object]]:  # type: ignore[no-untyped-def]
    findings: list[dict[str, object]] = []
    rows = conn.execute(
        "SELECT canonical_key,source_id,publication_date,deadline,payload_json FROM canonical_items WHERE item_kind='TENDER'"
    ).fetchall()
    with_deadline = 0
    with_evidence = 0
    conflicts = 0
    for row in rows:
        try:
            payload = json.loads(str(row["payload_json"]))
        except json.JSONDecodeError:
            findings.append(
                {
                    "type": "DEADLINE_EVIDENCE_SUSPECT",
                    "severity": "RED",
                    "source_id": row["source_id"],
                    "canonical_key": row["canonical_key"],
                    "code": "CANONICAL_PAYLOAD_INVALID_JSON",
                    "summary": "Canonical tender payload cannot be audited for deadline evidence",
                }
            )
            continue
        if not isinstance(payload, dict):
            continue
        column_deadline = row["deadline"]
        payload_deadline = payload.get("deadline")
        deadline = payload_deadline or column_deadline
        evidence = str(payload.get("deadline_evidence") or "")
        if deadline:
            with_deadline += 1
            if evidence:
                with_evidence += 1
        if column_deadline != payload_deadline:
            findings.append(
                {
                    "type": "DEADLINE_EVIDENCE_SUSPECT",
                    "severity": "RED",
                    "source_id": row["source_id"],
                    "canonical_key": row["canonical_key"],
                    "code": "DEADLINE_COLUMN_PAYLOAD_MISMATCH",
                    "summary": "Canonical deadline column and payload disagree",
                    "column_deadline": column_deadline,
                    "payload_deadline": payload_deadline,
                }
            )
        if "CONFLICT" in evidence.upper():
            conflicts += 1
            if deadline:
                findings.append(
                    {
                        "type": "DEADLINE_EVIDENCE_SUSPECT",
                        "severity": "RED",
                        "source_id": row["source_id"],
                        "canonical_key": row["canonical_key"],
                        "code": "DEADLINE_ACCEPTED_DESPITE_EVIDENCE_CONFLICT",
                        "summary": "Canonical tender accepted a deadline while its evidence declares a conflict",
                    }
                )
    return findings, {
        "tenders_checked": len(rows),
        "with_deadline": with_deadline,
        "with_explicit_evidence": with_evidence,
        "without_explicit_evidence": with_deadline - with_evidence,
        "declared_conflicts": conflicts,
        "suspects": len(findings),
        "independently_validates_official_deadline": False,
    }


_SIGNAL_FIELDS = ("reference_no", "project_name", "deadline", "deadline_time", "business_stage", "url")


def _signal_findings(conn, now: datetime, lookback_hours: int) -> tuple[list[dict[str, object]], dict[str, object]]:  # type: ignore[no-untyped-def]
    cutoff = _iso(now - timedelta(hours=lookback_hours))
    rows = conn.execute(
        "SELECT signal_id,source_id,canonical_key,signal_type,created_at,payload_json FROM signals WHERE created_at>=? ORDER BY created_at DESC",
        (cutoff,),
    ).fetchall()
    findings: list[dict[str, object]] = []
    checked = 0
    for row in rows:
        checked += 1
        canonical = conn.execute("SELECT * FROM canonical_items WHERE canonical_key=?", (row["canonical_key"],)).fetchone()
        if canonical is None:
            findings.append({"type": "SIGNAL_EVIDENCE_SUSPECT", "severity": "RED", "source_id": row["source_id"], "code": "SIGNAL_CANONICAL_MISSING", "signal_id": row["signal_id"], "canonical_key": row["canonical_key"]})
            continue
        if str(canonical["source_id"]) != str(row["source_id"]):
            findings.append({"type": "SIGNAL_EVIDENCE_SUSPECT", "severity": "RED", "source_id": row["source_id"], "code": "SIGNAL_SOURCE_MISMATCH", "signal_id": row["signal_id"], "canonical_key": row["canonical_key"]})
        try:
            signal_payload = json.loads(row["payload_json"])
            canonical_payload = json.loads(canonical["payload_json"])
        except json.JSONDecodeError:
            findings.append({"type": "SIGNAL_EVIDENCE_SUSPECT", "severity": "RED", "source_id": row["source_id"], "code": "SIGNAL_OR_CANONICAL_PAYLOAD_INVALID_JSON", "signal_id": row["signal_id"], "canonical_key": row["canonical_key"]})
            continue
        if not isinstance(signal_payload, dict) or not isinstance(canonical_payload, dict):
            continue
        if signal_payload.get("canonical_key") not in {None, row["canonical_key"]} or signal_payload.get("signal_type") not in {None, row["signal_type"]}:
            findings.append({"type": "SIGNAL_EVIDENCE_SUSPECT", "severity": "RED", "source_id": row["source_id"], "code": "SIGNAL_PAYLOAD_IDENTITY_MISMATCH", "signal_id": row["signal_id"], "canonical_key": row["canonical_key"]})

        signal_at = _parse_iso(row["created_at"])
        canonical_updated = _parse_iso(canonical["updated_at"])
        # Only compare material fields when the canonical has not been silently enriched after this signal.
        if signal_at is not None and canonical_updated is not None and canonical_updated <= signal_at + timedelta(seconds=2):
            mismatches = [field for field in _SIGNAL_FIELDS if field in signal_payload and signal_payload.get(field) != canonical_payload.get(field)]
            if mismatches:
                findings.append(
                    {
                        "type": "SIGNAL_EVIDENCE_SUSPECT",
                        "severity": "YELLOW",
                        "source_id": row["source_id"],
                        "code": "LATEST_SIGNAL_MATERIAL_MISMATCH",
                        "signal_id": row["signal_id"],
                        "canonical_key": row["canonical_key"],
                        "fields": mismatches,
                    }
                )
    return findings, {"lookback_hours": lookback_hours, "signals_checked": checked, "suspects": len(findings)}


def _delivery_findings(conn) -> tuple[list[dict[str, object]], dict[str, object]]:  # type: ignore[no-untyped-def]
    findings: list[dict[str, object]] = []
    rows = conn.execute(
        "SELECT delivery_key,canonical_key,signal_id,attention_action FROM delivery_receipts ORDER BY sent_at DESC"
    ).fetchall()
    for row in rows:
        canonical = conn.execute("SELECT 1 FROM canonical_items WHERE canonical_key=?", (row["canonical_key"],)).fetchone()
        signal = conn.execute("SELECT canonical_key FROM signals WHERE signal_id=?", (row["signal_id"],)).fetchone()
        if canonical is None or signal is None or str(signal["canonical_key"]) != str(row["canonical_key"]):
            findings.append(
                {
                    "type": "DELIVERY_ANOMALY",
                    "severity": "RED",
                    "code": "DELIVERY_RECEIPT_ORPHAN_OR_MISMATCH",
                    "delivery_key": row["delivery_key"],
                    "canonical_key": row["canonical_key"],
                    "signal_id": row["signal_id"],
                    "attention_action": row["attention_action"],
                }
            )
    return findings, {"receipts_checked": len(rows), "anomalies": len(findings), "provider_side_duplicates_observable": False}


def audit(
    *,
    database: Path | None = None,
    registry: Registry | None = None,
    now: datetime | None = None,
    network: bool = True,
    fetcher: Fetcher = fetch_bytes,
    mytel_fetcher: Fetcher = fetch_bytes_cloudrity_d1n,
    signal_lookback_hours: int = DEFAULT_SIGNAL_LOOKBACK_HOURS,
    mpt_lookback_days: int = DEFAULT_MPT_LOOKBACK_DAYS,
    mpt_page_limit: int = DEFAULT_MPT_PAGE_LIMIT,
) -> dict[str, object]:
    target = database or db_path()
    registry = registry or Registry.load()
    now = (now or datetime.now(UTC)).astimezone(UTC)
    findings: list[dict[str, object]] = []
    checks: dict[str, object] = {}

    with _read_connection(target) as conn:
        health_findings, health_summary = _health_findings(conn, registry, now)
        findings.extend(health_findings)
        checks["source_health"] = health_summary

        if network:
            coverage_findings, coverage_summary = _coverage_findings(
                conn,
                registry,
                now,
                fetcher=fetcher,
                mytel_fetcher=mytel_fetcher,
                mpt_lookback_days=mpt_lookback_days,
                mpt_page_limit=mpt_page_limit,
            )
            findings.extend(coverage_findings)
            checks["strategic_coverage"] = coverage_summary
            atom_findings, atom_summary = _atom_surface_findings(fetcher)
            findings.extend(atom_findings)
            checks["atom_surface_trigger"] = atom_summary
        else:
            checks["strategic_coverage"] = {"status": "SKIPPED", "reason": "NETWORK_DISABLED"}
            checks["atom_surface_trigger"] = {"status": "SKIPPED", "reason": "NETWORK_DISABLED"}

        deadline_findings, deadline_summary = _deadline_findings(conn)
        findings.extend(deadline_findings)
        checks["deadline_integrity"] = deadline_summary

        signal_findings, signal_summary = _signal_findings(conn, now, signal_lookback_hours)
        findings.extend(signal_findings)
        checks["signal_integrity"] = signal_summary

        delivery_findings, delivery_summary = _delivery_findings(conn)
        findings.extend(delivery_findings)
        checks["delivery_integrity"] = delivery_summary

    finding_types = (
        "HEALTH_ALERT",
        "COVERAGE_GAP",
        "SURFACE_TRIGGER",
        "DEADLINE_EVIDENCE_SUSPECT",
        "SIGNAL_EVIDENCE_SUSPECT",
        "DELIVERY_ANOMALY",
    )
    counts = {name: sum(1 for item in findings if item.get("type") == name) for name in finding_types}
    red = sum(1 for item in findings if item.get("severity") == "RED")
    yellow = sum(1 for item in findings if item.get("severity") == "YELLOW")
    return {
        "status": "ALERT" if red else ("DEGRADED" if yellow else "PASS"),
        "auditor_version": AUDITOR_VERSION,
        "as_of": _iso(now),
        "network_checks": network,
        "finding_count": len(findings),
        "severity_counts": {"RED": red, "YELLOW": yellow},
        "finding_type_counts": counts,
        "findings": findings,
        "checks": checks,
        "assurance": {
            "internal_integrity": "CHECKED",
            "external_completeness": "NOT_PROVEN",
            "failure_classes": {
                "missed_high_value_tender": "NOT_PROVEN_GLOBALLY",
                "wrong_deadline_accepted": "EVIDENCE_ANOMALIES_CHECKED_NOT_INDEPENDENTLY_VALIDATED",
                "false_signal_emitted": "RECENT_INTERNAL_TRACE_CHECKED_HISTORY_INCOMPLETE",
                "duplicated_push": "RECEIPT_INTEGRITY_CHECKED_PROVIDER_SIDE_NOT_OBSERVABLE",
                "persistent_non_green_source": "CHECKED",
                "missed_new_mpt_or_mytel_procurement": "BOUNDED_INDEPENDENT_RECONCILIATION",
                "new_atom_public_procurement_surface": "OFFICIAL_SITEMAP_TRIGGER_CHECKED" if network else "NOT_CHECKED",
            },
        },
        "contract": {
            "read_only": True,
            "does_not_mutate_canonical_or_signals": True,
            "does_not_emit_customer_signals": True,
            "does_not_send_telegram": True,
            "coverage_parser_independent_from_production_parser": True,
            "external_completeness_proven": False,
            "coverage_scope": "bounded recent MPT pages, bounded MYTEL feed, and ATOM sitemap trigger only",
            "false_signal_proof_complete": False,
            "false_signal_limit": "canonical version history is required to prove parser-only historical UPDATED automatically",
        },
    }
