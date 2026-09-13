from __future__ import annotations

import unittest

from signalforge.signal_quality import score_signal_quality


class SignalQualityTests(unittest.TestCase):
    def test_complete_ict_tender_is_very_high_quality(self) -> None:
        item = {
            "issuer": "Ministry of Foreign Affairs, Myanmar",
            "title": "Data Server procurement",
            "scope_summary": "Data Server (1) Set. Submit tender to Office No. 30 Nay Pyi Taw.",
            "deadline_status": "OPEN",
            "deadline_time": "16:30",
            "deadline_evidence": "OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME",
            "evidence_level": "OFFICIAL_HTML_PLUS_TEXT_PDF",
            "relevance_categories": ["ICT"],
            "urgency": "NORMAL",
        }
        result = score_signal_quality(item)
        self.assertGreaterEqual(result["signal_quality_score"], 85)
        self.assertEqual(result["signal_quality_band"], "VERY_HIGH")
        self.assertEqual(
            result["signal_quality_score"],
            result["signal_quality_evidence_score"] + result["signal_quality_context_score"],
        )
        self.assertEqual(result["signal_quality_evidence_max"], 85)
        self.assertEqual(result["signal_quality_context_max"], 15)
        self.assertIn("QUANTIFIED_SCOPE", result["signal_quality_strengths"])
        self.assertIn("PARTICIPATION_PATH_KNOWN", result["signal_quality_strengths"])

    def test_mte_time_bound_partial_commercial_event_is_medium_not_news_low(self) -> None:
        mte = {
            "issuer": "Myanma Timber Enterprise",
            "title": "Local Marketing and Milling Department, Open Tender No (6/2026-2027)(15.9.2026)",
            "scope_summary": "Local Marketing and Milling Department open tender",
            "deadline_status": "UNKNOWN",
            "action_date": "2026-09-15",
            "action_date_evidence": "EXPLICIT_OFFICIAL_TITLE_DATE",
            "evidence_level": "OFFICIAL_HTML",
            "relevance_categories": ["OTHER"],
            "urgency": "SOON",
        }
        news = {
            "issuer": "Myanma Timber Enterprise",
            "title": "General announcement",
            "scope_summary": "General corporate announcement for public information only",
            "deadline_status": "UNKNOWN",
            "evidence_level": "OFFICIAL_HTML",
            "relevance_categories": ["OTHER"],
            "urgency": "UNKNOWN",
        }
        mte_result = score_signal_quality(mte)
        news_result = score_signal_quality(news)
        self.assertEqual(mte_result["signal_quality_score"], 59)
        self.assertEqual(mte_result["signal_quality_band"], "MEDIUM")
        self.assertEqual(news_result["signal_quality_band"], "LOW")
        self.assertGreater(mte_result["signal_quality_score"], news_result["signal_quality_score"] + 15)

    def test_unknown_deadline_reference_only_event_stays_review_quality(self) -> None:
        item = {
            "issuer": "Department of Medical Services, Ministry of Health",
            "title": "Tender references",
            "scope_summary": "8DMS/2026-2027(L) 9DMS/2026-2027(L) 10DMS/2026-2027(F)",
            "deadline_status": "UNKNOWN",
            "evidence_level": "OFFICIAL_HTML",
            "relevance_categories": ["MEDICAL"],
            "urgency": "UNKNOWN",
        }
        result = score_signal_quality(item)
        self.assertEqual(result["signal_quality_score"], 40)
        self.assertEqual(result["signal_quality_band"], "REVIEW")
        self.assertIn("ACTION_TIMEFRAME_UNKNOWN", result["signal_quality_gaps"])
        self.assertIn("NEXT_ACTION_MISSING", result["signal_quality_gaps"])

    def test_score_is_explicitly_priority_independent(self) -> None:
        item = {
            "issuer": "Myanma Railways",
            "title": "Locomotive spare parts (106 types)",
            "scope_summary": "Locomotive spare parts (106) items",
            "deadline_status": "OPEN",
            "deadline": "2026-09-14",
            "deadline_evidence": "EXPLICIT_HTML_TENDER_CLOSE_DATE",
            "evidence_level": "OFFICIAL_HTML",
            "relevance_categories": ["OTHER"],
            "urgency": "SOON",
            "priority_band": "MEDIUM",
        }
        result = score_signal_quality(item)
        self.assertEqual(result["signal_quality_band"], "HIGH")
        self.assertTrue(result["signal_quality_priority_independent"])
        self.assertEqual(item["priority_band"], "MEDIUM")


if __name__ == "__main__":
    unittest.main()
