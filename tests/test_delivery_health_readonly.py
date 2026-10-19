"""Focused regression cases for independent receipt-only health reporting.

Run only at the project verification gate, not during development.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.delivery_health_readonly import news_health, tender_health


class ReadonlyDeliveryHealthTests(unittest.TestCase):
    def test_paired_s01_receipts_do_not_claim_daily_scheduler_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s01.db"
            with sqlite3.connect(path) as conn:
                conn.execute("CREATE TABLE deliveries (edition_id TEXT, part TEXT, status TEXT, message_id INTEGER, updated_at TEXT)")
                conn.executemany("INSERT INTO deliveries VALUES (?,?,?,?,?)", [
                    ("e1", "pdf", "SUCCESS", 421, "2026-10-19T08:00:00+00:00"),
                    ("e1", "digest", "SUCCESS", 420, "2026-10-19T08:00:00+00:00"),
                ])
            report = news_health(path, "2026-10-19T00:00:00+00:00")
            self.assertEqual(report["receipt_status"], "PAIRED_OBSERVED")
            self.assertEqual(report["status"], "WARN")

    def test_missing_ledgers_are_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "absent.db"
            self.assertEqual(news_health(path, "2026-10-19T00:00:00Z")["status"], "UNKNOWN")
            self.assertEqual(tender_health(path, "2026-10-19T00:00:00Z")["status"], "UNKNOWN")

    def test_incomplete_s01_edition_is_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s01.db"
            with sqlite3.connect(path) as conn:
                conn.execute("CREATE TABLE deliveries (edition_id TEXT, part TEXT, status TEXT, message_id INTEGER, updated_at TEXT)")
                conn.execute("INSERT INTO deliveries VALUES (?,?,?,?,?)",
                             ("e2", "digest", "SUCCESS", 420, "2026-10-19T08:00:00+00:00"))
            report = news_health(path, "2026-10-19T00:00:00+00:00")
            self.assertEqual(report["status"], "WARN")
            self.assertEqual(report["complete_editions"], 0)


if __name__ == "__main__":
    unittest.main()
