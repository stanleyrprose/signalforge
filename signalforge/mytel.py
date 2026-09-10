from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser

MYTEL_ISSUER = "Telecom International Myanmar Co., Ltd (MYTEL)"
MYTEL_BASE_URL = "https://viettelglobal.com.vn"
MYTEL_FEED_URL = f"{MYTEL_BASE_URL}/en/get-post-press-room?categories_id=82&offset=0&limit=100"


class MytelParseError(ValueError):
    pass


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        if tag in {"br", "p", "div", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _text(value: object) -> str:
    parser = _TextParser()
    parser.feed(html.unescape(str(value or "")))
    lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line)


def _normalize_reference(raw: str) -> str | None:
    value = html.unescape(raw).replace("_", " ")
    match = re.search(r"(?P<num>\d{1,3})\s*/\s*(?P<year>20\d{2})\s*/\s*MYTEL\s*-\s*(?P<tail>.+)", value, re.I)
    if match is None:
        return None
    tail = match.group("tail")
    tail = re.split(r"\s*[–—]\s*|[\"“”]|\bPurchas(?:e|ing)\b", tail, maxsplit=1, flags=re.I)[0]
    tail = re.sub(r"\s+", " ", tail).strip(" .,:;-–—")
    if not tail:
        return None
    return f"{int(match.group('num'))}/{match.group('year')}/MYTEL-{tail.upper()}"


def _reference(text: str, name: str) -> str | None:
    labeled = re.compile(
        r"(?:Reference number of Request for Proposal|Bidding package name|ANNOUNCEMENT ON EXTENSION TO BIDDING\s*NO\.)\s*:?\s*(?:No\.?\s*)?(?:RFP[ _]*)?([^\n]+)",
        re.I,
    )
    for source in (text, name):
        for match in labeled.finditer(source):
            value = _normalize_reference(match.group(1))
            if value:
                return value
        match = re.search(r"\d{1,3}\s*/\s*20\d{2}\s*/\s*MYTEL\s*-\s*[^\n]+", source, re.I)
        if match:
            value = _normalize_reference(match.group(0))
            if value:
                return value
    return None


def _canonical_key(reference_no: str) -> str:
    match = re.match(r"(?P<num>\d+)/(20(?P<year>\d{2}))/MYTEL-", reference_no, re.I)
    if match is None:
        digest = hashlib.sha256(reference_no.encode("utf-8")).hexdigest()[:20]
        return f"mytel:ref-{digest}"
    return f"mytel:{int(match.group('num'))}-{match.group(2)}"


_MONTHS = {name.lower(): number for number, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1
)}
_DATE_TIME_RE = re.compile(
    r"(?P<hour>\d{1,2})\s*h\s*(?P<minute>\d{2})\s*,?\s*(?:"
    r"(?P<month1>January|February|March|April|May|June|July|August|September|October|November|December)\s+(?P<day1>\d{1,2})(?:st|nd|rd|th)?"
    r"|(?P<day2>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month2>January|February|March|April|May|June|July|August|September|October|November|December)"
    r")\s*,?\s*(?P<year>20\d{2})",
    re.I,
)


def _parse_date_time(value: str) -> tuple[str, str] | None:
    match = _DATE_TIME_RE.search(value)
    if match is None:
        return None
    month_name = match.group("month1") or match.group("month2")
    day = match.group("day1") or match.group("day2")
    try:
        dt = datetime(
            int(match.group("year")),
            _MONTHS[str(month_name).lower()],
            int(str(day)),
            int(match.group("hour")),
            int(match.group("minute")),
        )
    except (KeyError, ValueError):
        return None
    return dt.date().isoformat(), dt.strftime("%H:%M")


def _deadline(text: str) -> tuple[str | None, str | None, str | None, str]:
    explicit = re.search(r"Deadline for submitting the Proposal Document\s*:\s*([^\n]+)", text, re.I)
    if explicit:
        parsed = _parse_date_time(explicit.group(1))
        if parsed:
            return parsed[0], parsed[1], "BID_SUBMISSION_DEADLINE", "OFFICIAL_FEED_EXPLICIT_PROPOSAL_SUBMISSION_DEADLINE"

    collect = re.search(r"Time to collect bid documents\s*:\s*([^\n]+)", text, re.I)
    if collect:
        parsed = _parse_date_time(collect.group(1))
        if parsed:
            return parsed[0], parsed[1], "TENDER_FORM_SALE_CLOSE", "OFFICIAL_FEED_TENDER_DOCUMENT_COLLECTION_CLOSE"

    return None, None, None, "UNKNOWN_NOT_IN_OFFICIAL_FEED_TEXT"


