from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.business_kpis import business_kpi_report, summarize_opportunity_quality
from signalforge.db import migrate


class BusinessKpiTests(unittest.TestCase):
    def test_quality_report_keeps_actionability_and_assurance_separate(self) -> None:
        canonical = [
            {
                "signal_quality_score": 90,
                "signal_quality_band": "VERY_HIGH",
                "trust_grade": "A",
                "signal_quality_dimensions": {
                    "time": {"score": 20},
                    "next_action": {"score": 10},
                    "official_evidence": {"score": 10},
                },
            },
            {
                "signal_quality_score": 45,
                "signal_quality_band": "REVIEW",
                "trust_grade": "B",
                "signal_quality_dimensions": {
                    "time": {"score": 0},
                    "next_action": {"score": 0},
                    "official_evidence": {"score": 10},
                },
            },
        ]
        verified_external = [
            {
                "issuer_document_verified": True,
                "issuer_identity_verified": True,
                "scope_verified": True,
                "deadline_verified": True,
                "canonical_truth": False,
                "document_sha256": "a" * 64,
            }
        ]
        assurance = {
            "latest_metric_review": {
                "status": "REVIEW",
                "observed_at": "2026-09-23T00:00:00Z",
                "metrics": {
                    "mandatory_coverage_proof_rate": 0.75,
                    "mandatory_business_coverage_accounted_rate": 1.0,
                    "open_misses": 1,
                    "open_red_misses": 0,
                    "noise_samples_conclusive_window": 4,
                    "noise_false_negatives_window": 1,
                    "noise_false_negative_rate": 0.25,
                },
            },
            "counts": {"open_misses": 1, "open_red_misses": 0},
            "coverage_risk_count": 2,
        }

        report = summarize_opportunity_quality(
            canonical_rows=canonical,
            verified_external_rows=verified_external,
            assurance=assurance,
        )

        self.assertEqual(report["business_current_opportunities"], 3)
        quality = report["canonical_signal_quality"]
        self.assertEqual(quality["score_average"], 67.5)
        self.assertEqual(quality["score_median"], 67.5)
        self.assertEqual(quality["band_counts"]["VERY_HIGH"], 1)
        self.assertEqual(quality["band_counts"]["REVIEW"], 1)
        self.assertEqual(quality["high_or_very_high_rate"], 0.5)
        self.assertEqual(quality["review_or_low_rate"], 0.5)
        self.assertEqual(quality["trust_a_rate"], 0.5)
        self.assertEqual(quality["timeframe_known_rate"], 0.5)
        self.assertEqual(quality["explicit_next_action_rate"], 0.5)
        self.assertEqual(quality["official_evidence_rate"], 1.0)

        external = report["verified_external_quality"]
        self.assertEqual(external["proof_complete_count"], 1)
        self.assertEqual(external["proof_complete_rate"], 1.0)
        self.assertFalse(external["signal_quality_score_assigned"])

        risk = report["assurance"]
        self.assertEqual(risk["metric_validity"], "REVIEW")
        self.assertEqual(risk["mandatory_coverage_proof_rate"], 0.75)
        self.assertEqual(risk["mandatory_business_coverage_accounted_rate"], 1.0)
        self.assertEqual(risk["noise_false_negative_rate"], 0.25)
        self.assertEqual(risk["coverage_risk_count"], 2)
        self.assertTrue(report["semantics"]["no_opaque_composite_score"])
        self.assertTrue(report["semantics"]["signal_quality_is_not_false_positive_precision"])

    def test_business_kpi_report_exposes_review_only_procurement_link_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            link_queue = {
                "metric": "PROJECT_PROCUREMENT_LINK_REVIEW_QUEUE",
                "summary": {
                    "tracked_projects": 1,
                    "already_linked_projects": 0,
                    "unlinked_projects": 1,
                    "projects_with_suggestions": 1,
                    "suggestions": 1,
                    "returned_suggestions": 1,
                },
                "suggestions": [{"project_key": "pinpet-steel-factory-power"}],
                "semantics": {"review_only": True, "no_link_write": True},
            }
            precursor_queue = {"summary": {"candidates": 0, "tracked": 1}}
            leadtime = {"summary": {"linked_projects": 0, "median_lead_days": None}}
            assurance = {
                "latest_metric_review": {"status": "PASS", "metrics": {}},
                "counts": {},
                "coverage_risk_count": 0,
            }
            with patch(
                "signalforge.business_kpis.current_opportunities",
                return_value={"opportunities": []},
            ), patch(
                "signalforge.business_kpis.verified_external_opportunities",
                return_value=[],
            ), patch(
                "signalforge.business_kpis.assurance_status",
                return_value=assurance,
            ), patch(
                "signalforge.business_kpis.precursor_candidates",
                return_value=precursor_queue,
            ), patch(
                "signalforge.business_kpis.procurement_link_suggestions",
                return_value=link_queue,
            ), patch(
                "signalforge.business_kpis.leadtime_report",
                return_value=leadtime,
            ):
                report = business_kpi_report(
                    database=database,
                    now=datetime(2026, 9, 27, 12, 0, tzinfo=UTC),
                    registry=object(),  # type: ignore[arg-type]
                    lead_limit=20,
                )

            self.assertIs(report["project_procurement_link_review"], link_queue)
            self.assertIs(report["project_precursor_pipeline"], precursor_queue)
            self.assertIs(report["project_to_procurement_lead_time"], leadtime)
            self.assertEqual(report["opportunity_output_quality"]["business_current_opportunities"], 0)



if __name__ == "__main__":
    unittest.main()
