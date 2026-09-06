from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from .mpt import SitemapEntry, normalize_text

YANGON_BASE_URL = "https://www.yangon.gov.mm"
YANGON_TENDERS_URL = f"{YANGON_BASE_URL}/category/tenders/"
YANGON_PUBLISHER = "Yangon Region Government"
YANGON_HOSTS = {"yangon.gov.mm", "www.yangon.gov.mm"}

_TENDER_TOKENS = ("တင်ဒါ", "အိတ်ဖွင့်", "အိတ်ဖွင့်", "open tender")
_OUTCOME_TOKENS = ("အောင်မြင်", "ရွေးချယ်", "winner", "award", "awarded", "result")
_VOID_TAGS = {"br", "img", "input", "meta", "link", "hr", "source", "area", "base", "embed", "param", "track", "wbr"}
_DATE_FORMATS = ("%d %B, %Y", "%d %b, %Y", "%d %B %Y", "%d %b %Y")
_GENERIC_REFERENCE_VALUES = {"ဖော်ပြပါအတိုင်း", "as stated", "as shown"}


class YangonRegionParseError(ValueError):
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


def _post_id(attrs) -> str | None:  # type: ignore[no-untyped-def]
    value = _attr(attrs, "id") or ""
    match = re.fullmatch(r"post-(\d+)", value)
    if match:
        return match.group(1)
    for token in _classes(attrs):
        match = re.fullmatch(r"post-(\d+)", token)
        if match:
            return match.group(1)
    return None


def _canonical_post_url(raw_url: str) -> str | None:
    absolute = urljoin(YANGON_BASE_URL, raw_url)
    parsed = urlsplit(absolute)
    if parsed.scheme != "https" or parsed.hostname not in YANGON_HOSTS or parsed.username or parsed.password:
        return None
    if parsed.port not in (None, 443) or parsed.query or parsed.fragment:
        return None
    decoded = unquote(parsed.path)
    parts = [part for part in decoded.split("/") if part]
    if len(parts) != 1 or parts[0].lower() in {"category", "tenders"}:
        return None
    encoded = quote(decoded if decoded.endswith("/") else decoded + "/", safe="/-._~")
    return urlunsplit(("https", "www.yangon.gov.mm", encoded, "", ""))


def _is_opportunity_title(value: str) -> bool:
    clean = normalize_text(value)
    lower = clean.lower()
    if not clean or any(token.lower() in lower for token in _OUTCOME_TOKENS):
        return False
    return any(token.lower() in lower for token in _TENDER_TOKENS)


def _parse_updated(value: str) -> tuple[str, str] | None:
    clean = normalize_text(value)
    try:
        parsed = datetime.fromisoformat(clean)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.date().isoformat(), parsed.isoformat()


