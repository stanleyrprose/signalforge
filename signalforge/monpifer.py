from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlparse

from .mpt import normalize_text

MONPIFER_TENDERS_URL = "https://www.monpifer.gov.mm/my/ministry-tenders"
MONPIFER_ISSUER = "Ministry of National Planning, Investment and Foreign Economic Relations"
MONPIFER_HOSTS = {"monpifer.gov.mm", "www.monpifer.gov.mm"}
_MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))
_TENDER_TOKENS = ("အိတ်ဖွင့်တင်ဒါ", "အိတ်ဖွင့်တင်ဒါ", "open tender")


class MonpiferParseError(ValueError):
    pass


def _attr(attrs, name: str) -> str | None:  # type: ignore[no-untyped-def]
    for key, value in attrs:
        if key == name and value is not None:
            return str(value)
    return None


def _issuer_path(path: str) -> str:
    if path.startswith("/index.php/"):
        return path[len("/index.php") :]
    return path


def _official_article_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in MONPIFER_HOSTS:
        return None
    path = _issuer_path(parsed.path)
    if not path.startswith("/my/ministry-article/"):
        return None
    alias = path.rstrip("/").rsplit("/", 1)[-1]
    if not alias:
        return None
    return f"https://www.monpifer.gov.mm/my/ministry-article/{alias}"


def _official_pdf_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in MONPIFER_HOSTS:
        return None
    path = _issuer_path(parsed.path)
    if not path.startswith("/sites/default/files/tender_pdf/"):
        return None
    if not path.lower().endswith(".pdf"):
        return None
    return f"https://www.monpifer.gov.mm{path}"


def _article_alias(article_url: str) -> str:
    return urlparse(article_url).path.rstrip("/").rsplit("/", 1)[-1]


def _visible_deadline(value: str) -> str | None:
    text = normalize_text(value)
    for fmt in ("%m/%d/%Y - %H:%M", "%m/%d/%Y-%H:%M"):
        try:
            parsed = datetime.strptime(text, fmt).replace(tzinfo=_MYANMAR_TZ)
            return parsed.isoformat()
        except ValueError:
            pass
    return None


def _is_open_tender(description: str) -> bool:
    value = normalize_text(description).lower()
    return any(token in value for token in _TENDER_TOKENS)


@dataclass(frozen=True)
class MonpiferTender:
    source_record_id: str
    description: str
    deadline: str
    tender_department: str | None
    attachment_name: str | None
    attachment_url: str | None
    url: str

    item_kind = "TENDER"
    publication_date = None
    location = None

    @property
    def reference_no(self) -> str:
        return self.source_record_id

    @property
    def reference_no_kind(self) -> str:
        return "issuer_article_alias"

    @property
    def title(self) -> str:
        return self.description

    @property
    def project_name(self) -> str:
        return self.description

    @property
    def canonical_key(self) -> str:
        return f"monpifer:{self.source_record_id}"

    def payload(self) -> dict[str, str | None]:
        return {
            "item_kind": self.item_kind,
            "issuer": MONPIFER_ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": self.reference_no_kind,
            "source_record_id": self.source_record_id,
            "publication_date": None,
            "deadline": self.deadline,
            "tender_department": self.tender_department,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "deadline_evidence": "VISIBLE_LAST_DATE_TEXT",
            "detail_completeness": "LISTING_COMPLETE_HTML_ATTACHMENT_METADATA",
            "url": self.url,
        }


class MonpiferTenderTableParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.rows: list[tuple[list[str], list[str]]] = []
        self._in_row = False
        self._cell_depth = 0
        self._cells: list[str] = []
        self._cell_parts: list[str] = []
        self._hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        lowered = tag.lower()
        if lowered == "tr":
            self._in_row = True
            self._cell_depth = 0
            self._cells = []
            self._cell_parts = []
            self._hrefs = []
            return
        if not self._in_row:
            return
        if lowered in {"td", "th"}:
            self._cell_depth = 1
            self._cell_parts = []
            return
        if self._cell_depth and lowered not in {"br", "img", "input", "meta", "link"}:
            self._cell_depth += 1
        if lowered == "a":
            href = _attr(attrs, "href")
            if href:
                self._hrefs.append(urljoin(self.page_url, href))

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._in_row:
            return
        if lowered in {"td", "th"} and self._cell_depth:
            self._cells.append(normalize_text(" ".join(self._cell_parts)))
            self._cell_depth = 0
            self._cell_parts = []
            return
        if self._cell_depth:
            self._cell_depth -= 1
        if lowered == "tr":
            self.rows.append((list(self._cells), list(self._hrefs)))
            self._in_row = False

    def handle_data(self, data: str) -> None:
        if self._in_row and self._cell_depth:
            value = normalize_text(data)
            if value:
                self._cell_parts.append(value)


def parse_tender_records(html_bytes: bytes, page_url: str = MONPIFER_TENDERS_URL) -> list[MonpiferTender]:
    parser = MonpiferTenderTableParser(page_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))

    tenders: list[MonpiferTender] = []
    seen: set[str] = set()
    for cells, hrefs in parser.rows:
        if len(cells) < 5:
            continue
        deadline = _visible_deadline(cells[0])
        description = normalize_text(cells[1])
        department = normalize_text(cells[3]) or None
        if deadline is None or not description or not _is_open_tender(description):
            continue

        article_url = next(
            (candidate for candidate in (_official_article_url(href) for href in hrefs) if candidate),
            None,
        )
        if article_url is None:
            continue
        source_record_id = _article_alias(article_url)
        if source_record_id in seen:
            continue
        seen.add(source_record_id)

        attachment_url = next(
            (candidate for candidate in (_official_pdf_url(href) for href in hrefs) if candidate),
            None,
        )
        attachment_name = None
        if attachment_url:
            attachment_name = unquote(urlparse(attachment_url).path.rsplit("/", 1)[-1])

        tenders.append(
            MonpiferTender(
                source_record_id=source_record_id,
                description=description,
                deadline=deadline,
                tender_department=department,
                attachment_name=attachment_name,
                attachment_url=attachment_url,
                url=article_url,
            )
        )

    if not tenders:
        raise MonpiferParseError("no recognized MONPIFER tender rows")
    return tenders
