"""Bounded discovery for the National Portal's separate government news surface.

Discovery hints never become verified news or tenders without issuer detail evidence.
"""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse

NEWS_URL = "https://myanmar.gov.mm/en/news-media/news/latest-news"
ANNOUNCEMENTS_URL = "https://myanmar.gov.mm/en/news-media/announcements"
MAX_HTML_BYTES = 2_000_000
MAX_CANDIDATES = 60


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.href: str | None = None
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data):
        if self.href is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join(" ".join(self.parts).split())))
            self.href = None
            self.parts = []


def parse_news_discovery(payload: bytes, *, base_url: str = NEWS_URL) -> list[dict[str, str]]:
    """Conservative portal links, no headline facts or publication dates invented."""
    if len(payload) > MAX_HTML_BYTES:
        raise ValueError("news listing exceeds bounded acquisition size")
    base = urlparse(base_url)
    if base.scheme != "https" or base.hostname not in {"myanmar.gov.mm", "www.myanmar.gov.mm"}:
        raise ValueError("unsupported government news origin")
    parser = _Links()
    parser.feed(payload.decode("utf-8", errors="replace"))
    found: dict[str, dict[str, str]] = {}
    for href, title in parser.links:
        if not href or len(title) < 12 or len(title) > 450:
            continue
        url = urlparse(urljoin(base_url, href))
        if url.scheme != "https" or url.hostname not in {"myanmar.gov.mm", "www.myanmar.gov.mm"} or url.port not in (None, 443):
            continue
        if not ("news-media" in url.path or "assetEntryId=" in url.query):
            continue
        if not ("assetEntryId=" in url.query or "/-/" in url.path or "/detail" in url.path):
            continue
        normalized = urlunparse((url.scheme, url.netloc.lower(), url.path, "", url.query, ""))
        found[normalized] = {"url": normalized, "title_hint": title,
                             "listing_sha256": hashlib.sha256(payload).hexdigest(),
                             "evidence_status": "LISTING_HINT_ONLY"}
        if len(found) >= MAX_CANDIDATES:
            break
    return list(found.values())
