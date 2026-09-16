from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from .mpt import SitemapEntry, normalize_text


IWT_BASE_URL = "https://iwt.gov.mm"
YANGON = ZoneInfo("Asia/Yangon")


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


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _local_date(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(YANGON).date().isoformat()


def _local_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(YANGON).isoformat()


@dataclass(frozen=True)
class IwtTender:
    source_record_id: str
    title: str
    project_name: str
    publication_date: str
    deadline: str | None
    publication_datetime_utc: str
    deadline_datetime_utc: str | None
    deadline_datetime_local: str | None
    attachment_name: str | None
    attachment_url: str | None
    location: str | None
    url: str
    content_hash: str

    @property
    def reference_no(self) -> str:
        # IWT does not currently expose a business tender/reference number in HTML.
        # Keep the required legacy DB field explicit about being an issuer record id.
        return f"IWT-NODE-{self.source_record_id}"

    @property
    def canonical_key(self) -> str:
        # Issuer-native Drupal record id + publication date is stable across body,
        # deadline and attachment edits, so those edits become UPDATED signals.
        return f"iwt:{self.source_record_id}:{self.publication_date}"

    def payload(self) -> dict[str, str | None]:
        return {
            "issuer": "Inland Water Transport (Myanmar)",
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_record_id",
            "source_record_id": self.source_record_id,
            "title": self.title,
            "project_name": self.project_name,
            "publication_date": self.publication_date,
            "deadline": self.deadline,
            "publication_datetime_utc": self.publication_datetime_utc,
            "deadline_datetime_utc": self.deadline_datetime_utc,
            "deadline_datetime_local": self.deadline_datetime_local,
            "location": self.location,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "url": self.url,
        }


class IwtTenderListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self._title_div_depth = 0
        self._post_div_depth = 0
        self._pending_url: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        classes = _classes(attrs)
        lowered = tag.lower()

        if lowered == "div":
            if self._title_div_depth:
                self._title_div_depth += 1
            elif "views-field-title" in classes:
                self._title_div_depth = 1

            if self._post_div_depth:
                self._post_div_depth += 1
            elif "views-field-field-post-date-tender" in classes:
                self._post_div_depth = 1

        if lowered == "a" and self._title_div_depth:
            href = _attr(attrs, "href")
            if not href:
                return
            url = urljoin(IWT_BASE_URL, href)
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.netloc.lower() not in {"iwt.gov.mm", "www.iwt.gov.mm"}:
                return
            match = re.fullmatch(r"(?:/index\.php)?/my/node/(\d+)", parsed.path)
            if match:
                # The issuer currently emits /index.php/my/node/<id>, while older
                # pages used /my/node/<id>. Normalize both shapes to one stable URL
                # so path-routing drift does not create new canonical identities.
                self._pending_url = f"https://iwt.gov.mm/my/node/{match.group(1)}"

        if lowered == "time" and self._post_div_depth and self._pending_url:
            value = _iso_utc(_parse_iso_datetime(_attr(attrs, "datetime")))
            self.entries.append(SitemapEntry(self._pending_url, value))
            self._pending_url = None

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "div":
            return
        if self._title_div_depth:
            self._title_div_depth -= 1
        if self._post_div_depth:
            self._post_div_depth -= 1


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = IwtTenderListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    deduplicated: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        deduplicated.setdefault(entry.url, entry)
    return list(deduplicated.values())


class IwtTenderDetailParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.is_tender_node = False
        self.source_record_id: str | None = None
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.attachment_name_parts: list[str] = []
        self.attachment_url: str | None = None
        self.publication_datetime: datetime | None = None
        self.deadline_datetime: datetime | None = None

        self._title_span_depth = 0
        self._body_div_depth = 0
        self._pdf_div_depth = 0
        self._post_div_depth = 0
        self._close_div_depth = 0
        self._in_pdf_link = False

    @staticmethod
    def _advance_div(depth: int, classes: set[str], marker: str) -> int:
        if depth:
            return depth + 1
        if marker in classes:
            return 1
        return 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)

        if lowered == "article" and "node--type-tenders" in classes:
            self.is_tender_node = True
            self.source_record_id = _attr(attrs, "data-history-node-id")

        if lowered == "span":
            if self._title_span_depth:
                self._title_span_depth += 1
            elif "field-name-title" in classes:
                self._title_span_depth = 1

        if lowered == "div":
            self._body_div_depth = self._advance_div(self._body_div_depth, classes, "field-node--body")
            self._pdf_div_depth = self._advance_div(self._pdf_div_depth, classes, "field-name-field-pdf-upload")
            self._post_div_depth = self._advance_div(self._post_div_depth, classes, "field-name-field-post-date-tender")
            self._close_div_depth = self._advance_div(self._close_div_depth, classes, "field-name-field-close-date-tender")

        if lowered == "time":
            value = _parse_iso_datetime(_attr(attrs, "datetime"))
            if self._post_div_depth:
                self.publication_datetime = value
            elif self._close_div_depth:
                self.deadline_datetime = value

        if lowered == "a" and self._pdf_div_depth:
            href = _attr(attrs, "href")
            media_type = _attr(attrs, "type") or ""
            if href and (media_type.startswith("application/pdf") or "file-download" in href):
                self.attachment_url = urljoin(self.page_url, href)
                self._in_pdf_link = True

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "span" and self._title_span_depth:
            self._title_span_depth -= 1
        elif lowered == "a" and self._in_pdf_link:
            self._in_pdf_link = False
        elif lowered == "div":
            if self._body_div_depth:
                self._body_div_depth -= 1
            if self._pdf_div_depth:
                self._pdf_div_depth -= 1
            if self._post_div_depth:
                self._post_div_depth -= 1
            if self._close_div_depth:
                self._close_div_depth -= 1

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._title_span_depth:
            self.title_parts.append(value)
        if self._body_div_depth:
            self.body_parts.append(value)
        if self._in_pdf_link:
            self.attachment_name_parts.append(value)


def parse_tender_detail(html_bytes: bytes, url: str) -> IwtTender | None:
    parser = IwtTenderDetailParser(url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))

    source_record_id = parser.source_record_id
    if not source_record_id:
        match = re.search(r"/node/(\d+)(?:/)?$", urlparse(url).path)
        source_record_id = match.group(1) if match else None

    title = normalize_text(" ".join(parser.title_parts))
    body = normalize_text(" ".join(parser.body_parts))
    publication_date = _local_date(parser.publication_datetime)
    publication_datetime_utc = _iso_utc(parser.publication_datetime)

    if not parser.is_tender_node or not source_record_id or not title or not publication_date or not publication_datetime_utc:
        return None

    digest = hashlib.sha256(html_bytes).hexdigest()
    return IwtTender(
        source_record_id=source_record_id,
        title=title,
        project_name=body or title,
        publication_date=publication_date,
        deadline=_local_date(parser.deadline_datetime),
        publication_datetime_utc=publication_datetime_utc,
        deadline_datetime_utc=_iso_utc(parser.deadline_datetime),
        deadline_datetime_local=_local_datetime(parser.deadline_datetime),
        attachment_name=normalize_text(" ".join(parser.attachment_name_parts)) or None,
        attachment_url=parser.attachment_url,
        location=None,
        url=url,
        content_hash=digest,
    )
