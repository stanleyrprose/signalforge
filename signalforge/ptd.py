from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from pypdf import PdfReader

from .mpt import SitemapEntry, normalize_text, parse_date

PTD_BASE_URL = "https://www.ptd.gov.mm"
PTD_LIST_URL = f"{PTD_BASE_URL}/Announcement.aspx?id=jOhwNsVnnrHGITOdpDNvsw%3D%3D"
PTD_ISSUER = "Posts and Telecommunications Department, Ministry of Digital Development and Communications, Myanmar"
PTD_HOSTS = {"ptd.gov.mm", "www.ptd.gov.mm"}
SELECTION_POLICY_VERSION = 1

_OPEN_TENDER_TOKENS = (
    "အိတ်ဖွင့်တင်ဒါ",
    "အိတ်ဖွင့်တင်ဒါ",
    "တင်ဒါခေါ်ယူခြင်း",
    "တင်ဒါတင်သွင်းရန်ဖိတ်ခေါ်",
    "တင်ဒါတင်သွင်းရန် ဖိတ်ခေါ်",
    "open tender",
    "invitation to tender",
)
_EXCLUDE_STAGE_TOKENS = (
    "တင်ဒါအောင်မြင်",
    "အောင်မြင်သူ",
    "အောင်စာရင်း",
    "tender award",
    "awarded",
    "winner",
    "result",
)
_GENERIC_TITLES = {
    "အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
    "အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
    "တင်ဒါခေါ်ယူခြင်း",
    "open tender",
}
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_SECTION_DATE_RE = re.compile(
    r"^(?P<section>[236])\s*[။.]?\s*.*?-\s*(?P<day>\d{1,2})\s*-\s*(?P<month>\d{1,2})\s*-\s*(?P<year>20\d{2})(?:\D|$)"
)
_TIME_RE = re.compile(r"(?<!\d)(?P<hour>[01]?\d|2[0-3])\s*:\s*(?P<minute>[0-5]\d)(?!\d)")


class PtdParseError(ValueError):
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


def is_opportunity_title(value: str) -> bool:
    clean = normalize_text(value)
    lower = clean.lower()
    if not clean or any(token.lower() in lower for token in _EXCLUDE_STAGE_TOKENS):
        return False
    return any(token.lower() in lower for token in _OPEN_TENDER_TOKENS)


def _opaque_detail_id(raw_url: str) -> str | None:
    absolute = urljoin(PTD_BASE_URL + "/", raw_url)
    parsed = urlsplit(absolute)
    if parsed.scheme != "https" or parsed.hostname not in PTD_HOSTS or parsed.username or parsed.password:
        return None
    if parsed.port not in (None, 443) or parsed.fragment or parsed.path.lower() != "/announcementdetail.aspx":
        return None
    if not parsed.query.startswith("id=") or "&" in parsed.query:
        return None
    value = unquote(parsed.query[3:])
    if not re.fullmatch(r"[A-Za-z0-9+/=]{12,128}", value):
        return None
    return value


def _canonical_detail_url(raw_url: str) -> str | None:
    opaque = _opaque_detail_id(raw_url)
    if opaque is None:
        return None
    return f"{PTD_BASE_URL}/AnnouncementDetail.aspx?id={quote(opaque, safe='')}"


def _canonical_attachment(raw_url: str, page_url: str) -> str | None:
    absolute = urljoin(page_url, raw_url)
    parsed = urlsplit(absolute)
    if parsed.scheme != "https" or parsed.hostname not in PTD_HOSTS or parsed.username or parsed.password:
        return None
    if parsed.port not in (None, 443) or parsed.fragment:
        return None
    path = unquote(parsed.path)
    if not path.lower().startswith("/uploads/announce/attach/") or not path.lower().endswith(".pdf"):
        return None
    return urlunsplit(("https", "www.ptd.gov.mm", quote(path, safe="/%()_-.'"), parsed.query, ""))



