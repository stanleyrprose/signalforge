#!/usr/bin/env python3
"""Deliver a Chinese newspaper Digest and full PDF through Bangkok SignalForge Bot.

Reads digest manifest staged from Mac. Telegram transport stays Bangkok-only;
not part of SignalForge tender Canonical / tender delivery table. One issue =
Digest messages (first) + one full PDF, both idempotent by paper/date and
original document SHA. A --digest-only mode exists for the already-sent R06 PDF.
"""
from __future__ import annotations

import argparse
import fcntl
import tempfile
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re

from newspaper_telegram_transport import _credentials, _send_document, _send_text

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
    if digest.get("schema_version") not in ("newspaper-digest-v1","newspaper-digest-v2"):
        raise ValueError("Unsupported newspaper digest schema")
    if digest.get("paper") not in ("km", "mal"):
        raise ValueError("Unknown official newspaper")
    try:
        datetime.strptime(str(digest["date"]), "%Y-%m-%d")
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("Invalid issue date") from exc
    if not re.fullmatch(r"[a-f0-9]{64}", str(digest.get("source_pdf_sha256") or "")):
        raise ValueError("Missing official issue digest")
    kind = digest.get("attachment_format", "pdf")
    if kind not in ("pdf", "markdown"):
        raise ValueError("Unsupported newspaper attachment format")
    basename_key = "edition_markdown_basename" if kind == "markdown" else "edition_pdf_basename"
    sha_key = "edition_markdown_sha256" if kind == "markdown" else "edition_pdf_sha256"
    limit = 2_000_000 if kind == "markdown" else MAX_BYTES
    if digest.get(basename_key) != pdf.name:
        raise ValueError("Digest is bound to a different attachment")
    if not pdf.is_file() or pdf.stat().st_size > limit:
        raise ValueError("Invalid or oversized edition PDF/Markdown")
    raw = pdf.read_bytes()
    if kind == "markdown":
        if pdf.suffix != ".md" or not raw.strip() or bytes([0]) in raw:
            raise ValueError("Invalid Markdown attachment")
        raw.decode("utf-8")
    elif not raw.startswith(b"%PDF-"):
        raise ValueError("Invalid or oversized edition PDF")
    if _sha256(pdf) != digest.get(sha_key):
        raise ValueError("PDF/Markdown was modified after digest generation")
    messages = digest.get("messages")
    selected = digest.get("selected")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 12:
        raise ValueError("Invalid digest message segmentation")
    if not isinstance(selected, list) or not 0 <= len(selected) <= 12:
        raise ValueError("Invalid digest item count")
    if not selected and (digest.get("schema_version") != "newspaper-digest-v2"
                         or digest.get("empty_digest_reason") != "NO_ELIGIBLE_DIGEST_STORY"):
        raise ValueError("Empty Digest requires an explicit no-eligible-story result")
    skipped = digest.get("unreadable_pages", [])
    if (not isinstance(skipped, list)
            or any(not isinstance(row, dict) or type(row.get("page")) is not int
                   or not 1 <= row["page"] <= digest.get("source_pages", 0)
                   or not isinstance(row.get("reason"), str) or not 1 <= len(row["reason"]) <= 160
                   for row in skipped)
            or len({row["page"] for row in skipped}) != len(skipped)):
        raise ValueError("Invalid unreadable-page markers")
    if digest.get("selected_count") != len(selected):
        raise ValueError("Digest item count mismatch")
    if digest.get("edition_news_count", 0) < digest["selected_count"]:
        raise ValueError("Digest exceeds edition article count")
    if digest.get("schema_version")=="newspaper-digest-v2":
        if digest.get("selection_method")!="AI_SEMANTIC_WITH_RULES":
            raise ValueError("V2 digest requires an AI assessment, no silent rules fallback")
        if digest.get("ai_assessed_count")!=digest["edition_news_count"]:
            raise ValueError("Incomplete AI assessment coverage")
        if digest.get("novelty_baseline") not in ("AVAILABLE","NO_HISTORY"):
            raise ValueError("Unverified novelty baseline")
        if not re.fullmatch(r"[0-9a-f]{64}",str(digest.get("ai_input_fingerprint") or "")):
            raise ValueError("AI source fingerprint missing")
        if any(
            not isinstance(x,dict) or
            x.get("novelty_status") not in ("NEW_DEVELOPMENT","REPEATED","UNKNOWN") or
            not isinstance(x.get("why_it_matters"),str) or
            len(x.get("why_it_matters",""))<10
            for x in selected
        ):
            raise ValueError("AI reason/novelty incomplete")
        if digest["novelty_baseline"]=="NO_HISTORY" and any(
            x["novelty_status"]!="UNKNOWN" for x in selected
        ):
            raise ValueError("Cannot claim novel developments without history")
    if len({x.get("publication_id") for x in selected if isinstance(x, dict)}) != len(selected):
        raise ValueError("Repeated or malformed article IDs")
    if not all(isinstance(message, str) and 0 < _utf16(message) <= 4096
               for message in messages):
        raise ValueError("Telegram digest message length invalid")


