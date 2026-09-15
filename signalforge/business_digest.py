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

from .auditor import audit
from .briefing import business_briefing
from .config import Registry, db_path
from .coverage_gaps import reviewed_coverage_gaps
from .db import connect
from .telegram_delivery import TelegramDeliveryError, _send_message
from .translation import contains_myanmar, translate_myanmar_to_zh_hans
from .source_scorecard import source_scorecard

DIGEST_VERSION = 3
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
    pump = re.search(r"(Equipments?\s+for\s+Second\s+Lift\s+Pump\s+House)\s+设备(\d+)类", raw, re.IGNORECASE)
    if pump:
        fragments.append(f"{pump.group(1)} ×{pump.group(2)}类")
    return fragments


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
            seen_business_keys.add(canonical_key)
            business_changes.append({
                "canonical_key": canonical_key,
                "source_id": str(row["source_id"]),
                "signal_type": str(row["signal_type"]),
                "created_at": str(row["created_at"]),
                "item_kind": str(row["item_kind"]),
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
    watchlist = briefing.get("watchlist") or {}
    if not isinstance(watchlist, dict):
        watchlist = {}

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
            "current_opportunities": briefing.get("current_opportunities"),
            "current_counts": briefing.get("current_counts"),
            "qualification_counts": qcounts,
            "priority_counts": priority_counts,
            "attention_count": briefing.get("attention_count"),
            "attention_action_counts": briefing.get("attention_action_counts"),
            "attention": attention,
            "watchlist_count": int(watchlist.get("count") or 0),
            "watchlist_relevance": watchlist.get("primary_relevance_counts") or {},
            "watchlist_items": watchlist.get("items") or [],
            "watchlist_delivery_policy": "VALID_MEDIUM_NOT_IMMEDIATE_ALERT; escalates on strategic fit or <=72h urgency",
            "coverage_gap_count": len(coverage_gaps),
            "coverage_gaps": coverage_gaps,
            "coverage_gap_policy": "REVIEWED_READ_ONLY_OUTSIDE_CANONICAL_SIGNAL_PIPELINE",
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
    quality_avg = qualification_counts.get("signal_quality_score_avg", 0)
    attention = business.get("attention") or []
    if not isinstance(attention, list):
        attention = []

    yield_states = source_yield.get("yield_states") or {}
    if not isinstance(yield_states, dict):
        yield_states = {}
    proven_sources = int(yield_states.get("ACTIONABLE_PROVEN", 0) or 0) + int(yield_states.get("SIGNAL_PROVEN", 0) or 0)

    business_changes = activity.get("business_changes") or []
    if not isinstance(business_changes, list):
        business_changes = []
    coverage_gaps = business.get("coverage_gaps") or []
    if not isinstance(coverage_gaps, list):
        coverage_gaps = []
    watch_items = business.get("watchlist_items") or []
    if not isinstance(watch_items, list):
        watch_items = []
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
        industry_lots = _industry_lot_fragments(scope) if source_id == "S38" else []
        if industry_lots:
            return _compact("；".join(industry_lots), 240)
        fragments = _scope_product_fragments(scope)
        if source_id == "S30" and fragments:
            data_server = [fragment for fragment in fragments if "data server" in fragment.lower()]
            if data_server:
                fragments = [min(data_server, key=len)]
        if fragments:
            summary = "；".join(fragments)
            if quantity and quantity not in summary:
                summary = f"{summary}；规模 {quantity}"
            return _compact(summary, 240)

        title_fragments = _title_product_fragments(title)
        if title_fragments:
            return _compact("；".join(title_fragments), 240)

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
        return translate_values([business_subject(item) for item in rows], 210)

    def translated_issuers(rows: list[dict[str, object]]) -> list[str]:
        return translate_values([str(item.get("issuer") or "") for item in rows], 46)


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
            return "拍卖内容"
        return "业务内容"

    def timing_text(item: dict[str, object]) -> str:
        value = _deadline_text(item)
        if value.startswith("活动日"):
            return value
        return f"截止 {value}"

    lines = [
        "📊 <b>SignalForge Myanmar 商机日报</b>",
        f"🗓 {html.escape(str(digest.get('digest_date') or ''))} · 过去24小时",
    ]

    all_attention_rows = [item for item in attention if isinstance(item, dict)]
    attention_rows = all_attention_rows[:4]
    selected_keys = {str(item.get("canonical_key") or "") for item in attention_rows}
    for item in all_attention_rows:
        key = str(item.get("canonical_key") or "")
        if key in selected_keys or str(item.get("primary_relevance") or "") not in {"ICT", "TELECOM"}:
            continue
        attention_rows.append(item)
        selected_keys.add(key)
        if len(attention_rows) >= 6:
            break
    for item in all_attention_rows:
        if len(attention_rows) >= 6:
            break
        key = str(item.get("canonical_key") or "")
        if key in selected_keys:
            continue
        attention_rows.append(item)
        selected_keys.add(key)
    attention_keys = {key for key in selected_keys if key}
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
            if reference:
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
            if reference:
                meta.append(f"Ref {reference}")
            link = official_link(item.get("url"))
            lines.append(f"• <b>{issuer}</b> · [{source_id}] · {signal_type}")
            lines.append(f"   {business_label(item)}：<b>{subject}</b>")
            lines.append("   " + html.escape(" · ".join(meta)) + link)

    if coverage_gaps:
        lines.extend(["", "<b>⚠️ 人工核验机会（尚未进入正式 Signal）</b>"])
        gap_rows = [gap for gap in coverage_gaps[:4] if isinstance(gap, dict)]
        gap_issuers = translate_values([str(gap.get("issuer") or "") for gap in gap_rows], 46)
        gap_titles = translate_values([str(gap.get("title") or "") for gap in gap_rows], 110)
        gap_locations = translate_values([str(gap.get("location") or "") for gap in gap_rows], 34)
        for index, gap in enumerate(gap_rows):
            source_id = html.escape(str(gap.get("source_id") or ""))
            issuer = html.escape(gap_issuers[index])
            title = html.escape(gap_titles[index])
            deadline = html.escape(str(gap.get("deadline") or ""))
            location = html.escape(gap_locations[index])
            url = str(gap.get("url") or "")
            link = official_link(url, "官方记录") if url.startswith("https://construction.gov.mm/") else ""
            lines.append(f"• <b>{issuer}</b> · [{source_id}]")
            lines.append(f"   招标：<b>{title}</b> · {location} · 截止 <b>{deadline}</b>{link}")
        lines.append("<i>已人工核验，但因来源接入门槛未满足，暂不计入正式机会数。</i>")

    watch_count = int(business.get("watchlist_count") or 0)
    watch_rows = [
        item for item in watch_items
        if isinstance(item, dict) and str(item.get("canonical_key")) not in attention_keys
    ][:2]
    if watch_rows:
        watch_issuers = translated_issuers(watch_rows)
        watch_subjects = translated_subjects(watch_rows)
        lines.extend(["", f"<b>🟡 后续跟进：{watch_count} 条 MEDIUM（展示前 {len(watch_rows)} 条）</b>"])
        for index, item in enumerate(watch_rows):
            source_id = html.escape(str(item.get("source_id") or "?"))
            issuer = html.escape(watch_issuers[index])
            subject = html.escape(watch_subjects[index])
            deadline = html.escape(timing_text(item))
            lines.append(f"• [{source_id}] <b>{issuer}</b> · {subject} · {deadline}")
    elif watch_count:
        lines.extend(["", f"🟡 后续跟进：{watch_count} 条 MEDIUM"])

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

    lines.extend([
        "",
        f"<b>📌 业务概览</b>：当前 <b>{business.get('current_opportunities', 0)}</b> 个机会 · HIGH {priorities.get('HIGH', 0)} · MEDIUM {priorities.get('MEDIUM', 0)} · REVIEW {priorities.get('REVIEW', 0)}",
    ])

    mytel = auditor.get("mytel") or {}
    mpt = auditor.get("mpt") or {}
    atom = auditor.get("atom") or {}
    if not isinstance(mytel, dict): mytel = {}
    if not isinstance(mpt, dict): mpt = {}
    if not isinstance(atom, dict): atom = {}
    findings = int(auditor.get("finding_count") or 0)
    system_icon = "✅" if int(sources.get("non_green", 0) or 0) == 0 and findings == 0 else "⚠️"
    lines.append(
        f"{system_icon} 系统：{sources.get('green', 0)}/{sources.get('monitored', 0)} GREEN · "
        f"degraded {sources.get('non_green', 0)} · Auditor {html.escape(str(auditor.get('status') or 'UNKNOWN'))}({findings})"
    )
    mpt_missing = mpt.get("missing", "?")
    mpt_label = "MPT 完整" if mpt_missing == 0 else f"MPT 缺 {mpt_missing}"
    lines.append(
        f"📶 Telecom：{mpt_label} · MYTEL {mytel.get('canonical_keys', '?')}/{mytel.get('official_keys', '?')} · ATOM {atom.get('status', 'UNKNOWN')}"
    )
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
    translator = None
    if not dry_run:
        translator = lambda values: translate_myanmar_to_zh_hans(values, database=target)
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
