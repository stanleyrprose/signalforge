from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .mpt import SitemapEntry, normalize_text

MOEE_BASE_URL = "https://moep.gov.mm"
MOEE_NEWS_LIST_URL = f"{MOEE_BASE_URL}/mm/ignite/page/12"
MOEE_PROJECT_ISSUER = "Ministry of Electricity and Energy, Myanmar"
MOEE_HOSTS = {"moep.gov.mm", "www.moep.gov.mm"}
SELECTION_POLICY_VERSION = 1

_ASSET_TOKENS = (
    "power plant", "power station", "substation", "transmission line", "distribution line",
    "switchbay", "switch bay", "grid", "solar plant", "hydropower plant", "transformer station",
    "ဓာတ်အားပေးစက်ရုံ", "ဓာတ်အားခွဲရုံ", "ဓာတ်အားလိုင်း", "မဟာဓာတ်အားလိုင်း",
    "ဓာတ်အားပို့လွှတ်ရေးလိုင်း", "ဓာတ်အားဖြန့်ဖြူးရေးလိုင်း", "ဓာတ်အားဖြန့်ဖြူးရေးလိုင်း",
)
_FUTURE_ACTION_TOKENS = (
    "to construct", "will construct", "will be constructed", "planned construction",
    "to build", "will build", "will be built", "to upgrade", "will upgrade",
    "to expand", "will expand", "planned expansion", "planned upgrade",
    "approved project", "project approved", "approval granted",
    "feasibility study", "detailed design", "master plan",
    "budget allocation", "fund allocation", "funding approved", "loan approved",
    "procurement plan", "tender preparation",
    "တည်ဆောက်မည်", "တည်ဆောက်မည့်", "တည်ဆောက်မည့်", "တည်ဆောက်ရန်",
    "ဆောက်လုပ်မည်", "ဆောက်လုပ်မည့်", "ဆောက်လုပ်မည့်", "ဆောက်လုပ်ရန်",
    "တိုးချဲ့မည်", "တိုးချဲ့မည့်", "တိုးချဲ့မည့်", "တိုးချဲ့ရန်",
    "အဆင့်မြှင့်မည်", "အဆင့်မြှင့်မည်", "အဆင့်မြှင့်ရန်", "အဆင့်မြှင့်ရန်",
    "အကောင်အထည်ဖော်ရန်", "အကောင်အထည်ဖော်မည်", "လျာထား",
    "ခွင့်ပြုချက်", "ခွင့်ပြုချက်", "အတည်ပြုချက်",
    "ဖြစ်နိုင်ခြေလေ့လာ", "ဒီဇိုင်းရေးဆွဲ", "မဟာစီမံကိန်း",
    "ဘတ်ဂျက်ခွဲဝေ", "ရန်ပုံငွေ", "ချေးငွေ",
    "တင်ဒါပြင်ဆင်",
)
_STARTED_OR_COMPLETED_TOKENS = (
    "under construction", "construction underway", "construction is underway",
    "work is underway", "works are underway", "operating", "in operation",
    "test operation", "trial operation", "commissioned", "completed",
    "opened", "inaugurated", "groundbreaking", "foundation stone",
    "တည်ဆောက်နေ", "တည်ဆောက်လျက်ရှိ", "တည်ဆောက်လျှက်ရှိ",
    "တိုးချဲ့တည်ဆောက်လျက်ရှိ", "တိုးချဲ့တည်ဆောက်လျှက်ရှိ",
    "ဆောက်လုပ်နေ", "ဆောင်ရွက်လျက်ရှိ", "ဆောင်ရွက်လျှက်ရှိ",
    "လုပ်ငန်းခွင်", "ပြီးစီး", "ဖွင့်လှစ်", "ဖွင့်လှစ်",
    "လည်ပတ်နေ", "စမ်းသပ်လည်ပတ်",
)
_OPEN_PROCUREMENT_TOKENS = (
    "open tender", "invitation to tender", "invitation for bid", "invitation to bid",
    "request for proposal", "request for quotation",
    "အိတ်ဖွင့်တင်ဒါ", "အိတ်ဖွင့်တင်ဒါ", "တင်ဒါခေါ်ယူ", "တင်ဒါဖိတ်ခေါ်",
)
_APPROVAL_TOKENS = (
    "approved project", "project approved", "approval granted",
    "ခွင့်ပြုချက်", "ခွင့်ပြုချက်", "အတည်ပြုချက်",
)
_BUDGET_FINANCE_TOKENS = (
    "budget allocation", "fund allocation", "funding approved", "loan approved",
    "ဘတ်ဂျက်ခွဲဝေ", "ရန်ပုံငွေ", "ချေးငွေ",
)
_PLANNING_TOKENS = (
    "feasibility study", "detailed design", "master plan",
    "ဖြစ်နိုင်ခြေလေ့လာ", "ဒီဇိုင်းရေးဆွဲ", "မဟာစီမံကိန်း",
)
_PRE_PROCUREMENT_TOKENS = ("procurement plan", "tender preparation", "တင်ဒါပြင်ဆင်")


