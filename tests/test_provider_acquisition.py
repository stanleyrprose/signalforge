from __future__ import annotations

import hashlib
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from signalforge.acquisition_runtime import acquire_provider_bytes
from signalforge.db import connect, migrate
from signalforge.provider_queue import claim_next_provider_request, complete_provider_claim

NOW = datetime(2026, 9, 8, 11, 45, tzinfo=UTC)
URL = "https://www.industrymsme.gov.mm/announcements"


class ProviderAcquisitionTests(unittest.TestCase):
    def test_provider_result_enters_standard_acquisition_evidence_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                conn.execute(
                    """INSERT INTO scheduler_runs(app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,status,baseline,recovery) VALUES (?,?,?,?,?,?,?,?,?)""",
                    ("11111111-1111-4111-8111-111111111111", "manual:S38:test", "MANUAL", "S38", "worker-test", NOW.isoformat().replace("+00:00", "Z"), "RUNNING", 1, 0),
                )
            artifact = b"<html><body>provider production</body></html>"
            artifact_path = root / "provider.html"
            artifact_path.write_bytes(artifact)
            serviced = False

            def service_once(_seconds: float) -> None:
                nonlocal serviced
                if serviced:
                    return
                serviced = True
                claimed = claim_next_provider_request(
                    provider_id="mac-mm-01",
                    database=database,
                    now=NOW + timedelta(seconds=1),
                    lease_seconds=60,
                )
                request = claimed["request"]
                digest = hashlib.sha256(artifact).hexdigest()
                complete_provider_claim(
                    provider_request_id=claimed["provider_request_id"],
                    provider_attempt_id=claimed["provider_attempt_id"],
                    claim_token=claimed["claim_token"],
                    result_sha256=digest,
                    browser_job_id="browser-job-production-test",
                    database=database,
                    result_media_type="text/html",
                    result_artifact_bytes=len(artifact),
                    result_artifact_path=str(artifact_path),
                    result_final_url=URL,
                    result_http_status=200,
                    result_request_sha256=request["request_sha256"],
                    now=NOW + timedelta(seconds=2),
                )

            capture = acquire_provider_bytes(
                database=database,
                scheduler_run_id="11111111-1111-4111-8111-111111111111",
                source_id="S38",
                source_policy_version=1,
                reason="MANUAL",
                egress_profile="mac-direct",
                target_kind="DISCOVERY",
                target_role="LISTING",
                url=URL,
                timeout_seconds=30,
                max_bytes=1_000_000,
                expected_content_types=["text/html"],
                observed_at=NOW.isoformat().replace("+00:00", "Z"),
                poll_interval_seconds=0.05,
                sleeper=service_once,
            )
            self.assertEqual(capture.payload, artifact)
            with connect(database) as conn:
                request = conn.execute("SELECT * FROM acquisition_requests WHERE request_id=?", (capture.request_id,)).fetchone()
                attempt = conn.execute("SELECT * FROM acquisition_attempts WHERE attempt_id=?", (capture.attempt_id,)).fetchone()
                evidence = conn.execute("SELECT * FROM evidence_envelopes WHERE evidence_id=?", (capture.evidence_id,)).fetchone()
            self.assertEqual(request["primary_method"], "MAC_BROWSER_PROVIDER")
            self.assertEqual(attempt["method"], "MAC_BROWSER_PROVIDER")
            self.assertEqual(attempt["status"], "SUCCESS")
            self.assertEqual(evidence["execution_scope"], "REMOTE_MAC_PROVIDER")
            self.assertEqual(evidence["provider_id"], "mac-mm-01")
            self.assertEqual(evidence["egress_profile"], "mac-direct")
            self.assertEqual(evidence["fetch_method"], "PROVIDER_C0_FETCH")
            self.assertEqual(evidence["final_url"], URL)
            self.assertEqual(evidence["artifact_sha256"], hashlib.sha256(artifact).hexdigest())


if __name__ == "__main__":
    unittest.main()
