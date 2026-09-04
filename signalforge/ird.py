from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlparse, urlsplit, urlunsplit

from .mpt import SitemapEntry, normalize_text

IRD_BASE_URL = "https://www.ird.gov.mm"
IRD_LIST_URL = f"{IRD_BASE_URL}/announcement-lists"
IRD_ISSUER = "Internal Revenue Department"
SELECTION_POLICY_VERSION = 1

_EXCLUDE_TOKENS = (
    "တင်ဒါ",
    "Tender",
    "TENDER",
    "အဂတိလိုက်စားမှု",
    "1111",
    "သင်တန်း",
    "အစည်းအဝေး",
    "ဖွင့်လှစ်ခြင်း",
)

_CATEGORY_TOKENS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("TAX_EXEMPTION", ("ကင်းလွတ်", "ကင်းလွတ်ခွင့်", "ကင်းလွတ်ခွင့်", "exempt")),
    ("TAX_FILING", ("ကြေညာလွှာ", "INCOME TAX RETURN", "ANNUAL SALARY STATEMENT", "COMMERCIAL TAX RETURN")),
    ("TAX_REGISTRATION", ("အခွန်ထမ်းမှတ်ပုံတင်", "အခွန်ထမ်းကုမ္ပဏီ")),
    ("TAX_PAYMENT", ("Digital Payment", "ငွေပေးချေ", "IMEI")),
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


def _parse_visible_date(value: str) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _iso_midnight(date_text: str) -> str:
    parsed = datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=UTC)
    return parsed.isoformat()


def _canonical_announcement_url(href: str) -> str | None:
    url = urljoin(IRD_BASE_URL, href)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"ird.gov.mm", "www.ird.gov.mm"}:
        return None
    match = re.fullmatch(r"/announcement-lists/(\d+)", parsed.path)
    if match is None:
        return None
    return f"{IRD_BASE_URL}/announcement-lists/{match.group(1)}"


def _announcement_id(url: str) -> str | None:
    parsed = urlparse(url)
    match = re.fullmatch(r"/announcement-lists/(\d+)", parsed.path)
    return match.group(1) if match else None


def _encoded_official_pdf(raw_url: str, page_url: str) -> str | None:
    url = urljoin(page_url, raw_url)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"ird.gov.mm", "www.ird.gov.mm"}:
        return None
    if not parsed.path.startswith("/storage/announcements/") or not parsed.path.lower().endswith(".pdf"):
        return None
    encoded_path = quote(unquote(parsed.path), safe="/%^()_-.")
    return urlunsplit((parsed.scheme, parsed.netloc, encoded_path, parsed.query, parsed.fragment))


def classify_business_notice(title: str, body: str = "") -> str | None:
    title_value = normalize_text(title)
    value = normalize_text(f"{title_value} {body}")
    if not title_value or any(token in title_value for token in _EXCLUDE_TOKENS):
        return None

    lower = value.lower()
    has_tax_signal = any(
        token in value
        for token in (
            "အခွန်",
            "ဝင်ငွေခွန်",
            "ကုန်သွယ်လုပ်ငန်းခွန်",
            "အထူးကုန်စည်ခွန်",
            "အခွန်ထမ်း",
        )
    ) or any(token in lower for token in ("income tax", "commercial tax", "taxpayer"))
    if not has_tax_signal:
        return None

    title_lower = title_value.lower()
    for category, tokens in _CATEGORY_TOKENS:
        for token in tokens:
            if token in title_value or token.lower() in title_lower:
                return category
    for category, tokens in _CATEGORY_TOKENS:
        for token in tokens:
            if token in value or token.lower() in lower:
                return category
    return "TAX_NOTICE"


class IrdAnnouncementListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self._card_depth = 0
        self._title_depth = 0
        self._meta_depth = 0
        self._row_url: str | None = None
        self._date_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "div":
            if self._card_depth:
                self._card_depth += 1
            elif "course__item-2" in classes:
                self._card_depth = 1
                self._row_url = None
                self._date_parts = []
            if self._card_depth:
                if self._title_depth:
                    self._title_depth += 1
                elif "blog__title" in classes:
                    self._title_depth = 1
                if self._meta_depth:
                    self._meta_depth += 1
                elif "blog__meta" in classes:
                    self._meta_depth = 1
        elif lowered == "h3" and self._card_depth and "blog__title" in classes:
            self._title_depth = 1
        elif lowered == "a" and self._card_depth and self._title_depth:
            href = _attr(attrs, "href")
            if href:
                self._row_url = _canonical_announcement_url(href)
        elif self._card_depth:
            if self._title_depth:
                self._title_depth += 1
            if self._meta_depth:
                self._meta_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._card_depth:
            return
        if self._title_depth and lowered in {"div", "h3", "a", "span", "ul", "li"}:
            self._title_depth -= 1
        if self._meta_depth and lowered in {"div", "span", "ul", "li", "i"}:
            self._meta_depth -= 1
        if lowered == "div":
            self._card_depth -= 1
            if self._card_depth == 0:
                visible_date = _parse_visible_date(" ".join(self._date_parts))
                if self._row_url and visible_date:
                    self.entries.append(SitemapEntry(self._row_url, _iso_midnight(visible_date)))
                self._row_url = None
                self._date_parts = []

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if value and self._card_depth and self._meta_depth:
            self._date_parts.append(value)


