from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SITEMAP_URL = "https://mpt.com.mm/page-sitemap.xml"
TENDER_URL = "https://mpt.com.mm/en/purchasing-of-top-up-card-with-qr-code-4/"
MPT4U_URL = "https://mpt.com.mm/en/mpt4u/"


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
            self.assertEqual(second["signals_created"], 1)
            with sqlite3.connect(db) as conn:
                signal = conn.execute("SELECT signal_type FROM signals").fetchone()
            self.assertEqual(signal, ("NEW",))

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


if __name__ == "__main__":
    unittest.main()
