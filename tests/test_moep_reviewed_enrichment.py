from __future__ import annotations

import unittest

from signalforge.moep_reviewed_enrichment import (
    apply_reviewed_moep_overlay,
    reviewed_moep_overlay,
    reviewed_moep_records,
)


class MoepReviewedEnrichmentTests(unittest.TestCase):
    def test_exact_reviewed_identity_returns_deadline_participation_and_evidence(self) -> None:
        result = reviewed_moep_overlay(
            canonical_key="moep:7157:2026-09-11",
            source_id="S20",
            item_kind="TENDER",
            reference_no="MOEP-CONTENT-7157",
            publication_date="2026-09-11",
            article_url="https://moep.gov.mm/mm/ignite/contentView/7157",
            attachment_name="ACCC_Conductor_Form.pdf",
        )
        self.assertEqual(result["deadline"], "2026-10-01")
        self.assertEqual(result["deadline_time"], "14:00")
        self.assertEqual(result["deadline_kind"], "BID_SUBMISSION_DEADLINE")
        self.assertIn("27号办公楼", str(result["next_action_summary"]))
        self.assertEqual(result["reviewed_document_page"], 28)
        self.assertTrue(result["reviewed_enrichment_read_only"])
        expected = "".join(("187aea12", "2f349e7d", "aac50e42", "45974d1d", "fe68fe9a", "bbb5b11b", "419addfe", "a2c5090b"))
        self.assertEqual(result["reviewed_document_sha256"], expected)

    def test_epge_review_recovers_two_exact_tender_references(self) -> None:
        result = reviewed_moep_overlay(
            canonical_key="moep:7151:2026-09-08",
            source_id="S20",
            item_kind="TENDER",
            reference_no="MOEP-CONTENT-7151",
            publication_date="2026-09-08",
            article_url="https://moep.gov.mm/mm/ignite/contentView/7151",
            attachment_name="EPGE-1955.pdf",
        )
        self.assertEqual(result["deadline"], "2026-09-22")
        self.assertEqual(result["deadline_time"], "13:00")
        self.assertEqual(result["reference_count"], 2)
        self.assertEqual(
            result["reference_numbers"],
            ["69(Re-T)/EPGE(REHP)/2026-2027", "70(Re-T)/EPGE(REHP)/2026-2027"],
        )

    def test_identity_mismatch_fails_closed(self) -> None:
        base = dict(
            canonical_key="moep:7157:2026-09-11",
            source_id="S20",
            item_kind="TENDER",
            reference_no="MOEP-CONTENT-7157",
            publication_date="2026-09-11",
            article_url="https://moep.gov.mm/mm/ignite/contentView/7157",
            attachment_name="ACCC_Conductor_Form.pdf",
        )
        for field, value in (
            ("source_id", "S21"),
            ("item_kind", "AUCTION_NOTICE"),
            ("reference_no", "MOEP-CONTENT-7156"),
            ("publication_date", "2026-09-10"),
            ("article_url", "https://moep.gov.mm/mm/ignite/contentView/7156"),
            ("attachment_name", "different.pdf"),
            ("canonical_key", "moep:7156:2026-09-10"),
        ):
            args = dict(base)
            args[field] = value
            self.assertEqual(reviewed_moep_overlay(**args), {})

    def test_overlay_only_fills_missing_canonical_fields(self) -> None:
        payload = {
            "reference_no": "MOEP-CONTENT-7157",
            "publication_date": "2026-09-11",
            "url": "https://moep.gov.mm/mm/ignite/contentView/7157",
            "attachment_name": "ACCC_Conductor_Form.pdf",
            "deadline": "2026-10-02",
            "location": "Canonical location",
            "detail_completeness": "HTML_PARTIAL_ATTACHMENT_METADATA",
        }
        result = apply_reviewed_moep_overlay(
            payload,
            canonical_key="moep:7157:2026-09-11",
            source_id="S20",
            item_kind="TENDER",
            reference_no="MOEP-CONTENT-7157",
        )
        self.assertEqual(result["deadline"], "2026-10-02")
        self.assertEqual(result["location"], "Canonical location")
        self.assertEqual(result["deadline_time"], "14:00")
        self.assertEqual(result["detail_completeness"], "HTML_PLUS_REVIEWED_TEXT_PDF")

    def test_all_reviewed_records_have_normalized_hashes_and_official_moi_urls(self) -> None:
        records = reviewed_moep_records()
        self.assertEqual(set(records), {"moep:7144:2026-09-04", "moep:7151:2026-09-08", "moep:7157:2026-09-11"})
        for record in records.values():
            self.assertEqual(len(str(record["document_sha256"])), 64)
            self.assertTrue(str(record["newspaper_url"]).startswith("https://www.moi.gov.mm/"))


if __name__ == "__main__":
    unittest.main()
