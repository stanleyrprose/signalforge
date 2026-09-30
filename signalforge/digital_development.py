from __future__ import annotations

import io
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from pypdf import PdfReader

from .mpt import SitemapEntry, normalize_text, parse_date
from .national_portal import (
    NATIONAL_PORTAL_HOSTS,
    NATIONAL_PORTAL_TENDER_URL,
    _TenderCardParser,
    _canonical_url,
)

ISSUER = "Digital Development Department, Ministry of Digital Development and Communications, Myanmar"
SELECTION_POLICY_VERSION = 1
_DDD_TITLE_TOKEN = "ဒီဂျစ်တယ်ဖွံ့ဖြိုးတိုးတက်ရေးဦးစီးဌာန"
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_REFERENCE_RE = re.compile(r"DD\s*[-–—]\s*(?P<number>\d+)\s*/\s*(?P<year>20\d{2})", re.I)
_DATE_RE = re.compile(r"(?<!\d)(?P<day>\d{1,2})\s*[-./]\s*(?P<month>\d{1,2})\s*[-./]\s*(?P<year>20\d{2})(?!\d)")
_TIME_RE = re.compile(r"[（(]?\s*(?P<hour>\d{1,2})\s*:\s*(?P<minute>\d{2})")


class DigitalDevelopmentParseError(ValueError):
    pass


def _is_portal_document(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() in NATIONAL_PORTAL_HOSTS
        and parsed.path.startswith("/documents/")
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
        and not parsed.fragment
    )


def parse_digital_development_listing(
    html_bytes: bytes,
    base_url: str = NATIONAL_PORTAL_TENDER_URL,
) -> list[SitemapEntry]:
    """Discover only Digital Development Department issuer documents.

    Portal card Closing Date is used solely as discovery freshness metadata.
    It is never business truth for the canonical Tender.
    """

    parser = _TenderCardParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if not parser.rows:
        raise DigitalDevelopmentParseError("Myanmar National Portal tender cards not found")

    entries: dict[str, SitemapEntry] = {}
    for row in parser.rows:
        title = normalize_text(row["title"])
        compact_title = re.sub(r"\s+", "", title)
        if _DDD_TITLE_TOKEN not in compact_title:
            continue
        url = _canonical_url(row["href"], base_url)
        if url is None or not _is_portal_document(url):
            continue
        closing_hint = parse_date(row["closing"])
        lastmod = f"{closing_hint}T00:00:00+06:30" if closing_hint else None
        entries.setdefault(url, SitemapEntry(url=url, lastmod=lastmod))
    return list(entries.values())


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _iso_date(match: re.Match[str]) -> str:
    return f"{int(match.group('year')):04d}-{int(match.group('month')):02d}-{int(match.group('day')):02d}"


_ITEM_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bswitch(?:es)?\b", re.I), "Switch"),
    (re.compile(r"\bfirewalls?\b", re.I), "Firewall"),
    (re.compile(r"\brouters?\b", re.I), "Router"),
    (re.compile(r"\bservers?\b", re.I), "Server"),
    (re.compile(r"\bstorage\b", re.I), "Storage"),
    (re.compile(r"\bups\b", re.I), "UPS"),
    (re.compile(r"\bbatter(?:y|ies)\b", re.I), "Battery"),
    (re.compile(r"\bsoftware\b", re.I), "Software"),
    (re.compile(r"\blicen[cs]e(?:s)?\b", re.I), "Software license"),
    (re.compile(r"\b(?:fiber|fibre)\b", re.I), "Fiber"),
    (re.compile(r"\bdata\s+cent(?:er|re)\b", re.I), "Data center"),
    (re.compile(r"\bhardware\b", re.I), "ICT hardware"),
    (re.compile(r"\bnetwork(?:ing)?\b", re.I), "Network equipment"),
    (re.compile(r"\bcomputers?\b", re.I), "Computer"),
    (re.compile(r"\blaptops?\b", re.I), "Laptop"),
    (re.compile(r"\bdesktops?\b", re.I), "Desktop"),
    (re.compile(r"\bprinters?\b", re.I), "Printer"),
    (re.compile(r"\bcctv\b", re.I), "CCTV"),
)
_QUANTITY_RE = re.compile(
    r"(?<!\d)[(（]?\s*(?P<count>\d[\d,]*)\s*[)）]?\s*"
    r"(?P<unit>lots?|units?|sets?|nos?|items?|pcs?|pieces?|ခု|လုံး|စုံ|မျိုး)\b",
    re.I,
)
_FEE_RE = re.compile(
    r"(?:ကျသ.{0,80}?|tender\s+form\s+fee.{0,50}?)(?P<amount>\d{1,3}(?:,\d{3})+|\d+)",
    re.I,
)


