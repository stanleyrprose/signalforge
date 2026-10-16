import unittest
from unittest.mock import patch
from signalforge.http import FetchError, fetch_s01_bytes_insecure_tls


class S01TlsExceptionTests(unittest.TestCase):
    def test_only_s01_host_and_https(self):
        for url in ('http://myanmar.gov.mm/news', 'https://other.gov.mm/news',
                    'https://myanmar.gov.mm.evil.example/news', 'https://user@myanmar.gov.mm/news',
                    'https://myanmar.gov.mm:444/news'):
            with self.assertRaises(FetchError):
                fetch_s01_bytes_insecure_tls(url)

    def test_scoped_context_and_redirects(self):
        with patch('signalforge.http._fetch_bytes_with_context', return_value=b'news') as fetch:
            self.assertEqual(fetch_s01_bytes_insecure_tls('https://myanmar.gov.mm/en/news-media/news/latest-news'), b'news')
            self.assertEqual(fetch.call_args.kwargs['allowed_redirect_hosts'], {'myanmar.gov.mm', 'www.myanmar.gov.mm'})
            self.assertFalse(fetch.call_args.kwargs['context'].check_hostname)
