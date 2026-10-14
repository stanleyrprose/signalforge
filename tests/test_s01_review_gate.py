import unittest
from signalforge.s01_review_gate import decide_s01_review


class S01ReviewGateTest(unittest.TestCase):
    def test_asset_leasing_excluded(self):
        result = decide_s01_review({"classification": "GOVERNMENT_ASSET_LEASING", "formal_procurement_tender": False})
        self.assertEqual(result["disposition"], "EXCLUDED_NON_PROCUREMENT")
        self.assertFalse(result["requires_human_review"])
        self.assertFalse(result["canonical_promotion_allowed"])

    def test_procurement_requires_evidence(self):
        item = {"classification": "GOVERNMENT_FUEL_PROCUREMENT", "formal_procurement_tender": True}
        self.assertEqual(decide_s01_review(item)["disposition"], "REVIEW_REQUIRED")
        verified = decide_s01_review(item, official_image_verified=True)
        self.assertEqual(verified["disposition"], "READY_FOR_OFFICIAL_EVIDENCE_CHECK")
        self.assertFalse(verified["canonical_promotion_allowed"])

    def test_unknown_fails_closed(self):
        self.assertTrue(decide_s01_review({"classification": "UNKNOWN"})["requires_human_review"])
