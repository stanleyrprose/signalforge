from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from pypdf import PdfReader

from .mpt import SitemapEntry, normalize_text

ENERGY_BASE_URL = "https://energy.gov.mm"
ENERGY_LIST_URL = f"{ENERGY_BASE_URL}/tenders"
ENERGY_HOST = "energy.gov.mm"
ENERGY_ISSUER = "Ministry of Energy, Myanmar"
SELECTION_POLICY_VERSION = 1
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_DATE_TIME_RE = re.compile(
    r"(?P<day>\d{1,2})\s*-\s*(?P<month>\d{1,2})\s*-\s*(?P<year>20\d{2})"
    r".{0,100}?\(?\s*(?P<hour>\d{1,2})\s*:\s*(?P<minute>\d{2})\s*\)?",
    re.S,
)
_NOTICE_RE = re.compile(r"\(\s*(?P<number>\d{1,3})\s*/\s*(?P<year>20\d{2})(?:\s*-\s*(?P<end>20\d{2}))?\s*\)")


class EnergyParseError(ValueError):
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


def _canonical_detail_url(raw_url: str) -> tuple[str, str] | None:
    url = urljoin(ENERGY_BASE_URL, raw_url)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ENERGY_HOST:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.params or parsed.query or parsed.fragment:
        return None
    match = re.fullmatch(r"/tenders/(\d+)", parsed.path.rstrip("/"))
    if match is None:
        return None
    record_id = match.group(1)
    return record_id, f"{ENERGY_BASE_URL}/tenders/{record_id}"


def _canonical_pdf_url(raw_url: str) -> str | None:
    url = urljoin(ENERGY_BASE_URL, raw_url)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ENERGY_HOST:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.params or parsed.query or parsed.fragment:
        return None
    if re.fullmatch(r"/storage/tenders/[A-Za-z0-9]+\.pdf", parsed.path) is None:
        return None
    return url


def _listing_date(value: str) -> str | None:
    text = normalize_text(value)
    text = re.sub(r"(?<=\d)\s*(?:st|nd|rd|th)\b", "", text, flags=re.I)
    try:
        parsed = datetime.strptime(text, "%d %b %Y")
    except ValueError:
        return None
    return f"{parsed.date().isoformat()}T00:00:00+06:30"


def _publication_date(value: str) -> str | None:
    listed = _listing_date(value)
    return listed.split("T", 1)[0] if listed else None


def _reference_no(title: str, record_id: str) -> str:
    translated = normalize_text(title).translate(_MYANMAR_DIGITS)
    match = _NOTICE_RE.search(translated)
    if match is None:
        return f"ENERGY-TENDER-{record_id}"
    suffix = f"-{match.group('end')}" if match.group("end") else ""
    return f"ENERGY-{match.group('number')}-{match.group('year')}{suffix}"


def _deadline(text: str) -> tuple[str | None, str | None]:
    translated = normalize_text(text).translate(_MYANMAR_DIGITS)
    matches = list(_DATE_TIME_RE.finditer(translated))
    if not matches:
        return None, None
    match = matches[-1]
    try:
        dt = datetime(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
            int(match.group("hour")),
            int(match.group("minute")),
        )
    except ValueError:
        return None, None
    return dt.date().isoformat(), dt.strftime("%H:%M")


def _scope_summary(text: str) -> str:
    translated = text.translate(_MYANMAR_DIGITS)
    lines: list[str] = []
    for raw in translated.splitlines():
        value = normalize_text(raw)
        if not value or not re.search(r"[A-Za-z]", value):
            continue
        lower = value.lower()
        if lower == "ks" or "energy.gov.mm" in lower:
            continue
        lines.append(value)
    summary = " | ".join(dict.fromkeys(lines))
    return summary[:2400]


class EnergyListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self.card_count = 0
        self._card_depth = 0
        self._href: str | None = None
        self._parts: list[str] = []

    def _reset(self) -> None:
        self._href = None
        self._parts = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "div" and {"card", "card-bg-color"}.issubset(classes) and self._card_depth == 0:
            self._card_depth = 1
            self._reset()
            return
        if not self._card_depth:
            return
        if lowered == "a" and "read_link" in classes:
            href = _attr(attrs, "href")
            if href:
                self._href = href
        if lowered not in {"br", "img", "input", "meta", "link", "hr", "embed"}:
            self._card_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._card_depth:
            return
        if lowered not in {"br", "img", "input", "meta", "link", "hr", "embed"}:
            self._card_depth -= 1
        if self._card_depth == 0:
            self._finish()

    def handle_data(self, data: str) -> None:
        if self._card_depth:
            value = normalize_text(data)
            if value:
                self._parts.append(value)

    def _finish(self) -> None:
        identity = _canonical_detail_url(self._href or "")
        text = normalize_text(" ".join(self._parts))
        date_match = re.search(r"\b\d{1,2}\s*(?:st|nd|rd|th)?\s+[A-Za-z]{3}\s+20\d{2}\b", text, re.I)
        listed_at = _listing_date(date_match.group(0)) if date_match else None
        if identity is not None and listed_at is not None:
            self.card_count += 1
            _record_id, canonical_url = identity
            self.entries.append(SitemapEntry(canonical_url, listed_at))
        self._reset()


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = EnergyListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise EnergyParseError("Ministry of Energy tender cards not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class EnergyDetailMetadata:
    record_id: str
    title: str
    publication_date: str
    pdf_url: str
    url: str


class EnergyDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._title_depth = 0
        self._date_depth = 0
        self.title_parts: list[str] = []
        self.date_parts: list[str] = []
        self.pdf_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "h1" and "main-color" in classes and not self.title_parts:
            self._title_depth = 1
            return
        if lowered == "div" and {"main-color", "py-3"}.issubset(classes):
            self._date_depth = 1
            return
        if lowered == "embed" and (_attr(attrs, "type") or "").lower() == "application/pdf":
            src = _attr(attrs, "src")
            if src:
                url = _canonical_pdf_url(src)
                if url:
                    self.pdf_urls.append(url)
        for name in ("_title_depth", "_date_depth"):
            if getattr(self, name) and lowered not in {"br", "img", "input", "meta", "link", "hr", "embed"}:
                setattr(self, name, getattr(self, name) + 1)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        for name in ("_title_depth", "_date_depth"):
            if getattr(self, name) and lowered not in {"br", "img", "input", "meta", "link", "hr", "embed"}:
                setattr(self, name, getattr(self, name) - 1)

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._date_depth:
            self.date_parts.append(value)


def parse_detail_metadata(html_bytes: bytes, page_url: str) -> EnergyDetailMetadata | None:
    identity = _canonical_detail_url(page_url)
    if identity is None:
        return None
    record_id, canonical_url = identity
    parser = EnergyDetailParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    date_match = re.search(r"\b\d{1,2}\s*(?:st|nd|rd|th)?\s+[A-Za-z]{3}\s+20\d{2}\b", " ".join(parser.date_parts), re.I)
    publication_date = _publication_date(date_match.group(0)) if date_match else None
    pdfs = list(dict.fromkeys(parser.pdf_urls))
    if not title or publication_date is None or len(pdfs) != 1:
        return None
    return EnergyDetailMetadata(record_id, title, publication_date, pdfs[0], canonical_url)


def extract_tender_pdf_urls(html_bytes: bytes, page_url: str) -> list[str]:
    metadata = parse_detail_metadata(html_bytes, page_url)
    return [metadata.pdf_url] if metadata is not None else []


@dataclass(frozen=True)
class EnergyTender:
    record_id: str
    title: str
    publication_date: str
    scope_summary: str
    deadline: str
    deadline_time: str | None
    attachment_url: str
    url: str

    item_kind = "TENDER"
    location = None
    business_unit = None

    @property
    def canonical_key(self) -> str:
        return f"energy:{self.record_id}"

    @property
    def reference_no(self) -> str:
        return _reference_no(self.title, self.record_id)

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": ENERGY_ISSUER,
            "business_unit": self.business_unit,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_tender_notice_number_or_record_id",
            "source_record_id": self.record_id,
            "publication_date": self.publication_date,
            "publication_date_evidence": "DETAIL_VISIBLE_DD_MON_YYYY",
            "scope_summary": self.scope_summary,
            "deadline": self.deadline,
            "deadline_time": self.deadline_time,
            "deadline_evidence": "OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME",
            "attachment_urls": [self.attachment_url],
            "attachment_policy": "SINGLE_TEXT_PDF_REQUIRED",
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "HTML_ID_PUBLICATION_PLUS_TEXT_PDF_SCOPE_DEADLINE",
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
        raise EnergyParseError("Ministry of Energy attachment URL mismatch")
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:
        raise EnergyParseError("Ministry of Energy PDF parse failed") from exc
    if not normalize_text(text):
        raise EnergyParseError("Ministry of Energy PDF contains no extractable text")
    deadline, deadline_time = _deadline(text)
    scope_summary = _scope_summary(text)
    if deadline is None or not scope_summary:
        return []
    return [
        EnergyTender(
            record_id=metadata.record_id,
            title=metadata.title,
            publication_date=metadata.publication_date,
            scope_summary=scope_summary,
            deadline=deadline,
            deadline_time=deadline_time,
            attachment_url=metadata.pdf_url,
            url=metadata.url,
        )
    ]
