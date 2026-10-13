"""S01 OCR triage regression checks; run only after implementation approval."""
import unittest
from signalforge.s01_image_triage import triage_s01_image_ocr


class S01ImageTriageTests(unittest.TestCase):
    def test_uncertain_quantity_remains_unknown(self):
        text = "Octane-92( Joooo) diesel"
        result = triage_s01_image_ocr(text)
        self.assertEqual(result["classification"], "UNKNOWN")
        self.assertFalse(result["canonical_promotion_allowed"])

    def test_real_fuel_ocr_excerpt_keeps_corrupted_octane_unknown(self):
        text = (
            "ဒီဇယ်ဆီ(၈၅၀၀၀)ဂါလန် Octane-92( Joooo)dlav§ "
            "နှင့် ပရီမီယမ်ဒီဇယ်ဆီ(၄၅၀၀၀)ဂါလန်"
        )
        result = triage_s01_image_ocr(text)
        self.assertEqual(result["item_quantity_candidates"], {
            "diesel": 85000, "octane_92": None, "premium_diesel": 45000,
        })
        self.assertFalse(result["canonical_promotion_allowed"])

    def test_real_lease_ocr_deadline_is_unverified(self):
        result = triage_s01_image_ocr(
            "Mandalay Convention Centre ငှားရမ်း\\n"
            "တင်ဒါလျှောက်လွှာတင်သွင်းရမည့်နောက်ဆုံး - (၃-၁၁-၂၀၂၆)"
        )
        self.assertEqual(result["bid_submission_deadline_date"], "2026-11-03")
        self.assertFalse(result["canonical_promotion_allowed"])

    def test_invalid_dates_never_promoted(self):
        result = triage_s01_image_ocr("31-02-2026")
        self.assertIsNone(result["bid_submission_deadline_date"])
        self.assertFalse(result["canonical_promotion_allowed"])

    def test_unrelated_dates_not_assigned(self):
        result = triage_s01_image_ocr("Octane-92(20000) 13.10.2026")
        self.assertIsNone(result["document_sale_end"])
        self.assertIsNone(result["bid_submission_deadline_date"])


if __name__ == "__main__":
    unittest.main()
