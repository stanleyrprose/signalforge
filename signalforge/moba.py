from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .mpt import SitemapEntry, normalize_text

MOBA_BASE_URL = "https://moba.gov.mm"
MOBA_LIST_URL = f"{MOBA_BASE_URL}/my/tender"
MOBA_HOST = "moba.gov.mm"
MOBA_ISSUER = "Ministry of Border Affairs, Myanmar"
SELECTION_POLICY_VERSION = 1

_TENDER_TOKENS = ("တင်ဒါ", "open tender")
_OUTCOME_TOKENS = ("တင်ဒါအောင်", "အောင်မြင်", "ကုမ္ပဏီများစာရင်း", "winner", "award", "result")


class MobaParseError(ValueError):
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


def _canonical_tender_url(raw_url: str) -> tuple[str, str] | None:
    url = urljoin(MOBA_BASE_URL, raw_url)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != MOBA_HOST:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.params or parsed.query or parsed.fragment:
        return None
    match = re.fullmatch(r"/my/tender/(\d+)", parsed.path.rstrip("/"))
    if match is None:
        return None
    node_id = match.group(1)
    return node_id, f"{MOBA_BASE_URL}/my/tender/{node_id}"


def _is_opportunity_title(title: str) -> bool:
    value = normalize_text(title)
    lower = value.lower()
    if not value or any(token.lower() in lower for token in _OUTCOME_TOKENS):
        return False
    return any(token.lower() in lower for token in _TENDER_TOKENS)


def _date(value: str) -> str | None:
    text = normalize_text(value)
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    return match.group(1) if match is not None else None


class MobaListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self.row_count = 0
        self._in_row = False
        self._field: str | None = None
        self._start_parts: list[str] = []
        self._end_parts: list[str] = []
        self._title_parts: list[str] = []
        self._href: str | None = None

    def _reset_row(self) -> None:
        self._field = None
        self._start_parts = []
        self._end_parts = []
        self._title_parts = []
        self._href = None

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "tr" and "tinder-table" in classes:
            self._in_row = True
            self.row_count += 1
            self._reset_row()
            return
        if not self._in_row:
            return
        if lowered == "td":
            headers = _attr(attrs, "headers") or ""
            if "field-tindar-start-date" in headers:
                self._field = "start"
            elif "field-tindar-end-date" in headers:
                self._field = "end"
            elif headers == "view-title-table-column":
                self._field = "title"
            else:
                self._field = None
            return
        if lowered == "a" and self._field == "title":
            href = _attr(attrs, "href")
            if href:
                self._href = href

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._in_row:
            return
        if lowered == "td":
            self._field = None
        elif lowered == "tr":
            self._finish_row()
            self._in_row = False
            self._reset_row()

    def handle_data(self, data: str) -> None:
        if not self._in_row or self._field is None:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._field == "start":
            self._start_parts.append(value)
        elif self._field == "end":
            self._end_parts.append(value)
        elif self._field == "title":
            self._title_parts.append(value)

    def _finish_row(self) -> None:
        identity = _canonical_tender_url(self._href or "")
        title = normalize_text(" ".join(self._title_parts))
        start_date = _date(" ".join(self._start_parts))
        end_date = _date(" ".join(self._end_parts))
        if identity is None or start_date is None or end_date is None or not _is_opportunity_title(title):
            return
        _node_id, canonical_url = identity
        self.entries.append(SitemapEntry(canonical_url, f"{end_date}T00:00:00+06:30"))


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = MobaListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.row_count == 0:
        raise MobaParseError("MOBA tender table rows not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class MobaTender:
    node_id: str
    title: str
    sale_start_date: str
    deadline: str
    business_unit: str | None
    attachment_urls: tuple[str, ...]
    url: str

    item_kind = "TENDER"
    publication_date = None
    location = None

    @property
    def canonical_key(self) -> str:
        return f"moba:{self.node_id}"

    @property
    def reference_no(self) -> str:
        return f"MOBA-TENDER-{self.node_id}"

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": MOBA_ISSUER,
            "business_unit": self.business_unit,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "drupal_tender_node_id",
            "source_record_id": self.node_id,
            "publication_date": None,
            "publication_date_evidence": "NOT_PUBLISHED_BY_ISSUER",
            "sale_start_date": self.sale_start_date,
            "sale_start_date_evidence": "EXPLICIT_HTML_TENDER_FORM_SALE_DATE",
            "scope_summary": self.title,
            "deadline": self.deadline,
            "deadline_time": None,
            "deadline_evidence": "EXPLICIT_HTML_TENDER_FORM_CLOSE_DATE",
            "attachment_urls": list(self.attachment_urls),
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "HTML_TITLE_SCOPE_AND_DEADLINE_ATTACHMENT_METADATA_ONLY",
            "url": self.url,
        }


class MobaDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._title_depth = 0
        self._start_depth = 0
        self._end_depth = 0
        self._file_depth = 0
        self.title_parts: list[str] = []
        self.start_parts: list[str] = []
        self.end_parts: list[str] = []
        self.attachment_hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "h1" and "page-title" in classes:
            self._title_depth = 1
            return
        if lowered == "div" and "field--name-field-tindar-start-date" in classes:
            self._start_depth = 1
            return
        if lowered == "div" and "field--name-field-tindar-end-date" in classes:
            self._end_depth = 1
            return
        if lowered == "div" and "field--name-field-tindar-file" in classes:
            self._file_depth = 1
            return
        if lowered == "a" and self._file_depth:
            href = _attr(attrs, "href")
            if href and href.lower().split("?", 1)[0].endswith(".pdf"):
                self.attachment_hrefs.append(href)
        if lowered == "time":
            dt = _attr(attrs, "datetime")
            if dt:
                if self._start_depth:
                    self.start_parts.append(dt)
                if self._end_depth:
                    self.end_parts.append(dt)
        if lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            for name in ("_title_depth", "_start_depth", "_end_depth", "_file_depth"):
                if getattr(self, name):
                    setattr(self, name, getattr(self, name) + 1)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            for name in ("_title_depth", "_start_depth", "_end_depth", "_file_depth"):
                if getattr(self, name):
                    setattr(self, name, getattr(self, name) - 1)

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._start_depth:
            self.start_parts.append(value)
        if self._end_depth:
            self.end_parts.append(value)


def parse_tender_detail(html_bytes: bytes, page_url: str) -> MobaTender | None:
    identity = _canonical_tender_url(page_url)
    if identity is None:
        return None
    node_id, canonical_url = identity
    parser = MobaDetailParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    sale_start_date = _date(" ".join(parser.start_parts))
    deadline = _date(" ".join(parser.end_parts))
    if not _is_opportunity_title(title) or sale_start_date is None or deadline is None:
        return None
    business_unit = normalize_text(title.split("၊", 1)[0]) or None
    attachments: list[str] = []
    for href in parser.attachment_hrefs:
        url = urljoin(MOBA_BASE_URL, href)
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.hostname == MOBA_HOST and not parsed.fragment:
            attachments.append(url)
    return MobaTender(
        node_id=node_id,
        title=title,
        sale_start_date=sale_start_date,
        deadline=deadline,
        business_unit=business_unit,
        attachment_urls=tuple(dict.fromkeys(attachments)),
        url=canonical_url,
    )
