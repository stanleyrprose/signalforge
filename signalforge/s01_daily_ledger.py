"""S01-only durable incremental and delivery ledger. Never touches tender tables."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


def article_identity(url: str) -> str:
    """Use stable Liferay asset entry id when present; otherwise path, not redirect/query."""
    parsed = urlsplit(url)
    if parsed.hostname not in {"myanmar.gov.mm", "www.myanmar.gov.mm"}:
        raise ValueError("S01 article must belong to Myanmar portal")
    query = parse_qs(parsed.query, keep_blank_values=True)
    ids = [values[0] for key, values in query.items()
           if key.lower().endswith("assetentryid") and len(values) == 1 and values[0].isdigit()]
    if ids and len(set(ids)) == 1:
        return "s01:asset:" + ids[0]
    # Different query parameters may identify different articles on a shared route.
    canonical = unquote(parsed.path).rstrip("/") + ("?" + parsed.query if parsed.query else "")
    return "s01:url:" + hashlib.sha256(canonical.encode()).hexdigest()


def edition_identity(day: str, articles: list[tuple[str, str]]) -> str:
    """Deterministic digest identity; order and URL aliases do not affect it."""
    stable = sorted(set(articles))
    data = json.dumps([day, stable], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


class S01Ledger:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS articles (
            identity TEXT PRIMARY KEY, url TEXT NOT NULL, detail_sha TEXT NOT NULL,
            review_json TEXT, delivered_sha TEXT, updated_at TEXT NOT NULL)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS deliveries (
            edition_id TEXT NOT NULL, part TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('PENDING','UNKNOWN','SUCCESS','FAILED')),
            message_id INTEGER, updated_at TEXT NOT NULL,
            PRIMARY KEY (edition_id, part))""")
        self.db.commit()

    def close(self):
        self.db.close()

    def upsert_article(self, url: str, detail_sha: str, review: dict | None = None) -> str:
        identity = article_identity(url)
        now = datetime.now(timezone.utc).isoformat()
        prior = self.db.execute("SELECT detail_sha,review_json FROM articles WHERE identity=?", (identity,)).fetchone()
        retained = prior[1] if prior and prior[0] == detail_sha else None
        review_json = json.dumps(review, ensure_ascii=False) if review is not None else retained
        self.db.execute("""INSERT INTO articles(identity,url,detail_sha,review_json,updated_at)
            VALUES (?,?,?,?,?) ON CONFLICT(identity) DO UPDATE SET
            url=excluded.url,detail_sha=excluded.detail_sha,review_json=excluded.review_json,
            updated_at=excluded.updated_at""", (identity, url, detail_sha, review_json, now))
        self.db.commit()
        return identity

    def pending_articles(self) -> list[tuple[str, str, str]]:
        return self.db.execute("""SELECT identity,url,detail_sha FROM articles
            WHERE delivered_sha IS NULL OR delivered_sha != detail_sha ORDER BY identity""").fetchall()

    def record_delivery(self, edition_id: str, part: str, status: str, message_id: int | None = None):
        if status not in {"PENDING", "UNKNOWN", "SUCCESS", "FAILED"}:
            raise ValueError("invalid delivery state")
        if status == "SUCCESS" and (type(message_id) is not int or message_id <= 0):
            raise ValueError("success requires Telegram message ID")
        prior = self.db.execute("SELECT status,message_id FROM deliveries WHERE edition_id=? AND part=?",
                                (edition_id, part)).fetchone()
        if prior and prior[0] == "SUCCESS":
            if status != "SUCCESS" or message_id != prior[1]:
                raise ValueError("cannot overwrite successful receipt")
            return
        if prior and prior[0] in ("UNKNOWN", "PENDING") and status == "PENDING":
            raise ValueError("unresolved outcome requires reconciliation before retry")
        self.db.execute("""INSERT INTO deliveries VALUES (?,?,?,?,?)
            ON CONFLICT(edition_id,part) DO UPDATE SET status=excluded.status,
            message_id=excluded.message_id,updated_at=excluded.updated_at""",
            (edition_id, part, status, message_id, datetime.now(timezone.utc).isoformat()))
        self.db.commit()

    def mark_delivered(self, articles: list[tuple[str, str]], edition_id: str):
        receipts = self.db.execute(
            "SELECT part,status FROM deliveries WHERE edition_id=?", (edition_id,)).fetchall()
        if dict(receipts).get("pdf") != "SUCCESS" or dict(receipts).get("digest") != "SUCCESS":
            raise ValueError("both Digest and PDF success receipts required")
        with self.db:
            for identity, sha in articles:
                self.db.execute("""UPDATE articles SET delivered_sha=?
                    WHERE identity=? AND detail_sha=?""", (sha, identity, sha))
