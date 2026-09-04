from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlparse, urlsplit, urlunsplit

from .mpt import SitemapEntry, normalize_text

DICA_BASE_URL = "https://www.dica.gov.mm"
DICA_LIST_URL = f"{DICA_BASE_URL}/category/announcements-and-information/"
DICA_PUBLISHER = "Directorate of Investment and Company Administration"
SELECTION_POLICY_VERSION = 1


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


def _canonical_post_url(href: str) -> str | None:
    url = urljoin(DICA_BASE_URL, href)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"dica.gov.mm", "www.dica.gov.mm"}:
        return None
    match = re.fullmatch(r"/(\d+)/?", parsed.path)
    if match is None:
        return None
    return f"{DICA_BASE_URL}/{match.group(1)}/"


def _post_id(url: str) -> str | None:
    parsed = urlparse(url)
    match = re.fullmatch(r"/(\d+)/?", parsed.path)
    return match.group(1) if match else None


def _encoded_official_pdf(raw_url: str, page_url: str) -> str | None:
    url = urljoin(page_url, raw_url)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"dica.gov.mm", "www.dica.gov.mm"}:
        return None
    if "/wp-content/uploads/" not in parsed.path or not parsed.path.lower().endswith(".pdf"):
        return None
    encoded_path = quote(unquote(parsed.path), safe="/%^()_-.")
    return urlunsplit((parsed.scheme, parsed.netloc, encoded_path, parsed.query, parsed.fragment))


def classify_business_notice(title: str) -> str | None:
    value = normalize_text(title)
    lower = value.lower()
    if not value:
        return None
    if "list of companies struck off from the company registration" in lower:
        return "COMPANY_STRIKE_OFF_BATCH"
    if "ကုမ္ပဏီများသို့ အသိပေးကြေညာခြင်း" in value:
        return "COMPANY_COMPLIANCE_NOTICE"
    if "tax exemption or relief" in lower:
        return "INVESTMENT_TAX_INCENTIVE"
    if "chinese yuan" in lower or "cny" in lower:
        return "INVESTMENT_CAPITAL_CURRENCY"
    return None


def _reference_from_title(title: str, post_id: str) -> tuple[str, str]:
    value = normalize_text(title)
    match = re.search(r"Notification\s+No\.?\s*([0-9]+)\s*/\s*([0-9]{4})", value, re.I)
    if match:
        return f"{match.group(1)}/{match.group(2)}", "issuer_notice_reference"
    match = re.search(r"Investment\s+Newsletter\s*\(\s*([0-9]+)\s*/\s*([0-9]{4})\s*\)", value, re.I)
    if match:
        return f"Investment Newsletter {match.group(1)}/{match.group(2)}", "issuer_notice_reference"
    return f"DICA-POST-{post_id}", "issuer_record_id"


class DicaListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self._article_depth = 0
        self._title_depth = 0
        self._time_depth = 0
        self._url: str | None = None
        self._datetime: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "article":
            if self._article_depth:
                self._article_depth += 1
            elif "category-announcements-and-information" in classes:
                self._article_depth = 1
                self._url = None
                self._datetime = None
        elif self._article_depth:
            if lowered == "h2" and "entry-title" in classes:
                self._title_depth = 1
            elif lowered == "a" and self._title_depth:
                href = _attr(attrs, "href")
                if href:
                    self._url = _canonical_post_url(href)
            elif lowered == "time" and "ct-meta-element-date" in classes:
                value = _attr(attrs, "datetime")
                if value:
                    self._datetime = value
                self._time_depth = 1
            elif self._title_depth and lowered not in {"br", "img", "input", "meta", "link"}:
                self._title_depth += 1
            elif self._time_depth and lowered not in {"br", "img", "input", "meta", "link"}:
                self._time_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._article_depth:
            return
        if self._title_depth and lowered in {"h2", "a", "span", "div"}:
            self._title_depth -= 1
        if self._time_depth and lowered in {"time", "span", "li"}:
            self._time_depth -= 1
        if lowered == "article":
            self._article_depth -= 1
            if self._article_depth == 0:
                if self._url and self._datetime:
                    self.entries.append(SitemapEntry(self._url, self._datetime))
                self._url = None
                self._datetime = None


def parse_announcement_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = DicaListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class DicaNotice:
    source_record_id: str
    title: str
    publication_date: str
    notice_category: str
    attachment_name: str | None
    attachment_url: str | None
    url: str

    item_kind = "REGULATORY_NOTICE"
    deadline = None
    location = None

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def reference_no(self) -> str:
        return _reference_from_title(self.title, self.source_record_id)[0]

    @property
    def reference_no_kind(self) -> str:
        return _reference_from_title(self.title, self.source_record_id)[1]

    @property
    def canonical_key(self) -> str:
        return f"dica-notice:{self.source_record_id}"

    def payload(self) -> dict[str, str | int | None]:
        return {
            "item_kind": self.item_kind,
            "issuer": DICA_PUBLISHER,
            "publisher": DICA_PUBLISHER,
            "legal_issuer": None,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": self.reference_no_kind,
            "source_record_id": self.source_record_id,
            "publication_date": self.publication_date,
            "notice_category": self.notice_category,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "pdf_value_gate": "TRIGGERED_EXTRACTION_RUNTIME_DEFERRED",
            "detail_completeness": "HTML_EVENT_METADATA_ATTACHMENT_ONLY",
            "url": self.url,
        }


class DicaDetailParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self._title_depth = 0
        self._time_depth = 0
        self._current_pdf_url: str | None = None
        self._current_pdf_parts: list[str] = []
        self.title_parts: list[str] = []
        self.publication_datetime: str | None = None
        self.attachment_name: str | None = None
        self.attachment_url: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered in {"h1", "h2"} and ({"page-title", "entry-title"} & classes):
            self._title_depth = 1
        elif self._title_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._title_depth += 1

        if lowered == "time" and "ct-meta-element-date" in classes:
            value = _attr(attrs, "datetime")
            if value and self.publication_datetime is None:
                self.publication_datetime = value
            self._time_depth = 1
        elif self._time_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._time_depth += 1

        if lowered == "a" and self.attachment_url is None:
            href = _attr(attrs, "href")
            if href:
                encoded = _encoded_official_pdf(href, self.page_url)
                if encoded:
                    self._current_pdf_url = encoded
                    self._current_pdf_parts = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._current_pdf_url and lowered == "a":
            self.attachment_url = self._current_pdf_url
            filename = unquote(urlparse(self._current_pdf_url).path.rsplit("/", 1)[-1])
            self.attachment_name = filename
            self._current_pdf_url = None
            self._current_pdf_parts = []
        if self._title_depth and lowered in {"h1", "h2", "a", "span", "div"}:
            self._title_depth -= 1
        if self._time_depth and lowered in {"time", "span", "li"}:
            self._time_depth -= 1

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._current_pdf_url:
            self._current_pdf_parts.append(value)
        if self._title_depth:
            self.title_parts.append(value)


def parse_announcement_detail(html_bytes: bytes, page_url: str) -> DicaNotice | None:
    post_id = _post_id(page_url)
    if post_id is None:
        return None
    parser = DicaDetailParser(page_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    if not title or parser.publication_datetime is None:
        return None
    category = classify_business_notice(title)
    if category is None:
        return None
    publication_date = parser.publication_datetime[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", publication_date):
        return None
    return DicaNotice(
        source_record_id=post_id,
        title=title,
        publication_date=publication_date,
        notice_category=category,
        attachment_name=parser.attachment_name,
        attachment_url=parser.attachment_url,
        url=page_url,
    )