def _parse_posted_date(value: str) -> str | None:
    clean = normalize_text(value)
    parsed = parse_date(clean)
    if parsed is not None:
        return parsed
    match = re.search(r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(20\d{2})\b", clean)
    if match is None:
        return None
    candidate = " ".join(match.groups())
    for fmt in ("%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(candidate, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _listing_lastmod(date_value: str) -> str:
    return f"{date_value}T00:00:00+06:30"


def _scope_summary(body: str) -> str | None:
    value = normalize_text(body)
    if not value:
        return None
    start = value.find("၁။")
    if start >= 0:
        value = value[start + len("၁။") :].strip()
    end = value.find("၂။")
    if end > 0:
        value = value[:end]
    value = normalize_text(value)
    return value[:3000] if value else None


def _section_schedule(text: str, publication_date: str) -> tuple[str | None, str | None, str | None]:
    lines = [normalize_text(line.translate(_MYANMAR_DIGITS)) for line in text.splitlines()]
    lines = [line for line in lines if line]
    dates: dict[str, tuple[datetime, int]] = {}
    for index, line in enumerate(lines):
        match = _SECTION_DATE_RE.match(line)
        if match is None:
            continue
        try:
            value = datetime(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            )
        except ValueError:
            continue
        dates[match.group("section")] = (value, index)

    sale_close_entry = dates.get("3")
    if sale_close_entry is None:
        return None, None, None
    sale_close, _sale_close_index = sale_close_entry
    try:
        published = datetime.fromisoformat(publication_date)
    except ValueError:
        return None, None, None
    if sale_close < published:
        return None, None, None

    opening_entry = dates.get("6")
    opening_date: str | None = None
    opening_time: str | None = None
    if opening_entry is not None:
        opening, opening_index = opening_entry
        if opening >= sale_close:
            opening_date = opening.date().isoformat()
            time_text = " ".join(lines[opening_index : opening_index + 3])
            time_match = _TIME_RE.search(time_text)
            if time_match is not None:
                opening_time = f"{int(time_match.group('hour')):02d}:{int(time_match.group('minute')):02d}"

    return sale_close.date().isoformat(), opening_date, opening_time


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


class PtdListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.table_seen = False
        self.entries: list[SitemapEntry] = []
        self._row_depth = 0
        self._parts: list[str] = []
        self._urls: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        if lowered == "table" and _attr(attrs, "id") == "ContentPlaceHolder1_gvnews":
            self.table_seen = True
        if lowered == "tr":
            if self._row_depth == 0:
                self._parts = []
                self._urls = []
            self._row_depth += 1
            return
        if self._row_depth and lowered == "a":
            href = _attr(attrs, "href")
            if href:
                canonical = _canonical_detail_url(href)
                if canonical and canonical not in self._urls:
                    self._urls.append(canonical)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "tr" or self._row_depth == 0:
            return
        self._row_depth -= 1
        if self._row_depth:
            return
        text = normalize_text(" ".join(self._parts))
        if not text or not self._urls:
            return
        publication_date = _parse_posted_date(text)
        marker = re.search(r"\bPosted\s+on\b", text, re.I)
        title = normalize_text(text[: marker.start()] if marker else text)
        title = re.sub(r"\s+ဆက်ဖတ်ရန်\s*$", "", title).strip()
        if publication_date and is_opportunity_title(title):
            self.entries.append(SitemapEntry(self._urls[0], _listing_lastmod(publication_date)))

    def handle_data(self, data: str) -> None:
        if self._row_depth:
            value = normalize_text(data)
            if value:
                self._parts.append(value)


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = PtdListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if not parser.table_seen:
        raise PtdParseError("PTD tender category table structure not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class PtdTender:
    title: str
    publication_date: str
    scope_summary: str
    attachment_name: str | None
    attachment_url: str | None
    url: str
    deadline: str | None = None
    deadline_kind: str | None = None
    tender_opening_date: str | None = None
    tender_opening_time: str | None = None
    pdf_schedule_reviewed: bool = False

    item_kind = "TENDER"
    deadline_time = None
    location = None

    @property
    def event_fingerprint(self) -> str:
        material = f"{self.publication_date}|{normalize_text(self.scope_summary)}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()[:16]

    @property
    def canonical_key(self) -> str:
        return f"ptd:{self.publication_date}:{self.event_fingerprint}"

    @property
    def reference_no(self) -> str:
        return f"PTD-{self.publication_date.replace('-', '')}-{self.event_fingerprint[:8]}"

    @property
    def reference_no_kind(self) -> str:
        return "issuer_archive_event_fingerprint"

    @property
    def project_name(self) -> str:
        if normalize_text(self.title).lower() in {title.lower() for title in _GENERIC_TITLES}:
            return self.scope_summary[:500]
        return self.title[:500]

    def payload(self) -> dict[str, object]:
        opaque = _opaque_detail_id(self.url) or ""
        return {
            "item_kind": self.item_kind,
            "issuer": PTD_ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": self.reference_no_kind,
            "identity_material": "publication_date+normalized_scope_summary",
            "publication_date": self.publication_date,
            "publication_date_evidence": "EXPLICIT_HTML_POSTED_DATE",
            "deadline": self.deadline,
            "deadline_time": None,
            "deadline_kind": self.deadline_kind,
            "deadline_evidence": (
                "OFFICIAL_TEXT_NATIVE_PDF_TENDER_FORM_SALE_CLOSE_DATE"
                if self.deadline is not None
                else (
                    "UNKNOWN_IN_TEXT_NATIVE_PDF_SCHEDULE_UNREADABLE"
                    if self.pdf_schedule_reviewed
                    else "UNKNOWN_IN_PDF_ATTACHMENT_NOT_PARSED"
                )
            ),
            "tender_opening_date": self.tender_opening_date,
            "tender_opening_time": self.tender_opening_time,
            "tender_opening_evidence": (
                "OFFICIAL_TEXT_NATIVE_PDF_TENDER_OPENING_DATE_TIME"
                if self.tender_opening_date is not None and self.tender_opening_time is not None
                else "UNKNOWN_OR_INCOMPLETE_IN_PDF_TEXT"
            ),
            "location": None,
            "scope_summary": self.scope_summary,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "attachment_policy": "SINGLE_TEXT_PDF_REQUIRED",
            "detail_locator_hash": hashlib.sha256(opaque.encode("utf-8")).hexdigest()[:16] if opaque else None,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": (
                "HTML_EVENT_SCOPE_TEXT_PDF_PARTICIPATION_CLOSE"
                if self.deadline is not None
                else (
                    "HTML_EVENT_SCOPE_TEXT_PDF_SCHEDULE_UNREADABLE"
                    if self.pdf_schedule_reviewed
                    else "HTML_EVENT_SCOPE_PDF_DEADLINE_UNPARSED"
                )
            ),
            "url": self.url,
        }


class PtdDetailParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.date_parts: list[str] = []
        self.attachment_url: str | None = None
        self.attachment_name: str | None = None
        self._title_depth = 0
        self._body_div_depth = 0
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
        if lowered == "h4" and not self.title_parts and self._title_depth == 0:
            self._title_depth = 1
        elif self._title_depth and lowered not in {"br", "hr", "img", "input", "meta", "link"}:
            self._title_depth += 1

        if lowered == "div":
            if self._body_div_depth:
                self._body_div_depth += 1
            elif "table-responsive" in classes:
                self._body_div_depth = 1

        if lowered == "p" and "pull-right" in classes:
            self._date_depth = 1

        if lowered == "a" and self.attachment_url is None:
            href = _attr(attrs, "href")
            if href:
                attachment = _canonical_attachment(href, self.page_url)
                if attachment:
                    self.attachment_url = attachment
                    self.attachment_name = unquote(urlsplit(attachment).path.rsplit("/", 1)[-1])

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._ignore_depth:
            self._ignore_depth -= 1
            return
        if self._title_depth and lowered == "h4":
            self._title_depth = 0
        elif self._title_depth and lowered not in {"br", "hr", "img", "input", "meta", "link"}:
            self._title_depth = max(1, self._title_depth - 1)
        if lowered == "div" and self._body_div_depth:
            self._body_div_depth -= 1
        if lowered == "p" and self._date_depth:
            self._date_depth = 0

    def handle_data(self, data: str) -> None:
        if self._ignore_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._body_div_depth:
            self.body_parts.append(value)
        if self._date_depth:
            self.date_parts.append(value)


def parse_tender_detail(html_bytes: bytes, page_url: str) -> PtdTender | None:
    canonical_url = _canonical_detail_url(page_url)
    if canonical_url is None:
        return None
    parser = PtdDetailParser(canonical_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    body = normalize_text(" ".join(parser.body_parts))
    scope = _scope_summary(body)
    publication_date = _parse_posted_date(" ".join(parser.date_parts))
    if not title or not scope or publication_date is None or not is_opportunity_title(f"{title} {scope}"):
        return None
    return PtdTender(
        title=title,
        publication_date=publication_date,
        scope_summary=scope,
        attachment_name=parser.attachment_name,
        attachment_url=parser.attachment_url,
        url=canonical_url,
    )


def extract_tender_pdf_urls(html_bytes: bytes, page_url: str) -> list[str]:
    tender = parse_tender_detail(html_bytes, page_url)
    if tender is None or not tender.attachment_url:
        return []
    return [tender.attachment_url]


def parse_tender_detail_with_attachments(
    html_bytes: bytes,
    page_url: str,
    attachments: list[tuple[str, bytes]],
) -> list[object]:
    base = parse_tender_detail(html_bytes, page_url)
    if base is None:
        return []
    if len(attachments) != 1 or base.attachment_url is None:
        raise PtdParseError("PTD requires exactly one official PDF attachment")
    attachment_url, pdf_bytes = attachments[0]
    if attachment_url != base.attachment_url:
        raise PtdParseError("PTD attachment URL mismatch")
    try:
        text = _extract_pdf_text(pdf_bytes)
    except Exception as exc:
        raise PtdParseError(f"PTD PDF parse failed: {exc}") from exc
    if not normalize_text(text):
        raise PtdParseError("PTD PDF contains no extractable text")

    deadline, opening_date, opening_time = _section_schedule(text, base.publication_date)
    return [
        PtdTender(
            title=base.title,
            publication_date=base.publication_date,
            scope_summary=base.scope_summary,
            attachment_name=base.attachment_name,
            attachment_url=base.attachment_url,
            url=base.url,
            deadline=deadline,
            deadline_kind="TENDER_FORM_SALE_CLOSE" if deadline is not None else None,
            tender_opening_date=opening_date,
            tender_opening_time=opening_time,
            pdf_schedule_reviewed=True,
        )
    ]
