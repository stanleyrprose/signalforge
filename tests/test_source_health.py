from __future__ import annotations

import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.cli import status
from signalforge.config import Registry
from signalforge.db import connect, migrate


ROOT = Path(__file__).resolve().parents[1]


class SourceHealthTests(unittest.TestCase):
    def _seed(self, db: Path, *, last_success: str, last_error: str | None = None, failures: int = 0) -> None:
        migrate(db)
        with connect(db) as conn, conn:
            conn.execute(
                """
                INSERT INTO source_state(
                    source_id,baseline_complete,last_success_at,next_due_at,last_error,consecutive_failures,updated_at
                ) VALUES ('S13',1,?,?,?,?,?)
                """,
                (last_success, last_success, last_error, failures, last_success),
            )

    def _run(self, db: Path, *, now: datetime) -> dict[str, object]:
        with patch.dict(os.environ, {"SIGNALFORGE_DB": str(db), "SIGNALFORGE_REPO_ROOT": str(ROOT)}, clear=False):
            return status(now=now)

    def test_registry_freezes_source_health_thresholds(self) -> None:
        source = Registry.load(ROOT).source("S13")
        health = source["health_policy"]
        self.assertEqual(health["freshness_yellow_seconds"], 1800)
        self.assertEqual(health["freshness_red_seconds"], 3600)
        self.assertEqual(health["parse_window_runs"], 10)
        self.assertEqual(health["parse_min_attempts"], 3)
        self.assertEqual(health["parse_yellow_ratio"], 0.9)
        self.assertEqual(health["parse_red_ratio"], 0.7)

    def test_green_health_with_unknown_parser_until_minimum_sample(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "signalforge.db"
            self._seed(db, last_success="2026-09-03T12:00:00Z")
            value = self._run(db, now=datetime(2026, 9, 3, 12, 10, tzinfo=UTC))
            health = value["sources"][0]["health"]
            self.assertEqual(value["status"], "PASS")
            self.assertEqual(health["source_health"], "GREEN")
            self.assertEqual(health["freshness_health"], "GREEN")
            self.assertEqual(health["parse_health"], "UNKNOWN")
            self.assertEqual(health["parse_attempts"], 0)

    def test_parse_ratio_is_yellow_and_red_from_structured_recent_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "signalforge.db"
            self._seed(db, last_success="2026-09-03T12:00:00Z")
            with connect(db) as conn, conn:
                conn.execute(
                    """INSERT INTO scheduler_runs(
                        app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,status,details_attempted,details_succeeded,tenders_parsed
                    ) VALUES ('yellow','poll:S13:1','POLL','S13','worker-1','2026-09-03T12:00:00Z','SUCCESS',10,8,8)"""
                )
            yellow = self._run(db, now=datetime(2026, 9, 3, 12, 10, tzinfo=UTC))
            health = yellow["sources"][0]["health"]
            self.assertEqual(health["parse_health"], "YELLOW")
            self.assertEqual(health["parse_success_ratio"], 0.8)
            self.assertEqual(yellow["status"], "DEGRADED")

            with connect(db) as conn, conn:
                conn.execute("DELETE FROM scheduler_runs")
                conn.execute(
                    """INSERT INTO scheduler_runs(
                        app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,status,details_attempted,details_succeeded,tenders_parsed
                    ) VALUES ('red','poll:S13:2','POLL','S13','worker-2','2026-09-03T12:05:00Z','SUCCESS',10,6,6)"""
                )
            red = self._run(db, now=datetime(2026, 9, 3, 12, 10, tzinfo=UTC))
            health = red["sources"][0]["health"]
            self.assertEqual(health["parse_health"], "RED")
            self.assertEqual(health["source_health"], "RED")

    def test_freshness_and_fetch_health_degrade_independently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "signalforge.db"
            self._seed(db, last_success="2026-09-03T10:00:00Z")
            stale = self._run(db, now=datetime(2026, 9, 3, 12, 0, tzinfo=UTC))
            health = stale["sources"][0]["health"]
            self.assertEqual(health["freshness_health"], "RED")
            self.assertEqual(health["source_health"], "RED")

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "signalforge.db"
            self._seed(db, last_success="2026-09-03T12:00:00Z", last_error="detail_errors=1")
            partial = self._run(db, now=datetime(2026, 9, 3, 12, 10, tzinfo=UTC))
            health = partial["sources"][0]["health"]
            self.assertEqual(health["fetch_health"], "YELLOW")
            self.assertEqual(health["source_health"], "YELLOW")


if __name__ == "__main__":
    unittest.main()