class MoeeProjectPrecursorParseError(ValueError):
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


def _canonical_content_url(raw_url: str) -> tuple[str, str] | None:
    absolute = urljoin(f"{MOEE_BASE_URL}/mm/", raw_url)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() not in MOEE_HOSTS:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 80, 443) or parsed.params or parsed.query or parsed.fragment:
        return None
    match = re.fullmatch(r"/mm/ignite/contentView/(\d+)", parsed.path.rstrip("/"))
    if match is None:
        return None
    content_id = match.group(1)
    return content_id, f"{MOEE_BASE_URL}/mm/ignite/contentView/{content_id}"


def _listing_datetime(value: str) -> str | None:
    text = normalize_text(value)
    match = re.search(r"\b(\d{1,2})-([A-Za-z]{3})-(20\d{2})\b", text)
    if match is None:
        return None
    try:
        parsed = datetime.strptime(match.group(0), "%d-%b-%Y")
    except ValueError:
        return None
    return f"{parsed.date().isoformat()}T00:00:00+06:30"


def _publication_date(html_text: str) -> str | None:
    match = re.search(
        r"Post\s+under\s+by\s*:.*?(\d{1,2}-[A-Za-z]{3}-20\d{2})",
        html_text,
        re.I | re.S,
    )
    if match is None:
        match = re.search(r"\b\d{1,2}-[A-Za-z]{3}-20\d{2}\b", html_text)
    if match is None:
        return None
    listed_at = _listing_datetime(match.group(1) if match.lastindex else match.group(0))
    return listed_at[:10] if listed_at else None


def _contains(value: str, tokens: tuple[str, ...]) -> bool:
    normalized = normalize_text(value).lower()
    return any(token.lower() in normalized for token in tokens)


def _asset_marker(value: str) -> bool:
    return _contains(value, _ASSET_TOKENS)


def _future_marker(value: str) -> bool:
    return _contains(value, _FUTURE_ACTION_TOKENS)


def _late_marker(value: str) -> bool:
    return _contains(value, _STARTED_OR_COMPLETED_TOKENS)


def _open_procurement(value: str) -> bool:
    return _contains(value, _OPEN_PROCUREMENT_TOKENS)


def _stage_hint(value: str) -> str:
    if _contains(value, _PRE_PROCUREMENT_TOKENS):
        return "PRE_PROCUREMENT"
    if _contains(value, _BUDGET_FINANCE_TOKENS):
        return "BUDGET_FINANCE"
    if _contains(value, _PLANNING_TOKENS):
        return "PLANNING_DESIGN"
    if _contains(value, _APPROVAL_TOKENS):
        return "APPROVAL"
    return "PROJECT_ANNOUNCEMENT"


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
            elif "content-data-list" in classes:
                self._card_depth = 1
                self.card_count += 1
                self._reset()
                return
        if not self._card_depth:
            return
        if lowered == "strong" and "text-primary" in classes:
            self._title_depth = 1
            return
        if lowered == "a":
            href = _attr(attrs, "href")
            if href and "contentView/" in href:
                self._href = href
        if lowered == "div" and {"text-right", "small-height"}.issubset(classes):
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
        identity = _canonical_content_url(self._href or "")
        listed_at = _listing_datetime(" ".join(self._date_parts))
        if title and identity is not None and listed_at is not None:
            _content_id, canonical_url = identity
            self.entries.append(SitemapEntry(canonical_url, listed_at))
        self._reset()


def parse_project_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = _ListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise MoeeProjectPrecursorParseError("MOEE latest-news card structure not found")
    dedup: dict[str, SitemapEntry] = {}
    for entry in parser.entries:
        dedup.setdefault(entry.url, entry)
    return list(dedup.values())


class _DetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.article_title: str | None = None
        self.body_found = False
        self.body_complete = False
        self._body_depth = 0
        self._paragraph_depth = 0
        self._paragraph_parts: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        if lowered == "meta":
            properties = {str(key): str(value) for key, value in attrs if key and value is not None}
            if properties.get("property") == "og:title":
                content = normalize_text(properties.get("content") or "")
                if content:
                    self.article_title = content
            return
        classes = _classes(attrs)
        if lowered == "div":
            if self._body_depth:
                self._body_depth += 1
            elif not self.body_found and not self.body_complete and "mid-margin" in classes:
                self.body_found = True
                self._body_depth = 1
                return
        if not self._body_depth:
            return
        if lowered == "p":
            self._paragraph_depth += 1
            if self._paragraph_depth == 1:
                self._paragraph_parts = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._body_depth:
            return
        if lowered == "p" and self._paragraph_depth:
            self._paragraph_depth -= 1
            if self._paragraph_depth == 0:
                paragraph = normalize_text(" ".join(self._paragraph_parts))
                if paragraph:
                    self.paragraphs.append(paragraph)
                self._paragraph_parts = []
        if lowered == "div":
            self._body_depth -= 1
            if self._body_depth == 0:
                self.body_complete = True

    def handle_data(self, data: str) -> None:
        if not self._body_depth or not self._paragraph_depth:
            return
        value = normalize_text(data)
        if value:
            self._paragraph_parts.append(value)


