from __future__ import annotations

import io
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlparse
from zoneinfo import ZoneInfo

from pypdf import PdfReader

from .mpt import normalize_text

MPA_LISTING_URL = "https://www.mpa.gov.mm/tenders-and-announcement/"
MPA_HOSTS = {"mpa.gov.mm", "www.mpa.gov.mm"}
_DATE_RE = re.compile(r"^(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>20\d{2})$")
_SHORTLINK_RE = re.compile(r"https://www\.mpa\.gov\.mm/\?p=(?P<post_id>\d+)$")


class MpaParseError(ValueError):
    pass


def _attr(attrs, name: str) -> str | None:  # type: ignore[no-untyped-def]
    for key, value in attrs:
        if key == name and value is not None:
            return str(value)
    return None


def _classes(attrs) -> set[str]:  # type: ignore[no-untyped-def]
    value = _attr(attrs, "class")
    return set(value.split()) if value else set()


def _parse_date(value: str) -> str | None:
    text = normalize_text(value)
    match = _DATE_RE.fullmatch(text)
    if match is None:
        return None
    try:
        parsed = date(int(match.group("year")), int(match.group("month")), int(match.group("day")))
    except ValueError:
        return None
    return parsed.isoformat()


def _normalize_record_url(raw_url: str, page_url: str = MPA_LISTING_URL) -> str | None:
    url = urljoin(page_url, raw_url)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in MPA_HOSTS:
        return None
    marker = "/announcements/"
    if marker not in parsed.path:
        return None
    encoded_slug = parsed.path.split(marker, 1)[1].strip("/")
    slug = unquote(encoded_slug).strip("/")
    if not slug:
        return None
    return f"https://www.mpa.gov.mm/announcements/{encoded_slug}/"


def _slug(url: str) -> str:
    return unquote(urlparse(url).path.rstrip("/").rsplit("/", 1)[-1])


def classify_item_kind(title: str) -> str:
    text = normalize_text(title)
    lowered = text.lower()
    disposal_tokens = (
        "လေလံ",
        "ရောင်းချ",
        "စာရင်းမှ ပယ်ဖျက်",
        "စာရင်းမှပယ်ဖျက်",
        "မလိုအပ်တော့",
        "သံတိုသံစအဟောင်း",
        "ကုန်သေတ္တာအခွံ",
    )
    if "auction" in lowered or any(token in text for token in disposal_tokens):
        return "AUCTION_NOTICE"
    if "တင်ဒါ" in text or "tender" in lowered:
        return "TENDER"
    return "UNCLASSIFIED"


@dataclass(frozen=True)
class MpaListingRecord:
    publication_date: str
    title: str
    url: str
    provisional_item_kind: str
    provisional_source_id: str
    identity_status: str = "PROVISIONAL_SLUG"
    classification_status: str = "TITLE_ONLY_REQUIRES_DETAIL_PDF"
    wordpress_post_id: int | None = None

    def preview_payload(self) -> dict[str, object]:
        return asdict(self)


class _MpaListingParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.records: list[MpaListingRecord] = []
        self._row_depth = 0
        self._cell_depth = 0
        self._cell_classes: set[str] = set()
        self._cell_parts: list[str] = []
        self._date_text: str | None = None
        self._href: str | None = None
        self._link_depth = 0
        self._link_parts: list[str] = []

    def _reset_row(self) -> None:
        self._cell_depth = 0
        self._cell_classes = set()
        self._cell_parts = []
        self._date_text = None
        self._href = None
        self._link_depth = 0
        self._link_parts = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        if lowered == "tr":
            if self._row_depth == 0:
                self._reset_row()
            self._row_depth += 1
            return
        if not self._row_depth:
            return
        if lowered == "td":
            self._cell_depth = 1
            self._cell_classes = _classes(attrs)
            self._cell_parts = []
            return
        if self._cell_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._cell_depth += 1
        if lowered == "a" and "ps-4" in self._cell_classes:
            href = _attr(attrs, "href")
            self._href = _normalize_record_url(href, self.page_url) if href else None
            self._link_depth = 1
            self._link_parts = []
        elif self._link_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._link_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._row_depth:
            return
        if self._link_depth:
            if lowered == "a":
                self._link_depth = 0
            else:
                self._link_depth = max(0, self._link_depth - 1)
        if self._cell_depth:
            if lowered == "td":
                text = normalize_text(" ".join(self._cell_parts))
                if "text-center" in self._cell_classes and _parse_date(text):
                    self._date_text = text
                self._cell_depth = 0
                self._cell_classes = set()
                self._cell_parts = []
            else:
                self._cell_depth = max(0, self._cell_depth - 1)
        if lowered == "tr":
            self._row_depth -= 1
            if self._row_depth == 0:
                self._finish_row()

    def handle_data(self, data: str) -> None:
        if not self._row_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._cell_depth:
            self._cell_parts.append(value)
        if self._link_depth:
            self._link_parts.append(value)

    def _finish_row(self) -> None:
        publication_date = _parse_date(self._date_text or "")
        title = normalize_text(" ".join(self._link_parts))
        if publication_date and self._href and title:
            self.records.append(
                MpaListingRecord(
                    publication_date=publication_date,
                    title=title,
                    url=self._href,
                    provisional_item_kind=classify_item_kind(title),
                    provisional_source_id=_slug(self._href),
                )
            )
        self._reset_row()


