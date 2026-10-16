#!/usr/bin/env python3
"""Deliver a Chinese newspaper Digest and full PDF through Bangkok SignalForge Bot.

Reads digest manifest staged from Mac. Telegram transport stays Bangkok-only;
not part of SignalForge tender Canonical / tender delivery table. One issue =
Digest messages (first) + one full PDF, both idempotent by paper/date and
original document SHA. A --digest-only mode exists for the already-sent R06 PDF.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re

from send_newspaper_acceptance_tg import _credentials
from send_newspaper_news_review_tg import _send_document, _send_text

DEFAULT_RECEIPTS = Path("/srv/signalforge/state/newspaper-digest-receipts")
MAX_BYTES = 18_000_000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utf16(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def validate_bundle(digest: dict, pdf: Path) -> None:
    if digest.get("schema_version") != "newspaper-digest-v1":
        raise ValueError("Unsupported newspaper digest schema")
    if digest.get("paper") not in ("km", "mal"):
        raise ValueError("Unknown official newspaper")
    try:
        datetime.strptime(str(digest["date"]), "%Y-%m-%d")
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("Invalid issue date") from exc
    if not re.fullmatch(r"[a-f0-9]{64}", str(digest.get("source_pdf_sha256") or "")):
        raise ValueError("Missing official issue digest")
    if digest.get("edition_pdf_basename") != pdf.name:
        raise ValueError("Digest is bound to a different PDF")
    if not pdf.is_file() or pdf.stat().st_size > MAX_BYTES:
        raise ValueError("Invalid or oversized edition PDF")
    with pdf.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise ValueError("Invalid or oversized edition PDF")
    if _sha256(pdf) != digest.get("edition_pdf_sha256"):
        raise ValueError("PDF was modified after digest generation")
    messages = digest.get("messages")
    selected = digest.get("selected")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 12:
        raise ValueError("Invalid digest message segmentation")
    if not isinstance(selected, list) or not 1 <= len(selected) <= 12:
        raise ValueError("Invalid digest item count")
    if digest.get("selected_count") != len(selected):
        raise ValueError("Digest item count mismatch")
    if digest.get("edition_news_count", 0) < digest["selected_count"]:
        raise ValueError("Digest exceeds edition article count")
    if len({x.get("publication_id") for x in selected if isinstance(x, dict)}) != len(selected):
        raise ValueError("Repeated or malformed article IDs")
    if not all(isinstance(message, str) and 0 < _utf16(message) <= 4096
               for message in messages):
        raise ValueError("Telegram digest message length invalid")


def _receipt_file(root: Path, digest: dict) -> Path:
    # All IDs and dates used to construct filename have already been validated.
    return root / digest["paper"] / (digest["date"] + ".json")


def _save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temp.chmod(0o600)
    os.replace(temp, path)


def send_issue(bundle: Path, pdf: Path, *, receipts: Path = DEFAULT_RECEIPTS,
               digest_only: bool = False, preview: bool = False) -> dict:
    digest = json.loads(bundle.read_text(encoding="utf-8"))
    validate_bundle(digest, pdf)
    token, chat = _credentials()
    receipt_file = _receipt_file(receipts, digest)
    digest_hash = _sha256(bundle)
    state = json.loads(receipt_file.read_text(encoding="utf-8")) if receipt_file.is_file() else {}
    if state and (
        state.get("source_pdf_sha256") != digest["source_pdf_sha256"]
        or state.get("edition_pdf_sha256") != digest["edition_pdf_sha256"]
    ):
        raise RuntimeError("Issue PDF was changed since previous delivery; manual release required")
    if state.get("digest_sha256") not in (None, digest_hash):
        raise RuntimeError("Digest was revised after delivery; do not auto-resend")
    state.setdefault("source_pdf_sha256", digest["source_pdf_sha256"])
    state.setdefault("edition_pdf_sha256", digest["edition_pdf_sha256"])
    state.setdefault("digest_sha256", digest_hash)
    state.setdefault("messages", {})
    for index, part in enumerate(digest["messages"], 1):
        key = str(index)
        if key not in state["messages"]:
            # Provider outcome on timeout is ambiguous: operator should check
            # Telegram before retry; no unsafe blind automatic resend.
            text = ("🧪 新闻Digest试运行（R06中文版已单独发送）\n" if preview else "") + part
            if _utf16(text) > 4096:
                raise RuntimeError("Preview marker exceeded Telegram limit")
            state["messages"][key] = _send_text(token, chat, text)
            _save(receipt_file, state)
    if not digest_only and "pdf_message_id" not in state:
        label = str(digest.get("paper_label") or digest["paper"])
        caption = f"📰 {label} · {digest['date']} 全量中文新闻PDF（非Top精选；Digest已单独发送）"
        state["pdf_message_id"] = _send_document(token, chat, pdf, caption)
        _save(receipt_file, state)
    return {
        "status": "SENT_OR_ALREADY_DELIVERED",
        "paper": digest["paper"], "date": digest["date"],
        "digest_parts": len(state["messages"]),
        "digest_ids": list(state["messages"].values()),
        "pdf_message_id": state.get("pdf_message_id"),
        "digest_only": digest_only,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Send Chinese newspaper Digest then full PDF via Bangkok")
    parser.add_argument("--digest", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--digest-only", action="store_true",
                        help="For previously delivered complete PDF (e.g. approved R06)")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    print(json.dumps(send_issue(args.digest,args.pdf,
                               digest_only=args.digest_only,preview=args.preview),
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
