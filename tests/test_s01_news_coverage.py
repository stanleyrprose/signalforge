import tempfile
from pathlib import Path

from signalforge.db import migrate
from signalforge.s01_news_review import acquire_news_review
from signalforge.s01_news_coverage import coverage_reconciliation


def test_discovered_news_cannot_silently_disappear():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        db = root / "db.sqlite"
        migrate(db)
        html = b'<a href="/en/news-media/news/latest-news/-/asset_publisher/idasset354/content/sample">A meaningful policy announcement</a>'
        acquire_news_review(db, root / "evidence", payload=html)
        result = coverage_reconciliation(db, root / "audit.json")
        assert result["total_discovered"] == 1
        assert result["detail_required"] == 1
        assert result["unresolved"] == 1
        assert result["digest_publish_gate"].startswith("BLOCKED")
        assert (root / "audit.json").exists()
