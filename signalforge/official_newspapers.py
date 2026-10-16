"""MOI-hosted Kyemon and Myanma Alinn procurement notices (strict evidence gate).

Two daily newspaper sources have separate listing contracts but share a narrowly
scoped formal tender parser. An issue PDF is *not* a tender. Burmese PUA-glyph
PDF extraction is deliberately review-only until a verified OCR contract exists.
"""
from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin

from pypdf import PdfReader

from .mpt import MONTHS, SitemapEntry, normalize_text

_BASE = "https://www.moi.gov.mm"
_ISSUE = re.compile(
    r"^\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{2}|20\d{2})\s*$",
    re.I,
)
_PDF_PATH = re.compile(r"^/(km|mal)/file-download/download/public/\d+$")
_TENDER = re.compile(r"(?:invitation\s+(?:to|for)\s+(?:bid|tender)|open\s+tender|tender\s+notice|အိတ်ဖွင့်တင်ဒါ)", re.I)
_ISSUER = re.compile(r"(?:Ministry\s+of\s+[A-Za-z &]{5,90}|Department\s+of\s+[A-Za-z &]{5,90}|[A-Za-z &]{5,90}(?:Authority|Corporation|Enterprise|Committee))", re.I)
_REFERENCE = re.compile(r"(?:Tender|Bid|RFQ)\s*(?:No\.?|Ref(?:erence)?\.?\s*(?:No\.?)?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9/().-]{4,65})", re.I)
_QTY = re.compile(r"\b\d[\d,]*\s*(?:lots?|sets?|units?|pieces?|pcs|nos|km|tons?|items?)\b", re.I)
_DEADLINE = re.compile(r"(?:bid\s+(?:submission|closing)|submission\s+deadline|tender\s+closing)[^\n]{0,130}", re.I)
_DATE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b")
_OFFICIAL_FONTS_RISK = re.compile(r"[\uE000-\uF8FF]")


class _DownloadLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._parts = []

    def handle_data(self, value: str) -> None:
        if self._href is not None:
            self._parts.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append((normalize_text(" ".join(self._parts)), self._href))
            self._href = None
            self._parts = []


def _as_issue_date(value: str) -> str | None:
    match = _ISSUE.fullmatch(value)
    if not match:
        return None
    day, month, year = match.groups()
    mon = MONTHS.get(month.lower())
    if mon is None:
        return None
    y = int(year)
    if y < 100:
        y += 2000
    try:
        return date(y, mon, int(day)).isoformat()
    except ValueError:
        return None


def _parse_issue_listing(payload: bytes, *, newspaper: str) -> list[SitemapEntry]:
    if newspaper not in {"km", "mal"}:
        raise ValueError("unknown official newspaper")
    parser = _DownloadLinks()
    parser.feed(payload.decode("utf-8", "replace"))
    current_day: str | None = None
    issues: dict[str, SitemapEntry] = {}
    for text, href in parser.links:
        parsed = urlparse(urljoin(_BASE + f"/{newspaper}/", href))
        day = _as_issue_date(text)
        if day and parsed.scheme == "https" and parsed.hostname == "www.moi.gov.mm" and parsed.path.startswith(f"/{newspaper}/"):
            current_day = day
            continue
        if text.lower() != "download" or current_day is None:
            continue
        if parsed.scheme != "https" or parsed.hostname != "www.moi.gov.mm" or parsed.query or parsed.fragment:
            continue
        match = _PDF_PATH.fullmatch(parsed.path)
        if not match or match.group(1) != newspaper:
            continue
        url = _BASE + parsed.path
        issues.setdefault(url, SitemapEntry(url, current_day + "T00:00:00Z"))
        current_day = None
        if len(issues) == 7:
            break
    if not issues:
        raise ValueError(f"no official {newspaper} newspaper PDFs found")
    return list(issues.values())


def parse_kyemon_issues(payload: bytes) -> list[SitemapEntry]:
    return _parse_issue_listing(payload, newspaper="km")


