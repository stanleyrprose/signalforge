from __future__ import annotations

import hashlib
import io
import re
from collections.abc import Callable
from datetime import date
from urllib.parse import urlparse

from pypdf import PdfReader

from .http import fetch_bytes
from .mpt import normalize_text

REVIEW_PACKET_VERSION = 0
AUTHORITY = "HUMAN_REVIEW_REQUIRED"
PRODUCTION_EFFECT = "NONE"
WRITES = "NONE"
EXTRACTION_METHOD = "PYPDF_TEXT_NATIVE_V0"
MPT_TEMPLATE_PROFILE = "S13_MPT_NUMBERED_TENDER_V0"
GENERIC_TEMPLATE_PROFILE = "GENERIC_TEXT_ONLY_V0"
DEFAULT_MAX_BYTES = 8_000_000
DEFAULT_TIMEOUT_SECONDS = 12

_ALLOWED_HOSTS = {"myanmar.gov.mm", "www.myanmar.gov.mm"}
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_SECTION_RE = re.compile(r"^\s*([1-9])\s*[။.)]\s*(.*)$")
_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(20(?:\s*\d){2})(?!\d)")
_TIME_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[:း.]\s*(\d{2})(?!\d)")


def _allowed_document_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() in _ALLOWED_HOSTS
        and parsed.path.startswith("/documents/")
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
    )


