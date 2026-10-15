from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

from signalforge.daily_cycle import _coverage_report
from signalforge.db import connect, migrate
from signalforge.moep_attachment_health import probe_recent_s20_attachments


class _FakePdfResponse:
    status = 200
    headers = {"Content-Type": "application/pdf"}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class S20AttachmentHealthTests(unittest.TestCase):
    def test_broken_issuer_pdfs_are_reported_not_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "signalforge.db"
            migrate(db)
            with connect(db) as conn, conn:
                for i, (name, url) in enumerate([
                    ("EPGE-2352.pdf", "https://moep.gov.mm/mm/userfile/EPGE-2352.pdf"),
                    ("YESC-5357.pdf", "https://moep.gov.mm/mm/userfile/YESC-5357.pdf"),
                    ("bad.pdf", "https://example.com/mm/userfile/bad.pdf"),
                ]):
                    key = f"moep:check-{i}:2026-10-13"
                    payload = json.dumps({"attachment_name": name, "attachment_url": url, "deadline": None})
                    conn.execute(
                        "INSERT INTO canonical_items(canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (key, "S20", "TENDER", name, key, name, "2026-10-13", None, None,
                         f"https://moep.gov.mm/mm/ignite/contentView/{i}", "a"*64, "b"*64,
                         payload, "2026-10-13T00:00:00Z", "2026-10-13T00:00:00Z"),
                    )

            def mock_open(request, *, timeout):
                self.assertEqual(request.get_method(), "HEAD")
                self.assertLessEqual(timeout, 10)
                if request.full_url.endswith("EPGE-2352.pdf"):
                    raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)
                return _FakePdfResponse()

            result = probe_recent_s20_attachments(
                db, now=datetime(2026, 10, 15, tzinfo=UTC), opener=mock_open,
            )
            self.assertEqual(result["checked_count"], 2)
            self.assertEqual(result["http_404_count"], 1)
            self.assertEqual(result["pdf_accessible_count"], 1)
            self.assertEqual(result["status"], "DEGRADED_HTTP_404")
            self.assertEqual(len(result["rows"]), 2)
            report = _coverage_report("2026-10-15", {"results":[]}, {"sent_count":0}, None, result)
            self.assertIn("S20", report)
            self.assertIn("HTTP 404", report)
            with connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE deadline IS NOT NULL").fetchone()[0], 0)

    def test_empty_recent_sample_reports_unproven_not_green(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            db = Path(d)/"signalforge.db"
            migrate(db)
            result = probe_recent_s20_attachments(db, now=datetime(2026,10,15,tzinfo=UTC))
            self.assertEqual(result["status"], "UNPROVEN")
            self.assertEqual(result["checked_count"], 0)


if __name__ == "__main__":
    unittest.main()