def parse_myanma_alinn_issues(payload: bytes) -> list[SitemapEntry]:
    return _parse_issue_listing(payload, newspaper="mal")


@dataclass(frozen=True)
class NewspaperTender:
    url: str
    title: str
    issuer: str
    reference_no: str
    scope_summary: str
    quantity_or_lot_summary: str
    deadline: str
    publication_date: str | None
    page_number: int
    document_sha256: str

    item_kind = "TENDER"
    location = None

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def canonical_key(self) -> str:
        # Share identity between KM/MAL reprints with exact issuer + reference + deadline.
        components = "|".join((self.issuer.casefold(), self.reference_no.casefold(), self.deadline))
        return "moi-official-newspaper:" + hashlib.sha256(components.encode("utf-8")).hexdigest()[:32]

    def payload(self) -> dict[str, object]:
        return {
            "issuer": self.issuer, "reference_no": self.reference_no,
            "title": self.title, "project_name": self.title,
            "scope_summary": self.scope_summary,
            "quantity_or_lot_summary": self.quantity_or_lot_summary,
            "deadline": self.deadline, "deadline_kind": "BID_SUBMISSION_DEADLINE",
            "deadline_evidence": "OFFICIAL_NEWSPAPER_NATIVE_TEXT_SAME_NOTICE",
            "publication_date": self.publication_date,
            "source_document_sha256": self.document_sha256,
            "newspaper_page": self.page_number,
            "document_authority": "MOI_OFFICIAL_DAILY_NEWSPAPER",
            "url": self.url,
        }


def parse_official_newspaper_pdf(payload: bytes, url: str) -> list[NewspaperTender]:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https" or parsed.hostname != "www.moi.gov.mm"
        or not _PDF_PATH.fullmatch(parsed.path) or parsed.query or parsed.fragment
        or not payload.startswith(b"%PDF-")
    ):
        return []
    issue = PdfReader(io.BytesIO(payload), strict=False)
    if len(issue.pages) > 48:
        raise ValueError("newspaper PDF exceeds bounded page limit")
    original_digest = hashlib.sha256(payload).hexdigest()
    cover = (issue.pages[0].extract_text() or "")[:2500] if issue.pages else ""
    date_match = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2}|\d{2})\b", cover)
    issue_date = _as_issue_date(date_match.group(0)) if date_match else None
    # No OCR signal promotion from PUA-font pages; they remain preserved evidence.
    validated: dict[str, NewspaperTender] = {}
    for page_no, page in enumerate(issue.pages, 1):
        text = page.extract_text() or ""
        if not text or _OFFICIAL_FONTS_RISK.search(text):
            continue
        # Layout from newspapers is multi-column; a whole-page match could mix
        # unrelated advertisements. Only coherent short blocks qualify.
        for block in re.split(r"\n\s*\n", text):
            if len(block) > 1200 or len(block) < 100 or not _TENDER.search(block):
                continue
            issuer_match = _ISSUER.search(block)
            ref_match = _REFERENCE.search(block)
            qty_match = _QTY.search(block)
            marker = _DEADLINE.search(block)
            if not (issuer_match and ref_match and qty_match and marker):
                continue
            closing = _DATE.findall(marker.group(0))
            if len(closing) != 1:
                continue
            dd, mm, yy = (int(x) for x in closing[0])
            try:
                deadline = date(yy, mm, dd).isoformat()
            except ValueError:
                continue
            # Require an explicit offer title near the issuer, rather than mixing
            # distant page columns into a fabricated business record.
            issuer = normalize_text(issuer_match.group(0))
            ref = ref_match.group(1).strip()
            summary = normalize_text(block[:500])
            candidate = NewspaperTender(
                url=url, title=summary[:140], issuer=issuer, reference_no=ref,
                scope_summary=summary, quantity_or_lot_summary=qty_match.group(0),
                deadline=deadline, publication_date=issue_date,
                page_number=page_no, document_sha256=original_digest,
            )
            validated.setdefault(candidate.canonical_key, candidate)
    return list(validated.values())
