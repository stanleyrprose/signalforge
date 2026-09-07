from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .mpt import SitemapEntry, normalize_text

MOI_BASE_URL = "https://www.moi.gov.mm"
MOI_LIST_URL = f"{MOI_BASE_URL}/department-announcement"
MOI_ISSUER = "Ministry of Information, Ministerial Office, Myanmar"
MOI_HOSTS = {"moi.gov.mm", "www.moi.gov.mm"}
SELECTION_POLICY_VERSION = 1

_OPEN_TENDER_TOKENS = (
    "အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
    "အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
    "အိတ်ဖွင့်တင်ဒါ တင်သွင်းရန် ဖိတ်ခေါ်",
    "အိတ်ဖွင့်တင်ဒါ တင်သွင်းရန် ဖိတ်ခေါ်",
    "open tender",
    "invitation to tender",
)
_EXCLUDE_STAGE_TOKENS = (
    "တင်ဒါအောင်",
    "အောင်မြင်ကြောင်း",
    "အောင်စာရင်း",
    "tender award",
    "awarded",
    "winner",
    "result",
)
_MINISTERIAL_OFFICE_TOKENS = (
    "ပြန်ကြားရေးဝန်ကြီးဌာန",
    "ဝန်ကြီးရုံး",
)
_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_SALE_WINDOW_RE = re.compile(
    r"(?P<start_day>\d{1,2})\s*-\s*(?P<start_month>\d{1,2})\s*-\s*(?P<start_year>20\d{2})"
    r".{0,80}?ရက်နေ့မှ.{0,160}?"
    r"(?P<end_day>\d{1,2})\s*-\s*(?P<end_month>\d{1,2})\s*-\s*(?P<end_year>20\d{2})"
    r".{0,40}?ရက်နေ့အထိ"
)
_DEADLINE_RE = re.compile(
    r"(?P<day>\d{1,2})\s*-\s*(?P<month>\d{1,2})\s*-\s*(?P<year>20\d{2})"
    r".{0,120}?နောက်ဆုံးထား"
)


class MoiParseError(ValueError):
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


def _canonical_announcement_url(raw_url: str) -> tuple[str, str] | None:
    url = urljoin(MOI_BASE_URL, raw_url)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in MOI_HOSTS:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 80, 443) or parsed.params or parsed.query or parsed.fragment:
        return None
    match = re.fullmatch(r"/announcements/(\d+)", parsed.path.rstrip("/"))
    if match is None:
        return None
    node_id = match.group(1)
    return node_id, f"{MOI_BASE_URL}/announcements/{node_id}"


def _listing_datetime(value: str) -> str | None:
    text = normalize_text(value)
    try:
        parsed = datetime.strptime(text, "%b %d, %Y")
    except ValueError:
        return None
    return f"{parsed.date().isoformat()}T00:00:00+06:30"


def _detail_publication_date(value: str) -> str | None:
    text = normalize_text(value)
    try:
        parsed = datetime.strptime(text, "%m/%d/%Y")
    except ValueError:
        return None
    return parsed.date().isoformat()


def _iso_dmy_match(match: re.Match[str] | None, prefix: str = "") -> str | None:
    if match is None:
        return None
    try:
        day = int(match.group(prefix + "day"))
        month = int(match.group(prefix + "month"))
        year = int(match.group(prefix + "year"))
        return datetime(year, month, day).date().isoformat()
    except (ValueError, IndexError):
        return None


def _sale_window(text: str) -> tuple[str | None, str | None]:
    normalized = normalize_text(text).translate(_MYANMAR_DIGITS)
    match = _SALE_WINDOW_RE.search(normalized)
    if match is None:
        return None, None
    start = _iso_dmy_match(match, "start_")
    end = _iso_dmy_match(match, "end_")
    return start, end


def _deadline(text: str) -> str | None:
    normalized = normalize_text(text).translate(_MYANMAR_DIGITS)
    return _iso_dmy_match(_DEADLINE_RE.search(normalized))


def is_ministerial_office_tender(title: str) -> bool:
    value = normalize_text(title)
    lower = value.lower()
    if not value:
        return False
    if not all(token in value for token in _MINISTERIAL_OFFICE_TOKENS):
        return False
    if any(token.lower() in lower for token in _EXCLUDE_STAGE_TOKENS):
        return False
    return any(token.lower() in lower for token in _OPEN_TENDER_TOKENS)


class MoiListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self.card_count = 0
        self._card_depth = 0
        self._title_depth = 0
        self._date_depth = 0
        self._title_parts: list[str] = []
        self._date_parts: list[str] = []
        self._href: str | None = None

    def _reset(self) -> None:
        self._title_depth = 0
        self._date_depth = 0
        self._title_parts = []
        self._date_parts = []
        self._href = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "div":
            if self._card_depth:
                self._card_depth += 1
            elif {"card", "shadow", "mb-3"}.issubset(classes):
                self._card_depth = 1
                self.card_count += 1
                self._reset()
                return
        if not self._card_depth:
            return
        if lowered == "div" and {"card-title", "news-title"}.issubset(classes):
            self._title_depth = 1
            return
        if lowered == "p" and "my-3" in classes and self._date_depth == 0:
            self._date_depth = 1
            return
        if self._title_depth:
            if lowered == "a":
                href = _attr(attrs, "href")
                if href:
                    self._href = href
            if lowered not in {"br", "img", "input", "meta", "link", "hr"}:
                self._title_depth += 1
        if self._date_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._date_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._card_depth:
            return
        if self._title_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._title_depth -= 1
        if self._date_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._date_depth -= 1
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
        if self._date_depth:
            self._date_parts.append(value)

    def _finish_card(self) -> None:
        title = normalize_text(" ".join(self._title_parts))
        listed_at = _listing_datetime(" ".join(self._date_parts))
        identity = _canonical_announcement_url(self._href or "")
        if identity is not None and listed_at is not None and is_ministerial_office_tender(title):
            _node_id, canonical_url = identity
            self.entries.append(SitemapEntry(canonical_url, listed_at))
        self._reset()


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = MoiListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise MoiParseError("MOI department-announcement card structure not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class MoiTender:
    node_id: str
    title: str
    publication_date: str
    scope_summary: str
    tender_form_sale_start: str | None
    tender_form_sale_end: str | None
    deadline: str
    url: str

    item_kind = "TENDER"
    location = None

    @property
    def canonical_key(self) -> str:
        return f"moi:{self.node_id}"

    @property
    def reference_no(self) -> str:
        return f"MOI-NODE-{self.node_id}"

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": MOI_ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "drupal_node_id",
            "source_record_id": self.node_id,
            "publication_date": self.publication_date,
            "publication_date_evidence": "DETAIL_VISIBLE_MM_DD_YYYY",
            "scope_summary": self.scope_summary,
            "tender_form_sale_start": self.tender_form_sale_start,
            "tender_form_sale_end": self.tender_form_sale_end,
            "deadline": self.deadline,
            "deadline_evidence": "EXPLICIT_HTML_FINAL_SUBMISSION_DATE",
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "HTML_BUSINESS_SCOPE_AND_DEADLINE_NO_ATTACHMENT_REQUIRED",
            "attachment_policy": "HTML_ONLY_NO_ATTACHMENT_REQUIRED",
            "url": self.url,
        }


class MoiDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.node_id: str | None = None
        self._article_depth = 0
        self._title_depth = 0
        self._body_depth = 0
        self._date_depth = 0
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.date_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "article":
            if self._article_depth:
                self._article_depth += 1
            elif "node--type-announcements" in classes:
                node_id = _attr(attrs, "data-history-node-id")
                if node_id and node_id.isdigit():
                    self._article_depth = 1
                    self.node_id = node_id
            return
        if not self._article_depth:
            return
        if lowered == "h1" and "post-title" in classes:
            self._title_depth = 1
            return
        if lowered == "span" and "post-created" in classes:
            self._date_depth = 1
            return
        if lowered == "div" and "field--name-body" in classes:
            self._body_depth = 1
            return
        if self._title_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._title_depth += 1
        if self._date_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._date_depth += 1
        if self._body_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._body_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._article_depth:
            return
        if self._title_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._title_depth -= 1
        if self._date_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._date_depth -= 1
        if self._body_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._body_depth -= 1
        if lowered == "article":
            self._article_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._article_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._date_depth:
            self.date_parts.append(value)
        if self._body_depth:
            self.body_parts.append(value)


def parse_tender_detail(html_bytes: bytes, page_url: str) -> MoiTender | None:
    identity = _canonical_announcement_url(page_url)
    if identity is None:
        return None
    expected_node_id, canonical_url = identity
    parser = MoiDetailParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    publication_date = _detail_publication_date(" ".join(parser.date_parts))
    body = normalize_text(" ".join(parser.body_parts))
    deadline = _deadline(body)
    sale_start, sale_end = _sale_window(body)
    if (
        parser.node_id != expected_node_id
        or not title
        or not is_ministerial_office_tender(title)
        or publication_date is None
        or not body
        or deadline is None
    ):
        return None
    return MoiTender(
        node_id=expected_node_id,
        title=title,
        publication_date=publication_date,
        scope_summary=body[:2500],
        tender_form_sale_start=sale_start,
        tender_form_sale_end=sale_end,
        deadline=deadline,
        url=canonical_url,
    )
