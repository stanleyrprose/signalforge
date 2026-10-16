import unittest
from unittest.mock import patch
from signalforge.http import FetchError, fetch_s01_news_unverified_tls


class S01NewsTlsTests(unittest.TestCase):
    def test_scoped_to_news_and_same_origin(self):
        with patch('signalforge.http._fetch_bytes_with_context', return_value=b'OK') as fetch:
            self.assertEqual(fetch_s01_news_unverified_tls('https://myanmar.gov.mm/en/news-media/news/latest-news'), b'OK')
            self.assertEqual(fetch.call_args.kwargs['allowed_redirect_hosts'], {'myanmar.gov.mm', 'www.myanmar.gov.mm'})
            for url in ['https://myanmar.gov.mm/tenders', 'https://evil.example/en/news-media/news',
                        'http://myanmar.gov.mm/en/news-media/news',
                        'https://myanmar.gov.mm.evil.example/en/news-media/news']:
                with self.assertRaises(FetchError):
                    fetch_s01_news_unverified_tls(url)
            self.assertEqual(fetch.call_count, 1)
