from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlparse, urlsplit, urlunsplit

from .mpt import normalize_text

MOEA_LIST_URL = "https://portal.moea.gov.mm/index.php?page=ORwuBwpT"
MOEA_ISSUER = "Ministry of Ethnic Affairs, Myanmar"
MOEA_HOSTS = {"portal.moea.gov.mm", "moea.gov.mm", "www.moea.gov.mm"}
SELECTION_POLICY_VERSION = 1

_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_INCLUDE_TOKENS = (
    "တင်ဒါခေါ်ယူ",
    "တင်ဒါခါ်ယူ",
    "အိတ်ဖွင့်တင်ဒါ",
    "အိတ်ဖွင့်တင်ဒါ",
    "tender invitation",
    "invitation to tender",
    "open tender",
)
_EXCLUDE_STAGE_TOKENS = (
    "တင်ဒါအောင်",
    "အောင်မြင်",
    "ရွေးချယ်",
    "tender award",
    "awarded",
    "result",
)
_EXCLUDE_NON_PROCUREMENT_TOKENS = (
    "ငှားရမ်း",
    "လေလံ",
    "lease",
    "auction",
)


class MoeaParseError(ValueError):
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


def _official_pdf(raw_url: str, page_url: str = MOEA_LIST_URL) -> str | None:
    url = urljoin(page_url, raw_url)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in MOEA_HOSTS:
        return None
    path = unquote(parsed.path)
    if not path.startswith("/news_images/pdf/") or not path.lower().endswith(".pdf"):
        return None
    encoded = quote(path, safe="/%^()_-.")
    return urlunsplit(("https", "portal.moea.gov.mm", encoded, parsed.query, ""))


def parse_visible_publication_date(value: str) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%d %B %Y").date().isoformat()
    except ValueError:
        return None


def is_procurement_invitation(title: str) -> bool:
    value = normalize_text(title)
    lower = value.lower()
    if not value:
        return False
    if any(token.lower() in lower for token in _EXCLUDE_STAGE_TOKENS):
        return False
    if any(token.lower() in lower for token in _EXCLUDE_NON_PROCUREMENT_TOKENS):
        return False
    return any(token.lower() in lower for token in _INCLUDE_TOKENS)


def parse_explicit_deadline(comment_text: str) -> str | None:
    text = normalize_text(comment_text).translate(_MYANMAR_DIGITS)
    if not text or "နောက်ဆုံး" not in text:
        return None
    marker = text.find("နောက်ဆုံး")
    tail = text[marker : marker + 220]
    match = re.search(r"(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{4})", tail)
    if match is None:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def _comment_text(value: str) -> str:
    decoded = unescape(value)
    stripped = re.sub(r"<[^>]+>", " ", decoded)
    return normalize_text(stripped)


@dataclass(frozen=True)
class MoeaTender:
    title: str
    publication_date: str
    location: str | None
    deadline: str | None
    scope_summary: str | None
    attachment_name: str
    attachment_url: str
    url: str = MOEA_LIST_URL

    item_kind = "TENDER"

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def record_fingerprint(self) -> str:
        material = f"{self.publication_date}|{normalize_text(self.title)}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()[:16]

    @property
    def reference_no(self) -> str:
        return f"MOEA-{self.publication_date.replace('-', '')}-{self.record_fingerprint[:8]}"

    @property
    def canonical_key(self) -> str:
        return f"moea:{self.publication_date}:{self.record_fingerprint}"

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": MOEA_ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_archive_event_fingerprint",
            "identity_material": "publication_date+normalized_title",
            "publication_date": self.publication_date,
            "deadline": self.deadline,
            "deadline_evidence": "EXPLICIT_HTML_COMMENT_FINAL_DATE" if self.deadline else "UNKNOWN_NO_EXPLICIT_FINAL_DATE_IN_HTML_COMMENT",
            "location": self.location,
            "scope_summary": self.scope_summary,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "HTML_ARCHIVE_CARD_COMMENT_TEXT_ATTACHMENT_METADATA",
            "url": self.url,
        }


