from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from .mpt import normalize_text

MOC_TENDER_URL = "https://construction.gov.mm/tindar-show/f878a520-d396-11ec-957c-cb8c3b494625?state_name=all"
MOC_ISSUER = "Ministry of Construction, Myanmar"
MOC_HOSTS = {"construction.gov.mm", "www.construction.gov.mm"}
SELECTION_POLICY_VERSION = 1

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_VOID_TAGS = {"area", "base", "br", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_TENDER_TOKENS = ("တင်ဒါ", "tender")
_EXCLUDE_TOKENS = ("award", "winner", "result", "တင်ဒါအောင်", "အောင်မြင်")


class MocParseError(ValueError):
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


def _is_tender_title(value: str) -> bool:
    text = normalize_text(value)
    lower = text.lower()
    if not text or any(token.lower() in lower for token in _EXCLUDE_TOKENS):
        return False
    return any(token.lower() in lower for token in _TENDER_TOKENS)


def _canonical_download_url(raw_url: str, page_url: str = MOC_TENDER_URL) -> tuple[str, str] | None:
    absolute = urljoin(page_url, raw_url)
    parsed = urlsplit(absolute)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in MOC_HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        return None
    match = re.fullmatch(r"/letter-download/([0-9a-fA-F-]+)", parsed.path.rstrip("/"))
    if match is None or _UUID_RE.fullmatch(match.group(1)) is None:
        return None
    record_id = match.group(1).lower()
    return record_id, f"https://construction.gov.mm/letter-download/{record_id}"


def _canonical_pdf_url(raw_url: str | None, page_url: str = MOC_TENDER_URL) -> str | None:
    if not raw_url:
        return None
    absolute = urljoin(page_url, raw_url)
    parsed = urlsplit(absolute)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in MOC_HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/storage/TinDar/")
        or not parsed.path.lower().endswith(".pdf")
    ):
        return None
    return absolute


def _deadline(value: str) -> str | None:
    text = normalize_text(value)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


@dataclass(frozen=True)
class MocTender:
    record_id: str
    title: str
    deadline: str
    location: str
    url: str
    attachment_url: str | None

    item_kind = "TENDER"
    publication_date = None
    deadline_time = None

    @property
    def canonical_key(self) -> str:
        return f"moc:{self.record_id}"

    @property
    def reference_no(self) -> str:
        # The listing exposes a stable issuer UUID but no human tender number.
        return self.record_id

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": MOC_ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_tender_uuid",
            "source_record_id": self.record_id,
            "publication_date": None,
            "deadline": self.deadline,
            "deadline_time": None,
            "deadline_kind": "TENDER_END_DATE",
            "deadline_evidence": "EXPLICIT_OFFICIAL_LISTING_END_DATE",
            "location": self.location,
            "location_evidence": "OFFICIAL_LISTING_REGION_BADGE",
            "scope_summary": self.title,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "LISTING_TITLE_REGION_END_DATE_OFFICIAL_DOWNLOAD",
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "attachment_url": self.attachment_url,
            "url": self.url,
        }


@dataclass(frozen=True)
class _Card:
    title: str
    region: str
    deadline: str
    download_href: str
    pdf_href: str | None


class _TenderBoardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[_Card] = []
        self.card_count = 0
        self._card_depth = 0
        self._title_depth = 0
        self._region_depth = 0
        self._deadline_depth = 0
        self._title_parts: list[str] = []
        self._region_parts: list[str] = []
        self._deadline_parts: list[str] = []
        self._download_href: str | None = None
        self._pdf_href: str | None = None

    def _reset(self) -> None:
        self._title_depth = 0
        self._region_depth = 0
        self._deadline_depth = 0
        self._title_parts = []
        self._region_parts = []
        self._deadline_parts = []
        self._download_href = None
        self._pdf_href = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if not self._card_depth:
            if lowered == "div" and {"card", "shadow"}.issubset(classes):
                self._card_depth = 1
                self.card_count += 1
                self._reset()
            return

        if lowered not in _VOID_TAGS:
            self._card_depth += 1

        if lowered == "h5" and "card-title" in classes:
            self._title_depth = 1
        elif lowered == "span" and {"badge", "bg-warning"}.issubset(classes):
            self._region_depth = 1
        elif lowered == "span" and {"badge", "bg-success"}.issubset(classes):
            self._deadline_depth = 1
        elif lowered == "a":
            href = _attr(attrs, "href")
            if href and "download-btn" in classes:
                self._download_href = href
            elif href and "custom_canvas" in classes:
                self._pdf_href = href

        for field in ("_title_depth", "_region_depth", "_deadline_depth"):
            value = getattr(self, field)
            if value and not (
                (field == "_title_depth" and lowered == "h5" and "card-title" in classes)
                or (field == "_region_depth" and lowered == "span" and {"badge", "bg-warning"}.issubset(classes))
                or (field == "_deadline_depth" and lowered == "span" and {"badge", "bg-success"}.issubset(classes))
            ) and lowered not in _VOID_TAGS:
                setattr(self, field, value + 1)

    def handle_endtag(self, tag: str) -> None:
        if not self._card_depth:
            return
        lowered = tag.lower()
        for field in ("_title_depth", "_region_depth", "_deadline_depth"):
            value = getattr(self, field)
            if value and lowered not in _VOID_TAGS:
                setattr(self, field, value - 1)
        if lowered not in _VOID_TAGS:
            self._card_depth -= 1
        if self._card_depth == 0:
            self._finish()

    def handle_data(self, data: str) -> None:
        if not self._card_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self._title_parts.append(value)
        if self._region_depth:
            self._region_parts.append(value)
        if self._deadline_depth:
            self._deadline_parts.append(value)

    def _finish(self) -> None:
        title = normalize_text(" ".join(self._title_parts))
        region = normalize_text(" ".join(self._region_parts))
        deadline = normalize_text(" ".join(self._deadline_parts))
        if title and region and deadline and self._download_href:
            self.cards.append(_Card(title, region, deadline, self._download_href, self._pdf_href))
        self._reset()


def parse_tender_records(payload: bytes, page_url: str = MOC_TENDER_URL) -> list[MocTender]:
    if page_url != MOC_TENDER_URL:
        raise MocParseError("unexpected Ministry of Construction listing URL")

    parser = _TenderBoardParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise MocParseError("Ministry of Construction tender cards not found")

    records: list[MocTender] = []
    seen: set[str] = set()
    for card in parser.cards:
        if not _is_tender_title(card.title):
            continue
        identity = _canonical_download_url(card.download_href, page_url)
        deadline = _deadline(card.deadline)
        if identity is None or deadline is None:
            continue
        record_id, download_url = identity
        if record_id in seen:
            continue
        seen.add(record_id)
        records.append(
            MocTender(
                record_id=record_id,
                title=card.title,
                deadline=deadline,
                location=card.region,
                url=download_url,
                attachment_url=_canonical_pdf_url(card.pdf_href, page_url),
            )
        )

    if not records:
        raise MocParseError("Ministry of Construction listing had no valid tender records")
    return records
