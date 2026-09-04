from __future__ import annotations

import hashlib
import json
import stat
import tempfile
import unittest
from pathlib import Path

from signalforge.cli import verb_manifest
from signalforge.config import Registry
from signalforge.db import connect
from signalforge.provider_bridge import (
    ProviderBridgeError,
    build_provider_request,
    import_provider_result,
    write_provider_request,
)


ROOT = Path(__file__).resolve().parents[1]


class ProviderBridgeTests(unittest.TestCase):
    def test_provider_request_is_browserctl_compatible_and_private(self) -> None:
        registry = Registry.load(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "request.json"
            summary = write_provider_request("S15A", output, registry=registry)
            request = json.loads(output.read_text(encoding="utf-8"))
            metadata = request["_provider_request"]

            self.assertEqual(summary["status"], "PROVIDER_REQUEST_CREATED")
            self.assertEqual(request["task_type"], "fetch")
            self.assertEqual(request["egress"], "direct")
            self.assertEqual(request["url"], "https://www.mpa.gov.mm/tenders-and-announcement/")
            self.assertEqual(metadata["provider_id"], "mac-mm-01")
            self.assertEqual(metadata["source_id"], "S15A")
            self.assertEqual(request["idempotency_key"], f"sf-provider:{metadata['provider_request_id']}")
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)

    def test_unapproved_source_cannot_create_manual_provider_request(self) -> None:
        with self.assertRaisesRegex(ProviderBridgeError, "not approved"):
            build_provider_request("S27", registry=Registry.load(ROOT))

    def test_import_records_full_correlation_and_is_idempotent(self) -> None:
        registry = Registry.load(ROOT)
        payload = b"<html><body>MPA tender evidence</body></html>"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = build_provider_request(
                "S15A",
                registry=registry,
                requested_at="2026-09-04T16:30:00Z",
            )
            request_path = root / "request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            artifact_path = root / "response.html"
            artifact_path.write_bytes(payload)
            browser_result = {
                "job_id": "browser-job-1",
                "state": "SUCCEEDED",
                "created_at": "2026-09-04T16:30:01Z",
                "started_at": "2026-09-04T16:30:02Z",
                "finished_at": "2026-09-04T16:30:03Z",
                "failure_class": None,
                "partial_effect_possible": False,
                "result": {
                    "engine": "c0-fetch",
                    "url": "https://www.mpa.gov.mm/tenders-and-announcement/",
                    "status": 200,
                    "elapsed_ms": 50,
                    "content_type": "text/html; charset=UTF-8",
                    "body_bytes": len(payload),
                    "artifact_path": str(artifact_path),
                    "sha256": digest,
                },
            }
            result_path = root / "browser-result.json"
            result_path.write_text(json.dumps(browser_result), encoding="utf-8")
            database = root / "state" / "signalforge.db"
            evidence = root / "evidence"

            imported = import_provider_result(
                request_path=request_path,
                result_path=result_path,
                database=database,
                evidence_directory=evidence,
                registry=registry,
            )
            self.assertEqual(imported["status"], "IMPORTED_EVIDENCE_ONLY")
            self.assertEqual(imported["provider_id"], "mac-mm-01")
            self.assertEqual(imported["browser_job_id"], "browser-job-1")
            self.assertEqual(imported["sha256"], digest)
            self.assertEqual(imported["artifact_bytes"], len(payload))

            metadata = request["_provider_request"]
            with connect(database) as conn:
                scheduler = conn.execute(
                    "SELECT app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,status FROM scheduler_runs"
                ).fetchone()
                self.assertEqual(scheduler["app_run_id"], metadata["signalforge_job_id"])
                self.assertEqual(scheduler["trigger_id"], metadata["provider_request_id"])
                self.assertEqual(scheduler["trigger_kind"], "MANUAL_PROVIDER")
                self.assertEqual(scheduler["source_id"], "S15A")
                self.assertEqual(scheduler["worker_run_id"], "browser-job-1")
                self.assertEqual(scheduler["status"], "SUCCESS")

                acquisition = conn.execute(
                    "SELECT request_id,scheduler_run_id,app_job_ref,mode,primary_method,egress_profile FROM acquisition_requests"
                ).fetchone()
                self.assertEqual(acquisition["request_id"], metadata["acquisition_request_id"])
                self.assertEqual(acquisition["scheduler_run_id"], metadata["signalforge_job_id"])
                self.assertEqual(acquisition["app_job_ref"], metadata["provider_request_id"])
                self.assertEqual(acquisition["mode"], "manual_provider_bridge")
                self.assertEqual(acquisition["primary_method"], "PROVIDER_C0")
                self.assertEqual(acquisition["egress_profile"], "mac-direct")

                attempt = conn.execute(
                    "SELECT attempt_id,request_id,method,status FROM acquisition_attempts"
                ).fetchone()
                self.assertEqual(attempt["attempt_id"], metadata["acquisition_attempt_id"])
                self.assertEqual(attempt["request_id"], metadata["acquisition_request_id"])
                self.assertEqual(attempt["method"], "PROVIDER_C0")
                self.assertEqual(attempt["status"], "SUCCESS")

                envelope = conn.execute(
                    "SELECT provider_id,execution_scope,fetch_method,artifact_sha256,artifact_bytes,http_status FROM evidence_envelopes"
                ).fetchone()
                self.assertEqual(envelope["provider_id"], "mac-mm-01")
                self.assertEqual(envelope["execution_scope"], "MAC_LOCAL_MANUAL_BRIDGE")
                self.assertEqual(envelope["fetch_method"], "C0_FETCH")
                self.assertEqual(envelope["artifact_sha256"], digest)
                self.assertEqual(envelope["artifact_bytes"], len(payload))
                self.assertEqual(envelope["http_status"], 200)

                processing = conn.execute(
                    "SELECT status,parser_version,normalizer_version,canonicalizer_version,items_found,canonical_items,signals_created FROM processing_records"
                ).fetchone()
                self.assertEqual(processing["status"], "EVIDENCE_ONLY")
                self.assertEqual(processing["parser_version"], "none")
                self.assertEqual(processing["normalizer_version"], "none")
                self.assertEqual(processing["canonicalizer_version"], "none")
                self.assertEqual(processing["items_found"], 0)
                self.assertEqual(processing["canonical_items"], 0)
                self.assertEqual(processing["signals_created"], 0)

            stored_artifact = Path(imported["artifact_path"])
            self.assertEqual(stored_artifact.read_bytes(), payload)
            self.assertEqual(stat.S_IMODE(stored_artifact.stat().st_mode), 0o640)
            self.assertEqual(stat.S_IMODE((stored_artifact.parent / "request.json").stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE((stored_artifact.parent / "browser-result.json").stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(stored_artifact.parent.stat().st_mode), 0o700)

            repeated = import_provider_result(
                request_path=request_path,
                result_path=result_path,
                database=database,
                evidence_directory=evidence,
                registry=registry,
            )
            self.assertEqual(repeated["status"], "ALREADY_IMPORTED")
            with connect(database) as conn:
                for table in (
                    "scheduler_runs",
                    "acquisition_requests",
                    "acquisition_attempts",
                    "evidence_envelopes",
                    "processing_records",
                ):
                    self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 1)

    def test_import_rejects_tampered_artifact(self) -> None:
        registry = Registry.load(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = build_provider_request("S15A", registry=registry)
            request_path = root / "request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            artifact_path = root / "response.html"
            artifact_path.write_bytes(b"tampered")
            result = {
                "job_id": "browser-job-2",
                "state": "SUCCEEDED",
                "started_at": "2026-09-04T16:30:00Z",
                "finished_at": "2026-09-04T16:30:01Z",
                "result": {
                    "engine": "c0-fetch",
                    "url": request["url"],
                    "status": 200,
                    "content_type": "text/html",
                    "body_bytes": 5,
                    "artifact_path": str(artifact_path),
                    "sha256": hashlib.sha256(b"other").hexdigest(),
                },
            }
            result_path = root / "result.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(ProviderBridgeError, "SHA-256 mismatch"):
                import_provider_result(
                    request_path=request_path,
                    result_path=result_path,
                    database=root / "state" / "signalforge.db",
                    evidence_directory=root / "evidence",
                    registry=registry,
                )

    def test_import_rejects_tampered_request_contract(self) -> None:
        registry = Registry.load(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = build_provider_request("S15A", registry=registry)
            request["_provider_request"]["expected_content_types"] = ["application/pdf"]
            request_path = root / "request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            artifact_path = root / "response.html"
            payload = b"<html>ok</html>"
            artifact_path.write_bytes(payload)
            result_path = root / "result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "job_id": "browser-job-3",
                        "state": "SUCCEEDED",
                        "result": {
                            "engine": "c0-fetch",
                            "url": "https://www.mpa.gov.mm/tenders-and-announcement/",
                            "status": 200,
                            "content_type": "text/html",
                            "body_bytes": len(payload),
                            "artifact_path": str(artifact_path),
                            "sha256": hashlib.sha256(payload).hexdigest(),
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ProviderBridgeError, "expected content types mismatch"):
                import_provider_result(
                    request_path=request_path,
                    result_path=result_path,
                    database=root / "state" / "signalforge.db",
                    evidence_directory=root / "evidence",
                    registry=registry,
                )

    def test_provider_bridge_commands_are_not_worker_verbs(self) -> None:
        verbs = verb_manifest()["verbs"]
        self.assertNotIn("provider-request", verbs)
        self.assertNotIn("provider-import", verbs)
        self.assertNotIn("signalforge-provider-request", verbs)
        self.assertNotIn("signalforge-provider-import", verbs)


if __name__ == "__main__":
    unittest.main()
