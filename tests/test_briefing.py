from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from signalforge.briefing import business_briefing
from signalforge.cli import main


class BriefingTests(unittest.TestCase):
    def _opportunities(self) -> dict[str, object]:
        return {
            "status": "PASS",
            "qualification_policy_version": 1,
            "as_of": "2026-09-09T10:00:00Z",
            "count": 4,
            "counts": {"OPEN": 3, "UNKNOWN": 1, "EXPIRED": 0},
            "qualification_counts": {
                "trust_grade": {"A": 3, "B": 1, "C": 0},
                "priority_band": {"HIGH": 2, "MEDIUM": 1, "REVIEW": 1, "LOW": 0},
                "relevance": {"ICT": 1, "INDUSTRIAL": 2, "MEDICAL": 1},
            },
            "opportunities": [
                {
                    "canonical_key": "industry:urgent",
                    "priority_band": "HIGH",
                    "trust_grade": "A",
                    "primary_relevance": "INDUSTRIAL",
                    "relevance_categories": ["INDUSTRIAL"],
                    "urgency": "URGENT",
                    "issuer": "Ministry of Industry",
                    "title": "Urgent industrial tender",
                    "reference_no": "IND-1",
                    "deadline": "2026-09-11",
                    "deadline_time": "16:00",
                    "deadline_at": "2026-09-11T16:00:00+06:30",
                    "deadline_status": "OPEN",
                    "evidence_level": "OFFICIAL_HTML_VIA_PROVIDER",
                    "completeness": "FULL",
                    "scope_summary": "Chemical procurement with explicit specification and delivery requirement.",
                    "latest_signal_type": "NEW",
                    "latest_signal_at": "2026-09-09T02:00:00Z",
                    "signal_count": 1,
                    "url": "https://example.test/industry",
                },
                {
                    "canonical_key": "mofa:ict",
                    "priority_band": "HIGH",
                    "trust_grade": "A",
                    "primary_relevance": "ICT",
                    "relevance_categories": ["ICT"],
                    "urgency": "NORMAL",
                    "issuer": "Ministry of Foreign Affairs",
                    "title": "Data Server tender",
                    "reference_no": "MOFA-1",
                    "deadline": "2026-09-18",
                    "deadline_time": "16:30",
                    "deadline_at": "2026-09-18T16:30:00+06:30",
                    "deadline_status": "OPEN",
                    "evidence_level": "OFFICIAL_HTML_PLUS_TEXT_PDF",
                    "completeness": "FULL",
                    "scope_summary": "Dell PowerEdge server, Windows Server and SQL Server with installation and maintenance.",
                    "latest_signal_type": "UPDATED",
                    "latest_signal_at": "2026-09-08T17:50:00Z",
                    "signal_count": 1,
                    "url": "https://example.test/mofa",
                },
                {
                    "canonical_key": "industry:watch",
                    "priority_band": "MEDIUM",
                    "trust_grade": "A",
                    "primary_relevance": "INDUSTRIAL",
                    "relevance_categories": ["INDUSTRIAL"],
                    "urgency": "NORMAL",
                    "issuer": "Ministry of Industry",
                    "title": "Watchlist tender",
                    "reference_no": "IND-2",
                    "deadline": "2026-10-02",
                    "deadline_time": "16:00",
                    "deadline_at": "2026-10-02T16:00:00+06:30",
                    "deadline_status": "OPEN",
                    "evidence_level": "OFFICIAL_HTML_VIA_PROVIDER",
                    "completeness": "FULL",
                    "scope_summary": "Industrial raw material procurement.",
                    "latest_signal_type": "NEW",
                    "latest_signal_at": "2026-09-09T02:01:00Z",
                    "signal_count": 1,
                    "url": "https://example.test/watch",
                },
                {
                    "canonical_key": "doms:review",
                    "priority_band": "REVIEW",
                    "trust_grade": "B",
                    "primary_relevance": "MEDICAL",
                    "relevance_categories": ["MEDICAL"],
                    "urgency": "UNKNOWN",
                    "issuer": "Department of Medical Services",
                    "title": "Medical tender references",
                    "reference_no": "8DMS/2026-2027(L)",
                    "reference_numbers": ["8DMS/2026-2027(L)", "9DMS/2026-2027(L)", "10DMS/2026-2027(F)"],
                    "deadline": None,
                    "deadline_time": None,
                    "deadline_at": None,
                    "deadline_status": "UNKNOWN",
                    "evidence_level": "OFFICIAL_HTML",
                    "completeness": "PARTIAL",
                    "scope_summary": "Official medical tender references with attachment metadata but no published deadline.",
                    "latest_signal_type": "UPDATED",
                    "latest_signal_at": "2026-09-09T09:05:00Z",
                    "signal_count": 2,
                    "url": "https://example.test/doms",
                },
            ],
        }

    def test_briefing_expands_high_and_review_but_summarizes_medium(self) -> None:
        with patch("signalforge.briefing.current_opportunities", return_value=self._opportunities()):
            result = business_briefing()

        self.assertEqual(result["briefing_policy_version"], 1)
        self.assertEqual(result["qualification_policy_version"], 1)
        self.assertEqual(result["attention_count"], 3)
        self.assertEqual(result["attention_action_counts"], {"ACT_NOW": 1, "PRIORITIZE": 1, "REVIEW": 1})
        self.assertEqual(
            [item["canonical_key"] for item in result["attention"]],
            ["industry:urgent", "mofa:ict", "doms:review"],
        )
        self.assertEqual(result["attention"][0]["attention_action"], "ACT_NOW")
        self.assertIn("DEADLINE_WITHIN_72H", result["attention"][0]["why_now"])
        self.assertEqual(result["attention"][1]["attention_action"], "PRIORITIZE")
        self.assertIn("STRATEGIC_FIT_ICT_TELECOM", result["attention"][1]["why_now"])
        self.assertEqual(result["attention"][2]["attention_action"], "REVIEW")
        self.assertIn("DEADLINE_UNKNOWN", result["attention"][2]["why_now"])
        self.assertEqual(result["watchlist"]["count"], 1)
        self.assertEqual(result["watchlist"]["canonical_keys"], ["industry:watch"])
        self.assertTrue(result["delivery_contract"]["facts_must_not_be_inferred"])

    def test_deadline_kind_and_opening_semantics_are_preserved_for_delivery(self) -> None:
        data = self._opportunities()
        item = data["opportunities"][0]
        item["deadline_kind"] = "TENDER_FORM_SALE_CLOSE"
        item["tender_opening_date"] = "2026-09-15"
        item["tender_opening_time"] = "13:30"
        with patch("signalforge.briefing.current_opportunities", return_value=data):
            result = business_briefing()
        attention = result["attention"][0]
        self.assertEqual(attention["deadline_kind"], "TENDER_FORM_SALE_CLOSE")
        self.assertEqual(attention["tender_opening_date"], "2026-09-15")
        self.assertEqual(attention["tender_opening_time"], "13:30")

    def test_scope_excerpt_is_bounded(self) -> None:
        data = self._opportunities()
        data["opportunities"][0]["scope_summary"] = "x" * 1000
        with patch("signalforge.briefing.current_opportunities", return_value=data):
            result = business_briefing()
        excerpt = result["attention"][0]["scope_excerpt"]
        self.assertLessEqual(len(excerpt), 420)
        self.assertTrue(excerpt.endswith("…"))

    def test_cli_briefing_is_read_only_no_argument_surface(self) -> None:
        payload = {"status": "PASS", "briefing_policy_version": 1, "attention_count": 0}
        output = io.StringIO()
        with patch("signalforge.cli.business_briefing", return_value=payload), redirect_stdout(output):
            code = main(["briefing"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), payload)


if __name__ == "__main__":
    unittest.main()
