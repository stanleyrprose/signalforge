from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .mpt import SitemapEntry, normalize_text

INDUSTRY_BASE_URL = "https://www.industrymsme.gov.mm"
INDUSTRY_LIST_URL = f"{INDUSTRY_BASE_URL}/announcements"
INDUSTRY_ISSUER = "Ministry of Industry, Myanmar"
INDUSTRY_HOST = "www.industrymsme.gov.mm"
SELECTION_POLICY_VERSION = 1

_TENDER_TOKENS = (
    "အိတ်ဖွင့်တင်ဒါ",
    "အိတ်ဖွင့်တင်ဒါ",
    "open tender",
    "invitation to tender",
)
_EXCLUDE_TOKENS = (
    "တင်ဒါအောင်",
    "အောင်မြင်",
    "winner",
    "award",
    "result",
)
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_DEADLINE_RE = re.compile(
    r"တင်ဒါပိတ်(?:မည့်)?ရက်(?:(?:နှင့်|နှင့်)အချိန်)?.{0,220}?\(?\s*(?P<day>\d{1,2})\s*[.\-/]\s*(?P<month>\d{1,2})\s*[.\-/]\s*(?P<year>20\d{2})\s*\)?"
    r".{0,100}?\(?\s*(?P<hour>\d{1,2})\s*:\s*(?P<minute>\d{2})\s*\)?",
    re.S,
)


class IndustryParseError(ValueError):
    pass


def _classes(attrs) -> set[str]:
    for key, value in attrs:
        if key == "class" and value:
            return set(str(value).split())
    return set()


def _attr(attrs, name: str) -> str | None:
    for key, value in attrs:
        if key == name and value is not None:
            return str(value)
    return None


def _canonical_announcement_url(raw_url: str) -> tuple[str, str] | None:
    url = urljoin(INDUSTRY_BASE_URL, raw_url)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != INDUSTRY_HOST:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.params or parsed.query or parsed.fragment:
        return None
    match = re.fullmatch(r"/announcements/(\d+)", parsed.path.rstrip("/"))
    if match is None:
        return None
    record_id = match.group(1)
    return record_id, f"{INDUSTRY_BASE_URL}/announcements/{record_id}"


def _is_tender_title(title: str) -> bool:
    value = normalize_text(title)
    lower = value.lower()
    if not value or any(token.lower() in lower for token in _EXCLUDE_TOKENS):
        return False
    return any(token.lower() in lower for token in _TENDER_TOKENS)


def _listing_datetime(value: str) -> str | None:
    text = normalize_text(value)
    try:
        parsed = datetime.strptime(text, "%d-%b-%Y")
    except ValueError:
        return None
    return f"{parsed.date().isoformat()}T00:00:00+06:30"


def _detail_publication_date(value: str) -> str | None:
    text = normalize_text(value)
    text = re.sub(r"^[A-Za-z]{3}\s+", "", text)
    try:
        return datetime.strptime(text, "%d-%m-%Y").date().isoformat()
    except ValueError:
        return None


def _deadline(value: str) -> tuple[str | None, str | None]:
    text = normalize_text(value).translate(_MYANMAR_DIGITS)
    # The issuer occasionally types Myanmar letter Wa (ဝ) as numeric zero inside a date year (for example ၂ဝ၂၆).
    # Normalize only when the glyph is sandwiched by digits so ordinary Burmese words are untouched.
    text = re.sub(r"(?<=\d)ဝ(?=\d)", "0", text)
    match = _DEADLINE_RE.search(text)
    if match is None:
        return None, None
    try:
        day = int(match.group("day"))
        month = int(match.group("month"))
        year = int(match.group("year"))
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        dt = datetime(year, month, day, hour, minute)
    except ValueError:
        return None, None
    return dt.date().isoformat(), f"{hour:02d}:{minute:02d}"


class IndustryListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self._li_depth = 0
        self._h3_depth = 0
        self._date_depth = 0
        self._href: str | None = None
        self._title_parts: list[str] = []
        self._date_parts: list[str] = []
        self.card_count = 0

    def _reset(self) -> None:
        self._h3_depth = 0
        self._date_depth = 0
        self._href = None
        self._title_parts = []
        self._date_parts = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "li":
            if self._li_depth:
                self._li_depth += 1
            else:
                self._li_depth = 1
                self._reset()
            return
        if not self._li_depth:
            return
        if lowered == "h3":
            self._h3_depth = 1
            return
        if lowered == "span" and "date" in classes:
            self._date_depth = 1
            return
        if self._h3_depth:
            if lowered == "a":
                href = _attr(attrs, "href")
                if href:
                    self._href = href
            if lowered not in {"br", "img", "input", "meta", "link", "hr"}:
                self._h3_depth += 1
        if self._date_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._date_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._li_depth:
            return
        if self._h3_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._h3_depth -= 1
        if self._date_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._date_depth -= 1
        if lowered == "li":
            self._li_depth -= 1
            if self._li_depth == 0:
                self._finish()

    def handle_data(self, data: str) -> None:
        if not self._li_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._h3_depth:
            self._title_parts.append(value)
        if self._date_depth:
            self._date_parts.append(value)

    def _finish(self) -> None:
        title = normalize_text(" ".join(self._title_parts))
        identity = _canonical_announcement_url(self._href or "")
        listed_at = _listing_datetime(" ".join(self._date_parts))
        if identity is not None and listed_at is not None:
            self.card_count += 1
            if _is_tender_title(title):
                _record_id, canonical_url = identity
                self.entries.append(SitemapEntry(canonical_url, listed_at))
        self._reset()


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = IndustryListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise IndustryParseError("Ministry of Industry announcement cards not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class IndustryTender:
    record_id: str
    title: str
    publication_date: str
    business_unit: str | None
    scope_summary: str
    deadline: str
    deadline_time: str | None
    url: str

    item_kind = "TENDER"
    location = None

    @property
    def canonical_key(self) -> str:
        return f"industry:{self.record_id}"

    @property
    def reference_no(self) -> str:
        return f"INDUSTRY-ANN-{self.record_id}"

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": INDUSTRY_ISSUER,
            "business_unit": self.business_unit,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_announcement_id",
            "source_record_id": self.record_id,
            "publication_date": self.publication_date,
            "publication_date_evidence": "DETAIL_VISIBLE_DD_MM_YYYY",
            "scope_summary": self.scope_summary,
            "deadline": self.deadline,
            "deadline_time": self.deadline_time,
            "deadline_evidence": "EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME",
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "HTML_BUSINESS_SCOPE_AND_DEADLINE_NO_ATTACHMENT_REQUIRED",
            "attachment_policy": "HTML_ONLY_NO_ATTACHMENT_REQUIRED",
            "url": self.url,
        }


class IndustryDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._title_depth = 0
        self._date_depth = 0
        self._author_depth = 0
        self._body_depth = 0
        self.title_parts: list[str] = []
        self.date_parts: list[str] = []
        self.author_parts: list[str] = []
        self.body_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "h3" and "title-bg" in classes:
            self._title_depth = 1
            return
        if lowered == "span" and "date" in classes:
            self._date_depth = 1
            return
        if lowered == "span" and "author" in classes:
            self._author_depth = 1
            return
        if lowered == "div" and "member-desc" in classes:
            self._body_depth = 1
            return
        for name in ("_title_depth", "_date_depth", "_author_depth", "_body_depth"):
            if getattr(self, name) and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
                setattr(self, name, getattr(self, name) + 1)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        for name in ("_title_depth", "_date_depth", "_author_depth", "_body_depth"):
            if getattr(self, name) and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
                setattr(self, name, getattr(self, name) - 1)

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._date_depth:
            self.date_parts.append(value)
        if self._author_depth:
            self.author_parts.append(value)
        if self._body_depth:
            self.body_parts.append(value)


def parse_tender_detail(html_bytes: bytes, page_url: str) -> IndustryTender | None:
    identity = _canonical_announcement_url(page_url)
    if identity is None:
        return None
    record_id, canonical_url = identity
    parser = IndustryDetailParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    publication_date = _detail_publication_date(" ".join(parser.date_parts))
    business_unit = normalize_text(" ".join(parser.author_parts)) or None
    body = normalize_text(" ".join(parser.body_parts))
    deadline, deadline_time = _deadline(body)
    if not title or not _is_tender_title(title) or publication_date is None or not body or deadline is None:
        return None
    return IndustryTender(
        record_id=record_id,
        title=title,
        publication_date=publication_date,
        business_unit=business_unit,
        scope_summary=body[:3000],
        deadline=deadline,
        deadline_time=deadline_time,
        url=canonical_url,
    )
