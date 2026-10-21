"""Safety contract for task-owned post-delivery cleanup (development only)."""
import tempfile
import unittest
from pathlib import Path

from signalforge.temporary_cleanup import CleanupSafetyError, cleanup_completed_temp


class CompletedTempCleanupTests(unittest.TestCase):
    def test_requires_delivery_and_durable_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            temporary = root / "intermediate.html"
            temporary.write_text("temp")
            for sent, receipted in ((False, True), (True, False)):
                with self.assertRaises(CleanupSafetyError):
                    cleanup_completed_temp(root, [temporary], delivery_confirmed=sent,
                                           durable_receipts_confirmed=receipted)
                self.assertTrue(temporary.exists())

    def test_only_explicit_task_owned_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            temp_file = root / "intermediate.html"
            temp_file.write_text("temp")
            ledger = root / "business.sqlite"
            ledger.write_bytes(b"preserve")
            outcome = cleanup_completed_temp(
                root, [temp_file], delivery_confirmed=True,
                durable_receipts_confirmed=True)
            self.assertEqual(outcome["removed"], 1)
            self.assertFalse(temp_file.exists())
            self.assertTrue(ledger.exists())

    def test_rejects_parent_escape_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root = parent / "temp"
            root.mkdir()
            outside = parent / "retained.sqlite"
            outside.write_bytes(b"keep")
            alias = root / "outside-link"
            alias.symlink_to(outside)
            for target in (outside, alias):
                with self.assertRaises(CleanupSafetyError):
                    cleanup_completed_temp(root, [target], delivery_confirmed=True,
                                           durable_receipts_confirmed=True)
            self.assertTrue(outside.exists())

    def test_rejects_mixed_valid_and_invalid_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            disposable = root / "a.html"
            disposable.write_text("temporary")
            missing = root / "missing.html"
            with self.assertRaises(CleanupSafetyError):
                cleanup_completed_temp(root, [disposable, missing],
                                       delivery_confirmed=True,
                                       durable_receipts_confirmed=True)
            self.assertTrue(disposable.exists())
