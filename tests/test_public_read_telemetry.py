from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from signalforge.db import connect
from signalforge.provider_queue import initialize_provider_queue
from signalforge.public_read_telemetry import (
    public_read_telemetry_alert,
    public_read_telemetry_report,
)

NOW = datetime(2026, 9, 30, 16, 0, tzinfo=UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def route_summary(*, selected: str = "C0_FETCH") -> dict:
    c1 = selected == "C1_RENDER"
    return {
        "schema_version": 1,
        "policy": "public_read_auto_v1",
        "selected_capability": selected,
        "selected_engine": "c1-lightpanda" if c1 else "c0-fetch",
        "selected_browser_engine": "lightpanda" if c1 else None,
        "selected_transport": None if c1 else "system_curl",
        "render_trigger": "spa_shell_low_text" if c1 else None,
        "render_fallback_attempted": c1,
        "render_skipped_reason": None,
        "attempt_count": 2 if c1 else 1,
        "attempts": (
            [
                {
                    "capability": "C0_FETCH",
                    "state": "SUCCEEDED",
                    "http_status": 200,
                    "engine": "c0-fetch",
                    "browser_engine": None,
                    "transport": "system_curl",
                },
                {
                    "capability": "C1_RENDER",
                    "state": "SUCCEEDED",
                    "http_status": 200,
                    "engine": "c1-lightpanda",
                    "browser_engine": "lightpanda",
                    "transport": None,
                },
            ]
            if c1
            else [{
                "capability": "C0_FETCH",
                "state": "SUCCEEDED",
                "http_status": 200,
                "engine": "c0-fetch",
                "browser_engine": None,
                "transport": "system_curl",
            }]
        ),
        "c2_authorized": False,
        "c3_authorized": False,
    }


class PublicReadTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "signalforge.db"
        initialize_provider_queue(self.db)
        self.sequence = 0

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def insert(
        self,
        *,
        created_at: datetime,
        state: str = "SUCCEEDED",
        source_id: str = "S38",
        route: dict | None = None,
        failure_class: str | None = None,
        integrity: bool = True,
    ) -> str:
        self.sequence += 1
        request_id = f"req-{self.sequence:03d}"
        completed_at = created_at + timedelta(seconds=2) if state == "SUCCEEDED" else created_at + timedelta(seconds=1)
        with connect(self.db) as conn, conn:
            conn.execute(
                """
                INSERT INTO provider_requests(
                    provider_request_id,schema_version,provider_id,source_id,capability,target_role,
                    priority,request_sha256,request_json,state,created_at,requested_at,expires_at,
                    completed_at,result_sha256,browser_job_id,result_media_type,result_artifact_bytes,
                    result_final_url,result_http_status,result_request_sha256,result_route_json,failure_class
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    request_id,
                    1,
                    "mac-mm-01",
                    source_id,
                    "PUBLIC_READ_ACQUIRE",
                    "LISTING",
                    0,
                    "a" * 64,
                    "{}",
                    state,
                    iso(created_at),
                    iso(created_at),
                    iso(created_at + timedelta(minutes=5)),
                    iso(completed_at),
                    "b" * 64 if state == "SUCCEEDED" and integrity else None,
                    f"browser-{request_id}" if state == "SUCCEEDED" and integrity else None,
                    "text/html" if state == "SUCCEEDED" and integrity else None,
                    1000 + self.sequence if state == "SUCCEEDED" and integrity else None,
                    "https://example.invalid/listing" if state == "SUCCEEDED" else None,
                    200 if state == "SUCCEEDED" else None,
                    "a" * 64 if state == "SUCCEEDED" else None,
                    json.dumps(route, sort_keys=True, separators=(",", ":")) if route is not None else None,
                    failure_class,
                ),
            )
        return request_id

    def test_no_data_is_quiet_and_gate_no_data(self) -> None:
        report = public_read_telemetry_report(database=self.db, now=NOW)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["requests_total"], 0)
        self.assertEqual(report["verification_gate"]["status"], "NO_DATA")

        called = []
        result = public_read_telemetry_alert(
            database=self.db,
            now=NOW,
            sender=lambda **kwargs: called.append(kwargs) or "1",
        )
        self.assertEqual(result["status"], "QUIET")
        self.assertFalse(result["sent"])
        self.assertEqual(called, [])

    def test_c0_routes_are_aggregated_and_gate_observes_before_24h(self) -> None:
        for index in range(3):
            self.insert(
                created_at=NOW - timedelta(hours=2) + timedelta(minutes=index),
                source_id="S38" if index % 2 == 0 else "S27",
                route=route_summary(),
            )
        report = public_read_telemetry_report(database=self.db, now=NOW)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["requests_total"], 3)
        self.assertEqual(report["routes"]["selected_capabilities"], {"C0_FETCH": 3})
        self.assertEqual(report["routes"]["selected_transports"], {"system_curl": 3})
        self.assertEqual(report["latency_seconds"]["p50"], 2.0)
        self.assertEqual(report["verification_gate"]["status"], "OBSERVING")
        self.assertEqual(report["verification_gate"]["instrumented_successes"], 3)

    def test_gate_passes_after_24h_and_ten_instrumented_successes(self) -> None:
        start = NOW - timedelta(hours=25)
        for index in range(10):
            self.insert(
                created_at=start + timedelta(minutes=index),
                source_id="S38" if index < 5 else "S27",
                route=route_summary(),
            )
        report = public_read_telemetry_report(
            database=self.db,
            now=NOW,
            window_hours=48,
        )
        gate = report["verification_gate"]
        self.assertEqual(gate["status"], "PASS")
        self.assertGreaterEqual(gate["observed_hours"], 24)
        self.assertEqual(gate["instrumented_successes"], 10)
        self.assertEqual(gate["terminal_failures_in_window"], 0)

    def test_natural_c1_is_audited_but_not_an_alert(self) -> None:
        self.insert(created_at=NOW - timedelta(hours=1), route=route_summary())
        c1_id = self.insert(
            created_at=NOW - timedelta(minutes=30),
            source_id="S27",
            route=route_summary(selected="C1_RENDER"),
        )
        report = public_read_telemetry_report(database=self.db, now=NOW)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["routes"]["c1_count"], 1)
        first = report["routes"]["first_natural_c1"]
        self.assertEqual(first["provider_request_id"], c1_id)
        self.assertEqual(first["render_trigger"], "spa_shell_low_text")
        self.assertTrue(report["verification_gate"]["natural_c1_observed"])
        self.assertEqual(report["anomalies"], [])

    def test_terminal_failure_alerts_once_and_is_deduplicated(self) -> None:
        self.insert(created_at=NOW - timedelta(hours=2), route=route_summary())
        failed_id = self.insert(
            created_at=NOW - timedelta(minutes=10),
            state="FAILED",
            source_id="S27",
            failure_class="PROVIDER_EXECUTION_FAILED",
        )
        report = public_read_telemetry_report(database=self.db, now=NOW)
        self.assertEqual(report["status"], "DEGRADED")
        self.assertEqual(report["verification_gate"]["status"], "FAIL")
        self.assertEqual(report["anomalies"][0]["latest_provider_request_id"], failed_id)

        calls = []
        def sender(**kwargs):
            calls.append(kwargs)
            return "tg-123"

        first = public_read_telemetry_alert(
            database=self.db,
            now=NOW,
            bot_token="test-token",
            chat_id="test-chat",
            sender=sender,
        )
        second = public_read_telemetry_alert(
            database=self.db,
            now=NOW + timedelta(minutes=1),
            bot_token="test-token",
            chat_id="test-chat",
            sender=sender,
        )
        self.assertEqual(first["status"], "ALERT_SENT")
        self.assertEqual(second["status"], "DEDUPLICATED")
        self.assertEqual(len(calls), 1)
        self.assertIn("PUBLIC_READ_TERMINAL_FAILURE", calls[0]["text"])
        self.assertNotIn("https://", calls[0]["text"])

    def test_failure_older_than_window_does_not_permanently_lock_gate(self) -> None:
        start = NOW - timedelta(hours=30)
        self.insert(created_at=start, route=route_summary())
        self.insert(
            created_at=NOW - timedelta(hours=25),
            state="FAILED",
            source_id="S27",
            failure_class="TRANSIENT_PROVIDER_FAILURE",
        )
        for index in range(9):
            self.insert(
                created_at=NOW - timedelta(hours=23) + timedelta(hours=index * 2),
                route=route_summary(),
            )
        report = public_read_telemetry_report(database=self.db, now=NOW, window_hours=24)
        self.assertEqual(report["anomalies"], [])
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["verification_gate"]["status"], "PASS")
        self.assertEqual(report["verification_gate"]["terminal_failures_in_window"], 0)

    def test_missing_route_after_instrumentation_is_anomaly_but_legacy_before_is_not(self) -> None:
        self.insert(created_at=NOW - timedelta(hours=3), route=None)
        self.insert(created_at=NOW - timedelta(hours=2), route=route_summary())
        missing_id = self.insert(created_at=NOW - timedelta(hours=1), route=None)
        report = public_read_telemetry_report(database=self.db, now=NOW)
        codes = {item["code"] for item in report["anomalies"]}
        self.assertIn("ROUTE_SUMMARY_MISSING_AFTER_INSTRUMENTATION", codes)
        missing = next(item for item in report["anomalies"] if item["code"] == "ROUTE_SUMMARY_MISSING_AFTER_INSTRUMENTATION")
        self.assertEqual(missing["count"], 1)
        self.assertEqual(missing["latest_provider_request_id"], missing_id)
        self.assertEqual(report["routes"]["legacy_missing_route_in_window"], 2)


if __name__ == "__main__":
    unittest.main()
