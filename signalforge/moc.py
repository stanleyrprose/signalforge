from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from .mpt import normalize_text

MOC_TENDER_URL = "https://construction.gov.mm/tindar-show/f878a520-d396-11ec-957c-cb8c3b494625?state_name=all"
MOC_ISSUER = "Ministry of Construction, Myanmar"
MOC_HOSTS = {"construction.gov.mm", "www.construction.gov.mm"}
SELECTION_POLICY_VERSION = 1

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_VOID_TAGS = {"area", "base", "br", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_TENDER_TOKENS = ("တင်ဒါ", "tender")
_EXCLUDE_TOKENS = ("award", "winner", "result", "တင်ဒါအောင်", "အောင်မြင်")
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_DATE_RE = re.compile(r"(?P<day>\d{1,2})\s*[-./]\s*(?P<month>\d{1,2})\s*[-./]\s*(?P<year>20\d{2})")
_TIME_RE = re.compile(r"(?P<hour>\d{1,2})\s*:\s*(?P<minute>\d{2})")


class MocParseError(ValueError):
    pass


def _classes(attrs) -> set[str]:  # type: ignore[no-untyped-def]
    for key, value in attrs:
        if key == "class" and value:
            return set(str(value).split())
    return set()


def _attr(attrs, name: str) -> str | None:  # type: ignore[no-untyped-def]
    for key, value in attrs:
        if key == name and value is not None:
            return str(value)
    return None


def _is_tender_title(value: str) -> bool:
    text = normalize_text(value)
    lower = text.lower()
    if not text or any(token.lower() in lower for token in _EXCLUDE_TOKENS):
        return False
    return any(token.lower() in lower for token in _TENDER_TOKENS)


def _canonical_download_url(raw_url: str, page_url: str = MOC_TENDER_URL) -> tuple[str, str] | None:
    absolute = urljoin(page_url, raw_url)
    parsed = urlsplit(absolute)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in MOC_HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        return None
    match = re.fullmatch(r"/letter-download/([0-9a-fA-F-]+)", parsed.path.rstrip("/"))
    if match is None or _UUID_RE.fullmatch(match.group(1)) is None:
        return None
    record_id = match.group(1).lower()
    return record_id, f"https://construction.gov.mm/letter-download/{record_id}"


def _canonical_pdf_url(raw_url: str | None, page_url: str = MOC_TENDER_URL) -> str | None:
    if not raw_url:
        return None
    absolute = urljoin(page_url, raw_url)
    parsed = urlsplit(absolute)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in MOC_HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/storage/TinDar/")
        or not parsed.path.lower().endswith(".pdf")
    ):
        return None
    return absolute


def _deadline(value: str) -> str | None:
    text = normalize_text(value)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


@dataclass(frozen=True)
class MocTender:
    record_id: str
    title: str
    deadline: str
    location: str
    url: str
    attachment_url: str | None
    scope_summary: str | None = None
    quantity_or_lot_summary: str | None = None
    deadline_time: str | None = None
    document_ocr_status: str | None = None
    document_ocr_input_sha256: str | None = None
    document_ocr_provider_request_id: str | None = None
    document_ocr_mean_confidence: float | None = None
    customer_readiness_excluded_reason: str | None = None

    item_kind = "TENDER"
    publication_date = None

    @property
    def canonical_key(self) -> str:
        return f"moc:{self.record_id}"

    @property
    def reference_no(self) -> str:
        # The listing exposes a stable issuer UUID but no human tender number.
        return self.record_id

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": MOC_ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_tender_uuid",
            "source_record_id": self.record_id,
            "publication_date": None,
            "deadline": self.deadline,
            "deadline_time": self.deadline_time,
            "deadline_kind": "TENDER_END_DATE",
            "deadline_evidence": (
                "EXPLICIT_OFFICIAL_LISTING_END_DATE_PLUS_DOCUMENT_OCR_TIME"
                if self.deadline_time else "EXPLICIT_OFFICIAL_LISTING_END_DATE"
            ),
            "location": self.location,
            "location_evidence": "OFFICIAL_LISTING_REGION_BADGE",
            "scope_summary": self.scope_summary or self.title,
            "quantity_or_lot_summary": self.quantity_or_lot_summary,
            "quantity_or_lot_evidence": "OFFICIAL_PDF_DOCUMENT_OCR" if self.quantity_or_lot_summary else None,
            "quantity_or_lot_confidence": "OCR_CROSSCHECKED_WITH_LISTING" if self.quantity_or_lot_summary else None,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": (
                "LISTING_PLUS_OFFICIAL_PDF_DOCUMENT_OCR"
                if self.document_ocr_status == "CROSSCHECKED" else "LISTING_TITLE_REGION_END_DATE_OFFICIAL_DOWNLOAD"
            ),
            "attachment_policy": "DOCUMENT_OCR_ENRICHMENT_FAIL_CLOSED",
            "attachment_url": self.attachment_url,
            "document_ocr_status": self.document_ocr_status,
            "document_ocr_input_sha256": self.document_ocr_input_sha256,
            "document_ocr_provider_request_id": self.document_ocr_provider_request_id,
            "document_ocr_mean_confidence": self.document_ocr_mean_confidence,
            "customer_readiness_excluded_reason": self.customer_readiness_excluded_reason,
            "url": self.url,
        }




