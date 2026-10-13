"""Conservative issuer-document acquisition for National Portal tenders.

Portal cards are discovery hints only; a document with unverified issuer or
submission deadline is never promoted to a canonical tender.
"""
from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from pypdf import PdfReader

from .mpt import SitemapEntry, normalize_text
from .digital_development import _DDD_TITLE_TOKEN
from .national_portal import NATIONAL_PORTAL_HOSTS, _TenderCardParser, _canonical_url

_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_DATE = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](20\d{2})(?!\d)")
_QTY = re.compile(r"(?<![\w/])\d[\d,]*\s*(?:units?|sets?|lots?|pieces?|pcs?|nos?|ခု|လုံး|စုံ|မျိုး)(?![A-Za-z0-9])", re.I)
_DEADLINE = re.compile(r"(?:submission\s+deadline|bid\s+closing|tender\s+closing|တင်ဒါ\s*ပိတ်|တင်သွင်းရမည့်)[^\n]{0,140}", re.I)
_ISSUER = re.compile(r"(?:ministry|department|government|enterprise|authority|committee|ဌာန|ဝန်ကြီးဌာန|ကော်မတီ)[^\n]{0,120}", re.I)


def _extract_closing_deadline(text: str) -> str | None:
    """Require a valid, unambiguous closing date in an explicit deadline line.

    Multiple different closing dates can indicate amendments or separate lots;
    never guess which one is authoritative.
    """
    dates: set[str] = set()
    for line in text.splitlines():
        marker = _DEADLINE.search(line)
        if marker is None:
            continue
        matches = list(_DATE.finditer(line[marker.start():]))
        if not matches:
            continue  # Heading only; a later explicit deadline line may contain the date.
        if len(matches) != 1:
            return None
        day, month, year = map(int, matches[0].groups())
        try:
            dates.add(date(year, month, day).isoformat())
        except ValueError:
            return None
    return next(iter(dates)) if len(dates) == 1 else None


def persist_national_portal_image_candidates(database, payload: bytes, observed_at: str, listing_sha256: str) -> int:
    """Persist review-only image hints without promoting them to tenders."""
    from .db import connect

    candidates = parse_national_portal_image_candidates(payload)
    with connect(database) as conn, conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS s01_image_review ("
            "url TEXT PRIMARY KEY, title_hint TEXT NOT NULL, issuer_hint TEXT NOT NULL, "
            "deadline_hint TEXT NOT NULL, listing_sha256 TEXT NOT NULL, "
            "first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, "
            "review_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED', "
            "ocr_input_sha256 TEXT, ocr_evidence_path TEXT, ocr_text TEXT, reviewed_at TEXT)"
        )
        for item in candidates:
            conn.execute(
                "INSERT INTO s01_image_review "
                "(url,title_hint,issuer_hint,deadline_hint,listing_sha256,first_seen_at,last_seen_at) "
                "VALUES (?,?,?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET "
                "title_hint=excluded.title_hint, issuer_hint=excluded.issuer_hint, "
                "deadline_hint=excluded.deadline_hint, listing_sha256=excluded.listing_sha256, "
                "last_seen_at=excluded.last_seen_at",
                (item["url"], item["title_hint"], item["issuer_hint"],
                 item["deadline_hint"], listing_sha256, observed_at, observed_at),
            )
    return len(candidates)


def parse_national_portal_image_candidates(payload: bytes) -> list[dict[str, str]]:
    """Retain S01 JPEG cards as review candidates, separate from PDF tenders.

    Listing metadata is a hint, not issuer-document proof. Do not create
    canonical tenders or send Telegram from these records.
    """
    parser = _TenderCardParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    if not parser.rows:
        raise ValueError("National Portal tender cards not found")
    found: dict[str, dict[str, str]] = {}
    for row in parser.rows:
        url = _canonical_url(row["href"], "https://myanmar.gov.mm/tenders")
        if not url:
            continue
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "myanmar.gov.mm"
            or not parsed.path.startswith("/documents/")
            or not re.search(r"\\.jpe?g(?:/|$)", parsed.path, re.I)
        ):
            continue
        if (
            "digital development" in row["agency"].lower()
            or "ဒစ်ဂျစ်တယ်" in row["agency"]
            or _DDD_TITLE_TOKEN in re.sub(r"\\s+", "", normalize_text(row["title"]))
        ):
            continue
        found[url] = {
            "url": url,
            "title_hint": row["title"],
            "issuer_hint": row["agency"],
            "deadline_hint": row["closing"],
            "status": "REVIEW_REQUIRED",
        }
    return list(found.values())


