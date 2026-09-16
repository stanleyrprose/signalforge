from __future__ import annotations

import hashlib
import html as html_lib
import json
import random
import re
import uuid
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from .acquisition_runtime import acquire_provider_diagnostic_bytes
from .auditor import audit
from .config import Registry, db_path, evidence_root
from .coverage_gaps import reviewed_coverage_gaps, verified_external_opportunities
from .db import connect, migrate
from .http import fetch_bytes
from .national_portal import parse_current_high_value_tender_leads
from .source_scorecard import PORTFOLIO_TIERS, _is_known_historical_noise, source_scorecard

ASSURANCE_VERSION = 1
METRIC_REVIEW_VERSION = 1
MANDATORY_COVERAGE_SOURCES = ("S13", "S20", "S21", "S30", "S38", "S39", "S41")
CORE_SOURCES = tuple(sorted(source_id for source_id, tier in PORTFOLIO_TIERS.items() if tier == "CORE"))
COVERAGE_STATUSES = {"PASS", "GAP", "PARTIAL", "UNPROVEN", "CHECK_FAILED"}
MISS_STATUSES = {"OPEN", "RESOLVED", "FALSE_POSITIVE"}
MISS_SEVERITIES = {"RED", "YELLOW"}
NOISE_REVIEW_STATUSES = {"PENDING", "CONFIRMED_NOISE", "FALSE_NEGATIVE", "INCONCLUSIVE"}
PROMOTION_STATUSES = {"ACTIVE", "RESOLVED"}
PROMOTION_PRIORITIES = {"HIGH", "REVIEW"}
_LOCAL_TZ = ZoneInfo("Asia/Yangon")


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _normalize_url(value: str) -> str:
    parsed = urlparse(value.strip())
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    # Percent-escape hex is case-insensitive; canonicalize it so WordPress URLs
    # emitted with %e1... and stored as %E1... compare as the same identity.
    path = re.sub(r"%[0-9A-Fa-f]{2}", lambda match: match.group(0).upper(), path)
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