def _scope_segment(normalized: str, reference_match: re.Match[str], first_schedule: re.Match[str]) -> str:
    return normalize_text(normalized[reference_match.end():first_schedule.start()])[:1200]


def _clean_scope_summary(raw_scope: str, item: str) -> str:
    supply = re.search(
        r"\bSupply\s+of\s+(.{8,300}?)(?=\s+အတွက်|\s+တင်ဒါ|$)",
        raw_scope,
        re.I,
    )
    if supply:
        base = normalize_text("Supply of " + supply.group(1))
        if item.lower() not in base.lower():
            return f"{base}; procurement item: {item}."
        return f"{base}."
    return f"Digital Development Department procurement item: {item}."


def _detect_procurement_item(scope: str) -> str | None:
    for pattern, label in _ITEM_PATTERNS:
        if pattern.search(scope):
            return label
    return None


def _title_from_scope(scope: str, item: str, reference_no: str) -> str:
    match = re.search(r"\bSupply\s+of\s+(.{8,260}?)(?=\s+အတွက်|\s+တင်ဒါ|$)", scope, re.I)
    if match:
        title = normalize_text("Supply of " + match.group(1))
        if item.lower() not in title.lower():
            title = f"{title} — {item}"
        return title[:280]
    return f"{item} procurement ({reference_no})"


def _quantity_summary(scope: str, item: str) -> tuple[str, str]:
    match = _QUANTITY_RE.search(scope)
    if match:
        count = normalize_text(match.group("count"))
        unit = normalize_text(match.group("unit"))
        return f"{count} {unit}", "HIGH"
    return f"Official public notice does not disclose the unit/lot quantity for {item}.", "HIGH"


def _location_from_text(normalized: str) -> str | None:
    if any(token in normalized for token in ("နေပြည်တော်", "ရေပပည်ရတာ်", "ရနမပည်ရတာ်")):
        return "Nay Pyi Taw"
    if "ရန်ကုန်" in normalized:
        return "Yangon"
    if "မန္တလေး" in normalized:
        return "Mandalay"
    return None


@dataclass(frozen=True)
class DigitalDevelopmentTender:
    reference_no: str
    title: str
    scope_summary: str
    quantity_or_lot_summary: str
    quantity_or_lot_confidence: str
    deadline: str
    deadline_time: str
    sale_start_date: str | None
    sale_close_date: str | None
    tender_document_fee_mmk: int | None
    location: str | None
    url: str

    item_kind = "TENDER"
    publication_date = None

    @property
    def canonical_key(self) -> str:
        return f"digital-development:{self.reference_no.lower()}"

    @property
    def reference_no_kind(self) -> str:
        return "issuer_tender_number"

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        action_parts: list[str] = []
        if self.sale_start_date and self.sale_close_date:
            action_parts.append(
                f"Tender forms are sold from {self.sale_start_date} through {self.sale_close_date}."
            )
        if self.tender_document_fee_mmk is not None:
            action_parts.append(f"Tender form fee: MMK {self.tender_document_fee_mmk:,}.")
        place = f" in {self.location}" if self.location else ""
        action_parts.append(f"Submit the bid by {self.deadline} {self.deadline_time}{place}.")
        return {
            "item_kind": self.item_kind,
            "issuer": ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": self.reference_no_kind,
            "identity_material": "issuer_tender_number",
            "publication_date": None,
            "deadline": self.deadline,
            "deadline_time": self.deadline_time,
            "deadline_kind": "BID_SUBMISSION_DEADLINE",
            "deadline_evidence": "ISSUER_AUTHORED_OFFICIAL_TEXT_NATIVE_PDF",
            "location": self.location,
            "location_evidence": "ISSUER_AUTHORED_OFFICIAL_TEXT_NATIVE_PDF" if self.location else None,
            "scope_summary": self.scope_summary,
            "scope_excerpt": self.scope_summary,
            "quantity_or_lot_summary": self.quantity_or_lot_summary,
            "quantity_or_lot_evidence": "ISSUER_AUTHORED_OFFICIAL_TEXT_NATIVE_PDF",
            "quantity_or_lot_confidence": self.quantity_or_lot_confidence,
            "tender_form_sale_start_date": self.sale_start_date,
            "tender_form_sale_close_date": self.sale_close_date,
            "tender_document_fee_mmk": self.tender_document_fee_mmk,
            "price_or_budget_summary": (
                f"Procurement budget not disclosed; tender form fee: MMK {self.tender_document_fee_mmk:,}."
                if self.tender_document_fee_mmk is not None
                else "Procurement budget not disclosed in the public notice."
            ),
            "next_action_summary": " ".join(action_parts),
            "next_action_evidence": "ISSUER_AUTHORED_OFFICIAL_TEXT_NATIVE_PDF",
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "ISSUER_PDF_SCOPE_ITEM_SCHEDULE_FEE_LOCATION",
            "evidence_level": "OFFICIAL_TEXT_PDF",
            "document_authority": "ISSUER_AUTHORED_PDF_VIA_OFFICIAL_NATIONAL_PORTAL",
            "portal_card_closing_date_authority": "HINT_ONLY_NOT_CANONICAL",
            "url": self.url,
        }


