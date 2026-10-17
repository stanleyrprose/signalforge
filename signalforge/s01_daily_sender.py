"""Independent Bangkok sender for S01 all-news editions.

Explicit CLI only. Not registered with Tender Core scheduler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from signalforge.s01_daily_ledger import S01Ledger, edition_identity


def deliver(ledger_path: Path, manifest_path: Path, *, transport) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    day = manifest["date"]
    articles = [(item["identity"], item["detail_sha"]) for item in manifest["articles"]]
    edition = edition_identity(day, articles)
    if edition != manifest["edition_id"]:
        raise ValueError("edition hash mismatch")
    if not articles or len(articles) != len(set(articles)):
        raise ValueError("empty or duplicate article edition")
    pdf = manifest_path.parent / Path(manifest["pdf"]).name
    if not pdf.is_file() or hashlib.sha256(pdf.read_bytes()).hexdigest() != manifest["pdf_sha256"]:
        raise ValueError("PDF missing or checksum mismatch")
    ledger = S01Ledger(ledger_path)
    try:
        from signalforge.s01_daily_ledger import article_identity
        seen_identities = set()
        for entry in manifest["articles"]:
            identity, sha, url = entry["identity"], entry["detail_sha"], entry["url"]
            if identity in seen_identities:
                raise ValueError("multiple versions of same article in one edition")
            seen_identities.add(identity)
            if article_identity(url) != identity:
                raise ValueError("manifest URL/identity mismatch")
            row = ledger.db.execute("SELECT detail_sha,delivered_sha FROM articles WHERE identity=?",
                                    (identity,)).fetchone()
            same_edition = ledger.db.execute(
                "SELECT status FROM deliveries WHERE edition_id=? AND part='pdf'",
                (edition,)).fetchone()
            if row and row[1] == sha and not (same_edition and same_edition[0] == "SUCCESS"):
                raise ValueError("manifest includes already delivered article version")
            if row and row[0] != sha and row[1] != row[0]:
                raise ValueError("unresolved prior article version; reconcile before replacement")
            ledger.upsert_article(url, sha)
        if not articles:
            raise ValueError("empty edition must use a no-news status message, not an empty PDF")
        token, chat = transport._credentials()
        receipts = {}
        for part in ("digest", "pdf"):
            previous = ledger.db.execute(
                "SELECT status,message_id FROM deliveries WHERE edition_id=? AND part=?",
                (edition, part)).fetchone()
            if previous and previous[0] == "SUCCESS":
                receipts[part] = previous[1]
                continue
            if previous and previous[0] in ("UNKNOWN", "PENDING"):
                raise RuntimeError(f"{part}: unresolved prior attempt; reconcile before retry")
            ledger.record_delivery(edition, part, "PENDING")
            try:
                if part == "digest":
                    message_id = transport._send_text(token, chat, manifest["digest"])
                else:
                    message_id = transport._send_document(token, chat, pdf, manifest["caption"])
            except Exception:
                ledger.record_delivery(edition, part, "UNKNOWN")
                raise
            ledger.record_delivery(edition, part, "SUCCESS", message_id)
            receipts[part] = message_id
        ledger.mark_delivered(articles, edition)
        from signalforge.s01_daily_receipt import export_receipt
        receipt_path = manifest_path.with_suffix(".receipt.json")
        receipt = export_receipt(ledger_path, manifest_path, receipt_path)
        return {"edition_id": edition, "receipts": receipts, "articles": len(articles),
                "receipt_path": str(receipt_path),
                "manifest_sha256": receipt["manifest_sha256"], "status": "SUCCESS"}
    finally:
        ledger.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    from tools import newspaper_telegram_transport as transport
    print(json.dumps(deliver(args.ledger, args.manifest, transport=transport)))


if __name__ == "__main__":
    main()
