from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.dof import DofParseError, parse_tender_records
from signalforge.engine import run_source

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://www.dof.gov.mm/index.php/my/tender"


class MapFetcher:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url != LIST_URL:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.payload


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    raw["sources"] = {"S28": raw["sources"]["S28"]}
    return Registry(raw)


class DofParserTests(unittest.TestCase):
    def test_listing_cards_are_complete_tenders_and_visible_dates_are_authoritative(self) -> None:
        items = parse_tender_records((FIXTURES / "dof_tenders.html").read_bytes())
        self.assertEqual(len(items), 3)
        first = items[0]
        self.assertEqual(first.item_kind, "TENDER")
        self.assertEqual(first.source_record_id, "2026-05-21t1546220630")
        self.assertEqual(first.canonical_key, "dof:2026-05-21t1546220630")
        self.assertEqual(first.reference_no_kind, "issuer_tender_alias")
        self.assertEqual(first.publication_date, "2026-05-21")
        self.assertEqual(first.tender_form_sale_date, "2026-05-21")
        self.assertEqual(first.deadline, "2026-06-01")
        self.assertIn("တည်ဆောက်ရေးလုပ်ငန်း", first.project_name)
        self.assertEqual(first.payload()["deadline_evidence"], "VISIBLE_TENDER_CLOSING_DATE_TEXT")
        self.assertEqual(first.payload()["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")
        self.assertEqual(items[1].deadline, "2026-04-24")
        self.assertIn("Website security", items[1].project_name)
        self.assertEqual(items[2].source_record_id, "2025-10-01t1433310630")
        self.assertEqual(items[2].publication_date, "2025-09-30")

    def test_parser_fails_closed_without_complete_tender_card(self) -> None:
        with self.assertRaises(DofParseError):
            parse_tender_records(b'<div class="card shadow"><h5 class="card-title">News</h5></div>')


class DofEngineTests(unittest.TestCase):
    def test_listing_complete_baseline_is_one_fetch_signal_free_and_same_alias_update_signals_once(self) -> None:
        registry = _registry()
        baseline_html = (FIXTURES / "dof_tenders.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            first_fetcher = MapFetcher(baseline_html)
            first = run_source(
                "S28", registry=registry, now=datetime(2026, 9, 4, 10, 0, tzinfo=UTC),
                fetcher=first_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "dof-baseline"},
            )
            self.assertTrue(first["baseline"])
            self.assertTrue(first["listing_complete"])
            self.assertEqual(first["items"], 3)
            self.assertEqual(first["tenders"], 3)
            self.assertEqual(first["details_attempted"], 0)
            self.assertEqual(first["changed"], 3)
            self.assertEqual(first["signals_created"], 0)
            self.assertEqual(first_fetcher.calls, [LIST_URL])

            changed_html = baseline_html.replace(
                "တင်ဒါနောက်ဆုံးလက်ခံမည့်နေ့ရက် ၁-၆-၂၀၂၆".encode(),
                "တင်ဒါနောက်ဆုံးလက်ခံမည့်နေ့ရက် ၂-၆-၂၀၂၆".encode(),
                1,
            )
            second_fetcher = MapFetcher(changed_html)
            second = run_source(
                "S28", registry=registry, now=datetime(2026, 9, 4, 10, 31, tzinfo=UTC),
                fetcher=second_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "dof-update"},
            )
            self.assertFalse(second["baseline"])
            self.assertEqual(second["items"], 3)
            self.assertEqual(second["changed"], 1)
            self.assertEqual(second["signals_created"], 1)
            self.assertEqual(second_fetcher.calls, [LIST_URL])

            with sqlite3.connect(db) as conn:
                rows = conn.execute("SELECT canonical_key,item_kind,deadline FROM canonical_items WHERE source_id='S28' ORDER BY canonical_key").fetchall()
                signal = conn.execute("SELECT signal_type,canonical_key FROM signals WHERE source_id='S28'").fetchone()
                lifecycle = tuple(conn.execute(q).fetchone()[0] for q in [
                    "SELECT count(*) FROM acquisition_requests WHERE source_id='S28'",
                    "SELECT count(*) FROM acquisition_attempts WHERE source_id='S28'",
                    "SELECT count(*) FROM evidence_envelopes WHERE source_id='S28'",
                    "SELECT count(*) FROM processing_records WHERE source_id='S28'",
                ])
                pdf_requests = conn.execute("SELECT count(*) FROM evidence_envelopes WHERE source_id='S28' AND lower(requested_url) LIKE '%.pdf%'").fetchone()[0]
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(row[1] == "TENDER" for row in rows))
            self.assertEqual(signal, ("UPDATED", "dof:2026-05-21t1546220630"))
            self.assertEqual(lifecycle, (2, 2, 2, 2))
            self.assertEqual(pdf_requests, 0)


if __name__ == "__main__":
    unittest.main()