def parse_listing_records(html_bytes: bytes, page_url: str = MPA_LISTING_URL) -> list[MpaListingRecord]:
    parser = _MpaListingParser(page_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    dedup: dict[tuple[str, str], MpaListingRecord] = {}
    for record in parser.records:
        dedup.setdefault((record.publication_date, record.url), record)
    records = list(dedup.values())
    if not records:
        raise MpaParseError("no recognized MPA listing rows")
    return records


class _ShortlinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.post_id: int | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        if tag.lower() != "link":
            return
        rel = (_attr(attrs, "rel") or "").lower()
        href = _attr(attrs, "href")
        if rel != "shortlink" or not href:
            return
        match = _SHORTLINK_RE.fullmatch(href)
        if match:
            self.post_id = int(match.group("post_id"))


def extract_wordpress_post_id(detail_html: bytes) -> int:
    parser = _ShortlinkParser()
    parser.feed(detail_html.decode("utf-8", errors="replace"))
    if parser.post_id is None:
        raise MpaParseError("MPA detail page does not expose a WordPress shortlink post ID")
    return parser.post_id


class _PdfIframeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pdf_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        if tag.lower() != "iframe":
            return
        raw_url = _attr(attrs, "data-src") or _attr(attrs, "src")
        if not raw_url:
            return
        parsed = urlparse(raw_url)
        if parsed.scheme != "https" or parsed.netloc.lower() not in MPA_HOSTS:
            return
        if not parsed.path.lower().endswith(".pdf"):
            return
        self.pdf_urls.append(raw_url)


def extract_detail_pdf_url(detail_html: bytes) -> str:
    parser = _PdfIframeParser()
    parser.feed(detail_html.decode("utf-8", errors="replace"))
    unique = list(dict.fromkeys(parser.pdf_urls))
    if len(unique) != 1:
        raise MpaParseError(f"expected exactly one MPA detail PDF iframe, found {len(unique)}")
    return unique[0]


MAX_MPA_PDF_BYTES = 10 * 1024 * 1024
MAX_MPA_PDF_PAGES = 20
MAX_MPA_PDF_TEXT_CHARS = 100_000
_MYANMAR_DIGIT_TRANSLATION = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_DATE_TOKEN_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(20\d{2})(?!\d)")
_REFERENCE_RE = re.compile(r"\bMPA-[A-Z0-9&]+/\d{1,4}-\s*20\d{2}\b", re.IGNORECASE)

_DISPOSAL_SIGNALS: tuple[tuple[str, str], ...] = (
    ("auctioned", "AUCTION_EN"),
    ("auction", "AUCTION_EN"),
    ("disposal", "DISPOSAL_EN"),
    ("လေလံ", "AUCTION_MY"),
    ("ရောင်းချ", "SALE_MY"),
    ("စာရင်းမှ ပယ်ဖျက်", "DECOMMISSION_MY"),
    ("စာရင်းမှပယ်ဖျက်", "DECOMMISSION_MY"),
    ("မလိုအပ်တော့", "SURPLUS_MY"),
)
_PROCUREMENT_SIGNALS: tuple[tuple[str, str], ...] = (
    ("ဝယ်ယူ", "PURCHASE_MY"),
    ("ဝန်ဆောင်မှုရယူ", "SERVICE_MY"),
    ("ပြုပြင်", "REPAIR_MY"),
    ("တည်ဆောက်", "CONSTRUCTION_MY"),
    ("တပ်ဆင်", "INSTALLATION_MY"),
    ("procurement", "PROCUREMENT_EN"),
    ("purchase", "PURCHASE_EN"),
    ("supply", "SUPPLY_EN"),
    ("operation and maintenance", "SERVICE_EN"),
    ("maintenance", "MAINTENANCE_EN"),
    ("repair", "REPAIR_EN"),
    ("construction", "CONSTRUCTION_EN"),
    ("installation", "INSTALLATION_EN"),
    ("dredging", "DREDGING_EN"),
    ("infrastructure refreshment", "INFRA_REFRESH_EN"),
)


@dataclass(frozen=True)
class MpaPdfFields:
    final_item_kind: str | None
    classification_status: str
    classification_basis: str | None
    deadline_local: str | None
    deadline_timezone: str
    deadline_status: str
    reference_no: str | None
    scope_excerpt: str | None
    page_count: int
    text_chars: int

    def payload(self) -> dict[str, object]:
        return asdict(self)


def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, int]:
    if not pdf_bytes or len(pdf_bytes) > MAX_MPA_PDF_BYTES:
        raise MpaParseError(f"MPA PDF size outside allowed range: {len(pdf_bytes)} bytes")
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes), strict=False)
    except Exception as exc:  # pypdf exposes multiple parser exception types
        raise MpaParseError(f"unable to open MPA PDF: {type(exc).__name__}") from exc
    if reader.is_encrypted:
        raise MpaParseError("encrypted MPA PDF is not supported")
    page_count = len(reader.pages)
    if page_count < 1 or page_count > MAX_MPA_PDF_PAGES:
        raise MpaParseError(f"MPA PDF page count outside allowed range: {page_count}")
    parts: list[str] = []
    try:
        for page in reader.pages:
            parts.append(page.extract_text() or "")
    except Exception as exc:
        raise MpaParseError(f"unable to extract MPA PDF text: {type(exc).__name__}") from exc
    text = normalize_text(" ".join(parts))
    if len(text) < 80:
        raise MpaParseError(f"MPA PDF text too short for deterministic parsing: {len(text)} chars")
    if len(text) > MAX_MPA_PDF_TEXT_CHARS:
        raise MpaParseError(f"MPA PDF text exceeds deterministic parser limit: {len(text)} chars")
    return text, page_count