def document_ocr_url(record: object) -> str | None:
    return record.attachment_url if isinstance(record, MocTender) else None


def _normalized_ocr_text(value: object) -> str:
    return normalize_text(str(value or "").translate(_MYANMAR_DIGITS))


def _deadline_time_from_ocr(text: str, deadline: str) -> str | None:
    try:
        expected = datetime.strptime(deadline, "%Y-%m-%d").date()
    except ValueError:
        return None
    for match in _DATE_RE.finditer(text):
        try:
            found = datetime(
                int(match.group("year")), int(match.group("month")), int(match.group("day"))
            ).date()
        except ValueError:
            continue
        if found != expected:
            continue
        window = text[match.end(): match.end() + 140]
        time_match = _TIME_RE.search(window)
        if time_match:
            hour = int(time_match.group("hour"))
            minute = int(time_match.group("minute"))
            context = window[: time_match.end()]
            if ("ညနေ" in context or "pm" in context.lower()) and 1 <= hour <= 11:
                hour += 12
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}"
    return None


def _business_fields_from_ocr(text: str) -> tuple[str | None, str | None, str | None]:
    # These are deliberately conservative source-specific patterns. Unknown
    # shapes remain incomplete and are blocked by the Telegram readiness gate.
    if "အမြန်လမ်း" in text and "သန့်စင်ခန်း" in text:
        total = re.search(r"သန့်စင်ခန်း\s*\(\s*(\d+)\s*\)\s*နေရာ", text)
        if total:
            count = int(total.group(1))
            scope = (
                "ရန်ကုန်-မန္တလေးအမြန်လမ်းရှိ Rest Camp သန့်စင်ခန်းများအတွက် "
                "ဝန်ဆောင်မှုလုပ်ငန်း လုပ်ကိုင်ခွင့်/ငှားရမ်းခ ပေးသွင်းရေး တင်ဒါ"
            )
            return (
                scope,
                f"Rest Camp သန့်စင်ခန်းဝန်ဆောင်မှု စုစုပေါင်း {count} နေရာ",
                "NON_PROCUREMENT_SERVICE_CONCESSION",
            )
    if "ရတနာသိင်္ခ" in text and "ပြန်လည်ပြုပြင်တည်ဆောက်" in text:
        feet_match = re.search(r"တံတား\s*\(\s*(\d+)\s*ပေ\s*\)", text)
        million_match = re.search(r"ကျပ်သန်း\s*\(\s*(\d+)\s*\)", text)
        scale_parts: list[str] = []
        if feet_match:
            scale_parts.append(f"တံတားအရှည် {int(feet_match.group(1)):,} ပေ")
        if million_match:
            scale_parts.append(f"ကျပ်သန်း {int(million_match.group(1)):,} အထက်/အောက် ပစ္စည်း package")
        scope = (
            "ရတနာသိင်္ခတံတား ပြန်လည်ပြုပြင်တည်ဆောက်ရေးအတွက် "
            "ဆောက်လုပ်ရေးပစ္စည်း ဝယ်ယူ/သယ်ယူပို့ဆောင်ရေးနှင့် စက်/ယာဉ်ယန္တရား ငှားရမ်းခြင်း"
        )
        return scope, "；".join(scale_parts) if scale_parts else None, None
    return None, None, None


def enrich_tender_with_document_ocr(record: object, ocr: dict[str, object]) -> object:
    if not isinstance(record, MocTender) or not record.attachment_url:
        return record
    text = _normalized_ocr_text(ocr.get("text"))
    input_sha256 = str(ocr.get("input_sha256") or "")
    provider_request_id = str(ocr.get("provider_request_id") or "")
    confidence = ocr.get("mean_confidence")
    if (
        not text
        or len(input_sha256) != 64
        or not provider_request_id
        or not isinstance(confidence, (int, float))
        or float(confidence) < 55.0
    ):
        return record
    deadline_time = _deadline_time_from_ocr(text, record.deadline)
    if deadline_time is None:
        # Listing/PDF date agreement is mandatory before OCR may enrich
        # customer-facing business fields.
        return record
    scope, quantity, excluded_reason = _business_fields_from_ocr(text)
    if not scope or not quantity:
        return record
    return replace(
        record,
        scope_summary=scope,
        quantity_or_lot_summary=quantity,
        deadline_time=deadline_time,
        document_ocr_status="CROSSCHECKED",
        document_ocr_input_sha256=input_sha256,
        document_ocr_provider_request_id=provider_request_id,
        document_ocr_mean_confidence=round(float(confidence), 2),
        customer_readiness_excluded_reason=excluded_reason,
    )


