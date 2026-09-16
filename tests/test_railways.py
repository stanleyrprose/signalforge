from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.db import migrate
from signalforge.engine import _failure_retry_delay_seconds, run_source
from signalforge.railways import parse_tender_detail, parse_tender_listing


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://www.railways.gov.mm/category/tender/"
DETAIL_URL = "https://www.railways.gov.mm/%e1%80%95%e1%80%ad%e1%80%af%e1%80%b7%e1%80%86%e1%80%b1%e1%80%ac%e1%80%84%e1%80%ba%e1%80%9b%e1%80%b1%e1%80%b8%e1%81%80%e1%80%94%e1%80%ba%e1%80%80%e1%80%bc%e1%80%ae%e1%80%b8%e1%80%8c%e1%80%ac-22/"


class RailwayFetcher:
    def __init__(self, listing: bytes, detail: bytes) -> None:
        self.listing = listing
        self.detail = detail
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url == LIST_URL:
            return self.listing
        if url == DETAIL_URL:
            return self.detail
        raise AssertionError(f"unexpected fetch: {url}")


def _railway_registry(*, actionable: bool = False) -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S21"]
    if not actionable:
        source.pop("actionable_baseline_signal_policy", None)
    source["bootstrap_seed_urls"] = [DETAIL_URL]
    source["baseline_detail_limit"] = 1
    source["delta_detail_limit"] = 2
    source["request_delay_ms"] = 0
    raw["sources"] = {"S21": source}
    return Registry(raw)


class RailwayParserTests(unittest.TestCase):
    def test_listing_discovers_current_tender_pages_with_dates(self) -> None:
        entries = parse_tender_listing((FIXTURES / "railways_tender_list.html").read_bytes())
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].url, DETAIL_URL)
        self.assertEqual(entries[0].lastmod, "2026-09-01T00:00:00Z")
        self.assertEqual(entries[1].lastmod, "2026-08-25T00:00:00Z")

    def test_detail_parses_multiple_tender_rows_and_myanmar_deadline(self) -> None:
        tenders = parse_tender_detail((FIXTURES / "railways_tender_detail.html").read_bytes(), DETAIL_URL)
        self.assertEqual(len(tenders), 4)
        self.assertEqual(tenders[0].reference_no, "၃၂၆/မမ/CE")
        self.assertEqual(tenders[0].canonical_key, "railways:326/မမ/CE")
        self.assertEqual(tenders[0].publication_date, "2026-09-01")
        self.assertEqual(tenders[0].deadline, "2026-09-14")
        self.assertIn("50KVA Transformer", tenders[0].project_name)
        self.assertEqual(tenders[1].canonical_key, "railways:12(T)30/MR(ML/ISN)")


