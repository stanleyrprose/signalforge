import unittest
from signalforge.s01_news_discovery import parse_news_discovery


class NewsDiscoveryTests(unittest.TestCase):
    def test_bounded_same_origin_and_hint_only(self):
        html = b'''<a href="/en/news-media/news/latest-news?assetEntryId=123">Government announces major power project</a>
        <a href="https://evil.example/en/news-media/news/latest-news?assetEntryId=4">External fabricated notice</a>
        <a href="/en/news-media/news/latest-news">Latest News</a>'''
        items = parse_news_discovery(html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['evidence_status'], 'LISTING_HINT_ONLY')
        self.assertIn('listing_sha256', items[0])

    def test_oversized_and_untrusted_origin(self):
        with self.assertRaises(ValueError):
            parse_news_discovery(b'x' * 2_000_001)
        with self.assertRaises(ValueError):
            parse_news_discovery(b'', base_url='https://example.org/news')
