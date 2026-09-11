from __future__ import annotations

import hashlib
import html
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .briefing import business_briefing
from .config import db_path
from .db import connect

CHANNEL = "telegram"
TELEGRAM_MESSAGE_LIMIT = 4096


class TelegramDeliveryError(RuntimeError):
    pass


def _delivery_key(item: dict[str, object]) -> str:
    raw = "|".join(
        (
            CHANNEL,
            str(item.get("canonical_key") or ""),
            str(item.get("latest_signal_id") or ""),
            str(item.get("attention_action") or ""),
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _payload_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _deadline_text(item: dict[str, object]) -> str:
    if item.get("deadline_status") == "UNKNOWN":
        return "UNKNOWN（官方材料未提供）"
    deadline = str(item.get("deadline") or "")
    deadline_time = str(item.get("deadline_time") or "")
    return f"{deadline} {deadline_time}".strip() or "UNKNOWN"


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
    }.get(str(value or ""), str(value or "UNKNOWN"))


def _compact_scope(value: object, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def render_telegram_message(item: dict[str, object]) -> str:
    action = str(item.get("attention_action") or "REVIEW")
    icon = {"ACT_NOW": "🔴", "PRIORITIZE": "🔴", "REVIEW": "🟡"}.get(action, "🔔")
    title = html.escape(str(item.get("title") or item.get("canonical_key") or "Opportunity"))
    issuer = html.escape(str(item.get("issuer") or "Unknown issuer"))
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
    scope = html.escape(_compact_scope(item.get("scope_excerpt")))
    reason = html.escape(_reason_text(item))
    url = html.escape(str(item.get("url") or ""), quote=True)
    evidence = html.escape(_evidence_label(item.get("evidence_level")))
    relevance = html.escape(str(item.get("primary_relevance") or "OTHER"))
    trust = html.escape(str(item.get("trust_grade") or "C"))
    priority = html.escape(str(item.get("priority_band") or "LOW"))
    signal_type = html.escape(str(item.get("latest_signal_type") or ""))
    quality_score = item.get("signal_quality_score")
    quality_band = html.escape(str(item.get("signal_quality_band") or ""))

    issuer_label = "卖方" if item.get("commercial_direction") == "BUY_FROM_ISSUER" else "买方"
    lines = [
        f"{icon} <b>{_action_label(action)}</b> · {priority} · {trust}级 · {relevance}",
        f"<b>{title}</b>",
        "",
        f"🏛 {issuer_label}：{issuer}",
    ]
    if isinstance(quality_score, int) and quality_band:
        lines.append(f"🧭 Signal质量：<b>{quality_score}/100 · {quality_band}</b>")
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
        lines.append(f"📌 编号：{html.escape(reference)}")
    if focus_reference and focus_reference != reference:
        lines.append(f"🧩 相关分包：{html.escape(focus_reference)}")
    if reason:
        lines.append(f"🎯 为什么：{reason}")
    if scope:
        lines.append(f"📦 范围：{scope}")
    lines.append(f"🔎 证据：{evidence}")
    if signal_type:
        lines.append(f"📡 Signal：{signal_type}")
    if url:
        lines.append(f'🔗 <a href="{url}">官方来源</a>')

    text = "\n".join(lines)
    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        return text
    # Scope is the only intentionally lossy field in the transport renderer.
    overflow = len(text) - TELEGRAM_MESSAGE_LIMIT + 80
    shorter = scope[: max(0, len(scope) - overflow)].rstrip() + "…"
    lines = [line if not line.startswith("📦 范围：") else f"📦 范围：{shorter}" for line in lines]
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
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> dict[str, object]:
    target = database or db_path()
    now = (now or datetime.now(UTC)).astimezone(UTC)
    briefing = business_briefing(database=target, now=now)
    rows = briefing.get("attention") or []
    assert isinstance(rows, list)

    pending: list[dict[str, object]] = []
    with connect(target) as conn:
        for item in rows:
            if not isinstance(item, dict):
                continue
            signal_id = str(item.get("latest_signal_id") or "")
            if not signal_id:
                raise TelegramDeliveryError("attention item missing latest_signal_id")
            key = _delivery_key(item)
            exists = conn.execute("SELECT 1 FROM delivery_receipts WHERE delivery_key=?", (key,)).fetchone()
            if exists is not None:
                continue
            text = render_telegram_message(item)
            pending.append({**item, "delivery_key": key, "message": text, "payload_sha256": _payload_sha256(text)})

    if dry_run:
        return {
            "status": "PASS",
            "channel": CHANNEL,
            "dry_run": True,
            "pending_count": len(pending),
            "pending": pending,
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
        "sent": sent,
        "delivery_semantics": "AT_LEAST_ONCE_WITH_SUCCESS_RECEIPT_DEDUP",
    }