def _coarse_chunks(paragraph: str) -> list[str]:
    return [
        normalize_text(value)
        for value in re.split(r"[။၊;]+", paragraph)
        if normalize_text(value)
    ]


def _fine_chunks(value: str) -> list[str]:
    return [
        normalize_text(part)
        for part in re.split(r"(?:နှင့်|နှင့်)", value)
        if normalize_text(part)
    ]


def _candidate_clauses(paragraphs: list[str]) -> list[str]:
    accepted: list[str] = []
    seen: set[str] = set()
    for paragraph in paragraphs:
        for coarse in _coarse_chunks(paragraph):
            if not (_asset_marker(coarse) and _future_marker(coarse)):
                continue
            candidates = [coarse]
            if _late_marker(coarse) or _open_procurement(coarse):
                candidates = _fine_chunks(coarse)
            for candidate in candidates:
                if (
                    not _asset_marker(candidate)
                    or not _future_marker(candidate)
                    or _late_marker(candidate)
                    or _open_procurement(candidate)
                ):
                    continue
                normalized = normalize_text(candidate)
                if normalized not in seen:
                    seen.add(normalized)
                    accepted.append(normalized)
    return accepted


@dataclass(frozen=True)
class MoeeProjectPrecursor:
    content_id: str
    candidate_hash: str
    article_title: str
    project_name: str
    publication_date: str
    scope_summary: str
    precursor_stage_hint: str
    url: str

    item_kind = "REGULATORY_NOTICE"
    deadline = None
    location = "Myanmar"
    relevance_categories = ("ENERGY",)

    @property
    def canonical_key(self) -> str:
        return f"moee-project:{self.content_id}:{self.candidate_hash}"

    @property
    def reference_no(self) -> str:
        return f"MOEE-NEWS-{self.content_id}-{self.candidate_hash[:8]}"

    @property
    def title(self) -> str:
        return self.project_name

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": MOEE_PROJECT_ISSUER,
            "title": self.title,
            "article_title": self.article_title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "moee_content_id_plus_candidate_hash",
            "source_record_id": self.content_id,
            "candidate_hash": self.candidate_hash,
            "publication_date": self.publication_date,
            "deadline": None,
            "location": self.location,
            "scope_summary": self.scope_summary,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "PROJECT_PRECURSOR_CANDIDATE",
            "precursor_stage_hint": self.precursor_stage_hint,
            "precursor_review_required": True,
            "precursor_selection_basis": "ARTICLE_BODY_PROJECT_CLAUSE+NAMED_ENERGY_ASSET+FUTURE_ACTION-NOT_STARTED-NOT_OPEN_PROCUREMENT",
            "relevance_categories": list(self.relevance_categories),
            "detail_completeness": "OFFICIAL_MOEE_NEWS_TITLE_DATE_BODY_PROJECT_CLAUSE",
            "url": self.url,
        }


def parse_project_detail(html_bytes: bytes, url: str) -> list[MoeeProjectPrecursor]:
    identity = _canonical_content_url(url)
    if identity is None:
        raise MoeeProjectPrecursorParseError("invalid MOEE project detail URL")
    content_id, canonical_url = identity

    html_text = html_bytes.decode("utf-8", errors="replace")
    parser = _DetailParser()
    parser.feed(html_text)
    publication_date = _publication_date(html_text)
    if (
        parser.article_title is None
        or not parser.body_found
        or not parser.body_complete
        or not parser.paragraphs
        or publication_date is None
    ):
        raise MoeeProjectPrecursorParseError("MOEE project detail structure not found")

    results: list[MoeeProjectPrecursor] = []
    for clause in _candidate_clauses(parser.paragraphs):
        digest = hashlib.sha256(clause.encode("utf-8")).hexdigest()[:12]
        results.append(
            MoeeProjectPrecursor(
                content_id=content_id,
                candidate_hash=digest,
                article_title=parser.article_title,
                project_name=clause[:500],
                publication_date=publication_date,
                scope_summary=clause[:1200],
                precursor_stage_hint=_stage_hint(clause),
                url=canonical_url,
            )
        )
    return results
