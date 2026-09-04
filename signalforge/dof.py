from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .mpt import normalize_text

DOF_TENDERS_URL = "https://www.dof.gov.mm/index.php/my/tender"
DOF_ISSUER = "Department of Fisheries, Ministry of Agriculture, Livestock and Irrigation"
DOF_HOSTS = {"dof.gov.mm", "www.dof.gov.mm"}
_TENDER_TOKENS = ("တင်ဒါ", "tender")
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_DATE_RE = re.compile(r"(?P<day>\d{1,2})\s*[-/]\s*(?P<month>\d{1,2})\s*[-/]\s*(?P<year>20\d{2})")


class DofParseError(ValueError):
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


def _official_tender_url(raw_url: str, page_url: str = DOF_TENDERS_URL) -> str | None:
    url = urljoin(page_url, raw_url)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in DOF_HOSTS:
        return None
    path = parsed.path
    marker = "/my/tender/"
    if marker not in path:
        return None
    alias = path.split(marker, 1)[1].strip("/")
    if not alias or "/" in alias:
        return None
    if re.fullmatch(r"[0-9a-zA-Z_-]+", alias) is None:
        return None
    return f"https://www.dof.gov.mm/my/tender/{alias}"


def _alias(url: str) -> str:
    return urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]


def _visible_date(value: str) -> str | None:
    text = normalize_text(value).translate(_MYANMAR_DIGITS)
    match = _DATE_RE.search(text)
    if match is None:
        return None
    day = int(match.group("day"))
    month = int(match.group("month"))
    year = int(match.group("year"))
    try:
        value_date = date(year, month, day)
    except ValueError:
        return None
    return value_date.isoformat()


def _publication_date(datetime_value: str | None) -> str | None:
    if not datetime_value:
        return None
    match = re.match(r"^(20\d{2}-\d{2}-\d{2})T", datetime_value)
    return match.group(1) if match else None


def _is_tender_title(value: str) -> bool:
    text = normalize_text(value).lower()
    return bool(text) and any(token in text for token in _TENDER_TOKENS)


@dataclass(frozen=True)
class DofTender:
    source_record_id: str
    title: str
    scope: str
    publication_date: str
    tender_form_sale_date: str | None
    deadline: str
    url: str

    item_kind = "TENDER"
    location = None

    @property
    def reference_no(self) -> str:
        return self.source_record_id

    @property
    def reference_no_kind(self) -> str:
        return "issuer_tender_alias"

    @property
    def project_name(self) -> str:
        return self.scope

    @property
    def canonical_key(self) -> str:
        return f"dof:{self.source_record_id}"

    def payload(self) -> dict[str, str | None]:
        return {
            "item_kind": self.item_kind,
            "issuer": DOF_ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": self.reference_no_kind,
            "source_record_id": self.source_record_id,
            "publication_date": self.publication_date,
            "scope": self.scope,
            "tender_form_sale_date": self.tender_form_sale_date,
            "deadline": self.deadline,
            "deadline_evidence": "VISIBLE_TENDER_CLOSING_DATE_TEXT",
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "detail_completeness": "LISTING_COMPLETE_HTML_NO_ATTACHMENT_REQUIRED",
            "url": self.url,
        }


class DofTenderCardParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.rows: list[DofTender] = []
        self._card_depth = 0
        self._title_depth = 0
        self._p_depth = 0
        self._p_classes: set[str] = set()
        self._title_parts: list[str] = []
        self._p_parts: list[str] = []
        self._href: str | None = None
        self._published: str | None = None
        self._scope: str | None = None
        self._sale_text: str | None = None
        self._deadline_text: str | None = None

    def _reset(self) -> None:
        self._title_depth = 0
        self._p_depth = 0
        self._p_classes = set()
        self._title_parts = []
        self._p_parts = []
        self._href = None
        self._published = None
        self._scope = None
        self._sale_text = None
        self._deadline_text = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "div" and {"card", "shadow"}.issubset(classes):
            if self._card_depth == 0:
                self._card_depth = 1
                self._reset()
                return
        if not self._card_depth:
            return
        if lowered == "div":
            self._card_depth += 1
        if lowered == "h5" and "card-title" in classes:
            self._title_depth = 1
            return
        if self._title_depth:
            if lowered == "a":
                href = _attr(attrs, "href")
                if href:
                    self._href = _official_tender_url(href, self.page_url)
            if lowered not in {"br", "img", "input", "meta", "link"}:
                self._title_depth += 1
        if lowered == "p" and "card-text" in classes:
            self._p_depth = 1
            self._p_classes = classes
            self._p_parts = []
            return
        if self._p_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._p_depth += 1
        if lowered == "time":
            publication = _publication_date(_attr(attrs, "datetime"))
            if publication:
                self._published = publication

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._card_depth:
            return
        if self._title_depth and lowered in {"h5", "a", "span", "strong"}:
            self._title_depth -= 1
        if self._p_depth:
            if lowered == "p":
                text = normalize_text(" ".join(self._p_parts))
                if "text-bold" in self._p_classes and text:
                    self._scope = text
                elif "text-danger" in self._p_classes and text:
                    self._deadline_text = text
                elif "တင်ဒါပုံစံရောင်းချ" in text:
                    self._sale_text = text
                self._p_depth = 0
                self._p_classes = set()
                self._p_parts = []
            else:
                self._p_depth = max(0, self._p_depth - 1)
        if lowered == "div":
            self._card_depth -= 1
            if self._card_depth == 0:
                self._finish_card()

    def handle_data(self, data: str) -> None:
        if not self._card_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self._title_parts.append(value)
        if self._p_depth:
            self._p_parts.append(value)

    def _finish_card(self) -> None:
        title = normalize_text(" ".join(self._title_parts))
        deadline = _visible_date(self._deadline_text or "")
        sale_date = _visible_date(self._sale_text or "")
        if self._href and self._published and self._scope and deadline and _is_tender_title(title):
            source_record_id = _alias(self._href)
            self.rows.append(
                DofTender(
                    source_record_id=source_record_id,
                    title=title,
                    scope=self._scope,
                    publication_date=self._published,
                    tender_form_sale_date=sale_date,
                    deadline=deadline,
                    url=self._href,
                )
            )
        self._reset()


def parse_tender_records(html_bytes: bytes, page_url: str = DOF_TENDERS_URL) -> list[DofTender]:
    parser = DofTenderCardParser(page_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    dedup: dict[str, DofTender] = {}
    for tender in parser.rows:
        dedup.setdefault(tender.source_record_id, tender)
    tenders = list(dedup.values())
    if not tenders:
        raise DofParseError("no recognized DOF tender cards")
    return tenders
