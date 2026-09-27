from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .mpt import SitemapEntry, normalize_text

CONSTRUCTION_BASE_URL = "https://construction.gov.mm"
CONSTRUCTION_PROJECT_LIST_URL = (
    f"{CONSTRUCTION_BASE_URL}/news-show/f87c94b0-d396-11ec-a8be-e9291a621227?page=1"
)
CONSTRUCTION_PROJECT_ISSUER = "Ministry of Construction, Myanmar"
CONSTRUCTION_HOSTS = {"construction.gov.mm", "www.construction.gov.mm"}
SELECTION_POLICY_VERSION = 1

_PROJECT_TOKENS = ("စီမံကိန်း", "project")
_SECTOR_TOKENS: dict[str, tuple[str, ...]] = {
    "CONSTRUCTION": (
        "construction", "infrastructure", "road", "bridge", "building", "housing",
        "urban development", "highway", "overpass",
        "ဆောက်လုပ်", "တည်ဆောက်", "လမ်း", "တံတား", "အဆောက်အအုံ", "အိမ်ရာ", "မြို့ပြ",
    ),
    "TELECOM": (
        "telecom", "telecommunication", "ict", "digital", "fiber", "fibre", "network",
        "cyber city", "data center", "data centre", "telematics", "5g",
        "ဆက်သွယ်ရေး", "ဒီဂျစ်တယ်", "ကွန်ရက်", "ဆိုက်ဘာစီးတီး",
    ),
    "ENERGY": (
        "energy", "power", "electric", "electricity", "grid", "substation", "solar", "hydropower",
        "စွမ်းအင်", "လျှပ်စစ်", "ဓာတ်အား",
    ),
    "ENGINEERING": (
        "engineering", "industrial zone", "water supply", "wastewater", "reservoir",
        "အင်ဂျင်နီယာ", "စက်မှုဇုန်", "ရေပေးဝေ", "ရေဆိုး", "ရေလှောင်ကန်",
    ),
}
_CAPITAL_INTENT_TOKENS = (
    "to construct", "will construct", "will be constructed", "planned construction",
    "to build", "will build", "will be built", "to upgrade", "will upgrade",
    "to expand", "will expand", "planned upgrade", "planned expansion",
    "တည်ဆောက်မည်", "တည်ဆောက်မည့်", "တည်ဆောက်ရန်",
    "ဆောက်လုပ်မည်", "ဆောက်လုပ်မည့်", "ဆောက်လုပ်ရန်",
    "အဆင့်မြှင့်မည်", "အဆင့်မြှင့်မည့်", "အဆင့်မြှင့်ရန်",
    "တိုးချဲ့မည်", "တိုးချဲ့မည့်", "တိုးချဲ့ရန်", "လျာထား",
)
_FORWARD_ACTION_TOKENS = (
    *_CAPITAL_INTENT_TOKENS,
    "approved project", "project approved", "approval granted", "approved for implementation",
    "master plan", "feasibility study", "detailed design", "budget allocation",
    "fund allocation", "funding approved", "procurement plan", "tender preparation",
    "ခွင့်ပြုချက်", "အတည်ပြုချက်", "စီမံကိန်းအတည်ပြု",
    "အကောင်အထည်ဖော်ဆောင်ရွက်ရန်", "အကောင်အထည်ဖော်ရန်",
    "မဟာစီမံကိန်း", "ဖြစ်နိုင်ခြေလေ့လာ", "ဒီဇိုင်းရေးဆွဲ",
    "ဘတ်ဂျက်", "ရန်ပုံငွေ", "တင်ဒါပြင်ဆင်",
)
_STARTED_OR_COMPLETED_TOKENS = (
    "under construction", "construction underway", "construction is underway",
    "work is underway", "works are underway", "implementation is underway",
    "groundbreaking", "foundation stone", "opened", "inaugurated", "commissioned",
    "completed", "completion ceremony",
    "တည်ဆောက်နေ", "တည်ဆောက်လျက်ရှိ", "ဆောက်လုပ်နေ", "ဆောက်လုပ်လျက်ရှိ",
    "ပြန်လည်တည်ဆောက်နေ", "ဆောင်ရွက်လျက်ရှိ", "အကောင်အထည်ဖော်လျက်ရှိ",
    "လုပ်ငန်းခွင်", "စတင်အသုံးပြု", "စတင်ဆောင်ရွက်", "အုတ်မြစ်", "ဖွင့်လှစ်", "ပြီးစီး",
)
_OPEN_PROCUREMENT_TOKENS = (
    "open tender", "invitation to tender", "invitation for bid", "invitation to bid",
    "request for proposal", "request for quotation",
    "အိတ်ဖွင့်တင်ဒါ", "အိတ်ဖွင့်တင်ဒါ", "တင်ဒါခေါ်ယူ", "တင်ဒါဖိတ်ခေါ်",
)
_APPROVAL_TOKENS = (
    "approved project", "project approved", "approval granted", "approved for implementation",
    "ခွင့်ပြုချက်", "အတည်ပြုချက်", "စီမံကိန်းအတည်ပြု",
)
_BUDGET_TOKENS = ("budget", "appropriation", "fund allocation", "funding approved", "ဘတ်ဂျက်", "ရန်ပုံငွေ")
_PLANNING_TOKENS = (
    "master plan", "feasibility study", "detailed design", "conceptual design",
    "မဟာစီမံကိန်း", "ဖြစ်နိုင်ခြေလေ့လာ", "ဒီဇိုင်းရေးဆွဲ",
)
_PRE_PROCUREMENT_TOKENS = ("procurement plan", "tender preparation", "တင်ဒါပြင်ဆင်")


