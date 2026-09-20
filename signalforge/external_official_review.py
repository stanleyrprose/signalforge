from __future__ import annotations

import hashlib
import io
import re
from collections.abc import Callable
from datetime import date
from urllib.parse import unquote, urlparse

from pypdf import PdfReader

from .http import fetch_bytes
from .mpt import normalize_text

REVIEW_PACKET_VERSION = 1
AUTHORITY = "HUMAN_REVIEW_REQUIRED"
PRODUCTION_EFFECT = "NONE"
WRITES = "NONE"
EXTRACTION_METHOD = "PYPDF_NATIVE_PLUS_MANDATORY_DOCUMENT_OCR_V1"
MPT_TEMPLATE_PROFILE = "S13_MPT_NUMBERED_TENDER_V1"
GENERIC_TEMPLATE_PROFILE = "GENERIC_TEXT_ONLY_V1"
DEFAULT_MAX_BYTES = 8_000_000
DEFAULT_TIMEOUT_SECONDS = 12

_ALLOWED_HOSTS = {"myanmar.gov.mm"}
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_SECTION_RE = re.compile(r"^\s*([1-9])\s*[။.)]\s*(.*)$")
_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(20(?:\s*\d){2})(?!\d)")
_TIME_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[:း.]\s*(\d{2})(?!\d)")


def _allowed_document_url(url: str) -> bool:
    parsed = urlparse(url)
    decoded_path = unquote(parsed.path)
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() in _ALLOWED_HOSTS
        and parsed.path.startswith("/documents/")
        and ".." not in decoded_path.split("/")
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
        and not parsed.query
        and not parsed.fragment
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


def _ocr_mpt_fields(text: str) -> dict[str, object]:
    fields: dict[str, object] = {
        "project_location_hint": _project_location_hint(text),
        "tender_form_sale_start": None,
        "tender_form_sale_start_time": None,
        "tender_form_sale_close": None,
        "tender_form_sale_close_time": None,
        "site_survey_date": None,
        "site_survey_time": None,
        "proposed_deadline": None,
        "tender_submission_start_time": None,
        "proposed_deadline_time": None,
    }
    for line in text.splitlines():
        date_value = _first_date(line)
        if not date_value:
            continue
        times = _times(line)
        lower = line.lower()
        if "site survey" in lower:
            fields["site_survey_date"] = date_value
            fields["site_survey_time"] = times[0] if times else None
        elif "စတင်" in line and "ရောင်း" in line:
            fields["tender_form_sale_start"] = date_value
            fields["tender_form_sale_start_time"] = times[0] if times else None
        elif "အရောင်းပိတ်" in line or ("ရောင်း" in line and "ပိတ်" in line):
            fields["tender_form_sale_close"] = date_value
            fields["tender_form_sale_close_time"] = times[-1] if times else None
        elif len(times) >= 2:
            fields["proposed_deadline"] = date_value
            fields["tender_submission_start_time"] = times[0]
            fields["proposed_deadline_time"] = times[-1]
    return fields


def _native_fields(text: str, lead: dict[str, object]) -> tuple[str, dict[str, object], dict[str, str]]:
    template_profile = _template_profile(lead)
    sections = _numbered_sections(text)
    preamble = _document_preamble(text)
    scope = _scope_excerpt(sections.get("1", ""))
    section_two = sections.get("2", "")
    section_three = sections.get("3", "")
    section_four = sections.get("4", "")
    section_five = sections.get("5", "")
    section_six = sections.get("6", "")

    fields: dict[str, object] = {
        "issuer_hint": str(lead.get("agency") or "") or None,
        "issuer_document_evidence": preamble,
        "scope_excerpt": scope,
        "project_location_hint": _project_location_hint(scope),
        "project_location_evidence": scope[:360] if scope else None,
        "submission_location_evidence": None,
        "tender_form_sale_start": None,
        "tender_form_sale_start_time": None,
        "tender_form_sale_close": None,
        "tender_form_sale_close_time": None,
        "site_survey_date": None,
        "site_survey_time": None,
        "proposed_deadline": None,
        "tender_submission_start_time": None,
        "proposed_deadline_time": None,
    }
    if template_profile == MPT_TEMPLATE_PROFILE:
        sale_start_times = _times(section_two)
        sale_close_times = _times(section_three)
        site_survey_times = _times(section_four)
        submission_times = _times(section_five)
        fields.update(
            {
                "submission_location_evidence": section_six[:700] if section_six else None,
                "tender_form_sale_start": _first_date(section_two),
                "tender_form_sale_start_time": sale_start_times[0] if sale_start_times else None,
                "tender_form_sale_close": _first_date(section_three),
                "tender_form_sale_close_time": sale_close_times[-1] if sale_close_times else None,
                "site_survey_date": _first_date(section_four),
                "site_survey_time": site_survey_times[0] if site_survey_times else None,
                "proposed_deadline": _first_date(section_five),
                "tender_submission_start_time": submission_times[0] if len(submission_times) >= 2 else None,
                "proposed_deadline_time": submission_times[-1] if submission_times else None,
            }
        )
    return template_profile, fields, sections


