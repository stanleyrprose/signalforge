from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.browser_escalation import REPORT_VERSION, browser_escalation_candidates
from signalforge.db import connect, migrate


class _Registry:
    raw = {
        "sources": {
            "S16": {
                "name": "YCDC Building",
                "role": "ACTIVE_SELECTIVE",
                "priority": 88,
                "engine": "direct_http",
                "discovery_url": "https://example.test/ycdc",
            },
            "S21": {
                "name": "Myanma Railways",
                "role": "ACTIVE_PRIMARY",
                "priority": 95,
                "engine": "direct_http",
                "discovery_url": "https://example.test/railways",
            },
            "S38": {
                "name": "Ministry of Industry",
                "role": "ACTIVE_PRIMARY",
                "priority": 90,
                "engine": "provider",
                "discovery_url": "https://example.test/industry",
            },
            "S41": {
                "name": "MYTEL Procurement",
                "role": "ACTIVE_PRIMARY",
                "priority": 99,
                "engine": "direct_http",
                "http_fetch_profile": "cloudrity_d1n_v1",
                "discovery_url": "https://example.test/mytel",
            },
            "S99": {
                "name": "403 Review",
                "role": "ACTIVE_SELECTIVE",
                "priority": 50,
                "engine": "direct_http",
                "discovery_url": "https://example.test/403",
            },
        }
    }

    def enabled_sources(self):
        return [(source_id, source) for source_id, source in self.raw["sources"].items()]


