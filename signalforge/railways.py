from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

from .mpt import SitemapEntry, TableTextParser, normalize_text, parse_date


MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")


@dataclass(frozen=True)
class RailwayTender:
    reference_no: str
    project_name: str
    publication_date: str | None
    deadline: str | None
    location: str | None
    remarks: str | None
    company_size: str | None
    required_quantity: str | None
    url: str
    content_hash: str

    @property
    def canonical_key(self) -> str:
        reference = normalize_text(self.reference_no).translate(MYANMAR_DIGITS).upper()
        reference = re.sub(r"\s+", "", reference)
        return f"railways:{reference}"

    def payload(self) -> dict[str, str | None]:
        return {
            "issuer": "Myanma Railways",
            "reference_no": self.reference_no,
            "project_name": self.project_name,
            "publication_date": self.publication_date,
            "deadline": self.deadline,
            "location": self.location,
            "remarks": self.remarks,
            "company_size": self.company_size,
            "required_quantity": self.required_quantity,
            "url": self.url,
        }


class TenderListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self._in_title = False
        self._in_date = False
        self._pending_url: str | None = None
        self._date_parts: list[str] = []

    @staticmethod
    def _classes(attrs) -> set[str]:  # type: ignore[no-untyped-def]
        for key, value in attrs:
            if key == "class" and value:
                return set(str(value).split())
        return set()

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = self._classes(attrs)
        if lowered == "h4" and "entry-title" in classes:
            self._in_title = True
            return
        if lowered == "a" and self._in_title:
            href = next((str(value) for key, value in attrs if key == "href" and value), None)
            if href:
                parsed = urlparse(href)
                if parsed.scheme == "https" and parsed.netloc.lower() in {"railways.gov.mm", "www.railways.gov.mm"}:
                    self._pending_url = href
            return
        if lowered == "span" and "mg-blog-date" in classes and self._pending_url:
            self._in_date = True
            self._date_parts = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "h4":
            self._in_title = False
        elif lowered == "span" and self._in_date:
            publication_date = _parse_wordpress_date(" ".join(self._date_parts))
            lastmod = f"{publication_date}T00:00:00Z" if publication_date else None
            assert self._pending_url is not None
            self.entries.append(SitemapEntry(self._pending_url, lastmod))
            self._pending_url = None
            self._date_parts = []
            self._in_date = False

    def handle_data(self, data: str) -> None:
        if self._in_date:
            value = normalize_text(data)
            if value:
                self._date_parts.append(value)


def _parse_wordpress_date(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_text(value)
    parsed = parse_date(normalized)
    if parsed:
        return parsed
    for pattern in ("%b %d, %Y", "%b %d %Y"):
        try:
            return datetime.strptime(normalized, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = TenderListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    deduplicated: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        deduplicated.setdefault(entry.url, entry)
    return list(deduplicated.values())


def _publication_date(html_bytes: bytes) -> str | None:
    text = html_bytes.decode("utf-8", errors="replace")
    match = re.search(
        r'<span[^>]*class="[^"]*mg-blog-date[^"]*"[^>]*>(.*?)</span>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    value = re.sub(r"<[^>]+>", " ", match.group(1))
    return _parse_wordpress_date(value)


def _deadline(full_text: str) -> str | None:
    translated = normalize_text(full_text).translate(MYANMAR_DIGITS)
    marker = "တင်ဒါပိတ်မည့်နေ့/အချိန်"
    position = translated.find(marker)
    if position < 0:
        return None
    window = translated[position : position + 240]
    match = re.search(r"\((\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(20\d{2})\)", window)
    if not match:
        return None
    day, month, year = (int(value) for value in match.groups())
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def parse_tender_detail(html_bytes: bytes, url: str) -> list[RailwayTender]:
    parser = TableTextParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    publication_date = _publication_date(html_bytes)
    deadline = _deadline(parser.full_text)
    digest = hashlib.sha256(html_bytes).hexdigest()

    tenders: list[RailwayTender] = []
    seen: set[str] = set()
    for row in parser.rows:
        if len(row) < 3:
            continue
        reference = normalize_text(row[1])
        project = normalize_text(" ".join(row[2:]))
        if not reference or not project or "တင်ဒါအမှတ်" in reference:
            continue
        if len(reference) > 160 or len(project) > 1200:
            continue
        if not re.search(r"[A-Za-z0-9၀-၉]", reference):
            continue
        candidate = RailwayTender(
            reference_no=reference,
            project_name=project,
            publication_date=publication_date,
            deadline=deadline,
            location=None,
            remarks=None,
            company_size=None,
            required_quantity=None,
            url=url,
            content_hash=digest,
        )
        if candidate.canonical_key in seen:
            continue
        seen.add(candidate.canonical_key)
        tenders.append(candidate)
    return tenders
