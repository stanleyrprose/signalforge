from __future__ import annotations

import tempfile
import unittest
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from signalforge.provider_dispatcher import ProviderDispatcherError, dispatch
from signalforge.provider_invocation import CAPABILITY_TOOL_MAP, build_provider_request
from signalforge.provider_queue import enqueue_provider_request


NOW = datetime(2026, 9, 8, 5, 30, tzinfo=UTC)


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


def request() -> dict:
    return build_provider_request(
        contract=contract(),
        source_id="S38",
        source_policy_version=1,
        capability="C0_FETCH",
        target_role="LISTING",
        requested_url="https://www.industrymsme.gov.mm/announcements",
        signalforge_job_id=str(uuid.uuid4()),
        acquisition_request_id=str(uuid.uuid4()),
        acquisition_attempt_id=str(uuid.uuid4()),
        max_bytes=1_000_000,
        max_run_seconds=60,
        now=NOW,
        ttl_seconds=120,
    )


class ProviderDispatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "signalforge.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_dispatcher_rejects_unknown_or_argument_bearing_command(self) -> None:
        for command in ("bash", "provider-claim-v1 extra", " provider-claim-v1", "provider-claim-v1 "):
            with self.assertRaisesRegex(ProviderDispatcherError, "DENY"):
                dispatch(command, database=self.db, now=NOW)

    def test_claim_and_status_are_pinned_to_mac_provider(self) -> None:
        item = request()
        enqueue_provider_request(item, contract=contract(), database=self.db, now=NOW)
        claimed = dispatch("provider-claim-v1", database=self.db, now=NOW)
        self.assertEqual(claimed["provider_id"], "mac-mm-01")
        self.assertEqual(claimed["provider_request_id"], item["provider_request_id"])
        status = dispatch("provider-status-v1", database=self.db, now=NOW)
        self.assertEqual(status["provider_id"], "mac-mm-01")
        self.assertEqual(status["counts"]["CLAIMED"], 1)

    def test_claim_and_status_reject_payloads(self) -> None:
        with self.assertRaisesRegex(ProviderDispatcherError, "accepts no payload"):
            dispatch("provider-claim-v1", {}, database=self.db, now=NOW)
        with self.assertRaisesRegex(ProviderDispatcherError, "accepts no payload"):
            dispatch("provider-status-v1", {}, database=self.db, now=NOW)

    def test_complete_requires_exact_fields_and_accepts_current_claim(self) -> None:
        item = request()
        enqueue_provider_request(item, contract=contract(), database=self.db, now=NOW)
        claimed = dispatch("provider-claim-v1", database=self.db, now=NOW)
        base = {
            "provider_request_id": item["provider_request_id"],
            "provider_attempt_id": claimed["provider_attempt_id"],
            "claim_token": claimed["claim_token"],
            "result_sha256": "a" * 64,
            "browser_job_id": "browser-job-1",
        }
        with self.assertRaisesRegex(ProviderDispatcherError, "fields"):
            dispatch("provider-complete-v1", {**base, "provider_id": "evil"}, database=self.db, now=NOW + timedelta(seconds=1))
        result = dispatch("provider-complete-v1", base, database=self.db, now=NOW + timedelta(seconds=1))
        self.assertEqual(result["status"], "ACCEPTED")

    def test_fail_requires_exact_fields(self) -> None:
        item = request()
        enqueue_provider_request(item, contract=contract(), database=self.db, now=NOW)
        claimed = dispatch("provider-claim-v1", database=self.db, now=NOW)
        payload = {
            "provider_request_id": item["provider_request_id"],
            "provider_attempt_id": claimed["provider_attempt_id"],
            "claim_token": claimed["claim_token"],
            "failure_class": "PROVIDER_NOT_READY",
        }
        result = dispatch("provider-fail-v1", payload, database=self.db, now=NOW + timedelta(seconds=1))
        self.assertEqual(result["state"], "FAILED")

    def test_no_command_accepts_provider_id_from_client(self) -> None:
        item = request()
        enqueue_provider_request(item, contract=contract(), database=self.db, now=NOW)
        claimed = dispatch("provider-claim-v1", database=self.db, now=NOW)
        payload = {
            "provider_request_id": item["provider_request_id"],
            "provider_attempt_id": claimed["provider_attempt_id"],
            "claim_token": claimed["claim_token"],
            "result_sha256": "b" * 64,
            "browser_job_id": "browser-job-2",
            "provider_id": "other-provider",
        }
        with self.assertRaisesRegex(ProviderDispatcherError, "fields"):
            dispatch("provider-complete-v1", payload, database=self.db, now=NOW + timedelta(seconds=1))


if __name__ == "__main__":
    unittest.main()
