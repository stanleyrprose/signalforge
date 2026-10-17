import tempfile
from pathlib import Path

import pytest

from signalforge.db import migrate, connect
from signalforge.s01_news_review import acquire_news_review
from signalforge.s01_chinese_digest import reconcile_ai_digest, render_chinese_digest


def test_digest_reconciles_every_discovered_item():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        db = root / "news.sqlite"
        migrate(db)
        html = b'<a href="/en/news-media/news/latest-news/-/asset_publisher/idasset354/content/policy">A significant government policy announcement</a>'
        acquire_news_review(db, root / "evidence", payload=html)
        with connect(db) as conn, conn:
            url = conn.execute("SELECT url FROM s01_news_review").fetchone()[0]
            conn.execute("""CREATE TABLE s01_news_detail_review
                (url TEXT PRIMARY KEY,detail_sha256 TEXT NOT NULL,detail_evidence_path TEXT NOT NULL,
                body_text TEXT NOT NULL,body_chars INTEGER NOT NULL,review_status TEXT NOT NULL,
                acquired_at TEXT NOT NULL)""")
            conn.execute("INSERT INTO s01_news_detail_review VALUES (?,?,?,?,?,?,?)",
                         (url, "sha", "evidence.html", "policy details " * 20, 300,
                          "DETAIL_EXTRACTED_UNCORROBORATED", "now"))
        pending = reconcile_ai_digest(db, [])
        assert pending["unresolved"] == 1
        assert pending["digest_publish_gate"] == "BLOCKED_UNRESOLVED_ITEMS"
        ai = {"items": [{"source_url": url, "chinese_title": "政府政策公告",
                         "chinese_summary": "政策相关信息，待进一步核实。",
                         "importance": 85, "category": "政策",
                         "rationale": "政策影响", "evidence_limitations": "TLS未验证"}]}
        report = reconcile_ai_digest(db, [ai], output=root / "audit.json")
        assert report["included"] == 1 and report["unresolved"] == 0
        assert report["digest_publish_gate"] == "REVIEW_REQUIRED"
        assert "政府政策公告" in render_chinese_digest(report)
        assert (root / "audit.json").exists()
        with pytest.raises(ValueError):
            reconcile_ai_digest(db, [ai, ai])
