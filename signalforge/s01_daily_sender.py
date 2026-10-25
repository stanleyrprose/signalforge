"""Independent Bangkok sender for S01 all-news editions.

Explicit CLI only. Not registered with Tender Core scheduler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from signalforge.s01_daily_ledger import S01Ledger, edition_identity
from signalforge.s01_attachment import attachment_part, verify_attachment


def failure_status(exc: Exception) -> str:
    import re
    return "FAILED" if re.search(r"Telegram HTTP 4\d\d", str(exc)) else "UNKNOWN"


def failure_reason(exc: Exception) -> str:
    import re
    code = re.search(r"Telegram HTTP (\d{3})", str(exc))
    if code:
        return f"Telegram 明确拒绝请求，HTTP {code.group(1)}" if code.group(1).startswith("4") else f"Telegram HTTP {code.group(1)}，送达结果未知"
    if "timeout" in str(exc).lower() or "timed out" in str(exc).lower():
        return "Telegram 请求超时，送达结果未知"
    return f"Telegram 传输异常（{type(exc).__name__}），送达结果未知"


def deliver(ledger_path: Path, manifest_path: Path, *, transport, digest_only: bool = False) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    day = manifest["date"]
    articles = [(item["identity"], item["detail_sha"]) for item in manifest["articles"]]
    edition = edition_identity(day, articles)
    if edition != manifest["edition_id"]:
        raise ValueError("edition hash mismatch")
    if not articles or len(articles) != len(set(articles)):
        raise ValueError("empty or duplicate article edition")
    document_part = attachment_part(manifest)
    ledger = S01Ledger(ledger_path)
    try:
        from signalforge.s01_daily_ledger import article_identity
        seen_identities = set()
        delivered = ledger.delivered_versions()
        from signalforge.s01_daily_ledger import review_metadata
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
                "SELECT status FROM deliveries WHERE edition_id=? AND part=?",
                (edition, document_part)).fetchone()
            if row and row[1] == sha and not (same_edition and same_edition[0] == "SUCCESS"):
                raise ValueError("manifest includes already delivered article version")
            if row and row[0] != sha and row[1] != row[0]:
                raise ValueError("unresolved prior article version; reconcile before replacement")
            metadata = review_metadata(entry)
            if (metadata and metadata["content_sha256"] in delivered.get(identity, {}).get("content", set())
                    and not (same_edition and same_edition[0] == "SUCCESS")):
                raise ValueError("manifest includes already delivered article content")
        for entry in manifest["articles"]:
            ledger.upsert_article(entry["url"], entry["detail_sha"], review=review_metadata(entry))
        if not articles:
            raise ValueError("empty edition must use a no-news status message, not an empty PDF")
        token, chat = transport._credentials()
        receipts, failures = {}, {}
        # Attempt each component independently; never resend a successful component.
        def notify(part, reason):
            notice_part = "failure_notice:" + part
            previous = ledger.db.execute(
                "SELECT status FROM deliveries WHERE edition_id=? AND part=?",
                (edition, notice_part)).fetchone()
            if previous and previous[0] in ("SUCCESS", "PENDING", "UNKNOWN"):
                return
            ledger.record_delivery(edition, notice_part, "PENDING")
            text = (f"⚠️ S01 新闻日报投递未完成｜{day}\n"
                    f"失败部分：{part}\n原因：{reason}\n"
                    "Digest 与正文附件独立投递；成功部分不重复发送。"
                    "结果未知的部分暂停自动重发，恢复文件继续保留。")
            try:
                mid = transport._send_text(token, chat, text)
            except Exception as exc:
                ledger.record_delivery(edition, notice_part, failure_status(exc))
            else:
                ledger.record_delivery(edition, notice_part, "SUCCESS", mid)

        for part in (("digest",) if digest_only else ("digest", document_part)):
            previous = ledger.db.execute(
                "SELECT status,message_id FROM deliveries WHERE edition_id=? AND part=?",
                (edition, part)).fetchone()
            if previous and previous[0] == "SUCCESS":
                receipts[part] = previous[1]
                continue
            if previous and previous[0] in ("UNKNOWN", "PENDING"):
                failures[part] = "此前请求结果未知，需核对原消息，未重复发送"
                notify(part, failures[part])
                continue
            # Validate payload after the independent Digest attempt.
            try:
                payload = verify_attachment(manifest, manifest_path.parent) if part != "digest" else None
            except (OSError, ValueError, KeyError):
                ledger.record_delivery(edition, part, "FAILED")
                failures[part] = "正文附件缺失或 SHA256 校验不符"
                notify(part, failures[part])
                continue
            ledger.record_delivery(edition, part, "PENDING")
            try:
                if part == "digest":
                    message_id = transport._send_text(token, chat, manifest["digest"])
                else:
                    message_id = transport._send_document(token, chat, payload, manifest["caption"])
            except Exception as exc:
                ledger.record_delivery(edition, part, failure_status(exc))
                failures[part] = failure_reason(exc)
                notify(part, failures[part])
                continue
            ledger.record_delivery(edition, part, "SUCCESS", message_id)
            receipts[part] = message_id
        if digest_only:
            return {"edition_id": edition, "receipts": receipts, "failures": failures,
                    "status": "DIGEST_ONLY"}
        if failures:
            return {"edition_id": edition, "receipts": receipts, "failures": failures,
                    "status": "PARTIAL"}
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
    parser.add_argument("--digest-only", action="store_true")
    args = parser.parse_args()
    from tools import newspaper_telegram_transport as transport
    import fcntl
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    with args.ledger.with_suffix(".sender.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        result = deliver(args.ledger, args.manifest, transport=transport, digest_only=args.digest_only)
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] not in ("SUCCESS", "DIGEST_ONLY"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
