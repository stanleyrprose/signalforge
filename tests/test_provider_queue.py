from __future__ import annotations

import sqlite3
import tempfile
import unittest
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from signalforge.provider_invocation import CAPABILITY_TOOL_MAP, build_provider_request
from signalforge.provider_queue import (
    ProviderQueueError,
    claim_next_provider_request,
    complete_provider_claim,
    enqueue_provider_request,
    fail_provider_claim,
    initialize_provider_queue,
    provider_queue_status,
)


NOW = datetime(2026, 9, 8, 5, 0, tzinfo=UTC)


def contract() -> dict:
    return {
        "schema_version": 1,
        "contract_name": "provider-invocation-v1",
        "provider_id": "mac-mm-01",
        "transport": "pull_ssh_v1",
        "enabled": False,
        "allowed_capabilities": list(CAPABILITY_TOOL_MAP),
        "tool_map": dict(CAPABILITY_TOOL_MAP),
        "limits": {"max_run_seconds": 180, "max_request_ttl_seconds": 180, "max_bytes": 16 * 1024 * 1024},
        "security": {
            "https_only": True,
            "arbitrary_url_allowed": False,
            "arbitrary_shell_allowed": False,
            "public_mac_listener_allowed": False,
            "off_host_redirect_allowed": False,
            "personal_chrome_profile_allowed": False,
        },
        "source_policies": {
            "S38": {
                "enabled": True,
                "source_policy_version": 1,
                "allowed_capabilities": list(CAPABILITY_TOOL_MAP),
                "targets": {
                    "LISTING": {
                        "capabilities": list(CAPABILITY_TOOL_MAP),
                        "exact_urls": ["https://www.industrymsme.gov.mm/announcements"],
                        "max_bytes": 1_000_000,
                        "max_run_seconds": 60,
                    }
                },
            }
        },
    }


def new_request(*, now: datetime = NOW, ttl: int = 90, capability: str = "C0_FETCH") -> dict:
    interaction = None
    if capability == "C3_BROWSER_USE":
        interaction = {
            "side_effect_class": "READ_ONLY_NAVIGATION",
            "retry_safe": False,
            "steps": [{"action": "snapshot"}, {"action": "screenshot"}],
        }
    return build_provider_request(
        contract=contract(),
        source_id="S38",
        source_policy_version=1,
        capability=capability,
        target_role="LISTING",
        requested_url="https://www.industrymsme.gov.mm/announcements",
        signalforge_job_id=str(uuid.uuid4()),
        acquisition_request_id=str(uuid.uuid4()),
        acquisition_attempt_id=str(uuid.uuid4()),
        max_bytes=1_000_000,
        max_run_seconds=60,
        interaction_plan=interaction,
        now=now,
        ttl_seconds=ttl,
    )


class ProviderQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "signalforge.db"
        initialize_provider_queue(self.db)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_enqueue_is_idempotent_and_conflict_fails_closed(self) -> None:
        request = new_request()
        first = enqueue_provider_request(request, contract=contract(), database=self.db, now=NOW)
        second = enqueue_provider_request(request, contract=contract(), database=self.db, now=NOW)
        self.assertEqual(first["status"], "ENQUEUED")
        self.assertEqual(second["status"], "ALREADY_ENQUEUED")
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM provider_requests").fetchone()[0], 1)
            conn.execute("UPDATE provider_requests SET request_sha256='0' WHERE provider_request_id=?", (request["provider_request_id"],))
            conn.commit()
        with self.assertRaisesRegex(ProviderQueueError, "idempotency conflict"):
            enqueue_provider_request(request, contract=contract(), database=self.db, now=NOW)

    def test_claim_prefers_higher_priority_and_only_one_active_claim(self) -> None:
        low = new_request()
        high = new_request()
        enqueue_provider_request(low, contract=contract(), database=self.db, priority=1, now=NOW)
        enqueue_provider_request(high, contract=contract(), database=self.db, priority=10, now=NOW)
        claimed = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW, lease_seconds=60)
        self.assertEqual(claimed["provider_request_id"], high["provider_request_id"])
        second = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW, lease_seconds=60)
        self.assertEqual(second["provider_request_id"], low["provider_request_id"])
        third = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW, lease_seconds=60)
        self.assertEqual(third["status"], "NO_WORK")

    def test_claim_token_is_only_stored_hashed(self) -> None:
        request = new_request()
        enqueue_provider_request(request, contract=contract(), database=self.db, now=NOW)
        claimed = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW)
        with sqlite3.connect(self.db) as conn:
            stored = conn.execute("SELECT claim_token_sha256 FROM provider_requests WHERE provider_request_id=?", (request["provider_request_id"],)).fetchone()[0]
        self.assertNotEqual(stored, claimed["claim_token"])
        self.assertEqual(len(stored), 64)

    def test_expired_lease_requeues_readonly_request_and_closes_old_attempt(self) -> None:
        request = new_request(ttl=180)
        enqueue_provider_request(request, contract=contract(), database=self.db, now=NOW)
        first = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW, lease_seconds=30)
        second = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW + timedelta(seconds=31), lease_seconds=30)
        self.assertEqual(second["provider_request_id"], request["provider_request_id"])
        self.assertNotEqual(first["provider_attempt_id"], second["provider_attempt_id"])
        with sqlite3.connect(self.db) as conn:
            state = conn.execute("SELECT state FROM provider_attempts WHERE provider_attempt_id=?", (first["provider_attempt_id"],)).fetchone()[0]
        self.assertEqual(state, "LEASE_EXPIRED")

    def test_request_expiry_removes_work_from_claim_queue(self) -> None:
        request = new_request(ttl=30)
        enqueue_provider_request(request, contract=contract(), database=self.db, now=NOW)
        result = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW + timedelta(seconds=31))
        self.assertEqual(result["status"], "NO_WORK")
        status = provider_queue_status(provider_id="mac-mm-01", database=self.db, now=NOW + timedelta(seconds=31))
        self.assertEqual(status["counts"]["EXPIRED"], 1)

    def test_complete_is_exactly_once_at_commit_boundary(self) -> None:
        request = new_request()
        enqueue_provider_request(request, contract=contract(), database=self.db, now=NOW)
        claimed = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW)
        digest = "a" * 64
        accepted = complete_provider_claim(
            provider_request_id=request["provider_request_id"],
            provider_attempt_id=claimed["provider_attempt_id"],
            claim_token=claimed["claim_token"],
            result_sha256=digest,
            browser_job_id="browser-job-1",
            database=self.db,
            now=NOW + timedelta(seconds=2),
        )
        repeated = complete_provider_claim(
            provider_request_id=request["provider_request_id"],
            provider_attempt_id=claimed["provider_attempt_id"],
            claim_token=claimed["claim_token"],
            result_sha256=digest,
            browser_job_id="browser-job-1",
            database=self.db,
            now=NOW + timedelta(seconds=3),
        )
        self.assertEqual(accepted["status"], "ACCEPTED")
        self.assertEqual(repeated["status"], "ALREADY_ACCEPTED")
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM provider_attempts").fetchone()[0], 1)

    def test_complete_rejects_wrong_token_and_conflicting_repeat(self) -> None:
        request = new_request()
        enqueue_provider_request(request, contract=contract(), database=self.db, now=NOW)
        claimed = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW)
        with self.assertRaisesRegex(ProviderQueueError, "token mismatch"):
            complete_provider_claim(
                provider_request_id=request["provider_request_id"],
                provider_attempt_id=claimed["provider_attempt_id"],
                claim_token="wrong",
                result_sha256="b" * 64,
                browser_job_id="browser-job-1",
                database=self.db,
                now=NOW + timedelta(seconds=1),
            )
        complete_provider_claim(
            provider_request_id=request["provider_request_id"],
            provider_attempt_id=claimed["provider_attempt_id"],
            claim_token=claimed["claim_token"],
            result_sha256="b" * 64,
            browser_job_id="browser-job-1",
            database=self.db,
            now=NOW + timedelta(seconds=2),
        )
        with self.assertRaisesRegex(ProviderQueueError, "idempotency conflict"):
            complete_provider_claim(
                provider_request_id=request["provider_request_id"],
                provider_attempt_id=claimed["provider_attempt_id"],
                claim_token=claimed["claim_token"],
                result_sha256="c" * 64,
                browser_job_id="browser-job-2",
                database=self.db,
                now=NOW + timedelta(seconds=3),
            )

    def test_fail_claim_records_provider_failure(self) -> None:
        request = new_request()
        enqueue_provider_request(request, contract=contract(), database=self.db, now=NOW)
        claimed = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW)
        result = fail_provider_claim(
            provider_request_id=request["provider_request_id"],
            provider_attempt_id=claimed["provider_attempt_id"],
            claim_token=claimed["claim_token"],
            failure_class="PROVIDER_NOT_READY",
            database=self.db,
            now=NOW + timedelta(seconds=1),
        )
        self.assertEqual(result["state"], "FAILED")
        status = provider_queue_status(provider_id="mac-mm-01", database=self.db, now=NOW + timedelta(seconds=2))
        self.assertEqual(status["counts"]["FAILED"], 1)

    def test_queue_accepts_c3_requests_without_treating_them_as_worker_runs(self) -> None:
        request = new_request(capability="C3_BROWSER_USE")
        enqueue_provider_request(request, contract=contract(), database=self.db, now=NOW)
        claimed = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW)
        self.assertEqual(claimed["request"]["capability"], "C3_BROWSER_USE")
        with sqlite3.connect(self.db) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("provider_requests", tables)
        self.assertIn("provider_attempts", tables)
        self.assertNotIn("runs", tables)


if __name__ == "__main__":
    unittest.main()
