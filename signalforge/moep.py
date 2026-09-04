from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .mpt import SitemapEntry, normalize_text


MOEP_BASE_URL = "https://moep.gov.mm/mm/"
TENDER_TOKEN = re.compile(r"(?:တင်ဒါ|tender|invitation\s+to\s+bid|quotation)", re.IGNORECASE)


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


def _parse_publication_date(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_text(value).lstrip("-: ")
    for pattern in ("%d-%b-%Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, pattern).date().isoformat()
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class MoepTender:
    source_record_id: str
    title: str
    project_name: str
    publication_date: str
    issuer: str
    attachment_name: str | None
    attachment_url: str | None
    url: str
    content_hash: str
    deadline: str | None = None
    location: str | None = None
    remarks: str | None = None
    company_size: str | None = None
    required_quantity: str | None = None

    @property
    def reference_no(self) -> str:
        return f"MOEP-CONTENT-{self.source_record_id}"

    @property
    def canonical_key(self) -> str:
        return f"moep:{self.source_record_id}:{self.publication_date}"

    def payload(self) -> dict[str, str | None]:
        return {
            "issuer": self.issuer,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_record_id",
            "source_record_id": self.source_record_id,
            "title": self.title,
            "project_name": self.project_name,
            "publication_date": self.publication_date,
            "deadline": self.deadline,
            "location": self.location,
            "remarks": self.remarks,
            "company_size": self.company_size,
            "required_quantity": self.required_quantity,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "detail_completeness": "HTML_PARTIAL_ATTACHMENT_METADATA",
            "url": self.url,
        }


class MoepTenderListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self._block_depth = 0
        self._pending_url: str | None = None
        self._in_date_box = False
        self._date_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)

        if lowered == "div":
            if self._block_depth:
                self._block_depth += 1
            elif "content-data-list" in classes:
                self._block_depth = 1
            if self._block_depth and "text-right" in classes and "small-height" in classes:
                self._in_date_box = True
                self._date_parts = []

        if lowered == "a" and self._block_depth:
            href = _attr(attrs, "href")
            if not href:
                return
            url = urljoin(MOEP_BASE_URL, href)
            parsed = urlparse(url)
            match = re.fullmatch(r"/mm/ignite/contentView/(\d+)", parsed.path)
            if parsed.scheme == "https" and parsed.netloc.lower() in {"moep.gov.mm", "www.moep.gov.mm"} and match:
                self._pending_url = f"https://moep.gov.mm{parsed.path}"

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "div" or not self._block_depth:
            return
        if self._in_date_box:
            publication_date = None
            for part in reversed(self._date_parts):
                publication_date = _parse_publication_date(part)
                if publication_date:
                    break
            if self._pending_url and publication_date:
                self.entries.append(SitemapEntry(self._pending_url, f"{publication_date}T00:00:00Z"))
            self._pending_url = None
            self._date_parts = []
            self._in_date_box = False
        self._block_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_date_box:
            value = normalize_text(data)
            if value:
                self._date_parts.append(value)


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = MoepTenderListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    deduplicated: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        deduplicated.setdefault(entry.url, entry)
    return list(deduplicated.values())


class MoepTenderDetailParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.og_title: str | None = None
        self.og_description: str | None = None
        self.attachment_name: str | None = None
        self.attachment_url: str | None = None
        self.issuer_parts: list[str] = []
        self.date_parts: list[str] = []
        self._in_issuer_box = False
        self._issuer_box_depth = 0
        self._in_italic = False

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)

        if lowered == "meta" and _attr(attrs, "property"):
            prop = (_attr(attrs, "property") or "").lower()
            content = _attr(attrs, "content")
            if prop == "og:title" and content:
                self.og_title = normalize_text(content)
            elif prop == "og:description" and content:
                self.og_description = normalize_text(content)

        if lowered == "a":
            href = _attr(attrs, "href")
            if href and urlparse(href).path.lower().endswith(".pdf") and self.attachment_url is None:
                self.attachment_url = urljoin(self.page_url, href)
                self.attachment_name = urlparse(self.attachment_url).path.rsplit("/", 1)[-1]

        if lowered == "div":
            if self._issuer_box_depth:
                self._issuer_box_depth += 1
            elif "text-right" in classes and "small-height" in classes:
                self._in_issuer_box = True
                self._issuer_box_depth = 1

        if lowered == "i" and self._in_issuer_box:
            self._in_italic = True

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "i":
            self._in_italic = False
        elif lowered == "div" and self._issuer_box_depth:
            self._issuer_box_depth -= 1
            if self._issuer_box_depth == 0:
                self._in_issuer_box = False

    def handle_data(self, data: str) -> None:
        if not self._in_issuer_box:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._in_italic:
            self.date_parts.append(value)
        else:
            self.issuer_parts.append(value)


def parse_tender_detail(html_bytes: bytes, url: str) -> MoepTender | None:
    parsed_url = urlparse(url)
    match = re.fullmatch(r"/mm/ignite/contentView/(\d+)", parsed_url.path)
    if not match:
        return None

    parser = MoepTenderDetailParser(url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))

    title = normalize_text(parser.og_title or "")
    body = normalize_text(parser.og_description or "")
    if not title or not TENDER_TOKEN.search(f"{title} {body}"):
        return None

    issuer_text = normalize_text(" ".join(parser.issuer_parts))
    issuer_text = re.sub(r"^Post\s+under\s+by\s*:\s*", "", issuer_text, flags=re.IGNORECASE)
    issuer = normalize_text(issuer_text)

    publication_date = None
    for value in parser.date_parts:
        publication_date = _parse_publication_date(value)
        if publication_date:
            break

    if not issuer or not publication_date:
        return None

    digest = hashlib.sha256(html_bytes).hexdigest()
    return MoepTender(
        source_record_id=match.group(1),
        title=title,
        project_name=body or title,
        publication_date=publication_date,
        issuer=issuer,
        attachment_name=parser.attachment_name,
        attachment_url=parser.attachment_url,
        url=f"https://moep.gov.mm{parsed_url.path}",
        content_hash=digest,
    )
