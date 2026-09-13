from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

from .mpt import normalize_text

LIST_URL = "https://mpt.com.mm/en/about-home/media-press-releases/latest-news/"
ISSUER = "Myanma Posts and Telecommunications (MPT)"
SELECTION_POLICY_VERSION = 1
_NETWORK_TOKENS = (
    "5g", "4g", "lte", "network", "fiber", "fibre", "ftth", "core network", "transport network",
    "radio network", "infrastructure", "coverage", "network site", "base station", "spectrum", "backhaul",
    "network expansion", "network upgrade", "high-speed fiber", "emergency network",
)


class MptNetworkParseError(ValueError):
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


def _is_network_notice(value: str) -> bool:
    lower = normalize_text(value).lower()
    return any(token in lower for token in _NETWORK_TOKENS)


@dataclass(frozen=True)
class MptNetworkNotice:
    record_id: str
    title: str
    publication_date: str
    scope_summary: str
    url: str

    item_kind = "REGULATORY_NOTICE"
    deadline = None
    location = "Myanmar"

    @property
    def reference_no(self) -> str:
        return f"MPT-NET-{self.record_id[:48]}"

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def canonical_key(self) -> str:
        return f"mpt-network:{self.record_id}"

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": "official_press_release_slug",
            "source_record_id": self.record_id,
            "publication_date": self.publication_date,
            "deadline": None,
            "location": self.location,
            "scope_summary": self.scope_summary,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "STRATEGIC_INTELLIGENCE",
            "relevance_categories": ["TELECOM"],
            "telecom_signal_kind": "NETWORK_TECHNOLOGY",
            "detail_completeness": "OFFICIAL_MEDIA_LISTING_TITLE_EXCERPT",
            "url": self.url,
        }


class _ListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.card_count = 0
        self.records: list[tuple[str, str, str, str]] = []
        self._depth = 0
        self._date_depth = 0
        self._title_depth = 0
        self._excerpt_depth = 0
        self._date: list[str] = []
        self._title: list[str] = []
        self._excerpt: list[str] = []
        self._url: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        tag = tag.lower()
        classes = _classes(attrs)
        if tag == "div" and "pressrelease_box" in classes and not self._depth:
            self._depth = 1
            self.card_count += 1
            self._date, self._title, self._excerpt, self._url = [], [], [], None
            return
        if not self._depth:
            return
        if tag == "div":
            self._depth += 1
        if tag == "span" and "date" in classes:
            self._date_depth = 1
        if tag in {"h3", "h4"} and "main-title" in classes:
            self._title_depth = 1
        if tag == "p" and "more_share" not in classes:
            self._excerpt_depth = 1
        if tag == "a" and "btn-blue" in classes:
            href = _attr(attrs, "href")
            if href and urlparse(href).scheme == "https" and (urlparse(href).hostname or "").lower() in {"mpt.com.mm", "www.mpt.com.mm"}:
                self._url = href

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if not self._depth:
            return
        if self._date_depth and tag == "span":
            self._date_depth = 0
        if self._title_depth and tag in {"h3", "h4"}:
            self._title_depth = 0
        if self._excerpt_depth and tag == "p":
            self._excerpt_depth = 0
        if tag == "div":
            self._depth -= 1
            if self._depth == 0:
                date = normalize_text(" ".join(self._date))
                title = normalize_text(" ".join(self._title))
                excerpt = normalize_text(" ".join(self._excerpt))
                if self._url and title:
                    self.records.append((date, title, excerpt, self._url))

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._date_depth:
            self._date.append(value)
        if self._title_depth:
            self._title.append(value)
        if self._excerpt_depth:
            self._excerpt.append(value)


def parse_network_records(payload: bytes, page_url: str = LIST_URL) -> list[MptNetworkNotice]:
    parser = _ListingParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    if parser.card_count == 0:
        raise MptNetworkParseError("MPT press release cards not found")
    selected: list[MptNetworkNotice] = []
    seen: set[str] = set()
    for raw_date, title, excerpt, url in parser.records:
        if not _is_network_notice(f"{title} {excerpt}"):
            continue
        match = re.search(r"(\d{1,2}\s+[A-Za-z]{3}\s+20\d{2})", raw_date)
        if match is None:
            continue
        try:
            publication = datetime.strptime(match.group(1), "%d %b %Y").date().isoformat()
        except ValueError:
            continue
        record_id = urlparse(url).path.strip("/").split("/")[-1]
        if not record_id or record_id in seen:
            continue
        seen.add(record_id)
        selected.append(MptNetworkNotice(record_id, title, publication, excerpt or title, url))
    return selected
