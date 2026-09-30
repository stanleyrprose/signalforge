from __future__ import annotations

import hashlib
import html
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .briefing import business_briefing
from .business_profile import BusinessProfile, load_business_profile, match_tender
from .config import db_path
from .db import connect
from .translation import contains_myanmar, translate_myanmar_to_zh_hans, translate_tender_fields_to_zh_hans

CHANNEL = "telegram"
TELEGRAM_MESSAGE_LIMIT = 4096
TranslationBatch = Callable[[list[str]], tuple[list[str], bool]]


class TelegramDeliveryError(RuntimeError):
    pass


def _delivery_key(item: dict[str, object]) -> str:
    raw = "|".join(
        (
            CHANNEL,
            str(item.get("canonical_key") or ""),
            str(item.get("latest_signal_id") or ""),
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _pilot_delivery_key(item: dict[str, object], profile_id: str) -> str:
    raw = "|".join(
        (
            CHANNEL,
            "pilot",
            profile_id,
            str(item.get("canonical_key") or ""),
            str(item.get("latest_signal_id") or ""),
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _payload_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _manual_delivery_key(item: dict[str, object]) -> str:
    raw = "|".join((CHANNEL, "manual-promotion", str(item.get("promotion_id") or "")))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_manual_promotion_message(
    item: dict[str, object],
    *,
    translator: TranslationBatch | None = None,
) -> str:
    raw_values = [
        str(item.get("title") or "Important nonstandard signal"),
        str(item.get("summary") or ""),
        str(item.get("reason") or ""),
        str(item.get("location") or ""),
    ]
    translate_batch = translator or translate_myanmar_to_zh_hans
    translated, was_translated = translate_batch(raw_values)
    title, summary, reason, location = [html.escape(value) for value in translated]
    source_id = html.escape(str(item.get("source_id") or "MANUAL"))
    priority = html.escape(str(item.get("priority_band") or "HIGH"))
    lines = [
        f"🧑 <b>人工升级 · {priority}</b> · [{source_id}]",
        f"<b>{title}</b>",
        "<i>重要但无法标准化；不是 canonical Signal。</i>",
    ]
    if summary:
        lines.append(f"📦 内容：{summary}")
    if reason:
        lines.append(f"🎯 升级原因：{reason}")
    if item.get("deadline"):
        lines.append(f"⏰ 截止：<b>{html.escape(str(item.get('deadline')))}</b>")
    if location:
        lines.append(f"📍 地点：{location}")
    url = html.escape(str(item.get("url") or ""), quote=True)
    if url.startswith("https://"):
        lines.append(f'🔗 <a href="{url}">来源</a>')
    if was_translated:
        lines.append("🌐 缅文内容已机器翻译为中文（事实以原始来源为准）")
    return "\n".join(lines)[:TELEGRAM_MESSAGE_LIMIT]


def _deadline_text(item: dict[str, object]) -> str:
    if item.get("deadline_status") == "UNKNOWN":
        return "未在已核验材料中确认"
    deadline = str(item.get("deadline") or "")
    deadline_time = str(item.get("deadline_time") or "")
    return f"{deadline} {deadline_time}".strip() or "未在已核验材料中确认"


def _deadline_label(item: dict[str, object]) -> str:
    kind = item.get("deadline_kind")
    if kind == "TENDER_FORM_SALE_CLOSE":
        return "获取标书截止"
    if kind == "TENDER_APPLICATION_ACCEPTANCE_CLOSE":
        return "投标申请接收截止"
    if kind == "BID_SUBMISSION_DEADLINE":
        return "投标截止"
    return "截止"


def _opening_text(item: dict[str, object]) -> str | None:
    opening_date = str(item.get("tender_opening_date") or "")
    if not opening_date:
        return None
    opening_time = str(item.get("tender_opening_time") or "")
    return f"{opening_date} {opening_time}".strip()


def _reason_text(item: dict[str, object]) -> str:
    mapping = {
        "DEADLINE_WITHIN_72H": "截止时间已进入72小时窗口",
        "COMMERCIAL_EVENT_WITHIN_72H": "商业活动已进入72小时窗口",
        "COMMERCIAL_EVENT_DATE_KNOWN": "官方商业活动日期明确",
        "STRATEGIC_FIT_ICT_TELECOM": "ICT/Telecom 战略相关",
        "HUMAN_REVIEW_REQUIRED": "需要人工确认后再行动",
        "DEADLINE_UNKNOWN": "官方未给出明确截止时间",
        "A_GRADE_BUSINESS_EVIDENCE": "A级业务证据完整",
        "TRUSTED_EVENT_PARTIAL_ACTIONABILITY": "事件可信但行动信息不完整",
    }
    return "；".join(mapping.get(str(value), str(value)) for value in (item.get("why_now") or []))


def _action_label(action: str) -> str:
    return {
        "ACT_NOW": "立即行动",
        "PRIORITIZE": "优先关注",
        "REVIEW": "人工复核",
    }.get(action, "关注")


def _evidence_label(value: object) -> str:
    return {
        "OFFICIAL_HTML_VIA_PROVIDER": "官方 HTML（Mac Provider）",
        "OFFICIAL_HTML_PLUS_TEXT_PDF": "官方 HTML + 官方文本 PDF",
        "OFFICIAL_HTML": "官方 HTML",
    }.get(str(value or ""), str(value or "已核验官方来源"))


def _compact_scope(value: object, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _telegram_business_readiness(item: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    item_kind = str(item.get("item_kind") or "")
    if item_kind and item_kind != "TENDER":
        reasons.append("ITEM_KIND_NOT_TENDER")
    excluded_reason = str(item.get("customer_readiness_excluded_reason") or "")
    if excluded_reason:
        reasons.append(f"CUSTOMER_SCOPE_EXCLUDED:{excluded_reason}")
    if str(item.get("deadline_status") or "") != "OPEN":
        reasons.append("DEADLINE_NOT_CONFIRMED_OPEN")
    opportunity_status = str(item.get("opportunity_status") or "")
    if opportunity_status and opportunity_status != "OPEN":
        reasons.append("OPPORTUNITY_NOT_OPEN")
    scope = _compact_scope(item.get("scope_excerpt"), limit=320)
    if len(scope) < 16:
        reasons.append("PROCUREMENT_SCOPE_NOT_ACTIONABLE")
    quantity = " ".join(str(item.get("quantity_or_lot_summary") or "").split())
    if not quantity:
        reasons.append("QUANTITY_OR_SCALE_NOT_EXPLAINED")
    return reasons


def render_telegram_message(
    item: dict[str, object],
    *,
    translator: TranslationBatch | None = None,
) -> str:
    raw_title = str(item.get("title") or item.get("canonical_key") or "Tender")
    raw_issuer = str(item.get("issuer") or "Unknown issuer")
    raw_scope = _compact_scope(item.get("scope_excerpt"))
    raw_quantity = str(item.get("quantity_or_lot_summary") or "")
    raw_amount = str(item.get("price_or_budget_summary") or "")
    raw_location = str(item.get("location") or "")
    raw_next_action = str(item.get("next_action_summary") or "")
    translate_batch = translator or translate_myanmar_to_zh_hans
    translated_values, was_translated = translate_batch(
        [raw_title, raw_issuer, raw_scope, raw_quantity, raw_amount, raw_location, raw_next_action]
    )
    translated_title, translated_issuer, translated_scope, translated_quantity, translated_amount, translated_location, translated_next_action = translated_values
    if str(item.get("item_kind") or "") == "TENDER" and translated_scope:
        translated_title = _compact_scope(f"{translated_issuer}｜{translated_scope}", limit=128)
    title, issuer, scope, quantity, amount, location, next_action = [
        html.escape(value)
        for value in (
            translated_title,
            translated_issuer,
            translated_scope,
            translated_quantity,
            translated_amount,
            translated_location,
            translated_next_action,
        )
    ]
    reference_numbers = item.get("reference_numbers")
    if isinstance(reference_numbers, list) and reference_numbers:
        reference = ", ".join(str(value) for value in reference_numbers)
    else:
        reference = str(item.get("reference_no") or "")
    focus_reference_numbers = item.get("focus_reference_numbers")
    focus_reference = (
        ", ".join(str(value) for value in focus_reference_numbers)
        if isinstance(focus_reference_numbers, list) and focus_reference_numbers
        else ""
    )
    url = html.escape(str(item.get("url") or ""), quote=True)
    evidence_text = _evidence_label(item.get("evidence_level"))
    if item.get("reviewed_attachment_status"):
        evidence_text += " + 官方附件（人工核验）"
    evidence = html.escape(evidence_text)
    signal_type = str(item.get("latest_signal_type") or "")
    signal_label = {"NEW": "新招标", "UPDATED": "招标更新"}.get(signal_type, "招标通知")
    icon = "📢" if signal_type == "NEW" else "🔄" if signal_type == "UPDATED" else "🔔"

    issuer_label = "卖方" if item.get("commercial_direction") == "BUY_FROM_ISSUER" else "采购方"
    lines = [
        f"{icon} <b>政府/国企招标 · {signal_label}</b>",
        f"<b>{title}</b>",
        "",
        f"🏛 {issuer_label}：{issuer}",
    ]
    if scope:
        lines.append(f"📦 采购内容：{scope}")
    if item.get("quantity_or_lot_summary"):
        lines.append(f"🔢 数量/规模：{quantity}")
    if item.get("price_or_budget_summary"):
        lines.append(f"💰 金额（原文）：{amount}")
    if item.get("deadline_status") != "UNKNOWN":
        lines.append(f"⏰ {_deadline_label(item)}：<b>{html.escape(_deadline_text(item))}</b>")
    elif item.get("action_date"):
        action_date = f"{item.get('action_date')} {item.get('action_time') or ''}".strip()
        lines.append(f"🗓 活动日：<b>{html.escape(action_date)}</b>")
    else:
        lines.append(f"⏰ {_deadline_label(item)}：<b>{html.escape(_deadline_text(item))}</b>")
    opening = _opening_text(item)
    if opening:
        lines.append(f"🗓 开标：<b>{html.escape(opening)}</b>")
    if reference:
        lines.append(f"📌 招标编号：{html.escape(reference)}")
    if item.get("location"):
        lines.append(f"📍 地点：{location}")
    profile_match_summary = str(item.get("business_profile_match_summary") or "")
    if profile_match_summary:
        lines.append(f"🎯 与你业务关联：{html.escape(profile_match_summary)}")
    if item.get("next_action_summary"):
        lines.append(f"➡️ 下一步：{next_action}")
    if focus_reference and focus_reference != reference:
        lines.append(f"🧩 相关分包：{html.escape(focus_reference)}")
    if was_translated:
        lines.append("🌐 原文内容已机器翻译为中文（事实以官方原文为准）")
    lines.append(f"🔎 证据：{evidence}")
    if url:
        lines.append(f'🔗 <a href="{url}">官方来源</a>')

    text = "\n".join(lines)
    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        return text
    # Procurement scope is the only intentionally lossy field in the transport renderer.
    overflow = len(text) - TELEGRAM_MESSAGE_LIMIT + 80
    shorter = scope[: max(0, len(scope) - overflow)].rstrip() + "…"
    lines = [line if not line.startswith("📦 采购内容：") else f"📦 采购内容：{shorter}" for line in lines]
    text = "\n".join(lines)
    return text[:TELEGRAM_MESSAGE_LIMIT]


def _send_message(*, bot_token: str, chat_id: str, text: str, timeout: int = 15) -> str:
    body = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(65536).decode("utf-8"))
    except HTTPError as exc:
        raise TelegramDeliveryError(f"telegram HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise TelegramDeliveryError("telegram transport failed") from None
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise TelegramDeliveryError("telegram API rejected message")
    result = payload.get("result")
    if not isinstance(result, dict) or result.get("message_id") is None:
        raise TelegramDeliveryError("telegram API response missing message_id")
    return str(result["message_id"])


def telegram_deliver(
    *,
    database: Path | None = None,
    now: datetime | None = None,
    dry_run: bool = False,
    translate_preview: bool = False,
    bot_token: str | None = None,
    chat_id: str | None = None,
    business_profile: BusinessProfile | None = None,
    profile_path: Path | None = None,
) -> dict[str, object]:
    target = database or db_path()
    profile = business_profile or load_business_profile(profile_path)
    now = (now or datetime.now(UTC)).astimezone(UTC)
    briefing = business_briefing(database=target, now=now)
    rows = briefing.get("attention") or []
    assert isinstance(rows, list)
    manual_bundle = briefing.get("manual_promotions") or {}
    if not isinstance(manual_bundle, dict):
        manual_bundle = {}
    manual_rows = manual_bundle.get("items") or []
    if not isinstance(manual_rows, list):
        manual_rows = []
    # Telegram is now a customer-facing canonical Tender channel. Manual
    # promotions remain available to operator/business-digest surfaces only.
    manual_suppressed_count = len(manual_rows)
    manual_rows = []

    pending: list[dict[str, object]] = []
    manual_pending: list[dict[str, object]] = []
    filtered_out_count = 0
    quality_filtered: list[dict[str, object]] = []
    translator: TranslationBatch | None = None
    if not dry_run or translate_preview:
        def translate_for_delivery(values: list[str]) -> tuple[list[str], bool]:
            return translate_tender_fields_to_zh_hans(values, database=target)

        translator = translate_for_delivery
    with connect(target) as conn:
        for item in rows:
            if not isinstance(item, dict):
                continue
            delivery_item = dict(item)
            if profile is not None:
                profile_match = match_tender(delivery_item, profile)
                if not bool(profile_match["eligible"]):
                    filtered_out_count += 1
                    continue
                delivery_item["business_profile_id"] = profile.profile_id
                delivery_item["business_profile_match_score"] = profile_match["score"]
                delivery_item["business_profile_match_summary"] = profile_match["summary"]
            readiness_reasons = _telegram_business_readiness(delivery_item)
            if readiness_reasons:
                quality_filtered.append(
                    {
                        "canonical_key": str(delivery_item.get("canonical_key") or ""),
                        "reasons": readiness_reasons,
                    }
                )
                continue
            signal_id = str(delivery_item.get("latest_signal_id") or "")
            if not signal_id:
                raise TelegramDeliveryError("attention item missing latest_signal_id")
            if profile is not None:
                key = _pilot_delivery_key(delivery_item, profile.profile_id)
                exists = conn.execute(
                    """
                    SELECT 1 FROM pilot_delivery_receipts
                    WHERE channel=? AND profile_id=? AND canonical_key=? AND signal_id=?
                    """,
                    (
                        CHANNEL,
                        profile.profile_id,
                        str(delivery_item.get("canonical_key") or ""),
                        signal_id,
                    ),
                ).fetchone()
            else:
                key = _delivery_key(delivery_item)
                # Semantic lookup keeps rollout compatible with legacy owner-feed
                # receipts whose delivery_key also included attention_action.
                exists = conn.execute(
                    "SELECT 1 FROM delivery_receipts WHERE channel=? AND canonical_key=? AND signal_id=?",
                    (CHANNEL, str(delivery_item.get("canonical_key") or ""), signal_id),
                ).fetchone()
            if exists is not None:
                continue
            text = render_telegram_message(delivery_item, translator=translator)
            if (not dry_run or translate_preview) and contains_myanmar(text):
                quality_filtered.append(
                    {
                        "canonical_key": str(delivery_item.get("canonical_key") or ""),
                        "reasons": ["UNTRANSLATED_MYANMAR_PRESENT"],
                    }
                )
                continue
            pending.append({**delivery_item, "delivery_key": key, "message": text, "payload_sha256": _payload_sha256(text)})
        for item in manual_rows:
            if not isinstance(item, dict):
                continue
            promotion_id = str(item.get("promotion_id") or "")
            if not promotion_id:
                continue
            key = _manual_delivery_key(item)
            exists = conn.execute(
                "SELECT 1 FROM manual_delivery_receipts WHERE delivery_key=? OR (channel=? AND promotion_id=?)",
                (key, CHANNEL, promotion_id),
            ).fetchone()
            if exists is not None:
                continue
            text = render_manual_promotion_message(item, translator=translator)
            manual_pending.append({**item, "delivery_key": key, "message": text, "payload_sha256": _payload_sha256(text)})

    if dry_run:
        return {
            "status": "PASS",
            "channel": CHANNEL,
            "dry_run": True,
            "pending_count": len(pending) + len(manual_pending),
            "signal_pending_count": len(pending),
            "manual_pending_count": len(manual_pending),
            "manual_suppressed_count": manual_suppressed_count,
            "filtered_out_count": filtered_out_count,
            "quality_filtered_count": len(quality_filtered),
            "quality_filtered": quality_filtered,
            "translate_preview": bool(translate_preview),
            "business_profile_id": profile.profile_id if profile is not None else None,
            "business_profile_delivery_mode": profile.delivery_mode if profile is not None else "ALL_TENDERS",
            "pending": [*pending, *manual_pending],
        }

    token = bot_token or os.environ.get("SIGNALFORGE_TELEGRAM_BOT_TOKEN", "")
    target_chat = chat_id or os.environ.get("SIGNALFORGE_TELEGRAM_CHAT_ID", "")
    if not token or not target_chat:
        raise TelegramDeliveryError("telegram credentials are not configured")

    sent: list[dict[str, object]] = []
    for item in pending:
        message_id = _send_message(bot_token=token, chat_id=target_chat, text=str(item["message"]))
        sent_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        with connect(target) as conn, conn:
            profile_id = item.get("business_profile_id")
            if profile_id:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO pilot_delivery_receipts(
                        delivery_key,channel,profile_id,canonical_key,signal_id,attention_action,
                        priority_band,profile_match_score,payload_sha256,provider_message_id,sent_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        item["delivery_key"],
                        CHANNEL,
                        profile_id,
                        item["canonical_key"],
                        item["latest_signal_id"],
                        item["attention_action"],
                        item["priority_band"],
                        int(item.get("business_profile_match_score") or 0),
                        item["payload_sha256"],
                        message_id,
                        sent_at,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO delivery_receipts(
                        delivery_key,channel,canonical_key,signal_id,attention_action,priority_band,
                        payload_sha256,provider_message_id,sent_at,profile_id,profile_match_score
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        item["delivery_key"],
                        CHANNEL,
                        item["canonical_key"],
                        item["latest_signal_id"],
                        item["attention_action"],
                        item["priority_band"],
                        item["payload_sha256"],
                        message_id,
                        sent_at,
                        None,
                        None,
                    ),
                )
        sent.append(
            {
                "canonical_key": item["canonical_key"],
                "attention_action": item["attention_action"],
                "message_id": message_id,
            }
        )

    manual_sent: list[dict[str, object]] = []
    for item in manual_pending:
        message_id = _send_message(bot_token=token, chat_id=target_chat, text=str(item["message"]))
        sent_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        with connect(target) as conn, conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO manual_delivery_receipts(
                    delivery_key,channel,promotion_id,payload_sha256,provider_message_id,sent_at
                ) VALUES (?,?,?,?,?,?)
                """,
                (
                    item["delivery_key"],
                    CHANNEL,
                    item["promotion_id"],
                    item["payload_sha256"],
                    message_id,
                    sent_at,
                ),
            )
        manual_sent.append({"promotion_id": item["promotion_id"], "message_id": message_id})

    return {
        "status": "PASS",
        "channel": CHANNEL,
        "dry_run": False,
        "pending_count": len(pending) + len(manual_pending),
        "signal_pending_count": len(pending),
        "manual_pending_count": len(manual_pending),
        "manual_suppressed_count": manual_suppressed_count,
        "sent_count": len(sent) + len(manual_sent),
        "signal_sent_count": len(sent),
        "manual_sent_count": len(manual_sent),
        "filtered_out_count": filtered_out_count,
        "quality_filtered_count": len(quality_filtered),
        "quality_filtered": quality_filtered,
        "business_profile_id": profile.profile_id if profile is not None else None,
        "business_profile_delivery_mode": profile.delivery_mode if profile is not None else "ALL_TENDERS",
        "sent": sent,
        "manual_sent": manual_sent,
        "delivery_semantics": "AT_LEAST_ONCE_CUSTOMER_READY_CANONICAL_TENDERS_ONLY",
    }
