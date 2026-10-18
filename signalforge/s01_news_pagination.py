"""Bounded discovery of official S01 Liferay listing pagination links."""
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse

from .s01_news_discovery import NEWS_URL


class _Pagination(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def pagination_urls(payload: bytes, *, base_url: str = NEWS_URL, max_pages: int = 5) -> list[str]:
    """Only follow Liferay page links for the same S01 news listing."""
    if not 1 <= max_pages <= 20:
        raise ValueError("max_pages must be between 1 and 20")
    parser = _Pagination()
    parser.feed(payload.decode("utf-8", errors="replace"))
    found = {}
    for href in parser.links:
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {"myanmar.gov.mm", "www.myanmar.gov.mm"}:
            continue
        if parsed.path != urlparse(NEWS_URL).path or parsed.port not in (None, 443):
            continue
        params = parse_qs(parsed.query)
        pages = [int(v) for k, values in params.items() if k.endswith("_cur") for v in values if v.isdecimal()]
        if not pages or not 2 <= pages[0] <= max_pages:
            continue
        if not any("AssetPublisherPortlet_INSTANCE_idasset354" in v for v in params.get("p_p_id", [])):
            continue
        found.setdefault(pages[0], urlunparse(parsed._replace(fragment="")))
    # Ignore out-of-window last-page jump links; this is a bounded daily review.
    return [found[p] for p in sorted(found)]
