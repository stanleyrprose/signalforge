from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import db_path
from .db import connect, migrate
from .pilot_validation import PilotFeedbackError, record_pilot_feedback

CALLBACK_PREFIX = "sfp1"
CALLBACK_KEY_HEX_LENGTH = 32

_FEEDBACK_CODES = {
    "r": "RELEVANT",
    "n": "NOT_RELEVANT",
    "a": "ACTION_TAKEN",
}
_FEEDBACK_LABELS = {
    "RELEVANT": "👍 Relevant",
    "NOT_RELEVANT": "👎 Not Relevant",
    "ACTION_TAKEN": "🚀 Took Action",
}
_CALLBACK_RE = re.compile(r"^sfp1:([rna]):([0-9a-f]{32})$")


class TelegramFeedbackError(RuntimeError):
    pass


def feedback_callback_data(delivery_key: str, event_type: str) -> str:
    code = next((key for key, value in _FEEDBACK_CODES.items() if value == event_type), None)
    if code is None:
        raise TelegramFeedbackError(f"unsupported feedback event type: {event_type}")
    normalized = str(delivery_key).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise TelegramFeedbackError("pilot delivery_key must be a SHA-256 hex digest")
    return f"{CALLBACK_PREFIX}:{code}:{normalized[:CALLBACK_KEY_HEX_LENGTH]}"


def feedback_reply_markup(delivery_key: str) -> dict[str, object]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": _FEEDBACK_LABELS["RELEVANT"],
                    "callback_data": feedback_callback_data(delivery_key, "RELEVANT"),
                },
                {
                    "text": _FEEDBACK_LABELS["NOT_RELEVANT"],
                    "callback_data": feedback_callback_data(delivery_key, "NOT_RELEVANT"),
                },
            ],
            [
                {
                    "text": _FEEDBACK_LABELS["ACTION_TAKEN"],
                    "callback_data": feedback_callback_data(delivery_key, "ACTION_TAKEN"),
                }
            ],
        ]
    }


def parse_feedback_callback(data: object) -> tuple[str, str]:
    match = _CALLBACK_RE.fullmatch(str(data or ""))
    if match is None:
        raise TelegramFeedbackError("unsupported callback data")
    return _FEEDBACK_CODES[match.group(1)], match.group(2)


