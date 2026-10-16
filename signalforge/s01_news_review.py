"""S01 news listing acquisition and evidence-preserving review staging.

This is a separate news surface, not the canonical tender pipeline.
TLS-unverified listings are hints, never verified government statements.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .db import connect
from .http import fetch_s01_news_unverified_tls
from .s01_news_discovery import NEWS_URL, parse_news_discovery


def acquire_news_review(database: Path, evidence_dir: Path, *, payload: bytes | None = None) -> dict:
    if payload is None:
        payload = fetch_s01_news_unverified_tls(NEWS_URL)
    sha = hashlib.sha256(payload).hexdigest()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / f"s01-news-listing-{sha}.html"
    if not evidence_path.exists():
        evidence_path.write_bytes(payload)
    candidates = parse_news_discovery(payload)
    now = datetime.now(UTC).isoformat()
    with connect(database) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS s01_news_review (
          url TEXT PRIMARY KEY, title_hint TEXT NOT NULL, listing_sha256 TEXT NOT NULL,
          listing_evidence_path TEXT NOT NULL, review_status TEXT NOT NULL,
          first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL)""")
        for item in candidates:
            conn.execute("""INSERT INTO s01_news_review VALUES (?,?,?,?,?,?,?)
              ON CONFLICT(url) DO UPDATE SET title_hint=excluded.title_hint,
              listing_sha256=excluded.listing_sha256,
              listing_evidence_path=excluded.listing_evidence_path,
              last_seen_at=excluded.last_seen_at""",
              (item['url'], item['title_hint'], sha, str(evidence_path),
               'DETAIL_EVIDENCE_REQUIRED', now, now))
    return {'status': 'REVIEW_ONLY', 'listing_sha256': sha, 'listing_evidence_path': str(evidence_path),
            'candidates_in_listing': len(candidates), 'verified_news': 0, 'telegram_sent': 0}


def news_review_digest(database: Path, *, limit: int = 30) -> str:
    with connect(database) as conn:
        rows = conn.execute("SELECT title_hint,url,listing_sha256 FROM s01_news_review ORDER BY last_seen_at DESC,url LIMIT ?", (limit,)).fetchall()
    lines = ['S01 官方门户新闻｜待审核清单',
             '以下仅为TLS未验证的列表标题，未验证原发布机构及正文；不构成正式中文新闻。']
    for i, (title, url, sha) in enumerate(rows, 1):
        lines.extend([f'{i}. {title}', f'原始链接：{url}', f'列表证据SHA256：{sha}'])
    return '\n'.join(lines)
