from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from signalforge.provider_queue import claim_next_provider_request, complete_provider_claim
from signalforge.config import Registry
from signalforge.provider_r3 import ProviderR3Error, R3_CAPABILITIES, R3_URL, load_r3_contract, prepare_r3_gate, r3_gate_status


NOW = datetime(2026, 9, 8, 9, 30, tzinfo=UTC)


class ProviderR3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "signalforge.db"
        self.contract_path = Path(__file__).resolve().parents[1] / "registry" / "Provider-Invocation-Contract-v1-r3-evidence-only.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _pre_r4_registry(self) -> Registry:
        return Registry(raw={
            "production_policy": {"browser_production_approved": False},
            "providers": {"mac-mm-01": {"production_enabled": False, "capabilities": {"remote_invocation": False}}},
            "sources": {},
        })

    def test_contract_is_isolated_and_production_disabled(self) -> None:
        contract = load_r3_contract(self.contract_path)
        self.assertIs(contract["enabled"], False)
        self.assertEqual(contract["verification_mode"], "EVIDENCE_ONLY")
        self.assertEqual(set(contract["source_policies"]), {"S38"})

    def test_r4_production_state_blocks_r3_rerun(self) -> None:
        with self.assertRaisesRegex(ProviderR3Error, "historical after R4"):
            prepare_r3_gate(database=self.db, contract_path=self.contract_path, now=NOW)

    def test_release_deploy_makes_provider_dispatcher_executable(self) -> None:
        deploy = (Path(__file__).resolve().parents[1] / "deploy" / "deploy-signalforge-release.sh").read_text(encoding="utf-8")
        self.assertIn('chmod 0755 "$STAGE/bin/signalforge" "$STAGE/bin/signalforge-provider-dispatcher"', deploy)

    def test_prepare_enqueues_exactly_c0_c1_c2_c3_without_business_side_effects(self) -> None:
        with patch("signalforge.provider_r3.Registry.load", return_value=self._pre_r4_registry()):
            prepared = prepare_r3_gate(database=self.db, contract_path=self.contract_path, now=NOW)
        self.assertEqual(prepared["status"], "R3_EVIDENCE_ONLY_PREPARED")
        self.assertIs(prepared["provider_contract_enabled"], False)
        self.assertIs(prepared["customer_signal_path_enabled"], False)
        self.assertEqual({item["capability"] for item in prepared["requests"]}, set(R3_CAPABILITIES))
        status = r3_gate_status(prepared["gate_id"], database=self.db)
        self.assertEqual(status["status"], "WAITING")
        self.assertEqual(status["business_side_effect_counts"], {"scheduler_runs": 0, "canonical_items": 0, "signals": 0})
        self.assertTrue(all(item["state"] == "PENDING" for item in status["capabilities"].values()))

    def test_status_pass_requires_four_verified_durable_results(self) -> None:
        with patch("signalforge.provider_r3.Registry.load", return_value=self._pre_r4_registry()):
            prepared = prepare_r3_gate(database=self.db, contract_path=self.contract_path, now=NOW)
        gate_id = prepared["gate_id"]
        engine_map = {
            "C1_RENDER": "c1-playwright",
            "C2_INSPECT": "c2-readonly-inspect",
            "C3_BROWSER_USE": "c3-browser-use",
        }
        for index, _expected_capability in enumerate(R3_CAPABILITIES, start=1):
            claimed = claim_next_provider_request(
                provider_id="mac-mm-01",
                database=self.db,
                now=NOW + timedelta(seconds=index),
                lease_seconds=60,
            )
            request = claimed["request"]
            capability = request["capability"]
            self.assertEqual(request["signalforge_job_id"], gate_id)
            self.assertEqual(request["requested_url"], R3_URL)
            artifact_path = self.root / f"evidence-{capability}.bin"
            if capability == "C0_FETCH":
                artifact = b"<html><body>industry</body></html>"
                media_type = "text/html"
            else:
                artifact = json.dumps(
                    {
                        "job_id": f"browser-job-{index}",
                        "state": "SUCCEEDED",
                        "result": {"engine": engine_map[capability], "url": R3_URL, "status": 200},
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                media_type = "application/json"
            artifact_path.write_bytes(artifact)
            digest = hashlib.sha256(artifact).hexdigest()
            complete_provider_claim(
                provider_request_id=claimed["provider_request_id"],
                provider_attempt_id=claimed["provider_attempt_id"],
                claim_token=claimed["claim_token"],
                result_sha256=digest,
                browser_job_id=f"browser-job-{index}",
                database=self.db,
                result_media_type=media_type,
                result_artifact_bytes=len(artifact),
                result_artifact_path=str(artifact_path),
                result_final_url=R3_URL,
                result_http_status=200,
                result_request_sha256=request["request_sha256"],
                now=NOW + timedelta(seconds=index + 1),
            )

        status = r3_gate_status(gate_id, database=self.db)
        self.assertEqual(status["status"], "PASS")
        self.assertEqual(set(status["capabilities"]), set(R3_CAPABILITIES))
        self.assertTrue(all(item["verified"] for item in status["capabilities"].values()))
        self.assertEqual(status["business_side_effect_counts"], {"scheduler_runs": 0, "canonical_items": 0, "signals": 0})


if __name__ == "__main__":
    unittest.main()
