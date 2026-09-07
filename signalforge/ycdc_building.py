from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser

from .mpt import normalize_text

YCDC_BUILDING_URL = "https://www.ycdc.gov.mm/frontend_engineering_building_detail/1"
YCDC_ISSUER = "Yangon City Development Committee, Myanmar"
SELECTION_POLICY_VERSION = 1

_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_EXCLUDE_TOKENS = (
    "လေလံ",
    "အငှားချထား",
    "ရောင်းချ",
    "ဖြိုဖျက်ရောင်းချ",
    "auction",
    "lease",
    "sale",
)
_IMPLEMENTATION_TOKENS = (
    "ပူးပေါင်းဆောင်ရွက်",
    "အကောင်အထည်ဖော်",
    "ဆောက်လုပ်",
    "public private partnership",
    "ppp",
    "construction",
)


class YcdcBuildingParseError(ValueError):
    pass


def _normalize_for_match(value: str) -> str:
    return normalize_text(value).lower()


def is_building_implementation_opportunity(text: str) -> bool:
    value = _normalize_for_match(text)
    marker = value.find("တင်ဒါခေါ်ယူခြင်း")
    if marker < 0:
        return False
    scope = value[marker + len("တင်ဒါခေါ်ယူခြင်း") :]
    boundary = scope.find("၂။")
    if boundary > 0:
        scope = scope[:boundary]
    if any(token.lower() in scope for token in _EXCLUDE_TOKENS):
        return False
    return any(token.lower() in scope for token in _IMPLEMENTATION_TOKENS)


def parse_explicit_deadline(text: str) -> str | None:
    value = normalize_text(text).translate(_MYANMAR_DIGITS)
    marker = value.find("နောက်ဆုံးရက်")
    if marker < 0:
        return None
    tail = value[marker : marker + 220]
    match = re.search(r"(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{4})", tail)
    if match is None:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def extract_scope_summary(text: str) -> str | None:
    value = normalize_text(text)
    marker = value.find("တင်ဒါခေါ်ယူခြင်း")
    if marker < 0:
        return None
    value = value[marker + len("တင်ဒါခေါ်ယူခြင်း") :].strip()
    boundary = value.find("၂။")
    if boundary > 0:
        value = value[:boundary]
    value = normalize_text(value)
    return value[:3000] if value else None


@dataclass(frozen=True)
class YcdcBuildingTender:
    scope_summary: str
    deadline: str
    raw_block: str
    url: str = YCDC_BUILDING_URL

    item_kind = "TENDER"
    publication_date = None
    location = "Yangon"

    @property
    def title(self) -> str:
        return self.scope_summary[:500]

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def record_fingerprint(self) -> str:
        material = f"{self.deadline}|{normalize_text(self.scope_summary)}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()[:16]

    @property
    def reference_no(self) -> str:
        return f"YCDC-BLDG-{self.deadline.replace('-', '')}-{self.record_fingerprint[:8]}"

    @property
    def canonical_key(self) -> str:
        return f"ycdc-building:{self.deadline}:{self.record_fingerprint}"

    @property
    def block_hash(self) -> str:
        return hashlib.sha256(normalize_text(self.raw_block).encode("utf-8")).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": YCDC_ISSUER,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "issuer_archive_event_fingerprint",
            "identity_material": "explicit_deadline+normalized_scope_summary",
            "publication_date": None,
            "publication_date_evidence": "UNKNOWN_NOT_EXPOSED_IN_STABLE_ARCHIVE_HTML",
            "deadline": self.deadline,
            "deadline_evidence": "EXPLICIT_HTML_FINAL_SUBMISSION_DATE",
            "location": self.location,
            "scope_summary": self.scope_summary,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "opportunity_kind": "PPP_OR_BUILDING_IMPLEMENTATION",
            "detail_completeness": "HTML_ARCHIVE_SCOPE_DEADLINE_CONTACT_FIELDS",
            "attachment_policy": "HTML_ONLY_NO_ATTACHMENT_REQUIRED",
            "url": self.url,
        }


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[str] = []
        self.table_count = 0
        self._depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        if tag.lower() != "table":
            return
        if self._depth == 0:
            self.table_count += 1
            self._parts = []
        self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "table" or self._depth == 0:
            return
        self._depth -= 1
        if self._depth == 0:
            value = normalize_text(" ".join(self._parts))
            if value:
                self.tables.append(value)
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._depth == 0:
            return
        value = normalize_text(data)
        if value:
            self._parts.append(value)


def parse_tender_records(html_bytes: bytes, page_url: str = YCDC_BUILDING_URL) -> list[YcdcBuildingTender]:
    parser = _TableParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    if parser.table_count == 0:
        raise YcdcBuildingParseError("YCDC Building archive table structure not found")

    tender_blocks = [table for table in parser.tables if "တင်ဒါ" in table or "လေလံ" in table]
    if not tender_blocks:
        raise YcdcBuildingParseError("YCDC Building tender block structure not found")

    selected: list[YcdcBuildingTender] = []
    seen: dict[str, str] = {}
    for block in tender_blocks:
        if not is_building_implementation_opportunity(block):
            continue
        deadline = parse_explicit_deadline(block)
        scope = extract_scope_summary(block)
        if deadline is None or scope is None:
            continue
        item = YcdcBuildingTender(scope_summary=scope, deadline=deadline, raw_block=block, url=page_url)
        prior_hash = seen.get(item.canonical_key)
        if prior_hash is not None:
            if prior_hash != item.block_hash:
                raise YcdcBuildingParseError(f"YCDC Building identity collision: {item.canonical_key}")
            continue
        seen[item.canonical_key] = item.block_hash
        selected.append(item)

    return selected
