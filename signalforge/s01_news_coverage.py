"""Coverage reconciliation for S01 review-only government news.

A news item cannot silently disappear between discovery, detail extraction,
and Chinese digest preparation. Unknown disposition remains an explicit blocker.
"""
from __future__ import annotations

import json
from pathlib import Path

from .db import connect


def coverage_reconciliation(database: Path, output: Path | None = None) -> dict:
    with connect(database) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS s01_news_detail_review (
          url TEXT PRIMARY KEY, detail_sha256 TEXT NOT NULL,
          detail_evidence_path TEXT NOT NULL, body_text TEXT NOT NULL,
          body_chars INTEGER NOT NULL, review_status TEXT NOT NULL,
          acquired_at TEXT NOT NULL)""")
        rows = conn.execute("""SELECT n.url, n.title_hint, n.listing_sha256,
                   d.detail_sha256, d.body_chars, d.review_status
                   FROM s01_news_review n
                   LEFT JOIN s01_news_detail_review d ON d.url=n.url
                   ORDER BY n.url""").fetchall()
    items = []
    for row in rows:
        url, title, listing_sha, detail_sha, chars, status = tuple(row)
        disposition = "TRANSLATION_PENDING" if detail_sha and chars and chars >= 100 else "DETAIL_REQUIRED"
        items.append({"url": url, "title_hint": title, "listing_sha256": listing_sha,
                      "detail_sha256": detail_sha, "body_chars": chars or 0,
                      "detail_status": status, "disposition": disposition,
                      "digest_included": False, "exclusion_reason": None})
    report = {"total_discovered": len(items),
              "detail_ready": sum(i["disposition"] == "TRANSLATION_PENDING" for i in items),
              "detail_required": sum(i["disposition"] == "DETAIL_REQUIRED" for i in items),
              "digest_included": 0, "unresolved": len(items),
              "digest_publish_gate": "BLOCKED_PENDING_TRANSLATION_AND_REVIEW",
              "items": items}
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
