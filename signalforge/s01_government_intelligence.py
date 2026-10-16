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


def intelligence_review_preview(database: Path) -> dict[str, object]:
    """Evidence-linked, Chinese review preview; never pretend English facts are translated."""
    with connect(database) as conn:
        rows = conn.execute(
            "SELECT identity,issuer,title,summary,category,evidence_sha256,review_status "
            "FROM government_intelligence_items WHERE source_id='S01' "
            "ORDER BY first_seen_at DESC, identity LIMIT 50"
        ).fetchall()
    items = []
    for row in rows:
        items.append({
            "identity": row[0], "发布单位（原文）": row[1],
            "公告标题（原文）": row[2], "内容（原文）": row[3],
            "类别": "政府资产出租" if row[4] == "STATE_ASSET_LEASE" else "政府公告",
            "证据SHA256": row[5], "审核状态": row[6],
            "中文翻译状态": "待翻译与人工验收",
        })
    return {"status": "REVIEW_ONLY", "count": len(items), "items": items}


def intelligence_coverage_audit(database: Path) -> dict[str, object]:
    """Account for all acquired S01 image candidates, including unreviewed and failed OCR."""
    with connect(database) as conn:
        has_images = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='s01_image_review'").fetchone()
        rows = conn.execute("SELECT review_status,COUNT(*) FROM s01_image_review GROUP BY review_status").fetchall() if has_images else []
        counts = {str(status): count for status, count in rows}
        reviewed = conn.execute("SELECT COUNT(*) FROM government_intelligence_items WHERE source_id='S01'").fetchone()[0]
    return {"source": "S01", "image_candidates": sum(counts.values()),
            "review_status_counts": counts, "verified_non_tender_items": reviewed,
            "coverage_complete": False,
            "limitations": "S01 tender listing images only; does not cover portal-wide government news"}


def render_intelligence_digest(database: Path) -> str:
    """Review draft, with clearly marked untranslated original fields."""
    preview = intelligence_review_preview(database)
    audit = intelligence_coverage_audit(database)
    lines = ["📰 S01 政府重要信息｜中文审核稿（禁止当作正式新闻推送）",
             f"已核实非招标公告：{preview['count']}；已发现图片候选：{audit['image_candidates']}；全站覆盖：未验证。"]
    for i, item in enumerate(preview["items"], 1):
        lines.extend([f"{i}. 【{item['类别']}】{item['公告标题（原文）']}",
                      f"发布单位：{item['发布单位（原文）']}",
                      f"内容（原文）：{item['内容（原文）']}",
                      f"证据 SHA256：{item['证据SHA256']}",
                      "中文译文：待生成／审核，不得将原文标为已翻译。"])
    if not preview["items"]:
        lines.append("本次没有可核实的非招标公告；不能据此认定官网没有重要新闻。")
    return "\n".join(lines)