def parse_national_portal_listing(payload: bytes) -> list[SitemapEntry]:
    parser = _TenderCardParser()
    parser.feed(payload.decode('utf-8', errors='replace'))
    if not parser.rows:
        raise ValueError('National Portal tender cards not found')
    found: dict[str, SitemapEntry] = {}
    for row in parser.rows:
        url = _canonical_url(row['href'], 'https://myanmar.gov.mm/tenders')
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.hostname not in NATIONAL_PORTAL_HOSTS or not parsed.path.startswith('/documents/'):
            continue
        # The PDF-only detail pipeline cannot process image attachments. Keep
        # image-backed cards out of PDF discovery rather than pretending
        # they are issuer PDF tenders. Image OCR needs a separate coverage path.
        if re.search(r'\.(?:jpe?g|png|gif|webp)(?:/|$)', parsed.path, re.I):
            continue
        # S51's Digital Development issuer documents are owned by its dedicated adapter.
        if ('digital development' in row['agency'].lower() or 'ဒစ်ဂျစ်တယ်' in row['agency']
                or _DDD_TITLE_TOKEN in re.sub(r'\s+', '', normalize_text(row['title']))):
            continue
        found[url] = SitemapEntry(url=url, lastmod=None)
    return list(found.values())


@dataclass(frozen=True)
class PortalTender:
    url: str
    issuer: str
    scope_summary: str
    quantity_or_lot_summary: str | None
    deadline: str
    title: str
    document_sha256: str

    item_kind = 'TENDER'
    publication_date = None
    location = None
    reference_no = None

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def canonical_key(self) -> str:
        # Stable document identity across source pages; S51 is excluded in discovery.
        return 'national-portal-document:' + hashlib.sha256(self.url.encode()).hexdigest()[:24]

    def payload(self) -> dict[str, object]:
        return {'item_kind': 'TENDER', 'issuer': self.issuer, 'title': self.title,
                'project_name': self.project_name, 'scope_summary': self.scope_summary,
                'quantity_or_lot_summary': self.quantity_or_lot_summary,
                'quantity_disclosure_status': 'EXPLICIT' if self.quantity_or_lot_summary else 'NOT_EXTRACTED',
                'deadline': self.deadline, 'deadline_kind': 'BID_SUBMISSION_DEADLINE',
                'deadline_evidence': 'ISSUER_DOCUMENT_TEXT', 'url': self.url,
                'document_authority': 'ISSUER_TEXT_PDF_VIA_NATIONAL_PORTAL',
                'source_document_sha256': self.document_sha256}


def parse_national_portal_document(payload: bytes, url: str) -> list[PortalTender]:
    if not payload.startswith(b'%PDF-'):
        return []
    text = '\n'.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(payload)).pages)
    text = '\n'.join(normalize_text(line).translate(_MYANMAR_DIGITS) for line in text.splitlines() if normalize_text(line))
    if len(text) < 100:
        return []  # Scanned PDFs require OCR and independent issuer review.
    issuer = _ISSUER.search(text)
    quantity = _QTY.search(text)
    # The first matching line may announce a meeting or provide an incomplete
    # heading; only a date on an explicit closing/deadline line is admissible.
    deadline = _extract_closing_deadline(text)
    if not (issuer and deadline):
        return []
    title = text[:180]
    return [PortalTender(url, issuer.group(0), title, quantity.group(0) if quantity else None, deadline, title, hashlib.sha256(payload).hexdigest())]
