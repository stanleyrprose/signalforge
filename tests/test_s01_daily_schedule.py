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
    def test_0940_boundary_and_plist_agree(self):
        import plistlib
        config = plistlib.loads((Path(__file__).resolve().parents[1] /
            "deploy/com.stanley.signalforge-s01-news-daily.plist").read_bytes())
        self.assertEqual(config["StartCalendarInterval"], {"Hour": 9, "Minute": 40})
        for hour, minute, expected in ((9, 39, "2026-10-23"),
                                       (9, 40, "2026-10-24"),
                                       (10, 0, "2026-10-24")):
            with self.subTest(hour=hour, minute=minute), tempfile.TemporaryDirectory() as t:
                with patch.object(sched, "_execute_day", return_value={"status": "NO_NEW_ARTICLES"}) as work:
                    sched.execute(Path(t), now=NOW.replace(hour=hour, minute=minute))
                    self.assertEqual(work.call_args.args[1], expected)

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

    def test_old_incomplete_receipt_does_not_block_current_day(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            sched._save(root/"daily-schedule/2026-10-23.json",
                        {"date": "2026-10-23", "status": "PREPARED", "edition_id": "abc"})
            ledger = S01Ledger(root/"s01-delivery.sqlite")
            ledger.record_delivery("abc", "digest", "SUCCESS", 601)
            ledger.close()
            with patch.object(sched, "run", return_value={"status":"NO_NEW_ARTICLES"}) as acquire, patch.object(sched, "transfer") as send:
                with self.assertRaisesRegex(RuntimeError, "confirmed receipts"):
                    sched.execute(root, now=NOW)
                acquire.assert_called_once_with(root.resolve(), day="2026-10-24")
                send.assert_not_called()
            self.assertEqual(json.loads((root/"daily-schedule/2026-10-24.json").read_text())["status"],"NO_NEW_ARTICLES")
            self.assertEqual(json.loads((root/"daily-schedule/2026-10-23.json").read_text())["status"],"PREPARED")

    def test_current_failure_still_attempts_one_history_and_retains_both(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            for day in ("2026-10-22","2026-10-23"):
                sched._save(root/"daily-schedule"/(day+".json"),{"date":day,"status":"STARTED"})
            with patch.object(sched,"run",side_effect=[RuntimeError("quota"),{"status":"NO_NEW_ARTICLES"}]) as acquire:
                with self.assertRaisesRegex(RuntimeError,"quota"):sched.execute(root,now=NOW)
                self.assertEqual([c.kwargs["day"] for c in acquire.call_args_list],["2026-10-24","2026-10-22"])
            self.assertEqual(json.loads((root/"daily-schedule/2026-10-22.json").read_text())["status"],"NO_NEW_ARTICLES")
            self.assertEqual(json.loads((root/"daily-schedule/2026-10-24.json").read_text())["last_error_type"],"RuntimeError")

    def test_corrupt_history_does_not_block_today_or_get_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);folder=root/"daily-schedule";folder.mkdir()
            bad=folder/"2026-10-23.json";bad.write_text("invalid preserved evidence")
            bad_shape=folder/"2026-10-22.json";bad_shape.write_text("[]")
            with patch.object(sched,"run",return_value={"status":"NO_NEW_ARTICLES"}):
                result=sched.execute(root,now=NOW)
            self.assertEqual(result["invalid_journals"],["2026-10-22.json","2026-10-23.json"])
            self.assertEqual(bad_shape.read_text(),"[]")
            self.assertEqual(bad.read_text(),"invalid preserved evidence")
