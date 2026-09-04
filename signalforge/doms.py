from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlparse, urlsplit, urlunsplit

from .mpt import SitemapEntry, normalize_text

DOMS_BASE_URL = "https://www.doms.gov.mm"
DOMS_LIST_URL = f"{DOMS_BASE_URL}/category/tender/"
DOMS_ISSUER = "Department of Medical Services, Ministry of Health"
DOMS_HOSTS = {"doms.gov.mm", "www.doms.gov.mm"}
SELECTION_POLICY_VERSION = 1

_EXCLUDE_STAGE_TOKENS = (
    "အောင်စာရင်း",
    "အောင်မြင်",
    "စိစစ်",
    "အစည်းအဝေး",
    "ဖွင့်ဖောက်",
    "ဖွင့်ဖောက်",
    "envelope",
    "awarded",
    "result",
)
_OPEN_TENDER_TOKENS = (
    "တင်ဒါခေါ်ယူ",
    "အိတ်ဖွင့်တင်ဒါ",
    "အိတ်ဖွင့်တင်ဒါ",
    "open tender",
)
_DMS_REFERENCE_RE = re.compile(
    r"(?P<number>\d+)\s*DMS\s*/?\s*[\u2068\u2069]?\s*"
    r"(?P<year1>20\d{2})\s*[-–]\s*(?P<year2>20\d{2})[\u2068\u2069]?"
    r"\s*(?:\(\s*(?P<suffix>[A-Za-z])\s*\))?",
    re.I,
)
_DATE_PATH_RE = re.compile(r"^/(20\d{2})/(\d{2})/(\d{2})/[^/]+/?$")


class DomsParseError(ValueError):
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


def _post_id_from_attrs(attrs) -> str | None:  # type: ignore[no-untyped-def]
    value = _attr(attrs, "id") or ""
    match = re.fullmatch(r"post-(\d+)", value)
    return match.group(1) if match else None


def _canonical_post_url(raw_url: str) -> str | None:
    url = urljoin(DOMS_BASE_URL, raw_url)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in DOMS_HOSTS:
        return None
    if _DATE_PATH_RE.fullmatch(parsed.path) is None:
        return None
    encoded_path = quote(unquote(parsed.path), safe="/%^()_-.")
    return urlunsplit(("https", "www.doms.gov.mm", encoded_path, "", ""))


def _publication_date_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    match = _DATE_PATH_RE.fullmatch(parsed.path)
    if match is None:
        return None
    year, month, day = match.groups()
    return f"{year}-{month}-{day}"


def _listing_lastmod(url: str) -> str | None:
    date = _publication_date_from_url(url)
    return f"{date}T00:00:00+06:30" if date else None


def _encoded_official_pdf(raw_url: str, page_url: str) -> str | None:
    url = urljoin(page_url, raw_url)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in DOMS_HOSTS:
        return None
    if "/wp-content/uploads/" not in parsed.path or not parsed.path.lower().endswith(".pdf"):
        return None
    encoded_path = quote(unquote(parsed.path), safe="/%^()_-.")
    return urlunsplit(("https", "www.doms.gov.mm", encoded_path, parsed.query, ""))


def _clean_reference_text(value: str) -> str:
    return normalize_text(value.replace("\u2068", "").replace("\u2069", ""))


def _reference_from_text(value: str, post_id: str) -> tuple[str, str]:
    clean = _clean_reference_text(value)
    match = _DMS_REFERENCE_RE.search(clean)
    if match:
        suffix = match.group("suffix")
        reference = f"{int(match.group('number'))}DMS/{match.group('year1')}-{match.group('year2')}"
        if suffix:
            reference += f"({suffix.upper()})"
        return reference, "issuer_tender_reference"
    return f"DOMS-POST-{post_id}", "wordpress_post_id"


def is_opportunity_title(title: str) -> bool:
    value = _clean_reference_text(title)
    lower = value.lower()
    if not value:
        return False
    if any(token.lower() in lower for token in _EXCLUDE_STAGE_TOKENS):
        return False
    if any(token.lower() in lower for token in _OPEN_TENDER_TOKENS):
        return True
    return _DMS_REFERENCE_RE.search(value) is not None


class DomsListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self.article_count = 0
        self._article_depth = 0
        self._title_depth = 0
        self._post_id: str | None = None
        self._url: str | None = None
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "article":
            if self._article_depth:
                self._article_depth += 1
            elif "category-tender" in classes:
                self._article_depth = 1
                self.article_count += 1
                self._post_id = _post_id_from_attrs(attrs)
                self._url = None
                self._title_parts = []
                self._title_depth = 0
            return
        if not self._article_depth:
            return
        if lowered in {"h1", "h2", "h3"} and "entry-title" in classes:
            self._title_depth = 1
            return
        if self._title_depth:
            if lowered == "a":
                href = _attr(attrs, "href")
                if href:
                    self._url = _canonical_post_url(href)
            if lowered not in {"br", "img", "input", "meta", "link"}:
                self._title_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._article_depth:
            return
        if self._title_depth and lowered in {"h1", "h2", "h3", "a", "span", "div"}:
            self._title_depth -= 1
        if lowered == "article":
            self._article_depth -= 1
            if self._article_depth == 0:
                title = normalize_text(" ".join(self._title_parts))
                if self._post_id and self._url and is_opportunity_title(title):
                    lastmod = _listing_lastmod(self._url)
                    if lastmod:
                        self.entries.append(SitemapEntry(self._url, lastmod))
                self._post_id = None
                self._url = None
                self._title_parts = []
                self._title_depth = 0

    def handle_data(self, data: str) -> None:
        if self._article_depth and self._title_depth:
            value = normalize_text(data)
            if value:
                self._title_parts.append(value)


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = DomsListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.article_count == 0:
        raise DomsParseError("DOMS tender category structure not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class DomsTender:
    source_record_id: str
    title: str
    publication_date: str
    scope_summary: str | None
    attachments: tuple[tuple[str, str], ...]
    url: str

    item_kind = "TENDER"
    deadline = None
    location = None

    @property
    def reference_no(self) -> str:
        return _reference_from_text(f"{self.title} {self.scope_summary or ''}", self.source_record_id)[0]

    @property
    def reference_no_kind(self) -> str:
        return _reference_from_text(f"{self.title} {self.scope_summary or ''}", self.source_record_id)[1]

    @property
    def project_name(self) -> str:
        if self.scope_summary:
            return self.scope_summary[:500]
        return self.title

    @property
    def canonical_key(self) -> str:
        return f"doms:{self.source_record_id}"

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": DOMS_ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": self.reference_no_kind,
            "source_record_id": self.source_record_id,
            "publication_date": self.publication_date,
            "deadline": None,
            "deadline_evidence": "UNKNOWN_NOT_IN_HTML_TEXT",
            "scope_summary": self.scope_summary,
            "attachments": [{"name": name, "url": url} for name, url in self.attachments],
            "attachment_count": len(self.attachments),
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "HTML_SCOPE_ATTACHMENT_METADATA",
            "url": self.url,
        }


class DomsDetailParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.post_id: str | None = None
        self._article_depth = 0
        self._title_depth = 0
        self._content_depth = 0
        self._ignore_depth = 0
        self._current_pdf_url: str | None = None
        self._current_pdf_parts: list[str] = []
        self.title_parts: list[str] = []
        self.content_parts: list[str] = []
        self._attachments: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "article":
            if self._article_depth:
                self._article_depth += 1
            else:
                post_id = _post_id_from_attrs(attrs)
                if post_id:
                    self._article_depth = 1
                    self.post_id = post_id
            return
        if not self._article_depth:
            return
        if self._ignore_depth:
            self._ignore_depth += 1
            return
        if lowered in {"script", "style", "noscript"}:
            self._ignore_depth = 1
            return
        if lowered in {"h1", "h2"} and "entry-title" in classes:
            self._title_depth = 1
            return
        if lowered == "div" and "entry-content" in classes:
            self._content_depth = 1
            return
        if self._title_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._title_depth += 1
        if self._content_depth:
            if lowered == "a":
                href = _attr(attrs, "href")
                if href:
                    encoded = _encoded_official_pdf(href, self.page_url)
                    if encoded:
                        self._current_pdf_url = encoded
                        self._current_pdf_parts = []
            if lowered not in {"br", "img", "input", "meta", "link"}:
                self._content_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._article_depth:
            return
        if self._ignore_depth:
            self._ignore_depth -= 1
            return
        if self._current_pdf_url and lowered == "a":
            label = normalize_text(" ".join(self._current_pdf_parts))
            filename = unquote(urlparse(self._current_pdf_url).path.rsplit("/", 1)[-1])
            if not label or label.lower() == "download":
                label = filename
            existing = self._attachments.get(self._current_pdf_url)
            if existing is None or (existing.lower().endswith(".pdf") and not label.lower().endswith(".pdf")):
                self._attachments[self._current_pdf_url] = label
            self._current_pdf_url = None
            self._current_pdf_parts = []
        if self._title_depth and lowered in {"h1", "h2", "a", "span", "div"}:
            self._title_depth -= 1
        if self._content_depth and lowered in {"div", "p", "a", "span", "li", "ul", "ol", "strong", "em"}:
            self._content_depth -= 1
        if lowered == "article":
            self._article_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._article_depth or self._ignore_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._current_pdf_url:
            self._current_pdf_parts.append(value)
        if self._title_depth:
            self.title_parts.append(value)
        if self._content_depth and value.lower() != "download":
            self.content_parts.append(value)

    @property
    def attachments(self) -> tuple[tuple[str, str], ...]:
        return tuple((name, url) for url, name in self._attachments.items())


def parse_tender_detail(html_bytes: bytes, page_url: str) -> DomsTender | None:
    canonical_url = _canonical_post_url(page_url)
    publication_date = _publication_date_from_url(page_url)
    if canonical_url is None or publication_date is None:
        return None
    parser = DomsDetailParser(canonical_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    if parser.post_id is None or not title or not is_opportunity_title(title):
        return None
    content = normalize_text(" ".join(parser.content_parts))
    scope_summary = content[:2000] if content else None
    return DomsTender(
        source_record_id=parser.post_id,
        title=title,
        publication_date=publication_date,
        scope_summary=scope_summary,
        attachments=parser.attachments[:50],
        url=canonical_url,
    )
