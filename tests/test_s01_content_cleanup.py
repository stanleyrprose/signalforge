import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from signalforge.s01_content_cleanup import cleanup_day
from signalforge.s01_daily_ledger import S01Ledger

DAY="2026-10-24"
EDITION="a"*64

class ContentCleanupTests(unittest.TestCase):
    def setup_case(self, root, *, pdf=True):
        folder=root/"evidence"/DAY
        folder.mkdir(parents=True)
        (folder/"original.html").write_text("source")
        (folder/"s01-news-review.sqlite").write_bytes(b"per-task processing content")
        (folder/"revisions").mkdir()
        (folder/"revisions"/"old.pdf").write_bytes(b"%PDF-old")
        (root/"edition-index").mkdir()
        (root/"edition-index"/(EDITION+".json")).write_text(json.dumps({"date":DAY,"edition_id":EDITION}))
        ledger=S01Ledger(root/"s01-delivery.sqlite")
        ledger.record_delivery(EDITION,"digest","SUCCESS",801)
        if pdf:ledger.record_delivery(EDITION,"pdf","SUCCESS",802)
        ledger.close()
        return folder

    def test_success_removes_all_task_content_but_preserves_receipts_and_other_day(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);folder=self.setup_case(root)
            other=root/"evidence/2026-10-25";other.mkdir()
            (other/"pending.txt").write_text("unpublished")
            result=cleanup_day(root,DAY,EDITION)
            self.assertEqual(result["status"],"ALL_TASK_CONTENT_REMOVED")
            self.assertFalse(folder.exists())
            self.assertTrue((root/"s01-delivery.sqlite").exists())
            self.assertTrue((other/"pending.txt").exists())
            self.assertEqual(cleanup_day(root,DAY,EDITION)["telegram"]["pdf"],802)

    def test_incomplete_receipt_and_wrong_date_preserve_content(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);folder=self.setup_case(root,pdf=False)
            with self.assertRaises(ValueError):cleanup_day(root,DAY,EDITION)
            self.assertTrue(folder.exists())
            with self.assertRaises(ValueError):cleanup_day(root,"2026-10-25",EDITION)
            self.assertTrue(folder.exists())

    def test_cleanup_failure_preserves_receipt_and_allows_cleanup_only_retry(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);folder=self.setup_case(root)
            with patch("signalforge.s01_content_cleanup.shutil.rmtree",side_effect=PermissionError):
                result=cleanup_day(root,DAY,EDITION)
            self.assertEqual(result["status"],"PENDING")
            self.assertTrue(folder.exists())
            self.assertEqual(cleanup_day(root,DAY,EDITION)["status"],"ALL_TASK_CONTENT_REMOVED")
