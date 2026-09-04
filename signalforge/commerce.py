from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlparse

from .mpt import SitemapEntry, normalize_text


COMMERCE_BASE_URL = "https://commerce.gov.mm/my/"
COMMERCE_ISSUER = "Ministry of Commerce"
SELECTION_POLICY_VERSION = 1

_EXCLUDE_TOKENS = (
    "အမှုထမ်း",
    "ရာထူး",
    "စာမေးပွဲ",
    "သင်တန်း",
    "သင်တန်းသား",
    "အောင်မြင်သူ",
)

_CATEGORY_TOKENS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("PRODUCT_CONTROL", ("ပိုးသတ်ဆေး",)),
    ("MARKET_SUPPLY", ("စားအုန်းဆီ",)),
    ("TRADE_PRICING", ("ရည်ညွှန်းစျေးနှုန်း",)),
)


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


def _canonical_article_url(href: str) -> str | None:
    url = urljoin(COMMERCE_BASE_URL, href)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"commerce.gov.mm", "www.commerce.gov.mm"}:
        return None
    if not re.fullmatch(r"/my/article/.+/(\d+)", parsed.path):
        return None
    return f"https://commerce.gov.mm{parsed.path}"


def classify_business_notice(title: str) -> str | None:
    value = normalize_text(title)
    if not value or any(token in value for token in _EXCLUDE_TOKENS):
        return None

    has_import = "သွင်းကုန်" in value
    has_export = "ပို့ကုန်" in value
    if has_import and has_export:
        return "IMPORT_EXPORT"
    if has_import:
        return "IMPORT"
    if has_export:
        return "EXPORT"

    for category, tokens in _CATEGORY_TOKENS:
        if any(token in value for token in tokens):
            return category
    return None


