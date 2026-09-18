from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from datetime import UTC, datetime
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from signalforge.cli import main
from signalforge.harness import evaluate_harness, persist_checkpoint


def _snapshots() -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    status = {
        "status": "PASS",
        "signalforge_health": "GREEN",
        "canonical_node": "bangkok",
        "counts": {
            "canonical_items": 10,
            "signals": 4,
            "scheduler_runs": 20,
            "recovery_backlog": 0,
        },
    }
    assurance = {
        "counts": {
            "open_misses": 0,
            "open_red_misses": 0,
        }
    }
    briefing = {
        "attention": [
            {
                "canonical_key": "SAMPLE:1",
                "mission_fit": True,
                "scope_excerpt": "Supply and installation of telecom power equipment",
                "signal_quality_band": "HIGH",
            }
        ],
        "watchlist": {"items": []},
        "assurance": {"metric_validity": "PASS"},
    }
    telegram = {
        "status": "PASS",
        "pending_count": 0,
        "pending": [],
    }
    return status, assurance, briefing, telegram


class HarnessTests(unittest.TestCase):
    def test_all_sensors_pass_definition_of_done(self) -> None:
        status, assurance, briefing, telegram = _snapshots()
        report = evaluate_harness(
            status_snapshot=status,
            assurance=assurance,
            briefing=briefing,
            telegram_dry_run=telegram,
            db_quick_check="ok",
            now=datetime(2026, 9, 18, 0, 0, tzinfo=UTC),
        )
        self.assertTrue(report["definition_of_done"]["passed"])
        self.assertTrue(all(sensor["status"] == "PASS" for sensor in report["sensors"].values()))

    def test_missing_procurement_scope_blocks_done(self) -> None:
        status, assurance, briefing, telegram = _snapshots()
        briefing["attention"][0]["scope_excerpt"] = ""
        report = evaluate_harness(
            status_snapshot=status,
            assurance=assurance,
            briefing=briefing,
            telegram_dry_run=telegram,
            db_quick_check="ok",
        )
        self.assertFalse(report["definition_of_done"]["passed"])
        self.assertEqual(report["sensors"]["S2"]["status"], "FAIL")
        self.assertEqual(report["sensors"]["S2"]["missing_scope_keys"], ["SAMPLE:1"])

    def test_pending_telegram_delivery_blocks_done(self) -> None:
        status, assurance, briefing, telegram = _snapshots()
        telegram["pending_count"] = 1
        telegram["pending"] = [{"canonical_key": "SAMPLE:1", "message": "valid message"}]
        report = evaluate_harness(
            status_snapshot=status,
            assurance=assurance,
            briefing=briefing,
            telegram_dry_run=telegram,
            db_quick_check="ok",
        )
        self.assertEqual(report["sensors"]["S3"]["status"], "FAIL")
        self.assertFalse(report["definition_of_done"]["passed"])

    def test_same_failure_escalates_after_three_verify_attempts(self) -> None:
        status, assurance, briefing, telegram = _snapshots()
        telegram["pending_count"] = 1
        telegram["pending"] = [{"canonical_key": "SAMPLE:1", "message": "valid message"}]
        report = evaluate_harness(
            status_snapshot=status,
            assurance=assurance,
            briefing=briefing,
            telegram_dry_run=telegram,
            db_quick_check="ok",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "harness.json"
            first = persist_checkpoint(report, path=path)
            second = persist_checkpoint(report, path=path)
            third = persist_checkpoint(report, path=path)
        self.assertEqual(first["phase"], "VERIFY")
        self.assertEqual(first["retry"]["attempt"], 1)
        self.assertEqual(second["retry"]["attempt"], 2)
        self.assertEqual(third["phase"], "ESCALATE")
        self.assertEqual(third["retry"]["attempt"], 3)
        self.assertEqual(third["next_action"], "reinspect_assumptions_or_operator_review")

    def test_cli_harness_verify_writes_checkpoint_and_returns_verify_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            checkpoint = Path(tmp) / "harness-checkpoint.json"
            output = io.StringIO()
            with patch.dict(os.environ, {"SIGNALFORGE_DB": str(database)}), redirect_stdout(output):
                code = main(["harness-verify", "--checkpoint", str(checkpoint)])
            result = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(result["phase"], "VERIFY")
            self.assertEqual(result["sensors"]["S0"]["status"], "PASS")
            self.assertEqual(result["sensors"]["S1"]["status"], "FAIL")
            self.assertEqual(result["retry"]["attempt"], 1)
            self.assertTrue(checkpoint.exists())
            self.assertEqual(json.loads(checkpoint.read_text(encoding="utf-8"))["phase"], "VERIFY")

    def test_success_resets_retry_state(self) -> None:
        status, assurance, briefing, telegram = _snapshots()
        failing_telegram = dict(telegram)
        failing_telegram["pending_count"] = 1
        failing_telegram["pending"] = [{"canonical_key": "SAMPLE:1", "message": "valid message"}]
        failed = evaluate_harness(
            status_snapshot=status,
            assurance=assurance,
            briefing=briefing,
            telegram_dry_run=failing_telegram,
            db_quick_check="ok",
        )
        passed = evaluate_harness(
            status_snapshot=status,
            assurance=assurance,
            briefing=briefing,
            telegram_dry_run=telegram,
            db_quick_check="ok",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "harness.json"
            persist_checkpoint(failed, path=path)
            result = persist_checkpoint(passed, path=path)
        self.assertEqual(result["phase"], "DONE")
        self.assertEqual(result["retry"]["attempt"], 0)
        self.assertIsNone(result["retry"]["failure_signature"])


if __name__ == "__main__":
    unittest.main()