def _clean_pdf_text(value: str) -> str:
    value = value.translate(_MYANMAR_DIGITS)
    value = "".join(char if (char in "\n\t" or ord(char) >= 32) else " " for char in value)
    lines = [normalize_text(line) for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def _document_preamble(text: str) -> str | None:
    parts: list[str] = []
    for line in text.splitlines():
        if _SECTION_RE.match(line):
            break
        if line:
            parts.append(line)
    value = normalize_text(" ".join(parts))
    return value[:900] if value else None


def _template_profile(lead: dict[str, object]) -> str:
    agency = str(lead.get("agency") or "").lower()
    target = str(lead.get("target_source_hint") or "")
    if target == "S13" and "digital development and communications" in agency:
        return MPT_TEMPLATE_PROFILE
    return GENERIC_TEMPLATE_PROFILE


def _numbered_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = _SECTION_RE.match(line)
        if match:
            current = match.group(1)
            sections.setdefault(current, [])
            remainder = normalize_text(match.group(2))
            if remainder:
                sections[current].append(remainder)
            continue
        if current is not None:
            sections[current].append(line)
    return {
        section: normalize_text(" ".join(parts))
        for section, parts in sections.items()
        if normalize_text(" ".join(parts))
    }


def _first_date(text: str) -> str | None:
    match = _DATE_RE.search(text)
    if match is None:
        return None
    day = int(match.group(1))
    month = int(match.group(2))
    year = int(re.sub(r"\s+", "", match.group(3)))
    try:
        parsed = date(year, month, day)
    except ValueError:
        return None
    return parsed.isoformat()


def _times(text: str) -> list[str]:
    values: list[str] = []
    matches = list(_TIME_RE.finditer(text))
    pm_context = any(marker in text.lower() for marker in ("ညေန", "ညနေ", " p.m", " pm"))
    for match in matches:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if hour > 23 or minute > 59:
            continue
        if pm_context and len(matches) == 1 and 1 <= hour <= 11:
            hour += 12
        value = f"{hour:02d}:{minute:02d}"
        if value not in values:
            values.append(value)
    return values


def _scope_excerpt(section_one: str) -> str | None:
    if not section_one:
        return None
    match = re.search(r"(?:^|\s)-\s+(.+)", section_one)
    scope = normalize_text(match.group(1) if match else section_one)
    return scope[:1600] if scope else None


def _project_location_hint(scope: str | None) -> str | None:
    text = scope or ""
    if "ပုဗ" in text and "သီရိ" in text:
        return "Pobbathiri Township, Nay Pyi Taw"
    patterns = (
        ("Nay Pyi Taw", ("နေပြည်တော်", "ေနြပည်ေတာ်", "ေနပြည်တော်", "နေြပည်ေတာ်")),
        ("Yangon", ("ရန်ကုန်", "ရန္ကုန္")),
        ("Mandalay", ("မန္တလေး", "မႏၲေလး")),
    )
    for label, aliases in patterns:
        if any(alias in text for alias in aliases):
            return label
    return None


def _next_action_summary(fields: dict[str, object]) -> str | None:
    parts: list[str] = []
    sale_close = str(fields.get("tender_form_sale_close") or "")
    sale_close_time = str(fields.get("tender_form_sale_close_time") or "")
    if sale_close:
        parts.append(f"Tender form sale closes {sale_close}{(' ' + sale_close_time) if sale_close_time else ''}")
    site_survey = str(fields.get("site_survey_date") or "")
    if site_survey:
        parts.append(f"Site survey {site_survey}")
    deadline = str(fields.get("proposed_deadline") or "")
    start = str(fields.get("tender_submission_start_time") or "")
    end = str(fields.get("proposed_deadline_time") or "")
    if deadline:
        window = f" {start}-{end}" if start and end and start != end else (f" {end}" if end else "")
        parts.append(f"Bid submission {deadline}{window}")
    return "; ".join(parts) or None


def _base_packet(*, lead: dict[str, object], url: str) -> dict[str, object]:
    return {
        "review_packet_version": REVIEW_PACKET_VERSION,
        "authority": AUTHORITY,
        "production_effect": PRODUCTION_EFFECT,
        "writes": WRITES,
        "review_state": "PENDING_HUMAN_CONFIRMATION",
        "lead_id": str(lead.get("lead_id") or ""),
        "target_source_hint": str(lead.get("target_source_hint") or ""),
        "document_url": url,
        "issuer_hint": str(lead.get("agency") or "") or None,
        "mission_sector_hint": str(lead.get("mission_sector_hint") or "") or None,
        "portal_closing_date_hint": str(lead.get("closing_date_hint") or "") or None,
        "canonical_truth": False,
        "verified_external": False,
        "human_confirmation_required": True,
    }


def build_external_official_review_packet(
    lead: dict[str, object],
    *,
    fetcher: Callable[..., bytes] = fetch_bytes,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, object]:
    """Build a bounded review packet from one Portal-hosted official PDF.

    The packet is evidence for human review only. It never verifies the proposed
    fields and never mutates canonical, Signal, miss, or verified-external state.
    """

    url = str(lead.get("url") or "")
    base = _base_packet(lead=lead, url=url)
    if (
        lead.get("evidence_kind") != "NATIONAL_PORTAL_HOSTED_DOCUMENT"
        or lead.get("aggregator_only") is not True
        or lead.get("canonical_truth") is not False
        or not str(lead.get("target_source_hint") or "")
        or not _allowed_document_url(url)
    ):
        return {
            **base,
            "status": "REJECTED_INPUT",
            "reason": "LEAD_DOES_NOT_SATISFY_OFFICIAL_REVIEW_PACKET_BOUNDARY",
        }
    if timeout < 1 or timeout > 120:
        raise ValueError("review packet timeout must be between 1 and 120 seconds")
    if max_bytes < 100_000 or max_bytes > 20_000_000:
        raise ValueError("review packet max_bytes must be between 100000 and 20000000")

    try:
        payload = fetcher(url, timeout=timeout, max_bytes=max_bytes)
    except Exception as exc:
        return {
            **base,
            "status": "FETCH_FAILED",
            "reason": f"{type(exc).__name__}: {exc}",
        }

    digest = hashlib.sha256(payload).hexdigest()
    packet: dict[str, object] = {
        **base,
        "document_sha256": digest,
        "document_bytes": len(payload),
    }
    if not payload.startswith(b"%PDF-"):
        return {
            **packet,
            "status": "NOT_PDF",
            "reason": "OFFICIAL_DOCUMENT_MAGIC_IS_NOT_PDF",
        }

    try:
        reader = PdfReader(io.BytesIO(payload))
        raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:
        return {
            **packet,
            "status": "PDF_PARSE_FAILED",
            "reason": f"{type(exc).__name__}: {exc}",
        }

    text = _clean_pdf_text(raw_text)
    packet.update(
        {
            "pdf_pages": len(reader.pages),
            "text_chars": len(text),
            "extraction_method": EXTRACTION_METHOD,
        }
    )
    if len(text) < 120:
        return {
            **packet,
            "status": "NEEDS_OCR_OR_MANUAL_REVIEW",
            "reason": "TEXT_NATIVE_EXTRACTION_TOO_SPARSE",
            "evidence_excerpt": text[:800] or None,
        }

    sections = _numbered_sections(text)
    preamble = _document_preamble(text)
    scope = _scope_excerpt(sections.get("1", ""))
    template_profile = _template_profile(lead)
    section_two = sections.get("2", "")
    section_three = sections.get("3", "")
    section_four = sections.get("4", "")
    section_five = sections.get("5", "")
    section_six = sections.get("6", "")

    sale_start = sale_close = site_survey = proposed_deadline = None
    sale_start_times: list[str] = []
    sale_close_times: list[str] = []
    site_survey_times: list[str] = []
    submission_times: list[str] = []
    if template_profile == MPT_TEMPLATE_PROFILE:
        sale_start = _first_date(section_two)
        sale_start_times = _times(section_two)
        sale_close = _first_date(section_three)
        sale_close_times = _times(section_three)
        site_survey = _first_date(section_four)
        site_survey_times = _times(section_four)
        proposed_deadline = _first_date(section_five)
        submission_times = _times(section_five)

    proposed_fields: dict[str, object] = {
        "issuer_hint": str(lead.get("agency") or "") or None,
        "issuer_document_evidence": preamble,
        "scope_excerpt": scope,
        "project_location_hint": _project_location_hint(scope),
        "project_location_evidence": scope[:360] if scope else None,
        "submission_location_evidence": section_six[:700] if section_six and template_profile == MPT_TEMPLATE_PROFILE else None,
        "tender_form_sale_start": sale_start,
        "tender_form_sale_start_time": sale_start_times[0] if sale_start_times else None,
        "tender_form_sale_close": sale_close,
        "tender_form_sale_close_time": sale_close_times[-1] if sale_close_times else None,
        "site_survey_date": site_survey,
        "site_survey_time": site_survey_times[0] if site_survey_times else None,
        "proposed_deadline": proposed_deadline,
        "tender_submission_start_time": submission_times[0] if len(submission_times) >= 2 else None,
        "proposed_deadline_time": submission_times[-1] if submission_times else None,
    }
    proposed_fields["next_action_summary"] = _next_action_summary(proposed_fields)

    required_ready = bool(template_profile == MPT_TEMPLATE_PROFILE and preamble and scope and proposed_deadline)
    return {
        **packet,
        "status": "TEXT_NATIVE_REVIEW_READY" if required_ready else "PARTIAL_REVIEW_PACKET",
        "reason": None if required_ready else (
            "UNREVIEWED_DOCUMENT_TEMPLATE_SEMANTICS"
            if template_profile == GENERIC_TEMPLATE_PROFILE
            else "TEXT_EXTRACTED_BUT_ISSUER_SCOPE_OR_BID_DEADLINE_NOT_PROVEN"
        ),
        "template_profile": template_profile,
        "proposed_fields": proposed_fields,
        "evidence_sections": {
            key: value[:1000]
            for key, value in sections.items()
            if key in {"1", "2", "3", "4", "5", "6"}
        },
        "evidence_excerpt": text[:1800],
        "human_confirmation_required": True,
        "promotion_contract": "VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY_REQUIRES_SEPARATE_REVIEW",
    }
