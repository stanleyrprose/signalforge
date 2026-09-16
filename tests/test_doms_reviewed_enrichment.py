from __future__ import annotations

import unittest

from signalforge.doms_reviewed_enrichment import apply_reviewed_doms_overlay, reviewed_doms_overlay


DOMS_URL = "https://www.doms.gov.mm/2026/09/08/%E1%80%90%E1%80%84%E1%80%BA%E1%80%92%E1%80%AB%E1%80%A1%E1%80%99%E1%80%BE%E1%80%90%E1%80%BA-8dms-2026-2027l-9dms-2026-2027l-%E1%80%94%E1%80%BE%E1%80%84%E1%80%B7%E1%80%BA-10dms-2026-2027f/"


class DomsReviewedEnrichmentTests(unittest.TestCase):
    def test_exact_identity_returns_reviewed_procurement_scope(self) -> None:
        result = reviewed_doms_overlay(
            canonical_key="doms:12735",
            source_id="S26",
            item_kind="TENDER",
            reference_no="8DMS/2026-2027(L)",
            url=DOMS_URL,
        )
        self.assertIn("Normalizer 135/165/220KVA ×4/2/4", result["scope_summary"])
        self.assertIn("OCT ×2", result["scope_summary"])
        self.assertIn("300mA X-Ray", result["scope_summary"])
        self.assertEqual(result["quantity_or_lot_confidence"], "MIXED_VERIFIED_ONLY")
        self.assertEqual(result["reviewed_enrichment_status"], "REVIEWED_OCR_SCOPE")
        self.assertTrue(result["reviewed_enrichment_read_only"])

    def test_identity_mismatch_fails_closed(self) -> None:
        base = dict(
            canonical_key="doms:12735",
            source_id="S26",
            item_kind="TENDER",
            reference_no="8DMS/2026-2027(L)",
            url=DOMS_URL,
        )
        for field, value in (
            ("canonical_key", "doms:12734"),
            ("source_id", "S25"),
            ("item_kind", "AUCTION_NOTICE"),
            ("reference_no", "7DMS/2026-2027(L)"),
            ("url", "https://www.doms.gov.mm/wrong/"),
        ):
            args = dict(base)
            args[field] = value
            self.assertEqual(reviewed_doms_overlay(**args), {})

    def test_overlay_replaces_only_reference_only_scope_in_read_model(self) -> None:
        payload = {
            "url": DOMS_URL,
            "scope_summary": "8DMS(2026-2027)(L)_ad9e1cc0-dc4c-4e87-8b04-8ca27e94ce68 9DMS(2026-2027)(L)_99c2e627-1816-4a8a-9b27-8f0b5d94acf0",
            "deadline": None,
        }
        result = apply_reviewed_doms_overlay(
            payload,
            canonical_key="doms:12735",
            source_id="S26",
            item_kind="TENDER",
            reference_no="8DMS/2026-2027(L)",
        )
        self.assertIn("Dental CAD-CAM+3D Printer+Scanner ×1", result["scope_summary"])
        self.assertIsNone(result["deadline"])
        self.assertIn("reviewed", str(result["image_review_notes"]).lower())

        canonical_scope = dict(payload, scope_summary="Issuer HTML already has explicit medical equipment scope")
        unchanged = apply_reviewed_doms_overlay(
            canonical_scope,
            canonical_key="doms:12735",
            source_id="S26",
            item_kind="TENDER",
            reference_no="8DMS/2026-2027(L)",
        )
        self.assertEqual(unchanged["scope_summary"], canonical_scope["scope_summary"])


if __name__ == "__main__":
    unittest.main()