def _signal_match(text: str, signals: tuple[tuple[str, str], ...]) -> tuple[str, str, int] | None:
    lowered = text.lower()
    best: tuple[str, str, int] | None = None
    for token, label in signals:
        index = lowered.find(token.lower())
        if index < 0:
            continue
        candidate = (token, label, index)
        if best is None or index < best[2]:
            best = candidate
    return best


def classify_pdf_text(text: str) -> tuple[str | None, str, str | None, str | None]:
    disposal = _signal_match(text, _DISPOSAL_SIGNALS)
    if disposal is not None:
        token, basis, index = disposal
        start = max(0, index - 180)
        end = min(len(text), index + max(420, len(token) + 180))
        return "AUCTION_NOTICE", "DETERMINISTIC_PDF", basis, text[start:end]
    procurement = _signal_match(text, _PROCUREMENT_SIGNALS)
    if procurement is not None:
        token, basis, index = procurement
        start = max(0, index - 180)
        end = min(len(text), index + max(420, len(token) + 180))
        return "TENDER", "DETERMINISTIC_PDF", basis, text[start:end]
    return None, "REVIEW_REQUIRED", None, None


def _normalize_numeric_text(text: str) -> str:
    return text.translate(_MYANMAR_DIGIT_TRANSLATION).translate(str.maketrans({"−": "-", "–": "-", "—": "-"}))


def _deadline_candidate_score(before: str, after: str) -> int:
    before_lower = before.lower()
    after_lower = after.lower()
    before_compact = re.sub(r"\s+", "", before)
    after_compact = re.sub(r"\s+", "", after)
    score = 0
    for marker in ("to submit", "submission", "closing", "deadline", "not later", "latest"):
        if marker in before_lower:
            score += 8
        elif marker in after_lower:
            score += 4
    if "တင်သွင်" in before_compact:
        score += 8
    elif "တင်သွင်" in after_compact:
        score += 4
    if "နောက်ဆ" in after_compact:
        score += 5
    elif "နောက်ဆ" in before_compact:
        score += 3
    return score


def extract_deadline(text: str) -> tuple[str | None, str]:
    normalized = _normalize_numeric_text(text)
    candidates: list[tuple[int, datetime]] = []
    for match in _DATE_TOKEN_RE.finditer(normalized):
        day, month, year = (int(value) for value in match.groups())
        tail = normalized[match.end() : match.end() + 100]
        time_match = re.search(r"\(?\s*(\d{1,2})\s*:\s*(\d{2})\s*\)?", tail)
        if time_match is None:
            compact_time = re.search(r"\(\s*(\d{2})(\d{2})\s*\)", tail)
            if compact_time is None:
                continue
            hour, minute = (int(value) for value in compact_time.groups())
        else:
            hour, minute = (int(value) for value in time_match.groups())
        try:
            value = datetime(year, month, day, hour, minute)
        except ValueError:
            continue
        before = normalized[max(0, match.start() - 90) : match.start()]
        after = normalized[match.end() : min(len(normalized), match.end() + 90)]
        candidates.append((_deadline_candidate_score(before, after), value))
    if not candidates:
        return None, "NOT_FOUND"
    best_score = max(score for score, _value in candidates)
    best = sorted({value for score, value in candidates if score == best_score})
    if len(best) != 1:
        return None, "AMBIGUOUS"
    return best[0].isoformat(timespec="seconds"), "FOUND"


