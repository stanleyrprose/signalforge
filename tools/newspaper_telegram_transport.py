#!/usr/bin/env python3
"""Minimal newspaper-only Telegram transport using existing Bangkok credentials.

This module is not imported by SignalForge's tender scheduler or canonical
engine. Calls occur only from the explicitly invoked newspaper sender.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import urllib.error
import urllib.request
import uuid

BOT_ENV = Path("/etc/signalforge/telegram.env")
MAX_PDF_BYTES = 18_000_000


def _credentials() -> tuple[str, str]:
    values: dict[str, str] = {}
    for line in BOT_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    token = values.get("SIGNALFORGE_TELEGRAM_BOT_TOKEN", "")
    chat = values.get("SIGNALFORGE_TELEGRAM_CHAT_ID", "")
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token) or not re.fullmatch(r"-?\d+", chat):
        raise RuntimeError("Bangkok SignalForge Telegram bot/chat configuration missing")
    return token, chat


def _send(token: str, endpoint: str, data: bytes, mime: str, *, timeout: int = 45) -> int:
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{endpoint}", data=data,
        headers={"Content-Type": mime}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            answer = json.loads(response.read(65536))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram HTTP {exc.code}; check receipt before retry") from None
    except Exception as exc:
        raise RuntimeError(
            f"Telegram delivery outcome unknown ({type(exc).__name__}: {str(exc)[:160]}); do not blindly resend"
        ) from None
    if answer.get("ok") is not True:
        raise RuntimeError("Telegram rejected newspaper dispatch")
    return int(answer["result"]["message_id"])


def _send_text(token: str, chat: str, text: str) -> int:
    data = json.dumps(
        {"chat_id": chat, "text": text, "disable_web_page_preview": True},
        ensure_ascii=False,
    ).encode("utf-8")
    return _send(token, "sendMessage", data, "application/json")


def _send_document(token: str, chat: str, path: Path, caption: str) -> int:
    pdf = path.read_bytes()
    if len(pdf) > MAX_PDF_BYTES or not pdf.startswith(b"%PDF-"):
        raise RuntimeError("Invalid or oversized Chinese news PDF")
    boundary = "newspaper-" + uuid.uuid4().hex
    fields = []
    for name, value in (("chat_id", chat), ("caption", caption)):
        fields.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n"
            .encode("utf-8")
        )
    fields.extend([
        (f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; "
         f"filename=\"{path.name}\"\r\nContent-Type: application/pdf\r\n\r\n").encode("utf-8"),
        pdf,
        (f"\r\n--{boundary}--\r\n").encode("utf-8"),
    ])
    return _send(token, "sendDocument", b"".join(fields),
                 f"multipart/form-data; boundary={boundary}", timeout=120)
