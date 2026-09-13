from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from .mpt import normalize_text

PTD_BASE_URL = "https://www.ptd.gov.mm"
PTD_POLICY_URL = f"{PTD_BASE_URL}/LawsFP.aspx"
PTD_ISSUER = "Posts and Telecommunications Department, Ministry of Digital Development and Communications, Myanmar"
PTD_HOSTS = {"ptd.gov.mm", "www.ptd.gov.mm"}
SELECTION_POLICY_VERSION = 1

_STRATEGIC_TOKENS = (
    "spectrum",
    "frequency",
    "5g",
    "2600 mhz",
    "2.6 ghz",
    "digital master plan",
    "digital masterplan",
    "broadband",
    "internet exchange",
    "numbering plan",
    "connectivity",
    "telecommunication",
    "ict master plan",
)


class PtdPolicyParseError(ValueError):
    pass


def _attr(attrs, name: str) -> str | None:  # type: ignore[no-untyped-def]
    for key, value in attrs:
        if key == name and value is not None:
            return str(value)
    return None


def _canonical_attachment(raw_url: str, page_url: str = PTD_POLICY_URL) -> str | None:
    absolute = urljoin(page_url, raw_url)
    parsed = urlsplit(absolute)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in PTD_HOSTS:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.fragment:
        return None
    path = unquote(parsed.path)
    if not path.lower().startswith("/uploads/lawfp/attach/") or not path.lower().endswith(".pdf"):
        return None
    return urlunsplit(("https", "www.ptd.gov.mm", quote(path, safe="/%()_-.'"), parsed.query, ""))


def _parse_date(value: str) -> str | None:
    clean = normalize_text(value)
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(clean, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _strategic_kind(title: str) -> str | None:
    lower = normalize_text(title).lower()
    if not any(token in lower for token in _STRATEGIC_TOKENS):
        return None
    if any(token in lower for token in ("spectrum", "frequency", "5g", "2600 mhz", "2.6 ghz")):
        return "SPECTRUM_5G_POLICY"
    if "numbering" in lower:
        return "NUMBERING_POLICY"
    if "internet exchange" in lower:
        return "INTERNET_EXCHANGE_POLICY"
    return "DIGITAL_CONNECTIVITY_POLICY"


@dataclass(frozen=True)
class PtdPolicyNotice:
    title: str
    publication_date: str
    attachment_url: str
    strategic_kind: str

    item_kind = "REGULATORY_NOTICE"
    deadline = None
    location = "Myanmar"

    @property
    def identity_hash(self) -> str:
        material = f"{self.publication_date}|{normalize_text(self.title).lower()}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()[:16]

    @property
    def canonical_key(self) -> str:
        return f"ptd-policy:{self.publication_date}:{self.identity_hash}"

    @property
    def reference_no(self) -> str:
        return f"PTD-POLICY-{self.publication_date.replace('-', '')}-{self.identity_hash[:8]}"

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def url(self) -> str:
        return self.attachment_url

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": PTD_ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_policy_title_publication_date_fingerprint",
            "identity_material": "publication_date+normalized_policy_title",
            "publication_date": self.publication_date,
            "deadline": None,
            "location": self.location,
            "scope_summary": self.title,
            "attachment_name": unquote(urlsplit(self.attachment_url).path.rsplit("/", 1)[-1]),
            "attachment_url": self.attachment_url,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "STRATEGIC_INTELLIGENCE",
            "relevance_categories": ["TELECOM"],
            "telecom_signal_kind": self.strategic_kind,
            "detail_completeness": "OFFICIAL_POLICY_TABLE_TITLE_DATE_PDF_LINK",
            "attachment_policy": "METADATA_ONLY_OFFICIAL_PDF_NOT_FETCHED",
            "url": self.url,
        }


class _PolicyTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.table_seen = False
        self.rows: list[tuple[str, str, str]] = []
        self._in_table = False
        self._row_depth = 0
        self._title_depth = 0
        self._title_parts: list[str] = []
        self._row_parts: list[str] = []
        self._attachment_url: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        tag = tag.lower()
        if tag == "table" and _attr(attrs, "id") == "ContentPlaceHolder1_gvnews":
            self.table_seen = True
            self._in_table = True
            return
        if not self._in_table:
            return
        if tag == "tr":
            if self._row_depth == 0:
                self._title_parts = []
                self._row_parts = []
                self._attachment_url = None
            self._row_depth += 1
            return
        if not self._row_depth:
            return
        if tag == "h6":
            self._title_depth = 1
            return
        if self._title_depth and tag not in {"br", "img", "input", "meta", "link", "hr"}:
            self._title_depth += 1
        if tag == "a" and self._attachment_url is None:
            href = _attr(attrs, "href")
            if href:
                self._attachment_url = _canonical_attachment(href)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if not self._in_table:
            return
        if self._title_depth:
            self._title_depth -= 1
        if tag == "tr" and self._row_depth:
            self._row_depth -= 1
            if self._row_depth == 0:
                title = normalize_text(" ".join(self._title_parts))
                text = normalize_text(" ".join(self._row_parts))
                if title and self._attachment_url:
                    # The visible publication date is the final English date in each row.
                    matches = re.findall(r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2},?\s+20\d{2}", text, re.I)
                    date = _parse_date(matches[-1]) if matches else None
                    if date:
                        self.rows.append((title, date, self._attachment_url))
        if tag == "table":
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if not self._row_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        self._row_parts.append(value)
        if self._title_depth:
            self._title_parts.append(value)


def parse_policy_records(html_bytes: bytes, page_url: str = PTD_POLICY_URL) -> list[PtdPolicyNotice]:
    parser = _PolicyTableParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if not parser.table_seen:
        raise PtdPolicyParseError("PTD policy table structure not found")

    selected: list[PtdPolicyNotice] = []
    seen: dict[str, str] = {}
    for title, publication_date, attachment_url in parser.rows:
        kind = _strategic_kind(title)
        if kind is None:
            continue
        item = PtdPolicyNotice(title, publication_date, attachment_url, kind)
        prior = seen.get(item.canonical_key)
        if prior is not None and prior != attachment_url:
            raise PtdPolicyParseError(f"PTD policy identity collision: {item.canonical_key}")
        if prior is None:
            seen[item.canonical_key] = attachment_url
            selected.append(item)
    return selected
