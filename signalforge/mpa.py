from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlparse

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
