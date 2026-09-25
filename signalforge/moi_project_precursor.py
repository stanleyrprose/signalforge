from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .mpt import SitemapEntry, normalize_text

MOI_BASE_URL = "https://www.moi.gov.mm"
MOI_PROJECT_LIST_URL = f"{MOI_BASE_URL}/news"
MOI_PROJECT_ISSUER = "Ministry of Information, Myanmar"
MOI_HOSTS = {"moi.gov.mm", "www.moi.gov.mm"}
SELECTION_POLICY_VERSION = 1

_PROJECT_TOKENS = ("စီမံကိန်း", "project")
_SECTOR_TOKENS: dict[str, tuple[str, ...]] = {
    "CONSTRUCTION": (
        "construction", "infrastructure", "road", "bridge", "building", "city development",
        "ဆောက်လုပ်", "လမ်း", "တံတား", "အဆောက်အအုံ", "မြို့ပြ",
    ),
    "TELECOM": (
        "telecom", "telecommunication", "ict", "digital", "fiber", "fibre", "network",
        "cyber city", "5g", "ဆက်သွယ်ရေး", "ဒီဂျစ်တယ်", "ကွန်ရက်", "ဆိုက်ဘာစီးတီး",
    ),
    "ENERGY": (
        "energy", "power", "electric", "electricity", "solar", "hydropower", "grid", "substation",
        "စွမ်းအင်", "လျှပ်စစ်", "ဓာတ်အား",
    ),
    "ENGINEERING": (
        "engineering", "industrial zone", "water supply", "wastewater",
        "အင်ဂျင်နီယာ", "စက်မှုဇုန်", "ရေပေးဝေ", "ရေဆိုး",
    ),
}
_FORWARD_ACTION_TOKENS = (
    "implementation", "implement", "will continue", "continue implementation", "to construct",
    "will construct", "to upgrade", "will upgrade", "to expand", "will expand", "approved",
    "approval", "master plan", "conceptual plan", "budget allocation", "procurement plan",
    "အကောင်အထည်ဖော်", "ဆက်လက်ဆောင်ရွက်", "ဆက်လက် အကောင်အထည်ဖော်", "တည်ဆောက်မည်",
    "အဆင့်မြှင့်", "တိုးချဲ့", "ခွင့်ပြု", "မဟာစီမံကိန်း", "ဘတ်ဂျက်",
)
_OPEN_PROCUREMENT_TOKENS = (
    "open tender", "invitation to tender", "invitation for bid", "invitation to bid",
    "request for proposal", "အိတ်ဖွင့်တင်ဒါ", "အိတ်ဖွင့်တင်ဒါ", "တင်ဒါခေါ်ယူ",
)
_BUDGET_TOKENS = ("budget", "appropriation", "fund allocation", "ဘတ်ဂျက်", "ရန်ပုံငွေ")
_PRE_PROCUREMENT_TOKENS = ("procurement plan", "tender preparation", "bid preparation", "တင်ဒါပြင်ဆင်")


class MoiProjectPrecursorParseError(ValueError):
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
    absolute = urljoin(MOI_BASE_URL, raw_url)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() not in MOI_HOSTS:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 80, 443) or parsed.params or parsed.query or parsed.fragment:
        return None
    match = re.fullmatch(r"/(?:index\.php/)?news/(\d+)", parsed.path.rstrip("/"))
    if match is None:
        return None
    node_id = match.group(1)
    return node_id, f"{MOI_BASE_URL}/news/{node_id}"


def _listing_datetime(value: str) -> str | None:
    text = normalize_text(value)
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2},\s+20\d{2}",
        text,
        re.I,
    )
    if match is None:
        return None
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            parsed = datetime.strptime(match.group(0), fmt)
        except ValueError:
            continue
        return f"{parsed.date().isoformat()}T00:00:00+06:30"
    return None