class ConstructionProjectPrecursorParseError(ValueError):
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


def _canonical_news_url(raw_url: str) -> tuple[str, str] | None:
    absolute = urljoin(CONSTRUCTION_BASE_URL, raw_url)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() not in CONSTRUCTION_HOSTS:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 80, 443) or parsed.params or parsed.query or parsed.fragment:
        return None
    match = re.fullmatch(
        r"/(?:index\.php/)?new-detail/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
        parsed.path.rstrip("/"),
    )
    if match is None:
        return None
    record_id = match.group(1).lower()
    return record_id, f"{CONSTRUCTION_BASE_URL}/new-detail/{record_id}"


def _listing_datetime(value: str) -> str | None:
    text = normalize_text(value)
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2}\s+20\d{2}",
        text,
        re.I,
    )
    if match is None:
        return None
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            parsed = datetime.strptime(match.group(0), fmt)
        except ValueError:
            continue
        return f"{parsed.date().isoformat()}T00:00:00+06:30"
    return None


def _publication_date(value: str) -> str | None:
    listed_at = _listing_datetime(value)
    return listed_at[:10] if listed_at else None


def _project_marker(value: str) -> bool:
    normalized = normalize_text(value).lower()
    return any(token.lower() in normalized for token in _PROJECT_TOKENS)


def _relevance_categories(value: str) -> list[str]:
    normalized = normalize_text(value).lower()
    return [
        category for category, tokens in _SECTOR_TOKENS.items()
        if any(token.lower() in normalized for token in tokens)
    ]


def _capital_intent_marker(value: str) -> bool:
    normalized = normalize_text(value).lower()
    return any(token.lower() in normalized for token in _CAPITAL_INTENT_TOKENS)


def _has_forward_action(value: str) -> bool:
    normalized = normalize_text(value).lower()
    return any(token.lower() in normalized for token in _FORWARD_ACTION_TOKENS)


def _has_started_or_completed(value: str) -> bool:
    normalized = normalize_text(value).lower()
    return any(token.lower() in normalized for token in _STARTED_OR_COMPLETED_TOKENS)


def _is_open_procurement(value: str) -> bool:
    normalized = normalize_text(value).lower()
    return any(token.lower() in normalized for token in _OPEN_PROCUREMENT_TOKENS)


def _stage_hint(value: str) -> str:
    normalized = normalize_text(value).lower()
    if any(token.lower() in normalized for token in _PRE_PROCUREMENT_TOKENS):
        return "PRE_PROCUREMENT"
    if any(token.lower() in normalized for token in _BUDGET_TOKENS):
        return "BUDGET"
    if any(token.lower() in normalized for token in _PLANNING_TOKENS):
        return "PLANNING_DESIGN"
    if any(token.lower() in normalized for token in _APPROVAL_TOKENS):
        return "APPROVAL"
    return "PROJECT_ANNOUNCEMENT"


def _listing_candidate(title: str) -> bool:
    return (
        bool(_relevance_categories(title))
        and (_project_marker(title) or _capital_intent_marker(title))
        and _has_forward_action(title)
        and not _has_started_or_completed(title)
        and not _is_open_procurement(title)
    )


class _ListingParser(HTMLParser):
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
        if lowered == "a" and "card-title" in classes:
            self._title_depth = 1
            href = _attr(attrs, "href")
            if href:
                self._href = href
            return
        if lowered == "small" and "text-muted" in classes:
            self._date_depth = 1
            return
        if self._title_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
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
        identity = _canonical_news_url(self._href or "")
        listed_at = _listing_datetime(" ".join(self._date_parts))
        if identity is not None and listed_at is not None and _listing_candidate(title):
            _record_id, canonical_url = identity
            self.entries.append(SitemapEntry(canonical_url, listed_at))
        self._reset()


