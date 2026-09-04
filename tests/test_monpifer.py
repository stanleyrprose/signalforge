from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.monpifer import MonpiferParseError, parse_tender_records

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://www.monpifer.gov.mm/my/ministry-tenders"


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
    source = raw["sources"]["S25"]
    raw["sources"] = {"S25": source}
    return Registry(raw)


class MonpiferParserTests(unittest.TestCase):
    def test_listing_rows_are_complete_tenders_with_visible_deadline_authoritative(self) -> None:
        items = parse_tender_records((FIXTURES / "monpifer_tenders.html").read_bytes())
        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first.item_kind, "TENDER")
        self.assertEqual(first.deadline, "2026-07-14T16:00:00+06:30")
        self.assertEqual(first.source_record_id, "current-tender-2")
        self.assertEqual(first.canonical_key, "monpifer:current-tender-2")
        self.assertEqual(first.reference_no_kind, "issuer_article_alias")
        self.assertEqual(first.attachment_name, "Tender_0.pdf")
        self.assertEqual(first.payload()["deadline_evidence"], "VISIBLE_LAST_DATE_TEXT")
        self.assertEqual(first.payload()["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")
        self.assertIsNone(first.tender_department)
        self.assertEqual(items[1].tender_department, "စီမံကိန်းစိစစ်ရေးနှင့် တိုးတက်မှုအစီရင်ခံရေးဦးစီးဌာန")

    def test_parser_fails_closed_when_table_shape_has_no_open_tender(self) -> None:
        with self.assertRaises(MonpiferParseError):
            parse_tender_records(b"<table><tr><td>07/14/2026 - 16:00</td><td>News</td></tr></table>")


class MonpiferEngineTests(unittest.TestCase):
    def test_listing_complete_baseline_is_one_fetch_signal_free_and_update_signals_once(self) -> None:
        registry = _registry()
        baseline_html = (FIXTURES / "monpifer_tenders.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            first_fetcher = MapFetcher(baseline_html)
            first = run_source(
                "S25", registry=registry, now=datetime(2026, 9, 4, 10, 0, tzinfo=UTC),
                fetcher=first_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "monpifer-baseline"},
            )
            self.assertTrue(first["baseline"])
            self.assertTrue(first["listing_complete"])
            self.assertEqual(first["items"], 2)
            self.assertEqual(first["tenders"], 2)
            self.assertEqual(first["details_attempted"], 0)
            self.assertEqual(first["changed"], 2)
            self.assertEqual(first["signals_created"], 0)
            self.assertEqual(first_fetcher.calls, [LIST_URL])

            changed_html = baseline_html.replace(
                b"07/14/2026 - 16:00",
                b"07/15/2026 - 16:00",
                1,
            )
            second_fetcher = MapFetcher(changed_html)
            second = run_source(
                "S25", registry=registry, now=datetime(2026, 9, 4, 10, 31, tzinfo=UTC),
                fetcher=second_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "monpifer-update"},
            )
            self.assertFalse(second["baseline"])
            self.assertEqual(second["items"], 2)
            self.assertEqual(second["changed"], 1)
            self.assertEqual(second["signals_created"], 1)
            self.assertEqual(second_fetcher.calls, [LIST_URL])

            with sqlite3.connect(db) as conn:
                rows = conn.execute("SELECT canonical_key,item_kind,deadline FROM canonical_items WHERE source_id='S25' ORDER BY canonical_key").fetchall()
                signal = conn.execute("SELECT signal_type,canonical_key FROM signals WHERE source_id='S25'").fetchone()
                lifecycle = tuple(conn.execute(q).fetchone()[0] for q in [
                    "SELECT count(*) FROM acquisition_requests WHERE source_id='S25'",
                    "SELECT count(*) FROM acquisition_attempts WHERE source_id='S25'",
                    "SELECT count(*) FROM evidence_envelopes WHERE source_id='S25'",
                    "SELECT count(*) FROM processing_records WHERE source_id='S25'",
                ])
                pdf_requests = conn.execute("SELECT count(*) FROM evidence_envelopes WHERE source_id='S25' AND lower(requested_url) LIKE '%.pdf%'").fetchone()[0]
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row[1] == "TENDER" for row in rows))
            self.assertEqual(signal, ("UPDATED", "monpifer:current-tender-2"))
            self.assertEqual(lifecycle, (2, 2, 2, 2))
            self.assertEqual(pdf_requests, 0)


if __name__ == "__main__":
    unittest.main()
