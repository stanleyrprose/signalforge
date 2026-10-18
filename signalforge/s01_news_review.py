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
from .s01_news_detail import acquire_detail
from .s01_news_pagination import pagination_urls


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

def acquire_news_details(database: Path, evidence_dir: Path, *, limit: int = 60) -> dict:
    """Acquire evidence for staged S01 news, without promoting to verified news."""
    with connect(database) as conn:
        rows = conn.execute(
            "SELECT url FROM s01_news_review ORDER BY last_seen_at DESC, url LIMIT ?",
            (limit,),
        ).fetchall()
    with connect(database) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS s01_news_detail_review (
          url TEXT PRIMARY KEY, detail_sha256 TEXT NOT NULL,
          detail_evidence_path TEXT NOT NULL, body_text TEXT NOT NULL,
          body_chars INTEGER NOT NULL, review_status TEXT NOT NULL,
          acquired_at TEXT NOT NULL)""")
    completed = 0
    failed = []
    for (url,) in rows:
        try:
            detail = acquire_detail(url, evidence_dir)
            with connect(database) as conn, conn:
                conn.execute("""INSERT INTO s01_news_detail_review VALUES (?,?,?,?,?,?,?)
                  ON CONFLICT(url) DO UPDATE SET detail_sha256=excluded.detail_sha256,
                  detail_evidence_path=excluded.detail_evidence_path,
                  body_text=excluded.body_text, body_chars=excluded.body_chars,
                  review_status=excluded.review_status, acquired_at=excluded.acquired_at""",
                  (url, detail['detail_sha256'], detail['detail_evidence_path'],
                   detail['body_text'], detail['body_chars'], detail['status'],
                   datetime.now(UTC).isoformat()))
            completed += 1
        except Exception as exc:
            failed.append({'url': url, 'error': str(exc)[:200]})
    return {'candidates': len(rows), 'details_saved': completed,
            'failed': failed, 'verified_news': 0, 'telegram_sent': 0}

def acquire_paginated_news_review(database: Path, evidence_dir: Path, *, max_pages: int = 5) -> dict:
    """Discover pages using observed links; record page-by-page coverage."""
    if not 1 <= max_pages <= 20:
        raise ValueError("max_pages must be between 1 and 20")
    queue = [NEWS_URL]
    seen_pages = set()
    seen_articles = set()
    audit = []
    fetch_attempts = {}
    while queue and len(seen_pages) < max_pages:
        url = queue.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        payload = None
        error = None
        for attempt in range(1, 4):
            try:
                payload = fetch_s01_news_unverified_tls(url)
                break
            except Exception as exc:
                error = exc
        fetch_attempts[url] = attempt
        if payload is None:
            audit.append({"page_url": url, "status": "FETCH_FAILED", "error": str(error)[:200],
                          "attempts": attempt, "candidates": 0, "duplicates": 0, "new_candidates": 0})
            continue
        candidates = parse_news_discovery(payload, base_url=url)
        links = {c["url"] for c in candidates}
        duplicates = len(links & seen_articles)
        seen_articles.update(links)
        result = acquire_news_review(database, evidence_dir, payload=payload)
        audit.append({"page_url": url, "listing_sha256": result["listing_sha256"],
                      "candidates": len(candidates), "attempts": attempt, "duplicates": duplicates,
                      "new_candidates": len(links) - duplicates})
        for next_url in pagination_urls(payload, base_url=url, max_pages=max_pages):
            if next_url not in seen_pages and next_url not in queue:
                queue.append(next_url)
    report = {"pages": audit, "pages_fetched": len(audit),
              "page_limit": max_pages, "unfetched_page_urls": sorted(set(queue) - seen_pages),
              "pagination_incomplete": bool(set(queue) - seen_pages) or any(
                  p.get("status") == "FETCH_FAILED" for p in audit),
              "total_candidates": sum(p["candidates"] for p in audit),
              "unique_candidates": len(seen_articles),
              "candidate_urls": sorted(seen_articles),
              "duplicate_candidates": sum(p["duplicates"] for p in audit),
              "verified_news": 0, "telegram_sent": 0}
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "s01-news-coverage-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
