from __future__ import annotations

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from signalforge.cli import main
from signalforge.jev_shadow import DEFAULT_THRESHOLD, jev_shadow_report, shadow_main_briefing


def _row(
    *,
    source_id: str,
    canonical_key: str,
    scope_summary: str,
    item_kind: str = "TENDER",
    primary_relevance: str = "OTHER",
    relevance_categories: list[str] | None = None,
) -> dict[str, object]:
    return {
        "source_id": source_id,
        "canonical_key": canonical_key,
        "item_kind": item_kind,
        "issuer": "Myanmar Government Department",
        "title": canonical_key,
        "scope_summary": scope_summary,
        "project_name": scope_summary,
        "primary_relevance": primary_relevance,
        "relevance_categories": relevance_categories or ["OTHER"],
    }


class JevShadowTests(unittest.TestCase):
    def test_shadow_main_briefing_uses_calibrated_atomic_gate(self) -> None:
        self.assertEqual(DEFAULT_THRESHOLD, 0.60)
        self.assertTrue(
            shadow_main_briefing(
                commercial_opportunity=0.95,
                sector=0.60,
                stage="open_opportunity",
            )
        )
        self.assertFalse(
            shadow_main_briefing(
                commercial_opportunity=0.95,
                sector=0.58,
                stage="open_opportunity",
            )
        )
        self.assertFalse(
            shadow_main_briefing(
                commercial_opportunity=0.59,
                sector=0.99,
                stage="open_opportunity",
            )
        )
        self.assertFalse(
            shadow_main_briefing(
                commercial_opportunity=0.99,
                sector=0.99,
                stage="post_bid_workflow",
            )
        )
        with self.assertRaisesRegex(ValueError, "threshold"):
            shadow_main_briefing(
                commercial_opportunity=0.9,
                sector=0.9,
                stage="open_opportunity",
                threshold=1.1,
            )

    def test_shadow_report_is_read_only_comparison_with_deterministic_authority(self) -> None:
        tracked = [
            _row(
                source_id="SXX",
                canonical_key="agree-include",
                scope_summary="Windows Server and SQL Server infrastructure",
                primary_relevance="ICT",
                relevance_categories=["ICT"],
            ),
            _row(
                source_id="SXX",
                canonical_key="jev-only",
                scope_summary="Medical equipment",
                primary_relevance="MEDICAL",
                relevance_categories=["MEDICAL"],
            ),
            _row(
                source_id="SXX",
                canonical_key="deterministic-only",
                scope_summary="Bridge construction works",
                primary_relevance="CONSTRUCTION",
                relevance_categories=["CONSTRUCTION"],
            ),
            _row(
                source_id="SXX",
                canonical_key="agree-exclude",
                scope_summary="Office furniture",
            ),
        ]

        answers = {
            "agree-include": (0.95, 0.98, "open_opportunity"),
            "jev-only": (0.96, 0.91, "open_opportunity"),
            "deterministic-only": (0.96, 0.59, "open_opportunity"),
            "agree-exclude": (0.95, 0.20, "open_opportunity"),
        }

        def fake_evaluator(state: dict[str, object]) -> dict[str, object]:
            commercial, sector, stage = answers[str(state["canonical_key"])]
            return {
                "commercial_opportunity": commercial,
                "procurement": 0.9,
                "sector": sector,
                "stage": stage,
                "stage_confidence": 0.99,
                "stage_probabilities": {stage: 1.0},
                "request_id": f"req-{state['canonical_key']}",
                "model": "jev-test",
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }

        with patch(
            "signalforge.jev_shadow.current_opportunities",
            return_value={"opportunities": tracked},
        ) as current:
            result = jev_shadow_report(evaluator=fake_evaluator, threshold=0.60, limit=4)

        current.assert_called_once()
        self.assertEqual(result["status"], "SHADOW_ONLY")
        self.assertEqual(result["authority"], "DETERMINISTIC_ONLY")
        self.assertEqual(result["production_effect"], "NONE")
        self.assertEqual(
            result["scope"]["false_negative_coverage_outside_current_opportunities"],
            "NOT_PROVEN",
        )
        self.assertEqual(
            result["counts"],
            {
                "tracked": 4,
                "evaluated": 4,
                "deterministic_include": 2,
                "jev_include": 2,
                "agreements": 2,
                "disagreements": 2,
                "jev_only": 1,
                "deterministic_only": 1,
            },
        )
        self.assertEqual(
            [row["decision"] for row in result["rows"]],
            [
                "AGREE_INCLUDE",
                "JEV_ONLY",
                "DETERMINISTIC_ONLY",
                "AGREE_EXCLUDE",
            ],
        )

    def test_shadow_report_requires_explicit_optional_credential_only_without_injected_evaluator(self) -> None:
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}):
            with patch(
                "signalforge.jev_shadow.current_opportunities",
                return_value={"opportunities": []},
            ):
                with self.assertRaisesRegex(RuntimeError, "TYPESAFE_API_KEY"):
                    jev_shadow_report()

    def test_shadow_report_validates_limit_before_external_call(self) -> None:
        with self.assertRaisesRegex(ValueError, "limit"):
            jev_shadow_report(limit=0, evaluator=lambda _state: {})

    def test_cli_exposes_shadow_command_without_changing_authority(self) -> None:
        report = {
            "status": "SHADOW_ONLY",
            "authority": "DETERMINISTIC_ONLY",
            "production_effect": "NONE",
        }
        stdout = io.StringIO()
        with patch("signalforge.cli.jev_shadow_report", return_value=report) as mocked:
            with redirect_stdout(stdout):
                code = main(
                    [
                        "jev-shadow",
                        "--threshold",
                        "0.65",
                        "--model",
                        "jev-test",
                        "--limit",
                        "7",
                        "--include-expired",
                    ]
                )

        self.assertEqual(code, 0)
        mocked.assert_called_once_with(
            threshold=0.65,
            model="jev-test",
            limit=7,
            include_expired=True,
        )
        self.assertIn('"authority": "DETERMINISTIC_ONLY"', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
