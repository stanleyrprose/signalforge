"""Regression checks for evidence-aware tender completeness semantics."""
import unittest

from signalforge.tender_quality import _has_fact, _missing_reason
from signalforge.telegram_delivery import render_telegram_message
from signalforge.mission_focus import classify_mission_fit


class TenderQualityFieldTests(unittest.TestCase):
    def test_quantity_unknown_is_not_a_fact(self):
        for value in ("未披露", "详见官方原文", "Not disclosed", "not specified", ""):
            with self.subTest(value=value):
                self.assertFalse(_has_fact(value))
        self.assertTrue(_has_fact("7 lots"))
        self.assertTrue(_has_fact("12 units"))

    def test_reference_count_not_procurement_quantity(self):
        payload = {"reference_count": 7, "reviewed_attachment_status": "REVIEWED"}
        self.assertEqual(
            _missing_reason(payload, "quantity", [None]),
            "REVIEWED_ATTACHMENT_NOT_NORMALIZED",
        )

    def test_unknown_deadline_has_warning(self):
        item = {
            "item_kind": "TENDER", "title": "Official tender",
            "issuer": "Government", "deadline_status": "UNKNOWN",
            "url": "https://example.org/tender",
        }
        message = render_telegram_message(
            item, translator=lambda values: (values, False)
        )
        self.assertIn("不能据此认定仍可投标", message)
        self.assertIn("未提取到明确数量", message)

    def test_myanmar_construction_is_mission_relevant(self):
        result = classify_mission_fit({
            "item_kind": "TENDER", "issuer": "Government",
            "title": "တည်ဆောက်ရေးလုပ်ငန်း",
            "source_id": "S35",
        })
        self.assertTrue(result["mission_fit"])


if __name__ == "__main__":
    unittest.main()