def _add_attempt(
    conn,
    *,
    source_id: str,
    suffix: str,
    failure: str,
    started_at: str = "2026-09-16T05:00:00Z",
    target_kind: str = "HTML",
) -> None:
    run_id = f"run-{source_id}-{suffix}"
    request_id = f"req-{source_id}-{suffix}"
    attempt_id = f"attempt-{source_id}-{suffix}"
    conn.execute(
        """
        INSERT INTO scheduler_runs(
            app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,
            started_at,finished_at,status,changed,signals_created,error
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        (run_id, "trigger", "POLL", source_id, f"worker-{suffix}", started_at, started_at, "FAILED", 0, 0, failure),
    )
    conn.execute(
        """
        INSERT INTO acquisition_requests(
            request_id,schema_version,scheduler_run_id,app_job_ref,source_id,
            source_policy_version,mode,reason,egress_profile,requested_at,
            primary_method,target_kind,timeout_seconds,expected_content_types_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            request_id,
            1,
            run_id,
            None,
            source_id,
            1,
            "PRIMARY",
            "SCHEDULED",
            "mm-intl-datacenter",
            started_at,
            "DIRECT_HTTP",
            target_kind,
            30,
            '["text/html"]',
        ),
    )
    conn.execute(
        """
        INSERT INTO acquisition_attempts(
            attempt_id,schema_version,request_id,attempt_number,source_id,
            source_policy_version,method,egress_profile,started_at,finished_at,
            status,acquisition_failure_class
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            attempt_id,
            1,
            request_id,
            1,
            source_id,
            1,
            "DIRECT_HTTP",
            "mm-intl-datacenter",
            started_at,
            started_at,
            "FAILED",
            failure,
        ),
    )


class BrowserEscalationCandidateTests(unittest.TestCase):
    def _db(self, root: str) -> Path:
        database = Path(root) / "signalforge.db"
        migrate(database)
        with connect(database) as conn, conn:
            _add_attempt(conn, source_id="S16", suffix="empty", failure="CONTENT_EMPTY")
            _add_attempt(conn, source_id="S21", suffix="timeout1", failure="CONNECT_TIMEOUT", target_kind="DISCOVERY")
            _add_attempt(conn, source_id="S21", suffix="timeout2", failure="CONNECT_TIMEOUT", started_at="2026-09-16T05:01:00Z", target_kind="DISCOVERY")
            _add_attempt(conn, source_id="S21", suffix="unknown", failure="TRANSPORT_UNKNOWN", started_at="2026-09-16T05:02:00Z", target_kind="DISCOVERY")
            _add_attempt(conn, source_id="S38", suffix="not-ready", failure="PROVIDER_NOT_READY", target_kind="DISCOVERY")
            _add_attempt(conn, source_id="S41", suffix="bot", failure="BOT_BLOCKED")
            _add_attempt(conn, source_id="S99", suffix="403a", failure="HTTP_403")
            _add_attempt(conn, source_id="S99", suffix="403b", failure="HTTP_403", started_at="2026-09-16T05:05:00Z")
            # PDF failures are intentionally not browser-escalation evidence.
            _add_attempt(conn, source_id="S16", suffix="pdf", failure="CONTENT_EMPTY", target_kind="PDF")
            for source_id, failures, last_error in (
                ("S16", 1, "empty content"),
                ("S21", 33, "timeout"),
                ("S38", 1, "provider not ready"),
                ("S41", 1, "bot blocked"),
                ("S99", 2, "HTTP 403"),
            ):
                conn.execute(
                    """
                    INSERT INTO source_state(
                        source_id,baseline_complete,last_success_at,last_error,
                        consecutive_failures,updated_at
                    ) VALUES (?,?,?,?,?,?)
                    """,
                    (source_id, 1, "2026-09-15T00:00:00Z", last_error, failures, "2026-09-16T05:05:00Z"),
                )
        return database

    def test_report_separates_browser_candidates_review_and_non_browser_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = browser_escalation_candidates(
                database=self._db(tmp),
                registry=_Registry(),  # type: ignore[arg-type]
                now=datetime(2026, 9, 16, 6, 0, tzinfo=UTC),
                window_days=7,
            )

        self.assertEqual(result["report_version"], REPORT_VERSION)
        self.assertEqual(result["summary"]["browser_ab_candidates"], 2)
        self.assertEqual(result["summary"]["review_first"], 1)
        self.assertEqual(result["summary"]["not_browser"], 2)
        by_id = {row["source_id"]: row for row in result["sources"]}

        self.assertEqual(by_id["S41"]["decision"], "AB_TEST_CANDIDATE")
        self.assertEqual(by_id["S41"]["candidate_score"], 100)
        self.assertTrue(by_id["S41"]["browser_ab_eligible"])
        self.assertEqual(by_id["S16"]["decision"], "AB_TEST_CANDIDATE")
        self.assertEqual(by_id["S16"]["failure_counts"], {"CONTENT_EMPTY": 1})
        self.assertEqual(by_id["S21"]["decision"], "NOT_BROWSER")
        self.assertFalse(by_id["S21"]["browser_ab_eligible"])
        self.assertEqual(by_id["S21"]["failure_counts"], {"CONNECT_TIMEOUT": 2, "TRANSPORT_UNKNOWN": 1})
        self.assertEqual(by_id["S21"]["current_consecutive_failures"], 33)
        self.assertEqual(by_id["S38"]["decision"], "NOT_BROWSER")
        self.assertEqual(by_id["S38"]["failure_counts"], {"PROVIDER_NOT_READY": 1})
        self.assertEqual(by_id["S99"]["decision"], "REVIEW_FIRST")
        self.assertEqual(by_id["S99"]["candidate_score"], 60)
        self.assertFalse(by_id["S99"]["browser_ab_eligible"])

    def test_generic_403_never_becomes_browser_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = browser_escalation_candidates(
                database=self._db(tmp),
                registry=_Registry(),  # type: ignore[arg-type]
                now=datetime(2026, 9, 16, 6, 0, tzinfo=UTC),
            )
        row = next(row for row in result["sources"] if row["source_id"] == "S99")
        self.assertEqual(row["decision"], "REVIEW_FIRST")
        self.assertFalse(result["policy"]["generic_http_403_is_browser_trigger"])

    def test_old_failures_outside_window_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                _add_attempt(
                    conn,
                    source_id="S16",
                    suffix="old",
                    failure="CONTENT_EMPTY",
                    started_at="2026-08-01T00:00:00Z",
                )
            result = browser_escalation_candidates(
                database=database,
                registry=_Registry(),  # type: ignore[arg-type]
                now=datetime(2026, 9, 16, 6, 0, tzinfo=UTC),
                window_days=7,
            )
        self.assertEqual(result["summary"]["sources_with_failed_html_attempts"], 0)
        self.assertEqual(result["candidates"], [])

    def test_window_and_limit_are_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "window_days"):
            browser_escalation_candidates(registry=_Registry(), window_days=0)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "limit"):
            browser_escalation_candidates(registry=_Registry(), limit=0)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