class CommerceNotificationListingParser(HTMLParser):
    """Parse only the current Notifications quicktab (`view-display-id-block_3`)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self._view_depth = 0
        self._row_depth = 0
        self._row_url: str | None = None
        self._row_lastmod: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)

        if lowered == "div":
            if self._view_depth:
                self._view_depth += 1
            elif "view-moc-inner-views" in classes and "view-display-id-block_3" in classes:
                self._view_depth = 1

            if self._view_depth:
                if self._row_depth:
                    self._row_depth += 1
                elif "views-row" in classes:
                    self._row_depth = 1
                    self._row_url = None
                    self._row_lastmod = None

        if not self._row_depth:
            return

        if lowered == "a":
            href = _attr(attrs, "href")
            if href:
                canonical = _canonical_article_url(href)
                if canonical:
                    self._row_url = canonical
        elif lowered == "time":
            value = _attr(attrs, "datetime")
            if value:
                try:
                    self._row_lastmod = datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
                except ValueError:
                    self._row_lastmod = None

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "div" or not self._view_depth:
            return

        if self._row_depth:
            self._row_depth -= 1
            if self._row_depth == 0:
                if self._row_url and self._row_lastmod:
                    self.entries.append(SitemapEntry(self._row_url, self._row_lastmod))
                self._row_url = None
                self._row_lastmod = None

        self._view_depth -= 1


def parse_notification_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = CommerceNotificationListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    deduplicated: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        deduplicated.setdefault(entry.url, entry)
    return list(deduplicated.values())


def _extract_notice_reference(*values: str | None) -> str | None:
    for raw in values:
        value = normalize_text(raw or "")
        if not value:
            continue
        match = re.search(
            r"(?:အသိပေးကြေညာချက်|ကြေညာချက်)\s*(?:အမှတ်)?\s*\(?\s*([၀-၉0-9]+\s*/\s*[၀-၉0-9]+)\s*\)?",
            value,
        )
        if match:
            return normalize_text(match.group(1)).replace(" ", "")
    return None


@dataclass(frozen=True)
class CommerceNotice:
    source_record_id: str
    title: str
    publication_date: str
    publication_datetime_utc: str
    notice_category: str
    attachment_name: str | None
    attachment_url: str | None
    notice_reference: str | None
    url: str

    item_kind = "REGULATORY_NOTICE"
    deadline = None
    location = None

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def reference_no(self) -> str:
        return self.notice_reference or f"COMMERCE-NODE-{self.source_record_id}"

    @property
    def canonical_key(self) -> str:
        return f"commerce-notice:{self.source_record_id}:{self.publication_date}"

    def payload(self) -> dict[str, str | int | None]:
        return {
            "item_kind": self.item_kind,
            "issuer": COMMERCE_ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_notice_reference" if self.notice_reference else "issuer_record_id",
            "source_record_id": self.source_record_id,
            "publication_date": self.publication_date,
            "publication_datetime_utc": self.publication_datetime_utc,
            "notice_category": self.notice_category,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "detail_completeness": "HTML_EVENT_METADATA_ATTACHMENT_ONLY",
            "url": self.url,
        }


class CommerceNotificationDetailParser(HTMLParser):
    def __init__(self, page_url: str, expected_node_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.expected_node_id = expected_node_id
        self.article_valid = False
        self._in_article = False
        self._title_depth = 0
        self._pubdate_depth = 0
        self._current_pdf_url: str | None = None
        self._current_pdf_parts: list[str] = []
        self.title_parts: list[str] = []
        self.publication_datetime: str | None = None
        self.attachment_name: str | None = None
        self.attachment_url: str | None = None
        self.attachment_label: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)

        if lowered == "article":
            node_id = _attr(attrs, "data-history-node-id")
            role = _attr(attrs, "role")
            if node_id == self.expected_node_id and role == "article" and "node--type-article" in classes:
                self.article_valid = True
                self._in_article = True
            return

        if not self._in_article:
            return

        if lowered == "h1" and "node__title" in classes:
            self._title_depth = 1
        elif self._title_depth and lowered in {"span", "div"}:
            self._title_depth += 1

        if lowered == "span" and "node__pubdate" in classes:
            self._pubdate_depth = 1
        elif self._pubdate_depth and lowered == "span":
            self._pubdate_depth += 1

        if lowered == "time" and self._pubdate_depth and self.publication_datetime is None:
            value = _attr(attrs, "datetime")
            if value:
                self.publication_datetime = value

        if lowered == "a" and self.attachment_url is None:
            href = _attr(attrs, "href")
            if href and urlparse(href).path.lower().endswith(".pdf"):
                self._current_pdf_url = urljoin(self.page_url, href)
                self._current_pdf_parts = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._in_article:
            return

        if lowered == "a" and self._current_pdf_url:
            self.attachment_url = self._current_pdf_url
            self.attachment_name = unquote(urlparse(self.attachment_url).path.rsplit("/", 1)[-1])
            self.attachment_label = normalize_text(" ".join(self._current_pdf_parts)) or None
            self._current_pdf_url = None
            self._current_pdf_parts = []

        if self._title_depth and lowered in {"span", "div", "h1"}:
            self._title_depth -= 1
        if self._pubdate_depth and lowered == "span":
            self._pubdate_depth -= 1
        if lowered == "article":
            self._in_article = False

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._current_pdf_url:
            self._current_pdf_parts.append(value)


def parse_notification_detail(html_bytes: bytes, url: str) -> CommerceNotice | None:
    parsed_url = urlparse(url)
    match = re.fullmatch(r"/my/article/.+/(\d+)", parsed_url.path)
    if not match or parsed_url.netloc.lower() not in {"commerce.gov.mm", "www.commerce.gov.mm"}:
        return None

    source_record_id = match.group(1)
    parser = CommerceNotificationDetailParser(url, source_record_id)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if not parser.article_valid:
        return None

    title = normalize_text(" ".join(parser.title_parts))
    category = classify_business_notice(title)
    if not title or category is None or not parser.publication_datetime:
        return None

    try:
        publication = datetime.fromisoformat(parser.publication_datetime.replace("Z", "+00:00"))
    except ValueError:
        return None

    notice_reference = _extract_notice_reference(title, parser.attachment_label)
    return CommerceNotice(
        source_record_id=source_record_id,
        title=title,
        publication_date=publication.date().isoformat(),
        publication_datetime_utc=publication.isoformat(),
        notice_category=category,
        attachment_name=parser.attachment_name,
        attachment_url=parser.attachment_url,
        notice_reference=notice_reference,
        url=f"https://commerce.gov.mm{parsed_url.path}",
    )
