from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signalforge.cli import main
from signalforge.db import connect, migrate
from signalforge.jev_noise_shadow import jev_noise_shadow_report, noise_review_recommended


def _insert_sample(
    database: Path,
    *,
    sample_id: str,
    source_id: str,
    candidate_kind: str,
    payload: dict[str, object],
    review_status: str = "PENDING",
) -> None:
    with connect(database) as conn, conn:
        conn.execute(
            """
            INSERT INTO noise_review_samples(
                noise_sample_id,assurance_run_id,source_id,candidate_kind,candidate_ref,
                evidence_url,sample_basis,sampled_at,payload_json,review_status
            ) VALUES (?,NULL,?,?,?,?,?,?,?,?)
            """,
            (
                sample_id,
                source_id,
                candidate_kind,
                f"ref:{sample_id}",
                f"https://example.test/{sample_id}",
                "TEST",
                "2026-09-19T00:00:00Z",
                json.dumps(payload),
                review_status,
            ),
        )


class JevNoiseShadowTests(unittest.TestCase):
    def test_review_recommendation_uses_recall_oriented_shadow_threshold(self) -> None:
        self.assertTrue(
            noise_review_recommended(
                open_actionable=0.50,
                mission_sector=0.60,
                page_state="contains_open_opportunity",
            )
        )
        self.assertFalse(
            noise_review_recommended(
                open_actionable=0.49,
                mission_sector=0.99,
                page_state="contains_open_opportunity",
            )
        )
        self.assertFalse(
            noise_review_recommended(
                open_actionable=0.99,
                mission_sector=0.59,
                page_state="contains_open_opportunity",
            )
        )
        self.assertFalse(
            noise_review_recommended(
                open_actionable=0.99,
                mission_sector=0.99,
                page_state="expired_or_closed",
            )
        )

    def test_report_reads_existing_review_queue_without_writing_review_or_miss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "signalforge.db"
            evidence = root / "evidence"
            artifact = evidence / "S22" / "hash.html"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(
                "<html><body>Open Tender for vessel engineering works. "
                "Bid submission deadline 30 September 2026.</body></html>",
                encoding="utf-8",
            )
            migrate(database)
            _insert_sample(
                database,
                sample_id="zero",
                source_id="S22",
                candidate_kind="ZERO_ITEM_PROCESSING",
                payload={
                    "artifact_path": "/srv/signalforge/evidence/S22/hash.html",
                    "artifact_sha256": "hash",
                    "finished_at": "2026-09-16T01:17:50Z",
                },
            )
            _insert_sample(
                database,
                sample_id="nonstandard",
                source_id="S30",
                candidate_kind="INDEPENDENT_LISTING_NONSTANDARD",
                payload={"title": "Tender award result", "url": "https://example.test/award"},
            )
            _insert_sample(
                database,
                sample_id="history",
                source_id="S25",
                candidate_kind="KNOWN_HISTORICAL_SIGNAL_NOISE",
                payload={"signal_type": "UPDATED"},
            )

            def evaluator(state: dict[str, object]) -> dict[str, object]:
                if state["source_id"] == "S22":
                    return {
                        "open_actionable": 0.50,
                        "mission_sector": 0.75,
                        "page_state": "contains_open_opportunity",
                        "page_state_confidence": 0.9,
                        "page_state_probabilities": {"contains_open_opportunity": 0.9},
                        "request_id": "req-s22",
                        "model": "jev-test",
                        "usage": {},
                    }
                return {
                    "open_actionable": 0.05,
                    "mission_sector": 0.20,
                    "page_state": "post_bid_result",
                    "page_state_confidence": 0.95,
                    "page_state_probabilities": {"post_bid_result": 0.95},
                    "request_id": "req-other",
                    "model": "jev-test",
                    "usage": {},
                }

            report = jev_noise_shadow_report(
                database=database,
                evidence_directory=evidence,
                status="PENDING",
                limit=10,
                evaluator=evaluator,
            )

            self.assertEqual(report["status"], "SHADOW_ONLY")
            self.assertEqual(report["authority"], "HUMAN_REVIEW_REQUIRED")
            self.assertEqual(report["production_effect"], "NONE")
            self.assertEqual(report["writes"], "NONE")
            self.assertEqual(
                report["counts"],
                {"tracked": 3, "evaluated": 2, "skipped": 1, "review_recommended": 1},
            )
            recommendations = {
                row["noise_sample_id"]: row["recommendation"]
                for row in report["rows"]
            }
            self.assertEqual(recommendations["zero"], "REVIEW_RECOMMENDED")
            self.assertEqual(recommendations["nonstandard"], "NO_JEV_ESCALATION")
            self.assertEqual(recommendations["history"], "SKIPPED_INSUFFICIENT_EVIDENCE")

            with connect(database) as conn:
                self.assertEqual(
                    conn.execute(
                        "SELECT COUNT(*) FROM noise_review_samples WHERE review_status='PENDING'"
                    ).fetchone()[0],
                    3,
                )
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM missed_signals").fetchone()[0], 0)

    def test_reviewed_confusion_is_reported_without_feeding_human_label_to_evaluator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "signalforge.db"
            evidence = root / "evidence"
            for source_id, name in (("S22", "fn"), ("S40", "noise")):
                path = evidence / source_id / f"{name}.html"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("<html><body>official evidence</body></html>", encoding="utf-8")
            migrate(database)
            _insert_sample(
                database,
                sample_id="fn",
                source_id="S22",
                candidate_kind="ZERO_ITEM_PROCESSING",
                payload={
                    "artifact_path": "/srv/signalforge/evidence/S22/fn.html",
                    "finished_at": "2026-09-16T00:00:00Z",
                },
                review_status="FALSE_NEGATIVE",
            )
            _insert_sample(
                database,
                sample_id="noise",
                source_id="S40",
                candidate_kind="ZERO_ITEM_PROCESSING",
                payload={
                    "artifact_path": "/srv/signalforge/evidence/S40/noise.html",
                    "finished_at": "2026-09-16T00:00:00Z",
                },
                review_status="CONFIRMED_NOISE",
            )

            seen_states: list[dict[str, object]] = []

            def evaluator(state: dict[str, object]) -> dict[str, object]:
                seen_states.append(dict(state))
                is_fn = state["source_id"] == "S22"
                return {
                    "open_actionable": 0.50 if is_fn else 0.05,
                    "mission_sector": 0.75 if is_fn else 0.20,
                    "page_state": "contains_open_opportunity" if is_fn else "post_bid_result",
                    "page_state_confidence": 0.9,
                    "page_state_probabilities": {},
                    "request_id": "req",
                    "model": "jev-test",
                    "usage": {},
                }

            report = jev_noise_shadow_report(
                database=database,
                evidence_directory=evidence,
                status=None,
                evaluator=evaluator,
            )
            self.assertEqual(report["reviewed_confusion"], {"tp": 1, "fp": 0, "tn": 1, "fn": 0})
            self.assertTrue(all("review_status" not in state for state in seen_states))
            self.assertTrue(all("review_note" not in state for state in seen_states))

    def test_cli_exposes_explicit_noise_shadow_command(self) -> None:
        report = {
            "status": "SHADOW_ONLY",
            "authority": "HUMAN_REVIEW_REQUIRED",
            "production_effect": "NONE",
        }
        with patch("signalforge.cli.jev_noise_shadow_report", return_value=report) as mocked:
            self.assertEqual(
                main(
                    [
                        "jev-noise-shadow",
                        "--status",
                        "ALL",
                        "--limit",
                        "12",
                        "--open-threshold",
                        "0.50",
                        "--sector-threshold",
                        "0.60",
                        "--model",
                        "jev-test",
                        "--database",
                        "/tmp/test.db",
                        "--evidence-root",
                        "/tmp/evidence",
                    ]
                ),
                0,
            )
        mocked.assert_called_once_with(
            database=Path("/tmp/test.db"),
            evidence_directory=Path("/tmp/evidence"),
            status=None,
            limit=12,
            open_threshold=0.50,
            sector_threshold=0.60,
            model="jev-test",
        )


if __name__ == "__main__":
    unittest.main()
