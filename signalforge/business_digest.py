from __future__ import annotations

import hashlib
import html
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .auditor import audit
from .briefing import business_briefing
from .config import Registry, db_path
from .db import connect
from .telegram_delivery import TelegramDeliveryError, _send_message
from .source_scorecard import source_scorecard

DIGEST_VERSION = 1
DIGEST_CHANNEL = "telegram-business-digest"
DIGEST_TIMEZONE = ZoneInfo("Asia/Yangon")
TELEGRAM_MESSAGE_LIMIT = 4096


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _compact(value: object, limit: int = 96) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


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
            "watchlist_delivery_policy": "VALID_MEDIUM_NOT_IMMEDIATE_ALERT; escalates on strategic fit or <=72h urgency",
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


def render_business_digest(digest: dict[str, object]) -> str:
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

    lines = [
        "📊 <b>SignalForge Myanmar Business Digest</b>",
        f"🗓 {html.escape(str(digest.get('digest_date') or ''))} · 过去24小时",
        "",
        f"📡 Sources：<b>{sources.get('monitored', 0)}</b> monitored · {sources.get('green', 0)} GREEN · {sources.get('non_green', 0)} degraded",
        f"🧭 Source产出：<b>{proven_sources}/{source_yield.get('active_sources', sources.get('monitored', 0))}</b> proven · actionable {yield_states.get('ACTIONABLE_PROVEN', 0)} · signal-only {yield_states.get('SIGNAL_PROVEN', 0)} · baseline {yield_states.get('BASELINE_ONLY', 0)} · noise-only {yield_states.get('NOISE_ONLY_HISTORY', 0)} · empty {yield_states.get('EMPTY', 0)}",
        f"🔄 采集：{activity.get('scheduler_runs', 0)} runs · {sources.get('changed_24h', 0)} sources changed · {activity.get('records_changed', 0)} records changed",
        f"🧾 Evidence：{activity.get('evidence_fetched', 0)} fetched · {activity.get('items_parsed', 0)} items parsed",
        f"📈 Signals：<b>{activity.get('signals', 0)}</b>（NEW {activity.get('new_signals', 0)} / UPDATED {activity.get('updated_signals', 0)}）",
        "",
        f"🎯 当前机会：<b>{business.get('current_opportunities', 0)}</b> · HIGH {priorities.get('HIGH', 0)} · MEDIUM {priorities.get('MEDIUM', 0)} · REVIEW {priorities.get('REVIEW', 0)}",
        f"🧭 Signal质量：均分 {quality_avg} · VERY_HIGH {quality_counts.get('VERY_HIGH', 0)} · HIGH {quality_counts.get('HIGH', 0)} · MEDIUM {quality_counts.get('MEDIUM', 0)} · REVIEW {quality_counts.get('REVIEW', 0)}",
        f"📲 TG即时提醒：过去24h {totals.get('telegram_alerts_24h', 0)} · 累计 {totals.get('telegram_alerts', 0)}",
    ]

    if attention:
        lines.extend(["", "<b>值得现在看</b>"])
        icons = {"ACT_NOW": "🔴", "PRIORITIZE": "🟠", "REVIEW": "🟡"}
        for item in attention[:4]:
            if not isinstance(item, dict):
                continue
            action = str(item.get("attention_action") or "REVIEW")
            issuer = _compact(item.get("issuer"), 42)
            relevance = str(item.get("primary_relevance") or "OTHER")
            deadline = _deadline_text(item)
            focus_count = int(item.get("focus_reference_count") or 0)
            focus = f" · 相关分包 {focus_count}" if focus_count else ""
            quality = ""
            if isinstance(item.get("signal_quality_score"), int) and item.get("signal_quality_band"):
                quality = f" · Q{item.get('signal_quality_score')}/{item.get('signal_quality_band')}"
            lines.append(
                f"{icons.get(action, '•')} {html.escape(action)} · {html.escape(issuer)} · {html.escape(relevance)} · {html.escape(deadline)}{quality}{focus}"
            )

    watch_count = int(business.get("watchlist_count") or 0)
    if watch_count:
        lines.append(f"🟡 Watchlist：{watch_count} 条 MEDIUM（有效但不即时打扰；进入72h或战略升级再提醒）")

    mytel = auditor.get("mytel") or {}
    mpt = auditor.get("mpt") or {}
    atom = auditor.get("atom") or {}
    if not isinstance(mytel, dict): mytel = {}
    if not isinstance(mpt, dict): mpt = {}
    if not isinstance(atom, dict): atom = {}
    mytel_missing = len(mytel.get("missing") or []) if isinstance(mytel.get("missing"), list) else mytel.get("missing", "?")
    lines.extend([
        "",
        f"🛡 Auditor：<b>{html.escape(str(auditor.get('status') or 'UNKNOWN'))}</b> · findings {auditor.get('finding_count', '?')}",
        f"📶 Telecom覆盖：MPT missing {mpt.get('missing', '?')} · MYTEL {mytel.get('canonical_keys', '?')}/{mytel.get('official_keys', '?')}（missing {mytel_missing}） · ATOM {atom.get('status', 'UNKNOWN')}",
        f"🗃 累计：{totals.get('canonical_items', 0)} canonical · {source_yield.get('effective_signals', '?')} effective / {totals.get('signals', 0)} raw signals",
    ])

    text = "\n".join(lines)
    if len(text) > TELEGRAM_MESSAGE_LIMIT:
        text = text[: TELEGRAM_MESSAGE_LIMIT - 1].rstrip() + "…"
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
    text = render_business_digest(digest)
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
