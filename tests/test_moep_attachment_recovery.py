"""Bounded S20 official PDF capture; never promote review candidates."""
from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from signalforge.db import connect, migrate
from signalforge.moep_attachment_recovery import recover_accessible_s20_pdfs


class _Response:
    status = 200
    headers = {"Content-Type": "application/pdf"}

    def __init__(self, data: bytes) -> None:
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, length: int) -> bytes:
        return self.data[:length]


class S20OriginalPdfRecoveryTests(unittest.TestCase):
    def _row(self, db: Path, url: str) -> None:
        migrate(db)
        with connect(db) as conn, conn:
            conn.execute(
                "INSERT INTO canonical_items("
                "canonical_key,source_id,item_kind,title,reference_no,project_name,"
                "publication_date,deadline,location,url,content_hash,evidence_sha256,"
                "payload_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("moep:7219:2026-10-13", "S20", "TENDER", "EPGE", "MOEP-CONTENT-7219",
                 "EPGE", "2026-10-13", None, None,
                 "https://moep.gov.mm/mm/ignite/contentView/7219", "a"*64, "b"*64,
                 json.dumps({"attachment_name": "EPGE-2352.pdf", "attachment_url": url}),
                 "2026-10-13T00:00:00Z", "2026-10-13T00:00:00Z"),
            )

    def test_archives_exact_original_only_when_head_confirmed_official_pdf(self) -> None:
        b = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(b)
        source = b.getvalue()
        digest = hashlib.sha256(source).hexdigest()
        url = "https://moep.gov.mm/mm/userfile/EPGE-2352.pdf"
        calls = []

        def opener(request, *, timeout):
            calls.append((request.full_url, request.get_method(), timeout))
            return _Response(source)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "db.sqlite"
            self._row(db, url)
            health = {"rows": [
                {"canonical_key": "moep:7219:2026-10-13", "attachment_name": "EPGE-2352.pdf", "status": "PDF_ACCESSIBLE"},
                {"canonical_key": "other", "attachment_name": "broken.pdf", "status": "HTTP_404"},
            ]}
            got = recover_accessible_s20_pdfs(
                db, health, evidence=root / "evidence", opener=opener,
            )
            self.assertEqual(got["downloaded_count"], 1)
            self.assertEqual(got["native_text_count"], 0)
            self.assertEqual(got["scan_or_parse_review_count"], 1)
            self.assertEqual(got["rows"][0]["source_sha256"], digest)
            self.assertFalse(got["rows"][0]["canonical_promotion_allowed"])
            self.assertEqual((root / "evidence/S20" / f"{digest}.pdf").read_bytes(), source)
            self.assertEqual(calls, [(url, "GET", 6)])
            with connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0], 0)
                self.assertIsNone(conn.execute("SELECT deadline FROM canonical_items").fetchone()[0])

    def test_cross_origin_and_unknown_urls_never_fetched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "db"
            self._row(db, "https://example.org/mm/userfile/EPGE-2352.pdf")
            got = recover_accessible_s20_pdfs(
                db, {"rows": [{
                    "canonical_key": "moep:7219:2026-10-13",
                    "attachment_name": "EPGE-2352.pdf",
                    "status": "PDF_ACCESSIBLE",
                }]},
                evidence=Path(tmp) / "evidence",
                opener=lambda *_args, **_kw: self.fail("GET must never be issued"),
            )
            self.assertEqual(got["downloaded_count"], 0)
            self.assertEqual(got["failed_count"], 1)

    def test_out_of_bounds_or_unproven_results_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "db"
            self._row(db, "https://moep.gov.mm/mm/userfile/EPGE-2352.pdf")
            with self.assertRaises(ValueError):
                recover_accessible_s20_pdfs(db, {"rows": [{"status":"PDF_ACCESSIBLE"}]*6})
            got = recover_accessible_s20_pdfs(
                db, {"rows": [{
                    "canonical_key": "moep:7219:2026-10-13",
                    "attachment_name": "EPGE-2352.pdf",
                    "status": "HTTP_404",
                }]},
                opener=lambda *_args, **_kw: self.fail("404 PDF must not be GET-fetched"),
            )
            self.assertEqual(got["available_candidates"], 0)
            self.assertEqual(got["downloaded_count"], 0)


if __name__ == "__main__":
    unittest.main()
