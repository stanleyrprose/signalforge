from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from signalforge.provider_invocation import CAPABILITY_TOOL_MAP, build_provider_request
from signalforge.provider_queue import claim_next_provider_request, enqueue_provider_request
from signalforge.provider_result import ProviderResultError, accept_result_stream, parse_result_stream

NOW = datetime(2026, 9, 8, 6, 0, tzinfo=UTC)

def contract() -> dict:
    return {
        "schema_version": 1, "contract_name": "provider-invocation-v1", "provider_id": "mac-mm-01", "transport": "pull_ssh_v1", "enabled": False,
        "allowed_capabilities": list(CAPABILITY_TOOL_MAP), "tool_map": dict(CAPABILITY_TOOL_MAP),
        "limits": {"max_run_seconds": 180, "max_request_ttl_seconds": 180, "max_bytes": 16 * 1024 * 1024},
        "security": {"https_only": True,"arbitrary_url_allowed": False,"arbitrary_shell_allowed": False,"public_mac_listener_allowed": False,"off_host_redirect_allowed": False,"personal_chrome_profile_allowed": False},
        "source_policies": {"S38": {"enabled": True,"source_policy_version": 1,"allowed_capabilities": list(CAPABILITY_TOOL_MAP),"targets": {"LISTING": {"capabilities": list(CAPABILITY_TOOL_MAP),"exact_urls": ["https://www.industrymsme.gov.mm/announcements"],"max_bytes": 1000000,"max_run_seconds": 60}}}},
    }

def request(*, max_bytes: int = 1000000, capability: str = "C0_FETCH") -> dict:
    return build_provider_request(contract=contract(), source_id="S38", source_policy_version=1, capability=capability, target_role="LISTING", requested_url="https://www.industrymsme.gov.mm/announcements", signalforge_job_id=str(uuid.uuid4()), acquisition_request_id=str(uuid.uuid4()), acquisition_attempt_id=str(uuid.uuid4()), max_bytes=max_bytes, max_run_seconds=60, now=NOW, ttl_seconds=120)


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

def framed(req: dict, claim: dict, artifact: bytes = b"<html>ok</html>", **changes) -> bytes:
    manifest = {
        "contract_version": 1,
        "provider_request_id": req["provider_request_id"],
        "provider_attempt_id": claim["provider_attempt_id"],
        "claim_token": claim["claim_token"],
        "browser_job_id": "browser-job-1",
        "request_sha256": req["request_sha256"],
        "state": "SUCCEEDED",
        "mcp_tool": req["mcp_tool"],
        "final_url": req["requested_url"],
        "http_status": 200,
        "media_type": "text/html",
        "artifact_bytes": len(artifact),
        "artifact_sha256": hashlib.sha256(artifact).hexdigest(),
    }
    manifest.update(changes)
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode() + b"\n" + artifact

class ProviderResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db = root / "signalforge.db"
        self.evidence = root / "evidence"
        self.req = request()
        enqueue_provider_request(self.req, contract=contract(), database=self.db, now=NOW)
        self.claim = claim_next_provider_request(provider_id="mac-mm-01", database=self.db, now=NOW, lease_seconds=60)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_accepts_exact_manifest_plus_raw_artifact_and_persists_private_evidence(self) -> None:
        result = accept_result_stream(io.BytesIO(framed(self.req, self.claim)), database=self.db, evidence_directory=self.evidence, now=NOW + timedelta(seconds=1))
        self.assertEqual(result["status"], "ACCEPTED")
        artifact = Path(result["artifact_path"])
        self.assertEqual(artifact.read_bytes(), b"<html>ok</html>")
        self.assertEqual(artifact.stat().st_mode & 0o777, 0o640)
        self.assertEqual(artifact.parent.stat().st_mode & 0o777, 0o700)
        with sqlite3.connect(self.db) as conn:
            row = conn.execute("SELECT state,result_artifact_bytes,result_media_type,result_final_url,result_request_sha256 FROM provider_requests WHERE provider_request_id=?", (self.req["provider_request_id"],)).fetchone()
        self.assertEqual(row, ("SUCCEEDED", 15, "text/html", self.req["requested_url"], self.req["request_sha256"]))

    def test_identical_resubmit_is_idempotent(self) -> None:
        payload = framed(self.req, self.claim)
        first = accept_result_stream(io.BytesIO(payload), database=self.db, evidence_directory=self.evidence, now=NOW + timedelta(seconds=1))
        second = accept_result_stream(io.BytesIO(payload), database=self.db, evidence_directory=self.evidence, now=NOW + timedelta(seconds=2))
        self.assertEqual(first["status"], "ACCEPTED")
        self.assertEqual(second["status"], "ALREADY_ACCEPTED")

    def test_rejects_hash_mismatch_truncation_and_trailing_bytes(self) -> None:
        good = framed(self.req, self.claim)
        line, artifact = good.split(b"\n", 1)
        manifest = json.loads(line)
        manifest["artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(ProviderResultError, "SHA-256"):
            parse_result_stream(io.BytesIO(json.dumps(manifest).encode()+b"\n"+artifact))
        with self.assertRaisesRegex(ProviderResultError, "truncated"):
            parse_result_stream(io.BytesIO(line+b"\n"+artifact[:-1]))
        with self.assertRaisesRegex(ProviderResultError, "trailing"):
            parse_result_stream(io.BytesIO(good+b"x"))

    def test_rejects_wrong_claim_request_hash_tool_or_final_url(self) -> None:
        cases = [
            {"claim_token": "wrong"},
            {"request_sha256": "f" * 64},
            {"mcp_tool": "browser_render"},
            {"final_url": "https://example.com/"},
        ]
        for change in cases:
            with self.assertRaises(ProviderResultError, msg=str(change)):
                accept_result_stream(io.BytesIO(framed(self.req, self.claim, **change)), database=self.db, evidence_directory=self.evidence, now=NOW + timedelta(seconds=1))

    def test_rejects_extra_manifest_fields(self) -> None:
        raw = framed(self.req, self.claim)
        line, artifact = raw.split(b"\n", 1)
        manifest = json.loads(line); manifest["provider_id"] = "client-controlled"
        with self.assertRaisesRegex(ProviderResultError, "fields"):
            parse_result_stream(io.BytesIO(json.dumps(manifest).encode()+b"\n"+artifact))

    def test_public_read_route_summary_is_optional_for_rollout_and_persisted_when_present(self) -> None:
        legacy_db = Path(self.tmp.name) / "public-read-legacy.db"
        legacy_req = request(capability="PUBLIC_READ_ACQUIRE")
        enqueue_provider_request(legacy_req, contract=contract(), database=legacy_db, now=NOW)
        legacy_claim = claim_next_provider_request(provider_id="mac-mm-01", database=legacy_db, now=NOW, lease_seconds=60)
        legacy = accept_result_stream(
            io.BytesIO(framed(legacy_req, legacy_claim)),
            database=legacy_db,
            evidence_directory=self.evidence / "legacy",
            now=NOW + timedelta(seconds=1),
        )
        self.assertIsNone(legacy["route_summary"])
        with sqlite3.connect(legacy_db) as conn:
            self.assertIsNone(conn.execute(
                "SELECT result_route_json FROM provider_requests WHERE provider_request_id=?",
                (legacy_req["provider_request_id"],),
            ).fetchone()[0])

        instrumented_db = Path(self.tmp.name) / "public-read-instrumented.db"
        instrumented_req = request(capability="PUBLIC_READ_ACQUIRE")
        enqueue_provider_request(instrumented_req, contract=contract(), database=instrumented_db, now=NOW)
        instrumented_claim = claim_next_provider_request(provider_id="mac-mm-01", database=instrumented_db, now=NOW, lease_seconds=60)
        summary = route_summary()
        accepted = accept_result_stream(
            io.BytesIO(framed(instrumented_req, instrumented_claim, route_summary=summary)),
            database=instrumented_db,
            evidence_directory=self.evidence / "instrumented",
            now=NOW + timedelta(seconds=1),
        )
        self.assertEqual(accepted["route_summary"], summary)
        with sqlite3.connect(instrumented_db) as conn:
            stored = conn.execute(
                "SELECT result_route_json FROM provider_requests WHERE provider_request_id=?",
                (instrumented_req["provider_request_id"],),
            ).fetchone()[0]
        self.assertEqual(json.loads(stored), summary)

    def test_route_summary_rejected_for_non_public_read_or_malformed_boundary(self) -> None:
        with self.assertRaisesRegex(ProviderResultError, "only valid for browser_acquire"):
            parse_result_stream(io.BytesIO(framed(self.req, self.claim, route_summary=route_summary())))

        public_db = Path(self.tmp.name) / "public-read-invalid.db"
        public_req = request(capability="PUBLIC_READ_ACQUIRE")
        enqueue_provider_request(public_req, contract=contract(), database=public_db, now=NOW)
        public_claim = claim_next_provider_request(provider_id="mac-mm-01", database=public_db, now=NOW, lease_seconds=60)
        invalid = route_summary()
        invalid["c2_authorized"] = True
        with self.assertRaisesRegex(ProviderResultError, "authorization boundary"):
            parse_result_stream(io.BytesIO(framed(public_req, public_claim, route_summary=invalid)))

    def test_route_summary_rejects_unknown_fields(self) -> None:
        public_db = Path(self.tmp.name) / "public-read-extra.db"
        public_req = request(capability="PUBLIC_READ_ACQUIRE")
        enqueue_provider_request(public_req, contract=contract(), database=public_db, now=NOW)
        public_claim = claim_next_provider_request(provider_id="mac-mm-01", database=public_db, now=NOW, lease_seconds=60)
        summary = route_summary()
        summary["url"] = "https://should-not-appear.example"
        with self.assertRaisesRegex(ProviderResultError, "fields"):
            parse_result_stream(io.BytesIO(framed(public_req, public_claim, route_summary=summary)))

    def test_rejects_artifact_larger_than_original_request_budget(self) -> None:
        small_db = Path(self.tmp.name) / "small-budget.db"
        small_req = request(max_bytes=8)
        enqueue_provider_request(small_req, contract=contract(), database=small_db, now=NOW)
        small_claim = claim_next_provider_request(provider_id="mac-mm-01", database=small_db, now=NOW, lease_seconds=60)
        with self.assertRaisesRegex(ProviderResultError, "request max_bytes"):
            accept_result_stream(
                io.BytesIO(framed(small_req, small_claim, artifact=b"123456789")),
                database=small_db,
                evidence_directory=self.evidence,
                now=NOW + timedelta(seconds=1),
            )

if __name__ == "__main__":
    unittest.main()
