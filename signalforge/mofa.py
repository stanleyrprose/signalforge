from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlparse, urlsplit, urlunsplit

from pypdf import PdfReader

from .mpt import SitemapEntry, normalize_text

MOFA_BASE_URL = "https://www.mofa.gov.mm"
MOFA_LIST_URL = f"{MOFA_BASE_URL}/category/announcement/"
MOFA_ISSUER = "Ministry of Foreign Affairs, Myanmar"
MOFA_HOSTS = {"mofa.gov.mm", "www.mofa.gov.mm"}
SELECTION_POLICY_VERSION = 1
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_DATE_RE = re.compile(r"(?P<day>\d{1,2})\s*-\s*(?P<month>\d{1,2})\s*-\s*(?P<year>20\d{2})")
_TIME_RE = re.compile(r"(?<!\d)(?P<hour>\d{1,2})\D{0,8}(?P<minute>\d{2})(?!\d)")

_OPEN_TENDER_TOKENS = (
    "အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
    "အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
    "အိတ်ဖွင့်တင်ဒါတင်သွင်းရန် ဖိတ်ခေါ်",
    "အိတ်ဖွင့်တင်ဒါတင်သွင်းရန် ဖိတ်ခေါ်",
    "open tender",
    "invitation to tender",
)
_EXCLUDE_STAGE_TOKENS = (
    "တင်ဒါအောင်မြင်",
    "နည်းပညာအောင်မြင်",
    "နည်းပညာရမှတ်",
    "ကုမ္ပဏီများစာရင်း",
    "tender award",
    "awarded",
    "result",
)


class MofaParseError(ValueError):
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
    url = urljoin(MOFA_BASE_URL, raw_url)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in MOFA_HOSTS:
        return None
    path = unquote(parsed.path)
    if not re.fullmatch(r"/[^/]+/", path) or path.startswith("/category/"):
        return None
    encoded = quote(path, safe="/%^()_-.")
    return urlunsplit(("https", "www.mofa.gov.mm", encoded, "", ""))


def _encoded_official_attachment(raw_url: str, page_url: str) -> str | None:
    url = urljoin(page_url, raw_url)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in MOFA_HOSTS:
        return None
    if "/wp-content/uploads/" not in parsed.path or not parsed.path.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
        return None
    encoded_path = quote(unquote(parsed.path), safe="/%^()_-.")
    return urlunsplit(("https", "www.mofa.gov.mm", encoded_path, parsed.query, ""))


def is_opportunity_title(title: str) -> bool:
    value = normalize_text(title)
    lower = value.lower()
    if not value or any(token.lower() in lower for token in _EXCLUDE_STAGE_TOKENS):
        return False
    return any(token.lower() in lower for token in _OPEN_TENDER_TOKENS)


class MofaListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self.article_count = 0
        self._article_depth = 0
        self._title_depth = 0
        self._post_id: str | None = None
        self._url: str | None = None
        self._datetime: str | None = None
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "article":
            if self._article_depth:
                self._article_depth += 1
            elif "category-announcement" in classes:
                self._article_depth = 1
                self.article_count += 1
                self._post_id = _post_id_from_attrs(attrs)
                self._url = None
                self._datetime = None
                self._title_parts = []
                self._title_depth = 0
            return
        if not self._article_depth:
            return
        if lowered in {"h1", "h2", "h3", "h4"} and "entry-title" in classes:
            self._title_depth = 1
            return
        if self._title_depth:
            if lowered == "a":
                href = _attr(attrs, "href")
                if href:
                    self._url = _canonical_post_url(href)
            if lowered not in {"br", "img", "input", "meta", "link"}:
                self._title_depth += 1
        if lowered == "time" and "published" in classes and self._datetime is None:
            value = _attr(attrs, "datetime")
            if value:
                self._datetime = value

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._article_depth:
            return
        if self._title_depth and lowered in {"h1", "h2", "h3", "h4", "a", "span", "div"}:
            self._title_depth -= 1
        if lowered == "article":
            self._article_depth -= 1
            if self._article_depth == 0:
                title = normalize_text(" ".join(self._title_parts))
                if self._post_id and self._url and self._datetime and is_opportunity_title(title):
                    self.entries.append(SitemapEntry(self._url, self._datetime))
                self._post_id = None
                self._url = None
                self._datetime = None
                self._title_parts = []
                self._title_depth = 0

    def handle_data(self, data: str) -> None:
        if self._article_depth and self._title_depth:
            value = normalize_text(data)
            if value:
                self._title_parts.append(value)


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = MofaListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.article_count == 0:
        raise MofaParseError("MOFA announcement category structure not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class MofaTender:
    source_record_id: str
    title: str
    publication_date: str
    scope_summary: str | None
    attachment_name: str | None
    attachment_url: str | None
    url: str
    deadline: str | None = None
    deadline_time: str | None = None

    item_kind = "TENDER"
    location = None

    @property
    def reference_no(self) -> str:
        return f"MOFA-POST-{self.source_record_id}"

    @property
    def reference_no_kind(self) -> str:
        return "wordpress_post_id"

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def canonical_key(self) -> str:
        return f"mofa:{self.source_record_id}"

    def payload(self) -> dict[str, object]:
        enriched = self.deadline is not None
        return {
            "item_kind": self.item_kind,
            "issuer": MOFA_ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": self.reference_no_kind,
            "source_record_id": self.source_record_id,
            "publication_date": self.publication_date,
            "deadline": self.deadline,
            "deadline_time": self.deadline_time,
            "deadline_evidence": (
                "OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME" if enriched else "UNKNOWN_NOT_IN_HTML_TEXT"
            ),
            "scope_summary": self.scope_summary,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "attachment_policy": "OPTIONAL_TEXT_PDF_ENRICHMENT" if enriched else "METADATA_ONLY_NON_BLOCKING",
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": (
                "HTML_EVENT_PLUS_TEXT_PDF_SCOPE_DEADLINE" if enriched else "HTML_EVENT_METADATA_ATTACHMENT_ONLY"
            ),
            "url": self.url,
        }


class MofaDetailParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.post_id: str | None = None
        self.publication_datetime: str | None = None
        self._article_depth = 0
        self._title_depth = 0
        self._content_depth = 0
        self._current_pdf_url: str | None = None
        self.title_parts: list[str] = []
        self.content_parts: list[str] = []
        self.attachment_url: str | None = None
        self.attachment_name: str | None = None

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
        if lowered in {"h1", "h2"} and "entry-title" in classes:
            self._title_depth = 1
            return
        if lowered == "div" and "entry-content" in classes:
            self._content_depth = 1
            return
        if lowered == "time" and "published" in classes and self.publication_datetime is None:
            value = _attr(attrs, "datetime")
            if value:
                self.publication_datetime = value
        if self._title_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._title_depth += 1
        if self._content_depth:
            if lowered in {"a", "object", "img"} and self.attachment_url is None:
                if lowered == "a":
                    raw = _attr(attrs, "href")
                elif lowered == "object":
                    raw = _attr(attrs, "data")
                else:
                    raw = _attr(attrs, "src")
                if raw:
                    encoded = _encoded_official_attachment(raw, self.page_url)
                    if encoded:
                        self._current_pdf_url = encoded
                        self.attachment_url = encoded
                        self.attachment_name = unquote(urlparse(encoded).path.rsplit("/", 1)[-1])
            if lowered not in {"br", "img", "input", "meta", "link"}:
                self._content_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._article_depth:
            return
        if self._title_depth and lowered in {"h1", "h2", "a", "span", "div"}:
            self._title_depth -= 1
        if self._content_depth and lowered in {"div", "p", "a", "object", "span", "li", "ul", "ol", "strong", "em"}:
            self._content_depth -= 1
        if lowered == "article":
            self._article_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._article_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._content_depth and value.lower() not in {"download", "tender announcement"}:
            self.content_parts.append(value)


def parse_tender_detail(html_bytes: bytes, page_url: str) -> MofaTender | None:
    canonical_url = _canonical_post_url(page_url)
    if canonical_url is None:
        return None
    parser = MofaDetailParser(canonical_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    if parser.post_id is None or parser.publication_datetime is None or not title or not is_opportunity_title(title):
        return None
    publication_date = parser.publication_datetime[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", publication_date):
        return None
    content = normalize_text(" ".join(parser.content_parts))
    scope_summary = content[:2000] if content else None
    return MofaTender(
        source_record_id=parser.post_id,
        title=title,
        publication_date=publication_date,
        scope_summary=scope_summary,
        attachment_name=parser.attachment_name,
        attachment_url=parser.attachment_url,
        url=canonical_url,
    )


def extract_tender_pdf_urls(html_bytes: bytes, page_url: str) -> list[str]:
    tender = parse_tender_detail(html_bytes, page_url)
    if tender is None or not tender.attachment_url or not tender.attachment_url.lower().endswith(".pdf"):
        return []
    return [tender.attachment_url]


def _pdf_deadline(text: str) -> tuple[str | None, str | None]:
    translated = text.translate(_MYANMAR_DIGITS)
    candidates: list[datetime] = []
    for date_match in _DATE_RE.finditer(translated):
        tail = translated[date_match.end(): date_match.end() + 60]
        time_match = _TIME_RE.search(tail)
        if time_match is None:
            continue
        try:
            candidate = datetime(
                int(date_match.group("year")),
                int(date_match.group("month")),
                int(date_match.group("day")),
                int(time_match.group("hour")),
                int(time_match.group("minute")),
            )
        except ValueError:
            continue
        candidates.append(candidate)
    if not candidates:
        return None, None
    deadline = max(candidates)
    return deadline.date().isoformat(), deadline.strftime("%H:%M")


def _pdf_scope_summary(base_scope: str | None, text: str) -> str | None:
    parts: list[str] = []
    if base_scope:
        parts.append(base_scope)
    for raw in text.translate(_MYANMAR_DIGITS).splitlines():
        value = normalize_text(raw)
        if not value or not re.search(r"[A-Za-z]", value):
            continue
        lower = value.lower()
        if "http://" in lower or "https://" in lower or "website" in lower:
            continue
        parts.append(value)
    summary = " | ".join(dict.fromkeys(parts))
    return summary[:2400] if summary else None


def parse_tender_detail_with_attachments(
    html_bytes: bytes,
    page_url: str,
    attachments: list[tuple[str, bytes]],
) -> list[object]:
    base = parse_tender_detail(html_bytes, page_url)
    if base is None:
        return []
    if not attachments:
        return [base]
    if len(attachments) != 1 or base.attachment_url is None:
        raise MofaParseError("MOFA optional attachment set is invalid")
    attachment_url, pdf_bytes = attachments[0]
    if attachment_url != base.attachment_url:
        raise MofaParseError("MOFA attachment URL mismatch")
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return [base]
    if not normalize_text(text):
        return [base]
    deadline, deadline_time = _pdf_deadline(text)
    if deadline is None:
        return [base]
    return [
        MofaTender(
            source_record_id=base.source_record_id,
            title=base.title,
            publication_date=base.publication_date,
            scope_summary=_pdf_scope_summary(base.scope_summary, text),
            attachment_name=base.attachment_name,
            attachment_url=base.attachment_url,
            url=base.url,
            deadline=deadline,
            deadline_time=deadline_time,
        )
    ]
