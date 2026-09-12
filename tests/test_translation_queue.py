from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from signalforge.translation_queue import (
    TranslationQueueError,
    claim_next_translation_request,
    complete_translation_claim,
    enqueue_translation_request,
    protected_tokens,
    request_translation_and_wait,
    translation_queue_status,
    translation_request_result,
)

NOW = datetime(2026, 9, 12, 5, 0, tzinfo=UTC)


class TranslationQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "signalforge.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_protected_tokens_capture_dates_numbers_and_references(self) -> None:
        tokens = protected_tokens("Tender MTE-6/2026-2027 qty 6,243 date 15.9.2026")
        self.assertIn("MTE-6/2026-2027", tokens)
        self.assertIn("6,243", tokens)
        self.assertIn("15.9.2026", tokens)

    def test_enqueue_claim_complete_and_cache(self) -> None:
        values = ["အိတ်ဖွင့်တင်ဒါ 15.9.2026", "ရန်ကုန်"]
        queued = enqueue_translation_request(values, database=self.db, now=NOW)
        self.assertEqual(queued["status"], "ENQUEUED")
        claimed = claim_next_translation_request(database=self.db, now=NOW + timedelta(seconds=1))
        self.assertEqual(claimed["status"], "CLAIMED")
        req = claimed["request"]
        result = complete_translation_claim(
            translation_request_id=claimed["translation_request_id"],
            translation_attempt_id=claimed["translation_attempt_id"],
            claim_token=claimed["claim_token"],
            request_sha256=req["request_sha256"],
            values=["公开招标 15.9.2026", "仰光"],
            model="gpt-test",
            duration_ms=123,
            usage={"tokens": 42},
            database=self.db,
            now=NOW + timedelta(seconds=2),
        )
        self.assertEqual(result["status"], "SUCCEEDED")
        current = translation_request_result(
            translation_request_id=claimed["translation_request_id"], database=self.db
        )
        self.assertEqual(current["result"]["values"], ["公开招标 15.9.2026", "仰光"])
        cached = enqueue_translation_request(values, database=self.db, now=NOW + timedelta(seconds=3))
        self.assertEqual(cached["status"], "CACHED")
        status = translation_queue_status(database=self.db, now=NOW + timedelta(seconds=3))
        self.assertTrue(status["ready"])
        self.assertEqual(status["counts"]["SUCCEEDED"], 1)

    def test_changed_protected_token_is_rejected(self) -> None:
        values = ["တင်ဒါ 15.9.2026 6,243"]
        enqueue_translation_request(values, database=self.db, now=NOW)
        claimed = claim_next_translation_request(database=self.db, now=NOW + timedelta(seconds=1))
        req = claimed["request"]
        with self.assertRaisesRegex(TranslationQueueError, "protected token"):
            complete_translation_claim(
                translation_request_id=claimed["translation_request_id"],
                translation_attempt_id=claimed["translation_attempt_id"],
                claim_token=claimed["claim_token"],
                request_sha256=req["request_sha256"],
                values=["招标 16.9.2026 6,244"],
                model="gpt-test",
                duration_ms=1,
                usage=None,
                database=self.db,
                now=NOW + timedelta(seconds=2),
            )

    def test_expired_claim_is_requeued_then_request_expires(self) -> None:
        enqueue_translation_request(["တင်ဒါ"], database=self.db, now=NOW, ttl_seconds=60)
        first = claim_next_translation_request(database=self.db, now=NOW, lease_seconds=15)
        second = claim_next_translation_request(database=self.db, now=NOW + timedelta(seconds=16), lease_seconds=15)
        self.assertEqual(first["translation_request_id"], second["translation_request_id"])
        status = translation_queue_status(database=self.db, now=NOW + timedelta(seconds=61))
        self.assertEqual(status["counts"]["EXPIRED"], 1)

    def test_wait_uses_cached_result_without_sleeping(self) -> None:
        values = ["အိတ်ဖွင့်တင်ဒါ"]
        enqueue_translation_request(values, database=self.db, now=NOW)
        claimed = claim_next_translation_request(database=self.db, now=NOW)
        req = claimed["request"]
        complete_translation_claim(
            translation_request_id=claimed["translation_request_id"],
            translation_attempt_id=claimed["translation_attempt_id"],
            claim_token=claimed["claim_token"],
            request_sha256=req["request_sha256"],
            values=["公开招标"],
            model="gpt-test",
            duration_ms=10,
            usage={},
            database=self.db,
            now=NOW,
        )
        translated, ok = request_translation_and_wait(values, database=self.db, wait_seconds=0)
        self.assertTrue(ok)
        self.assertEqual(translated, ["公开招标"])


if __name__ == "__main__":
    unittest.main()