def parse_project_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = _ListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise ConstructionProjectPrecursorParseError("Construction Ministry news card structure not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class ConstructionProjectPrecursor:
    record_id: str
    title: str
    publication_date: str
    scope_summary: str
    relevance_categories: tuple[str, ...]
    precursor_stage_hint: str
    url: str

    item_kind = "REGULATORY_NOTICE"
    deadline = None
    location = "Myanmar"

    @property
    def canonical_key(self) -> str:
        return f"construction-project:{self.record_id}"

    @property
    def reference_no(self) -> str:
        return f"MOC-NEWS-{self.record_id}"

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": CONSTRUCTION_PROJECT_ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "construction_gov_mm_news_uuid",
            "source_record_id": self.record_id,
            "publication_date": self.publication_date,
            "deadline": None,
            "location": self.location,
            "scope_summary": self.scope_summary,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "PROJECT_PRECURSOR_CANDIDATE",
            "precursor_stage_hint": self.precursor_stage_hint,
            "precursor_review_required": True,
            "precursor_selection_basis": "MAIN_PROJECT_TITLE+PRIMARY_PARAGRAPH+PRE_PROCUREMENT_FORWARD_ACTION-NOT_STARTED-NOT_OPEN_PROCUREMENT",
            "relevance_categories": list(self.relevance_categories),
            "detail_completeness": "OFFICIAL_CONSTRUCTION_NEWS_TITLE_DATE_PRIMARY_BODY",
            "url": self.url,
        }


class _DetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root_found = False
        self._root_depth = 0
        self._title_depth = 0
        self._body_depth = 0
        self._date_depth = 0
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.date_parts: list[str] = []
        self.paragraphs: list[str] = []
        self._paragraph_stack: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "div":
            if self._root_depth:
                self._root_depth += 1
            elif "summernote_content" in classes:
                self.root_found = True
                self._root_depth = 1
                return
        if not self._root_depth:
            return
        if lowered == "h5" and "head-3" in classes:
            self._title_depth = 1
            return
        if lowered == "div" and {"row", "mt-2"}.issubset(classes) and self._body_depth == 0:
            self._body_depth = 1
            return
        if lowered == "small" and {"text-primary", "float-end"}.issubset(classes):
            self._date_depth = 1
            return
        if lowered == "p" and self._body_depth:
            self._paragraph_stack.append([])
        if self._title_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._title_depth += 1
        if self._body_depth and lowered == "div":
            self._body_depth += 1
        if self._date_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._date_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._root_depth:
            return
        if self._title_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._title_depth -= 1
        if self._date_depth and lowered not in {"br", "img", "input", "meta", "link", "hr"}:
            self._date_depth -= 1
        if lowered == "p" and self._paragraph_stack:
            parts = self._paragraph_stack.pop()
            paragraph = normalize_text(" ".join(parts))
            if paragraph:
                self.paragraphs.append(paragraph)
        if lowered == "div":
            if self._body_depth:
                self._body_depth -= 1
            self._root_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._root_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._body_depth:
            self.body_parts.append(value)
            if self._paragraph_stack:
                self._paragraph_stack[-1].append(value)
        if self._date_depth:
            self.date_parts.append(value)


def parse_project_detail(html_bytes: bytes, url: str) -> ConstructionProjectPrecursor | None:
    identity = _canonical_news_url(url)
    if identity is None:
        raise ConstructionProjectPrecursorParseError("invalid Construction Ministry project detail URL")
    record_id, canonical_url = identity

    parser = _DetailParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    body = normalize_text(" ".join(parser.body_parts))
    publication_date = _publication_date(" ".join(parser.date_parts))
    if not parser.root_found or not title or not body or publication_date is None:
        raise ConstructionProjectPrecursorParseError("Construction Ministry project detail structure not found")

    primary_paragraph = next(
        (
            paragraph
            for paragraph in parser.paragraphs
            if _project_marker(paragraph)
            or _capital_intent_marker(paragraph)
            or _has_forward_action(paragraph)
        ),
        body[:600],
    )
    primary_scope = normalize_text(f"{title} {primary_paragraph}")
    categories = _relevance_categories(primary_scope)
    if (
        not categories
        or not (_project_marker(title) or _capital_intent_marker(title))
        or not _has_forward_action(primary_scope)
        or _has_started_or_completed(primary_scope)
        or _is_open_procurement(primary_scope)
    ):
        return None

    return ConstructionProjectPrecursor(
        record_id=record_id,
        title=title,
        publication_date=publication_date,
        scope_summary=body[:1200],
        relevance_categories=tuple(categories),
        precursor_stage_hint=_stage_hint(primary_scope),
        url=canonical_url,
    )
