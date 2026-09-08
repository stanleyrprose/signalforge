from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlparse, urlsplit, urlunsplit

from pypdf import PdfReader

from .mpt import SitemapEntry, normalize_text

MOL_BASE_URL = "https://www.mol.gov.mm"
MOL_LIST_URL = f"{MOL_BASE_URL}/tender/"
MOL_HOST = "www.mol.gov.mm"
MOL_ISSUER = "Ministry of Labour, Myanmar"
SELECTION_POLICY_VERSION = 1
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")

_OPEN_TENDER_TOKENS = (
    "အိတ်ဖွင့်တင်ဒါ",
    "အိတ်ဖွင့်တင်ဒါ",
    "တင်ဒါခေါ်ယူခြင်း",
    "တင်ဒါခေါ်ယူ",
    "တင်ဒါ တင်သွင်းရန် ဖိတ်ခေါ်",
    "တင်ဒါတင်သွင်းရန် ဖိတ်ခေါ်",
    "open tender",
    "invitation to tender",
)
_EXCLUDE_STAGE_TOKENS = (
    "တင်ဒါအောင်မြင်",
    "နည်းပညာအောင်မြင်",
    "နည်းပညာရမှတ်",
    "ကုမ္ပဏီများစာရင်း",
    "အောင်စာရင်း",
    "နောက်ဆက်တွဲ",
    "tender award",
    "awarded",
    "result",
)
_DATE_RE = re.compile(r"(?P<day>\d{1,2})\s*-\s*(?P<month>\d{1,2})\s*-\s*(?P<year>20\d{2})")
_TIME_RE = re.compile(r"(?<!\d)(?P<hour>\d{1,2})\D{0,4}(?P<minute>\d{2})(?!\d)")


class MolParseError(ValueError):
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


def _void(tag: str) -> bool:
    return tag in {"br", "img", "input", "meta", "link", "hr", "embed", "source", "area", "base", "col", "param", "track", "wbr"}


def _canonical_post_url(raw_url: str) -> str | None:
    url = urljoin(MOL_BASE_URL, raw_url)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != MOL_HOST:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.params or parsed.query or parsed.fragment:
        return None
    path = unquote(parsed.path)
    if not path.startswith("/") or path in {"/", "/tender", "/tender/"} or path.startswith("/tender/?"):
        return None
    encoded = quote(path, safe="/%^()_-.")
    return urlunsplit(("https", MOL_HOST, encoded, "", ""))


def _canonical_pdf_url(raw_url: str, page_url: str) -> str | None:
    url = urljoin(page_url, raw_url)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != MOL_HOST:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.query or parsed.fragment:
        return None
    path = unquote(parsed.path)
    if not path.startswith("/wp-content/uploads/") or not path.lower().endswith(".pdf"):
        return None
    encoded = quote(path, safe="/%^()_-.")
    return urlunsplit(("https", MOL_HOST, encoded, "", ""))


def is_opportunity_title(title: str) -> bool:
    value = normalize_text(title)
    lower = value.lower()
    if not value or any(token.lower() in lower for token in _EXCLUDE_STAGE_TOKENS):
        return False
    return any(token.lower() in lower for token in _OPEN_TENDER_TOKENS)


class MolListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self.card_count = 0
        self._card_depth = 0
        self._title_depth = 0
        self._post_id: str | None = None
        self._url: str | None = None
        self._datetime: str | None = None
        self._title_parts: list[str] = []

    def _reset(self) -> None:
        self._title_depth = 0
        self._post_id = None
        self._url = None
        self._datetime = None
        self._title_parts = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "div" and "pt-cv-content-item" in classes and self._card_depth == 0:
            post_id = _attr(attrs, "data-pid")
            if post_id and post_id.isdigit():
                self._card_depth = 1
                self.card_count += 1
                self._reset()
                self._post_id = post_id
                return
        if not self._card_depth:
            return
        if lowered == "h6" and "pt-cv-title" in classes and self._title_depth == 0:
            self._title_depth = 1
        elif self._title_depth and not _void(lowered):
            self._title_depth += 1
        if self._title_depth and lowered == "a" and self._url is None:
            href = _attr(attrs, "href")
            if href:
                self._url = _canonical_post_url(href)
        if lowered == "time" and self._datetime is None:
            value = _attr(attrs, "datetime")
            if value:
                self._datetime = value
        if not _void(lowered):
            self._card_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._card_depth:
            return
        if self._title_depth and not _void(lowered):
            self._title_depth -= 1
        if not _void(lowered):
            self._card_depth -= 1
        if self._card_depth == 0:
            title = normalize_text(" ".join(self._title_parts))
            if self._post_id and self._url and self._datetime and is_opportunity_title(title):
                self.entries.append(SitemapEntry(self._url, self._datetime))
            self._reset()

    def handle_data(self, data: str) -> None:
        if self._card_depth and self._title_depth:
            value = normalize_text(data)
            if value:
                self._title_parts.append(value)


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = MolListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise MolParseError("Ministry of Labour tender cards not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class MolDetailMetadata:
    post_id: str
    title: str
    publication_date: str
    pdf_url: str
    url: str


class MolDetailParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.post_id: str | None = None
        self.title_parts: list[str] = []
        self.date_parts: list[str] = []
        self.pdf_urls: list[str] = []
        self._title_depth = 0
        self._date_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "body":
            for value in classes:
                match = re.fullmatch(r"postid-(\d+)", value)
                if match:
                    self.post_id = match.group(1)
                    break
        if lowered == "h1" and {"title", "single"}.issubset(classes) and self._title_depth == 0:
            self._title_depth = 1
        elif self._title_depth and not _void(lowered):
            self._title_depth += 1
        if lowered == "span" and "mg-blog-date" in classes and self._date_depth == 0:
            self._date_depth = 1
        elif self._date_depth and not _void(lowered):
            self._date_depth += 1
        if lowered == "object" and (_attr(attrs, "type") or "").lower() == "application/pdf":
            data = _attr(attrs, "data")
            if data:
                pdf = _canonical_pdf_url(data, self.page_url)
                if pdf:
                    self.pdf_urls.append(pdf)
        if lowered == "a":
            href = _attr(attrs, "href") or ""
            if href.lower().endswith(".pdf"):
                pdf = _canonical_pdf_url(href, self.page_url)
                if pdf:
                    self.pdf_urls.append(pdf)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._title_depth and not _void(lowered):
            self._title_depth -= 1
        if self._date_depth and not _void(lowered):
            self._date_depth -= 1

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._date_depth:
            self.date_parts.append(value)


def _publication_date(text: str) -> str | None:
    value = normalize_text(text)
    match = re.search(r"\b([A-Za-z]{3})\s+(\d{1,2}),\s*(20\d{2})\b", value)
    if match is None:
        return None
    try:
        parsed = datetime.strptime(f"{match.group(1)} {match.group(2)} {match.group(3)}", "%b %d %Y")
    except ValueError:
        return None
    return parsed.date().isoformat()


def parse_detail_metadata(html_bytes: bytes, page_url: str) -> MolDetailMetadata | None:
    canonical_url = _canonical_post_url(page_url)
    if canonical_url is None:
        return None
    parser = MolDetailParser(canonical_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    publication_date = _publication_date(" ".join(parser.date_parts))
    pdfs = list(dict.fromkeys(parser.pdf_urls))
    if parser.post_id is None or not is_opportunity_title(title) or publication_date is None or len(pdfs) != 1:
        return None
    return MolDetailMetadata(parser.post_id, title, publication_date, pdfs[0], canonical_url)


def extract_tender_pdf_urls(html_bytes: bytes, page_url: str) -> list[str]:
    metadata = parse_detail_metadata(html_bytes, page_url)
    return [metadata.pdf_url] if metadata is not None else []


def _deadline(text: str) -> tuple[str | None, str | None]:
    translated = text.translate(_MYANMAR_DIGITS)
    matches = list(_DATE_RE.finditer(translated))
    if not matches:
        return None, None
    match = matches[-1]
    try:
        parsed = datetime(int(match.group("year")), int(match.group("month")), int(match.group("day")))
    except ValueError:
        return None, None
    tail = translated[match.end(): match.end() + 160]
    deadline_time: str | None = None
    for time_match in _TIME_RE.finditer(tail):
        hour = int(time_match.group("hour"))
        minute = int(time_match.group("minute"))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            context = tail[max(0, time_match.start() - 40): time_match.start()]
            if hour < 12 and any(token in context for token in ("ညနေ", "ညရန", "ညရေ")):
                hour += 12
            deadline_time = f"{hour:02d}:{minute:02d}"
            break
    return parsed.date().isoformat(), deadline_time


def _scope_summary(title: str, text: str) -> str:
    parts = [normalize_text(title)]
    for raw in text.translate(_MYANMAR_DIGITS).splitlines():
        value = normalize_text(raw)
        if not value or not re.search(r"[A-Za-z]", value):
            continue
        lower = value.lower()
        if "http://" in lower or "https://" in lower or "website" in lower:
            continue
        parts.append(value)
    return " | ".join(dict.fromkeys(parts))[:2400]


@dataclass(frozen=True)
class MolTender:
    post_id: str
    title: str
    publication_date: str
    scope_summary: str
    deadline: str
    deadline_time: str | None
    attachment_url: str
    url: str
    business_unit: str | None

    item_kind = "TENDER"
    location = None

    @property
    def canonical_key(self) -> str:
        return f"mol:{self.post_id}"

    @property
    def reference_no(self) -> str:
        return f"MOL-POST-{self.post_id}"

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": MOL_ISSUER,
            "business_unit": self.business_unit,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "wordpress_post_id",
            "source_record_id": self.post_id,
            "publication_date": self.publication_date,
            "publication_date_evidence": "DETAIL_VISIBLE_MON_DD_YYYY",
            "scope_summary": self.scope_summary,
            "deadline": self.deadline,
            "deadline_time": self.deadline_time,
            "deadline_evidence": "OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME",
            "attachment_urls": [self.attachment_url],
            "attachment_policy": "SINGLE_TEXT_PDF_REQUIRED",
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "HTML_POST_ID_PUBLICATION_PLUS_TEXT_PDF_SCOPE_DEADLINE",
            "url": self.url,
        }


def parse_tender_detail_with_attachments(
    html_bytes: bytes,
    page_url: str,
    attachments: list[tuple[str, bytes]],
) -> list[object]:
    metadata = parse_detail_metadata(html_bytes, page_url)
    if metadata is None or len(attachments) != 1:
        return []
    attachment_url, pdf_bytes = attachments[0]
    if attachment_url != metadata.pdf_url:
        raise MolParseError("Ministry of Labour attachment URL mismatch")
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:
        raise MolParseError("Ministry of Labour PDF parse failed") from exc
    if not normalize_text(text):
        raise MolParseError("Ministry of Labour PDF contains no extractable text")
    deadline, deadline_time = _deadline(text)
    scope_summary = _scope_summary(metadata.title, text)
    if deadline is None or not scope_summary:
        return []
    business_unit = "Social Security Board" if "လူမှုဖူလုံရေးအဖွဲ့" in metadata.title or "လူမ္ှုဖူလံုထရိုးအဖ ွဲ့" in text else None
    return [
        MolTender(
            post_id=metadata.post_id,
            title=metadata.title,
            publication_date=metadata.publication_date,
            scope_summary=scope_summary,
            deadline=deadline,
            deadline_time=deadline_time,
            attachment_url=metadata.pdf_url,
            url=metadata.url,
            business_unit=business_unit,
        )
    ]
