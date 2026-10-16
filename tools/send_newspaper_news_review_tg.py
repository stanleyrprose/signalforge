#!/usr/bin/env python3
"""One-time R03/R04 newspaper NEWS-ONLY editorial review through Bangkok SF Bot.

Staging script. Not a tender alert, does not write SignalForge canonical/receipts.
Keeps separate idempotency receipts; do not rerun after an ambiguous Telegram
connection failure until the Telegram chat has been manually inspected.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import uuid
from send_newspaper_acceptance_tg import _credentials, _send

ROOT = Path("/srv/signalforge/tmp/manual-newspaper-news-qa-20261016")
RECEIPTS = Path("/srv/signalforge/state/manual-newspaper-news-qa-20261016-receipts.json")
ENTRIES = (
    ("R03", "《镜报》Kyemon", "https://www.moi.gov.mm/km/file-download/download/public/5395",
     "2条：免费医疗巡诊；佛学考试通知", "镇区名称OCR待核"),
    ("R04", "《缅甸之光》Myanma Alinn", "https://www.moi.gov.mm/mal/file-download/download/public/5762",
     "1篇：农业创新与粮食安全（社论）", "请核对社论主张是否译得准确"),
)


def _send_document(token: str, chat: str, path: Path, caption: str) -> int:
    pdf = path.read_bytes()
    if not pdf.startswith(b"%PDF-") or len(pdf) > 18_000_000:
        raise RuntimeError("Invalid or unbounded PDF review attachment")
    boundary = "sf-newsqa-" + uuid.uuid4().hex
    parts = []
    for name, value in (("chat_id", chat), ("caption", caption)):
        parts.append((
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n"
        ).encode("utf-8"))
    parts.append((
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{path.name}\"\r\n"
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8"))
    parts.append(pdf)
    parts.append((f"\r\n--{boundary}--\r\n").encode("utf-8"))
    return _send(token=token, endpoint="sendDocument", payload=b"".join(parts),
                 mime=f"multipart/form-data; boundary={boundary}")


def _send_text(token: str, chat: str, text: str) -> int:
    data = json.dumps({"chat_id": chat, "text": text,
                       "disable_web_page_preview": True}, ensure_ascii=False).encode("utf-8")
    return _send(token=token, endpoint="sendMessage", payload=data, mime="application/json")


def _persist(state: dict[str, int]) -> None:
    tmp = RECEIPTS.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    os.replace(tmp, RECEIPTS)


def main() -> None:
    token, chat = _credentials()
    state = json.loads(RECEIPTS.read_text(encoding="utf-8")) if RECEIPTS.exists() else {}
    for code, paper, official_url, headlines, issue in ENTRIES:
        src = ROOT / f"{code}-source.pdf"
        zh = ROOT / f"{code}-news-zh.pdf"
        if not src.is_file() or not zh.is_file():
            raise RuntimeError("Manual news QA input missing: " + code)
        for key, file, caption in (
            (code + ".source", src, f"📰 {code} {paper} 原版新闻页 1–2（供比对）"),
            (code + ".news", zh, f"🗞️ {code} {paper} 全新【中文新闻编辑版】审核样稿"),
        ):
            if key not in state:
                state[key] = _send_document(token, chat, file, caption)
                _persist(state)
        key = code + ".instructions"
        if key not in state:
            text = (
                f"🧪 SignalForge 新闻版重新验收 {code}\n"
                f"报纸：{paper} · 日期：2026-10-16\n"
                f"新版仅保留新闻/社论，不再逐页照搬排版。\n"
                f"本轮处理官方前2页/整份32页，属于新版样稿，尚非整期完成品。\n"
                f"识别新闻：{headlines}\n"
                "广告、房产/遗失声明、商业祝福等不进入中文样稿。\n"
                f"重点关注：{issue}。\n"
                f"原版链接：{official_url}\n\n"
                f"请对照刚才发送的两份PDF回复：{code} PASS 或 "
                f"{code} REVISE（列出需修改的新闻选择、表述或排版）。\n"
                "本消息为人工审核，不是正式招标Signal。此前R01/R02已被新版取代。"
            )
            state[key] = _send_text(token, chat, text)
            _persist(state)
    print(json.dumps({"status": "SENT", "telegram_bot": "SignalForge Bangkok",
                      "review_receipts": state}, ensure_ascii=False))


if __name__ == "__main__":
    main()
