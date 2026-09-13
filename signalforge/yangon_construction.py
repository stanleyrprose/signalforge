from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .mpt import SitemapEntry, normalize_text

BASE_URL = "https://www.yangon.gov.mm"
LIST_URL = f"{BASE_URL}/category/ministry-of-construction/"
ISSUER = "Ministry of Construction, Yangon Region"
HOSTS = {"yangon.gov.mm", "www.yangon.gov.mm"}
SELECTION_POLICY_VERSION = 1
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_TENDER_TOKENS = ("တင်ဒါ", "open tender", "invitation to tender")
_EXCLUDE_TOKENS = ("အောင်မြင်", "award", "result", "awarded")


class YangonConstructionParseError(ValueError):
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


def _official_url(raw: str) -> str | None:
    url = urljoin(BASE_URL, raw)
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in HOSTS:
        return None
    if parsed.path.startswith("/category/") or parsed.path.startswith("/author/"):
        return None
    return url


def _is_tender_title(title: str) -> bool:
    value = normalize_text(title).lower()
    return bool(value) and any(t in value for t in _TENDER_TOKENS) and not any(t in value for t in _EXCLUDE_TOKENS)


class _ListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self.article_count = 0
        self._depth = 0
        self._title_depth = 0
        self._title: list[str] = []
        self._url: str | None = None
        self._updated_depth = 0
        self._updated: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        tag = tag.lower()
        classes = _classes(attrs)
        if tag == "article":
            if self._depth:
                self._depth += 1
            else:
                self._depth = 1
                self.article_count += 1
                self._title = []
                self._url = None
                self._updated = []
            return
        if not self._depth:
            return
        if tag == "div":
            self._depth += 1
        if tag in {"h1", "h2", "h3", "h4"} and "entry-title" in classes:
            self._title_depth = 1
            return
        if self._title_depth:
            if tag == "a":
                href = _attr(attrs, "href")
                if href:
                    self._url = _official_url(href)
            if tag not in {"br", "img", "meta", "link", "input"}:
                self._title_depth += 1
        if tag == "span" and "updated" in classes:
            self._updated_depth = 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if not self._depth:
            return
        if self._title_depth and tag in {"h1", "h2", "h3", "h4", "a", "span", "div"}:
            self._title_depth -= 1
        if self._updated_depth and tag == "span":
            self._updated_depth = 0
        if tag == "div" and self._depth > 1:
            self._depth -= 1
            return
        if tag == "article":
            self._depth -= 1
            if self._depth == 0:
                title = normalize_text(" ".join(self._title))
                updated = normalize_text(" ".join(self._updated)) or None
                if self._url and _is_tender_title(title):
                    self.entries.append(SitemapEntry(self._url, updated))

    def handle_data(self, data: str) -> None:
        if self._title_depth:
            value = normalize_text(data)
            if value:
                self._title.append(value)
        if self._updated_depth:
            value = normalize_text(data)
            if value:
                self._updated.append(value)


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = _ListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.article_count == 0:
        raise YangonConstructionParseError("Yangon construction WordPress articles not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


def _numeric_text(value: str) -> str:
    return normalize_text(value).translate(_MYANMAR_DIGITS).replace("ဝ", "0")


def _dates(value: str) -> list[str]:
    out: list[str] = []
    for d, m, y in re.findall(r"(?<!\d)(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(20\d{2})(?!\d)", _numeric_text(value)):
        try:
            out.append(datetime(int(y), int(m), int(d)).date().isoformat())
        except ValueError:
            continue
    return out


def _deadline(value: str) -> str | None:
    normalized = _numeric_text(value)
    for marker in ("တင်ဒါပိတ်မည့်ရက်စွဲ", "တင်ဒါပိတ်မည့်ရက်စွဲ", "တင်ဒါလျှောက်လွှာတင်သွင်းရမည့်", "တင်ဒါတင်သွင်းရမည့်"):
        idx = normalized.find(marker)
        if idx >= 0:
            found = _dates(normalized[idx : idx + 500])
            if found:
                return max(found)
    found = _dates(normalized)
    return max(found) if found else None


def _reference(title: str, post_id: str) -> str:
    value = _numeric_text(title)
    match = re.search(r"(?<!\d)(\d{1,3}/20\d{2}-20\d{2})(?:\s*\(([^)]{1,40})\))?", value)
    if match:
        suffix = f"({normalize_text(match.group(2))})" if match.group(2) else ""
        return f"{match.group(1)}{suffix}"
    return f"YGN-MOC-{post_id}"


class _DetailParser(HTMLParser):
    _VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.content_parts: list[str] = []
        self.updated_parts: list[str] = []
        self.published: str | None = None
        self._title_depth = 0
        self._content_depth = 0
        self._updated_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        tag = tag.lower()
        classes = _classes(attrs)
        if tag == "meta" and _attr(attrs, "property") == "article:published_time":
            self.published = _attr(attrs, "content")
        if tag == "time" and not self.published:
            self.published = _attr(attrs, "datetime")

        if self._title_depth:
            if tag not in self._VOID:
                self._title_depth += 1
        elif tag in {"h1", "h2"} and "entry-title" in classes:
            self._title_depth = 1

        if self._content_depth:
            if tag not in self._VOID:
                self._content_depth += 1
        elif tag == "div" and "entry-content" in classes:
            self._content_depth = 1

        if self._updated_depth:
            if tag not in self._VOID:
                self._updated_depth += 1
        elif tag == "span" and "updated" in classes:
            self._updated_depth = 1

    def handle_endtag(self, tag: str) -> None:
        if self._title_depth:
            self._title_depth -= 1
        if self._content_depth:
            self._content_depth -= 1
        if self._updated_depth:
            self._updated_depth -= 1

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._content_depth:
            self.content_parts.append(value)
        if self._updated_depth:
            self.updated_parts.append(value)


@dataclass(frozen=True)
class YangonConstructionTender:
    post_id: str
    title: str
    publication_date: str | None
    deadline: str | None
    scope_summary: str
    url: str

    item_kind = "TENDER"
    location = "Yangon Region"

    @property
    def reference_no(self) -> str:
        return _reference(self.title, self.post_id)

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def canonical_key(self) -> str:
        return f"yangon-construction:{self.post_id}"

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": "wordpress_post_id_or_explicit_tender_reference",
            "source_record_id": self.post_id,
            "publication_date": self.publication_date,
            "deadline": self.deadline,
            "deadline_evidence": "OFFICIAL_HTML_SUBMISSION_OR_CLOSE_DATE" if self.deadline else "UNKNOWN_NOT_PARSED",
            "location": self.location,
            "scope_summary": self.scope_summary,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "relevance_categories": ["CONSTRUCTION"],
            "detail_completeness": "OFFICIAL_HTML_SCOPE_AND_DEADLINE" if self.deadline else "OFFICIAL_HTML_SCOPE_DEADLINE_UNKNOWN",
            "attachment_policy": "HTML_ONLY_NO_ATTACHMENT_REQUIRED",
            "url": self.url,
        }


def parse_tender_detail(html_bytes: bytes, url: str) -> YangonConstructionTender | None:
    text = html_bytes.decode("utf-8", errors="replace")
    body_match = re.search(r"\bpostid-(\d+)\b", text)
    if body_match is None:
        canonical_match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', text, re.I)
        source = canonical_match.group(1) if canonical_match else url
        post_id = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    else:
        post_id = body_match.group(1)
    parser = _DetailParser()
    parser.feed(text)
    title = normalize_text(" ".join(parser.title_parts))
    scope = normalize_text(" ".join(parser.content_parts))
    if not _is_tender_title(title) or not scope:
        return None
    publication = None
    published_raw = parser.published or normalize_text(" ".join(parser.updated_parts)) or None
    if published_raw:
        try:
            publication = datetime.fromisoformat(published_raw.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            publication = None
    return YangonConstructionTender(
        post_id=post_id,
        title=title,
        publication_date=publication,
        deadline=_deadline(scope),
        scope_summary=scope[:4000],
        url=url,
    )