def _opening(text: str) -> tuple[str | None, str | None]:
    match = re.search(r"(?:shall be opened in public on|Proposal Opening\s*:[^\n]*opened at)\s*([^\n]+)", text, re.I)
    if match is None:
        return None, None
    parsed = _parse_date_time(match.group(1))
    return parsed if parsed else (None, None)


def _project_name(text: str, name: str, reference_no: str) -> str:
    for source in (text, name):
        match = re.search(r"[“\"](?P<name>Purchas(?:e|ing)\s+[^\"”\n]{2,220}?\s+for\s+Mytel)[”\"]", source, re.I)
        if match:
            return re.sub(r"\s+", " ", match.group("name")).strip()
    cleaned = re.sub(r"^Mytel\s+Announcement\s+on\s+(?:Invitation|Extension)\s+to\s+Bidding\s*", "", name, flags=re.I)
    return cleaned.strip() or reference_no


def _created_date(value: object) -> tuple[str, str] | None:
    raw = str(value or "")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.date().isoformat(), dt.isoformat()


@dataclass(frozen=True)
class MytelTender:
    reference_no: str
    project_name: str
    publication_date: str
    deadline: str | None
    deadline_time: str | None
    deadline_kind: str | None
    deadline_evidence: str
    tender_opening_date: str | None
    tender_opening_time: str | None
    source_post_id: int
    source_created_at: str
    source_version_kind: str
    url: str

    item_kind = "TENDER"
    location = "Yangon, Myanmar"
    issuer = MYTEL_ISSUER

    @property
    def canonical_key(self) -> str:
        return _canonical_key(self.reference_no)

    @property
    def title(self) -> str:
        return self.project_name

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": self.issuer,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "rfp_reference",
            "publication_date": self.publication_date,
            "deadline": self.deadline,
            "deadline_time": self.deadline_time,
            "deadline_kind": self.deadline_kind,
            "deadline_evidence": self.deadline_evidence,
            "tender_opening_date": self.tender_opening_date,
            "tender_opening_time": self.tender_opening_time,
            "scope_summary": self.project_name,
            "location": self.location,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "OFFICIAL_FEED_FULL_TEXT_SCOPE_AND_ACTION_DATE" if self.deadline else "OFFICIAL_FEED_SCOPE_DEADLINE_UNKNOWN",
            "source_post_id": self.source_post_id,
            "source_created_at": self.source_created_at,
            "source_version_kind": self.source_version_kind,
            "semantic_version": 1,
            "url": self.url,
        }


def _record_tender(record: dict[str, object]) -> MytelTender | None:
    content = str(record.get("content") or "")
    name = str(record.get("name") or "")
    text = _text(content)
    issuer_text = f"{name}\n{text}".lower()
    if "telecom international myanmar co., ltd" not in issuer_text or "mytel" not in issuer_text:
        return None
    reference_no = _reference(text, name)
    if reference_no is None or "/MYTEL-" not in reference_no:
        return None
    created = _created_date(record.get("created_at"))
    if created is None:
        return None
    try:
        source_post_id = int(record.get("id"))
    except (TypeError, ValueError):
        return None
    slugable = record.get("slugable")
    slug = str(slugable.get("key") or "") if isinstance(slugable, dict) else ""
    if not slug:
        return None
    deadline, deadline_time, deadline_kind, evidence = _deadline(text)
    opening_date, opening_time = _opening(text)
    version_kind = "EXTENSION" if "extension to bidding" in f"{name}\n{text}".lower() else "INVITATION"
    return MytelTender(
        reference_no=reference_no,
        project_name=_project_name(text, name, reference_no),
        publication_date=created[0],
        deadline=deadline,
        deadline_time=deadline_time,
        deadline_kind=deadline_kind,
        deadline_evidence=evidence,
        tender_opening_date=opening_date,
        tender_opening_time=opening_time,
        source_post_id=source_post_id,
        source_created_at=created[1],
        source_version_kind=version_kind,
        url=f"{MYTEL_BASE_URL}/en/{slug}",
    )


def parse_tender_records(payload: bytes, _url: str = MYTEL_FEED_URL) -> list[MytelTender]:
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MytelParseError(f"invalid Mytel feed JSON: {exc}") from exc
    rows = decoded.get("data") if isinstance(decoded, dict) else None
    if not isinstance(rows, list):
        raise MytelParseError("Mytel feed missing data list")

    latest: dict[str, MytelTender] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        tender = _record_tender(raw)
        if tender is None:
            continue
        previous = latest.get(tender.canonical_key)
        if previous is None or (tender.source_created_at, tender.source_post_id) > (previous.source_created_at, previous.source_post_id):
            latest[tender.canonical_key] = tender
    return sorted(latest.values(), key=lambda item: (item.source_created_at, item.canonical_key), reverse=True)
