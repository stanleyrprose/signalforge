from __future__ import annotations

import hashlib
import html
import json
import os
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .acquisition_runtime import acquire_provider_document_ocr
from .assurance import aggregator_surface_snapshot
from .auditor import audit
from .briefing import business_briefing
from .config import Registry, db_path
from .coverage_gaps import reviewed_coverage_gaps, verified_external_opportunities
from .external_official_review import build_external_official_review_packet
from .db import connect
from .mission_focus import classify_mission_fit
from .telegram_delivery import TelegramDeliveryError, _send_message
from .translation import contains_myanmar, translate_myanmar_to_zh_hans
from .source_scorecard import source_scorecard

DIGEST_VERSION = 11
DIGEST_CHANNEL = "telegram-business-digest"
DIGEST_TIMEZONE = ZoneInfo("Asia/Yangon")
TELEGRAM_MESSAGE_LIMIT = 4096
TranslationBatch = Callable[[list[str]], tuple[list[str], bool]]


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _compact(value: object, limit: int = 96) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _official_review_candidates(snapshot: dict[str, object]) -> list[dict[str, object]]:
    details = snapshot.get("details") or {}
    if not isinstance(details, dict):
        return []
    unresolved = details.get("unresolved_leads") or []
    if not isinstance(unresolved, list):
        return []
    candidates: list[dict[str, object]] = []
    seen: set[str] = set()
    for value in unresolved:
        if not isinstance(value, dict):
            continue
        if value.get("evidence_kind") != "NATIONAL_PORTAL_HOSTED_DOCUMENT":
            continue
        if value.get("aggregator_only") is not True or value.get("canonical_truth") is not False:
            continue
        target_source = str(value.get("target_source_hint") or "")
        lead_id = str(value.get("lead_id") or "")
        url = str(value.get("url") or "")
        mission_sector = str(value.get("mission_sector_hint") or "")
        if mission_sector not in {"TELECOM_ICT_INFRA", "CONSTRUCTION", "ENERGY", "ENGINEERING"}:
            continue
        if not target_source or not lead_id or not url.startswith("https://myanmar.gov.mm/documents/"):
            continue
        if lead_id in seen:
            continue
        seen.add(lead_id)
        candidates.append(dict(value))
    candidates.sort(
        key=lambda item: (
            str(item.get("closing_date_hint") or "9999-12-31"),
            str(item.get("target_source_hint") or ""),
            str(item.get("lead_id") or ""),
        )
    )
    return candidates


_MYANMAR_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_PROCUREMENT_KEYWORDS = (
    "server", "software", "module", "scanner", "computer", "ups", "accessor",
    "equipment", "relay", "steel", "gas", "chemical", "machine", "cable",
    "battery", "router", "switch", "radio", "fiber", "fibre", "material",
)


def _presentation_cleanup(value: object) -> str:
    text = str(value or "").translate(_MYANMAR_DIGITS)
    text = re.sub(r"(?<=[0-9,])ဝ(?=\D|$)", "0", text)
    text = re.sub(r"အမှတ်\s*\((\d+)\)", r"第\1号", text)
    text = re.sub(r"ပစ္စည်း\s*\((\d+)\)\s*မျိုး", r"设备\1类", text)
    return " ".join(text.split())