def record_feedback_callback(
    callback_query: dict[str, object],
    *,
    database: Path | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    target = database or db_path()
    migrate(target)
    event_type, delivery_prefix = parse_feedback_callback(callback_query.get("data"))

    actor = callback_query.get("from")
    actor_dict = actor if isinstance(actor, dict) else {}
    actor_id = str(actor_dict.get("id") or "").strip()
    if not actor_id:
        raise TelegramFeedbackError("callback query missing actor id")
    actor_username = str(actor_dict.get("username") or "").strip()

    message = callback_query.get("message")
    message_dict = message if isinstance(message, dict) else {}
    provider_message_id = str(message_dict.get("message_id") or "").strip()

    with connect(target) as conn:
        receipts = conn.execute(
            """
            SELECT delivery_key,profile_id,canonical_key,signal_id,provider_message_id
            FROM pilot_delivery_receipts
            WHERE delivery_key LIKE ?
            ORDER BY sent_at DESC
            LIMIT 2
            """,
            (delivery_prefix + "%",),
        ).fetchall()

    if not receipts:
        raise TelegramFeedbackError("pilot delivery receipt not found")
    if len(receipts) != 1:
        raise TelegramFeedbackError("pilot delivery prefix is ambiguous")

    receipt = receipts[0]
    stored_message_id = str(receipt["provider_message_id"] or "")
    if provider_message_id and stored_message_id and provider_message_id != stored_message_id:
        raise TelegramFeedbackError("callback message does not match pilot delivery receipt")

    recorded_by = f"telegram:{actor_id}"
    if actor_username:
        recorded_by += f":@{actor_username}"

    try:
        result = record_pilot_feedback(
            profile_id=str(receipt["profile_id"]),
            canonical_key=str(receipt["canonical_key"]),
            signal_id=str(receipt["signal_id"]),
            event_type=event_type,
            recorded_by=recorded_by,
            database=target,
            now=now,
        )
    except PilotFeedbackError as exc:
        raise TelegramFeedbackError(f"pilot feedback rejected: {exc}") from None
    return {
        "status": "RECORDED",
        "event_type": event_type,
        "profile_id": receipt["profile_id"],
        "canonical_key": receipt["canonical_key"],
        "signal_id": receipt["signal_id"],
        "delivery_key": receipt["delivery_key"],
        "event_id": result.get("event_id"),
    }


def _telegram_api(
    *,
    bot_token: str,
    method: str,
    payload: dict[str, object],
    timeout: int = 15,
) -> object:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{bot_token}/{method}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            envelope = json.loads(response.read(262144).decode("utf-8"))
    except HTTPError as exc:
        raise TelegramFeedbackError(f"telegram {method} HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise TelegramFeedbackError(f"telegram {method} transport failed") from None
    if not isinstance(envelope, dict) or envelope.get("ok") is not True:
        description = (
            str(envelope.get("description") or "API rejected request")
            if isinstance(envelope, dict)
            else "invalid API response"
        )
        raise TelegramFeedbackError(f"telegram {method} failed: {description}")
    return envelope.get("result")


def _bot_key(bot_token: str) -> str:
    return hashlib.sha256(bot_token.encode("utf-8")).hexdigest()[:16]


def telegram_feedback_poll(
    *,
    database: Path | None = None,
    bot_token: str | None = None,
    poll_timeout: int = 0,
) -> dict[str, object]:
    target = database or db_path()
    migrate(target)
    token = bot_token or os.environ.get("SIGNALFORGE_TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise TelegramFeedbackError("telegram credentials are not configured")

    webhook = _telegram_api(bot_token=token, method="getWebhookInfo", payload={})
    if isinstance(webhook, dict) and str(webhook.get("url") or "").strip():
        raise TelegramFeedbackError("telegram webhook is configured; getUpdates polling is disabled")

    bot_key = _bot_key(token)
    with connect(target) as conn:
        state = conn.execute(
            "SELECT last_update_id FROM telegram_update_state WHERE bot_key=?",
            (bot_key,),
        ).fetchone()
    last_update_id = int(state["last_update_id"]) if state is not None else -1

    payload: dict[str, object] = {
        "limit": 100,
        "timeout": max(0, min(int(poll_timeout), 50)),
        "allowed_updates": ["callback_query"],
    }
    if last_update_id >= 0:
        payload["offset"] = last_update_id + 1

    result = _telegram_api(
        bot_token=token,
        method="getUpdates",
        payload=payload,
        timeout=max(15, int(poll_timeout) + 10),
    )
    updates = result if isinstance(result, list) else []

    processed: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    ignored_count = 0
    max_update_id = last_update_id

    for update in updates:
        if not isinstance(update, dict):
            ignored_count += 1
            continue
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            max_update_id = max(max_update_id, update_id)

        callback = update.get("callback_query")
        if not isinstance(callback, dict):
            ignored_count += 1
            continue

        try:
            parse_feedback_callback(callback.get("data"))
        except TelegramFeedbackError:
            ignored_count += 1
            continue

        callback_id = str(callback.get("id") or "")
        try:
            recorded = record_feedback_callback(callback, database=target)
            processed.append(recorded)
            answer = {
                "RELEVANT": "已记录：相关",
                "NOT_RELEVANT": "已记录：不相关",
                "ACTION_TAKEN": "已记录：已采取行动",
            }.get(str(recorded.get("event_type") or ""), "已记录")
            if callback_id:
                _telegram_api(
                    bot_token=token,
                    method="answerCallbackQuery",
                    payload={"callback_query_id": callback_id, "text": answer},
                )
        except TelegramFeedbackError as exc:
            failures.append({"update_id": update_id, "error": str(exc)})
            if callback_id:
                _telegram_api(
                    bot_token=token,
                    method="answerCallbackQuery",
                    payload={"callback_query_id": callback_id, "text": "反馈未记录，请联系管理员"},
                )

    if max_update_id >= 0:
        updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        with connect(target) as conn, conn:
            conn.execute(
                """
                INSERT INTO telegram_update_state(bot_key,last_update_id,updated_at)
                VALUES (?,?,?)
                ON CONFLICT(bot_key) DO UPDATE SET
                    last_update_id=excluded.last_update_id,
                    updated_at=excluded.updated_at
                """,
                (bot_key, max_update_id, updated_at),
            )

    return {
        "status": "DEGRADED" if failures else "PASS",
        "updates_received": len(updates),
        "processed_count": len(processed),
        "ignored_count": ignored_count,
        "failed_count": len(failures),
        "last_update_id": max_update_id if max_update_id >= 0 else None,
        "processed": processed,
        "failures": failures,
    }
