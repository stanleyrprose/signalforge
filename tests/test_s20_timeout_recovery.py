"""S20 transient retry must preserve attempt evidence and other source dispatch."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from signalforge.db import migrate
from signalforge.engine import _acquire_source_bytes, run_due
from signalforge.http import FetchError

class S20TimeoutTests(unittest.TestCase):
    def acquire(self, database, fetcher, target="DISCOVERY"):
        return _acquire_source_bytes(
            source={"engine":"direct_http", "request_timeout_seconds":30,
                    "request_max_bytes":3000000, "source_policy_version":1,
                    "egress_profile":"mm-intl-datacenter"},
            database=database, scheduler_run_id="isolated-run", source_id="S20",
            reason="SCHEDULED", target_kind=target,
            url="https://moep.gov.mm/mm/ignite/page/62",
            expected_content_types=["text/html"], observed_at="2026-10-27T00:00:00Z",
            fetcher=fetcher)

    def test_one_transient_timeout_recovers_with_both_audit_rows(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"isolated.sqlite";migrate(db)
            with sqlite3.connect(db) as conn:
                conn.execute("INSERT INTO scheduler_runs(app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,status) VALUES(?,?,?,?,?,?,?)",
                             ("isolated-run","isolated-trigger","POLL","S20","isolated-worker","2026-10-27T00:00:00Z","RUNNING"))
            calls=[]
            def fetch(url, **limits):
                calls.append(limits)
                if len(calls)==1: raise FetchError("The read operation timed out")
                return b"<html>issuer content</html>"
            with patch("signalforge.engine.time.sleep") as pause:
                capture=self.acquire(db,fetch)
            self.assertEqual(capture.payload,b"<html>issuer content</html>")
            self.assertEqual(calls,[{"timeout":30,"max_bytes":3000000}]*2)
            pause.assert_called_once_with(0.5)
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT status,acquisition_failure_class FROM acquisition_attempts ORDER BY rowid").fetchall(),
                    [("FAILED","CONNECT_TIMEOUT"),("SUCCESS",None)])
                self.assertEqual(conn.execute("SELECT count(*) FROM evidence_envelopes").fetchone()[0],1)

    def test_persistent_timeout_stops_after_two_attempts_and_never_creates_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"isolated.sqlite";migrate(db)
            with sqlite3.connect(db) as conn:
                conn.execute("INSERT INTO scheduler_runs(app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,status) VALUES(?,?,?,?,?,?,?)",
                             ("isolated-run","isolated-trigger","POLL","S20","isolated-worker","2026-10-27T00:00:00Z","RUNNING"))
            calls=[]
            def fetch(*args,**kwargs):
                calls.append(kwargs)
                raise FetchError("timed out")
            with patch("signalforge.engine.time.sleep"):
                with self.assertRaises(FetchError):self.acquire(db,fetch)
            self.assertEqual(len(calls),2)
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT status,acquisition_failure_class FROM acquisition_attempts").fetchall(),
                                 [("FAILED","CONNECT_TIMEOUT")]*2)
                self.assertEqual(conn.execute("SELECT count(*) FROM evidence_envelopes").fetchone()[0],0)

    def test_missing_pdf_tls_failure_and_parser_errors_are_not_retried(self):
        for message,target in (("HTTP 404","HTML"),("certificate verify failed","HTML"),
                               ("HTML parser drift","HTML"),("timed out","PDF")):
            with self.subTest(message=message,target=target), tempfile.TemporaryDirectory() as td:
                with patch("signalforge.engine.acquire_local_bytes",side_effect=FetchError(message)) as request, patch("signalforge.engine.time.sleep") as pause:
                    with self.assertRaises(FetchError):self.acquire(Path(td)/"unused.sqlite",None,target)
                self.assertEqual(request.call_count,1)
                pause.assert_not_called()

    def test_exhausted_s20_does_not_prevent_next_source(self):
        class Registry:
            def enabled_sources(self):return [("S20",{}),("S37",{})]
        def run(source_id,**kwargs):
            if source_id=="S20":raise FetchError("timed out")
            return {"source_id":source_id,"status":"SUCCESS"}
        with patch("signalforge.engine.run_source",side_effect=run):
            result=run_due(registry=Registry())
        self.assertEqual([(r["source_id"],r["status"]) for r in result["results"]],
                         [("S20","FAILED"),("S37","SUCCESS")])
