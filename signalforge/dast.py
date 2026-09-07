from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from .mpt import SitemapEntry, normalize_text, parse_date

DAST_BASE_URL = "https://www.dast.gov.mm"
DAST_LIST_URL = f"{DAST_BASE_URL}/category/tender/"
DAST_ISSUER = "Department of Advanced Science and Technology, Ministry of Science and Technology, Myanmar"
_DAST_HOSTS = {"dast.edu.mm", "www.dast.edu.mm", "dast.gov.mm", "www.dast.gov.mm"}
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_DMY_RE = re.compile(r"(?P<day>[၀-၉0-9]{1,2})\s*[-/.]\s*(?P<month>[၀-၉0-9]{1,2})\s*[-/.]\s*(?P<year>[၀-၉0-9]{4})")
_VOID_TAGS = {"br", "img", "input", "meta", "link", "hr", "source", "area", "base", "embed", "param", "track", "wbr"}


class DastParseError(ValueError):
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
    element_id = _attr(attrs, "id") or ""
    match = re.fullmatch(r"post-(\d+)", element_id)
    if match:
        return match.group(1)
    for cls in _classes(attrs):
        match = re.fullmatch(r"post-(\d+)", cls)
        if match:
            return match.group(1)
    return None


def _canonical_detail_url(post_id: str) -> str:
    if not re.fullmatch(r"\d+", post_id):
        raise ValueError("invalid DAST post id")
    return f"{DAST_BASE_URL}/?p={post_id}"


def _post_id_from_url(raw_url: str) -> str | None:
    parsed = urlsplit(raw_url)
    if parsed.scheme != "https" or parsed.hostname not in _DAST_HOSTS or parsed.username or parsed.password:
        return None
    if parsed.port not in (None, 443) or parsed.path not in {"", "/"} or parsed.fragment:
        return None
    match = re.fullmatch(r"p=(\d+)", parsed.query)
    return match.group(1) if match else None


def _canonical_attachment(raw_url: str, page_url: str) -> str | None:
    absolute = urljoin(page_url, raw_url)
    parsed = urlsplit(absolute)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in _DAST_HOSTS or parsed.username or parsed.password:
        return None
    if parsed.port not in (None, 80, 443) or parsed.fragment:
        return None
    path = unquote(parsed.path)
    if not path.lower().startswith("/wp-content/uploads/") or not path.lower().endswith(".pdf"):
        return None
    encoded_path = quote(path, safe="/%()_-.,'[]")
    return urlunsplit(("https", "www.dast.gov.mm", encoded_path, parsed.query, ""))


def _parse_dmy(value: str) -> date | None:
    match = _DMY_RE.search(value)
    if match is None:
        return None
    try:
        return date(
            int(match.group("year").translate(_MYANMAR_DIGITS)),
            int(match.group("month").translate(_MYANMAR_DIGITS)),
            int(match.group("day").translate(_MYANMAR_DIGITS)),
        )
    except ValueError:
        return None


def _all_dmy(value: str) -> list[date]:
    result: list[date] = []
    for match in _DMY_RE.finditer(value):
        parsed = _parse_dmy(match.group(0))
        if parsed is not None:
            result.append(parsed)
    return result


def _extract_deadline(content: str) -> str | None:
    clean = normalize_text(content)
    explicit = re.search(r"နောက်ဆုံး\s*တင်သွင်းရမည့်ရက်", clean)
    if explicit:
        parsed = _parse_dmy(clean[explicit.end() : explicit.end() + 250])
        if parsed is not None:
            return parsed.isoformat()

    section_two = re.search(r"၂။(?P<body>.*?)(?:၃။|$)", clean)
    if section_two:
        body = section_two.group("body")
        if "တင်သွင်း" in body and ("ပြန်လည်" in body or "နောက်ဆုံး" in body):
            dates = _all_dmy(body)
            if dates:
                return max(dates).isoformat()

    generic = re.search(r"နောက်ဆုံး.{0,80}?တင်သွင်း", clean)
    if generic:
        parsed = _parse_dmy(clean[generic.start() : generic.end() + 250])
        if parsed is not None:
            return parsed.isoformat()
    return None


def _extract_scope(content: str) -> str | None:
    clean = normalize_text(content)
    match = re.search(r"၁။(?P<body>.*?)(?:၂။|$)", clean)
    if match:
        value = normalize_text(match.group("body"))
        return value[:5000] if value else None
    return clean[:5000] if clean else None


class DastListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self.tender_article_count = 0
        self._article_depth = 0
        self._post_id: str | None = None
        self._title_depth = 0
        self._date_depth = 0
        self._title_parts: list[str] = []
        self._date_parts: list[str] = []
        self._date_value: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "article":
            if self._article_depth:
                self._article_depth += 1
            elif "category-tender" in classes:
                self._article_depth = 1
                self.tender_article_count += 1
                self._post_id = _post_id_from_attrs(attrs)
                self._title_parts = []
                self._date_parts = []
                self._date_value = None
            return
        if not self._article_depth:
            return
        if lowered in {"h1", "h2", "h3", "h4", "h5", "h6"} and "elementor-post__title" in classes:
            self._title_depth = 1
            return
        if lowered == "time" and self._date_value is None:
            value = _attr(attrs, "datetime")
            if value:
                self._date_value = value
        if lowered == "span" and "elementor-post-date" in classes and self._date_depth == 0:
            self._date_depth = 1
            self._date_parts = []
            return
        if self._date_depth and lowered not in _VOID_TAGS:
            self._date_depth += 1
        if self._title_depth and lowered not in _VOID_TAGS:
            self._title_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._article_depth:
            return
        if self._title_depth and lowered not in _VOID_TAGS:
            self._title_depth -= 1
        if self._date_depth and lowered not in _VOID_TAGS:
            self._date_depth -= 1
        if lowered == "article":
            self._article_depth -= 1
            if self._article_depth == 0:
                title = normalize_text(" ".join(self._title_parts))
                lastmod = self._date_value
                if lastmod is None and self._date_parts:
                    visible_date = parse_date(" ".join(self._date_parts))
                    if visible_date:
                        lastmod = f"{visible_date}T00:00:00+06:30"
                if self._post_id and title and lastmod and "တင်ဒါ" in title:
                    self.entries.append(SitemapEntry(_canonical_detail_url(self._post_id), lastmod))
                self._post_id = None
                self._title_parts = []
                self._date_parts = []
                self._date_value = None
                self._title_depth = 0
                self._date_depth = 0

    def handle_data(self, data: str) -> None:
        if not self._article_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self._title_parts.append(value)
        if self._date_depth:
            self._date_parts.append(value)

def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = DastListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.tender_article_count == 0:
        raise DastParseError("DAST tender archive article structure not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class DastTender:
    source_record_id: str
    title: str
    publication_date: str
    deadline: str | None
    scope_summary: str
    attachment_urls: tuple[str, ...]
    url: str

    item_kind = "TENDER"
    location = None

    @property
    def canonical_key(self) -> str:
        return f"dast:{self.source_record_id}"

    @property
    def reference_no(self) -> str:
        return f"DAST-POST-{self.source_record_id}"

    @property
    def reference_no_kind(self) -> str:
        return "wordpress_post_id"

    @property
    def project_name(self) -> str:
        return self.scope_summary[:500]

    def payload(self) -> dict[str, object]:
        names = [unquote(urlsplit(url).path.rsplit("/", 1)[-1]) for url in self.attachment_urls]
        return {
            "item_kind": self.item_kind,
            "issuer": DAST_ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": self.reference_no_kind,
            "source_record_id": self.source_record_id,
            "publication_date": self.publication_date,
            "publication_date_evidence": "WORDPRESS_TIME_PUBLISHED",
            "deadline": self.deadline,
            "deadline_evidence": "EXPLICIT_HTML_SUBMISSION_DATE" if self.deadline else "UNKNOWN_NOT_UNAMBIGUOUS_IN_HTML",
            "location": None,
            "scope_summary": self.scope_summary,
            "attachment_names": names,
            "attachment_urls": list(self.attachment_urls),
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "locator_rewrite": "issuer_legacy_dast.edu.mm_post_id_to_www.dast.gov.mm",
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "HTML_SCOPE_AND_DEADLINE_ATTACHMENT_METADATA_ONLY",
            "url": self.url,
        }


class DastDetailParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.post_id: str | None = None
        self.publication_datetime: str | None = None
        self.title_parts: list[str] = []
        self.content_parts: list[str] = []
        self.attachment_urls: list[str] = []
        self._article_depth = 0
        self._title_depth = 0
        self._content_depth = 0
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
        if lowered == "article":
            if self._article_depth:
                self._article_depth += 1
            else:
                post_id = _post_id_from_attrs(attrs)
                if post_id and "category-tender" in classes:
                    self._article_depth = 1
                    self.post_id = post_id
            return
        if not self._article_depth:
            return
        if lowered == "h1" and "entry-title" in classes:
            self._title_depth = 1
            return
        if lowered == "time" and "published" in classes and self.publication_datetime is None:
            value = _attr(attrs, "datetime")
            if value:
                self.publication_datetime = value
        if lowered == "div" and "entry-content" in classes and self._content_depth == 0:
            self._content_depth = 1
            return
        if self._title_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._title_depth += 1
        if self._content_depth:
            if lowered == "a":
                href = _attr(attrs, "href")
                if href:
                    attachment = _canonical_attachment(href, self.page_url)
                    if attachment and attachment not in self.attachment_urls:
                        self.attachment_urls.append(attachment)
            if lowered not in _VOID_TAGS:
                self._content_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._ignore_depth:
            self._ignore_depth -= 1
            return
        if not self._article_depth:
            return
        if self._title_depth and lowered == "h1":
            self._title_depth = 0
        elif self._title_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._title_depth = max(1, self._title_depth - 1)
        if self._content_depth and lowered not in _VOID_TAGS:
            self._content_depth -= 1
        if lowered == "article":
            self._article_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignore_depth or not self._article_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._content_depth:
            self.content_parts.append(value)


def parse_tender_detail(html_bytes: bytes, page_url: str) -> DastTender | None:
    source_record_id = _post_id_from_url(page_url)
    if source_record_id is None:
        return None
    canonical_url = _canonical_detail_url(source_record_id)
    parser = DastDetailParser(canonical_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.post_id != source_record_id or parser.publication_datetime is None:
        return None
    title = normalize_text(" ".join(parser.title_parts))
    content = normalize_text(" ".join(parser.content_parts))
    scope = _extract_scope(content)
    publication_date = parser.publication_datetime[:10]
    if not title or "တင်ဒါ" not in title or scope is None or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", publication_date):
        return None
    return DastTender(
        source_record_id=source_record_id,
        title=title,
        publication_date=publication_date,
        deadline=_extract_deadline(content),
        scope_summary=scope,
        attachment_urls=tuple(parser.attachment_urls),
        url=canonical_url,
    )