def parse_announcement_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = IrdAnnouncementListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    deduplicated: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        deduplicated.setdefault(entry.url, entry)
    return list(deduplicated.values())


@dataclass(frozen=True)
class IrdNotice:
    source_record_id: str
    title: str
    publication_date: str
    notice_category: str
    body_excerpt: str | None
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
        return f"IRD-ANNOUNCEMENT-{self.source_record_id}"

    @property
    def canonical_key(self) -> str:
        return f"ird-notice:{self.source_record_id}:{self.publication_date}"

    def payload(self) -> dict[str, str | int | None]:
        return {
            "item_kind": self.item_kind,
            "issuer": IRD_ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_record_id",
            "source_record_id": self.source_record_id,
            "publication_date": self.publication_date,
            "notice_category": self.notice_category,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "body_excerpt": self.body_excerpt,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "detail_completeness": "HTML_EVENT_METADATA_ATTACHMENT_ONLY",
            "url": self.url,
        }


class IrdAnnouncementDetailParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.record_id = _announcement_id(page_url)
        self._content_depth = 0
        self._meta_depth = 0
        self._title_depth = 0
        self._text_depth = 0
        self._current_pdf_url: str | None = None
        self._current_pdf_parts: list[str] = []
        self.date_parts: list[str] = []
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.attachment_name: str | None = None
        self.attachment_url: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "div":
            if self._content_depth:
                self._content_depth += 1
            elif "postbox__content" in classes:
                self._content_depth = 1
            if self._content_depth:
                if self._meta_depth:
                    self._meta_depth += 1
                elif "postbox__meta" in classes:
                    self._meta_depth = 1
                if self._text_depth:
                    self._text_depth += 1
                elif "postbox__text" in classes:
                    self._text_depth = 1
        elif lowered == "h3" and self._content_depth and "postbox__title" in classes:
            self._title_depth = 1
        elif self._content_depth:
            if self._meta_depth:
                self._meta_depth += 1
            if self._title_depth:
                self._title_depth += 1
            if self._text_depth and lowered not in {"br", "hr", "img", "input", "meta", "link"}:
                self._text_depth += 1

        if lowered == "a" and self._content_depth and self.attachment_url is None:
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
            label = normalize_text(" ".join(self._current_pdf_parts))
            self.attachment_name = label or unquote(urlparse(self._current_pdf_url).path.rsplit("/", 1)[-1])
            self._current_pdf_url = None
            self._current_pdf_parts = []
        if not self._content_depth:
            return
        if self._meta_depth and lowered in {"div", "span", "a", "i"}:
            self._meta_depth -= 1
        if self._title_depth and lowered in {"h3", "span", "a", "div"}:
            self._title_depth -= 1
        if self._text_depth and lowered in {"div", "p", "span", "br", "strong", "ul", "ol", "li"}:
            self._text_depth -= 1
        if lowered == "div":
            self._content_depth -= 1

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._current_pdf_url:
            self._current_pdf_parts.append(value)
        if not self._content_depth:
            return
        if self._meta_depth:
            if "IRD Admin" not in value:
                self.date_parts.append(value)
        if self._title_depth:
            self.title_parts.append(value)
        if self._text_depth:
            self.body_parts.append(value)


def parse_announcement_detail(html_bytes: bytes, page_url: str) -> IrdNotice | None:
    record_id = _announcement_id(page_url)
    if record_id is None:
        return None
    parser = IrdAnnouncementDetailParser(page_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))

    title = normalize_text(" ".join(parser.title_parts))
    publication_date = _parse_visible_date(" ".join(parser.date_parts))
    body = normalize_text(" ".join(parser.body_parts)).replace("\ufeff", "").strip()
    if not title or publication_date is None:
        return None

    category = classify_business_notice(title, body)
    if category is None:
        return None

    excerpt = body[:1200] if body else None
    return IrdNotice(
        source_record_id=record_id,
        title=title,
        publication_date=publication_date,
        notice_category=category,
        body_excerpt=excerpt,
        attachment_name=parser.attachment_name,
        attachment_url=parser.attachment_url,
        url=page_url,
    )
