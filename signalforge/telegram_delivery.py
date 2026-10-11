from __future__ import annotations

import hashlib
import html
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen

from .briefing import business_briefing
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


def _payload_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        "OFFICIAL_TEXT_PDF": "官方文本 PDF",
        "OFFICIAL_HTML": "官方 HTML",
    }.get(str(value or ""), str(value or "已核验官方来源"))


def _compact_scope(value: object, limit: int = 320) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


_LOCAL_TZ = ZoneInfo("Asia/Yangon")


def _deadline_urgency_text(item: dict[str, object], now: datetime | None) -> str | None:
    if now is None or str(item.get("deadline_status") or "") != "OPEN":
        return None
    deadline = str(item.get("deadline") or "").strip()
    if not deadline:
        return None
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
    except ValueError:
        return None

    local_now = now.astimezone(_LOCAL_TZ)
    deadline_time = str(item.get("deadline_time") or "").strip()
    if deadline_time:
        try:
            deadline_at = datetime.strptime(
                f"{deadline} {deadline_time[:5]}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=_LOCAL_TZ)
        except ValueError:
            deadline_at = None
        if deadline_at is not None:
            remaining_seconds = int((deadline_at - local_now).total_seconds())
            if remaining_seconds <= 0:
                return "⚠️ 时效：按已核验时间已到截止点，请先确认是否延期"
            if remaining_seconds <= 72 * 3600:
                remaining_hours = max(1, (remaining_seconds + 3599) // 3600)
                if remaining_hours < 24:
                    prefix = "🔴" if remaining_hours <= 12 else "⏳"
                    return f"{prefix} 时效：约 {remaining_hours} 小时后截止"
                days, hours = divmod(remaining_hours, 24)
                suffix = f"{days} 天" + (f" {hours} 小时" if hours else "")
                return f"⏳ 时效：约 {suffix}后截止"
            return None

    days_remaining = (deadline_date - local_now.date()).days
    if days_remaining < 0:
        return "⚠️ 时效：截止日期已到，请先确认是否延期"
    if days_remaining == 0:
        return "🔴 时效：今日截止；具体时间未确认，请立即核实"
    if days_remaining == 1:
        return "⏳ 时效：明日截止；具体时间未确认"
    if days_remaining == 2:
        return "⏳ 时效：2 天后截止；具体时间未确认"
    return None


def _telegram_business_readiness(item: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    if str(item.get("item_kind") or "") != "TENDER":
        reasons.append("ITEM_KIND_NOT_TENDER")
    excluded_reason = str(item.get("customer_readiness_excluded_reason") or "")
    if excluded_reason:
        reasons.append(f"PRIMARY_DELIVERY_EXCLUDED:{excluded_reason}")
    if str(item.get("deadline_status") or "") == "EXPIRED":
        reasons.append("TENDER_EXPIRED")
    if str(item.get("opportunity_status") or "") == "EXPIRED":
        reasons.append("TENDER_EXPIRED")
    return list(dict.fromkeys(reasons))


def render_telegram_message(
    item: dict[str, object],
    *,
    translator: TranslationBatch | None = None,
    now: datetime | None = None,
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
    publication_date = str(item.get("publication_date") or "").strip()
    if publication_date:
        lines.append(f"📅 发布：{html.escape(publication_date)}")
    if scope:
        lines.append(f"📦 采购内容：{scope}")
    else:
        lines.append("📦 采购内容：已识别为正式招标，但自动摘要尚未提取；请查看官方原文")
    if item.get("quantity_or_lot_summary"):
        lines.append(f"🔢 数量/规模：{quantity}")
    else:
        lines.append("🔢 数量/规模：已核验摘要未单列；详见采购内容/官方原文")
    if item.get("price_or_budget_summary"):
        lines.append(f"💰 预算/价格（原文）：{amount}")
    if item.get("deadline_status") != "UNKNOWN":
        lines.append(f"⏰ {_deadline_label(item)}：<b>{html.escape(_deadline_text(item))}</b>")
    elif item.get("action_date"):
        action_date = f"{item.get('action_date')} {item.get('action_time') or ''}".strip()
        lines.append(f"🗓 活动日：<b>{html.escape(action_date)}</b>")
    else:
        lines.append(f"⏰ {_deadline_label(item)}：<b>{html.escape(_deadline_text(item))}</b>")
    urgency_text = _deadline_urgency_text(item, now)
    if urgency_text:
        lines.append(urgency_text)
    opening = _opening_text(item)
    if opening:
        lines.append(f"🗓 开标：<b>{html.escape(opening)}</b>")
    if reference:
        lines.append(f"📌 招标编号：{html.escape(reference)}")
    if item.get("location"):
        lines.append(f"📍 地点：{location}")
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


def _send_message(
    *,
    bot_token: str,
    chat_id: str,
    text: str,
    timeout: int = 15,
) -> str:
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
) -> dict[str, object]:
    target = database or db_path()
    now = (now or datetime.now(UTC)).astimezone(UTC)
    briefing = business_briefing(database=target, now=now)
    rows = briefing.get("attention") or []
    assert isinstance(rows, list)
    pending: list[dict[str, object]] = []
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
            key = _delivery_key(delivery_item)
            # Semantic lookup keeps rollout compatible with legacy owner-feed
            # receipts whose delivery_key also included attention_action.
            exists = conn.execute(
                "SELECT 1 FROM delivery_receipts WHERE channel=? AND canonical_key=? AND signal_id=?",
                (CHANNEL, str(delivery_item.get("canonical_key") or ""), signal_id),
            ).fetchone()
            if exists is not None:
                continue
            text = render_telegram_message(delivery_item, translator=translator, now=now)
            if (not dry_run or translate_preview) and contains_myanmar(text):
                quality_filtered.append(
                    {
                        "canonical_key": str(delivery_item.get("canonical_key") or ""),
                        "reasons": ["UNTRANSLATED_MYANMAR_PRESENT"],
                    }
                )
                continue
            pending.append(
                {
                    **delivery_item,
                    "delivery_key": key,
                    "message": text,
                    "payload_sha256": _payload_sha256(text),
                }
            )
    if dry_run:
        return {
            "status": "PASS",
            "channel": CHANNEL,
            "dry_run": True,
            "pending_count": len(pending),
            "quality_filtered_count": len(quality_filtered),
            "quality_filtered": quality_filtered,
            "translate_preview": bool(translate_preview),
            "pending": pending,
        }

    token = bot_token or os.environ.get("SIGNALFORGE_TELEGRAM_BOT_TOKEN", "")
    target_chat = chat_id or os.environ.get("SIGNALFORGE_TELEGRAM_CHAT_ID", "")
    if not token or not target_chat:
        raise TelegramDeliveryError("telegram credentials are not configured")

    sent: list[dict[str, object]] = []
    for item in pending:
        message_id = _send_message(
            bot_token=token,
            chat_id=target_chat,
            text=str(item["message"]),
        )
        sent_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        with connect(target) as conn, conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO delivery_receipts(
                    delivery_key,channel,canonical_key,signal_id,attention_action,priority_band,
                    payload_sha256,provider_message_id,sent_at
                ) VALUES (?,?,?,?,?,?,?,?,?)
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
                ),
            )
        sent.append(
            {
                "canonical_key": item["canonical_key"],
                "attention_action": item["attention_action"],
                "message_id": message_id,
            }
        )

    return {
        "status": "PASS",
        "channel": CHANNEL,
        "dry_run": False,
        "pending_count": len(pending),
        "sent_count": len(sent),
        "quality_filtered_count": len(quality_filtered),
        "quality_filtered": quality_filtered,
        "sent": sent,
        "delivery_semantics": "AT_LEAST_ONCE_FORMAL_TENDERS_ONLY",
    }
