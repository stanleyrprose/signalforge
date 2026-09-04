from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlparse

from .mpt import normalize_text

CUSTOMS_NOTIFICATIONS_URL = "https://customs.gov.mm/notifications"
CUSTOMS_ISSUER = "Myanmar Customs Department"
CUSTOMS_HOSTS = {"customs.gov.mm", "www.customs.gov.mm"}

_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_REFERENCE_RE = re.compile(r"([0-9]+)\s*/\s*([0-9]{4})")


class CustomsParseError(ValueError):
    pass


def _attr(attrs, name: str) -> str | None:  # type: ignore[no-untyped-def]
    for key, value in attrs:
        if key == name and value is not None:
            return str(value)
    return None


def normalize_reference(value: str) -> str | None:
    text = normalize_text(value).translate(_MYANMAR_DIGITS)
    match = _REFERENCE_RE.search(text)
    if match is None:
        return None
    return f"{match.group(1)}/{match.group(2)}"


def classify_customs_notice(title: str) -> str:
    value = normalize_text(title).lower()
    if "အကောက်ခွန်နှုန်း" in value or "customs dut" in value or "tariff" in value:
        return "CUSTOMS_TARIFF"
    if "လုပ်ထုံးလုပ်နည်း" in value or "လုပ်ငန်းလမ်းညွှန်" in value or "procedure" in value or "guideline" in value:
        return "CUSTOMS_PROCEDURE"
    if "ကုန်သည်လုပ်ငန်းခွန်" in value or "commercial tax" in value:
        return "TAX_TREATMENT"
    return "CUSTOMS_NOTICE"


@dataclass(frozen=True)
class CustomsNotice:
    reference_no: str
    title: str
    notice_category: str
    attachment_name: str | None
    attachment_url: str | None
    url: str = CUSTOMS_NOTIFICATIONS_URL

    item_kind = "REGULATORY_NOTICE"
    publication_date = None
    deadline = None
    location = None

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def canonical_key(self) -> str:
        return f"customs-notice:{self.reference_no}"

    def payload(self) -> dict[str, str | None]:
        return {
            "item_kind": self.item_kind,
            "issuer": CUSTOMS_ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_notification_or_order_number",
            "publication_date": None,
            "notice_category": self.notice_category,
            "attachment_name": self.attachment_name,
            "attachment_url": self.attachment_url,
            "attachment_policy": "METADATA_ONLY_NON_BLOCKING",
            "detail_completeness": "LISTING_EVENT_METADATA_ATTACHMENT_ONLY",
            "url": self.url,
        }


class CustomsNotificationTableParser(HTMLParser):
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
        if lowered == "td":
            self._cell_depth = 1
            self._cell_parts = []
            return
        if self._cell_depth:
            self._cell_depth += 1
        if lowered == "a":
            href = _attr(attrs, "href")
            if href:
                self._hrefs.append(urljoin(self.page_url, href))

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if not self._in_row:
            return
        if lowered == "td" and self._cell_depth:
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


def _official_pdf_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in CUSTOMS_HOSTS:
        return None
    if not parsed.path.lower().endswith(".pdf"):
        return None
    if not parsed.path.startswith("/admin/storage/files/"):
        return None
    return url


def parse_notification_records(html_bytes: bytes, page_url: str = CUSTOMS_NOTIFICATIONS_URL) -> list[CustomsNotice]:
    parser = CustomsNotificationTableParser(page_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))

    notices: list[CustomsNotice] = []
    seen: set[str] = set()
    for cells, hrefs in parser.rows:
        if len(cells) < 2:
            continue
        reference = normalize_reference(cells[0])
        title = normalize_text(cells[1])
        if reference is None or not title:
            continue
        if reference in seen:
            continue
        seen.add(reference)

        attachment_url = next((candidate for candidate in (_official_pdf_url(href) for href in hrefs) if candidate), None)
        attachment_name = None
        if attachment_url:
            attachment_name = unquote(urlparse(attachment_url).path.rsplit("/", 1)[-1])
        notices.append(
            CustomsNotice(
                reference_no=reference,
                title=title,
                notice_category=classify_customs_notice(title),
                attachment_name=attachment_name,
                attachment_url=attachment_url,
                url=page_url,
            )
        )

    if not notices:
        raise CustomsParseError("no recognized Customs notification rows")
    return notices