def extract_reference_no(text: str) -> str | None:
    normalized = _normalize_numeric_text(text)
    match = _REFERENCE_RE.search(normalized)
    if match is None:
        return None
    return re.sub(r"-\s+(20\d{2})$", r"-\1", match.group(0))


def parse_pdf_business_fields(pdf_bytes: bytes) -> MpaPdfFields:
    text, page_count = extract_pdf_text(pdf_bytes)
    final_item_kind, classification_status, classification_basis, scope_excerpt = classify_pdf_text(text)
    deadline_local, deadline_status = extract_deadline(text)
    return MpaPdfFields(
        final_item_kind=final_item_kind,
        classification_status=classification_status,
        classification_basis=classification_basis,
        deadline_local=deadline_local,
        deadline_timezone="Asia/Yangon",
        deadline_status=deadline_status,
        reference_no=extract_reference_no(text),
        scope_excerpt=scope_excerpt,
        page_count=page_count,
        text_chars=len(text),
    )


def build_manual_bundle_preview(
    listing_html: bytes,
    detail_html: bytes,
    pdf_bytes: bytes,
    *,
    detail_url: str,
    pdf_url: str,
) -> dict[str, object]:
    records = [record for record in parse_listing_records(listing_html) if record.url == detail_url]
    if len(records) != 1:
        raise MpaParseError(f"expected exactly one listing row for detail URL, found {len(records)}")
    record = records[0]
    post_id = extract_wordpress_post_id(detail_html)
    expected_pdf_url = extract_detail_pdf_url(detail_html)
    if pdf_url != expected_pdf_url:
        raise MpaParseError("manual bundle PDF URL does not match detail-page issuer PDF locator")
    fields = parse_pdf_business_fields(pdf_bytes)
    deadline = None
    if fields.deadline_local is not None:
        deadline = datetime.fromisoformat(fields.deadline_local).replace(tzinfo=ZoneInfo("Asia/Yangon")).isoformat()
    reference_no = fields.reference_no or f"MPA-POST-{post_id}"
    reference_no_kind = "issuer_reference_no" if fields.reference_no else "wordpress_post_id"
    candidate = {
        "canonical_key": f"mpa:{post_id}",
        "item_kind": fields.final_item_kind,
        "title": record.title,
        "project_name": record.title,
        "publication_date": record.publication_date,
        "deadline": deadline,
        "location": None,
        "url": detail_url,
        "pdf_url": pdf_url,
        "reference_no": reference_no,
        "reference_no_kind": reference_no_kind,
        "source_record_id": str(post_id),
        "scope_excerpt": fields.scope_excerpt,
        "classification_status": fields.classification_status,
        "classification_basis": fields.classification_basis,
        "deadline_status": fields.deadline_status,
        "listing_provisional_item_kind": record.provisional_item_kind,
    }
    return {
        "status": "READY_FOR_MANUAL_COMMIT" if fields.final_item_kind is not None else "REVIEW_REQUIRED",
        "source_id": "S15A",
        "identity_status": "WORDPRESS_POST_ID",
        "candidate": candidate,
        "pdf_fields": fields.payload(),
    }


def preview_summary(records: list[MpaListingRecord]) -> dict[str, object]:
    counts = {"TENDER": 0, "AUCTION_NOTICE": 0, "UNCLASSIFIED": 0}
    for record in records:
        counts[record.provisional_item_kind] = counts.get(record.provisional_item_kind, 0) + 1
    return {
        "status": "PREVIEW_ONLY",
        "source_id": "S15A",
        "total": len(records),
        "provisional_tender": counts.get("TENDER", 0),
        "provisional_auction_notice": counts.get("AUCTION_NOTICE", 0),
        "provisional_unclassified": counts.get("UNCLASSIFIED", 0),
        "identity": "PROVISIONAL_SLUG_UNTIL_DETAIL_SHORTLINK",
        "classification": "TITLE_ONLY_REQUIRES_DETAIL_PDF_FOR_FINAL_ITEM_KIND",
        "records": [record.preview_payload() for record in records],
    }
