from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from .mpt import normalize_text

MTE_ANNOUNCEMENTS_URL = "https://mte.gov.mm/index.php/en/annoucements"
MTE_ISSUER = "Myanma Timber Enterprise"
MTE_HOSTS = {"mte.gov.mm", "www.mte.gov.mm"}
SELECTION_POLICY_VERSION = 1

_STRONG_PROCUREMENT_TOKENS = (
    "ဝန်ဆောင်မှုရယူရန်",
    "ဝယ္ယူလို",  # legacy encoding variants occasionally appear in old content
    "ဝယ်ယူလို",
    "ပေးသွင်းရန်ဖိတ်ခေါ်",
    "ပေးသွင်းရန် ဖိတ်ခေါ်",
    "purchase",
    "procure",
    "supply invitation",
)
_EXCLUDE_SALE_TOKENS = (
    "ရောင်းချ",
    "လေလံ",
    " sale ",
    " sales ",
    "auction",
)


class MteParseError(ValueError):
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


def _canonical_article_url(raw_url: str, page_url: str = MTE_ANNOUNCEMENTS_URL) -> tuple[str, str] | None:
    url = urljoin(page_url, raw_url)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in MTE_HOSTS:
        return None
    path = unquote(parsed.path)
    match = re.search(r"/(?:annoucements|announcements-mm)/(\d+)(?:-|$)", path, flags=re.I)
    if match is None:
        return None
    article_id = match.group(1)
    encoded_path = quote(path, safe="/%^()_-.")
    canonical = urlunsplit(("https", "mte.gov.mm", encoded_path, "", ""))
    return article_id, canonical


def is_procurement_event(text: str) -> bool:
    value = f" {normalize_text(text)} "
    lower = value.lower()
    if not normalize_text(text):
        return False
    if any(token.lower() in lower for token in _EXCLUDE_SALE_TOKENS):
        return False
    if "ဝန်ဆောင်မှုရယူရန်" in value:
        return True
    if "ဝယ်ယူလို" in value or "ဝယ္ယူလို" in value:
        return "ပေးသွင်းရန်" in value or "ဖိတ်ခေါ်" in value
    return any(token.lower() in lower for token in _STRONG_PROCUREMENT_TOKENS[-3:]) and "tender" in lower


def _extract_reference_no(paragraphs: tuple[str, ...]) -> str | None:
    for paragraph in paragraphs:
        text = normalize_text(paragraph)
        if "တင်ဒါ" not in text or "အမှတ်" not in text:
            continue
        match = re.search(r"အမှတ်\s*\(?\s*([^()]{2,40}?)\s*\)?$", text)
        if match:
            value = normalize_text(match.group(1))
            if value:
                return value
    return None


def _best_title(paragraphs: tuple[str, ...], fallback: str) -> str:
    candidates = [normalize_text(p) for p in paragraphs if normalize_text(p)]
    for value in candidates:
        if "ဝန်ဆောင်မှုရယူရန်" in value:
            return value
    for value in candidates:
        if "ဝယ်ယူလို" in value or "ဝယ္ယူလို" in value:
            return value
    return normalize_text(fallback)


@dataclass(frozen=True)
class MteTender:
    article_id: str
    title: str
    reference_no_value: str | None
    scope_summary: str
    url: str

    item_kind = "TENDER"
    publication_date = None
    deadline = None
    location = None

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def reference_no(self) -> str:
        return self.reference_no_value or f"MTE-ARTICLE-{self.article_id}"

    @property
    def canonical_key(self) -> str:
        return f"mte:{self.article_id}"

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": MTE_ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_visible_tender_no" if self.reference_no_value else "joomla_article_id_fallback",
            "source_record_id": self.article_id,
            "publication_date": None,
            "publication_date_evidence": "UNKNOWN_NOT_EXPOSED_IN_ARCHIVE_HTML",
            "deadline": None,
            "deadline_evidence": "UNKNOWN_IN_IMAGE_SUPPLEMENT_NOT_PARSED",
            "scope_summary": self.scope_summary,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "HTML_EVENT_SCOPE_REFERENCE_IMAGE_SUPPLEMENT_UNPARSED",
            "supplementary_image_policy": "UNFETCHED_NON_BLOCKING",
            "url": self.url,
        }


@dataclass(frozen=True)
class _ArchiveCard:
    paragraphs: tuple[str, ...]
    text: str
    href: str


class MteAnnouncementsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[_ArchiveCard] = []
        self.item_count = 0
        self._item_depth = 0
        self._paragraph_depth = 0
        self._paragraph_parts: list[str] = []
        self._paragraphs: list[str] = []
        self._all_parts: list[str] = []
        self._href: str | None = None

    def _reset_item(self) -> None:
        self._paragraph_depth = 0
        self._paragraph_parts = []
        self._paragraphs = []
        self._all_parts = []
        self._href = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "div":
            if self._item_depth:
                self._item_depth += 1
            elif "item" in classes and "column-1" in classes:
                self._item_depth = 1
                self.item_count += 1
                self._reset_item()
                return
        if not self._item_depth:
            return
        if lowered == "p":
            self._paragraph_depth = 1
            self._paragraph_parts = []
            return
        if self._paragraph_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._paragraph_depth += 1
        if lowered == "a" and "readmore-link" in classes:
            href = _attr(attrs, "href")
            if href:
                self._href = href

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._item_depth:
            return
        if self._paragraph_depth and lowered in {"p", "span", "strong", "em", "a"}:
            self._paragraph_depth -= 1
            if lowered == "p" and self._paragraph_depth == 0:
                value = normalize_text(" ".join(self._paragraph_parts))
                if value:
                    self._paragraphs.append(value)
                self._paragraph_parts = []
        if lowered == "div":
            self._item_depth -= 1
            if self._item_depth == 0:
                text = normalize_text(" ".join(self._all_parts))
                if text and self._href:
                    self.cards.append(_ArchiveCard(tuple(self._paragraphs), text, self._href))
                self._reset_item()

    def handle_data(self, data: str) -> None:
        if not self._item_depth:
            return
        value = normalize_text(data)
        if not value or value.lower() in {"read more...", "အပြည့်အစုံသို့..."}:
            return
        self._all_parts.append(value)
        if self._paragraph_depth:
            self._paragraph_parts.append(value)


def parse_tender_records(html_bytes: bytes, page_url: str = MTE_ANNOUNCEMENTS_URL) -> list[MteTender]:
    parser = MteAnnouncementsParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.item_count == 0:
        raise MteParseError("MTE announcement archive structure not found")

    selected: list[MteTender] = []
    seen: set[str] = set()
    for card in parser.cards:
        if not is_procurement_event(card.text):
            continue
        identity = _canonical_article_url(card.href, page_url)
        if identity is None:
            continue
        article_id, canonical_url = identity
        if article_id in seen:
            continue
        seen.add(article_id)
        title = _best_title(card.paragraphs, card.text)
        selected.append(
            MteTender(
                article_id=article_id,
                title=title,
                reference_no_value=_extract_reference_no(card.paragraphs),
                scope_summary=card.text[:2000],
                url=canonical_url,
            )
        )
    return selected