def parse_digital_development_text(text: str, url: str) -> DigitalDevelopmentTender | None:
    if not _is_portal_document(url):
        raise DigitalDevelopmentParseError("Digital Development Tender requires official Portal /documents/ URL")

    normalized = normalize_text(text.translate(_MYANMAR_DIGITS))
    if "ဒီဂျစ်တယ်" not in normalized:
        return None

    reference_match = _REFERENCE_RE.search(normalized)
    if reference_match is None:
        return None
    reference_no = f"DD-{int(reference_match.group('number'))}/{reference_match.group('year')}"

    schedule_matches = list(_DATE_RE.finditer(normalized))
    if len(schedule_matches) < 3:
        raise DigitalDevelopmentParseError("DDD tender sale/submission schedule incomplete")
    sale_start_date = _iso_date(schedule_matches[0])
    sale_close_date = _iso_date(schedule_matches[1])

    deadline = None
    deadline_time = None
    for index, match in enumerate(schedule_matches[2:], start=2):
        candidate = _iso_date(match)
        if candidate < sale_close_date:
            continue
        next_start = schedule_matches[index + 1].start() if index + 1 < len(schedule_matches) else min(len(normalized), match.end() + 240)
        segment = normalized[match.end():next_start]
        time_match = _TIME_RE.search(segment)
        if time_match is None:
            continue
        hour = int(time_match.group("hour"))
        minute = int(time_match.group("minute"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            continue
        deadline = candidate
        deadline_time = f"{hour:02d}:{minute:02d}"
        break
    if deadline is None or deadline_time is None:
        raise DigitalDevelopmentParseError("DDD bid submission deadline not found")
    if not (sale_start_date <= sale_close_date <= deadline):
        raise DigitalDevelopmentParseError("DDD tender schedule order invalid")

    raw_scope = _scope_segment(normalized, reference_match, schedule_matches[0])
    item = _detect_procurement_item(raw_scope)
    if not raw_scope or item is None:
        return None
    scope = _clean_scope_summary(raw_scope, item)
    title = _title_from_scope(raw_scope, item, reference_no)
    quantity_summary, quantity_confidence = _quantity_summary(raw_scope, item)

    fee = None
    fee_match = _FEE_RE.search(normalized)
    if fee_match:
        try:
            fee = int(fee_match.group("amount").replace(",", ""))
        except ValueError:
            fee = None

    return DigitalDevelopmentTender(
        reference_no=reference_no,
        title=title,
        scope_summary=scope,
        quantity_or_lot_summary=quantity_summary,
        quantity_or_lot_confidence=quantity_confidence,
        deadline=deadline,
        deadline_time=deadline_time,
        sale_start_date=sale_start_date,
        sale_close_date=sale_close_date,
        tender_document_fee_mmk=fee,
        location=_location_from_text(normalized),
        url=url,
    )


def parse_digital_development_pdf(pdf_bytes: bytes, url: str) -> DigitalDevelopmentTender | None:
    if not pdf_bytes.startswith(b"%PDF-"):
        raise DigitalDevelopmentParseError("Digital Development detail is not PDF")
    text = _extract_pdf_text(pdf_bytes)
    if len(normalize_text(text)) < 100:
        raise DigitalDevelopmentParseError("Digital Development PDF text layer is insufficient")
    return parse_digital_development_text(text, url)
