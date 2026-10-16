"""Separate, review-only Government Intelligence records from approved S01 evidence.

Never writes tender canonical items, signals or Telegram receipts.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from .config import repo_root
from .db import connect
from .s01_reviewed_tenders import _review_manifest


def refresh_s01_government_intelligence(database: Path, *, root: Path | None = None) -> dict[str, object]:
    """Stage independently reviewed non-tender official-image facts for digest review."""
    records = _review_manifest(root or repo_root())
    now = datetime.now(UTC).isoformat()
    candidates = 0
    excluded = 0
    with connect(database) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS government_intelligence_items (
            identity TEXT PRIMARY KEY, source_id TEXT NOT NULL,
            evidence_sha256 TEXT NOT NULL, issuer TEXT NOT NULL,
            title TEXT NOT NULL, summary TEXT NOT NULL,
            category TEXT NOT NULL, review_status TEXT NOT NULL,
            first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
        )""")
        for digest, record in records.items():
            if record.get("formal_procurement_tender") is not False:
                excluded += 1
                continue
            title = str(record.get("title") or "").strip()
            issuer = str(record.get("issuer") or "").strip()
            summary = str(record.get("scope_summary") or "").strip()
            if not (title and issuer and summary):
                excluded += 1
                continue
            category = "STATE_ASSET_LEASE" if "lease" in title.lower() or "rental" in summary.lower() else "GOVERNMENT_NOTICE"
            identity = "s01-intelligence:" + hashlib.sha256((issuer + "|" + title).encode()).hexdigest()[:24]
            conn.execute("""INSERT INTO government_intelligence_items
                (identity,source_id,evidence_sha256,issuer,title,summary,category,review_status,first_seen_at,last_seen_at)
                VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(identity) DO UPDATE SET
                last_seen_at=excluded.last_seen_at""",
                (identity, "S01", digest, issuer, title, summary, category,
                 "HUMAN_DIGEST_REVIEW_REQUIRED", now, now))
            candidates += 1
    return {"status": "REVIEW_ONLY", "candidates": candidates, "excluded_tender_or_incomplete": excluded,
            "telegram_sent": 0}