@dataclass(frozen=True)
class _MoeaCard:
    title: str
    visible_date: str
    location: str | None
    comment_text: str | None
    attachment_href: str


class MoeaListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[_MoeaCard] = []
        self.card_count = 0
        self._card_depth = 0
        self._title_depth = 0
        self._li_depth = 0
        self._title_parts: list[str] = []
        self._li_parts: list[str] = []
        self._event_items: list[str] = []
        self._comments: list[str] = []
        self._attachment_href: str | None = None

    def _reset_card(self) -> None:
        self._title_depth = 0
        self._li_depth = 0
        self._title_parts = []
        self._li_parts = []
        self._event_items = []
        self._comments = []
        self._attachment_href = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "div":
            if self._card_depth:
                self._card_depth += 1
            elif "tender-content" in classes:
                self._card_depth = 1
                self.card_count += 1
                self._reset_card()
                return
        if not self._card_depth:
            return
        if lowered == "h4" and "tender-title" in classes:
            self._title_depth = 1
            return
        if self._title_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._title_depth += 1
        if lowered == "li":
            self._li_depth = 1
            self._li_parts = []
            return
        if self._li_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._li_depth += 1
        if lowered == "a" and self._attachment_href is None:
            href = _attr(attrs, "href")
            if href and ".pdf" in href.lower():
                self._attachment_href = href

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._card_depth:
            return
        if self._title_depth and lowered in {"h4", "a", "span", "strong", "em"}:
            self._title_depth -= 1
        if self._li_depth and lowered in {"li", "span", "i", "a", "strong", "em"}:
            self._li_depth -= 1
            if lowered == "li" and self._li_depth == 0:
                value = normalize_text(" ".join(self._li_parts))
                if value:
                    self._event_items.append(value)
                self._li_parts = []
        if lowered == "div":
            self._card_depth -= 1
            if self._card_depth == 0:
                title = normalize_text(" ".join(self._title_parts))
                if title and self._event_items and self._attachment_href:
                    comment = max(self._comments, key=len) if self._comments else None
                    self.cards.append(
                        _MoeaCard(
                            title=title,
                            visible_date=self._event_items[0],
                            location=self._event_items[1] if len(self._event_items) > 1 else None,
                            comment_text=comment,
                            attachment_href=self._attachment_href,
                        )
                    )
                self._reset_card()

    def handle_data(self, data: str) -> None:
        if not self._card_depth:
            return
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self._title_parts.append(value)
        if self._li_depth:
            self._li_parts.append(value)

    def handle_comment(self, data: str) -> None:
        if not self._card_depth:
            return
        value = _comment_text(data)
        if value:
            self._comments.append(value)


def parse_tender_records(html_bytes: bytes, page_url: str = MOEA_LIST_URL) -> list[MoeaTender]:
    parser = MoeaListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise MoeaParseError("MOEA tender listing structure not found")

    selected: list[MoeaTender] = []
    seen: dict[str, str] = {}
    for card in parser.cards:
        if not is_procurement_invitation(card.title):
            continue
        publication_date = parse_visible_publication_date(card.visible_date)
        attachment_url = _official_pdf(card.attachment_href, page_url)
        if publication_date is None or attachment_url is None:
            continue
        attachment_name = unquote(urlparse(attachment_url).path.rsplit("/", 1)[-1])
        comment = card.comment_text or ""
        item = MoeaTender(
            title=card.title,
            publication_date=publication_date,
            location=card.location,
            deadline=parse_explicit_deadline(comment),
            scope_summary=comment[:2000] if comment else None,
            attachment_name=attachment_name,
            attachment_url=attachment_url,
            url=page_url,
        )
        prior_attachment = seen.get(item.canonical_key)
        if prior_attachment is not None:
            if prior_attachment != item.attachment_url:
                raise MoeaParseError(f"MOEA identity collision: {item.canonical_key}")
            continue
        seen[item.canonical_key] = item.attachment_url
        selected.append(item)

    return selected
