from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from .mpt import normalize_text

MCRD_TENDER_URL = "https://www.mcrd.gov.mm/index.php?page=dGluZGEmbW8%3D"
MCRD_ISSUER = "Ministry of Cooperatives and Rural Development, Myanmar"
MCRD_HOSTS = {"mcrd.gov.mm", "www.mcrd.gov.mm"}
SELECTION_POLICY_VERSION = 1

_INCLUDE_TOKENS = (
    "တင်ဒါခေါ်ယူ",
    "တင်ဒါ ခေါ်ယူ",
    "အိတ်ဖွင့်တင်ဒါ",
    "အိတ်ဖွင့်တင်ဒါ",
    "tender invitation",
    "invitation to tender",
    "open tender",
)
_EXCLUDE_TOKENS = (
    "တင်ဒါအောင်",
    "အောင်မြင်",
    "ရွေးချယ်",
    "tender award",
    "awarded",
    "result",
)


class McrdParseError(ValueError):
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


def parse_closing_date(value: str) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def is_procurement_invitation(title: str) -> bool:
    value = normalize_text(title)
    lower = value.lower()
    if not value:
        return False
    if any(token.lower() in lower for token in _EXCLUDE_TOKENS):
        return False
    return any(token.lower() in lower for token in _INCLUDE_TOKENS)


def _official_document(raw_url: str, page_url: str = MCRD_TENDER_URL) -> str | None:
    url = urljoin(page_url, raw_url)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in MCRD_HOSTS:
        return None
    path = unquote(parsed.path)
    if not path.startswith("/tender_documents/") or path.rstrip("/") == "/tender_documents":
        return None
    encoded = quote(path, safe="/%^()_-. '＆&")
    return urlunsplit(("https", "www.mcrd.gov.mm", encoded, parsed.query, ""))


@dataclass(frozen=True)
class McrdTender:
    title: str
    closing_date: str
    department: str
    attachment_name: str
    attachment_url: str
    url: str = MCRD_TENDER_URL

    item_kind = "TENDER"
    publication_date = None
    location = None

    @property
    def deadline(self) -> str:
        return self.closing_date

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def record_fingerprint(self) -> str:
        material = "|".join(
            (
                normalize_text(self.title),
                self.closing_date,
                normalize_text(self.department),
            )
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()[:16]

    @property
    def reference_no(self) -> str:
        return f"MCRD-{self.closing_date.replace('-', '')}-{self.record_fingerprint[:8]}"

    @property
    def canonical_key(self) -> str:
        return f"mcrd:{self.closing_date}:{self.record_fingerprint}"

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": MCRD_ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_archive_event_fingerprint",
            "identity_material": "normalized_title+closing_date+department",
            "publication_date": None,
            "publication_date_evidence": "UNKNOWN_NOT_EXPOSED_IN_TENDER_BOARD_HTML",
            "deadline": self.deadline,
            "deadline_evidence": "EXPLICIT_TENDER_BOARD_CLOSING_DATE",
            "department": self.department,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "HTML_BOARD_TITLE_DEADLINE_DEPARTMENT_DOCUMENT_METADATA",
            "url": self.url,
        }


@dataclass(frozen=True)
class _Cell:
    text: str
    hrefs: tuple[str, ...]


class McrdTenderBoardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[list[tuple[_Cell, _Cell]]] = []
        self.block_count = 0
        self._block_depth = 0
        self._in_row = False
        self._cell_tag: str | None = None
        self._cell_parts: list[str] = []
        self._cell_hrefs: list[str] = []
        self._row_cells: list[_Cell] = []
        self._rows: list[tuple[_Cell, _Cell]] = []

    def _reset_block(self) -> None:
        self._in_row = False
        self._cell_tag = None
        self._cell_parts = []
        self._cell_hrefs = []
        self._row_cells = []
        self._rows = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "div":
            if self._block_depth:
                self._block_depth += 1
            elif "alert" in classes and "alert-info" in classes:
                self._block_depth = 1
                self.block_count += 1
                self._reset_block()
                return
        if not self._block_depth:
            return
        if lowered == "tr":
            self._in_row = True
            self._row_cells = []
            return
        if self._in_row and lowered in {"th", "td"}:
            self._cell_tag = lowered
            self._cell_parts = []
            self._cell_hrefs = []
            return
        if self._cell_tag and lowered == "a":
            href = _attr(attrs, "href")
            if href:
                self._cell_hrefs.append(href)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._block_depth:
            return
        if self._cell_tag and lowered == self._cell_tag:
            self._row_cells.append(
                _Cell(
                    text=normalize_text(" ".join(self._cell_parts)),
                    hrefs=tuple(self._cell_hrefs),
                )
            )
            self._cell_tag = None
            self._cell_parts = []
            self._cell_hrefs = []
            return
        if lowered == "tr" and self._in_row:
            if len(self._row_cells) >= 2:
                self._rows.append((self._row_cells[0], self._row_cells[1]))
            self._in_row = False
            self._row_cells = []
            return
        if lowered == "div":
            self._block_depth -= 1
            if self._block_depth == 0:
                if self._rows:
                    self.blocks.append(list(self._rows))
                self._reset_block()

    def handle_data(self, data: str) -> None:
        if not self._block_depth or self._cell_tag is None:
            return
        value = normalize_text(data)
        if value:
            self._cell_parts.append(value)


def parse_tender_records(html_bytes: bytes, page_url: str = MCRD_TENDER_URL) -> list[McrdTender]:
    parser = McrdTenderBoardParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.block_count == 0:
        raise McrdParseError("MCRD tender board structure not found")

    selected: list[McrdTender] = []
    seen: dict[str, str] = {}
    for rows in parser.blocks:
        fields: dict[str, _Cell] = {}
        for label_cell, value_cell in rows:
            label = normalize_text(label_cell.text)
            if label:
                fields[label] = value_cell

        title_cell = next((v for k, v in fields.items() if "ခေါင်းစဉ်" in k), None)
        deadline_cell = next((v for k, v in fields.items() if "ပိတ်သိမ်းမည့်ရက်" in k), None)
        info_cell = next((v for k, v in fields.items() if "တင်ဒါဆိုင်ရာအချက်အလက်များ" in k), None)
        dept_cell = next((v for k, v in fields.items() if "ဌာန" in k), None)
        if title_cell is None or deadline_cell is None or info_cell is None or dept_cell is None:
            continue
        title = normalize_text(title_cell.text)
        if not is_procurement_invitation(title):
            continue
        closing_date = parse_closing_date(deadline_cell.text)
        if closing_date is None:
            continue
        attachment_url = next((_official_document(href, page_url) for href in info_cell.hrefs if _official_document(href, page_url)), None)
        if attachment_url is None:
            continue
        attachment_name = unquote(urlsplit(attachment_url).path.rsplit("/", 1)[-1])
        department = normalize_text(dept_cell.text)
        if not department:
            continue
        item = McrdTender(
            title=title,
            closing_date=closing_date,
            department=department,
            attachment_name=attachment_name,
            attachment_url=attachment_url,
            url=page_url,
        )
        prior_attachment = seen.get(item.canonical_key)
        if prior_attachment is not None:
            if prior_attachment != item.attachment_url:
                raise McrdParseError(f"MCRD identity collision: {item.canonical_key}")
            continue
        seen[item.canonical_key] = item.attachment_url
        selected.append(item)

    return selected