def _dedupe_key(*parts: object) -> str:
    material = "|".join(str(part or "") for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class _LinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        if tag.lower() != "a":
            return
        href = next((str(value) for key, value in attrs if key == "href" and value), None)
        if href:
            self._href = urljoin(self.base_url, html_lib.unescape(href))
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            value = " ".join(data.split())
            if value:
                self._text.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


def _all_links(payload: bytes, base_url: str) -> list[tuple[str, str]]:
    parser = _LinkParser(base_url)
    parser.feed(payload.decode("utf-8", errors="replace"))
    dedup: dict[str, str] = {}
    for url, text in parser.links:
        normalized = _normalize_url(url)
        previous = dedup.get(normalized, "")
        if normalized not in dedup or len(text.strip()) > len(previous.strip()):
            dedup[normalized] = text
    return [(url, dedup[url]) for url in sorted(dedup)]


def _is_tender_result_notice(text: str) -> bool:
    lowered = " ".join(text.lower().split())
    markers = (
        "တင်ဒါအောင်မြင်ကြောင်း",
        "တင်ဒါအောင်စာရင်း",
        "tender award",
        "award notice",
        "successful bidder",
        "tender result",
        "bid result",
    )
    return any(marker in lowered for marker in markers)


def _source_candidates(source_id: str, payload: bytes, base_url: str) -> list[dict[str, str]]:
    text_payload = payload.decode("utf-8", errors="replace")
    if source_id == "S20":
        # MOEP publishes relative `ignite/contentView/<id>` links that are
        # malformed under ordinary urljoin from the page URL. Extract only the
        # allowlisted business-detail identity and its nearby official post date,
        # independent of the production parser.
        rows: list[dict[str, str]] = []
        seen: set[str] = set()
        for match in re.finditer(r"(?:/mm/)?ignite/contentView/(\d+)", text_payload):
            record_id = match.group(1)
            if record_id in seen:
                continue
            seen.add(record_id)
            nearby = text_payload[match.end() : match.end() + 1800]
            date_match = re.search(r"(\d{1,2}-[A-Za-z]{3}-\d{4})", nearby)
            publication_date = ""
            if date_match:
                try:
                    publication_date = datetime.strptime(date_match.group(1), "%d-%b-%Y").date().isoformat()
                except ValueError:
                    publication_date = ""
            rows.append({"url": f"https://moep.gov.mm/mm/ignite/contentView/{record_id}", "title": "", "publication_date": publication_date})
        return rows
    links = _all_links(payload, base_url)
    candidates: list[dict[str, str]] = []
    tender_terms = ("tender", "procurement", "rfp", "rfq", "အိတ်ဖွင့်တင်ဒါ", "တင်ဒါ")
    for url, text in links:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.rstrip("/") or "/"
        match = False
        if source_id == "S20":
            match = host in {"moep.gov.mm", "www.moep.gov.mm"} and re.fullmatch(r"/mm/ignite/contentView/\d+", path) is not None
        elif source_id == "S21":
            match = (
                host in {"railways.gov.mm", "www.railways.gov.mm"}
                and path not in {"/", "/tenders", "/category/tender"}
                and not path.startswith(("/category/", "/tag/", "/author/", "/wp-", "/page/"))
                and any(term in text.lower() if term.isascii() else term in text for term in tender_terms)
            )
        elif source_id == "S30":
            match = (
                host in {"mofa.gov.mm", "www.mofa.gov.mm"}
                and path not in {"/", "/category/announcement"}
                and not path.startswith(("/category/", "/tag/", "/author/", "/wp-", "/page/"))
                and any(term in text.lower() if term.isascii() else term in text for term in tender_terms)
                and not _is_tender_result_notice(text)
            )
        elif source_id == "S38":
            match = (
                host in {"industrymsme.gov.mm", "www.industrymsme.gov.mm"}
                and re.fullmatch(r"/announcements/\d+", path) is not None
                and any(term in text.lower() if term.isascii() else term in text for term in tender_terms)
            )
        elif source_id == "S39":
            match = host in {"energy.gov.mm", "www.energy.gov.mm"} and re.fullmatch(r"/tenders/\d+", path) is not None
        if match:
            candidates.append({"url": url, "title": text[:300]})
    unique: dict[str, dict[str, str]] = {}
    for item in candidates:
        unique.setdefault(_normalize_url(item["url"]), item)
    return [unique[key] for key in sorted(unique)]


def _nonstandard_candidates(source_id: str, payload: bytes, base_url: str) -> list[dict[str, str]]:
    if source_id not in {"S30", "S38"}:
        return []
    standard = {_normalize_url(item["url"]) for item in _source_candidates(source_id, payload, base_url)}
    rows: list[dict[str, str]] = []
    for url, text in _all_links(payload, base_url):
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.rstrip("/") or "/"
        normalized = _normalize_url(url)
        if normalized in standard or not text.strip():
            continue
        if source_id == "S38":
            match = (
                host in {"industrymsme.gov.mm", "www.industrymsme.gov.mm"}
                and re.fullmatch(r"/announcements/\d+", path) is not None
            )
        else:
            match = (
                host in {"mofa.gov.mm", "www.mofa.gov.mm"}
                and path not in {"/", "/category/announcement"}
                and not path.startswith(("/category/", "/tag/", "/author/", "/wp-", "/page/"))
                and _is_tender_result_notice(text)
            )
        if match:
            rows.append({"url": url, "title": text[:300]})
    return rows


def _canonical_urls(conn, source_id: str) -> set[str]:  # type: ignore[no-untyped-def]
    return {
        _normalize_url(str(row[0]))
        for row in conn.execute("SELECT url FROM canonical_items WHERE source_id=? AND url IS NOT NULL", (source_id,))
        if row[0]
    }


def record_missed_signal(
    *,
    source_id: str,
    title: str,
    reason: str,
    severity: str = "RED",
    detected_by: str = "MANUAL",
    url: str | None = None,
    canonical_key: str | None = None,
    metadata: dict[str, object] | None = None,
    database: Path | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    severity = severity.upper()
    if severity not in MISS_SEVERITIES:
        raise ValueError("severity must be RED or YELLOW")
    target = database or db_path()
    migrate(target)
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    identity = url or canonical_key or title
    dedupe = _dedupe_key(source_id, detected_by, identity)
    miss_id = str(uuid.uuid4())
    with connect(target) as conn, conn:
        existing = conn.execute("SELECT * FROM missed_signals WHERE dedupe_key=?", (dedupe,)).fetchone()
        if existing is not None:
            if str(existing["status"]) == "RESOLVED":
                conn.execute(
                    """
                    UPDATE missed_signals SET status='OPEN',detected_at=?,title=?,url=?,reason=?,severity=?,
                        canonical_key=?,resolution_note=NULL,resolved_at=NULL,resolved_by=NULL,metadata_json=?
                    WHERE miss_id=?
                    """,
                    (_iso(observed), title, url, reason, severity, canonical_key, _json(metadata or {}), existing["miss_id"]),
                )
                row = conn.execute("SELECT * FROM missed_signals WHERE miss_id=?", (existing["miss_id"],)).fetchone()
                return {**dict(row), "deduplicated": True, "reopened": True}
            return {**dict(existing), "deduplicated": True, "reopened": False}
        conn.execute(
            """
            INSERT INTO missed_signals(
                miss_id,dedupe_key,source_id,detected_at,detected_by,title,url,reason,severity,status,canonical_key,metadata_json
            ) VALUES (?,?,?,?,?,?,?,?,?,'OPEN',?,?)
            """,
            (miss_id, dedupe, source_id, _iso(observed), detected_by, title, url, reason, severity, canonical_key, _json(metadata or {})),
        )
        row = conn.execute("SELECT * FROM missed_signals WHERE miss_id=?", (miss_id,)).fetchone()
    return {**dict(row), "deduplicated": False, "reopened": False}


def list_missed_signals(*, database: Path | None = None, status: str | None = "OPEN", limit: int = 100) -> dict[str, object]:
    target = database or db_path()
    migrate(target)
    if status is not None and status not in MISS_STATUSES:
        raise ValueError("invalid miss status")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be 1..1000")
    with connect(target) as conn:
        if status is None:
            rows = conn.execute("SELECT * FROM missed_signals ORDER BY detected_at DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM missed_signals WHERE status=? ORDER BY detected_at DESC LIMIT ?", (status, limit)).fetchall()
    return {"status": "PASS", "count": len(rows), "misses": [dict(row) for row in rows]}


def resolve_missed_signal(
    miss_id: str,
    *,
    outcome: str = "RESOLVED",
    note: str,
    resolved_by: str = "operator",
    database: Path | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    if outcome not in {"RESOLVED", "FALSE_POSITIVE"}:
        raise ValueError("outcome must be RESOLVED or FALSE_POSITIVE")
    target = database or db_path()
    migrate(target)
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    with connect(target) as conn, conn:
        row = conn.execute("SELECT * FROM missed_signals WHERE miss_id=?", (miss_id,)).fetchone()
        if row is None:
            raise ValueError("miss not found")
        conn.execute(
            "UPDATE missed_signals SET status=?,resolution_note=?,resolved_at=?,resolved_by=? WHERE miss_id=?",
            (outcome, note, _iso(observed), resolved_by, miss_id),
        )
        updated = conn.execute("SELECT * FROM missed_signals WHERE miss_id=?", (miss_id,)).fetchone()
    return {"status": "PASS", "miss": dict(updated)}


def record_manual_promotion(
    *,
    source_id: str,
    title: str,
    summary: str,
    reason: str,
    priority_band: str = "HIGH",
    url: str | None = None,
    deadline: str | None = None,
    location: str | None = None,
    created_by: str = "operator",
    database: Path | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    priority_band = priority_band.upper()
    if priority_band not in PROMOTION_PRIORITIES:
        raise ValueError("priority_band must be HIGH or REVIEW")
    if not title.strip() or not summary.strip() or not reason.strip():
        raise ValueError("title, summary and reason are required")
    target = database or db_path()
    migrate(target)
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    promotion_id = str(uuid.uuid4())
    with connect(target) as conn, conn:
        conn.execute(
            """
            INSERT INTO manual_promotions(
                promotion_id,source_id,created_at,created_by,title,summary,url,reason,priority_band,deadline,location,status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,'ACTIVE')
            """,
            (promotion_id, source_id, _iso(observed), created_by, title.strip(), summary.strip(), url, reason.strip(), priority_band, deadline, location),
        )
        row = conn.execute("SELECT * FROM manual_promotions WHERE promotion_id=?", (promotion_id,)).fetchone()
    return {"status": "PASS", "promotion": dict(row)}


def list_manual_promotions(*, database: Path | None = None, status: str = "ACTIVE", limit: int = 100) -> dict[str, object]:
    if status not in PROMOTION_STATUSES:
        raise ValueError("invalid promotion status")
    target = database or db_path()
    migrate(target)
    with connect(target) as conn:
        rows = conn.execute("SELECT * FROM manual_promotions WHERE status=? ORDER BY created_at DESC LIMIT ?", (status, limit)).fetchall()
    return {"status": "PASS", "count": len(rows), "promotions": [dict(row) for row in rows]}


def resolve_manual_promotion(
    promotion_id: str,
    *,
    note: str,
    resolved_by: str = "operator",
    database: Path | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    target = database or db_path()
    migrate(target)
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    with connect(target) as conn, conn:
        row = conn.execute("SELECT 1 FROM manual_promotions WHERE promotion_id=?", (promotion_id,)).fetchone()
        if row is None:
            raise ValueError("promotion not found")
        conn.execute(
            "UPDATE manual_promotions SET status='RESOLVED',resolved_at=?,resolved_by=?,resolution_note=? WHERE promotion_id=?",
            (_iso(observed), resolved_by, note, promotion_id),
        )
        updated = conn.execute("SELECT * FROM manual_promotions WHERE promotion_id=?", (promotion_id,)).fetchone()
    return {"status": "PASS", "promotion": dict(updated)}


def _coverage_from_existing_audit(audit_result: dict[str, object], source_id: str) -> dict[str, object]:
    checks = audit_result.get("checks") or {}
    strategic = checks.get("strategic_coverage") if isinstance(checks, dict) else {}
    summary = strategic.get(source_id) if isinstance(strategic, dict) else None
    if not isinstance(summary, dict):
        return {"source_id": source_id, "method": "existing-independent-auditor", "status": "UNPROVEN", "official": 0, "covered": 0, "missing": [], "details": {"reason": "NO_AUDIT_RESULT"}}
    raw_status = str(summary.get("status") or "CHECK_FAILED")
    if source_id == "S41":
        official = int(summary.get("official_keys") or 0)
        covered = int(summary.get("canonical_keys") or 0)
        missing = [str(value) for value in (summary.get("missing") or [])]
    else:
        official = int(summary.get("tender_like_pages") or 0)
        missing_count = int(summary.get("missing") or 0)
        covered = max(0, official - missing_count)
        missing = [
            str(item.get("url") or item.get("canonical_key") or "")
            for item in (audit_result.get("findings") or [])
            if isinstance(item, dict) and item.get("source_id") == source_id and item.get("type") == "COVERAGE_GAP"
        ]
    status = "PASS" if raw_status == "PASS" else "GAP" if raw_status == "GAP" else "CHECK_FAILED"
    return {"source_id": source_id, "method": "existing-independent-auditor", "status": status, "official": official, "covered": covered, "missing": missing, "details": summary}


def _coverage_from_listing(
    conn,  # type: ignore[no-untyped-def]
    *,
    database: Path,
    assurance_run_id: str,
    source_id: str,
    policy: dict[str, object],
    network: bool,
    now: datetime,
) -> dict[str, object]:
    discovery_url = str(policy.get("discovery_url") or "")
    if not discovery_url:
        return {"source_id": source_id, "method": "independent-listing-links", "status": "UNPROVEN", "official": 0, "covered": 0, "missing": [], "details": {"reason": "DISCOVERY_URL_MISSING"}}
    payload: bytes | None = None
    method = "independent-listing-links"
    details: dict[str, object] = {}
    if source_id == "S38":
        method = "independent-provider-raw-fetch-links"
        if not network:
            return {"source_id": source_id, "method": method, "status": "UNPROVEN", "official": 0, "covered": 0, "missing": [], "details": {"reason": "NETWORK_DISABLED"}}
        provider_roles = policy.get("provider_target_roles") or {}
        if not isinstance(provider_roles, dict) or not provider_roles.get("DISCOVERY"):
            return {"source_id": source_id, "method": method, "status": "UNPROVEN", "official": 0, "covered": 0, "missing": [], "details": {"reason": "PROVIDER_DISCOVERY_ROLE_MISSING"}}
        try:
            capture = acquire_provider_diagnostic_bytes(
                database=database,
                assurance_run_id=assurance_run_id,
                source_id=source_id,
                source_policy_version=int(policy.get("source_policy_version") or 1),
                target_role=str(provider_roles["DISCOVERY"]),
                url=discovery_url,
                timeout_seconds=int(policy.get("request_timeout_seconds") or 90),
                max_bytes=int(policy.get("request_max_bytes") or 1_000_000),
                expected_content_types=["text/html"],
                capability=str(policy.get("provider_capability") or "C0_FETCH"),
                request_now=now,
            )
            payload = capture.payload
            details = {
                "provider_request_id": capture.provider_request_id,
                "artifact_sha256": capture.sha256,
                "provider_id": policy.get("provider_id"),
                "final_url": capture.final_url,
                "http_status": capture.http_status,
            }
        except Exception as exc:
            return {"source_id": source_id, "method": method, "status": "CHECK_FAILED", "official": 0, "covered": 0, "missing": [], "details": {"error": f"{type(exc).__name__}: {exc}"}}
    elif not network:
        return {"source_id": source_id, "method": method, "status": "UNPROVEN", "official": 0, "covered": 0, "missing": [], "details": {"reason": "NETWORK_DISABLED"}}
    else:
        try:
            payload = fetch_bytes(
                discovery_url,
                timeout=int(policy.get("request_timeout_seconds") or 30),
                max_bytes=int(policy.get("request_max_bytes") or 2_000_000),
            )
        except Exception as exc:
            return {"source_id": source_id, "method": method, "status": "CHECK_FAILED", "official": 0, "covered": 0, "missing": [], "details": {"error": f"{type(exc).__name__}: {exc}"}}
    assert payload is not None
    candidates = _source_candidates(source_id, payload, discovery_url)
    nonstandard_candidates = _nonstandard_candidates(source_id, payload, discovery_url)
    if nonstandard_candidates:
        details = {
            **details,
            "nonstandard_candidate_count": len(nonstandard_candidates),
            "nonstandard_candidates": nonstandard_candidates[:100],
        }
    if source_id == "S20":
        cutoff_date = (now - timedelta(days=45)).date().isoformat()
        dated = [item for item in candidates if item.get("publication_date")]
        if dated:
            candidates = [item for item in dated if str(item.get("publication_date")) >= cutoff_date]
            details = {**details, "commercial_window_days": 45, "commercial_window_start": cutoff_date}
        else:
            return {
                "source_id": source_id,
                "method": method,
                "status": "PARTIAL",
                "official": 0,
                "covered": 0,
                "missing": [],
                "details": {**details, "reason": "OFFICIAL_POST_DATES_NOT_EXTRACTABLE", "candidate_count_unbounded": len(candidates)},
            }
    official_urls = {_normalize_url(item["url"]) for item in candidates}
    canonical_urls = _canonical_urls(conn, source_id)
    missing_urls = sorted(official_urls - canonical_urls)
    covered = len(official_urls & canonical_urls)
    if not candidates:
        status = "UNPROVEN"
        details = {**details, "reason": "NO_INDEPENDENT_CANDIDATES", "candidate_rule": source_id}
    else:
        status = "GAP" if missing_urls else "PASS"
        details = {**details, "candidates": candidates[:100], "candidate_rule": source_id}
    return {"source_id": source_id, "method": method, "status": status, "official": len(official_urls), "covered": covered, "missing": missing_urls, "details": details}


def _coverage_from_aggregator_surface(
    conn,  # type: ignore[no-untyped-def]
    *,
    source_id: str,
    policy: dict[str, object],
    network: bool,
    now: datetime,
) -> dict[str, object]:
    method = "official-aggregator-discovery-lead-resolution"
    if policy.get("enabled") is not True:
        return {
            "source_id": source_id,
            "method": method,
            "status": "UNPROVEN",
            "official": 0,
            "covered": 0,
            "missing": [],
            "details": {"reason": "ASSURANCE_SURFACE_DISABLED"},
        }
    discovery_url = str(policy.get("discovery_url") or "")
    if not discovery_url:
        return {
            "source_id": source_id,
            "method": method,
            "status": "UNPROVEN",
            "official": 0,
            "covered": 0,
            "missing": [],
            "details": {"reason": "DISCOVERY_URL_MISSING"},
        }
    if not network:
        return {
            "source_id": source_id,
            "method": method,
            "status": "UNPROVEN",
            "official": 0,
            "covered": 0,
            "missing": [],
            "details": {"reason": "NETWORK_DISABLED", "canonical_truth": False},
        }
    try:
        payload = fetch_bytes(
            discovery_url,
            timeout=int(policy.get("request_timeout_seconds") or 30),
            max_bytes=int(policy.get("request_max_bytes") or 500_000),
        )
        leads = parse_current_high_value_tender_leads(
            payload,
            base_url=discovery_url,
            today=now.astimezone(_LOCAL_TZ).date(),
        )
    except Exception as exc:
        return {
            "source_id": source_id,
            "method": method,
            "status": "CHECK_FAILED",
            "official": 0,
            "covered": 0,
            "missing": [],
            "details": {"error": f"{type(exc).__name__}: {exc}", "canonical_truth": False},
        }

    canonical_urls = {
        _normalize_url(str(row[0]))
        for row in conn.execute("SELECT url FROM canonical_items WHERE url IS NOT NULL")
        if row[0]
    }
    reviewed = {
        _normalize_url(str(gap["url"])): gap
        for gap in reviewed_coverage_gaps(now=now)
        if str(gap.get("evidence_basis") or "").startswith("REVIEWED_NATIONAL_PORTAL_HOSTED_")
    }
    verified_external = {
        _normalize_url(str(item["url"])): item
        for item in verified_external_opportunities(now=now)
        if str(item.get("coverage_origin") or "") == source_id
    }
    covered_leads: list[dict[str, object]] = []
    verified_external_leads: list[dict[str, object]] = []
    confirmed_gaps: list[dict[str, object]] = []
    unresolved_leads: list[dict[str, object]] = []
    for lead in leads:
        normalized = _normalize_url(str(lead["url"]))
        if normalized in canonical_urls:
            covered_leads.append({**lead, "coverage_resolution": "CANONICAL"})
            continue
        verified = verified_external.get(normalized)
        if verified is not None:
            resolved = {
                **lead,
                "coverage_resolution": "VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY",
                "verified_external": verified,
            }
            covered_leads.append(resolved)
            verified_external_leads.append(resolved)
            continue
        reviewed_gap = reviewed.get(normalized)
        if reviewed_gap is not None:
            confirmed_gaps.append({**lead, "reviewed_gap": reviewed_gap})
            continue
        unresolved_leads.append(lead)

    if confirmed_gaps:
        status = "GAP"
    elif unresolved_leads:
        status = "PARTIAL"
    elif leads:
        status = "PASS"
    else:
        status = "UNPROVEN"
    return {
        "source_id": source_id,
        "method": method,
        "status": status,
        "official": len(leads),
        "covered": len(covered_leads),
        "missing": [str(item["url"]) for item in confirmed_gaps],
        "details": {
            "contract": "DISCOVERY_AGGREGATOR_ONLY",
            "canonical_truth": False,
            "closing_date_semantics": "HINT_ONLY_NOT_CANONICAL",
            "current_page_only": bool(policy.get("current_page_only", True)),
            "candidate_count": len(leads),
            "covered_leads": covered_leads[:50],
            "verified_external_leads": verified_external_leads[:50],
            "confirmed_gaps": confirmed_gaps[:50],
            "unresolved_leads": unresolved_leads[:50],
            "issuer_page_coverage_debt_retained": bool(verified_external_leads),
        },
    }



def _resolve_verified_aggregator_misses(
    conn, *, now: datetime, verified_urls: set[str]
) -> int:  # type: ignore[no-untyped-def]
    verified_urls = {_normalize_url(url) for url in verified_urls if url}
    if not verified_urls:
        return 0
    resolved = 0
    rows = conn.execute(
        "SELECT miss_id,url FROM missed_signals WHERE status='OPEN' AND detected_by='AGGREGATOR_COVERAGE_AUDIT'"
    ).fetchall()
    for row in rows:
        url = str(row["url"] or "")
        if not url or _normalize_url(url) not in verified_urls:
            continue
        conn.execute(
            """
            UPDATE missed_signals
            SET status='RESOLVED',resolution_note=?,resolved_at=?,resolved_by=?
            WHERE miss_id=?
            """,
            (
                "Business coverage restored by reviewed official issuer document on alternate official surface; issuer-page coverage debt remains diagnostic",
                _iso(now),
                "ASSURANCE_VERIFIED_EXTERNAL",
                row["miss_id"],
            ),
        )
        resolved += 1
    return resolved

def _resolve_expired_aggregator_misses(conn, *, now: datetime) -> int:  # type: ignore[no-untyped-def]
    today = now.astimezone(_LOCAL_TZ).date().isoformat()
    resolved = 0
    rows = conn.execute(
        "SELECT miss_id,metadata_json FROM missed_signals WHERE status='OPEN' AND detected_by='AGGREGATOR_COVERAGE_AUDIT'"
    ).fetchall()
    for row in rows:
        try:
            metadata = json.loads(str(row["metadata_json"] or "{}"))
        except json.JSONDecodeError:
            continue
        deadline = str(metadata.get("deadline") or "")
        if not deadline or deadline >= today:
            continue
        conn.execute(
            """
            UPDATE missed_signals
            SET status='RESOLVED',resolution_note=?,resolved_at=?,resolved_by=?
            WHERE miss_id=?
            """,
            ("Aggregator-discovered opportunity window expired; retained in miss history", _iso(now), "ASSURANCE_AUTO_EXPIRY", row["miss_id"]),
        )
        resolved += 1
    return resolved


def _retained_evidence_path(source_id: str, artifact_sha256: str, media_type: str) -> Path | None:
    if not artifact_sha256:
        return None
    suffix = ".pdf" if "pdf" in media_type.lower() else ".html"
    path = evidence_root() / source_id / f"{artifact_sha256}{suffix}"
    return path if path.is_file() else None


def _zero_item_replayability(conn, *, cutoff: str) -> dict[str, int]:  # type: ignore[no-untyped-def]
    rows = conn.execute(
        """
        SELECT p.source_id,e.artifact_sha256,e.artifact_media_type
        FROM processing_records p
        JOIN evidence_envelopes e ON e.evidence_id=p.evidence_id
        WHERE p.status='SUCCESS' AND p.items_found=0 AND p.finished_at>=?
        """,
        (cutoff,),
    ).fetchall()
    replayable = sum(
        1
        for row in rows
        if _retained_evidence_path(
            str(row["source_id"]),
            str(row["artifact_sha256"] or ""),
            str(row["artifact_media_type"] or ""),
        )
        is not None
    )
    return {"total": len(rows), "replayable": replayable, "unreplayable": len(rows) - replayable}


def _noise_candidates(conn) -> list[dict[str, object]]:  # type: ignore[no-untyped-def]
    candidates: list[dict[str, object]] = []
    for row in conn.execute("SELECT signal_id,source_id,canonical_key,signal_type,created_at,payload_json FROM signals"):
        if _is_known_historical_noise(row):
            candidates.append(
                {
                    "source_id": str(row["source_id"]),
                    "candidate_kind": "KNOWN_HISTORICAL_SIGNAL_NOISE",
                    "candidate_ref": f"signal:{row['signal_id']}",
                    "evidence_url": None,
                    "sample_basis": "AUDITED_SIGNAL_NOISE_ACCOUNTING_EXCLUSION",
                    "payload": {"signal_id": row["signal_id"], "canonical_key": row["canonical_key"], "signal_type": row["signal_type"], "created_at": row["created_at"]},
                }
            )
    zero_rows = conn.execute(
        """
        SELECT p.processing_id,p.source_id,p.parser_version,p.finished_at,e.requested_url,e.final_url,e.artifact_sha256,e.artifact_media_type
        FROM processing_records p
        JOIN evidence_envelopes e ON e.evidence_id=p.evidence_id
        WHERE p.status='SUCCESS' AND p.items_found=0
        ORDER BY p.finished_at DESC
        """
    ).fetchall()
    for row in zero_rows:
        retained_path = _retained_evidence_path(
            str(row["source_id"]),
            str(row["artifact_sha256"] or ""),
            str(row["artifact_media_type"] or ""),
        )
        if retained_path is None:
            continue
        candidates.append(
            {
                "source_id": str(row["source_id"]),
                "candidate_kind": "ZERO_ITEM_PROCESSING",
                "candidate_ref": f"processing:{row['processing_id']}",
                "evidence_url": str(row["final_url"] or row["requested_url"] or "") or None,
                "sample_basis": "SUCCESSFUL_PROCESSING_FILTERED_TO_ZERO_ITEMS_WITH_RETAINED_EVIDENCE",
                "payload": {
                    "processing_id": row["processing_id"],
                    "parser_version": row["parser_version"],
                    "finished_at": row["finished_at"],
                    "artifact_sha256": row["artifact_sha256"],
                    "artifact_path": str(retained_path),
                },
            }
        )
    seen_nonstandard_sources: set[str] = set()
    for latest_nonstandard in conn.execute(
        "SELECT source_id,details_json FROM coverage_audit_results ORDER BY checked_at DESC"
    ):
        source_id = str(latest_nonstandard["source_id"])
        if source_id in seen_nonstandard_sources:
            continue
        seen_nonstandard_sources.add(source_id)
        try:
            details = json.loads(str(latest_nonstandard["details_json"] or "{}"))
        except json.JSONDecodeError:
            details = {}
        rows = details.get("nonstandard_candidates") if isinstance(details, dict) else None
        if isinstance(rows, list):
            for item in rows:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url") or "")
                title = str(item.get("title") or "")
                if not url:
                    continue
                candidates.append(
                    {
                        "source_id": source_id,
                        "candidate_kind": "INDEPENDENT_LISTING_NONSTANDARD",
                        "candidate_ref": f"url:{_normalize_url(url)}",
                        "evidence_url": url,
                        "sample_basis": "OFFICIAL_LISTING_NOT_STANDARD_TENDER_CANDIDATE",
                        "payload": {"title": title, "url": url},
                    }
                )
    return candidates


def _sample_noise(conn, *, assurance_run_id: str, now: datetime, sample_size: int) -> list[dict[str, object]]:  # type: ignore[no-untyped-def]
    if sample_size < 0 or sample_size > 50:
        raise ValueError("noise_sample_size must be 0..50")
    if sample_size == 0:
        return []
    existing = {
        (str(row["source_id"]), str(row["candidate_kind"]), str(row["candidate_ref"]))
        for row in conn.execute("SELECT source_id,candidate_kind,candidate_ref FROM noise_review_samples")
    }
    pool = [item for item in _noise_candidates(conn) if (str(item["source_id"]), str(item["candidate_kind"]), str(item["candidate_ref"])) not in existing]
    seed = int(hashlib.sha256(f"{now.date().isoformat()}|noise-sampling-v1".encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    rng.shuffle(pool)
    selected = pool[:sample_size]
    sampled_at = _iso(now)
    output: list[dict[str, object]] = []
    for item in selected:
        sample_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO noise_review_samples(
                noise_sample_id,assurance_run_id,source_id,candidate_kind,candidate_ref,evidence_url,
                sample_basis,sampled_at,payload_json,review_status
            ) VALUES (?,?,?,?,?,?,?,?,?,'PENDING')
            """,
            (sample_id, assurance_run_id, item["source_id"], item["candidate_kind"], item["candidate_ref"], item["evidence_url"], item["sample_basis"], sampled_at, _json(item["payload"])),
        )
        output.append({"noise_sample_id": sample_id, **item, "review_status": "PENDING"})
    return output


def list_noise_samples(*, database: Path | None = None, status: str | None = None, limit: int = 100) -> dict[str, object]:
    if status is not None and status not in NOISE_REVIEW_STATUSES:
        raise ValueError("invalid noise review status")
    target = database or db_path()
    migrate(target)
    with connect(target) as conn:
        if status is None:
            rows = conn.execute("SELECT * FROM noise_review_samples ORDER BY sampled_at DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM noise_review_samples WHERE review_status=? ORDER BY sampled_at DESC LIMIT ?", (status, limit)).fetchall()
    return {"status": "PASS", "count": len(rows), "samples": [dict(row) for row in rows]}


def review_noise_sample(
    noise_sample_id: str,
    *,
    outcome: str,
    note: str,
    reviewed_by: str = "operator",
    miss_title: str | None = None,
    database: Path | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    outcome = outcome.upper()
    if outcome not in NOISE_REVIEW_STATUSES - {"PENDING"}:
        raise ValueError("outcome must be CONFIRMED_NOISE, FALSE_NEGATIVE or INCONCLUSIVE")
    target = database or db_path()
    migrate(target)
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    with connect(target) as conn, conn:
        row = conn.execute("SELECT * FROM noise_review_samples WHERE noise_sample_id=?", (noise_sample_id,)).fetchone()
        if row is None:
            raise ValueError("noise sample not found")
        conn.execute(
            "UPDATE noise_review_samples SET review_status=?,reviewed_at=?,reviewed_by=?,review_note=? WHERE noise_sample_id=?",
            (outcome, _iso(observed), reviewed_by, note, noise_sample_id),
        )
        sample = dict(conn.execute("SELECT * FROM noise_review_samples WHERE noise_sample_id=?", (noise_sample_id,)).fetchone())
    miss = None
    if outcome == "FALSE_NEGATIVE":
        miss = record_missed_signal(
            source_id=str(sample["source_id"]),
            title=miss_title or f"Noise sample {sample['candidate_ref']} was a false negative",
            reason=f"Noise review found a false negative: {note}",
            severity="RED",
            detected_by="NOISE_REVIEW",
            url=str(sample.get("evidence_url") or "") or None,
            metadata={"noise_sample_id": noise_sample_id, "candidate_ref": sample["candidate_ref"]},
            database=target,
            now=observed,
        )
    return {"status": "PASS", "sample": sample, "miss": miss}


def _metric_review(
    conn,  # type: ignore[no-untyped-def]
    *,
    assurance_run_id: str,
    coverage_rows: list[dict[str, object]],
    now: datetime,
    registry: Registry,
    window_days: int = 30,
) -> dict[str, object]:
    scorecard = source_scorecard(database=Path(conn.execute("PRAGMA database_list").fetchone()[2]), now=now, registry=registry, window_days=window_days)
    summary = scorecard.get("summary") or {}
    source_rows = scorecard.get("sources") or []
    coverage_status = {str(row["source_id"]): str(row["status"]) for row in coverage_rows}
    mandatory_total = len(MANDATORY_COVERAGE_SOURCES)
    mandatory_proven = sum(1 for sid in MANDATORY_COVERAGE_SOURCES if coverage_status.get(sid) == "PASS")
    coverage_distribution = {status: sum(1 for sid in MANDATORY_COVERAGE_SOURCES if coverage_status.get(sid) == status) for status in sorted(COVERAGE_STATUSES)}
    open_miss_rows = conn.execute("SELECT severity,detected_at FROM missed_signals WHERE status='OPEN'").fetchall()
    cutoff = _iso(now - timedelta(days=window_days))
    reviewed = conn.execute("SELECT review_status FROM noise_review_samples WHERE reviewed_at>=?", (cutoff,)).fetchall()
    conclusive = [
        row
        for row in reviewed
        if str(row["review_status"]) in {"CONFIRMED_NOISE", "FALSE_NEGATIVE"}
    ]
    inconclusive = sum(1 for row in reviewed if str(row["review_status"]) == "INCONCLUSIVE")
    false_negatives = sum(1 for row in conclusive if str(row["review_status"]) == "FALSE_NEGATIVE")
    replayability = _zero_item_replayability(conn, cutoff=cutoff)
    active_manual = int(conn.execute("SELECT COUNT(*) FROM manual_promotions WHERE status='ACTIVE'").fetchone()[0])
    high_value_recent_yield = 0
    source_by_id = {str(row.get("source_id")): row for row in source_rows if isinstance(row, dict)}
    for sid in MANDATORY_COVERAGE_SOURCES:
        row = source_by_id.get(sid) or {}
        if int(row.get("current_opportunities") or 0) > 0 or int(row.get("effective_signals_window") or 0) > 0:
            high_value_recent_yield += 1
    metrics = {
        "active_sources": int(summary.get("active_sources") or 0),
        "green_sources": int(summary.get("health_green") or 0),
        "mandatory_coverage_proven": mandatory_proven,
        "mandatory_coverage_total": mandatory_total,
        "mandatory_coverage_proof_rate": round(mandatory_proven / mandatory_total, 4) if mandatory_total else 0.0,
        "mandatory_coverage_statuses": coverage_distribution,
        "open_misses": len(open_miss_rows),
        "open_red_misses": sum(1 for row in open_miss_rows if str(row["severity"]) == "RED"),
        "noise_samples_reviewed_window": len(reviewed),
        "noise_samples_conclusive_window": len(conclusive),
        "noise_samples_inconclusive_window": inconclusive,
        "noise_false_negatives_window": false_negatives,
        "noise_false_negative_rate": round(false_negatives / len(conclusive), 4) if conclusive else None,
        "filtered_zero_item_records_window": replayability["total"],
        "filtered_zero_item_replayable_window": replayability["replayable"],
        "filtered_zero_item_unreplayable_window": replayability["unreplayable"],
        "current_opportunities": int(summary.get("current_opportunities") or 0),
        "canonical_current_opportunities": int(summary.get("canonical_current_opportunities") or 0),
        "verified_external_opportunities": int(summary.get("verified_external_opportunities") or 0),
        "raw_signals": int(summary.get("raw_signals") or 0),
        "known_noise_signals": int(summary.get("known_noise_signals") or 0),
        "effective_signals": int(summary.get("effective_signals") or 0),
        "telegram_alerts": int(summary.get("telegram_alerts") or 0),
        "active_manual_promotions": active_manual,
        "high_value_sources_with_recent_business_yield": high_value_recent_yield,
        "high_value_sources_total": mandatory_total,
        "window_days": window_days,
    }
    fail_reasons: list[str] = []
    review_reasons: list[str] = []
    if metrics["open_red_misses"]:
        fail_reasons.append("OPEN_RED_MISS_EXISTS")
    if coverage_distribution.get("GAP", 0):
        fail_reasons.append("MANDATORY_COVERAGE_GAP")
    unproven = sum(coverage_distribution.get(state, 0) for state in ("UNPROVEN", "CHECK_FAILED", "PARTIAL"))
    if unproven:
        review_reasons.append("MANDATORY_COVERAGE_NOT_FULLY_PROVEN")
    if not conclusive:
        review_reasons.append("NO_CONCLUSIVE_NOISE_SAMPLE_IN_WINDOW")
    if int(metrics["filtered_zero_item_unreplayable_window"]) > 0:
        review_reasons.append("FILTERED_EVIDENCE_NOT_REPLAYABLE")
    if false_negatives > 0:
        review_reasons.append("RECENT_NOISE_FALSE_NEGATIVE_EXISTS")
    if int(metrics["green_sources"]) > 0 and int(metrics["current_opportunities"]) == 0 and int(metrics["effective_signals"]) == 0:
        review_reasons.append("TECHNICAL_HEALTH_WITHOUT_BUSINESS_OUTCOME")
    if fail_reasons:
        status = "FAIL"
    elif review_reasons:
        status = "REVIEW"
    else:
        status = "PASS"
    conclusions = {
        "fail_reasons": fail_reasons,
        "review_reasons": review_reasons,
        "useful_metrics": ["mandatory_coverage_proof_rate", "open_misses", "noise_samples_conclusive_window", "noise_false_negative_rate", "filtered_zero_item_replayable_window", "current_opportunities", "canonical_current_opportunities", "verified_external_opportunities", "effective_signals", "high_value_sources_with_recent_business_yield"],
        "diagnostic_only_not_business_value_proof": ["active_sources", "green_sources", "raw_signals"],
        "principle": "Source count, GREEN health and raw Signal volume are diagnostics; none is sufficient evidence of commercial value without coverage and outcome evidence.",
    }
    review_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO metric_reviews(metric_review_id,assurance_run_id,observed_at,window_days,status,metrics_json,conclusions_json) VALUES (?,?,?,?,?,?,?)",
        (review_id, assurance_run_id, _iso(now), window_days, status, _json(metrics), _json(conclusions)),
    )
    return {"metric_review_id": review_id, "status": status, "metrics": metrics, "conclusions": conclusions}


def run_assurance(
    *,
    database: Path | None = None,
    now: datetime | None = None,
    registry: Registry | None = None,
    network: bool = True,
    noise_sample_size: int = 5,
) -> dict[str, object]:
    target = database or db_path()
    migrate(target)
    registry = registry or Registry.load()
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    run_id = str(uuid.uuid4())
    started_at = _iso(observed)
    with connect(target) as conn, conn:
        conn.execute(
            "INSERT INTO assurance_runs(assurance_run_id,started_at,status,network_checks,summary_json) VALUES (?,?,'RUNNING',?,?)",
            (run_id, started_at, int(network), "{}"),
        )

    audit_result = audit(database=target, registry=registry, now=observed, network=network)
    coverage_rows: list[dict[str, object]] = []
    sources_raw = registry.raw.get("sources") or {}
    for source_id in MANDATORY_COVERAGE_SOURCES:
        if source_id in {"S13", "S41"}:
            result = _coverage_from_existing_audit(audit_result, source_id) if network else {
                "source_id": source_id, "method": "existing-independent-auditor", "status": "UNPROVEN", "official": 0, "covered": 0, "missing": [], "details": {"reason": "NETWORK_DISABLED"}
            }
        else:
            policy = sources_raw.get(source_id) if isinstance(sources_raw, dict) else None
            if not isinstance(policy, dict) or policy.get("enabled") is not True:
                result = {"source_id": source_id, "method": "independent-listing-links", "status": "UNPROVEN", "official": 0, "covered": 0, "missing": [], "details": {"reason": "SOURCE_DISABLED_OR_MISSING"}}
            else:
                with connect(target) as coverage_conn:
                    result = _coverage_from_listing(
                        coverage_conn,
                        database=target,
                        assurance_run_id=run_id,
                        source_id=source_id,
                        policy=policy,
                        network=network,
                        now=observed,
                    )
        if str(result["status"]) not in COVERAGE_STATUSES:
            result["status"] = "CHECK_FAILED"
        coverage_rows.append(result)
        with connect(target) as conn, conn:
            conn.execute(
                """
                INSERT INTO coverage_audit_results(
                    coverage_audit_id,assurance_run_id,source_id,audit_method,status,official_candidate_count,
                    canonical_covered_count,missing_count,checked_at,details_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(uuid.uuid4()), run_id, source_id, result["method"], result["status"], int(result["official"]),
                    int(result["covered"]), len(result["missing"]), _iso(observed), _json(result["details"]),
                ),
            )

    supplemental_coverage_rows: list[dict[str, object]] = []
    assurance_surfaces = registry.raw.get("assurance_surfaces") or {}
    if isinstance(assurance_surfaces, dict):
        for surface_id, policy in sorted(assurance_surfaces.items()):
            if not isinstance(policy, dict) or policy.get("enabled") is not True:
                continue
            with connect(target) as coverage_conn:
                result = _coverage_from_aggregator_surface(
                    coverage_conn,
                    source_id=str(surface_id),
                    policy=policy,
                    network=network,
                    now=observed,
                )
            if str(result["status"]) not in COVERAGE_STATUSES:
                result["status"] = "CHECK_FAILED"
            supplemental_coverage_rows.append(result)
            with connect(target) as conn, conn:
                conn.execute(
                    """
                    INSERT INTO coverage_audit_results(
                        coverage_audit_id,assurance_run_id,source_id,audit_method,status,official_candidate_count,
                        canonical_covered_count,missing_count,checked_at,details_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(uuid.uuid4()), run_id, str(surface_id), result["method"], result["status"], int(result["official"]),
                        int(result["covered"]), len(result["missing"]), _iso(observed), _json(result["details"]),
                    ),
                )

    with connect(target) as conn, conn:
        samples = _sample_noise(conn, assurance_run_id=run_id, now=observed, sample_size=noise_sample_size)

    misses_created: list[dict[str, object]] = []
    for result in coverage_rows:
        if result["status"] != "GAP":
            continue
        for missing in result["missing"]:
            miss = record_missed_signal(
                source_id=str(result["source_id"]),
                title=f"Official high-value source item missing from SignalForge: {missing}",
                reason="Independent high-value coverage audit found an official candidate absent from canonical state",
                severity="RED",
                detected_by="COVERAGE_AUDIT",
                url=str(missing) if str(missing).startswith("http") else None,
                canonical_key=str(missing) if not str(missing).startswith("http") else None,
                metadata={"assurance_run_id": run_id, "audit_method": result["method"]},
                database=target,
                now=observed,
            )
            misses_created.append(miss)

    for result in supplemental_coverage_rows:
        details = result.get("details") or {}
        confirmed_gaps = details.get("confirmed_gaps") if isinstance(details, dict) else []
        if not isinstance(confirmed_gaps, list):
            continue
        for lead in confirmed_gaps:
            if not isinstance(lead, dict):
                continue
            reviewed_gap = lead.get("reviewed_gap") or {}
            if not isinstance(reviewed_gap, dict):
                continue
            miss = record_missed_signal(
                source_id=str(reviewed_gap.get("source_id") or lead.get("target_source_hint") or result["source_id"]),
                title=str(reviewed_gap.get("title") or lead.get("title") or "Aggregator-discovered coverage gap"),
                reason="Reviewed National Portal lead proves a current official opportunity absent from issuer-oriented canonical coverage",
                severity="RED",
                detected_by="AGGREGATOR_COVERAGE_AUDIT",
                url=str(lead.get("url") or reviewed_gap.get("url") or "") or None,
                metadata={
                    "assurance_run_id": run_id,
                    "aggregator_source_id": str(result["source_id"]),
                    "lead_id": lead.get("lead_id"),
                    "deadline": reviewed_gap.get("deadline") or lead.get("closing_date_hint"),
                    "portal_closing_date_hint": lead.get("closing_date_hint"),
                    "reviewed_gap_id": reviewed_gap.get("gap_id"),
                    "canonical_truth": False,
                },
                database=target,
                now=observed,
            )
            misses_created.append(miss)

    verified_resolution_urls: set[str] = set()
    for result in supplemental_coverage_rows:
        details = result.get("details") or {}
        rows = details.get("verified_external_leads") if isinstance(details, dict) else []
        if not isinstance(rows, list):
            continue
        for item in rows:
            if isinstance(item, dict) and item.get("url"):
                verified_resolution_urls.add(str(item["url"]))

    with connect(target) as conn, conn:
        verified_resolved_aggregator_misses = _resolve_verified_aggregator_misses(
            conn, now=observed, verified_urls=verified_resolution_urls
        )
        auto_resolved_aggregator_misses = _resolve_expired_aggregator_misses(conn, now=observed)
        metric_review = _metric_review(conn, assurance_run_id=run_id, coverage_rows=coverage_rows, now=observed, registry=registry)
        open_misses = int(conn.execute("SELECT COUNT(*) FROM missed_signals WHERE status='OPEN'").fetchone()[0])
        red_misses = int(conn.execute("SELECT COUNT(*) FROM missed_signals WHERE status='OPEN' AND severity='RED'").fetchone()[0])
        summary = {
            "assurance_version": ASSURANCE_VERSION,
            "coverage": {"mandatory": len(MANDATORY_COVERAGE_SOURCES), "proven": sum(1 for row in coverage_rows if row["status"] == "PASS"), "gaps": sum(1 for row in coverage_rows if row["status"] == "GAP"), "unproven": sum(1 for row in coverage_rows if row["status"] in {"UNPROVEN", "PARTIAL", "CHECK_FAILED"})},
            "supplemental_coverage": {
                "surfaces": len(supplemental_coverage_rows),
                "gaps": sum(1 for row in supplemental_coverage_rows if row["status"] == "GAP"),
                "partial": sum(1 for row in supplemental_coverage_rows if row["status"] == "PARTIAL"),
            },
            "noise_samples_created": len(samples),
            "verified_resolved_aggregator_misses": verified_resolved_aggregator_misses,
            "auto_resolved_aggregator_misses": auto_resolved_aggregator_misses,
            "open_misses": open_misses,
            "open_red_misses": red_misses,
            "metric_validity": metric_review["status"],
        }
        final_status = str(metric_review["status"])
        conn.execute(
            "UPDATE assurance_runs SET finished_at=?,status=?,summary_json=? WHERE assurance_run_id=?",
            (_iso(datetime.now(UTC)), final_status, _json(summary), run_id),
        )
    return {
        "status": final_status,
        "assurance_version": ASSURANCE_VERSION,
        "assurance_run_id": run_id,
        "as_of": _iso(observed),
        "network_checks": network,
        "coverage": coverage_rows,
        "supplemental_coverage": supplemental_coverage_rows,
        "noise_samples_created": samples,
        "coverage_misses_recorded": len(misses_created),
        "verified_resolved_aggregator_misses": verified_resolved_aggregator_misses,
        "auto_resolved_aggregator_misses": auto_resolved_aggregator_misses,
        "metric_review": metric_review,
        "contract": {"sends_telegram": False, "mutates_canonical_or_signals": False, "persists_assurance_state": True, "unsupported_coverage_never_defaults_to_pass": True},
    }


def _coverage_risk_rows(
    conn,  # type: ignore[no-untyped-def]
    *,
    assurance_run_id: str,
    registry: Registry | None = None,
) -> list[dict[str, object]]:
    placeholders = ",".join("?" for _ in MANDATORY_COVERAGE_SOURCES)
    rows = conn.execute(
        f"""
        SELECT c.source_id,c.status,c.checked_at,c.details_json,
               s.last_success_at,s.last_error,s.consecutive_failures
        FROM coverage_audit_results c
        LEFT JOIN source_state s ON s.source_id=c.source_id
        WHERE c.assurance_run_id=?
          AND c.source_id IN ({placeholders})
          AND c.status!='PASS'
        ORDER BY c.source_id
        """,
        (assurance_run_id, *MANDATORY_COVERAGE_SOURCES),
    ).fetchall()
    sources = {}
    if registry is not None:
        raw_sources = registry.raw.get("sources") or {}
        if isinstance(raw_sources, dict):
            sources = raw_sources

    risks: list[dict[str, object]] = []
    for row in rows:
        try:
            details = json.loads(str(row["details_json"] or "{}"))
        except json.JSONDecodeError:
            details = {}
        source_id = str(row["source_id"])
        source_name = source_id
        policy = sources.get(source_id) if isinstance(sources, dict) else None
        if isinstance(policy, dict) and policy.get("name"):
            source_name = str(policy["name"])
        reason = str(details.get("reason") or details.get("error") or "COVERAGE_NOT_PROVEN")
        last_success_at = row["last_success_at"]
        risks.append(
            {
                "source_id": source_id,
                "source_name": source_name,
                "coverage_status": str(row["status"]),
                "checked_at": row["checked_at"],
                "last_success_at": last_success_at,
                "risk_since": last_success_at or row["checked_at"],
                "reason": reason,
                "last_error": row["last_error"],
                "consecutive_failures": int(row["consecutive_failures"] or 0),
                "known_miss": False,
                "semantics": "COVERAGE_RISK_NOT_CONFIRMED_MISS",
                "interpretation": "NO_NEW_SIGNAL_DOES_NOT_PROVE_NO_NEW_OPPORTUNITY",
            }
        )
    return risks


def assurance_status(
    *,
    database: Path | None = None,
    registry: Registry | None = None,
) -> dict[str, object]:
    target = database or db_path()
    migrate(target)
    registry = registry or Registry.load()
    with connect(target) as conn:
        run = conn.execute("SELECT * FROM assurance_runs ORDER BY started_at DESC LIMIT 1").fetchone()
        review = conn.execute("SELECT * FROM metric_reviews ORDER BY observed_at DESC LIMIT 1").fetchone()
        counts = {
            "open_misses": int(conn.execute("SELECT COUNT(*) FROM missed_signals WHERE status='OPEN'").fetchone()[0]),
            "open_red_misses": int(conn.execute("SELECT COUNT(*) FROM missed_signals WHERE status='OPEN' AND severity='RED'").fetchone()[0]),
            "pending_noise_reviews": int(conn.execute("SELECT COUNT(*) FROM noise_review_samples WHERE review_status='PENDING'").fetchone()[0]),
            "false_negative_noise_reviews": int(conn.execute("SELECT COUNT(*) FROM noise_review_samples WHERE review_status='FALSE_NEGATIVE'").fetchone()[0]),
            "active_manual_promotions": int(conn.execute("SELECT COUNT(*) FROM manual_promotions WHERE status='ACTIVE'").fetchone()[0]),
        }
        coverage = []
        coverage_risks: list[dict[str, object]] = []
        if run is not None:
            coverage = [dict(row) for row in conn.execute("SELECT source_id,audit_method,status,official_candidate_count,canonical_covered_count,missing_count,checked_at FROM coverage_audit_results WHERE assurance_run_id=? ORDER BY source_id", (run["assurance_run_id"],))]
            coverage_risks = _coverage_risk_rows(
                conn,
                assurance_run_id=str(run["assurance_run_id"]),
                registry=registry,
            )
    return {
        "status": "NOT_RUN" if run is None else str(run["status"]),
        "assurance_version": ASSURANCE_VERSION,
        "latest_run": dict(run) if run is not None else None,
        "latest_metric_review": ({**dict(review), "metrics": json.loads(str(review["metrics_json"])), "conclusions": json.loads(str(review["conclusions_json"]))} if review is not None else None),
        "counts": counts,
        "coverage": coverage,
        "coverage_risk_count": len(coverage_risks),
        "coverage_risks": coverage_risks,
    }
