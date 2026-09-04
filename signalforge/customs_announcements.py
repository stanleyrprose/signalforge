from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlparse, urlsplit, urlunsplit

from .mpt import normalize_text

CUSTOMS_ANNOUNCEMENTS_URL = "https://customs.gov.mm/Announcements"
CUSTOMS_ISSUER = "Myanmar Customs Department"
CUSTOMS_HOSTS = {"customs.gov.mm", "www.customs.gov.mm"}


class CustomsAnnouncementParseError(ValueError):
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


def _encoded_official_pdf(raw_url: str) -> str | None:
    url = urljoin(CUSTOMS_ANNOUNCEMENTS_URL, raw_url)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in CUSTOMS_HOSTS:
        return None
    if not parsed.path.startswith("/admin/storage/files/") or not parsed.path.lower().endswith(".pdf"):
        return None
    encoded_path = quote(unquote(parsed.path), safe="/%^()_-.")
    return urlunsplit((parsed.scheme, parsed.netloc, encoded_path, parsed.query, parsed.fragment))


def parse_visible_publication_date(value: str) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    for fmt in ("%A %B %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def is_auction_notice(title: str) -> bool:
    value = normalize_text(title)
    return "လေလံ" in value and "တင်ဒါအောင်မြင်" not in value


@dataclass(frozen=True)
class CustomsAuctionNotice:
    title: str
    publication_date: str
    attachment_name: str
    attachment_url: str
    url: str = CUSTOMS_ANNOUNCEMENTS_URL

    item_kind = "AUCTION_NOTICE"
    deadline = None
    location = None

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def record_fingerprint(self) -> str:
        material = f"{normalize_text(self.title)}|{self.publication_date}|{self.attachment_name}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()[:16]

    @property
    def reference_no(self) -> str:
        return f"CUSTOMS-AUCTION-{self.publication_date.replace('-', '')}-{self.record_fingerprint[:8]}"

    @property
    def canonical_key(self) -> str:
        return f"customs-auction:{self.publication_date}:{self.record_fingerprint}"

    def payload(self) -> dict[str, str | None]:
        return {
            "item_kind": self.item_kind,
            "issuer": CUSTOMS_ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_archive_record_fingerprint",
            "publication_date": self.publication_date,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "detail_completeness": "HTML_EVENT_METADATA_ATTACHMENT_ONLY",
            "url": self.url,
        }


class CustomsAnnouncementListingParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.rows: list[tuple[str, str, str]] = []
        self._article_depth = 0
        self._title_depth = 0
        self._published_depth = 0
        self._title_parts: list[str] = []
        self._date_parts: list[str] = []
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        classes = _classes(attrs)
        if lowered == "article":
            if self._article_depth:
                self._article_depth += 1
            else:
                self._article_depth = 1
                self._title_depth = 0
                self._published_depth = 0
                self._title_parts = []
                self._date_parts = []
                self._href = None
            return
        if not self._article_depth:
            return
        if lowered in {"div", "header", "span", "h2", "a", "time"}:
            if self._title_depth:
                self._title_depth += 1
            if self._published_depth:
                self._published_depth += 1
        if lowered == "h2" and "entry-title" in classes:
            self._title_depth = 1
        if lowered == "time" and "entry-date" in classes and "published" in classes:
            self._published_depth = 1
        if lowered == "a" and self._title_depth:
            href = _attr(attrs, "href")
            if href:
                self._href = href

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._article_depth:
            return
        if self._title_depth and lowered in {"div", "header", "span", "h2", "a", "time"}:
            self._title_depth -= 1
        if self._published_depth and lowered in {"div", "header", "span", "h2", "a", "time"}:
            self._published_depth -= 1
        if lowered == "article":
            self._article_depth -= 1
            if self._article_depth == 0:
                title = normalize_text(" ".join(self._title_parts))
                visible_date = normalize_text(" ".join(self._date_parts))
                if title and visible_date and self._href:
                    self.rows.append((title, visible_date, self._href))

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value or not self._article_depth:
            return
        if self._title_depth:
            self._title_parts.append(value)
        if self._published_depth:
            self._date_parts.append(value)


def parse_auction_records(html_bytes: bytes, page_url: str = CUSTOMS_ANNOUNCEMENTS_URL) -> list[CustomsAuctionNotice]:
    parser = CustomsAnnouncementListingParser(page_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))

    selected: list[CustomsAuctionNotice] = []
    seen: set[str] = set()
    for title, visible_date, href in parser.rows:
        if not is_auction_notice(title):
            continue
        publication_date = parse_visible_publication_date(visible_date)
        attachment_url = _encoded_official_pdf(href)
        if publication_date is None or attachment_url is None:
            continue
        attachment_name = unquote(urlparse(attachment_url).path.rsplit("/", 1)[-1])
        item = CustomsAuctionNotice(
            title=title,
            publication_date=publication_date,
            attachment_name=attachment_name,
            attachment_url=attachment_url,
            url=page_url,
        )
        if item.canonical_key in seen:
            continue
        seen.add(item.canonical_key)
        selected.append(item)

    if not selected:
        raise CustomsAnnouncementParseError("no recognized Customs auction announcements")
    return selected
