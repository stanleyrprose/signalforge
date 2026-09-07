from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.doa import DOA_ANNOUNCEMENTS_URL, DoaParseError, is_procurement_event, parse_tender_records
from signalforge.engine import run_source

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LISTING = (FIXTURES / "doa_announcements.html").read_bytes()


class SinglePageFetcher:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url != DOA_ANNOUNCEMENTS_URL:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.payload


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    raw["sources"] = {"S36": raw["sources"]["S36"]}
    return Registry(raw)


class DoaParserTests(unittest.TestCase):
    def test_selection_requires_buyer_or_works_semantics(self) -> None:
        self.assertTrue(is_procurement_event("Desktop Computer i5 (၄၅) စုံ ဝယ်ယူရန် အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"))
        self.assertTrue(is_procurement_event("ISO Lab အကြီးစားပြင်ဆင်ခြင်းလုပ်ငန်းအတွက် အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"))
        self.assertFalse(is_procurement_event("တင်ဒါအောင်စာရင်းထုတ်ပြန်ခြင်း"))
        self.assertFalse(is_procurement_event("ဆီအုန်းစိုက်ခင်းလုပ်ငန်းအား အိတ်ဖွင့်တင်ဒါဖြင့် ရောင်းချခြင်း"))
        self.assertFalse(is_procurement_event("အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"))

    def test_listing_selects_native_article_ids_and_visible_dates(self) -> None:
        rows = parse_tender_records(LISTING)
        self.assertEqual([row.article_id for row in rows], ["574", "560", "558", "573", "559", "333"])
        self.assertEqual(rows[0].canonical_key, "doa:574")
        self.assertEqual(rows[0].publication_date, "2026-05-18")
        self.assertIsNone(rows[0].deadline)
        desktop = next(row for row in rows if row.article_id == "560")
        self.assertIn("Desktop Computer i5 (၄၅) စုံ", desktop.title)
        hplc = next(row for row in rows if row.article_id == "573")
        self.assertIn("HPLC (with PDA-Detector)", hplc.title)
        payload = hplc.payload()
        self.assertEqual(payload["publication_date_evidence"], "LISTING_VISIBLE_ARTICLE_DATE")
        self.assertEqual(payload["deadline_evidence"], "UNKNOWN_IN_IMAGE_SUPPLEMENT_NOT_PARSED")
        self.assertEqual(payload["supplementary_image_policy"], "UNFETCHED_NON_BLOCKING")
        self.assertEqual(payload["reference_no_kind"], "issuer_article_id")
        malformed = LISTING.replace(
            "ISO Lab အကြီးစားပြင်ဆင်ခြင်းလုပ်ငန်းအတွက် အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း".encode(),
            "ISO Lab အကြီးစားပြင်ဆင်ခြင်းလုပ်ငန်းအတွက် အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း\"".encode(),
        )
        fixed = next(row for row in parse_tender_records(malformed) if row.article_id == "559")
        self.assertFalse(fixed.title.endswith('\"'))

    def test_listing_fails_closed_on_structural_drift_and_allows_valid_no_match_board(self) -> None:
        with self.assertRaisesRegex(DoaParseError, "listing structure"):
            parse_tender_records(b"<html><body>changed</body></html>")
        board = b'<div class="article-layout article-list col-xs-12"><div><span class="article-date">Mon, 1 June 2026</span><div class="article-title"><a href="https://www.doa.gov.mm/doa/index.php?route=cms/article&amp;path=22&amp;article_id=999">General announcement</a></div></div></div>'
        self.assertEqual(parse_tender_records(board), [])


class DoaEngineTests(unittest.TestCase):
    def test_baseline_and_second_poll_are_single_fetch_signal_free_and_image_free(self) -> None:
        registry = _registry()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            first_fetcher = SinglePageFetcher(LISTING)
            first = run_source(
                "S36", registry=registry, now=datetime(2026, 9, 7, 13, 30, tzinfo=UTC),
                fetcher=first_fetcher, force=True, database=db, evidence=evidence,
                worker_context={"run_id": "doa-baseline"},
            )
            self.assertTrue(first["baseline"])
            self.assertTrue(first["listing_complete"])
            self.assertEqual(first["items"], 6)
            self.assertEqual(first["tenders"], 6)
            self.assertEqual(first["details_attempted"], 0)
            self.assertEqual(first["changed"], 6)
            self.assertEqual(first["signals_created"], 0)
            self.assertEqual(first_fetcher.calls, [DOA_ANNOUNCEMENTS_URL])

            second_fetcher = SinglePageFetcher(LISTING)
            second = run_source(
                "S36", registry=registry, now=datetime(2026, 9, 7, 13, 31, tzinfo=UTC),
                fetcher=second_fetcher, force=True, database=db, evidence=evidence,
                worker_context={"run_id": "doa-second"},
            )
            self.assertFalse(second["baseline"])
            self.assertEqual(second["items"], 6)
            self.assertEqual(second["details_attempted"], 0)
            self.assertEqual(second["changed"], 0)
            self.assertEqual(second["signals_created"], 0)
            self.assertEqual(second_fetcher.calls, [DOA_ANNOUNCEMENTS_URL])

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S36'").fetchone()[0], 6)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S36'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S36'").fetchone()[0], 2)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM discovery_items WHERE source_id='S36'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT publication_date,deadline FROM canonical_items WHERE canonical_key='doa:560'").fetchone(), ("2026-05-18", None))
                self.assertEqual(tuple(conn.execute(q).fetchone()[0] for q in [
                    "SELECT COUNT(*) FROM acquisition_requests WHERE source_id='S36'",
                    "SELECT COUNT(*) FROM acquisition_attempts WHERE source_id='S36'",
                    "SELECT COUNT(*) FROM processing_records WHERE source_id='S36'",
                ]), (2, 2, 2))


if __name__ == "__main__":
    unittest.main()
