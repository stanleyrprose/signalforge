from __future__ import annotations

import unittest

from signalforge.customs_reviewed_enrichment import apply_reviewed_customs_overlay, reviewed_customs_overlay

KEY = "customs-auction:2026-09-08:de1e5fca89686a1f"
REF = "CUSTOMS-AUCTION-20260908-de1e5fca"
ATTACH = "https://customs.gov.mm/admin/storage/files/Announcement-1.pdf"


class CustomsReviewedEnrichmentTests(unittest.TestCase):
    def test_exact_identity_returns_current_business_event(self) -> None:
        result = reviewed_customs_overlay(
            canonical_key=KEY,
            source_id="S08A",
            item_kind="AUCTION_NOTICE",
            reference_no=REF,
            publication_date="2026-09-08",
            attachment_url=ATTACH,
        )
        self.assertEqual(result["business_stage"], "OPPORTUNITY")
        self.assertEqual(result["action_date"], "2026-09-28")
        self.assertEqual(result["action_time"], "10:00")
        self.assertEqual(result["commercial_direction"], "BUY_FROM_ISSUER")
        self.assertIn("钢铁/塑料原料", result["scope_summary"])
        self.assertIn("9/16–18买表格", result["next_action_summary"])
        self.assertEqual(result["reviewed_enrichment_status"], "REVIEWED_TEXT_PDF_CURRENT_EVENT")
        self.assertTrue(result["reviewed_enrichment_read_only"])

    def test_identity_mismatch_fails_closed(self) -> None:
        base = dict(
            canonical_key=KEY, source_id="S08A", item_kind="AUCTION_NOTICE", reference_no=REF,
            publication_date="2026-09-08", attachment_url=ATTACH,
        )
        for field, value in (
            ("canonical_key", "customs-auction:wrong"),
            ("source_id", "S07"),
            ("item_kind", "TENDER"),
            ("reference_no", "CUSTOMS-WRONG"),
            ("publication_date", "2026-09-09"),
            ("attachment_url", "https://customs.gov.mm/admin/storage/files/other.pdf"),
        ):
            args = dict(base)
            args[field] = value
            self.assertEqual(reviewed_customs_overlay(**args), {})

    def test_overlay_fills_only_missing_fields(self) -> None:
        payload = {
            "publication_date": "2026-09-08",
            "attachment_url": ATTACH,
            "reference_no": REF,
            "scope_summary": "Canonical scope wins",
        }
        result = apply_reviewed_customs_overlay(
            payload, canonical_key=KEY, source_id="S08A", item_kind="AUCTION_NOTICE", reference_no=REF
        )
        self.assertEqual(result["scope_summary"], "Canonical scope wins")
        self.assertEqual(result["action_date"], "2026-09-28")
        self.assertEqual(result["business_stage"], "OPPORTUNITY")


if __name__ == "__main__":
    unittest.main()
