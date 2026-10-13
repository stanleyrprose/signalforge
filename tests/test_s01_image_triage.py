"""S01 OCR triage regression checks; run only after implementation approval."""
import unittest
from signalforge.s01_image_triage import triage_s01_image_ocr


class S01ImageTriageTests(unittest.TestCase):
    def test_uncertain_quantity_remains_unknown(self):
        text = "Octane-92( Joooo) diesel"
        result = triage_s01_image_ocr(text)
        self.assertEqual(result["classification"], "UNKNOWN")
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
