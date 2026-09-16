from __future__ import annotations

import re
from dataclasses import dataclass

from .mpt import SitemapEntry, normalize_text
from .yangon_construction import _numeric_text, parse_tender_detail as parse_wordpress_tender_detail
from .yangon_construction import parse_tender_listing as parse_wordpress_tender_listing

ISSUER = "Yangon City Development Committee (YCDC)"
SELECTION_POLICY_VERSION = 1
YCDC_TOKEN = "".join(chr(value) for value in (0x101B,0x1014,0x103A,0x1000,0x102F,0x1014,0x103A,0x1019,0x103C,0x102D,0x102F,0x1037,0x1010,0x1031,0x102C,0x103A,0x1005,0x100A,0x103A,0x1015,0x1004,0x103A,0x101E,0x102C,0x101A,0x102C,0x101B,0x1031,0x1038,0x1000,0x1031,0x102C,0x103A,0x1019,0x1010,0x102E))

_CONSTRUCTION_TERMS = (
    "hdpe",
    "hrb-400",
    "cement",
    "chipping",
    "crushed dust",
    "rebar",
    "steel bar",
    "road",
    "bridge",
    "construction",
    "retaining wall",
    "ဘိလပ်မြေ",
    "သံချောင်း",
    "လမ်း",
    "တံတား",
    "ဆောက်လုပ်",
)
_ENGINEERING_TERMS = (
    "transformer",
    "substation",
    "induction motor",
    "generator",
    "pump",
    "switchgear",
    "electrical",
    "mechanical",
    "ဓာတ်အား",
    "လျှပ်စစ်",
)
_ICT_TERMS = (
    "server",
    "data center",
    "data centre",
    "network equipment",
    "router",
    "switch",
    "firewall",
    "fiber",
    "fibre",
    "telecom",
    "gmdss",
)

_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[-./–]\s*(\d{1,2})\s*[-./–]\s*(20\d{2})(?!\d)")
_TIME_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[:.]\s*(\d{2})(?!\d)")


def parse_tender_listing(html_bytes: bytes) -> list[SitemapEntry]:
    return parse_wordpress_tender_listing(html_bytes)


def _mission_sector(title: str, scope: str) -> str | None:
    text = f" {normalize_text(title + ' ' + scope).lower()} "
    if YCDC_TOKEN not in text:
        return None
    if any(term in text for term in _CONSTRUCTION_TERMS):
        return "CONSTRUCTION"
    if any(term in text for term in _ENGINEERING_TERMS):
        return "ENGINEERING"
    if any(term in text for term in _ICT_TERMS):
        return "TELECOM_ICT_INFRA"
    return None


def _deadline(scope: str) -> tuple[str | None, str | None]:
    text = _numeric_text(scope).replace("—", "-").replace("–", "-")
    markers = ("နောက်ဆုံးထား၍", "နောက်ဆုံးထား", "တင်ဒါပိတ်မည့်ရက်စွဲ", "တင်ဒါပိတ်မည့်ရက်စွဲ")
    windows: list[str] = []
    for marker in markers:
        start = 0
        while True:
            idx = text.find(marker, start)
            if idx < 0:
                break
            windows.append(text[max(0, idx - 260) : idx + 140])
            start = idx + len(marker)
    if not windows:
        windows = [text]

    candidates: list[tuple[str, str | None]] = []
    for window in windows:
        for match in _DATE_RE.finditer(window):
            day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            try:
                from datetime import date

                parsed = date(year, month, day).isoformat()
            except ValueError:
                continue
            after = window[match.end() : match.end() + 80]
            time_match = _TIME_RE.search(after)
            time_value = None
            if time_match:
                hour, minute = int(time_match.group(1)), int(time_match.group(2))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    time_value = f"{hour:02d}:{minute:02d}"
            candidates.append((parsed, time_value))
    if not candidates:
        return None, None
    return max(candidates, key=lambda value: value[0])


