from __future__ import annotations

import copy
import sqlite3
import ssl
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.acquisition_contract import (
    AcquisitionContractError,
    AcquisitionFailure,
    classify_acquisition_failure,
    validate_source_acquisition_policy,
)
from signalforge.config import Registry
from signalforge.engine import run_source


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SITEMAP_URL = "https://mpt.com.mm/page-sitemap.xml"
TENDER_URL = "https://mpt.com.mm/en/purchasing-of-top-up-card-with-qr-code-4/"


class FixtureFetcher:
    def __init__(self) -> None:
        self.sitemap = (FIXTURES / "mpt_page_sitemap.xml").read_bytes()
        self.tender = (FIXTURES / "mpt_tender_detail.html").read_bytes()

    def __call__(self, url: str, **_kwargs) -> bytes:
        if url == SITEMAP_URL:
            return self.sitemap
        if url == TENDER_URL:
            return self.tender
        return b"<html><body>ordinary MPT page</body></html>"


class AcquisitionContractTests(unittest.TestCase):
    def test_s13_acquisition_policy_is_local_direct_http_and_fails_closed(self) -> None:
        registry = Registry.load(ROOT)
        source = registry.source("S13")
        self.assertEqual(source["source_policy_version"], 8)
        self.assertEqual(source["egress_profile"], "mm-intl-datacenter")
        self.assertEqual(source["acquisition_policy"]["primary"], {"method": "DIRECT_HTTP", "target_kind": "HTML"})
        self.assertEqual(source["acquisition_policy"]["escalation"]["TLS_FAILURE"]["action"], "FAIL")
        self.assertEqual(source["acquisition_policy"]["escalation"]["JS_RENDER_REQUIRED"]["action"], "REVIEW_CAPABILITY")
        self.assertEqual(source["acquisition_policy"]["escalation"]["PARSER_DRIFT"]["action"], "REAUDIT")

        bad = copy.deepcopy(source)
        bad["acquisition_policy"]["escalation"]["TLS_FAILURE"]["action"] = "REVIEW"
        with self.assertRaisesRegex(AcquisitionContractError, "TLS_FAILURE must fail closed"):
            validate_source_acquisition_policy("S13", bad)

    def test_acquisition_failure_classification_is_failure_aware(self) -> None:
        self.assertEqual(classify_acquisition_failure(TimeoutError("timed out")), AcquisitionFailure.CONNECT_TIMEOUT)
        self.assertEqual(classify_acquisition_failure(ssl.SSLError("certificate verify failed")), AcquisitionFailure.TLS_FAILURE)
        self.assertEqual(classify_acquisition_failure(RuntimeError("HTTP 403 for source")), AcquisitionFailure.HTTP_403)
        self.assertEqual(classify_acquisition_failure(RuntimeError("HTTP 429 for source")), AcquisitionFailure.HTTP_429)
        self.assertEqual(classify_acquisition_failure(RuntimeError("unknown transport")), AcquisitionFailure.TRANSPORT_UNKNOWN)

    def test_s13_records_internal_request_attempt_evidence_processing_without_new_worker_runs(self) -> None:
        registry = Registry.load(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            result = run_source(
                "S13",
                registry=registry,
                now=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
                fetcher=FixtureFetcher(),
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=base / "evidence",
                worker_context={"run_id": "worker-v15-reference"},
            )
            self.assertEqual(result["status"], "SUCCESS")
            self.assertEqual(result["signals_created"], 0)

            with sqlite3.connect(db) as conn:
                scheduler = conn.execute("SELECT app_run_id,worker_run_id,status FROM scheduler_runs").fetchall()
                requests = conn.execute(
                    "SELECT request_id,scheduler_run_id,reason,source_id,source_policy_version,egress_profile FROM acquisition_requests ORDER BY requested_at,request_id"
                ).fetchall()
                attempts = conn.execute(
                    "SELECT request_id,attempt_number,status,acquisition_failure_class FROM acquisition_attempts"
                ).fetchall()
                evidence = conn.execute(
                    "SELECT request_id,attempt_id,source_id,execution_scope,provider_id,fetch_method,artifact_sha256 FROM evidence_envelopes"
                ).fetchall()
                processing = conn.execute(
                    "SELECT evidence_id,parser_version,status,processing_failure_class FROM processing_records"
                ).fetchall()
                attempt_columns = {row[1] for row in conn.execute("PRAGMA table_info(acquisition_attempts)")}
                evidence_columns = {row[1] for row in conn.execute("PRAGMA table_info(evidence_envelopes)")}
                schema_versions = {
                    table: conn.execute(f"SELECT DISTINCT schema_version FROM {table}").fetchall()
                    for table in ("acquisition_requests", "acquisition_attempts", "evidence_envelopes", "processing_records")
                }

            self.assertEqual(len(scheduler), 1)
            self.assertEqual(scheduler[0][1:], ("worker-v15-reference", "SUCCESS"))
            self.assertGreaterEqual(len(requests), 2)
            self.assertEqual(len(requests), len(attempts))
            self.assertEqual(len(requests), len(evidence))
            self.assertEqual(len(requests), len(processing))
            self.assertTrue(all(row[1] == scheduler[0][0] for row in requests))
            self.assertTrue(all(row[2] == "SCHEDULED" for row in requests))
            self.assertTrue(all(row[3] == "S13" and row[4] == 8 and row[5] == "mm-intl-datacenter" for row in requests))
            self.assertTrue(all(row[1] == 1 and row[2] == "SUCCESS" and row[3] is None for row in attempts))
            self.assertTrue(all(row[2] == "S13" and row[3] == "LOCAL_BANGKOK" and row[4] == "bkk-local" and row[5] == "DIRECT_HTTP" for row in evidence))
            self.assertTrue(any(row[1] == "mpt-v3" for row in processing))
            self.assertNotIn("worker_run_id", attempt_columns)
            self.assertNotIn("worker_run_id", evidence_columns)
            self.assertNotIn("parser_version", evidence_columns)
            self.assertTrue(all(values == [(1,)] for values in schema_versions.values()))

    def test_failed_acquisition_persists_failure_class_without_fake_evidence(self) -> None:
        registry = Registry.load(ROOT)

        class ForbiddenFetcher:
            def __call__(self, url: str, **_kwargs) -> bytes:
                raise RuntimeError(f"HTTP 403 for {url}")

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
                run_source(
                    "S13", registry=registry, now=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
                    fetcher=ForbiddenFetcher(), sleeper=lambda _seconds: None, force=True,
                    database=db, evidence=base / "evidence", worker_context={"run_id": "worker-failed-acquisition"},
                )
            with sqlite3.connect(db) as conn:
                attempt = conn.execute(
                    "SELECT status,acquisition_failure_class FROM acquisition_attempts"
                ).fetchone()
                evidence_count = conn.execute("SELECT COUNT(*) FROM evidence_envelopes").fetchone()[0]
                processing_count = conn.execute("SELECT COUNT(*) FROM processing_records").fetchone()[0]
                scheduler = conn.execute("SELECT status,worker_run_id FROM scheduler_runs").fetchone()
            self.assertEqual(attempt, ("FAILED", "HTTP_403"))
            self.assertEqual(evidence_count, 0)
            self.assertEqual(processing_count, 0)
            self.assertEqual(scheduler, ("FAILED", "worker-failed-acquisition"))

    def test_health_probe_is_a_signalforge_acquisition_reason_not_a_worker_run(self) -> None:
        registry = Registry.load(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence_root = base / "evidence"
            run_source(
                "S13", registry=registry, now=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
                fetcher=FixtureFetcher(), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence_root, worker_context={"run_id": "worker-baseline"},
            )
            due = run_source(
                "S13", registry=registry, now=datetime(2026, 9, 3, 13, 1, tzinfo=UTC),
                fetcher=FixtureFetcher(), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence_root, worker_context={"run_id": "worker-probe"},
            )
            self.assertTrue(due["health_probe"])
            with sqlite3.connect(db) as conn:
                reasons = [row[0] for row in conn.execute(
                    "SELECT reason FROM acquisition_requests WHERE scheduler_run_id=? ORDER BY rowid",
                    (due["app_run_id"],),
                )]
                worker_runs = conn.execute("SELECT COUNT(*) FROM scheduler_runs WHERE worker_run_id='worker-probe'").fetchone()[0]
            self.assertIn("HEALTH_PROBE", reasons)
            self.assertEqual(worker_runs, 1)


if __name__ == "__main__":
    unittest.main()