def _publication_date(value: str) -> str | None:
    text = normalize_text(value)
    match = re.search(
        r"(?:\d{1,2}/\d{1,2}/20\d{2}|"
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2},\s+20\d{2})",
        text,
        re.I,
    )
    candidates = [match.group(0)] if match else []
    candidates.append(text)
    for candidate in candidates:
        for fmt in ("%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(candidate, fmt).date().isoformat()
            except ValueError:
                continue
    return None


def _project_marker(value: str) -> bool:
    normalized = normalize_text(value).lower()
    return any(token.lower() in normalized for token in _PROJECT_TOKENS)


def _relevance_categories(value: str) -> list[str]:
    normalized = normalize_text(value).lower()
    return [
        category for category, tokens in _SECTOR_TOKENS.items()
        if any(token.lower() in normalized for token in tokens)
    ]


def _has_forward_action(value: str) -> bool:
    normalized = normalize_text(value).lower()
    return any(token.lower() in normalized for token in _FORWARD_ACTION_TOKENS)


def _is_open_procurement(value: str) -> bool:
    normalized = normalize_text(value).lower()
    return any(token.lower() in normalized for token in _OPEN_PROCUREMENT_TOKENS)


def _stage_hint(value: str) -> str:
    normalized = normalize_text(value).lower()
    if any(token.lower() in normalized for token in _PRE_PROCUREMENT_TOKENS):
        return "PRE_PROCUREMENT"
    if any(token.lower() in normalized for token in _BUDGET_TOKENS):
        return "BUDGET"
    return "PROJECT_ANNOUNCEMENT"


def _listing_candidate(title: str) -> bool:
    return _project_marker(title) and bool(_relevance_categories(title)) and not _is_open_procurement(title)


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
        identity = _canonical_news_url(self._href or "")
        listed_at = _listing_datetime(" ".join(self._date_parts))
        if identity is not None and listed_at is not None and _listing_candidate(title):
            _node_id, canonical_url = identity
            self.entries.append(SitemapEntry(canonical_url, listed_at))
        self._reset()


def parse_project_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = _ListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise MoiProjectPrecursorParseError("MOI news card structure not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


@dataclass(frozen=True)
class MoiProjectPrecursor:
    node_id: str
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
        return f"moi-project:{self.node_id}"

    @property
    def reference_no(self) -> str:
        return f"MOI-NEWS-{self.node_id}"

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": MOI_PROJECT_ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "drupal_news_node_id",
            "source_record_id": self.node_id,
            "publication_date": self.publication_date,
            "deadline": None,
            "location": self.location,
            "scope_summary": self.scope_summary,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "PROJECT_PRECURSOR_CANDIDATE",
            "precursor_stage_hint": self.precursor_stage_hint,
            "precursor_review_required": True,
            "precursor_selection_basis": "PROJECT_MARKER+TARGET_SECTOR+FORWARD_ACTION",
            "relevance_categories": list(self.relevance_categories),
            "detail_completeness": "OFFICIAL_NEWS_TITLE_DATE_BODY",
            "url": self.url,
        }


class _DetailParser(HTMLParser):
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
            elif "node--type-news" in classes:
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


def parse_project_detail(html_bytes: bytes, page_url: str) -> MoiProjectPrecursor | None:
    identity = _canonical_news_url(page_url)
    if identity is None:
        return None
    expected_node_id, canonical_url = identity
    parser = _DetailParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    title = normalize_text(" ".join(parser.title_parts))
    body = normalize_text(" ".join(parser.body_parts))
    publication_date = _publication_date(" ".join(parser.date_parts))
    combined = normalize_text(f"{title} {body}")
    categories = _relevance_categories(combined)
    if (
        parser.node_id != expected_node_id
        or not title
        or not body
        or publication_date is None
        or not _project_marker(combined)
        or not categories
        or not _has_forward_action(combined)
        or _is_open_procurement(combined)
    ):
        return None
    return MoiProjectPrecursor(
        node_id=expected_node_id,
        title=title,
        publication_date=publication_date,
        scope_summary=body[:4000],
        relevance_categories=tuple(categories),
        precursor_stage_hint=_stage_hint(combined),
        url=canonical_url,
    )
