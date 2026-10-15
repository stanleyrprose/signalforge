"""S01 verified-image promotion is bounded by two independent evidence gates."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.db import connect, migrate
from signalforge.s01_reviewed_tenders import promote_reviewed_s01_images


class S01ReviewedImagePromotionTests(unittest.TestCase):
    def _image_db(self, path: Path, rows: list[tuple[str, str, str]]) -> None:
        migrate(path)
        with connect(path) as conn, conn:
            conn.execute(
                "CREATE TABLE s01_image_review("
                "url TEXT PRIMARY KEY,review_status TEXT NOT NULL,ocr_input_sha256 TEXT)"
            )
            conn.executemany(
                "INSERT INTO s01_image_review(url,review_status,ocr_input_sha256) VALUES(?,?,?)",
                rows,
            )

    def test_actual_reviewed_fuel_and_lease_remain_unpromoted(self) -> None:
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "registry/S01-Reviewed-Issuer-Images-v1.json").read_text())
        digests = list(manifest["records"])
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.db"
            self._image_db(db, [
                ("https://myanmar.gov.mm/documents/fuel.jpg/id", "HUMAN_APPROVED", digests[0]),
                ("https://myanmar.gov.mm/documents/lease.jpg/id", "HUMAN_APPROVED", digests[1]),
            ])
            result = promote_reviewed_s01_images(
                db, now=datetime(2026, 10, 15, tzinfo=UTC),
            )
            self.assertEqual(result["reviewed"], 2)
            self.assertEqual(result["blocked_missing_bid_deadline"], 1)
            self.assertEqual(result["excluded_nonprocurement"], 1)
            self.assertEqual(result["promoted"], 0)
            with connect(db) as conn:
                self.assertEqual(conn.execute(
                    "SELECT COUNT(*) FROM canonical_items WHERE source_id='S01'"
                ).fetchone()[0], 0)

    def test_valid_independently_reviewed_tender_promotes_once_with_deadline(self) -> None:
        digest = "c" * 64
        url = "https://myanmar.gov.mm/documents/power-supply.jpg/issuer-id"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "registry").mkdir()
            (root / "registry/S01-Reviewed-Issuer-Images-v1.json").write_text(json.dumps({
                "schema_version": 1, "records": {digest: {
                    "review_status": "HUMAN_APPROVED_SOURCE_IMAGE",
                    "reviewed_at": "2026-10-14",
                    "formal_procurement_tender": True,
                    "issuer": "Electricity Enterprise",
                    "title": "Power transformer tender",
                    "scope_summary": "Procure 2 power transformers",
                    "quantity_or_lot_summary": "2 units",
                    "bid_submission_deadline": "2026-10-31",
                    "bid_submission_deadline_evidence": "HUMAN_REVIEWED_OFFICIAL_IMAGE_DEADLINE",
                }}
            }))
            db = root / "state.db"
            self._image_db(db, [(url, "HUMAN_APPROVED", digest)])
            clock = datetime(2026, 10, 15, tzinfo=UTC)
            first = promote_reviewed_s01_images(db, root=root, now=clock)
            second = promote_reviewed_s01_images(db, root=root, now=clock)
            self.assertEqual((first["promoted"], first["signals_created"]), (1, 1))
            self.assertEqual((second["promoted"], second["signals_created"]), (0, 0))
            with connect(db) as conn:
                row = conn.execute(
                    "SELECT deadline,payload_json,evidence_sha256 FROM canonical_items "
                    "WHERE source_id='S01'"
                ).fetchone()
                self.assertEqual(row["deadline"], "2026-10-31")
                self.assertEqual(row["evidence_sha256"], digest)
                self.assertEqual(json.loads(row["payload_json"])["quantity_or_lot_summary"], "2 units")

    def test_sale_date_or_ocr_without_human_review_never_promotes(self) -> None:
        digest = "d" * 64
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "registry").mkdir()
            (root / "registry/S01-Reviewed-Issuer-Images-v1.json").write_text(json.dumps({
                "schema_version": 1, "records": {digest: {
                    "review_status": "HUMAN_APPROVED_SOURCE_IMAGE",
                    "reviewed_at": "2026-10-14",
                    "formal_procurement_tender": True,
                    "issuer": "Public Works", "title": "Supply", "scope_summary": "Supply",
                    "quantity_or_lot_summary": "3 lots",
                    "document_sale_end": "2026-10-30",
                    "bid_submission_deadline": None,
                }}
            }))
            db = root / "state.db"
            self._image_db(db, [
                ("https://myanmar.gov.mm/documents/a.jpg/uuid", "HUMAN_APPROVED", digest),
                ("https://myanmar.gov.mm/documents/b.jpg/uuid", "OCR_REVIEW_REQUIRED", digest),
            ])
            out = promote_reviewed_s01_images(db, root=root)
            self.assertEqual(out["blocked_missing_bid_deadline"], 1)
            self.assertEqual(out["promoted"], 0)
            self.assertEqual(out["signals_created"], 0)

    def test_unverified_digest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "db"
            self._image_db(db, [
                ("https://myanmar.gov.mm/documents/supply.jpg/x", "HUMAN_APPROVED", "f"*64),
            ])
            out = promote_reviewed_s01_images(db)
            self.assertEqual(out["blocked_no_evidence_match"], 1)
            self.assertEqual(out["promoted"], 0)


if __name__ == "__main__":
    unittest.main()
