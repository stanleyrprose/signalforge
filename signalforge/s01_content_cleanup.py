"""Receipt-gated removal of all S01 task content under its exact daily directory.

Owner policy 2026-10-25: retain only minimum identity/hash/coverage/receipt state,
not original HTML, per-day review DB, OCR, translations, PDFs or model files.
Tender Core and shared delivery ledgers are never removed.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sqlite3

from .s01_daily_ledger import S01Ledger


def cleanup_day(root: Path, day: str, edition: str) -> dict:
    if date.fromisoformat(day).isoformat() != day or not re.fullmatch(r"[a-f0-9]{64}", edition):
        raise ValueError("Invalid S01 daily cleanup identity")
    root = root.resolve(strict=True)
    index = root / "edition-index" / (edition + ".json")
    if not index.is_file():
        index = root / "daily-schedule" / (day + ".json")  # previous deployed version
    binding = json.loads(index.read_text(encoding="utf-8"))
    if binding.get("date") != day or binding.get("edition_id") != edition:
        raise ValueError("S01 cleanup date is not bound to the confirmed edition")
    ledger_path = root / "s01-delivery.sqlite"
    with sqlite3.connect("file:" + str(ledger_path) + "?mode=ro", uri=True) as conn:
        receipts = dict(conn.execute(
            "SELECT part,message_id FROM deliveries WHERE edition_id=? AND status='SUCCESS'",
            (edition,)).fetchall())
    if not all(type(receipts.get(part)) is int and receipts[part] > 0 for part in ("pdf", "digest")):
        raise ValueError("Both durable S01 message receipts required")
    folder = root / "evidence" / day
    if folder.is_symlink() or folder.resolve() != root / "evidence" / day:
        raise ValueError("Unsafe S01 task content root")
    proof = root / "content-cleanup" / (day + ".json")
    if proof.resolve() != root / "content-cleanup" / (day + ".json"):
        raise ValueError("Unsafe cleanup receipt path")
    previous = json.loads(proof.read_text(encoding="utf-8")) if proof.is_file() else {}
    summary = previous.get("coverage", {}) if previous.get("edition_id") == edition else {}
    audit = folder / "coverage-audit.json"
    if audit.is_file():
        data = json.loads(audit.read_text(encoding="utf-8"))
        summary = {key:data.get(key) for key in
                   ("total_discovered", "included", "excluded", "unresolved")}
    result = {"date":day, "edition_id":edition, "telegram":receipts,
              "coverage":summary, "status":"PENDING", "policy":"ALL_TASK_CONTENT_V1"}
    proof.parent.mkdir(parents=True, exist_ok=True)

    def save():
        tmp = proof.with_suffix(".tmp")
        tmp.write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(proof)

    save()
    try:
        ledger = S01Ledger(ledger_path)
        try:
            ledger.purge_delivered_review_content(edition)
        finally:
            ledger.close()
        if folder.exists():
            shutil.rmtree(folder)
    except (OSError, ValueError) as exc:
        result["reason"] = type(exc).__name__
    else:
        result["status"] = "ALL_TASK_CONTENT_REMOVED"
        result["completed_at"] = datetime.now(timezone.utc).isoformat()
    save()
    return result