_CRITICAL_FIELDS = (
    "project_location_hint",
    "tender_form_sale_start",
    "tender_form_sale_start_time",
    "tender_form_sale_close",
    "tender_form_sale_close_time",
    "site_survey_date",
    "site_survey_time",
    "proposed_deadline",
    "tender_submission_start_time",
    "proposed_deadline_time",
)


def _field_reconciliation(native: object, ocr: object) -> str:
    native_value = str(native or "")
    ocr_value = str(ocr or "")
    if native_value and ocr_value:
        return "AGREED" if native_value == ocr_value else "CONFLICT"
    if native_value:
        return "NATIVE_ONLY_PROPOSED"
    if ocr_value:
        return "OCR_ONLY_PROPOSED"
    return "MISSING"


def _merge_fields(native: dict[str, object], ocr: dict[str, object]) -> tuple[dict[str, object], dict[str, str]]:
    merged = dict(native)
    statuses: dict[str, str] = {}
    for key in _CRITICAL_FIELDS:
        status = _field_reconciliation(native.get(key), ocr.get(key))
        statuses[key] = status
        if status == "OCR_ONLY_PROPOSED":
            merged[key] = ocr.get(key)
        elif status == "CONFLICT":
            merged[key] = None
    merged["next_action_summary"] = None if "CONFLICT" in statuses.values() else _next_action_summary(merged)
    return merged, statuses


