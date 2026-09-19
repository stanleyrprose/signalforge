from __future__ import annotations

import unittest

from signalforge.qualification import qualify_opportunity


class QualificationTests(unittest.TestCase):
    def test_multi_reference_reason_tracks_evidence_origin(self) -> None:
        base = {
            "source_id": "S26",
            "deadline_status": "UNKNOWN",
            "scope_summary": "Tender scope with enough business detail for qualification.",
            "reference_no": "REF-1",
            "reference_count": 3,
        }
        html = qualify_opportunity(dict(base, reference_numbers_evidence="HTML_TITLE"))
        self.assertIn("MULTI_REFERENCE_HTML_TITLE", html["qualification_reasons"])
        self.assertNotIn("MULTI_REFERENCE_OFFICIAL_PDF_SCOPE", html["qualification_reasons"])

        pdf = qualify_opportunity(
            dict(base, source_id="S39", reference_numbers_evidence="OFFICIAL_TEXT_NATIVE_PDF_SCOPE_DMP_REFERENCE_PATTERN")
        )
        self.assertIn("MULTI_REFERENCE_OFFICIAL_PDF_SCOPE", pdf["qualification_reasons"])
        self.assertNotIn("MULTI_REFERENCE_HTML_TITLE", pdf["qualification_reasons"])

        generic = qualify_opportunity(dict(base, reference_numbers_evidence="CANONICAL"))
        self.assertIn("MULTI_REFERENCE_EVIDENCE", generic["qualification_reasons"])

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
        self.assertEqual(result["relevance_provenance"]["ICT"], "ITEM_TEXT_KEYWORD:data server")
        self.assertIn(
            "ICT=ITEM_TEXT_KEYWORD:data server",
            result["signal_quality_dimensions"]["strategic_relevance"]["evidence"],
        )

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

    def test_source_policy_name_keyword_is_distinct_from_item_evidence(self) -> None:
        item = {
            "source_id": "SX",
            "title": "Tender references",
            "scope_summary": "Official attachment metadata for three procurement references with enough business detail.",
            "deadline_status": "UNKNOWN",
            "remaining_seconds": None,
            "detail_completeness": "HTML_SCOPE_ATTACHMENT_METADATA",
            "reference_no": "REF-1",
        }
        result = qualify_opportunity(item, {"engine": "direct_http", "name": "Medical Procurement Opportunities"})
        self.assertIn("MEDICAL", result["relevance_categories"])
        self.assertEqual(result["relevance_provenance"]["MEDICAL"], "SOURCE_POLICY_NAME_KEYWORD:medical")

    def test_source_category_fallback_is_explicitly_provenanced(self) -> None:
        item = {
            "source_id": "S26",
            "title": "Tender references",
            "scope_summary": "Official attachment metadata for three procurement references with enough business detail.",
            "deadline_status": "UNKNOWN",
            "remaining_seconds": None,
            "detail_completeness": "HTML_SCOPE_ATTACHMENT_METADATA",
            "reference_no": "8DMS/2026-2027(L)",
        }
        result = qualify_opportunity(item, {"engine": "direct_http", "name": "Issuer Procurement Opportunities"})
        self.assertIn("MEDICAL", result["relevance_categories"])
        self.assertEqual(result["relevance_provenance"]["MEDICAL"], "SOURCE_CATEGORY_FALLBACK:S26")
        self.assertIn(
            "MEDICAL=SOURCE_CATEGORY_FALLBACK:S26",
            result["signal_quality_dimensions"]["strategic_relevance"]["evidence"],
        )

    def test_doms_medical_source_keeps_medical_primary_when_scope_contains_scanner(self) -> None:
        item = {
            "source_id": "S26",
            "title": "Tender 8DMS, 9DMS and 10DMS",
            "scope_summary": "Dental CAD-CAM, 3D Printer, Intra Oral Scanner, OCT, X-Ray and medical equipment",
            "deadline_status": "UNKNOWN",
            "remaining_seconds": None,
            "detail_completeness": "HTML_ATTACHMENT_METADATA_PLUS_REVIEWED_SCAN_OCR_SCOPE",
            "reference_no": "8DMS/2026-2027(L)",
        }
        result = qualify_opportunity(item, {"engine": "direct_http", "name": "DOMS Medical Procurement Opportunities"})
        self.assertEqual(result["primary_relevance"], "MEDICAL")
        self.assertEqual(result["relevance_categories"][0], "MEDICAL")
        self.assertIn("ICT", result["relevance_categories"])
        self.assertEqual(result["relevance_provenance"]["MEDICAL"], "ITEM_TEXT_KEYWORD:medical")

    def test_coastal_cargo_vessel_is_engineering_without_becoming_strategic_high(self) -> None:
        item = {
            "source_id": "S22",
            "title": "အိတ်ဖွင့်တင်ဒါအပြိုင်ဈေးနှုန်းလွှာခေါ်ယူခြင်း",
            "scope_summary": "ပြည်တွင်းရေကြောင်းပို့ဆောင်ရေးဌာနမှ ရေယာဉ် ၁ စီးကို ဝယ်ယူရန် ဖိတ်ခေါ်အပ်ပါသည်။",
            "issuer": "Inland Water Transport (Myanmar)",
            "deadline_status": "OPEN",
            "remaining_seconds": 30 * 24 * 3600,
            "detail_completeness": "HTML_SCOPE_DEADLINE_PLUS_SCANNED_PDF_REVIEWED_OCR_LOCATION",
            "deadline_evidence": "OFFICIAL_HTML_DEADLINE_DATE_TIME",
            "reference_no": "IWT-NODE-1038",
            "location": "No. 50 Pansodan Road, Yangon Region",
            "next_action_summary": "Contact IWT Administration / Supply Division",
            "next_action_evidence": "IWT_SOURCE_NATIVE_SCANNED_PDF_REVIEWED_OCR",
        }
        result = qualify_opportunity(
            item,
            {"engine": "direct_http", "name": "Inland Water Transport Tenders"},
        )
        self.assertEqual(result["primary_relevance"], "ENGINEERING")
        self.assertEqual(result["relevance_categories"][0], "ENGINEERING")
        self.assertEqual(
            result["relevance_provenance"]["ENGINEERING"],
            "ITEM_TEXT_KEYWORD:ရေယာဉ်",
        )
        self.assertEqual(
            result["signal_quality_dimensions"]["strategic_relevance"]["score"],
            7,
        )
        self.assertEqual(result["priority_band"], "MEDIUM")

    def test_transport_or_partnership_substrings_do_not_create_engineering_false_positive(self) -> None:
        item = {
            "source_id": "SX",
            "title": "Transport partnership support services",
            "scope_summary": "Software support for a transport partnership with enough business detail.",
            "deadline_status": "OPEN",
            "remaining_seconds": 10 * 24 * 3600,
            "detail_completeness": "HTML_SCOPE_DEADLINE",
            "deadline_evidence": "EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME",
            "reference_no": "REF-TRANSPORT-1",
        }
        result = qualify_opportunity(item, {"engine": "direct_http", "name": "General Procurement"})
        self.assertNotIn("ENGINEERING", result["relevance_categories"])
        self.assertIn("ICT", result["relevance_categories"])

    def test_port_as_logistics_origin_does_not_create_engineering_false_positive(self) -> None:
        item = {
            "source_id": "S38",
            "title": "Container truck rental tender",
            "scope_summary": "ဆေးဝါးကုန်ကြမ်းများအား ရန်ကုန်ဆိပ်ကမ်းများမှ စက်ရုံများသို့ ပို့ဆောင်ရန် ကုန်သေတ္တာတင်ယာဉ် ငှားရမ်းခြင်း",
            "deadline_status": "OPEN",
            "remaining_seconds": 10 * 24 * 3600,
            "detail_completeness": "HTML_SCOPE_DEADLINE",
            "deadline_evidence": "EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME",
            "reference_no": "INDUSTRY-ANN-1038",
        }
        result = qualify_opportunity(
            item,
            {"engine": "provider", "name": "Ministry of Industry Procurement Announcements"},
        )
        self.assertNotIn("ENGINEERING", result["relevance_categories"])
        self.assertIn("INDUSTRIAL", result["relevance_categories"])

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
