from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse

from .mpt import normalize_text, parse_date

NATIONAL_PORTAL_TENDER_URL = "https://myanmar.gov.mm/tenders"
NATIONAL_PORTAL_HOSTS = {"myanmar.gov.mm", "www.myanmar.gov.mm"}
SELECTION_POLICY_VERSION = 1

_TECH_TITLE_TERMS = (
    "telecom",
    "telecommunication",
    "server",
    "software",
    "network",
    "data center",
    "data centre",
    "database",
    "ict",
    "cyber",
    "digital",
    "gmdss",
    "vmware",
    "cisco",
    "red hat",
    "netapp",
    "veritas",
    " f5 ",
    "မြန်မာ့ဆက်သွယ်ရေး",
)
_UNCONDITIONAL_AGENCY_TERMS = (
    "ministry of digital development and communications",
    "central bank",
)
_CONDITIONAL_AGENCY_TERMS = (
    "planning and finance",
    "finance and revenue",
    "insurance",
)


def _attr(attrs, name: str) -> str | None:  # type: ignore[no-untyped-def]
    for key, value in attrs:
        if key == name and value is not None:
            return str(value)
    return None


def _classes(attrs) -> set[str]:  # type: ignore[no-untyped-def]
    value = _attr(attrs, "class") or ""
    return set(value.split())


def _canonical_url(raw_url: str, base_url: str) -> str | None:
    if not raw_url or raw_url == "#" or raw_url.lower().startswith("javascript:"):
        return None
    value = urljoin(base_url, raw_url)
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    if parsed.port not in (None, 443):
        return None
    return urlunparse(("https", parsed.netloc.lower(), parsed.path, "", "", ""))


def _document_id(url: str, *, agency: str, title: str, deadline: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    for part in reversed(parts):
        if len(part) == 36 and part.count("-") == 4:
            return part.lower()
    material = "|".join((agency, title, deadline, url))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _is_high_value(*, agency: str, title: str) -> bool:
    agency_lower = agency.lower()
    title_lower = f" {title.lower()} "
    if any(term in agency_lower for term in _UNCONDITIONAL_AGENCY_TERMS):
        return True
    tech_match = any(term in title_lower for term in _TECH_TITLE_TERMS)
    if tech_match:
        return True
    return any(term in agency_lower for term in _CONDITIONAL_AGENCY_TERMS) and tech_match


def _source_hint(*, agency: str, title: str) -> str | None:
    agency_lower = agency.lower()
    if "digital development and communications" in agency_lower and "မြန်မာ့ဆက်သွယ်ရေး" in title:
        return "S13"
    return None


@dataclass(frozen=True)
class NationalPortalLead:
    lead_id: str
    title: str
    agency: str
    closing_date_hint: str
    url: str
    target_source_hint: str | None
    evidence_kind: str

    def as_dict(self) -> dict[str, object]:
        return {
            "lead_id": self.lead_id,
            "title": self.title,
            "agency": self.agency,
            "closing_date_hint": self.closing_date_hint,
            "url": self.url,
            "target_source_hint": self.target_source_hint,
            "evidence_kind": self.evidence_kind,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "canonical_truth": False,
            "aggregator_only": True,
        }


class _TenderCardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, str]] = []
        self._row_depth = 0
        self._href: str | None = None
        self._title_depth = 0
        self._p_depth = 0
        self._span_mode: str | None = None
        self._title_parts: list[str] = []
        self._label_parts: list[str] = []
        self._value_parts: list[str] = []
        self._agency = ""
        self._closing = ""

    def _start_row(self) -> None:
        self._row_depth = 1
        self._href = None
        self._title_depth = 0
        self._p_depth = 0
        self._span_mode = None
        self._title_parts = []
        self._label_parts = []
        self._value_parts = []
        self._agency = ""
        self._closing = ""

    def _finish_p(self) -> None:
        label = normalize_text(" ".join(self._label_parts)).rstrip(":")
        value = normalize_text(" ".join(self._value_parts))
        if label.lower() == "agency":
            self._agency = value
        elif label.lower() == "closing date":
            self._closing = value
        self._label_parts = []
        self._value_parts = []
        self._span_mode = None

    def _finish_row(self) -> None:
        title = normalize_text(" ".join(self._title_parts))
        if title and self._agency and self._closing:
            self.rows.append({
                "title": title,
                "agency": self._agency,
                "closing": self._closing,
                "href": self._href or "",
            })
        self._row_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if self._row_depth == 0:
            if lowered == "div" and "smallcardstyle" in classes:
                self._start_row()
            return
        if lowered == "div":
            self._row_depth += 1
            return
        if lowered == "a" and not self._href:
            self._href = _attr(attrs, "href")
        elif lowered == "h2":
            self._title_depth += 1
        elif lowered == "p":
            self._p_depth += 1
            self._label_parts = []
            self._value_parts = []
        elif lowered == "span" and self._p_depth:
            if "graycolor" in classes:
                self._span_mode = "label"
            elif "blueColor1" in classes:
                self._span_mode = "value"

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._row_depth == 0:
            return
        if lowered == "h2" and self._title_depth:
            self._title_depth -= 1
        elif lowered == "span":
            self._span_mode = None
        elif lowered == "p" and self._p_depth:
            self._p_depth -= 1
            if self._p_depth == 0:
                self._finish_p()
        elif lowered == "div":
            self._row_depth -= 1
            if self._row_depth == 0:
                self._finish_row()

    def handle_data(self, data: str) -> None:
        if self._row_depth == 0:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self._title_parts.append(value)
        if self._span_mode == "label":
            self._label_parts.append(value)
        elif self._span_mode == "value":
            self._value_parts.append(value)


def parse_current_high_value_tender_leads(
    html_bytes: bytes,
    *,
    base_url: str = NATIONAL_PORTAL_TENDER_URL,
    today: date,
) -> list[dict[str, object]]:
    parser = _TenderCardParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if not parser.rows:
        raise ValueError("Myanmar National Portal tender cards not found")
    leads: list[NationalPortalLead] = []
    seen: set[str] = set()
    for row in parser.rows:
        deadline = parse_date(row["closing"])
        if deadline is None or deadline < today.isoformat():
            continue
        title = normalize_text(row["title"])
        agency = normalize_text(row["agency"])
        if not _is_high_value(agency=agency, title=title):
            continue
        url = _canonical_url(row["href"], base_url)
        if url is None:
            continue
        record_id = _document_id(url, agency=agency, title=title, deadline=deadline)
        lead_id = f"national-portal:{record_id}"
        if lead_id in seen:
            continue
        seen.add(lead_id)
        host = (urlparse(url).hostname or "").lower()
        evidence_kind = (
            "NATIONAL_PORTAL_HOSTED_DOCUMENT"
            if host in NATIONAL_PORTAL_HOSTS and urlparse(url).path.startswith("/documents/")
            else "NATIONAL_PORTAL_EXTERNAL_TARGET"
        )
        leads.append(NationalPortalLead(
            lead_id=lead_id,
            title=title,
            agency=agency,
            closing_date_hint=deadline,
            url=url,
            target_source_hint=_source_hint(agency=agency, title=title),
            evidence_kind=evidence_kind,
        ))
    leads.sort(key=lambda item: (item.closing_date_hint, item.agency, item.title, item.lead_id))
    return [lead.as_dict() for lead in leads]