def restore_tender_from_payload(record: object, payload: dict[str, object]) -> object:
    if not isinstance(record, MocTender):
        return record
    if (
        payload.get("attachment_url") != record.attachment_url
        or payload.get("document_ocr_status") != "CROSSCHECKED"
        or not payload.get("scope_summary")
        or not payload.get("quantity_or_lot_summary")
    ):
        return record
    return replace(
        record,
        scope_summary=str(payload["scope_summary"]),
        quantity_or_lot_summary=str(payload["quantity_or_lot_summary"]),
        deadline_time=str(payload.get("deadline_time") or "") or None,
        document_ocr_status="CROSSCHECKED",
        document_ocr_input_sha256=str(payload.get("document_ocr_input_sha256") or "") or None,
        document_ocr_provider_request_id=str(payload.get("document_ocr_provider_request_id") or "") or None,
        document_ocr_mean_confidence=(
            float(payload["document_ocr_mean_confidence"])
            if isinstance(payload.get("document_ocr_mean_confidence"), (int, float)) else None
        ),
        customer_readiness_excluded_reason=(
            str(payload.get("customer_readiness_excluded_reason") or "") or None
        ),
    )


@dataclass(frozen=True)
class _Card:
    title: str
    region: str
    deadline: str
    download_href: str
    pdf_href: str | None


class _TenderBoardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[_Card] = []
        self.card_count = 0
        self._card_depth = 0
        self._title_depth = 0
        self._region_depth = 0
        self._deadline_depth = 0
        self._title_parts: list[str] = []
        self._region_parts: list[str] = []
        self._deadline_parts: list[str] = []
        self._download_href: str | None = None
        self._pdf_href: str | None = None

    def _reset(self) -> None:
        self._title_depth = 0
        self._region_depth = 0
        self._deadline_depth = 0
        self._title_parts = []
        self._region_parts = []
        self._deadline_parts = []
        self._download_href = None
        self._pdf_href = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if not self._card_depth:
            if lowered == "div" and {"card", "shadow"}.issubset(classes):
                self._card_depth = 1
                self.card_count += 1
                self._reset()
            return

        if lowered not in _VOID_TAGS:
            self._card_depth += 1

        if lowered == "h5" and "card-title" in classes:
            self._title_depth = 1
        elif lowered == "span" and {"badge", "bg-warning"}.issubset(classes):
            self._region_depth = 1
        elif lowered == "span" and {"badge", "bg-success"}.issubset(classes):
            self._deadline_depth = 1
        elif lowered == "a":
            href = _attr(attrs, "href")
            if href and "download-btn" in classes:
                self._download_href = href
            elif href and "custom_canvas" in classes:
                self._pdf_href = href

        for field in ("_title_depth", "_region_depth", "_deadline_depth"):
            value = getattr(self, field)
            if value and not (
                (field == "_title_depth" and lowered == "h5" and "card-title" in classes)
                or (field == "_region_depth" and lowered == "span" and {"badge", "bg-warning"}.issubset(classes))
                or (field == "_deadline_depth" and lowered == "span" and {"badge", "bg-success"}.issubset(classes))
            ) and lowered not in _VOID_TAGS:
                setattr(self, field, value + 1)

    def handle_endtag(self, tag: str) -> None:
        if not self._card_depth:
            return
        lowered = tag.lower()
        for field in ("_title_depth", "_region_depth", "_deadline_depth"):
            value = getattr(self, field)
            if value and lowered not in _VOID_TAGS:
                setattr(self, field, value - 1)
        if lowered not in _VOID_TAGS:
            self._card_depth -= 1
        if self._card_depth == 0:
            self._finish()

    def handle_data(self, data: str) -> None:
        if not self._card_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self._title_parts.append(value)
        if self._region_depth:
            self._region_parts.append(value)
        if self._deadline_depth:
            self._deadline_parts.append(value)

    def _finish(self) -> None:
        title = normalize_text(" ".join(self._title_parts))
        region = normalize_text(" ".join(self._region_parts))
        deadline = normalize_text(" ".join(self._deadline_parts))
        if title and region and deadline and self._download_href:
            self.cards.append(_Card(title, region, deadline, self._download_href, self._pdf_href))
        self._reset()


def parse_tender_records(payload: bytes, page_url: str = MOC_TENDER_URL) -> list[MocTender]:
    if page_url != MOC_TENDER_URL:
        raise MocParseError("unexpected Ministry of Construction listing URL")

    parser = _TenderBoardParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise MocParseError("Ministry of Construction tender cards not found")

    records: list[MocTender] = []
    seen: set[str] = set()
    for card in parser.cards:
        if not _is_tender_title(card.title):
            continue
        identity = _canonical_download_url(card.download_href, page_url)
        deadline = _deadline(card.deadline)
        if identity is None or deadline is None:
            continue
        record_id, download_url = identity
        if record_id in seen:
            continue
        seen.add(record_id)
        records.append(
            MocTender(
                record_id=record_id,
                title=card.title,
                deadline=deadline,
                location=card.region,
                url=download_url,
                attachment_url=_canonical_pdf_url(card.pdf_href, page_url),
            )
        )

    if not records:
        raise MocParseError("Ministry of Construction listing had no valid tender records")
    return records
