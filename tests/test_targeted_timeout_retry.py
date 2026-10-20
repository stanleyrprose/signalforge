from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signalforge.engine import _acquire_source_bytes


class TargetedTimeoutRetryTests(unittest.TestCase):
    def _acquire(self, source_id: str):
        with tempfile.TemporaryDirectory() as root:
            source = {
                "engine": "direct_http",
                "request_timeout_seconds": 1,
                "request_max_bytes": 10000,
                "source_policy_version": 1,
                "egress_profile": "mm-intl-datacenter",
            }
            return _acquire_source_bytes(
                source=source, database=Path(root) / "data.db",
                scheduler_run_id="run", source_id=source_id, reason="POLL",
                target_kind="DISCOVERY", url="https://example.org/",
                expected_content_types=["text/html"], observed_at="2026-10-20T00:00:00Z",
                fetcher=lambda *_a, **_k: b"ok",
            )

    def test_targeted_timeout_retries_and_recovers(self):
        from signalforge.http import FetchError
        with patch("signalforge.engine.acquire_local_bytes", side_effect=[FetchError("The read operation timed out"), b"ok"]) as fetch, patch("signalforge.engine.time.sleep") as pause:
            self.assertEqual(self._acquire("S47"), b"ok")
        self.assertEqual(fetch.call_count, 2)
        pause.assert_called_once_with(0.5)

    def test_other_sources_do_not_retry(self):
        from signalforge.http import FetchError
        with patch("signalforge.engine.acquire_local_bytes", side_effect=FetchError("The read operation timed out")) as fetch, patch("signalforge.engine.time.sleep") as pause:
            with self.assertRaises(FetchError):
                self._acquire("S20")
        self.assertEqual(fetch.call_count, 1)
        pause.assert_not_called()

    def test_non_timeout_failure_does_not_retry(self):
        from signalforge.http import FetchError
        with patch("signalforge.engine.acquire_local_bytes", side_effect=FetchError("HTTP 404")) as fetch, patch("signalforge.engine.time.sleep") as pause:
            with self.assertRaises(FetchError):
                self._acquire("S37")
        self.assertEqual(fetch.call_count, 1)
        pause.assert_not_called()


if __name__ == "__main__":
    unittest.main()
