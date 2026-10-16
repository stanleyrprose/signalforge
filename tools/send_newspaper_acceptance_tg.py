#!/usr/bin/env python3
"""Explicit manual-review Telegram dispatch on Bangkok, NOT tender publication.

Uses only the existing SignalForge Bot/chat secrets on the Bangkok host. Runs
one time on prepared, user-requested newspaper OCR sample artifacts. Durable
receipts prevent duplicated review prompts after an uncertain interruption.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
import uuid

BOT_ENV = Path("/etc/signalforge/telegram.env")
INPUT_ROOT = Path("/srv/signalforge/tmp/manual-newspaper-qa-20261016")
RECEIPTS = Path("/srv/signalforge/state/manual-newspaper-qa-20261016-receipts.json")
SPEC = (
    ("km", "R01", "《镜报》 Kyemon", "https://www.moi.gov.mm/km/file-download/download/public/5395", "64.87"),
    ("mal", "R02", "《缅甸之光》 Myanma Alinn", "https://www.moi.gov.mm/mal/file-download/download/public/5762", "69.31"),
)


def _credentials() -> tuple[str, str]:
    # Never print, transmit outside Telegram, or store raw credentials in receipts.
    vars_: dict[str, str] = {}
    for raw in BOT_ENV.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        vars_[key.strip()] = value.strip().strip("'\"")
    token = vars_.get("SIGNALFORGE_TELEGRAM_BOT_TOKEN", "")
    chat = vars_.get("SIGNALFORGE_TELEGRAM_CHAT_ID", "")
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token) or not re.fullmatch(r"-?\d+", chat):
        raise RuntimeError("SignalForge Telegram bot/chat configuration missing")
    return token, chat


def _persist(receipts: dict[str, int]) -> None:
    tmp = RECEIPTS.with_suffix(".tmp")
    tmp.write_text(json.dumps(receipts, sort_keys=True) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    os.replace(tmp, RECEIPTS)


def _send(*, token: str, endpoint: str, payload: bytes, mime: str) -> int:
    req = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/" + endpoint,
        data=payload,
        headers={"Content-Type": mime},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            answer = json.loads(resp.read(65536))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram rejected request: HTTP {exc.code}") from None
    except Exception as exc:
        # Outcome may be unknown; never blindly resend after connection errors.
        raise RuntimeError(f"Telegram outcome uncertain: {type(exc).__name__}") from None
    if answer.get("ok") is not True:
        raise RuntimeError("Telegram returned unsuccessful response")
    return int(answer["result"]["message_id"])


def _send_message(token: str, chat: str, message: str) -> int:
    data = json.dumps({
        "chat_id": chat,
        "text": message,
        "disable_web_page_preview": True,
    }, ensure_ascii=False).encode("utf-8")
    return _send(token=token, endpoint="sendMessage", payload=data, mime="application/json")


def _send_photo(token: str, chat: str, photo: Path, caption: str) -> int:
    image = photo.read_bytes()
    if len(image) > 9_000_000 or not image.startswith(b"\xff\xd8"):
        raise RuntimeError("Reviewer image is not a bounded JPEG")
    boundary = "sf-review-" + uuid.uuid4().hex
    pieces: list[bytes] = []
    for key, value in (("chat_id", chat), ("caption", caption)):
        pieces.append((
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n"
        ).encode("utf-8"))
    pieces.append((
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; "
        f"filename=\"{photo.name}\"\r\nContent-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8"))
    pieces.append(image)
    pieces.append((f"\r\n--{boundary}--\r\n").encode())
    return _send(
        token=token, endpoint="sendPhoto", payload=b"".join(pieces),
        mime=f"multipart/form-data; boundary={boundary}",
    )


def main() -> None:
    token, chat = _credentials()
    receipts = json.loads(RECEIPTS.read_text()) if RECEIPTS.exists() else {}
    for paper, item_id, name, source, confidence in SPEC:
        image = INPUT_ROOT / f"{paper}-p28.jpg"
        translation = INPUT_ROOT / f"{paper}-p28-zh.txt"
        if not image.is_file() or not translation.is_file():
            raise RuntimeError(f"{item_id} missing prepared review input")
        translated = translation.read_text(encoding="utf-8").strip()
        if not translated:
            raise RuntimeError(f"{item_id} empty translation sample")

        image_id = item_id + ".source_photo"
        if image_id not in receipts:
            caption = (
                f"📰 SignalForge 人工验收 {item_id}（非正式招标 Signal）\n"
                f"{name} · 2026-10-16 · 原报第28页\n"
                f"官方原版：{source}\n"
                "请对照下一条中文试译，重点核查漏字、错列和数字。"
            )
            receipts[image_id] = _send_photo(token, chat, image, caption)
            _persist(receipts)

        text_id = item_id + ".translation"
        if text_id not in receipts:
            body = (
                f"🧪 SignalForge 人工验收 {item_id}｜{name}\n"
                f"2026-10-16，第28页。OCR置信度 {confidence}%\n"
                "以下仅是该页约1100字原文的机器试译，并非整页或整期成品：\n\n"
                + translated[:2200]
                + "\n\n请核对上一条原文图。回复："
                + f"{item_id} PASS 或 {item_id} REVISE（指出漏译、错译、分栏或数字问题）。"
                + "\n本样本未审定，不会进入正式招标通知。"
            )
            receipts[text_id] = _send_message(token, chat, body)
            _persist(receipts)
    print(json.dumps({
        "telegram_provider": "existing SignalForge Bangkok VPS bot",
        "review_message_ids": receipts,
        "review_required": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
