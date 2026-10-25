import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from signalforge import s01_daily_schedule as sched
from signalforge.s01_daily_ledger import S01Ledger

NOW = datetime(2026, 10, 24, 18, tzinfo=sched.YANGON)


class ScheduleTests(unittest.TestCase):
    def test_successful_date_never_reacquires_or_resends(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            sched._save(root/"daily-schedule/2026-10-24.json",
                        {"date": "2026-10-24", "status": "DELIVERED"})
            with patch.object(sched, "run") as acquire, patch.object(sched, "transfer") as send:
                self.assertEqual(sched.execute(root, now=NOW)["status"], "ALREADY_COMPLETED")
                acquire.assert_not_called()
                send.assert_not_called()

    def test_failed_transfer_reuses_same_manifest_without_ai(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            manifest = root/"outbox/S01-manifest-2026-10-24-abc.json"
            sched._save(manifest, {"edition_id": "abc"})
            with patch.object(sched, "run") as acquire, patch.object(
                    sched, "transfer", side_effect=[RuntimeError("ambiguous"), {"edition_id": "abc", "status": "RECEIPT_IMPORTED"}]) as send:
                with self.assertRaisesRegex(RuntimeError, "ambiguous"):
                    sched.execute(root, now=NOW)
                self.assertEqual(sched.execute(root, now=NOW)["status"], "DELIVERED")
                acquire.assert_not_called()
                self.assertEqual(send.call_count, 2)
                self.assertEqual(send.call_args_list[0], send.call_args_list[1])

    def test_crash_after_manifest_cleanup_recovers_from_two_receipts(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            sched._save(root/"daily-schedule/2026-10-24.json",
                        {"date": "2026-10-24", "status": "PREPARED", "edition_id": "abc"})
            ledger = S01Ledger(root/"s01-delivery.sqlite")
            ledger.record_delivery("abc", "digest", "SUCCESS", 601)
            ledger.record_delivery("abc", "pdf", "SUCCESS", 602)
            ledger.close()
            with patch.object(sched, "run") as acquire, patch.object(sched, "transfer") as send:
                self.assertEqual(sched.execute(root, now=NOW)["status"], "DELIVERED")
                acquire.assert_not_called()
                send.assert_not_called()

    def test_incomplete_receipt_does_not_start_fresh_issue(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            sched._save(root/"daily-schedule/2026-10-23.json",
                        {"date": "2026-10-23", "status": "PREPARED", "edition_id": "abc"})
            ledger = S01Ledger(root/"s01-delivery.sqlite")
            ledger.record_delivery("abc", "digest", "SUCCESS", 601)
            ledger.close()
            with patch.object(sched, "run") as acquire, patch.object(sched, "transfer") as send:
                with self.assertRaisesRegex(RuntimeError, "confirmed receipts"):
                    sched.execute(root, now=NOW)
                acquire.assert_not_called()
                send.assert_not_called()