def build_external_official_review_packet(
    lead: dict[str, object],
    *,
    fetcher: Callable[..., bytes] = fetch_bytes,
    ocr_provider: Callable[[str], dict[str, object]] | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, object]:
    """Build a mandatory-OCR review packet from one Portal-hosted official PDF.

    Native PDF text and visual OCR are independent evidence channels. A packet
    cannot become review-ready without OCR, and every proposed field still
    requires human confirmation before promotion.
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
        return {**base, "status": "REJECTED_INPUT", "reason": "LEAD_DOES_NOT_SATISFY_OFFICIAL_REVIEW_PACKET_BOUNDARY"}
    if timeout < 1 or timeout > 120:
        raise ValueError("review packet timeout must be between 1 and 120 seconds")
    if max_bytes < 100_000 or max_bytes > 20_000_000:
        raise ValueError("review packet max_bytes must be between 100000 and 20000000")

    payload: bytes | None = None
    native_fetch_error: str | None = None
    try:
        payload = fetcher(url, timeout=timeout, max_bytes=max_bytes)
    except Exception as exc:
        native_fetch_error = f"{type(exc).__name__}: {exc}"

    digest = hashlib.sha256(payload).hexdigest() if payload is not None else None
    packet: dict[str, object] = {
        **base,
        "document_sha256": digest,
        "document_bytes": len(payload) if payload is not None else None,
        "native_fetch_error": native_fetch_error,
        "ocr_required": True,
    }
    native_is_pdf = payload is not None and payload.startswith(b"%PDF-")
    native_text = ""
    native_parse_error: str | None = None
    native_pages: int | None = None
    if payload is not None and native_is_pdf:
        try:
            reader = PdfReader(io.BytesIO(payload))
            native_pages = len(reader.pages)
            native_text = _clean_pdf_text("\n".join((page.extract_text() or "") for page in reader.pages))
        except Exception as exc:
            native_parse_error = f"{type(exc).__name__}: {exc}"
    elif payload is not None:
        native_parse_error = "OFFICIAL_DOCUMENT_MAGIC_IS_NOT_PDF"
    packet.update(
        {
            "pdf_pages": native_pages,
            "native_text_chars": len(native_text),
            "native_parse_error": native_parse_error,
            "extraction_method": EXTRACTION_METHOD,
        }
    )

    if ocr_provider is None:
        return {
            **packet,
            "status": "OCR_REQUIRED_NOT_AVAILABLE",
            "reason": "MANDATORY_DOCUMENT_OCR_PROVIDER_NOT_CONFIGURED",
            "native_evidence_excerpt": native_text[:1800] or None,
        }
    try:
        ocr_result = ocr_provider(url)
    except Exception as exc:
        return {
            **packet,
            "status": "OCR_REQUIRED_FAILED",
            "reason": f"{type(exc).__name__}: {exc}",
            "native_evidence_excerpt": native_text[:1800] or None,
        }
    if not isinstance(ocr_result, dict):
        return {**packet, "status": "OCR_REQUIRED_FAILED", "reason": "OCR_PROVIDER_RESULT_NOT_OBJECT"}

    ocr_sha = str(ocr_result.get("input_sha256") or "")
    provider_fetch_sha = str(ocr_result.get("provider_fetch_sha256") or "")
    provider_request_id = str(ocr_result.get("provider_request_id") or "")
    ocr_text_raw = ocr_result.get("text")
    if (
        len(ocr_sha) != 64
        or len(provider_fetch_sha) != 64
        or not provider_request_id
        or not isinstance(ocr_text_raw, str)
    ):
        return {**packet, "status": "OCR_REQUIRED_FAILED", "reason": "OCR_PROVIDER_RESULT_INCOMPLETE"}
    if provider_fetch_sha != ocr_sha:
        return {
            **packet,
            "status": "EVIDENCE_SHA_CONFLICT",
            "reason": "PROVIDER_FETCH_AND_OCR_PDF_SHA256_DIFFER",
            "provider_fetch_sha256": provider_fetch_sha,
            "ocr_input_sha256": ocr_sha,
            "provider_request_id": provider_request_id,
        }
    if digest is not None and digest != provider_fetch_sha:
        return {
            **packet,
            "status": "EVIDENCE_SHA_CONFLICT",
            "reason": "NATIVE_PROVIDER_AND_OCR_PDF_SHA256_DIFFER",
            "native_sha256": digest,
            "provider_fetch_sha256": provider_fetch_sha,
            "ocr_input_sha256": ocr_sha,
            "provider_request_id": provider_request_id,
        }
    if ocr_result.get("network_access") is not False:
        return {**packet, "status": "OCR_REQUIRED_FAILED", "reason": "OCR_PROVIDER_NETWORK_BOUNDARY_INVALID"}

    ocr_text = _clean_pdf_text(ocr_text_raw)
    page_limit_truncated = bool(ocr_result.get("page_limit_truncated"))
    page_count = ocr_result.get("page_count")
    processed_pages = ocr_result.get("processed_pages")
    if not isinstance(page_count, int) or not isinstance(processed_pages, int) or page_count < 1 or processed_pages < 1:
        return {**packet, "status": "OCR_REQUIRED_FAILED", "reason": "OCR_PROVIDER_PAGE_METADATA_INVALID"}
    if processed_pages > page_count or page_limit_truncated != (processed_pages < page_count):
        return {**packet, "status": "OCR_REQUIRED_FAILED", "reason": "OCR_PROVIDER_PAGE_COMPLETENESS_INCONSISTENT"}
    packet.update(
        {
            "document_sha256": digest or ocr_sha,
            "provider_request_id": provider_request_id,
            "provider_fetch_sha256": provider_fetch_sha,
            "ocr_input_sha256": ocr_sha,
            "ocr_text_chars": len(ocr_text),
            "ocr_engine": ocr_result.get("engine"),
            "ocr_rasterizer": ocr_result.get("rasterizer"),
            "ocr_model_profile": ocr_result.get("model_profile"),
            "ocr_languages": ocr_result.get("languages"),
            "ocr_mean_confidence": ocr_result.get("mean_confidence"),
            "ocr_page_count": page_count,
            "ocr_processed_pages": processed_pages,
            "ocr_page_limit_truncated": page_limit_truncated,
        }
    )
    if page_limit_truncated:
        return {
            **packet,
            "status": "OCR_PAGE_LIMIT_REVIEW_REQUIRED",
            "reason": "MANDATORY_OCR_DID_NOT_PROCESS_ALL_PAGES",
            "native_evidence_excerpt": native_text[:1800] or None,
            "ocr_evidence_excerpt": ocr_text[:1800] or None,
        }

    template_profile, native_fields, sections = _native_fields(native_text, lead)
    ocr_fields: dict[str, object] = {}
    if template_profile == MPT_TEMPLATE_PROFILE:
        ocr_fields = _ocr_mpt_fields(ocr_text)
    else:
        ocr_fields = {"project_location_hint": _project_location_hint(ocr_text)}
    proposed_fields, field_statuses = _merge_fields(native_fields, ocr_fields)
    conflicts = [key for key, value in field_statuses.items() if value == "CONFLICT"]
    native_only = [key for key, value in field_statuses.items() if value == "NATIVE_ONLY_PROPOSED"]
    ocr_only = [key for key, value in field_statuses.items() if value == "OCR_ONLY_PROPOSED"]

    field_evidence = {
        key: {
            "native": native_fields.get(key),
            "ocr": ocr_fields.get(key),
            "status": field_statuses.get(key),
        }
        for key in _CRITICAL_FIELDS
    }
    sha_abc_match = digest is not None and digest == provider_fetch_sha == ocr_sha
    reconciliation = {
        "native_sha256": digest,
        "provider_fetch_sha256": provider_fetch_sha,
        "ocr_sha256": ocr_sha,
        "sha_a_equals_b_equals_c": sha_abc_match,
        "field_statuses": field_statuses,
        "field_evidence": field_evidence,
        "conflict_fields": conflicts,
        "native_only_fields": native_only,
        "ocr_only_fields": ocr_only,
    }
    common = {
        **packet,
        "template_profile": template_profile,
        "proposed_fields": proposed_fields,
        "reconciliation": reconciliation,
        "evidence_sections": {key: value[:1000] for key, value in sections.items() if key in {"1", "2", "3", "4", "5", "6"}},
        "native_evidence_excerpt": native_text[:1800] or None,
        "ocr_evidence_excerpt": ocr_text[:1800] or None,
        "promotion_contract": "VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY_REQUIRES_SEPARATE_REVIEW",
    }

    if template_profile == GENERIC_TEMPLATE_PROFILE:
        generic_fields = dict(proposed_fields)
        generic_fields["next_action_summary"] = None
        return {**common, "proposed_fields": generic_fields, "status": "PARTIAL_REVIEW_PACKET", "reason": "UNREVIEWED_DOCUMENT_TEMPLATE_SEMANTICS"}
    if conflicts:
        conflict_fields = dict(proposed_fields)
        conflict_fields["next_action_summary"] = None
        return {**common, "proposed_fields": conflict_fields, "status": "DUAL_EVIDENCE_CONFLICT", "reason": "NATIVE_AND_OCR_CRITICAL_FIELD_CONFLICT"}
    if len(native_text) < 120 or native_parse_error or native_fetch_error:
        if proposed_fields.get("proposed_deadline"):
            ocr_only_fields = dict(proposed_fields)
            ocr_only_fields["next_action_summary"] = None
            return {**common, "proposed_fields": ocr_only_fields, "status": "OCR_ONLY_REVIEW_PACKET", "reason": "NATIVE_TEXT_UNAVAILABLE_OR_INSUFFICIENT"}
        incomplete_fields = dict(proposed_fields)
        incomplete_fields["next_action_summary"] = None
        return {**common, "proposed_fields": incomplete_fields, "status": "PARTIAL_REVIEW_PACKET", "reason": "OCR_PRESENT_BUT_CRITICAL_FIELDS_INCOMPLETE"}

    required_native = [
        key
        for key in (
            "tender_form_sale_close",
            "tender_form_sale_close_time",
            "site_survey_date",
            "proposed_deadline",
            "tender_submission_start_time",
            "proposed_deadline_time",
        )
        if native_fields.get(key)
    ]
    corroborated = all(field_statuses.get(key) == "AGREED" for key in required_native)
    if proposed_fields.get("proposed_deadline") and corroborated and sha_abc_match:
        return {**common, "status": "DUAL_EVIDENCE_REVIEW_READY", "reason": None}
    review_fields = dict(proposed_fields)
    review_fields["next_action_summary"] = None
    return {**common, "proposed_fields": review_fields, "status": "DUAL_EVIDENCE_REVIEW_REQUIRED", "reason": "OCR_DID_NOT_CORROBORATE_ALL_NATIVE_CRITICAL_FIELDS"}
