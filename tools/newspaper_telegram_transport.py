#!/usr/bin/env python3
"""Standalone Telegram transport for optional Chinese newspaper delivery.

This file is only imported by tools/send_newspaper_daily_digest_tg.py. It does
not import SignalForge's tender core or use its canonical/delivery database.
The existing Bangkok Bot/recipient remain configured by the operator.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import urllib.error
import urllib.request
import uuid

BOT_ENV = Path("/etc/signalforge/telegram.env")
MAX_DOCUMENT_BYTES = 18_000_000


def _credentials() -> tuple[str, str]:
    values: dict[str, str] = {}
    for raw in BOT_ENV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    token = values.get("SIGNALFORGE_TELEGRAM_BOT_TOKEN", "")
    chat = values.get("SIGNALFORGE_TELEGRAM_CHAT_ID", "")
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token) or not re.fullmatch(r"-?\d+", chat):
        raise RuntimeError("Existing SignalForge Bot/chat configuration missing")
    return token, chat


def _post(token: str, endpoint: str, payload: bytes, mime: str) -> int:
    if endpoint not in ("sendMessage", "sendDocument"):
        raise ValueError("Unsupported Telegram endpoint")
    request = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/" + endpoint,
        data=payload,
        headers={"Content-Type": mime},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            data = json.loads(response.read(65536))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram rejected request: HTTP {exc.code}") from None
    except Exception as exc:
        # Provider may have accepted a request before a connection failure.
        raise RuntimeError(f"Telegram outcome uncertain: {type(exc).__name__}") from None
    if not isinstance(data, dict) or data.get("ok") is not True:
        raise RuntimeError("Telegram returned unsuccessful response")
    return int(data["result"]["message_id"])


def _send_text(token: str, chat: str, message: str) -> int:
    payload = json.dumps({
        "chat_id": chat, "text": message, "disable_web_page_preview": True,
    }, ensure_ascii=False).encode("utf-8")
    return _post(token, "sendMessage", payload, "application/json")


def _send_document(token: str, chat: str, file: Path, caption: str) -> int:
    content = file.read_bytes()
    if not content.startswith(b"%PDF-") or len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("Telegram news edition must be a bounded PDF")
    boundary = "sf-news-edition-" + uuid.uuid4().hex
    pieces: list[bytes] = []
    for key, value in (("chat_id", chat), ("caption", caption)):
        pieces.append((
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n"
        ).encode("utf-8"))
    pieces.append((
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{file.name}\"\r\n"
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8"))
    pieces.extend((content, f"\r\n--{boundary}--\r\n".encode("utf-8")))
    return _post(token, "sendDocument", b"".join(pieces),
                 f"multipart/form-data; boundary={boundary}")
