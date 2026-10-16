import tempfile
from pathlib import Path
from signalforge.db import connect, migrate
from signalforge.s01_news_review import acquire_news_review, news_review_digest


def test_news_review_is_independent_and_deduplicated():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        db = root / 'db.sqlite'
        migrate(db)
        html = b'<a href="/en/news-media/news/latest-news/-/asset_publisher/idasset354/content/example">Important government power project announced</a>'
        for _ in range(2):
            result = acquire_news_review(db, root / 'evidence', payload=html)
            assert result['candidates_in_listing'] == 1
            assert result['telegram_sent'] == 0
        with connect(db) as conn:
            assert conn.execute('SELECT COUNT(*) FROM s01_news_review').fetchone()[0] == 1
            assert conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0] == 0
        assert '待审核清单' in news_review_digest(db)
