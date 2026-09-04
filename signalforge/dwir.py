from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlparse, urlsplit, urlunsplit

from .mpt import SitemapEntry, normalize_text

DWIR_BASE_URL = "https://www.dwir.gov.mm"
DWIR_HOME_URL = f"{DWIR_BASE_URL}/"
DWIR_ISSUER = "Directorate of Water Resources and Improvement of River Systems, Ministry of Transport"
DWIR_HOSTS = {"dwir.gov.mm", "www.dwir.gov.mm"}

_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_DETAIL_PATH_RE = re.compile(r"^/index\.php/news-events/dwir-news/(?P<id>\d+)(?:-[^/?#]+)?/?$")
_TENDER_REFERENCE_RE = re.compile(
    r"tender\s*no\.?\s*(?P<prefix>\(\s*\d+\s*\)\s*[A-Z&]*)?\s*[./]?\s*"
    r"(?P<year1>20\d{2})\s*[/\-]\s*(?P<year2>20\d{2})",
    re.I,
)
_ENGLISH_DATE_FORMATS = ("%d %B %Y", "%d %b %Y")
_OUTCOME_TOKENS = (
    "တင်ဒါအောင်",
    "အောင်မြင်သူ",
    "အောင်စာရင်း",
    "winner",
    "award",
    "awarded",
    "result",
)
_TENDER_TOKENS = ("tender", "တင်ဒါ", "အိတ်ဖွင်", "အိတ်ဖွင့်")
_GENERIC_TITLES = {"tender", "open tender", "အိတ်ဖွင့်တင်ဒါ", "အိတ်ဖွင့်တင်ဒါ", "တင်ဒါခေါ်ယူခြင်း"}


class DwirParseError(ValueError):
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


def _parse_visible_date(value: str) -> str | None:
    clean = normalize_text(value).translate(_MYANMAR_DIGITS)
    for fmt in _ENGLISH_DATE_FORMATS:
        try:
            return datetime.strptime(clean, fmt).date().isoformat()
        except ValueError:
            continue
    match = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})\b", clean)
    if match:
        for fmt in _ENGLISH_DATE_FORMATS:
            try:
                return datetime.strptime(" ".join(match.groups()), fmt).date().isoformat()
            except ValueError:
                continue
    return None


def _listing_lastmod(date_value: str | None) -> str | None:
    return f"{date_value}T00:00:00+06:30" if date_value else None


def _canonical_detail_url(raw_url: str) -> str | None:
    absolute = urljoin(DWIR_BASE_URL, raw_url)
    parsed = urlsplit(absolute)
    if parsed.scheme != "https" or parsed.hostname not in DWIR_HOSTS or parsed.username or parsed.password:
        return None
    if parsed.port not in (None, 443) or parsed.query or parsed.fragment:
        return None
    decoded_path = unquote(parsed.path)
    if _DETAIL_PATH_RE.fullmatch(decoded_path) is None:
        return None
    encoded_path = quote(decoded_path, safe="/%:@-._~()")
    return urlunsplit(("https", "www.dwir.gov.mm", encoded_path, "", ""))


def _source_record_id(url: str) -> str | None:
    parsed = urlparse(url)
    match = _DETAIL_PATH_RE.fullmatch(unquote(parsed.path))
    return match.group("id") if match else None


def is_opportunity_title(value: str) -> bool:
    clean = normalize_text(value)
    lower = clean.lower()
    if not clean:
        return False
    if any(token.lower() in lower for token in _OUTCOME_TOKENS):
        return False
    return any(token.lower() in lower for token in _TENDER_TOKENS)


def _normalized_reference(value: str) -> str | None:
    clean = normalize_text(value).translate(_MYANMAR_DIGITS)
    clean = re.sub(r"(?<=\d)\s+(?=\d)", "", clean)
    match = _TENDER_REFERENCE_RE.search(clean)
    if match is None:
        return None
    prefix = re.sub(r"\s+", "", match.group("prefix") or "")
    return f"TENDER No.{prefix}/{match.group('year1')}-{match.group('year2')}"


class DwirHomepageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self.latest_module_seen = False
        self._module_title_depth = 0
        self._module_title_parts: list[str] = []
        self._intro_depth = 0
        self._list_item_depth = 0
        self._anchor_depth = 0
        self._anchor_href: str | None = None
        self._anchor_parts: list[str] = []
        self._date_depth = 0
        self._date_parts: list[str] = []
        self._container_parts: list[str] = []
        self._container_url: str | None = None
        self._container_title: str | None = None

    def _reset_container(self) -> None:
        self._container_parts = []
        self._container_url = None
        self._container_title = None
        self._date_parts = []
        self._date_depth = 0

    def _finish_container(self) -> None:
        if not self._container_url or not self._container_title or not is_opportunity_title(self._container_title):
            self._reset_container()
            return
        date_text = normalize_text(" ".join(self._date_parts or self._container_parts))
        visible_date = _parse_visible_date(date_text)
        self.entries.append(SitemapEntry(self._container_url, _listing_lastmod(visible_date)))
        self._reset_container()

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "h3" and "module-title" in classes:
            self._module_title_depth = 1
            self._module_title_parts = []
            return
        if self._module_title_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._module_title_depth += 1

        if lowered == "div":
            if self._intro_depth:
                self._intro_depth += 1
            elif "div_lnd_intro" in classes:
                self._intro_depth = 1
                self._reset_container()

        if lowered == "li":
            if self._list_item_depth:
                self._list_item_depth += 1
            elif "lnd_latestnews" in classes:
                self._list_item_depth = 1
                self._reset_container()
                self.latest_module_seen = True

        if (self._intro_depth or self._list_item_depth) and lowered == "a":
            href = _attr(attrs, "href")
            if href and ({"lndtitle", "latestnews"} & classes):
                canonical = _canonical_detail_url(href)
                if canonical:
                    self._anchor_depth = 1
                    self._anchor_href = canonical
                    self._anchor_parts = []

        if self._intro_depth and lowered == "span" and "lnd_introdate" in classes:
            self._date_depth = 1
            self._date_parts = []
        elif self._date_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._date_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._module_title_depth and lowered == "h3":
            text = normalize_text(" ".join(self._module_title_parts)).lower()
            if "latest news" in text and "bulletin" in text:
                self.latest_module_seen = True
            self._module_title_depth = 0

        if self._anchor_depth and lowered == "a":
            title = normalize_text(" ".join(self._anchor_parts))
            if self._anchor_href and title:
                self._container_url = self._anchor_href
                self._container_title = title
            self._anchor_depth = 0
            self._anchor_href = None
            self._anchor_parts = []

        if self._date_depth and lowered == "span":
            self._date_depth = 0

        if lowered == "div" and self._intro_depth:
            self._intro_depth -= 1
            if self._intro_depth == 0:
                self.latest_module_seen = True
                self._finish_container()

        if lowered == "li" and self._list_item_depth:
            self._list_item_depth -= 1
            if self._list_item_depth == 0:
                self._finish_container()

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._module_title_depth:
            self._module_title_parts.append(value)
        if self._intro_depth or self._list_item_depth:
            self._container_parts.append(value)
        if self._anchor_depth:
            self._anchor_parts.append(value)
        if self._date_depth:
            self._date_parts.append(value)


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = DwirHomepageParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if not parser.latest_module_seen:
        raise DwirParseError("DWIR Latest News bulletin structure not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        record_id = _source_record_id(entry.url)
        if record_id and record_id not in dedup:
            dedup[record_id] = entry
    return list(dedup.values())


@dataclass(frozen=True)
class DwirTender:
    source_record_id: str
    title: str
    publication_date: str
    scope_summary: str | None
    embedded_image_count: int
    url: str
    reference_no: str
    reference_no_kind: str

    item_kind = "TENDER"
    deadline = None
    location = None

    @property
    def canonical_key(self) -> str:
        return f"dwir:{self.source_record_id}"

    @property
    def project_name(self) -> str:
        if self.scope_summary and self.title.lower() in _GENERIC_TITLES:
            return self.scope_summary[:500]
        return self.scope_summary[:500] if self.scope_summary else self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": DWIR_ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": self.reference_no_kind,
            "source_record_id": self.source_record_id,
            "publication_date": self.publication_date,
            "deadline": None,
            "deadline_evidence": "UNKNOWN_NOT_IN_HTML_TEXT",
            "scope_summary": self.scope_summary,
            "embedded_image_count": self.embedded_image_count,
            "embedded_image_policy": "UNPARSED_NON_BLOCKING",
            "detail_completeness": "HTML_TEXT_PARTIAL_EMBEDDED_IMAGE_UNPARSED",
            "business_stage": "OPPORTUNITY",
            "url": self.url,
        }


class DwirDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.date_parts: list[str] = []
        self.embedded_image_count = 0
        self._title_depth = 0
        self._body_depth = 0
        self._date_depth = 0
        self._ignore_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if self._ignore_depth:
            self._ignore_depth += 1
            return
        if lowered in {"script", "style", "noscript"}:
            self._ignore_depth = 1
            return
        if lowered in {"h1", "h2"} and "article-title" in classes:
            self._title_depth = 1
            return
        if lowered == "section" and _attr(attrs, "itemprop") == "articleBody":
            self._body_depth = 1
            return
        if lowered == "time" and _attr(attrs, "itemprop") == "datePublished":
            self._date_depth = 1
            return
        if self._body_depth and lowered == "img":
            src = _attr(attrs, "src") or ""
            if src.startswith("data:image/"):
                self.embedded_image_count += 1
        if self._title_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._title_depth += 1
        if self._body_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._body_depth += 1
        if self._date_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._date_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._ignore_depth:
            self._ignore_depth -= 1
            return
        if self._title_depth and lowered in {"h1", "h2", "a", "span", "div"}:
            self._title_depth -= 1
        if self._body_depth and lowered in {"section", "div", "p", "a", "span", "li", "ul", "ol", "strong", "em"}:
            self._body_depth -= 1
        if self._date_depth and lowered == "time":
            self._date_depth = 0

    def handle_data(self, data: str) -> None:
        if self._ignore_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._body_depth:
            self.body_parts.append(value)
        if self._date_depth:
            self.date_parts.append(value)


def parse_tender_detail(html_bytes: bytes, page_url: str) -> DwirTender | None:
    canonical_url = _canonical_detail_url(page_url)
    source_record_id = _source_record_id(canonical_url or "")
    if canonical_url is None or source_record_id is None:
        return None
    parser = DwirDetailParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    body = normalize_text(" ".join(parser.body_parts))
    if not title or not is_opportunity_title(f"{title} {body}"):
        return None
    publication_date = _parse_visible_date(" ".join(parser.date_parts))
    if publication_date is None:
        return None
    reference = _normalized_reference(f"{title} {body}")
    return DwirTender(
        source_record_id=source_record_id,
        title=title,
        publication_date=publication_date,
        scope_summary=body[:2000] if body else None,
        embedded_image_count=parser.embedded_image_count,
        url=canonical_url,
        reference_no=reference or f"DWIR-POST-{source_record_id}",
        reference_no_kind="issuer_tender_reference" if reference else "joomla_article_id",
    )
