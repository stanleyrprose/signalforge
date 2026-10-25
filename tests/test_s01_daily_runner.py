import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signalforge.s01_daily_runner import run


class S01DailyRunnerTests(unittest.TestCase):
    def snapshot_root(self, tmp):
        root=Path(tmp)
        folder=root/'evidence/2026-10-18'
        folder.mkdir(parents=True)
        (folder/'s01-news-review.sqlite').write_bytes(b'mocked acquisition snapshot')
        return root

    def test_incomplete_pagination_never_calls_ai_or_delivery(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            'signalforge.s01_daily_runner.acquire_paginated_news_review',
            return_value={'pagination_incomplete': True, 'unique_candidates': 1}
        ), patch('signalforge.s01_daily_runner.review') as ai, patch(
            'signalforge.s01_daily_runner.transfer') as send:
            with self.assertRaisesRegex(RuntimeError, 'pagination'):
                run(self.snapshot_root(tmp), day='2026-10-18', publish=True)
            ai.assert_not_called()
            send.assert_not_called()

    def test_partial_details_continue_to_ai_and_prepare(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            'signalforge.s01_daily_runner.acquire_paginated_news_review',
            return_value={'pagination_incomplete': False, 'unique_candidates': 3}
        ), patch('signalforge.s01_daily_runner.acquire_news_details',
                 return_value={'failed': ['url'], 'details_saved': 2}), patch(
            'signalforge.s01_daily_runner.review',
            return_value={'unresolved': 1, 'excluded': 0, 'included': 2}) as ai, patch(
            'signalforge.s01_daily_runner.prepare',
            return_value={'status': 'READY_FOR_REVIEW', 'edition_id': 'partial', 'manifest': '/tmp/manifest'}
        ), patch('signalforge.s01_daily_runner.transfer') as send:
            result = run(self.snapshot_root(tmp), day='2026-10-18')
            self.assertEqual(result['articles'], 2)
            ai.assert_called_once()
            send.assert_not_called()

    def test_review_mode_does_not_send(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            'signalforge.s01_daily_runner.acquire_paginated_news_review',
            return_value={'pagination_incomplete': False, 'unique_candidates': 1}
        ), patch('signalforge.s01_daily_runner.acquire_news_details',
                 return_value={'failed': [], 'details_saved': 1}), patch(
            'signalforge.s01_daily_runner.review',
            return_value={'unresolved': 0, 'excluded': 0, 'included': 1}), patch(
            'signalforge.s01_daily_runner.prepare',
            return_value={'status': 'READY_FOR_REVIEW', 'edition_id': 'abc', 'manifest': '/tmp/manifest'}
        ), patch('signalforge.s01_daily_runner.transfer') as send:
            result = run(self.snapshot_root(tmp), day='2026-10-18')
            self.assertEqual(result['status'], 'READY_NOT_PUBLISHED')
            send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