def _focus_scope(scope: str, sector: str) -> str:
    if sector != "CONSTRUCTION":
        return normalize_text(scope)[:900]
    text = _numeric_text(scope)
    parts: list[str] = []
    hdpe = re.search(r"HDPE[^\n]{0,180}?(\d+(?:\.\d+)?)\s*Lot", text, re.I)
    cement = re.search(r"ဘိလပ်မြေ[^\n]{0,180}?(\d+(?:\.\d+)?)\s*အိတ်", text)
    rebar = re.search(r"(\d+(?:\.\d+)?)\s*တန်\s*သံချောင်း[^\n]{0,120}?HRB-400", text, re.I)
    if hdpe:
        parts.append(f"HDPE pipe & fittings {hdpe.group(1)} Lot")
    elif "hdpe" in text.lower():
        parts.append("HDPE pipe & fittings")
    if cement:
        parts.append(f"Cement {cement.group(1)} bags")
    elif "ဘိလပ်မြေ" in text:
        parts.append("Cement")
    if rebar:
        parts.append(f"HRB-400 rebar {rebar.group(1)} tons")
    elif "hrb-400" in text.lower():
        parts.append("HRB-400 rebar")
    if any(term in text.lower() for term in ("chipping", "crushed dust")) or "သဲ" in text:
        parts.append("sand / aggregate / chipping / crushed dust")
    return "Construction materials: " + "; ".join(parts) if parts else normalize_text(scope)[:900]


@dataclass(frozen=True)
class YangonYCDCMissionTender:
    post_id: str
    title: str
    publication_date: str | None
    deadline: str | None
    deadline_time: str | None
    scope_summary: str
    focus_scope_summary: str
    mission_sector: str
    url: str

    item_kind = "TENDER"
    issuer = ISSUER
    location = "Yangon"

    @property
    def reference_no(self) -> str:
        return f"YCDC-YRG-{self.post_id}"

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def canonical_key(self) -> str:
        return f"yangon-ycdc-mission:{self.post_id}"

    def payload(self) -> dict[str, object]:
        categories = ["CONSTRUCTION"] if self.mission_sector == "CONSTRUCTION" else []
        if self.mission_sector == "TELECOM_ICT_INFRA":
            categories = ["ICT"]
        return {
            "item_kind": self.item_kind,
            "issuer": self.issuer,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": "wordpress_post_id",
            "source_record_id": self.post_id,
            "publication_date": self.publication_date,
            "deadline": self.deadline,
            "deadline_time": self.deadline_time,
            "deadline_kind": "BID_SUBMISSION_DEADLINE",
            "deadline_evidence": "OFFICIAL_HTML_FINAL_SUBMISSION_DATE_TIME" if self.deadline else "UNKNOWN_NOT_PARSED",
            "location": self.location,
            "scope_summary": self.scope_summary,
            "focus_scope_summary": self.focus_scope_summary,
            "mission_sector_hint": self.mission_sector,
            "relevance_categories": categories,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "OPPORTUNITY",
            "detail_completeness": "OFFICIAL_HTML_SCOPE_AND_DEADLINE_TIME" if self.deadline_time else "OFFICIAL_HTML_SCOPE_AND_DEADLINE",
            "attachment_policy": "HTML_ONLY_NO_ATTACHMENT_REQUIRED",
            "url": self.url,
        }


def parse_tender_detail(html_bytes: bytes, url: str) -> YangonYCDCMissionTender | None:
    base = parse_wordpress_tender_detail(html_bytes, url)
    if base is None:
        return None
    sector = _mission_sector(base.title, base.scope_summary)
    if sector is None:
        return None
    deadline, deadline_time = _deadline(base.scope_summary)
    return YangonYCDCMissionTender(
        post_id=base.post_id,
        title=base.title,
        publication_date=base.publication_date,
        deadline=deadline,
        deadline_time=deadline_time,
        scope_summary=base.scope_summary,
        focus_scope_summary=_focus_scope(base.scope_summary, sector),
        mission_sector=sector,
        url=url,
    )