class RailwayEngineTests(unittest.TestCase):
    def test_connect_timeout_retry_backoff_is_capped_by_recovery_slo(self) -> None:
        source = _railway_registry().raw["sources"]["S21"]
        expected = {
            1: 300,
            3: 300,
            4: 600,
            6: 600,
            7: 1200,
            9: 1200,
            10: 1800,
            500: 1800,
        }
        for failures, delay in expected.items():
            self.assertEqual(
                _failure_retry_delay_seconds(
                    source,
                    failure_class="CONNECT_TIMEOUT",
                    consecutive_failures_after=failures,
                ),
                delay,
            )
        self.assertEqual(
            _failure_retry_delay_seconds(
                source,
                failure_class="TRANSPORT_UNKNOWN",
                consecutive_failures_after=500,
            ),
            300,
        )

    def test_failed_acquisition_uses_persisted_failure_class_for_backoff(self) -> None:
        registry = _railway_registry()

        def timeout_fetcher(_url: str, **_kwargs) -> bytes:
            raise TimeoutError("connect timed out")

        now = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            migrate(db)
            with sqlite3.connect(db) as conn:
                conn.execute(
                    """
                    INSERT INTO source_state(
                        source_id,baseline_complete,last_success_at,next_due_at,last_error,
                        consecutive_failures,updated_at
                    ) VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        "S21",
                        1,
                        "2026-09-13T13:00:00Z",
                        "2026-09-16T09:00:00Z",
                        "previous timeout",
                        9,
                        "2026-09-16T08:30:00Z",
                    ),
                )

            with self.assertRaises(TimeoutError):
                run_source(
                    "S21",
                    registry=registry,
                    now=now,
                    fetcher=timeout_fetcher,
                    sleeper=lambda _seconds: None,
                    force=True,
                    database=db,
                    evidence=evidence,
                    worker_context={"run_id": "railways-timeout-backoff"},
                )

            with sqlite3.connect(db) as conn:
                state = conn.execute(
                    "SELECT next_due_at,consecutive_failures FROM source_state WHERE source_id='S21'"
                ).fetchone()
                failure = conn.execute(
                    """
                    SELECT a.acquisition_failure_class
                    FROM acquisition_attempts a
                    JOIN acquisition_requests r ON r.request_id=a.request_id
                    WHERE r.scheduler_run_id=(
                        SELECT app_run_id FROM scheduler_runs WHERE source_id='S21' ORDER BY started_at DESC LIMIT 1
                    )
                    ORDER BY a.started_at DESC
                    LIMIT 1
                    """
                ).fetchone()[0]

            self.assertEqual(state, ("2026-09-16T09:30:00Z", 10))
            self.assertEqual(failure, "CONNECT_TIMEOUT")

    def test_baseline_multi_item_page_is_signal_free_then_one_material_change_signals_once(self) -> None:
        registry = _railway_registry()
        listing = (FIXTURES / "railways_tender_list.html").read_bytes()
        detail = (FIXTURES / "railways_tender_detail.html").read_bytes()

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            baseline = run_source(
                "S21",
                registry=registry,
                now=datetime(2026, 9, 4, 0, 0, tzinfo=UTC),
                fetcher=RailwayFetcher(listing, detail),
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "railways-baseline"},
            )
            self.assertTrue(baseline["baseline"])
            self.assertEqual(baseline["details_attempted"], 1)
            self.assertEqual(baseline["details_succeeded"], 1)
            self.assertEqual(baseline["tenders"], 4)
            self.assertEqual(baseline["changed"], 4)
            self.assertEqual(baseline["signals_created"], 0)

            changed_listing = listing.replace(b"Sep 1, 2026", b"Sep 2, 2026", 1)
            changed_detail = detail.replace(
                "50KVA Transformer".encode(),
                "100KVA Transformer".encode(),
                1,
            )
            delta = run_source(
                "S21",
                registry=registry,
                now=datetime(2026, 9, 4, 0, 20, tzinfo=UTC),
                fetcher=RailwayFetcher(changed_listing, changed_detail),
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "railways-delta"},
            )
            self.assertFalse(delta["baseline"])
            self.assertEqual(delta["tenders"], 4)
            self.assertEqual(delta["changed"], 1)
            self.assertEqual(delta["signals_created"], 1)

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items").fetchone()[0], 4)
                signal = conn.execute("SELECT source_id,signal_type,canonical_key FROM signals").fetchone()
                counts = {
                    "requests": conn.execute("SELECT COUNT(*) FROM acquisition_requests").fetchone()[0],
                    "attempts": conn.execute("SELECT COUNT(*) FROM acquisition_attempts").fetchone()[0],
                    "evidence": conn.execute("SELECT COUNT(*) FROM evidence_envelopes").fetchone()[0],
                    "processing": conn.execute("SELECT COUNT(*) FROM processing_records").fetchone()[0],
                }
                marker = conn.execute(
                    "SELECT canonical_key FROM discovery_items WHERE source_id='S21' AND url=?",
                    (DETAIL_URL,),
                ).fetchone()[0]
            self.assertEqual(signal, ("S21", "UPDATED", "railways:326/မမ/CE"))
            self.assertEqual(counts, {"requests": 4, "attempts": 4, "evidence": 4, "processing": 4})
            self.assertIsNone(marker)

    def test_actionable_baseline_reconciliation_promotes_date_only_future_rows_without_inventing_time(self) -> None:
        registry = _railway_registry(actionable=True)
        listing = (FIXTURES / "railways_tender_list.html").read_bytes()
        detail = (FIXTURES / "railways_tender_detail.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            baseline = run_source(
                "S21", registry=registry, now=datetime(2026, 9, 11, 1, 0, tzinfo=UTC),
                fetcher=RailwayFetcher(listing, detail), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "railways-reconcile-baseline"},
            )
            self.assertEqual(baseline["signals_created"], 0)
            reconciled = run_source(
                "S21", registry=registry, now=datetime(2026, 9, 11, 1, 20, tzinfo=UTC),
                fetcher=RailwayFetcher(listing, detail), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "railways-reconcile-delta"},
            )
            self.assertEqual(reconciled["changed"], 0)
            self.assertEqual(reconciled["signals_created"], 4)
            idempotent = run_source(
                "S21", registry=registry, now=datetime(2026, 9, 11, 1, 40, tzinfo=UTC),
                fetcher=RailwayFetcher(listing, detail), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "railways-reconcile-idempotent"},
            )
            self.assertEqual(idempotent["signals_created"], 0)
            with sqlite3.connect(db) as conn:
                rows = conn.execute("SELECT canonical_key,payload_json FROM signals ORDER BY canonical_key").fetchall()
            self.assertEqual(len(rows), 4)
            for _key, raw in rows:
                payload = json.loads(raw)
                self.assertEqual(payload["signal_reason"], "ACTIONABLE_BASELINE_RECONCILIATION")
                self.assertEqual(payload["deadline"], "2026-09-14")
                self.assertNotIn("deadline_time", payload)



if __name__ == "__main__":
    unittest.main()