def _parse_visible_date(value: str) -> str | None:
    clean = normalize_text(value)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(clean, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _clean_field(value: str | None) -> str | None:
    clean = normalize_text((value or "").replace("\u200b", "").replace("\u200c", "").replace("\ufeff", ""))
    return None if clean in {"", "-", "–", "—"} else clean


def _clean_reference(value: str | None) -> str | None:
    clean = _clean_field(value)
    if clean is None or clean.lower() in _GENERIC_REFERENCE_VALUES:
        return None
    return clean


def _field(fields: dict[str, str], token: str) -> str | None:
    for key, value in fields.items():
        clean_key = _clean_field(key) or ""
        if token in clean_key:
            return _clean_field(value)
    return None


class YangonListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self.article_count = 0
        self._article_active = False
        self._post_id: str | None = None
        self._title_active = False
        self._title_parts: list[str] = []
        self._url: str | None = None
        self._updated_active = False
        self._updated_parts: list[str] = []

    def _reset(self) -> None:
        self._post_id = None
        self._title_active = False
        self._title_parts = []
        self._url = None
        self._updated_active = False
        self._updated_parts = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "article" and not self._article_active and "category-tenders" in classes:
            self._article_active = True
            self.article_count += 1
            self._reset()
            self._post_id = _post_id(attrs)
            return
        if not self._article_active:
            return
        if lowered in {"h1", "h2", "h3"} and "entry-title" in classes:
            self._title_active = True
            return
        if lowered == "span" and "updated" in classes:
            self._updated_active = True
            return
        if self._title_active and lowered == "a":
            href = _attr(attrs, "href")
            if href:
                self._url = _canonical_post_url(href)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._article_active:
            return
        if self._title_active and lowered in {"h1", "h2", "h3"}:
            self._title_active = False
        if self._updated_active and lowered == "span":
            self._updated_active = False
        if lowered == "article":
            title = normalize_text(" ".join(self._title_parts))
            updated = _parse_updated(" ".join(self._updated_parts))
            if self._post_id and self._url and updated and _is_opportunity_title(title):
                self.entries.append(SitemapEntry(self._url, updated[1]))
            self._article_active = False
            self._reset()

    def handle_data(self, data: str) -> None:
        if not self._article_active:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_active:
            self._title_parts.append(value)
        if self._updated_active:
            self._updated_parts.append(value)


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = YangonListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.article_count == 0:
        raise YangonRegionParseError("Yangon Region tender category structure not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class YangonRegionTender:
    source_record_id: str
    title: str
    publication_date: str
    tender_form_sale_date: str | None
    deadline: str
    tender_reference: str | None
    department: str | None
    business_type: str | None
    estimated_value: str | None
    location: str | None
    scope_summary: str | None
    url: str

    item_kind = "TENDER"

    @property
    def reference_no(self) -> str:
        return self.tender_reference or f"YRG-POST-{self.source_record_id}"

    @property
    def reference_no_kind(self) -> str:
        return "issuer_tender_reference" if self.tender_reference else "wordpress_post_id"

    @property
    def project_name(self) -> str:
        if self.scope_summary:
            return self.scope_summary[:500]
        if self.business_type:
            return self.business_type
        return self.title

    @property
    def canonical_key(self) -> str:
        return f"yangon-region:{self.source_record_id}"

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": self.department or YANGON_PUBLISHER,
            "publisher": YANGON_PUBLISHER,
            "publisher_scope": "REGIONAL_MULTI_AGENCY",
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": self.reference_no_kind,
            "source_record_id": self.source_record_id,
            "publication_date": self.publication_date,
            "publication_evidence": "VISIBLE_POST_DATE_MATCHED_UPDATED_TIMESTAMP",
            "tender_form_sale_date": self.tender_form_sale_date,
            "deadline": self.deadline,
            "deadline_evidence": "VISIBLE_STRUCTURED_CLOSING_DATE",
            "department": self.department,
            "business_type": self.business_type,
            "estimated_value": self.estimated_value,
            "location": self.location,
            "scope_summary": self.scope_summary,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "STRUCTURED_HTML_FIELDS_AND_BODY",
            "cross_source_overlap_policy": "REVIEW_BEFORE_DIRECT_AGENCY_ONBOARDING",
            "url": self.url,
        }


class YangonDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.post_id: str | None = None
        self.title_parts: list[str] = []
        self.updated_parts: list[str] = []
        self.visible_day_parts: list[str] = []
        self.visible_month_parts: list[str] = []
        self.fields: dict[str, str] = {}
        self.content_parts: list[str] = []
        self._article_active = False
        self._title_active = False
        self._updated_active = False
        self._post_date_div_depth = 0
        self._day_active = False
        self._month_active = False
        self._field_div_depth = 0
        self._row_active = False
        self._cell_active = False
        self._cell_parts: list[str] = []
        self._row_cells: list[str] = []
        self._content_div_depth = 0
        self._ignore_tag: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "article" and not self._article_active and "category-tenders" in classes:
            post_id = _post_id(attrs)
            if post_id:
                self._article_active = True
                self.post_id = post_id
            return
        if not self._article_active:
            return
        if self._ignore_tag:
            return
        if lowered in {"script", "style", "noscript"}:
            self._ignore_tag = lowered
            return
        if lowered in {"h1", "h2"} and "entry-title" in classes:
            self._title_active = True
            return
        if lowered == "span" and "updated" in classes:
            self._updated_active = True
            return
        if lowered == "div":
            if self._post_date_div_depth:
                self._post_date_div_depth += 1
            elif "post-date" in classes:
                self._post_date_div_depth = 1
            if self._field_div_depth:
                self._field_div_depth += 1
            elif "wwm-tender-field" in classes:
                self._field_div_depth = 1
            if self._content_div_depth:
                self._content_div_depth += 1
            elif "entry-content" in classes:
                self._content_div_depth = 1
        if self._post_date_div_depth and lowered == "span" and "day" in classes:
            self._day_active = True
        elif self._post_date_div_depth and lowered == "span" and "month" in classes:
            self._month_active = True
        if self._field_div_depth and lowered == "tr":
            self._row_active = True
            self._row_cells = []
        elif self._row_active and lowered in {"td", "th"}:
            self._cell_active = True
            self._cell_parts = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._article_active:
            return
        if self._ignore_tag:
            if lowered == self._ignore_tag:
                self._ignore_tag = None
            return
        if self._cell_active and lowered in {"td", "th"}:
            self._row_cells.append(normalize_text(" ".join(self._cell_parts)))
            self._cell_active = False
            self._cell_parts = []
        if self._row_active and lowered == "tr":
            cells = [normalize_text(cell) for cell in self._row_cells]
            if len(cells) >= 2 and cells[0]:
                self.fields[cells[0]] = cells[1]
            self._row_active = False
            self._row_cells = []
        if self._title_active and lowered in {"h1", "h2"}:
            self._title_active = False
        if self._updated_active and lowered == "span":
            self._updated_active = False
        if self._day_active and lowered == "span":
            self._day_active = False
        if self._month_active and lowered == "span":
            self._month_active = False
        if lowered == "div":
            if self._post_date_div_depth:
                self._post_date_div_depth -= 1
            if self._field_div_depth:
                self._field_div_depth -= 1
            if self._content_div_depth:
                self._content_div_depth -= 1
        if lowered == "article":
            self._article_active = False

    def handle_data(self, data: str) -> None:
        if not self._article_active or self._ignore_tag:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_active:
            self.title_parts.append(value)
        if self._updated_active:
            self.updated_parts.append(value)
        if self._day_active:
            self.visible_day_parts.append(value)
        if self._month_active:
            self.visible_month_parts.append(value)
        if self._cell_active:
            self._cell_parts.append(value)
        if self._content_div_depth:
            self.content_parts.append(value)


def parse_tender_detail(html_bytes: bytes, page_url: str) -> YangonRegionTender | None:
    canonical_url = _canonical_post_url(page_url)
    if canonical_url is None:
        return None
    parser = YangonDetailParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    if parser.post_id is None or not title or not _is_opportunity_title(title):
        return None
    updated = _parse_updated(" ".join(parser.updated_parts))
    if updated is None:
        return None
    publication_date = updated[0]
    try:
        publication = datetime.fromisoformat(publication_date)
    except ValueError:
        return None
    visible_day = normalize_text(" ".join(parser.visible_day_parts))
    visible_month = normalize_text(" ".join(parser.visible_month_parts))
    if not visible_day.isdigit() or int(visible_day) != publication.day or visible_month.lower() != publication.strftime("%b").lower():
        return None

    sale_date = _parse_visible_date(_field(parser.fields, "တင်ဒါစတင်ရောင်းချသည့်နေ့") or "")
    deadline = _parse_visible_date(_field(parser.fields, "တင်ဒါပိတ်မည့်ရက်စွဲ") or "")
    if deadline is None:
        return None
    tender_reference = _clean_reference(_field(parser.fields, "တင်ဒါအမှတ်"))
    department = _clean_field(_field(parser.fields, "ဌာန"))
    business_type = _clean_field(_field(parser.fields, "လုပ်ငန်းအမျိုးအစား"))
    estimated_value = _clean_field(_field(parser.fields, "ခန့်မှန်းတန်ဖိုး"))
    location = _clean_field(_field(parser.fields, "လုပ်ငန်းဆောင်ရွက်မည့်နေရာ"))
    scope = normalize_text(" ".join(parser.content_parts))
    if not (business_type or scope):
        return None
    return YangonRegionTender(
        source_record_id=parser.post_id,
        title=title,
        publication_date=publication_date,
        tender_form_sale_date=sale_date,
        deadline=deadline,
        tender_reference=tender_reference,
        department=department,
        business_type=business_type,
        estimated_value=estimated_value,
        location=location,
        scope_summary=scope[:4000] if scope else None,
        url=canonical_url,
    )
