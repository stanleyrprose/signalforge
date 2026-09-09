from __future__ import annotations

import unittest

from signalforge.qualification import qualify_opportunity


class QualificationTests(unittest.TestCase):
    def test_poweredge_does_not_create_energy_false_positive(self) -> None:
        item = {
            "source_id": "S30",
            "title": "Data Server tender",
            "scope_summary": "Dell PowerEdge R750-XS with redundant Power Supply, Windows Server 2025 and SQL Server 2022",
            "deadline_status": "OPEN",
            "remaining_seconds": 8 * 24 * 3600,
            "detail_completeness": "HTML_EVENT_PLUS_TEXT_PDF_SCOPE_DEADLINE",
            "deadline_evidence": "OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME",
            "reference_no": "MOFA-POST-59800",
        }
        result = qualify_opportunity(item, {"engine": "direct_http", "name": "Ministry of Foreign Affairs Procurement Invitations"})
        self.assertEqual(result["trust_grade"], "A")
        self.assertEqual(result["priority_band"], "HIGH")
        self.assertIn("ICT", result["relevance_categories"])
        self.assertNotIn("ENERGY", result["relevance_categories"])

    def test_industry_engine_power_does_not_create_energy_false_positive(self) -> None:
        item = {
            "source_id": "S38",
            "title": "Renovation of Heavy Machinery & Equipment",
            "scope_summary": "Wheel Loader Engine Power 164 KW, Excavator, Forklift and Electrical Spare Parts renovation works",
            "deadline_status": "OPEN",
            "remaining_seconds": 5 * 24 * 3600,
            "detail_completeness": "HTML_BUSINESS_SCOPE_AND_DEADLINE_NO_ATTACHMENT_REQUIRED",
            "deadline_evidence": "EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME",
            "reference_no": "INDUSTRY-ANN-1034",
        }
        result = qualify_opportunity(item, {"engine": "provider", "name": "Ministry of Industry Procurement Announcements"})
        self.assertEqual(result["trust_grade"], "A")
        self.assertIn("INDUSTRIAL", result["relevance_categories"])
        self.assertNotIn("ENERGY", result["relevance_categories"])
        self.assertEqual(result["evidence_level"], "OFFICIAL_HTML_VIA_PROVIDER")

    def test_unknown_deadline_stays_review_grade(self) -> None:
        item = {
            "source_id": "S26",
            "title": "Tender 8DMS, 9DMS and 10DMS",
            "scope_summary": "Official attachment metadata for three medical procurement references",
            "deadline_status": "UNKNOWN",
            "remaining_seconds": None,
            "detail_completeness": "HTML_SCOPE_ATTACHMENT_METADATA",
            "reference_no": "8DMS/2026-2027(L)",
            "reference_numbers": ["8DMS/2026-2027(L)", "9DMS/2026-2027(L)", "10DMS/2026-2027(F)"],
            "reference_count": 3,
        }
        result = qualify_opportunity(item, {"engine": "direct_http", "name": "DOMS Medical Procurement Opportunities"})
        self.assertEqual(result["trust_grade"], "B")
        self.assertEqual(result["priority_band"], "REVIEW")
        self.assertEqual(result["primary_relevance"], "MEDICAL")
        self.assertEqual(result["urgency"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
