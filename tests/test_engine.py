from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.cli import status
from signalforge.config import Registry
from signalforge.engine import run_due, run_source


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SITEMAP_URL = "https://mpt.com.mm/page-sitemap.xml"
TENDER_URL = "https://mpt.com.mm/en/purchasing-of-top-up-card-with-qr-code-4/"
MPT4U_URL = "https://mpt.com.mm/en/mpt4u/"


def _sitemap(entries: list[tuple[str, str]]) -> bytes:
    body = "".join(f"<url><loc>{url}</loc><lastmod>{lastmod}</lastmod></url>" for url, lastmod in entries)
    return (f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>').encode()


def _tender_html(reference: str, project: str) -> bytes:
    return f"""
    <html><body><table>
      <tr><td>Date</td><td>September 2, 2026</td></tr>
      <tr><td>Reference No</td><td>{reference}</td></tr>
      <tr><td>Project Name</td><td>{project}</td></tr>
      <tr><td>Location</td><td>Yangon, Myanmar</td></tr>
    </table><p>Deadline September 30, 2026</p></body></html>
    """.encode()


class FixtureFetcher:
    def __init__(self, sitemap: bytes, tender: bytes) -> None:
        self.sitemap = sitemap
        self.tender = tender
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url == SITEMAP_URL:
            return self.sitemap
        if url == TENDER_URL:
            return self.tender
        if url == MPT4U_URL:
            return b"<html><h1>MPT4U</h1><p>consumer page</p></html>"
        raise AssertionError(f"unexpected fetch: {url}")


class RunDueIsolationTests(unittest.TestCase):
    def test_one_source_exception_does_not_block_later_sources(self) -> None:
        class FakeRegistry:
            def enabled_sources(self):
                return [("S28", {}), ("S29", {}), ("S38", {})]

        registry = FakeRegistry()
        with patch(
            "signalforge.engine.run_source",
            side_effect=[
                {"source_id": "S28", "status": "SUCCESS"},
                RuntimeError("all bounded detail candidates failed"),
                {"source_id": "S38", "status": "SUCCESS"},
            ],
        ) as mocked:
            result = run_due(registry=registry)

        self.assertEqual(mocked.call_count, 3)
        self.assertEqual([item["source_id"] for item in result["results"]], ["S28", "S29", "S38"])
        self.assertEqual(result["results"][1]["status"], "FAILED")
        self.assertIn("all bounded detail candidates failed", result["results"][1]["error"])
        self.assertEqual(result["results"][2]["status"], "SUCCESS")
        self.assertEqual(result["status"], "FAILED")


class EngineTests(unittest.TestCase):
    def test_failed_detail_remains_retryable_after_sitemap_snapshot(self) -> None:
        registry = Registry.load(ROOT)
        sitemap = (FIXTURES / "mpt_page_sitemap.xml").read_bytes()
        tender = (FIXTURES / "mpt_tender_detail.html").read_bytes()

        class FirstFetcher(FixtureFetcher):
            def __call__(self, url: str, **kwargs) -> bytes:
                if url == TENDER_URL:
                    self.calls.append(url)
                    raise RuntimeError("transient detail failure")
                return super().__call__(url, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            first = run_source(
                "S13",
                registry=registry,
                now=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                fetcher=FirstFetcher(sitemap, tender),
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "worker-retry-1"},
            )
            self.assertEqual(first["detail_errors"], 1)
            self.assertEqual(first["signals_created"], 0)
            second = run_source(
                "S13",
                registry=registry,
                now=datetime(2026, 9, 2, 12, 20, tzinfo=UTC),
                fetcher=FixtureFetcher(sitemap, tender),
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "worker-retry-2"},
            )
            self.assertEqual(second["candidates"], 1)
            self.assertEqual(second["tenders"], 1)
            self.assertEqual(second["signals_created"], 0)
            with sqlite3.connect(db) as conn:
                signal_count = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
                discovery = conn.execute(
                    "SELECT fetched_lastmod,pending_since_at,suppress_signal_once FROM discovery_items WHERE source_id='S13' AND url=?",
                    (TENDER_URL,),
                ).fetchone()
            self.assertEqual(signal_count, 0)
            self.assertIsNotNone(discovery[0])
            self.assertIsNone(discovery[1])
            self.assertEqual(discovery[2], 0)

    def test_zero_item_detail_retains_raw_evidence_for_assurance(self) -> None:
        registry = Registry.load(ROOT)
        sitemap = _sitemap([(TENDER_URL, "2026-09-02T12:00:00+00:00")])
        filtered_html = b"<html><body><h1>Not a tender detail</h1></body></html>"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            result = run_source(
                "S13",
                registry=registry,
                now=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                fetcher=FixtureFetcher(sitemap, filtered_html),
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "zero-item-evidence"},
            )
            self.assertEqual(result["status"], "SUCCESS")
            self.assertEqual(result["details_attempted"], 1)
            self.assertEqual(result["tenders"], 0)
            with sqlite3.connect(db) as conn:
                artifact_sha = conn.execute(
                    "SELECT artifact_sha256 FROM evidence_envelopes WHERE requested_url=?",
                    (TENDER_URL,),
                ).fetchone()[0]
                processing = conn.execute(
                    """
                    SELECT p.status,p.items_found
                    FROM processing_records p
                    JOIN evidence_envelopes e ON e.evidence_id=p.evidence_id
                    WHERE e.requested_url=?
                    """,
                    (TENDER_URL,),
                ).fetchone()
            self.assertEqual(processing, ("SUCCESS", 0))
            self.assertEqual((evidence / "S13" / f"{artifact_sha}.html").read_bytes(), filtered_html)

    def test_baseline_suppresses_signal_then_material_change_updates(self) -> None:
        registry = Registry.load(ROOT)
        sitemap = (FIXTURES / "mpt_page_sitemap.xml").read_bytes()
        tender = (FIXTURES / "mpt_tender_detail.html").read_bytes()
        now = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
        worker = {"run_id": "worker-run-001", "worker": "bangkok", "application": "signalforge"}

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            fetcher = FixtureFetcher(sitemap, tender)
            first = run_source(
                "S13",
                registry=registry,
                now=now,
                fetcher=fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context=worker,
            )
            self.assertTrue(first["baseline"])
            self.assertEqual(first["signals_created"], 0)
            self.assertEqual(first["tenders"], 1)
            self.assertTrue(any((evidence / "S13").glob("*.html")))

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0], 0)
                correlation = conn.execute("SELECT worker_run_id,baseline,status FROM scheduler_runs").fetchone()
            self.assertEqual(correlation, ("worker-run-001", 1, "SUCCESS"))

            changed_sitemap = sitemap.replace(
                b"2026-07-17T05:33:56+00:00",
                b"2026-09-02T12:01:00+00:00",
            )
            changed_tender = tender.replace(
                b"Purchasing of Top-up Card with QR code</strong></td></tr>",
                b"Purchasing of Top-up Card with QR code - revised</strong></td></tr>",
                1,
            )
            second_fetcher = FixtureFetcher(changed_sitemap, changed_tender)
            second = run_source(
                "S13",
                registry=registry,
                now=datetime(2026, 9, 2, 12, 20, tzinfo=UTC),
                fetcher=second_fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={**worker, "run_id": "worker-run-002"},
            )
            self.assertFalse(second["baseline"])
            self.assertEqual(second["candidates"], 1)
            self.assertEqual(second["signals_created"], 1)
            with sqlite3.connect(db) as conn:
                signal = conn.execute("SELECT signal_type,canonical_key FROM signals").fetchone()
                latest = conn.execute("SELECT worker_run_id,baseline,status FROM scheduler_runs ORDER BY started_at DESC LIMIT 1").fetchone()
            self.assertEqual(signal, ("UPDATED", "mpt:CCO-2026-001"))
            self.assertEqual(latest, ("worker-run-002", 0, "SUCCESS"))

    def test_manual_refresh_is_forceful_and_records_manual_trigger(self) -> None:
        registry = Registry.load(ROOT)
        sitemap = (FIXTURES / "mpt_page_sitemap.xml").read_bytes()
        tender = (FIXTURES / "mpt_tender_detail.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            baseline = run_source(
                "S13", registry=registry, now=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                fetcher=FixtureFetcher(sitemap, tender), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "manual-baseline"},
            )
            self.assertEqual(baseline["signals_created"], 0)
            manual = run_source(
                "S13", registry=registry, now=datetime(2026, 9, 2, 12, 5, tzinfo=UTC),
                fetcher=FixtureFetcher(sitemap, tender), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "manual-worker-run"},
                trigger_kind_override="MANUAL",
            )
            self.assertEqual(manual["status"], "SUCCESS")
            with sqlite3.connect(db) as conn:
                row = conn.execute(
                    "SELECT trigger_kind,trigger_id,worker_run_id,signals_created FROM scheduler_runs WHERE worker_run_id='manual-worker-run'"
                ).fetchone()
                acquisition_reasons = {
                    item[0] for item in conn.execute(
                        "SELECT reason FROM acquisition_requests WHERE scheduler_run_id=?",
                        (manual["app_run_id"],),
                    )
                }
            self.assertEqual(row[0], "MANUAL")
            self.assertTrue(row[1].startswith("manual:S13:"))
            self.assertEqual(row[2], "manual-worker-run")
            self.assertEqual(row[3], 0)
            self.assertEqual(acquisition_reasons, {"MANUAL"})

    def test_low_frequency_parse_health_probe_is_bounded_and_signal_free(self) -> None:
        registry = Registry.load(ROOT)
        sitemap = (FIXTURES / "mpt_page_sitemap.xml").read_bytes()
        tender = (FIXTURES / "mpt_tender_detail.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            baseline = run_source(
                "S13", registry=registry, now=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                fetcher=FixtureFetcher(sitemap, tender), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "probe-baseline"},
            )
            self.assertEqual(baseline["details_attempted"], 1)
            self.assertEqual(baseline["details_succeeded"], 1)

            early_fetcher = FixtureFetcher(sitemap, tender)
            early = run_source(
                "S13", registry=registry, now=datetime(2026, 9, 2, 12, 20, tzinfo=UTC),
                fetcher=early_fetcher, sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "probe-early"},
            )
            self.assertFalse(early["health_probe"])
            self.assertEqual(early["candidates"], 0)
            self.assertEqual(early_fetcher.calls, [SITEMAP_URL])

            due_fetcher = FixtureFetcher(sitemap, tender)
            due = run_source(
                "S13", registry=registry, now=datetime(2026, 9, 2, 13, 1, tzinfo=UTC),
                fetcher=due_fetcher, sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "probe-due"},
            )
            self.assertTrue(due["health_probe"])
            self.assertEqual(due["candidates"], 1)
            self.assertEqual(due["details_attempted"], 1)
            self.assertEqual(due["details_succeeded"], 1)
            self.assertEqual(due["signals_created"], 0)
            self.assertEqual(due_fetcher.calls, [SITEMAP_URL, TENDER_URL])

            with sqlite3.connect(db) as conn:
                row = conn.execute(
                    "SELECT details_attempted,details_succeeded,tenders_parsed,signals_created FROM scheduler_runs WHERE worker_run_id='probe-due'"
                ).fetchone()
            self.assertEqual(row, (1, 1, 1, 0))

    def test_same_evidence_semantic_reparse_updates_canonical_without_signal(self) -> None:
        registry = Registry.load(ROOT)
        sitemap = (FIXTURES / "mpt_page_sitemap.xml").read_bytes()
        tender = (FIXTURES / "mpt_tender_detail.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            baseline = run_source(
                "S13", registry=registry, now=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                fetcher=FixtureFetcher(sitemap, tender), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "semantic-baseline"},
            )
            self.assertEqual(baseline["signals_created"], 0)

            with sqlite3.connect(db) as conn:
                conn.execute(
                    "UPDATE canonical_items SET content_hash='legacy-semantic-output', payload_json='{}' "
                    "WHERE canonical_key='mpt:CCO-2026-001'"
                )
                conn.commit()

            reparsed = run_source(
                "S13", registry=registry, now=datetime(2026, 9, 2, 13, 1, tzinfo=UTC),
                fetcher=FixtureFetcher(sitemap, tender), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "semantic-reparse"},
            )
            self.assertTrue(reparsed["health_probe"])
            self.assertEqual(reparsed["changed"], 1)
            self.assertEqual(reparsed["signals_created"], 0)

            with sqlite3.connect(db) as conn:
                signal_count = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
                payload_json = conn.execute(
                    "SELECT payload_json FROM canonical_items WHERE canonical_key='mpt:CCO-2026-001'"
                ).fetchone()[0]
            self.assertEqual(signal_count, 0)
            self.assertEqual(json.loads(payload_json)["business_stage"], "OPPORTUNITY")

    def test_recovery_reconciliation_is_bounded_durable_and_deduplicated(self) -> None:
        raw = json.loads(json.dumps(Registry.load(ROOT).raw))
        source = raw["sources"]["S13"]
        source["baseline_lookback_days"] = 365
        source["baseline_detail_limit"] = 10
        source["delta_detail_limit"] = 2
        source["request_delay_ms"] = 0
        source["bootstrap_seed_urls"] = []
        raw["sources"] = {"S13": source}
        registry = Registry(raw)

        urls = [f"https://mpt.com.mm/en/gate-s-tender-{index}/" for index in range(5)]
        baseline_sitemap = _sitemap([(url, "2026-09-02T12:00:00+00:00") for url in urls])
        recovery_sitemap = _sitemap([(url, "2026-09-02T13:00:00+00:00") for url in urls])
        baseline_pages = {url: _tender_html(f"GATE-S-{index}", f"Gate S Project {index}") for index, url in enumerate(urls)}
        recovery_pages = {url: _tender_html(f"GATE-S-{index}", f"Gate S Project {index} revised") for index, url in enumerate(urls)}

        class MapFetcher:
            def __init__(self, sitemap: bytes, pages: dict[str, bytes]) -> None:
                self.sitemap = sitemap
                self.pages = pages
                self.calls: list[str] = []

            def __call__(self, url: str, **_kwargs) -> bytes:
                self.calls.append(url)
                if url == SITEMAP_URL:
                    return self.sitemap
                return self.pages[url]

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            baseline_fetcher = MapFetcher(baseline_sitemap, baseline_pages)
            baseline = run_source(
                "S13",
                registry=registry,
                now=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                fetcher=baseline_fetcher,
                sleeper=lambda _seconds: None,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "worker-baseline"},
            )
            self.assertTrue(baseline["baseline"])
            self.assertEqual(baseline["changed"], 5)
            self.assertEqual(baseline["signals_created"], 0)
            self.assertEqual(baseline["backlog_remaining"], 0)

            first_fetcher = MapFetcher(recovery_sitemap, recovery_pages)
            first = run_source(
                "S13",
                registry=registry,
                now=datetime(2026, 9, 2, 13, 0, tzinfo=UTC),
                fetcher=first_fetcher,
                sleeper=lambda _seconds: None,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "worker-recovery-1"},
            )
            self.assertTrue(first["recovery"])
            self.assertEqual(first["trigger_type"], "RECONCILIATION")
            self.assertEqual(first["candidates"], 2)
            self.assertEqual(first["backlog_remaining"], 3)
            self.assertEqual(first["signals_created"], 2)
            self.assertLessEqual(len(first_fetcher.calls), 3)

            with patch.dict(
                os.environ,
                {"SIGNALFORGE_DB": str(db), "SIGNALFORGE_REPO_ROOT": str(ROOT)},
                clear=False,
            ):
                health = status(registry=registry)
            self.assertEqual(health["counts"]["recovery_backlog"], 3)
            self.assertIn(health["sources"][0]["health"]["recovery_backlog_health"], {"YELLOW", "RED"})

            second_fetcher = MapFetcher(recovery_sitemap, recovery_pages)
            second = run_source(
                "S13",
                registry=registry,
                now=datetime(2026, 9, 2, 13, 5, tzinfo=UTC),
                fetcher=second_fetcher,
                sleeper=lambda _seconds: None,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "worker-recovery-2"},
            )
            self.assertTrue(second["recovery"])
            self.assertEqual(second["candidates"], 2)
            self.assertEqual(second["backlog_remaining"], 1)
            self.assertEqual(second["signals_created"], 2)
            self.assertLessEqual(len(second_fetcher.calls), 3)

            third_fetcher = MapFetcher(recovery_sitemap, recovery_pages)
            third = run_source(
                "S13",
                registry=registry,
                now=datetime(2026, 9, 2, 13, 10, tzinfo=UTC),
                fetcher=third_fetcher,
                sleeper=lambda _seconds: None,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "worker-recovery-3"},
            )
            self.assertTrue(third["recovery"])
            self.assertEqual(third["candidates"], 1)
            self.assertEqual(third["backlog_remaining"], 0)
            self.assertEqual(third["signals_created"], 1)
            self.assertLessEqual(len(third_fetcher.calls), 2)

            steady_fetcher = MapFetcher(recovery_sitemap, recovery_pages)
            steady = run_source(
                "S13",
                registry=registry,
                now=datetime(2026, 9, 2, 13, 25, tzinfo=UTC),
                fetcher=steady_fetcher,
                sleeper=lambda _seconds: None,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "worker-steady"},
            )
            self.assertFalse(steady["recovery"])
            self.assertEqual(steady["candidates"], 0)
            self.assertEqual(steady["signals_created"], 0)

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items").fetchone()[0], 5)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0], 5)
                self.assertEqual(conn.execute("SELECT COUNT(DISTINCT canonical_key) FROM canonical_items").fetchone()[0], 5)
                recovery_runs = conn.execute(
                    "SELECT trigger_kind,recovery,backlog_remaining,outage_window_start,outage_window_end FROM scheduler_runs WHERE recovery=1 ORDER BY started_at"
                ).fetchall()
                state = conn.execute(
                    "SELECT recovery_window_start,recovery_window_end,last_successful_reconciliation_at FROM source_state WHERE source_id='S13'"
                ).fetchone()
            self.assertEqual([row[2] for row in recovery_runs], [3, 1, 0])
            self.assertTrue(all(row[0] == "RECONCILIATION" and row[1] == 1 for row in recovery_runs))
            self.assertTrue(all(row[3] == recovery_runs[0][3] and row[4] == recovery_runs[0][4] for row in recovery_runs))
            self.assertEqual(state[0:2], (None, None))
            self.assertEqual(state[2], "2026-09-02T13:25:00Z")

            with patch.dict(
                os.environ,
                {"SIGNALFORGE_DB": str(db), "SIGNALFORGE_REPO_ROOT": str(ROOT)},
                clear=False,
            ):
                recovered_health = status(now=datetime(2026, 9, 2, 13, 25, tzinfo=UTC), registry=registry)
            self.assertEqual(recovered_health["status"], "PASS")
            self.assertEqual(recovered_health["counts"]["recovery_backlog"], 0)


if __name__ == "__main__":
    unittest.main()
