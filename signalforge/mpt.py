from __future__ import annotations

import hashlib
import html as html_lib
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlparse
from xml.etree import ElementTree


SPACE_RE = re.compile(r"\s+")
DATE_PATTERNS = (
    re.compile(r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<year>20\d{2})", re.I),
    re.compile(r"(?P<day>\d{1,2})(?:\s*(?:st|nd|rd|th))?\s+(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+(?P<year>20\d{2})", re.I),
)


def normalize_text(value: str) -> str:
    return SPACE_RE.sub(" ", html_lib.unescape(value)).strip()


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    text = normalize_text(value)
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            parsed = datetime.strptime(
                f"{match.group('month')} {int(match.group('day'))} {match.group('year')}",
                "%B %d %Y",
            )
            return parsed.date().isoformat()
    return None


@dataclass(frozen=True)
class SitemapEntry:
    url: str
    lastmod: str | None


@dataclass(frozen=True)
class Tender:
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
        reference = re.sub(r"[^A-Z0-9]+", "-", self.reference_no.upper()).strip("-")
        return f"mpt:{reference}"

    def payload(self) -> dict[str, str | None]:
        return {
            "issuer": "MPT",
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


class TableTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._all_text: list[str] = []
        self.heading: list[str] = []
        self._heading_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        if lowered == "tr":
            self._row = []
        elif lowered in {"td", "th"} and self._row is not None:
            self._cell = []
        elif lowered in {"h1", "h2", "h3"}:
            self._heading_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(normalize_text(" ".join(self._cell)))
            self._cell = None
        elif lowered == "tr" and self._row is not None:
            if any(cell for cell in self._row):
                self.rows.append(self._row)
            self._row = None
            self._cell = None
        elif lowered in {"h1", "h2", "h3"} and self._heading_depth:
            self._heading_depth -= 1

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        self._all_text.append(value)
        if self._cell is not None:
            self._cell.append(value)
        if self._heading_depth:
            self.heading.append(value)

    @property
    def full_text(self) -> str:
        return normalize_text(" ".join(self._all_text))


def parse_sitemap(xml_bytes: bytes) -> list[SitemapEntry]:
    root = ElementTree.fromstring(xml_bytes)
    entries: list[SitemapEntry] = []
    for url_node in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
        loc = url_node.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        if not loc:
            continue
        parsed = urlparse(loc)
        if parsed.netloc.lower() not in {"mpt.com.mm", "www.mpt.com.mm"}:
            continue
        if not parsed.path.startswith("/en/"):
            continue
        lastmod = url_node.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
        entries.append(SitemapEntry(loc.strip(), lastmod.strip() if lastmod else None))
    return entries


def _rows_to_fields(rows: list[list[str]]) -> dict[str, str]:
    fields: dict[str, str] = {}
    aliases = {
        "date": "date",
        "reference no": "reference_no",
        "reference no.": "reference_no",
        "project name": "project_name",
        "project": "project_name",
        "location": "location",
        "other remarks": "remarks",
        "company size": "company_size",
        "required quantity": "required_quantity",
    }
    for row in rows:
        if len(row) < 2:
            continue
        key = normalize_text(row[0]).rstrip(":").lower()
        canonical = aliases.get(key)
        if canonical and canonical not in fields:
            fields[canonical] = normalize_text(" ".join(row[1:]))
    return fields


def _extract_deadline(text: str) -> str | None:
    lower = text.lower()
    positions = [match.start() for match in re.finditer("deadline", lower)]
    for position in positions:
        window = text[position : position + 220]
        value = parse_date(window)
        if value:
            return value
    return None


def parse_tender_detail(html_bytes: bytes, url: str) -> Tender | None:
    digest = hashlib.sha256(html_bytes).hexdigest()
    text = html_bytes.decode("utf-8", errors="replace")
    parser = TableTextParser()
    parser.feed(text)
    fields = _rows_to_fields(parser.rows)
    reference = normalize_text(fields.get("reference_no", ""))
    project = normalize_text(fields.get("project_name", ""))
    if not reference or not project:
        return None
    if len(reference) > 120 or len(project) > 500:
        return None
    return Tender(
        reference_no=reference,
        project_name=project,
        publication_date=parse_date(fields.get("date")),
        deadline=_extract_deadline(parser.full_text),
        location=fields.get("location") or None,
        remarks=fields.get("remarks") or None,
        company_size=fields.get("company_size") or None,
        required_quantity=fields.get("required_quantity") or None,
        url=url,
        content_hash=digest,
    )