def _receipt_file(root: Path, digest: dict, *, preview: bool = False,
                  review_tag: str | None = None) -> Path:
    # Review editions (e.g. V2 replacing accepted V1) have their own receipt
    # namespace. Never overwrite a genuine delivered issue's receipt.
    if review_tag and (not preview or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,30}",review_tag)):
        raise ValueError("Review tag requires preview and a bounded slug")
    if preview:
        suffix = ("-"+review_tag) if review_tag else ""
        return (root / "human-review" / digest["schema_version"]
                / digest["paper"] / (digest["date"]+suffix+".json"))
    return root / digest["paper"] / (digest["date"] + ".json")


def _save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name + ".", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(state, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _send_issue(bundle: Path, pdf: Path, *, receipts: Path = DEFAULT_RECEIPTS,
               digest_only: bool = False, preview: bool = False,
               review_tag: str | None = None) -> dict:
    digest = json.loads(bundle.read_text(encoding="utf-8"))
    validate_bundle(digest, pdf)
    token, chat = _credentials()
    receipt_file = _receipt_file(receipts, digest, preview=preview,
                                 review_tag=review_tag)
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
    state.setdefault("coverage", {
        "source_pages": digest.get("source_pages"),
        "edition_news_count": digest["edition_news_count"],
        "unreadable_pages": digest.get("unreadable_pages", []),
    })
    kind = digest.get("attachment_format", "pdf")
    state.setdefault("attachment_format", kind)
    state.setdefault("attachment_sha256", _sha256(pdf))
    if state["attachment_format"] != kind or state["attachment_sha256"] != _sha256(pdf):
        raise RuntimeError("Issue attachment changed; manual release required")
    state.setdefault("messages", {})
    for index, part in enumerate(digest["messages"], 1):
        key = str(index)
        if key not in state["messages"]:
            # Provider outcome on timeout is ambiguous: operator should check
            # Telegram before retry; no unsafe blind automatic resend.
            label=(str(digest.get("editorial_policy_version") or "Digest").replace("digest-editorial-","")).upper()
            prefix=(f"🧪 新闻Digest {label} 人工验收｜R06完整中文版PDF不重发\n"
                    if preview else "")
            text=prefix+part
            if _utf16(text) > 4096:
                raise RuntimeError("Preview marker exceeded Telegram limit")
            state["messages"][key] = _send_text(token, chat, text)
            _save(receipt_file, state)
    body_key = "attachment_message_id" if kind == "markdown" else "pdf_message_id"
    if not digest_only and body_key not in state:
        label = str(digest.get("paper_label") or digest["paper"])
        skipped_count = len(digest.get("unreadable_pages", []))
        coverage = f"；{skipped_count}页无法读取，已标记跳过" if skipped_count else ""
        format_label = "Markdown" if kind == "markdown" else "PDF"
        caption = f"📰 {label} · {digest['date']} 中文新闻{format_label}（可读新闻全收录{coverage}；Digest已单独发送）"
        state[body_key] = _send_document(token, chat, pdf, caption)
        _save(receipt_file, state)
    return {
        "status": "SENT_OR_ALREADY_DELIVERED",
        "paper": digest["paper"], "date": digest["date"],
        "digest_parts": len(state["messages"]),
        "digest_ids": list(state["messages"].values()),
        "attachment_message_id": state.get(body_key),
        "attachment_format": kind,
        **({"pdf_message_id": state.get("pdf_message_id")} if kind == "pdf" else {}),
        "digest_only": digest_only,
    }


def send_issue(bundle: Path, pdf: Path, *, receipts: Path = DEFAULT_RECEIPTS,
               digest_only: bool = False, preview: bool = False,
               review_tag: str | None = None) -> dict:
    digest = json.loads(bundle.read_text(encoding="utf-8"))
    validate_bundle(digest, pdf)
    path = _receipt_file(receipts, digest, preview=preview, review_tag=review_tag)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.with_suffix(".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _send_issue(bundle, pdf, receipts=receipts, digest_only=digest_only,
                           preview=preview, review_tag=review_tag)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send Chinese newspaper Digest then full PDF via Bangkok")
    parser.add_argument("--digest", type=Path, required=True)
    parser.add_argument("--attachment", "--pdf", dest="pdf", type=Path, required=True)
    parser.add_argument("--digest-only", action="store_true",
                        help="For previously delivered complete PDF (e.g. approved R06)")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--review-tag", default=None,
                        help="Unique per-revision preview receipt slug; e.g. v2-1")
    args = parser.parse_args()
    print(json.dumps(send_issue(args.digest,args.pdf,
                               digest_only=args.digest_only,preview=args.preview,
                               review_tag=args.review_tag),
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