def _scope_product_fragments(scope: object) -> list[str]:
    """Prefer concrete product/quantity fragments over tender boilerplate."""
    raw = _presentation_cleanup(scope)
    if not raw:
        return []
    segments = [segment.strip(" ;·") for segment in raw.split("|") if segment.strip(" ;·")]
    if len(segments) <= 1:
        return []
    ranked: list[tuple[int, int, str]] = []
    for index, segment in enumerate(segments):
        lowered = segment.lower()
        if re.search(r"_[0-9a-f]{8,}(?:-[0-9a-f]{4,})+", lowered):
            continue
        score = 0
        if any(keyword in lowered for keyword in _PROCUREMENT_KEYWORDS):
            score += 5
        if re.search(r"\b\d+[\s)]*(?:set|sets|no|nos|lot|lots|group|groups|ton|tons|kg|pcs?)\b", lowered):
            score += 4
        if re.search(r"\b(?:cap|dmp/l-|tender no\.?|ref(?:erence)?)\b", lowered):
            score += 1
        if score >= 4:
            cleaned = re.sub(r"\s+Ks\s*$", "", segment, flags=re.IGNORECASE)
            cleaned = re.sub(r"^\((?:second\s+)?retender\)\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"^[A-Z]{2,}/[A-Z]-\s*\d+\([^)]+\)\s*(?:CAP\s*)?", "", cleaned)
            cleaned = re.sub(r"^\([a-z]\)\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"^\([\u1000-\u109f]\)\s*", "", cleaned)
            cleaned = re.sub(r"\((\d+)\)\s*Nos?\b", r"×\1", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\((\d+)\)\s*Sets?\b", r"×\1套", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\((\d+)\)\s*Groups?\b", r"×\1组", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\((\d+)\)\s*Lots?\b", r"×\1 Lot", cleaned, flags=re.IGNORECASE)
            ranked.append((score, index, cleaned))
    selected = sorted(ranked, key=lambda row: row[1])[:6]
    fragments = [row[2] for row in selected]
    if len(fragments) >= 2 and fragments[0].rstrip().endswith("Information") and fragments[1].startswith("Technology "):
        fragments[0] = f"{fragments[0]} {fragments[1]}"
        del fragments[1]
    merged: list[str] = []
    for fragment in fragments:
        if merged and merged[-1].rstrip().lower().endswith(" and"):
            merged[-1] = f"{merged[-1]} {fragment}"
        else:
            merged.append(fragment)
    return merged


def _title_product_fragments(title: object) -> list[str]:
    raw = _presentation_cleanup(title)
    if not raw:
        return []
    fragments: list[str] = []
    relay = re.search(r"(Schneider\s+SEPAM\s+Relay\s+for\s+MSDS)\s*\((\d+)\s*No\)", raw, re.IGNORECASE)
    if relay:
        fragments.append(f"{relay.group(1)} ×{relay.group(2)}")
    pump = re.search(r"Equipments?\s+for\s+Second\s+Lift\s+Pump\s+House\s+设备(\d+)类", raw, re.IGNORECASE)
    if pump:
        fragments.append(f"Second Lift Pump House equipment ×{pump.group(1)}类")
    yarn = re.search(r"(1/7)\s+ပီစီချည်\(ရောင်စုံ\)\s+([0-9,]+)\s+ပေါင်", raw)
    if yarn:
        fragments.append(f"{yarn.group(1)} PC 彩色纱线 {yarn.group(2)} 磅")
    vessel = re.search(r"ရေယာဉ်\s+(\d+)\s+စီး", raw)
    if vessel:
        fragments.append(f"船舶 ×{vessel.group(1)}艘")
    if "ကုန်သေတ္တာတင်ယာဉ်" in raw and "ငှားရမ်း" in raw:
        fragments.append("医药原料、包装材料及机器备件集装箱卡车运输服务")
    return fragments


def _mofa_business_summary(scope: object) -> str | None:
    raw = _presentation_cleanup(scope)
    if not raw:
        return None
    fragments: list[str] = []
    server = re.search(r"Data Server\s*\(?\s*(\d+)\s*\)?\s*Set", raw, re.IGNORECASE)
    if server:
        fragments.append(f"Data Server ×{server.group(1)}套")
    windows = re.search(r"Windows Server\s+(20\d{2})\s+Standard\s+(\d+)\s+Core", raw, re.IGNORECASE)
    if windows:
        fragments.append(f"Windows Server {windows.group(1)} Standard {windows.group(2)} Core")
    sql = re.search(r"(?:Microsoft\s+)?SQL Server\s+(20\d{2})\s+Standard", raw, re.IGNORECASE)
    if sql:
        fragments.append(f"SQL Server {sql.group(1)} Standard")
    return "；".join(fragments) if fragments else None


def _moep_business_summary(scope: object) -> str | None:
    raw = _presentation_cleanup(scope)
    if not raw:
        return None
    if "Database Creation and Modification" in raw and re.search(r"SCADA[- ]+EMS", raw, re.IGNORECASE):
        return "500kV Phayagyi、Hlaingtharyar、Taungoo 变电站现有 SCADA-EMS 数据库创建与修改"
    spare_match = re.search(r"(?:စက်အရံ)?设备\s*(\d+)类", raw)
    if spare_match and "လျှပ်စစ်" in raw:
        return f"水电站机械及电气备件 {spare_match.group(1)}类"
    if "ACSR Conductor" in raw and "ACCC Conductor" in raw:
        distance = re.search(r"\(([0-9.]+)\)\s*မိုင်", raw)
        distance_text = f" {distance.group(1)}英里" if distance else ""
        return f"230kV Kamanat–Hlawga{distance_text}线路 ACSR→ACCC 导线更换所需材料"
    if "အောက်ဖော်ပြပါပစ္စည်း" in raw or "လိုအပ်သော" in raw:
        return "电力采购项目（官方附件当前失效，具体物资待核验）"
    return None


def _industry_scope_product_fragments(scope: object) -> list[str]:
    """Extract the concrete goods/services already present in current S38 scope text."""
    raw = _presentation_cleanup(scope)
    if not raw:
        return []
    patterns = (
        (r"Laboratory\s+Appratus\s+for\s+Enviromental\s+Control\s+System\s+设备(\d+)类", "环境控制实验室设备 {0}类"),
        (r"Chemical\s+Reagent\s*\((\d+)\)\s*မျိုး", "Chemical Reagent {0}类"),
        (r"Sample\s+Gas\s*\((\d+)\)\s*မျိုး", "Sample Gas {0}类"),
        (r"စက်ဆီ၊?ချောဆီ\s*\((\d+)\)\s*မျိုး", "润滑油 {0}类"),
        (r"Electrical\s+စက်အရန်\s+设备(\d+)类", "Electrical 备件 {0}类"),
        (r"Mechanical\s+စက်အရန်\s*设备(\d+)类", "Mechanical 备件 {0}类"),
        (r"Refractory\s*\((\d+)\)\s*မျိုး", "Refractory {0}类"),
        (r"Castable\s+Mortar\s*\((\d+)\)\s*မျိုး", "Castable Mortar {0}类"),
        (r"Consumable\s*\((\d+)\)\s*မျိုး", "Consumable {0}类"),
        (r"HMS-1\s*\(([0-9,]+)\)\s*Tons?", "HMS-1 {0}吨"),
        (r"HMS-2\s*\(([0-9,]+)\)\s*Tons?", "HMS-2 {0}吨"),
        (r"သံရည်ပျက်တုံး\s*\(([0-9,]+)\)\s*တန်\s*ဖြတ်တောက်ခြင်း", "废钢块切割服务 {0}吨"),
    )
    fragments: list[str] = []
    for pattern, template in patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            fragments.append(template.format(match.group(1)))
    if "ကုန်သေတ္တာတင်ယာဉ်" in raw and "ငှားရမ်း" in raw:
        fragments.append("医药原料、包装材料及机器备件集装箱卡车运输服务")
    return fragments


def _industry_actionability_overlay(item: dict[str, object]) -> dict[str, object]:
    """Add read-model-only actionability for S38 from already-retained official HTML text.

    This never mutates canonical state or Signal payloads. It only fills missing
    digest-facing location / next-action fields from explicit issuer text.
    """

    if str(item.get("source_id") or "") != "S38":
        return dict(item)
    if item.get("location") and item.get("next_action_summary"):
        return dict(item)

    raw = _presentation_cleanup(item.get("scope_excerpt") or item.get("scope_summary") or "")
    if not raw:
        return dict(item)
    raw = re.sub(r"(?<=\d)ဝ(?=\d)", "0", raw)

    result = dict(item)
    submission_tail = ""
    for marker in (
        "တင်ဒါတင်သွင်းရမည့်နေရာ",
        "တင်ဒါတင်သွင်းရမည့်နေရာ",
        "တင်ဒါသွင်းရမည့်နေရာ",
        "တင်ဒါသွင်းရမည့်နေရာ",
    ):
        pos = raw.find(marker)
        if pos >= 0:
            submission_tail = raw[pos + len(marker) : pos + len(marker) + 650]
            break

    office_no: str | None = None
    if submission_tail:
        office = re.search(r"ရုံး(?:အမှတ်\s*\(?\s*(\d+)\s*\)?|第(\d+)号)", submission_tail)
        if office and "နေပြည်တော်" in submission_tail:
            office_no = office.group(1) or office.group(2)
            if not result.get("location"):
                result["location"] = f"Office No.{office_no}, Nay Pyi Taw"
                result["location_evidence"] = "S38_OFFICIAL_HTML_SUBMISSION_LOCATION"

    phones: list[str] = []
    phone_pos = raw.find("ဖုန်း")
    if phone_pos >= 0:
        phone_segment = raw[phone_pos : phone_pos + 140]
        for phone in re.findall(r"(?:0\d{1,2}|09)-\d{5,10}", phone_segment):
            if phone not in phones:
                phones.append(phone)
            if len(phones) >= 2:
                break

    if not result.get("next_action_summary"):
        deadline = str(result.get("deadline") or "")
        deadline_time = str(result.get("deadline_time") or "")
        date_text = deadline
        try:
            parsed = datetime.fromisoformat(deadline).date()
            date_text = f"{parsed.month}/{parsed.day}"
        except ValueError:
            pass
        action = ""
        if deadline:
            action = f"{date_text}{(' ' + deadline_time) if deadline_time else ''}前提交"
            if office_no:
                action += f"至内比都{office_no}号办公楼"
        if phones:
            phone_text = "/".join(phones)
            action += ("；" if action else "") + f"咨询 {phone_text}"
        if action:
            result["next_action_summary"] = action
            result["next_action_evidence"] = "S38_OFFICIAL_HTML_SCOPE_DERIVED"

    return result


def _industry_lot_fragments(scope: object) -> list[str]:
    raw = _presentation_cleanup(scope)
    if not raw or "Lot-" not in raw:
        return []
    fragments: list[str] = []
    blocks = re.split(r"(?=Lot-\d+)", raw)
    for block in blocks:
        lot = re.match(r"Lot-(\d+)", block)
        if lot is None:
            continue
        quantity = re.search(r"设备\s*(\d+)类|စက်ပစ္စည်း\s*\((\d+)\)\s*မျိုး", block)
        if quantity is None:
            continue
        quantity_value = quantity.group(1) or quantity.group(2)
        if "ဘိလပ်မြေ" in block:
            category = "水泥实验室设备"
        elif "သံ" in block and "သံမဏိ" in block:
            category = "钢铁实验室设备"
        else:
            category = "实验室设备"
        fragments.append(f"Lot {lot.group(1)}：{category} {quantity_value}类")
    return fragments[:4]


def _deadline_text(item: dict[str, object]) -> str:
    if item.get("deadline_status") == "UNKNOWN" and item.get("action_date"):
        return f"活动日 {item.get('action_date')} {item.get('action_time') or ''}".strip()
    if item.get("deadline_status") == "UNKNOWN":
        return "UNKNOWN"
    value = f"{item.get('deadline') or ''} {item.get('deadline_time') or ''}".strip()
    return value or "UNKNOWN"


def _verified_external_attention(
    items: list[dict[str, object]],
    *,
    now: datetime,
) -> list[dict[str, object]]:
    """Promote date-only tender-form sale ends into digest-only urgency.

    The verified-external record remains non-canonical. Because reviewed S23
    documents currently expose only a sale-end date ("during office hours"),
    the 72h gate is intentionally date-level: it starts 72h before the local
    sale-end date begins and stays active through that calendar date.
    """

    local_now = now.astimezone(DIGEST_TIMEZONE)
    rows: list[dict[str, object]] = []
    for item in items:
        sale_end_raw = str(item.get("tender_form_sale_end") or "").strip()
        if len(sale_end_raw) < 10:
            continue
        try:
            sale_end_date = datetime.strptime(sale_end_raw[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if sale_end_date < local_now.date():
            continue
        sale_end_start = datetime.combine(sale_end_date, datetime.min.time(), tzinfo=DIGEST_TIMEZONE)
        if sale_end_start - local_now > timedelta(hours=72):
            continue
        final_deadline = str(item.get("deadline") or "").strip()
        final_deadline_time = str(item.get("deadline_time") or "").strip()
        rows.append(
            {
                **item,
                "source_id": str(item.get("target_source_id") or item.get("source_id") or ""),
                "scope_excerpt": item.get("business_summary") or item.get("scope_excerpt"),
                "attention_action": "ACT_NOW",
                "attention_reason": "VERIFIED_EXTERNAL_TENDER_FORM_SALE_END_WITHIN_72H_DATE_WINDOW",
                "attention_timing_kind": "TENDER_FORM_SALE_END",
                "deadline": sale_end_date.isoformat(),
                "deadline_time": None,
                "deadline_status": "OPEN",
                "final_bid_deadline": final_deadline,
                "final_bid_deadline_time": final_deadline_time,
            }
        )
    return rows


def _digest_key(digest_date: str) -> str:
    return hashlib.sha256(f"{DIGEST_CHANNEL}|{digest_date}".encode("utf-8")).hexdigest()


def business_digest(
    *,
    database: Path | None = None,
    now: datetime | None = None,
    registry: Registry | None = None,
    audit_network: bool = True,
) -> dict[str, object]:
    target = database or db_path()
    now = (now or datetime.now(UTC)).astimezone(UTC)
    registry = registry or Registry.load()
    cutoff = now - timedelta(hours=24)
    cutoff_iso = _iso(cutoff)
    now_iso = _iso(now)
    local_now = now.astimezone(DIGEST_TIMEZONE)

    briefing = business_briefing(database=target, now=now, registry=registry)
    audit_result = audit(database=target, registry=registry, now=now, network=audit_network)
    scorecard_result = source_scorecard(database=target, now=now, registry=registry, window_days=30)
    try:
        official_review_radar = aggregator_surface_snapshot(
            source_id="S01",
            database=target,
            registry=registry,
            now=now,
            network=audit_network,
        )
    except Exception as exc:
        official_review_radar = {
            "source_id": "S01",
            "status": "CHECK_FAILED",
            "official": 0,
            "covered": 0,
            "missing": [],
            "details": {
                "reason": "DIGEST_RADAR_CHECK_FAILED",
                "error": f"{type(exc).__name__}: {exc}",
                "canonical_truth": False,
            },
        }
    official_review_candidates = _official_review_candidates(official_review_radar)
    review_packet_ready_count = 0

    def ocr_provider(url: str) -> dict[str, object]:
        if not audit_network:
            raise RuntimeError("MANDATORY_DOCUMENT_OCR_DISABLED_WITH_AUDIT_NETWORK_FALSE")
        return acquire_provider_document_ocr(
            database=target,
            url=url,
            timeout_seconds=60,
            max_bytes=8_000_000,
            request_now=now,
        ).result

    for index, candidate in enumerate(official_review_candidates):
        try:
            packet = build_external_official_review_packet(
                candidate,
                ocr_provider=ocr_provider if audit_network else None,
            )
        except Exception as exc:
            packet = {
                "status": "PACKET_BUILD_FAILED",
                "reason": f"{type(exc).__name__}: {exc}",
                "authority": "HUMAN_REVIEW_REQUIRED",
                "production_effect": "NONE",
                "writes": "NONE",
                "review_state": "PENDING_HUMAN_CONFIRMATION",
                "ocr_required": True,
            }
        official_review_candidates[index] = {**candidate, "review_packet": packet}
        if packet.get("status") == "DUAL_EVIDENCE_REVIEW_READY":
            review_packet_ready_count += 1

    with connect(target) as conn:
        run_row = conn.execute(
            """
            SELECT COUNT(*) AS runs,
                   COUNT(DISTINCT source_id) AS sources_polled,
                   COUNT(DISTINCT CASE WHEN changed>0 THEN source_id END) AS sources_changed,
                   COALESCE(SUM(changed),0) AS records_changed,
                   COALESCE(SUM(items_parsed),0) AS items_parsed,
                   COALESCE(SUM(tenders_parsed),0) AS tenders_parsed
            FROM scheduler_runs WHERE started_at>=?
            """,
            (cutoff_iso,),
        ).fetchone()
        evidence_24h = int(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE fetched_at>=?", (cutoff_iso,)).fetchone()[0])
        canonical_total = int(conn.execute("SELECT COUNT(*) FROM canonical_items").fetchone()[0])
        canonical_urls = {
            str(row[0]).rstrip("/")
            for row in conn.execute("SELECT url FROM canonical_items WHERE url IS NOT NULL")
            if row[0]
        }
        signal_total = int(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0])
        signal_rows = conn.execute(
            "SELECT signal_type,COUNT(*) AS n FROM signals WHERE created_at>=? GROUP BY signal_type",
            (cutoff_iso,),
        ).fetchall()
        signal_counts = {str(row["signal_type"]): int(row["n"]) for row in signal_rows}
        signal_24h = sum(signal_counts.values())
        signal_source_rows = conn.execute(
            "SELECT source_id,COUNT(*) AS n FROM signals WHERE created_at>=? GROUP BY source_id ORDER BY n DESC,source_id LIMIT 5",
            (cutoff_iso,),
        ).fetchall()
        business_change_rows = conn.execute(
            """
            SELECT s.canonical_key,s.source_id,s.signal_type,s.created_at,s.payload_json,c.item_kind
            FROM signals s
            JOIN canonical_items c ON c.canonical_key=s.canonical_key
            WHERE s.created_at>=? AND c.item_kind IN ('TENDER','AUCTION_NOTICE')
            ORDER BY s.created_at DESC,s.signal_id DESC
            LIMIT 50
            """,
            (cutoff_iso,),
        ).fetchall()
        business_changes: list[dict[str, object]] = []
        seen_business_keys: set[str] = set()
        for row in business_change_rows:
            canonical_key = str(row["canonical_key"])
            if canonical_key in seen_business_keys:
                continue
            try:
                payload = json.loads(str(row["payload_json"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            mission_input = {**payload, "source_id": str(row["source_id"]), "item_kind": str(row["item_kind"])}
            mission = classify_mission_fit(mission_input)
            if not mission["mission_fit"]:
                continue
            seen_business_keys.add(canonical_key)
            business_changes.append({
                "canonical_key": canonical_key,
                "source_id": str(row["source_id"]),
                "signal_type": str(row["signal_type"]),
                "created_at": str(row["created_at"]),
                "item_kind": str(row["item_kind"]),
                "mission_sector": mission.get("mission_sector"),
                "mission_reason": mission.get("mission_reason"),
                "commercial_event_type": payload.get("commercial_event_type"),
                "commercial_direction": payload.get("commercial_direction"),
                "issuer": str(payload.get("issuer") or ""),
                "title": str(payload.get("title") or payload.get("project_name") or ""),
                "reference_no": payload.get("reference_no"),
                "deadline": payload.get("deadline"),
                "deadline_time": payload.get("deadline_time"),
                "deadline_status": payload.get("deadline_status"),
                "action_date": payload.get("action_date"),
                "action_time": payload.get("action_time"),
                "location": payload.get("location"),
                "quantity_or_lot_summary": payload.get("quantity_or_lot_summary"),
                "next_action_summary": payload.get("next_action_summary"),
                "scope_excerpt": _compact(payload.get("focus_scope_summary") or payload.get("scope_summary") or "", 180),
                "url": str(payload.get("url") or payload.get("attachment_url") or ""),
            })
            if len(business_changes) >= 6:
                break
        strategic_rows = conn.execute(
            """
            SELECT s.source_id,s.signal_type,s.created_at,s.payload_json
            FROM signals s
            JOIN canonical_items c ON c.canonical_key=s.canonical_key
            WHERE s.created_at>=? AND c.item_kind='REGULATORY_NOTICE'
            ORDER BY s.created_at DESC,s.signal_id DESC
            LIMIT 50
            """,
            (cutoff_iso,),
        ).fetchall()
        strategic_notices: list[dict[str, object]] = []
        for row in strategic_rows:
            try:
                payload = json.loads(str(row["payload_json"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or payload.get("business_stage") != "STRATEGIC_INTELLIGENCE":
                continue
            strategic_notices.append({
                "source_id": str(row["source_id"]),
                "signal_type": str(row["signal_type"]),
                "created_at": str(row["created_at"]),
                "title": str(payload.get("title") or payload.get("project_name") or ""),
                "issuer": str(payload.get("issuer") or ""),
                "publication_date": payload.get("publication_date"),
                "telecom_signal_kind": payload.get("telecom_signal_kind"),
                "url": str(payload.get("url") or payload.get("attachment_url") or ""),
            })
            if len(strategic_notices) >= 4:
                break
        alert_total = int(conn.execute("SELECT COUNT(*) FROM delivery_receipts WHERE channel='telegram'").fetchone()[0])
        alert_24h = int(conn.execute("SELECT COUNT(*) FROM delivery_receipts WHERE channel='telegram' AND sent_at>=?", (cutoff_iso,)).fetchone()[0])
        digest_total = int(conn.execute("SELECT COUNT(*) FROM digest_delivery_receipts WHERE channel=?", (DIGEST_CHANNEL,)).fetchone()[0])

    health = audit_result.get("checks", {}).get("source_health", {}) if isinstance(audit_result.get("checks"), dict) else {}
    monitored = len(registry.enabled_sources())
    non_green = int(health.get("non_green_sources") or 0) if isinstance(health, dict) else monitored
    green = max(0, monitored - non_green)
    qcounts = briefing.get("qualification_counts") or {}
    priority_counts = qcounts.get("priority_band") if isinstance(qcounts, dict) else {}
    if not isinstance(priority_counts, dict):
        priority_counts = {}
    attention = briefing.get("attention") or []
    if not isinstance(attention, list):
        attention = []
    attention = [
        _industry_actionability_overlay(item) if isinstance(item, dict) else item
        for item in attention
    ]
    business_changes = [
        _industry_actionability_overlay(item) if isinstance(item, dict) else item
        for item in business_changes
    ]
    watchlist = briefing.get("watchlist") or {}
    if not isinstance(watchlist, dict):
        watchlist = {}
    else:
        watchlist = dict(watchlist)
        watch_items = watchlist.get("items") or []
        if isinstance(watch_items, list):
            watchlist["items"] = [
                _industry_actionability_overlay(item) if isinstance(item, dict) else item
                for item in watch_items
            ]

    checks = audit_result.get("checks") or {}
    if not isinstance(checks, dict):
        checks = {}
    strategic = checks.get("strategic_coverage") or {}
    if not isinstance(strategic, dict):
        strategic = {}
    s13 = strategic.get("S13") or {}
    s41 = strategic.get("S41") or {}
    atom = checks.get("atom_surface_trigger") or {}
    coverage_gaps = reviewed_coverage_gaps(now=now)
    verified_external: list[dict[str, object]] = []
    for raw in verified_external_opportunities(now=now):
        url = str(raw.get("url") or "")
        if url.rstrip("/") in canonical_urls:
            continue
        mission = classify_mission_fit({
            **raw,
            "source_id": str(raw.get("target_source_id") or raw.get("source_id") or ""),
            "item_kind": str(raw.get("item_kind") or "TENDER"),
            "scope_summary": raw.get("business_summary"),
        })
        if not mission["mission_fit"]:
            continue
        verified_external.append({**raw, **mission})

    external_attention = _verified_external_attention(verified_external, now=now)
    if external_attention:
        attention = external_attention + attention
    attention_action_counts = dict(briefing.get("attention_action_counts") or {})
    for item in external_attention:
        action = str(item.get("attention_action") or "REVIEW")
        attention_action_counts[action] = int(attention_action_counts.get(action) or 0) + 1

    canonical_current = int(briefing.get("current_opportunities") or 0)
    business_current = canonical_current + len(verified_external)
    business_current_counts = dict(briefing.get("current_counts") or {})
    business_current_counts["OPEN"] = int(business_current_counts.get("OPEN") or 0) + len(verified_external)
    mission_sector_counts = dict(briefing.get("mission_sector_counts") or {})
    priority_counts = dict(priority_counts)
    for item in verified_external:
        sector = str(item.get("mission_sector") or "OTHER")
        mission_sector_counts[sector] = int(mission_sector_counts.get(sector) or 0) + 1
        priority = str(item.get("priority_band") or "REVIEW")
        priority_counts[priority] = int(priority_counts.get(priority) or 0) + 1

    return {
        "status": "PASS",
        "digest_version": DIGEST_VERSION,
        "digest_date": local_now.date().isoformat(),
        "timezone": "Asia/Yangon",
        "as_of": now_iso,
        "window": {"hours": 24, "start": cutoff_iso, "end": now_iso},
        "sources": {
            "monitored": monitored,
            "green": green,
            "non_green": non_green,
            "polled_24h": int(run_row["sources_polled"] or 0),
            "changed_24h": int(run_row["sources_changed"] or 0),
        },
        "activity_24h": {
            "scheduler_runs": int(run_row["runs"] or 0),
            "records_changed": int(run_row["records_changed"] or 0),
            "items_parsed": int(run_row["items_parsed"] or 0),
            "tenders_parsed": int(run_row["tenders_parsed"] or 0),
            "evidence_fetched": evidence_24h,
            "signals": signal_24h,
            "new_signals": int(signal_counts.get("NEW", 0)),
            "updated_signals": int(signal_counts.get("UPDATED", 0)),
            "signal_sources": [{"source_id": str(row["source_id"]), "count": int(row["n"])} for row in signal_source_rows],
            "business_changes": business_changes,
            "strategic_notices": strategic_notices,
        },
        "pipeline_totals": {
            "canonical_items": canonical_total,
            "signals": signal_total,
            "telegram_alerts": alert_total,
            "telegram_alerts_24h": alert_24h,
            "telegram_digests": digest_total,
        },
        "source_yield": scorecard_result.get("summary") or {},
        "business": {
            "current_opportunities": business_current,
            "canonical_current_opportunities": canonical_current,
            "verified_external_opportunity_count": len(verified_external),
            "verified_external_opportunities": verified_external,
            "verified_external_policy": "OFFICIAL_ISSUER_DOCUMENT_REVIEWED_NON_CANONICAL_BUSINESS_COVERAGE",
            "current_counts": business_current_counts,
            "canonical_current_counts": briefing.get("current_counts"),
            "tracked_opportunities": briefing.get("tracked_opportunities", briefing.get("current_opportunities")),
            "mission_excluded_count": briefing.get("mission_excluded_count", 0),
            "mission_sector_counts": dict(sorted(mission_sector_counts.items())),
            "mission_policy_version": briefing.get("mission_policy_version"),
            "qualification_counts": qcounts,
            "priority_counts": priority_counts,
            "attention_count": len(attention),
            "attention_action_counts": attention_action_counts,
            "attention": attention,
            "watchlist_count": int(watchlist.get("count") or 0),
            "watchlist_relevance": watchlist.get("primary_relevance_counts") or {},
            "watchlist_items": watchlist.get("items") or [],
            "watchlist_delivery_policy": "VALID_MEDIUM_NOT_IMMEDIATE_ALERT; escalates on strategic fit or <=72h urgency",
            "manual_promotions": briefing.get("manual_promotions") or {"count": 0, "items": []},
            "assurance": briefing.get("assurance") or {"open_misses": 0, "open_red_misses": 0, "coverage_risk_count": 0, "coverage_risks": [], "metric_validity": "NOT_RUN"},
            "coverage_gap_count": len(coverage_gaps),
            "coverage_gaps": coverage_gaps,
            "coverage_gap_policy": "REVIEWED_READ_ONLY_OUTSIDE_CANONICAL_SIGNAL_PIPELINE",
            "official_review_candidate_count": len(official_review_candidates),
            "official_review_candidates": official_review_candidates,
            "official_review_packet_ready_count": review_packet_ready_count,
            "official_review_radar_status": str(official_review_radar.get("status") or "UNPROVEN"),
            "official_review_radar_policy": "FRESH_S01_AGGREGATOR_ONLY_NONCANONICAL_REVIEW_REQUIRED",
        },
        "auditor": {
            "status": audit_result.get("status"),
            "finding_count": audit_result.get("finding_count"),
            "mpt": s13,
            "mytel": s41,
            "atom": atom,
            "external_completeness": (audit_result.get("assurance") or {}).get("external_completeness") if isinstance(audit_result.get("assurance"), dict) else None,
        },
    }


def render_business_digest(
    digest: dict[str, object],
    *,
    translator: TranslationBatch | None = None,
) -> str:
    sources = digest.get("sources") or {}
    activity = digest.get("activity_24h") or {}
    totals = digest.get("pipeline_totals") or {}
    business = digest.get("business") or {}
    auditor = digest.get("auditor") or {}
    source_yield = digest.get("source_yield") or {}
    assert isinstance(sources, dict) and isinstance(activity, dict) and isinstance(totals, dict) and isinstance(business, dict) and isinstance(auditor, dict) and isinstance(source_yield, dict)

    priorities = business.get("priority_counts") or {}
    if not isinstance(priorities, dict):
        priorities = {}
    qualification_counts = business.get("qualification_counts") or {}
    if not isinstance(qualification_counts, dict):
        qualification_counts = {}
    quality_counts = qualification_counts.get("signal_quality_band") or {}
    if not isinstance(quality_counts, dict):
        quality_counts = {}
    attention = business.get("attention") or []
    if not isinstance(attention, list):
        attention = []

    yield_states = source_yield.get("yield_states") or {}
    if not isinstance(yield_states, dict):
        yield_states = {}

    business_changes = activity.get("business_changes") or []
    if not isinstance(business_changes, list):
        business_changes = []
    coverage_gaps = business.get("coverage_gaps") or []
    if not isinstance(coverage_gaps, list):
        coverage_gaps = []
    official_review_candidates = business.get("official_review_candidates") or []
    if not isinstance(official_review_candidates, list):
        official_review_candidates = []
    official_review_radar_status = str(business.get("official_review_radar_status") or "UNPROVEN")
    verified_external = business.get("verified_external_opportunities") or []
    if not isinstance(verified_external, list):
        verified_external = []
    watch_items = business.get("watchlist_items") or []
    if not isinstance(watch_items, list):
        watch_items = []
    manual_promotions = business.get("manual_promotions") or {}
    if not isinstance(manual_promotions, dict):
        manual_promotions = {}
    manual_items = manual_promotions.get("items") or []
    if not isinstance(manual_items, list):
        manual_items = []
    assurance = business.get("assurance") or {}
    if not isinstance(assurance, dict):
        assurance = {}
    coverage_risks = assurance.get("coverage_risks") or []
    if not isinstance(coverage_risks, list):
        coverage_risks = []
    strategic_notices = activity.get("strategic_notices") or []
    if not isinstance(strategic_notices, list):
        strategic_notices = []

    translate_batch = translator or translate_myanmar_to_zh_hans
    digest_was_translated = False

    def business_subject(item: dict[str, object]) -> str:
        title = _presentation_cleanup(item.get("title"))
        scope = _presentation_cleanup(item.get("scope_excerpt"))
        quantity = _presentation_cleanup(item.get("quantity_or_lot_summary"))
        source_id = str(item.get("source_id") or "")
        if source_id == "S08A" and item.get("reviewed_enrichment_status") and scope:
            return _compact(scope, 180)
        if source_id == "S22" and str(item.get("canonical_key") or "") == "iwt:1038:2026-08-25":
            return "Coastal Cargo Vessel ×1艘"
        if source_id == "S47" and scope:
            return _compact(scope, 240)
        if source_id == "S30":
            mofa_summary = _mofa_business_summary(scope)
            if mofa_summary:
                return _compact(mofa_summary, 240)
        if source_id == "S20":
            moep_summary = _moep_business_summary(scope)
            if moep_summary:
                return _compact(moep_summary, 240)
        industry_lots = _industry_lot_fragments(scope) if source_id == "S38" else []
        if industry_lots:
            return _compact("；".join(industry_lots), 240)
        industry_products = _industry_scope_product_fragments(scope) if source_id == "S38" else []
        if industry_products and str(item.get("mission_sector") or "") == "ENGINEERING":
            engineering_products = [
                value for value in industry_products
                if value.startswith(("Electrical ", "Mechanical "))
            ]
            if engineering_products:
                industry_products = engineering_products
        if industry_products:
            return _compact("；".join(industry_products), 240)
        fragments = _scope_product_fragments(scope)
        if fragments:
            summary = "；".join(fragments)
            if quantity and quantity not in summary:
                summary = f"{summary}；规模 {quantity}"
            return _compact(summary, 240)

        title_fragments = _title_product_fragments(title)
        if title_fragments:
            return _compact("；".join(title_fragments), 240)

        # DOMS scan-only attachment details may be supplied by a reviewed OCR read-model overlay.
        if source_id == "S26" and item.get("reviewed_enrichment_status") and scope:
            return _compact(scope, 300)
        # Some issuer pages expose only attachment/tender identifiers. Do not
        # pretend that a reference number is a useful procurement summary.
        if source_id == "S26" and scope and re.search(r"DMS/?\d*[-/()]", scope, re.IGNORECASE):
            return "采购明细尚未从官方附件抽取；当前仅识别招标编号，需打开附件核验具体物资与数量"

        parts: list[str] = []
        if title:
            parts.append(title)
        if quantity and quantity not in title:
            parts.append(f"规模 {quantity}")
        if not parts and scope:
            parts.append(scope)
        return _compact("；".join(parts) or "采购/招标内容待补充", 220)

    def translate_values(values: list[str], limit: int) -> list[str]:
        nonlocal digest_was_translated
        if not values or not any(contains_myanmar(value) for value in values):
            return [_compact(_presentation_cleanup(value), limit) for value in values]
        myanmar_indices = [index for index, value in enumerate(values) if contains_myanmar(value)]
        if len(myanmar_indices) <= 2:
            translated, used = translate_batch(values)
            digest_was_translated = digest_was_translated or used
            return [_compact(_presentation_cleanup(value), limit) for value in translated]

        translated_values = list(values)
        for offset in range(0, len(myanmar_indices), 2):
            indices = myanmar_indices[offset : offset + 2]
            batch = [values[index] for index in indices]
            translated, used = translate_batch(batch)
            digest_was_translated = digest_was_translated or used
            if not used or len(translated) != len(indices):
                continue
            for index, value in zip(indices, translated, strict=True):
                translated_values[index] = value
        return [_compact(_presentation_cleanup(value), limit) for value in translated_values]

    def translated_subjects(rows: list[dict[str, object]]) -> list[str]:
        return translate_values([business_subject(item) for item in rows], 260)

    def translated_issuers(rows: list[dict[str, object]]) -> list[str]:
        values: list[str] = []
        for item in rows:
            issuer = str(item.get("issuer") or "")
            source_id = str(item.get("source_id") or "")
            if source_id == "S08A":
                issuer = "Myanmar Customs"
            elif source_id == "S22":
                issuer = "IWT"
            elif source_id == "S26":
                issuer = "DOMS / Ministry of Health"
            elif source_id == "S30":
                issuer = "MOFA"
            elif source_id == "S38":
                issuer = "Ministry of Industry"
            elif source_id == "S39":
                issuer = "Ministry of Energy"
            elif source_id == "S20":
                upper = issuer.upper()
                if "DPTSC" in upper:
                    issuer = "MOEP / DPTSC"
                elif "EPGE" in upper:
                    issuer = "MOEP / EPGE"
                elif "YESC" in upper:
                    issuer = "MOEP / YESC"
                else:
                    issuer = "MOEP"
            values.append(issuer)
        return translate_values(values, 46)


    def official_link(url: object, label: str = "官方") -> str:
        value = str(url or "")
        if not value.startswith("https://") or len(value) > 140:
            return ""
        return f' · <a href="{html.escape(value, quote=True)}">{label}</a>'

    def action_label(action: object) -> str:
        return {
            "ACT_NOW": "现在处理",
            "PRIORITIZE": "优先跟进",
            "REVIEW": "人工核验",
        }.get(str(action or ""), "关注")

    def business_label(item: dict[str, object]) -> str:
        kind = str(item.get("item_kind") or "")
        direction = str(item.get("commercial_direction") or "")
        if kind == "TENDER":
            return "采购内容"
        if kind == "AUCTION_NOTICE" and direction == "BUY_FROM_ISSUER":
            return "竞买内容"
        if kind == "AUCTION_NOTICE":
            return "竞买内容"
        return "业务内容"

    def timing_text(item: dict[str, object]) -> str:
        if item.get("attention_timing_kind") == "TENDER_FORM_SALE_END":
            sale_end = _deadline_text(item)
            final_deadline = f"{item.get('final_bid_deadline') or ''} {item.get('final_bid_deadline_time') or ''}".strip()
            suffix = f" · 投标截止 {final_deadline}" if final_deadline else ""
            return f"售标截止 {sale_end}{suffix}"
        value = _deadline_text(item)
        if value.startswith("活动日"):
            return value
        return f"截止 {value}"

    lines = [
        "📊 <b>SignalForge Myanmar 重点招投标</b>",
        f"🗓 {html.escape(str(digest.get('digest_date') or ''))} · 政府/国企 · 工程/建设/通讯/能源 · 当前+24h变化",
    ]

    all_attention_rows = [item for item in attention if isinstance(item, dict)]
    attention_rows = all_attention_rows
    attention_keys = {str(item.get("canonical_key") or "") for item in attention_rows if item.get("canonical_key")}
    attention_external_gap_ids = {
        str(item.get("gap_id")) for item in attention_rows if item.get("gap_id")
    }
    if attention_rows:
        attention_issuers = translated_issuers(attention_rows)
        attention_subjects = translated_subjects(attention_rows)
        attention_locations = translate_values([str(item.get("location") or "") for item in attention_rows], 38)
        attention_actions = translate_values([str(item.get("next_action_summary") or "") for item in attention_rows], 72)
        total_attention = len([item for item in attention if isinstance(item, dict)])
        shown = len(attention_rows)
        suffix = f"（展示前 {shown} 条）" if total_attention > shown else ""
        lines.extend(["", f"<b>🔥 今天先看：{total_attention} 条需处理{suffix}</b>"])
        icons = {"ACT_NOW": "🔴", "PRIORITIZE": "🟠", "REVIEW": "🟡"}
        for index, item in enumerate(attention_rows):
            action = str(item.get("attention_action") or "REVIEW")
            source_id = html.escape(str(item.get("source_id") or "?"))
            issuer = html.escape(attention_issuers[index])
            subject = html.escape(attention_subjects[index])
            icon = icons.get(action, "•")
            lines.append(f"{icon} <b>{issuer}</b> · [{source_id}] · {action_label(action)}")
            lines.append(f"   {business_label(item)}：<b>{subject}</b>")
            meta = [timing_text(item)]
            location = attention_locations[index]
            if location:
                meta.append(f"地点 {location}")
            reference = _compact(item.get("reference_no"), 28)
            if reference and source_id != "S08A":
                meta.append(f"Ref {reference}")
            focus_count = int(item.get("focus_reference_count") or 0)
            if focus_count:
                meta.append(f"相关分包 {focus_count}")
            next_action = attention_actions[index]
            if next_action:
                meta.append(f"下一步 {next_action}")
            link = official_link(item.get("url"))
            lines.append("   " + html.escape(" · ".join(meta)) + link)

    change_rows = [
        item for item in business_changes
        if isinstance(item, dict) and str(item.get("canonical_key")) not in attention_keys
    ][:3]
    change_keys = {str(item.get("canonical_key")) for item in change_rows}
    if change_rows:
        change_issuers = translated_issuers(change_rows)
        change_subjects = translated_subjects(change_rows)
        lines.extend(["", f"<b>🆕 24h 新增/更新：{len(change_rows)} 条（未在上方重复）</b>"])
        for index, item in enumerate(change_rows):
            source_id = html.escape(str(item.get("source_id") or "?"))
            issuer = html.escape(change_issuers[index])
            subject = html.escape(change_subjects[index])
            signal_type = html.escape(str(item.get("signal_type") or ""))
            meta = [timing_text(item)]
            location = _compact(item.get("location"), 32)
            if location:
                meta.append(f"地点 {location}")
            reference = _compact(item.get("reference_no"), 28)
            if reference and source_id != "S08A":
                meta.append(f"Ref {reference}")
            link = official_link(item.get("url"))
            lines.append(f"• <b>{issuer}</b> · [{source_id}] · {signal_type}")
            lines.append(f"   {business_label(item)}：<b>{subject}</b>")
            lines.append("   " + html.escape(" · ".join(meta)) + link)

    risk_rows = [item for item in coverage_risks[:3] if isinstance(item, dict)]
    if risk_rows:
        lines.extend(["", "<b>⚠️ 覆盖风险</b>"])
        for risk in risk_rows:
            source_id = html.escape(str(risk.get("source_id") or "?"))
            source_name = html.escape(str(risk.get("source_name") or source_id))
            if risk.get("risk_kind") == "BUSINESS_DETAIL_GAP":
                affected = int(risk.get("affected_current_opportunities") or 0)
                recovered = int(risk.get("reviewed_official_recovery_count") or 0)
                recovery_text = f"；另有 <b>{recovered}</b> 条已通过 MOI/Kyemon 官方报纸补足关键商务字段" if recovered else ""
                lines.append(
                    f"• <b>{source_name}</b> · [{source_id}]：已发现招标事件，但 <b>{affected}</b> 条当前机会仍缺少截止/投标细节{recovery_text}；官方附件通道当前为 HTTP 404 降级。"
                )
                continue
            if risk.get("risk_kind") == "ISSUER_DISCOVERY_PARTIAL":
                recovered = int(risk.get("verified_external_recovery_count") or 0)
                lines.append(
                    f"• <b>{source_name}</b> · [{source_id}]：已通过外部官方文件补获 <b>{recovered}</b> 条当前机会；issuer sitemap 未覆盖该机会，官网采购发现覆盖仍为 <b>PARTIAL</b>。"
                )
                continue
            proven_through = str(risk.get("last_success_at") or "")
            proven_date = html.escape(proven_through.split("T", 1)[0]) if proven_through else "未知"
            open_count = risk.get("retained_open_tender_count")
            latest_publication = html.escape(str(risk.get("latest_retained_tender_publication_date") or ""))
            latest_deadline = html.escape(str(risk.get("latest_retained_tender_deadline") or ""))
            if isinstance(open_count, int) and latest_publication:
                retained = f"留存记录中当前开放 <b>{open_count}</b> 条；最新已知发布 <b>{latest_publication}</b>"
                if latest_deadline:
                    retained += f"，最晚已知截止 <b>{latest_deadline}</b>"
                if proven_through:
                    lines.append(
                        f"• <b>{source_name}</b> · [{source_id}]：{retained}；官网采集可验证到 <b>{proven_date}</b>，之后新发布无法确认。"
                    )
                else:
                    lines.append(
                        f"• <b>{source_name}</b> · [{source_id}]：{retained}；当前采集覆盖无法验证，新发布无法确认。"
                    )
            elif proven_through:
                lines.append(f"• <b>{source_name}</b> · [{source_id}]：采集覆盖最近可验证到 <b>{proven_date}</b>；之后新招标无法确认。")
            else:
                lines.append(f"• <b>{source_name}</b> · [{source_id}]：最近可验证采集时间未知；当前无法证明没有新招标。")
        lines.append("<i>覆盖风险可能是“新发布不可验证”，也可能是“事件已发现但关键商务字段未证明”；均不等于已确认漏报。</i>")

    if official_review_radar_status == "CHECK_FAILED":
        lines.extend([
            "",
            "<b>⚠️ S01 官方线索雷达检查失败</b>",
            "<i>今日 National Portal 外部官方线索完整性不可确认；不据此判断“没有新机会”。</i>",
        ])

    if official_review_candidates:
        review_rows = [item for item in official_review_candidates[:2] if isinstance(item, dict)]
        review_agencies = translate_values([str(item.get("agency") or "") for item in review_rows], 34)
        review_titles = translate_values([str(item.get("title") or "") for item in review_rows], 110)
        ready_count = int(business.get("official_review_packet_ready_count") or 0)
        lines.extend(["", f"<b>🕵️ 待核验官方线索：{len(official_review_candidates)} 条（预审就绪 {ready_count} · 展示前 {len(review_rows)} 条）</b>"])
        for index, item in enumerate(review_rows):
            target_source = html.escape(str(item.get("target_source_hint") or "?"))
            agency = html.escape(review_agencies[index])
            title = html.escape(review_titles[index])
            closing_hint = html.escape(str(item.get("closing_date_hint") or "未知"))
            document_url = str(item.get("url") or "")
            document_link = (
                f' · <a href="{html.escape(document_url, quote=True)}">候选文件</a>'
                if len(document_url) <= 320 and document_url.startswith("https://myanmar.gov.mm/documents/")
                else official_link("https://myanmar.gov.mm/tenders", "官方Portal")
            )
            lines.append(f"• <b>{agency}</b> · [{target_source} ← S01] · 人工核验")
            lines.append(f"   线索：<b>{title}</b> · 截止提示 <b>{closing_hint}</b>{document_link}")
            packet = item.get("review_packet") or {}
            if isinstance(packet, dict):
                packet_status = str(packet.get("status") or "")
                fields = packet.get("proposed_fields") or {}
                if not isinstance(fields, dict):
                    fields = {}
                reconciliation = packet.get("reconciliation") or {}
                if not isinstance(reconciliation, dict):
                    reconciliation = {}
                scope_raw = str(fields.get("scope_excerpt") or "")
                scope_text = translate_values([scope_raw], 100)[0] if scope_raw else ""
                if packet_status == "DUAL_EVIDENCE_REVIEW_READY":
                    location = _compact(fields.get("project_location_hint"), 36)
                    next_action = _compact(fields.get("next_action_summary"), 120)
                    sha = str(packet.get("document_sha256") or "")[:12]
                    confidence = packet.get("ocr_mean_confidence")
                    meta = ["Native+OCR 双证据", "SHA A=B=C"]
                    if isinstance(confidence, (int, float)):
                        meta.append(f"OCR {float(confidence):.1f}%")
                    if sha:
                        meta.append(f"SHA {sha}…")
                    if location:
                        meta.append(f"地点 {location}")
                    lines.append("   预审：" + html.escape(" · ".join(meta)))
                    if scope_text:
                        lines.append(f"   范围：{html.escape(scope_text)}")
                    if next_action:
                        lines.append(f"   建议动作：{html.escape(next_action)}")
                elif packet_status == "DUAL_EVIDENCE_CONFLICT":
                    conflicts = reconciliation.get("conflict_fields") or []
                    conflict_text = ", ".join(str(value) for value in conflicts[:3]) if isinstance(conflicts, list) else "关键字段"
                    lines.append(f"   预审：⚠️ Native/OCR 冲突（{html.escape(conflict_text or '关键字段')}），必须人工核验")
                    field_evidence = reconciliation.get("field_evidence") or {}
                    if isinstance(field_evidence, dict):
                        for key in (conflicts[:2] if isinstance(conflicts, list) else []):
                            evidence = field_evidence.get(key) or {}
                            if isinstance(evidence, dict):
                                native = _compact(evidence.get("native"), 32) or "—"
                                ocr = _compact(evidence.get("ocr"), 32) or "—"
                                lines.append(f"   冲突 {html.escape(str(key))}：Native {html.escape(native)} / OCR {html.escape(ocr)}")
                elif packet_status == "DUAL_EVIDENCE_REVIEW_REQUIRED":
                    single = []
                    for key in ("native_only_fields", "ocr_only_fields"):
                        values = reconciliation.get(key) or []
                        if isinstance(values, list):
                            single.extend(str(value) for value in values)
                    lines.append("   预审：OCR 已完成，但关键字段尚未全部获得双证据确认；需人工核验" + (f"（{html.escape(', '.join(single[:3]))}）" if single else ""))
                elif packet_status == "OCR_ONLY_REVIEW_PACKET":
                    deadline = _compact(fields.get("proposed_deadline"), 24)
                    suffix = f"；OCR 提示截止 {html.escape(deadline)}" if deadline else ""
                    lines.append(f"   预审：扫描件/文本层不足，仅有 OCR 证据，必须人工确认{suffix}")
                elif packet_status == "OCR_PAGE_LIMIT_REVIEW_REQUIRED":
                    lines.append(f"   预审：OCR 未覆盖全部 PDF 页（{html.escape(str(packet.get('ocr_processed_pages') or '?'))}/{html.escape(str(packet.get('ocr_page_count') or '?'))}），不得标记就绪")
                elif packet_status == "EVIDENCE_SHA_CONFLICT":
                    lines.append("   预审：⚠️ Native / Provider fetch / OCR 的 PDF SHA 不一致，证据链冲突，必须人工核验")
                elif packet_status == "PARTIAL_REVIEW_PACKET":
                    lines.append("   预审：Native+OCR 已完成，但该机构模板语义尚未核验；不自动解释编号日期")
                    if scope_text:
                        lines.append(f"   范围证据：{html.escape(scope_text)}")
                elif packet_status in {"OCR_REQUIRED_FAILED", "OCR_REQUIRED_NOT_AVAILABLE"}:
                    lines.append("   预审：⚠️ 强制 OCR 未完成；Native text 不得单独作为 review-ready 证据")
                elif packet_status in {"PACKET_BUILD_FAILED", "REJECTED_INPUT"}:
                    lines.append(f"   预审：{html.escape(packet_status)}，请人工打开候选文件")
        lines.append("<i>所有进入审核面的 mission PDF 必须完成视觉 OCR；预审字段均为 proposed evidence。必须人工确认后才可升级，当前不计入机会数，也不作为 canonical Signal。</i>")

    if verified_external:
        verified_candidates = [item for item in verified_external if isinstance(item, dict)]
        promoted_external_count = sum(
            1 for item in verified_candidates
            if item.get("gap_id") and str(item.get("gap_id")) in attention_external_gap_ids
        )
        verified_rows = [
            item for item in verified_candidates
            if not item.get("gap_id") or str(item.get("gap_id")) not in attention_external_gap_ids
        ][:4]
        verified_issuers = translate_values([str(item.get("issuer") or "") for item in verified_rows], 34)
        verified_titles = translate_values([str(item.get("business_summary") or item.get("title") or "") for item in verified_rows], 120)
        verified_locations = translate_values([str(item.get("location") or "") for item in verified_rows], 24)
        total_verified = len(verified_candidates)
        if promoted_external_count and verified_rows:
            heading = f"<b>✅ 外部官方文件核验：{total_verified} 条（{promoted_external_count}条已在上方，以下{len(verified_rows)}条）</b>"
        elif promoted_external_count:
            heading = f"<b>✅ 外部官方文件核验：{total_verified} 条（已在上方‘今天先看’展示）</b>"
        else:
            heading = f"<b>✅ 外部官方文件核验：{total_verified} 条</b>"
        lines.extend(["", heading])
        for index, item in enumerate(verified_rows):
            target_source = html.escape(str(item.get("target_source_id") or item.get("source_id") or ""))
            origin = html.escape(str(item.get("coverage_origin") or ""))
            issuer = html.escape(verified_issuers[index])
            title = html.escape(verified_titles[index])
            location = html.escape(verified_locations[index])
            deadline = html.escape(
                f"{item.get('deadline') or ''} {item.get('deadline_time') or ''}".strip()
            )
            next_action = html.escape(_compact(item.get("next_action_summary"), 70))
            url = str(item.get("url") or "")
            link = official_link(url, "官方PDF") if url.startswith((
                "https://myanmar.gov.mm/",
                "https://www.myanmar.gov.mm/",
                "https://construction.gov.mm/",
            )) else ""
            provenance = f"[{target_source} ← {origin}]" if origin else f"[{target_source}]"
            lines.append(f"• <b>{issuer}</b> · {provenance}")
            detail = f"   工程/采购内容：<b>{title}</b> · {location} · 截止 <b>{deadline}</b>{link}"
            if next_action:
                detail += f" · 下一步 {next_action}"
            lines.append(detail)
        lines.append("<i>已计入目标机会；官方机构文件已核验，但不伪装成 canonical Signal。</i>")

    if coverage_gaps:
        lines.extend(["", "<b>⚠️ 人工核验机会（尚未形成可计入的官方覆盖）</b>"])
        gap_rows = [gap for gap in coverage_gaps[:4] if isinstance(gap, dict)]
        gap_issuers = translate_values([str(gap.get("issuer") or "") for gap in gap_rows], 34)
        gap_titles = translate_values([str(gap.get("business_summary") or gap.get("title") or "") for gap in gap_rows], 110)
        gap_locations = translate_values([str(gap.get("location") or "") for gap in gap_rows], 24)
        for index, gap in enumerate(gap_rows):
            source_id = html.escape(str(gap.get("source_id") or ""))
            issuer = html.escape(gap_issuers[index])
            title = html.escape(gap_titles[index])
            deadline = html.escape(
                f"{gap.get('deadline') or ''} {gap.get('deadline_time') or ''}".strip()
            )
            location = html.escape(gap_locations[index])
            url = str(gap.get("url") or "")
            allowed_gap_link = url.startswith((
                "https://construction.gov.mm/",
                "https://myanmar.gov.mm/documents/",
                "https://www.myanmar.gov.mm/documents/",
            ))
            if url.startswith("https://construction.gov.mm/letter-download/"):
                display_url = "https://construction.gov.mm/"
            elif url.startswith((
                "https://myanmar.gov.mm/documents/",
                "https://www.myanmar.gov.mm/documents/",
            )):
                display_url = "https://myanmar.gov.mm/tenders"
            else:
                display_url = url
            link = official_link(display_url, "官方记录") if allowed_gap_link else ""
            next_action = _compact(gap.get("next_action_summary"), 60)
            lines.append(f"• <b>{issuer}</b> · [{source_id}]")
            detail = f"   工程/采购内容：<b>{title}</b> · {location} · 截止 <b>{deadline}</b>{link}"
            if next_action:
                detail += f" · 下一步 {html.escape(next_action)}"
            lines.append(detail)
        lines.append("<i>仍属 coverage gap，不计入目标机会数。</i>")

    manual_rows = [item for item in manual_items[:3] if isinstance(item, dict)]
    if manual_rows:
        manual_titles = translate_values([str(item.get("title") or "") for item in manual_rows], 100)
        manual_summaries = translate_values([str(item.get("summary") or "") for item in manual_rows], 160)
        manual_reasons = translate_values([str(item.get("reason") or "") for item in manual_rows], 90)
        lines.extend(["", f"<b>🧑 人工升级：{int(manual_promotions.get('count') or len(manual_rows))} 条</b>"])
        for index, item in enumerate(manual_rows):
            source_id = html.escape(str(item.get("source_id") or "MANUAL"))
            priority = html.escape(str(item.get("priority_band") or "HIGH"))
            title = html.escape(manual_titles[index])
            summary = html.escape(manual_summaries[index])
            reason = html.escape(manual_reasons[index])
            lines.append(f"• [{source_id}] <b>{title}</b> · {priority} · <i>非标准化人工升级</i>")
            if summary:
                lines.append(f"   内容：{summary}")
            meta: list[str] = []
            if item.get("deadline"):
                meta.append(f"截止 {item.get('deadline')}")
            if item.get("location"):
                meta.append(f"地点 {_compact(item.get('location'), 34)}")
            if reason:
                meta.append(f"升级原因 {reason}")
            link = official_link(item.get("url"), "来源")
            if meta or link:
                lines.append("   " + html.escape(" · ".join(meta)) + link)

    raw_watch_count = int(business.get("watchlist_count") or 0)
    watch_rows = [
        item for item in watch_items
        if isinstance(item, dict)
        and str(item.get("canonical_key")) not in attention_keys
        and str(item.get("canonical_key")) not in change_keys
    ]
    watch_count = len(watch_rows)
    if watch_rows:
        watch_issuers = translated_issuers(watch_rows)
        watch_subjects = translated_subjects(watch_rows)
        lines.extend(["", f"<b>🟡 后续跟进：{watch_count} 条 MEDIUM</b>"])
        for index, item in enumerate(watch_rows):
            source_id = html.escape(str(item.get("source_id") or "?"))
            issuer = html.escape(watch_issuers[index])
            subject = html.escape(_compact(watch_subjects[index], 132))
            deadline = html.escape(timing_text(item))
            lines.append(f"• [{source_id}] <b>{issuer}</b> · {subject} · {deadline}")

    elif raw_watch_count and not watch_items:
        lines.extend(["", f"🟡 后续跟进：{raw_watch_count} 条 MEDIUM"])

    if strategic_notices:
        lines.extend(["", "<b>📡 战略动态</b>"])
        strategic_rows = [notice for notice in strategic_notices[:3] if isinstance(notice, dict)]
        strategic_titles = translate_values([str(notice.get("title") or "") for notice in strategic_rows], 125)
        for index, notice in enumerate(strategic_rows):
            source_id = html.escape(str(notice.get("source_id") or ""))
            date = html.escape(str(notice.get("publication_date") or ""))
            kind = html.escape(str(notice.get("telecom_signal_kind") or "STRATEGIC_INTELLIGENCE"))
            title = html.escape(strategic_titles[index])
            url = str(notice.get("url") or "")
            link = f' · <a href="{html.escape(url, quote=True)}">官方详情</a>' if url.startswith("https://") else ""
            lines.append(f"• [{source_id}] {date} · <b>{title}</b> · {kind}{link}")

    current = int(business.get("current_opportunities") or 0)
    canonical_current = int(business.get("canonical_current_opportunities") or current)
    verified_count = int(business.get("verified_external_opportunity_count") or 0)
    tracked = int(business.get("tracked_opportunities") or canonical_current)
    mix = f"（canonical {canonical_current} + 外部官方核验 {verified_count}）" if verified_count else ""
    tracked_suffix = f" · canonical后台 {tracked}" if tracked != canonical_current else ""
    lines.extend([
        "",
        f"<b>📌 业务概览</b>：目标内 <b>{current}</b> 个机会{mix}{tracked_suffix} · HIGH {priorities.get('HIGH', 0)} · MEDIUM {priorities.get('MEDIUM', 0)} · REVIEW {priorities.get('REVIEW', 0)}",
    ])
    if digest_was_translated:
        lines.append("🌐 缅文内容已机器翻译为中文（事实以官方原文为准）")

    text = "\n".join(lines)
    if len(text) > TELEGRAM_MESSAGE_LIMIT:
        kept: list[str] = []
        for line in lines:
            candidate = "\n".join([*kept, line])
            if len(candidate) + 2 > TELEGRAM_MESSAGE_LIMIT:
                break
            kept.append(line)
        while kept and len("\n".join([*kept, "…"])) > TELEGRAM_MESSAGE_LIMIT:
            kept.pop()
        text = "\n".join([*kept, "…"])
    return text


def telegram_digest(
    *,
    database: Path | None = None,
    now: datetime | None = None,
    dry_run: bool = False,
    bot_token: str | None = None,
    chat_id: str | None = None,
    audit_network: bool = True,
) -> dict[str, object]:
    target = database or db_path()
    now = (now or datetime.now(UTC)).astimezone(UTC)
    digest = business_digest(database=target, now=now, audit_network=audit_network)
    digest_date = str(digest["digest_date"])
    key = _digest_key(digest_date)
    translator: TranslationBatch | None = None
    if not dry_run:
        def translate_for_digest(values: list[str]) -> tuple[list[str], bool]:
            return translate_myanmar_to_zh_hans(values, database=target)

        translator = translate_for_digest
    text = render_business_digest(digest, translator=translator)
    payload_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()

    with connect(target) as conn:
        exists = conn.execute("SELECT 1 FROM digest_delivery_receipts WHERE digest_key=?", (key,)).fetchone() is not None
    if exists:
        return {"status": "PASS", "channel": DIGEST_CHANNEL, "dry_run": dry_run, "digest_date": digest_date, "pending_count": 0, "sent_count": 0, "deduplicated": True}

    pending = {"digest_key": key, "digest_date": digest_date, "message": text, "payload_sha256": payload_sha256, "digest": digest}
    if dry_run:
        return {"status": "PASS", "channel": DIGEST_CHANNEL, "dry_run": True, "digest_date": digest_date, "pending_count": 1, "pending": pending}

    token = bot_token or os.environ.get("SIGNALFORGE_TELEGRAM_BOT_TOKEN", "")
    target_chat = chat_id or os.environ.get("SIGNALFORGE_TELEGRAM_CHAT_ID", "")
    if not token or not target_chat:
        raise TelegramDeliveryError("telegram credentials are not configured")

    message_id = _send_message(bot_token=token, chat_id=target_chat, text=text)
    sent_at = _iso(datetime.now(UTC))
    window = digest.get("window") or {}
    assert isinstance(window, dict)
    with connect(target) as conn, conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO digest_delivery_receipts(
                digest_key,channel,digest_date,window_start,window_end,payload_sha256,provider_message_id,sent_at
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (key, DIGEST_CHANNEL, digest_date, window.get("start"), window.get("end"), payload_sha256, message_id, sent_at),
        )
    return {"status": "PASS", "channel": DIGEST_CHANNEL, "dry_run": False, "digest_date": digest_date, "pending_count": 1, "sent_count": 1, "message_id": message_id, "delivery_semantics": "ONCE_PER_MYANMAR_CALENDAR_DAY_WITH_SUCCESS_RECEIPT"}
