"""Receipt bridge: Bangkok exports a checksum-bound receipt, Mac imports it.

Transport of this JSON is external; neither machine needs access to the other's DB.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .s01_daily_ledger import S01Ledger, article_identity, edition_identity


def export_receipt(ledger_path: Path, manifest_path: Path, output: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["articles"]
    pairs = [(e["identity"], e["detail_sha"]) for e in entries]
    edition = edition_identity(manifest["date"], pairs)
    if edition != manifest["edition_id"] or not pairs:
        raise ValueError("invalid manifest edition")
    if len(set(pairs)) != len(pairs) or len({identity for identity, _ in pairs}) != len(pairs):
        raise ValueError("duplicate manifest article identity")
    for entry in entries:
        if article_identity(entry["url"]) != entry["identity"]:
            raise ValueError("article identity mismatch")
    ledger = S01Ledger(ledger_path)
    try:
        rows = dict(ledger.db.execute(
            "SELECT part,message_id FROM deliveries WHERE edition_id=? AND status='SUCCESS'",
            (edition,)).fetchall())
        if not all(type(rows.get(part)) is int and rows[part] > 0
                   for part in ("digest", "pdf")):
            raise ValueError("both successful Telegram receipts required")
        receipt = {
            "date": manifest["date"], "edition_id": edition,
            "articles": entries, "telegram": rows,
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        return receipt
    finally:
        ledger.close()


def import_receipt(ledger_path: Path, manifest_path: Path, receipt_path: Path) -> dict:
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    pdf = manifest_path.parent / Path(manifest["pdf"]).name
    if not pdf.is_file() or hashlib.sha256(pdf.read_bytes()).hexdigest() != manifest["pdf_sha256"]:
        raise ValueError("local PDF missing or checksum mismatch")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    pairs = [(e["identity"], e["detail_sha"]) for e in manifest["articles"]]
    edition = edition_identity(manifest["date"], pairs)
    if not pairs or edition != manifest["edition_id"]:
        raise ValueError("invalid manifest")
    if receipt["edition_id"] != edition or receipt["date"] != manifest["date"]:
        raise ValueError("receipt edition mismatch")
    if receipt["manifest_sha256"] != hashlib.sha256(manifest_bytes).hexdigest():
        raise ValueError("receipt manifest checksum mismatch")
    if receipt["articles"] != manifest["articles"]:
        raise ValueError("receipt article list mismatch")
    for entry in manifest["articles"]:
        if article_identity(entry["url"]) != entry["identity"]:
            raise ValueError("article identity mismatch")
    if len(set(pairs)) != len(pairs) or len({identity for identity, _ in pairs}) != len(pairs):
        raise ValueError("duplicate article identity")
    telegram = receipt["telegram"]
    if not all(type(telegram.get(part)) is int and telegram[part] > 0
               for part in ("digest", "pdf")):
        raise ValueError("invalid Telegram receipt")
    ledger = S01Ledger(ledger_path)
    try:
        # Reject conflicting revisions instead of overwriting newer local state.
        for entry in manifest["articles"]:
            row = ledger.db.execute(
                "SELECT detail_sha,delivered_sha FROM articles WHERE identity=?", (entry["identity"],)).fetchone()
            if row and row[0] != entry["detail_sha"] and row[1] != row[0]:
                raise ValueError("local article revision conflict")
        for entry in manifest["articles"]:
            from .s01_daily_ledger import review_metadata
            ledger.upsert_article(entry["url"], entry["detail_sha"], review=review_metadata(entry))
        for part in ("digest", "pdf"):
            ledger.record_delivery(edition, part, "SUCCESS", telegram[part])
        ledger.mark_delivered(pairs, edition)
        return {"status": "RECEIPT_IMPORTED", "edition_id": edition, "articles": len(pairs)}
    finally:
        ledger.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("export", "import"))
    parser.add_argument("ledger", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    result = (export_receipt(args.ledger, args.manifest, args.receipt)
              if args.mode == "export"
              else import_receipt(args.ledger, args.manifest, args.receipt))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
