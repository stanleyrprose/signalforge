from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from .mpt import normalize_text, parse_date

DOA_ANNOUNCEMENTS_URL = "https://www.doa.gov.mm/doa/index.php?route=cms/category&path=22"
DOA_ISSUER = "Department of Agriculture, Ministry of Agriculture, Livestock and Irrigation, Myanmar"
DOA_HOSTS = {"doa.gov.mm", "www.doa.gov.mm"}
SELECTION_POLICY_VERSION = 1

_INCLUDE_TOKENS = (
    "ဝယ်ယူ",
    "တည်ဆောက်",
    "ဆောက်လုပ်",
    "ပြင်ဆင်",
    "ဝန်ဆောင်မှု",
    "ပစ္စည်း",
    "လုပ်ငန်းအတွက်",
)
_EXCLUDE_TOKENS = (
    "တင်ဒါအောင်",
    "အောင်စာရင်း",
    "ရောင်း",
    "လေလံ",
    "ငှား",
    "award",
    "result",
    "winner",
)
_VOID_TAGS = {"br", "img", "input", "meta", "link", "hr", "source", "area", "base", "embed", "param", "track", "wbr"}


class DoaParseError(ValueError):
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


def _canonical_article_url(raw_url: str, page_url: str = DOA_ANNOUNCEMENTS_URL) -> tuple[str, str] | None:
    absolute = urljoin(page_url, raw_url)
    parsed = urlsplit(absolute)
    if parsed.scheme != "https" or parsed.hostname not in DOA_HOSTS or parsed.username or parsed.password:
        return None
    if parsed.port not in (None, 443) or parsed.path != "/doa/index.php" or parsed.fragment:
        return None
    query = parse_qs(parsed.query, keep_blank_values=True)
    if query.get("route") != ["cms/article"] or query.get("path") != ["22"]:
        return None
    article_ids = query.get("article_id")
    if not article_ids or len(article_ids) != 1 or not article_ids[0].isdigit():
        return None
    article_id = article_ids[0]
    return article_id, f"https://www.doa.gov.mm/doa/index.php?route=cms/article&path=22&article_id={article_id}"


def _clean_title(value: str) -> str:
    return normalize_text(value).strip('\"“”')


def is_procurement_event(title: str) -> bool:
    text = normalize_text(title)
    lower = text.lower()
    if not text or "တင်ဒါ" not in text:
        return False
    if any(token.lower() in lower for token in _EXCLUDE_TOKENS):
        return False
    return any(token in text for token in _INCLUDE_TOKENS)


@dataclass(frozen=True)
class DoaTender:
    article_id: str
    title: str
    publication_date: str
    url: str

    item_kind = "TENDER"
    deadline = None
    location = None

    @property
    def canonical_key(self) -> str:
        return f"doa:{self.article_id}"

    @property
    def reference_no(self) -> str:
        return f"DOA-ARTICLE-{self.article_id}"

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": DOA_ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_article_id",
            "source_record_id": self.article_id,
            "publication_date": self.publication_date,
            "publication_date_evidence": "LISTING_VISIBLE_ARTICLE_DATE",
            "deadline": None,
            "deadline_evidence": "UNKNOWN_IN_IMAGE_SUPPLEMENT_NOT_PARSED",
            "location": None,
            "scope_summary": self.title,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "LISTING_TITLE_BUSINESS_SCOPE_IMAGE_SUPPLEMENT_UNPARSED",
            "supplementary_image_policy": "UNFETCHED_NON_BLOCKING",
            "url": self.url,
        }


@dataclass(frozen=True)
class _ArticleCard:
    title: str
    date_text: str
    href: str


class DoaAnnouncementParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[_ArticleCard] = []
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
            elif {"article-layout", "article-list"}.issubset(classes):
                self._card_depth = 1
                self.card_count += 1
                self._reset()
                return
        if not self._card_depth:
            return
        if lowered == "span" and "article-date" in classes and self._date_depth == 0:
            self._date_depth = 1
            self._date_parts = []
            return
        if lowered == "div" and "article-title" in classes and self._title_depth == 0:
            self._title_depth = 1
            self._title_parts = []
            return
        if self._title_depth:
            if lowered == "a":
                href = _attr(attrs, "href")
                if href:
                    self._href = href
            if lowered not in _VOID_TAGS:
                self._title_depth += 1
        if self._date_depth and lowered not in _VOID_TAGS:
            self._date_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._card_depth:
            return
        if self._title_depth and lowered not in _VOID_TAGS:
            self._title_depth -= 1
        if self._date_depth and lowered not in _VOID_TAGS:
            self._date_depth -= 1
        if lowered == "div":
            self._card_depth -= 1
            if self._card_depth == 0:
                title = _clean_title(" ".join(self._title_parts))
                date_text = normalize_text(" ".join(self._date_parts))
                if title and date_text and self._href:
                    self.cards.append(_ArticleCard(title, date_text, self._href))
                self._reset()

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


def parse_tender_records(html_bytes: bytes, page_url: str = DOA_ANNOUNCEMENTS_URL) -> list[DoaTender]:
    parser = DoaAnnouncementParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise DoaParseError("DOA announcement listing structure not found")

    selected: list[DoaTender] = []
    seen: set[str] = set()
    for card in parser.cards:
        if not is_procurement_event(card.title):
            continue
        identity = _canonical_article_url(card.href, page_url)
        publication_date = parse_date(card.date_text)
        if identity is None or publication_date is None:
            continue
        article_id, canonical_url = identity
        if article_id in seen:
            continue
        seen.add(article_id)
        selected.append(
            DoaTender(
                article_id=article_id,
                title=card.title,
                publication_date=publication_date,
                url=canonical_url,
            )
        )
    return selected
