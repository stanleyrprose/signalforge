"""Isolated SQLite integration for S01 image OCR review lifecycle."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signalforge.national_portal_tender import process_pending_s01_image_ocr


class S01ImageOCRIntegration(unittest.TestCase):
    def test_success_is_review_only_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE s01_image_review (url TEXT PRIMARY KEY, review_status TEXT, ocr_attempts INTEGER DEFAULT 0, first_seen_at TEXT, ocr_last_attempt_at TEXT, ocr_last_error TEXT, ocr_input_sha256 TEXT, ocr_evidence_path TEXT, ocr_text TEXT)")
                conn.execute("INSERT INTO s01_image_review (url,review_status,first_seen_at) VALUES ('https://myanmar.gov.mm/documents/sample.jpg','REVIEW_REQUIRED','2026-10-13')")
            evidence = {
                "source_image_sha256": "a" * 64,
                "evidence_artifact_path": "/tmp/fake.jpg",
                "ocr_text": "ဒီဇယ်ဆီ(85000) Octane-92(20000) ပရီမီယမ်ဒီဇယ်(45000)",
            }
            with patch("signalforge.acquisition_runtime.acquire_provider_image_ocr", return_value=evidence) as fetch:
                first = process_pending_s01_image_ocr(db)
                second = process_pending_s01_image_ocr(db)
            self.assertEqual(first, {"attempted": 1, "completed": 1, "failed": 0})
            self.assertEqual(second, {"attempted": 0, "completed": 0, "failed": 0})
            fetch.assert_called_once()
            with sqlite3.connect(db) as conn:
                status = conn.execute("SELECT review_status FROM s01_image_review").fetchone()[0]
                classification, quantities = conn.execute("SELECT classification,item_quantity_candidates_json FROM s01_image_triage").fetchone()
            self.assertEqual(status, "OCR_REVIEW_REQUIRED")
            self.assertEqual(classification, "GOVERNMENT_FUEL_PROCUREMENT")
            self.assertEqual(json.loads(quantities), {"diesel": 85000, "octane_92": 20000, "premium_diesel": 45000})

    def test_provider_failure_keeps_candidate_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE s01_image_review (url TEXT PRIMARY KEY, review_status TEXT, ocr_attempts INTEGER DEFAULT 0, first_seen_at TEXT, ocr_last_attempt_at TEXT, ocr_last_error TEXT)")
                conn.execute("INSERT INTO s01_image_review (url,review_status,first_seen_at) VALUES ('https://myanmar.gov.mm/documents/sample.jpg','REVIEW_REQUIRED','2026-10-13')")
            with patch("signalforge.acquisition_runtime.acquire_provider_image_ocr", side_effect=RuntimeError("provider unavailable")):
                result = process_pending_s01_image_ocr(db)
            self.assertEqual(result, {"attempted": 1, "completed": 0, "failed": 1})
            with sqlite3.connect(db) as conn:
                status, attempts, error = conn.execute("SELECT review_status,ocr_attempts,ocr_last_error FROM s01_image_review").fetchone()
            self.assertEqual(status, "REVIEW_REQUIRED")
            self.assertEqual(attempts, 1)
            self.assertIn("provider unavailable", error)


if __name__ == "__main__":
    unittest.main()
