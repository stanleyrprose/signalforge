from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.mte import MTE_ANNOUNCEMENTS_URL, MteParseError, is_procurement_event, parse_tender_records

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class SinglePageFetcher:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url != MTE_ANNOUNCEMENTS_URL:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.payload


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S32"]
    raw["sources"] = {"S32": source}
    return Registry(raw)


class MteParserTests(unittest.TestCase):
    def test_selection_requires_procurement_semantics_not_tender_word_alone(self) -> None:
        self.assertTrue(is_procurement_event("ဝန်ဆောင်မှုရယူရန် တင်ဒါခေါ်ယူခြင်း"))
        self.assertTrue(is_procurement_event("Diesel ဝယ်ယူလိုပါ၍ Open Tender ပေးသွင်းရန်ဖိတ်ခေါ်အပ်ပါသည်"))
        self.assertFalse(is_procurement_event("TENTATIVE PROGRAMME FOR OPEN TENDER SALES 2025-2026"))
        self.assertFalse(is_procurement_event("အိတ်ဖွင့်တင်ဒါ ခေါ်ယူခြင်း"))

    def test_archive_selects_only_two_strong_procurement_records(self) -> None:
        rows = parse_tender_records((FIXTURES / "mte_announcements.html").read_bytes())
        self.assertEqual([row.article_id for row in rows], ["1600", "1415"])
        current = rows[0]
        self.assertEqual(current.canonical_key, "mte:1600")
        self.assertEqual(current.reference_no, "၁/၂၆-၂၇")
        self.assertIn("ဝန်ဆောင်မှုရယူရန်", current.title)
        self.assertIsNone(current.publication_date)
        self.assertIsNone(current.deadline)
        payload = current.payload()
        self.assertEqual(payload["publication_date_evidence"], "UNKNOWN_NOT_EXPOSED_IN_ARCHIVE_HTML")
        self.assertEqual(payload["deadline_evidence"], "UNKNOWN_IN_IMAGE_SUPPLEMENT_NOT_PARSED")
        self.assertEqual(payload["supplementary_image_policy"], "UNFETCHED_NON_BLOCKING")
        self.assertEqual(rows[1].reference_no, "MTE-ARTICLE-1415")

    def test_structural_drift_fails_closed_and_valid_sale_only_archive_is_empty(self) -> None:
        with self.assertRaisesRegex(MteParseError, "archive structure"):
            parse_tender_records(b"<html><body>changed</body></html>")
        sale_only = b'''<div class="item column-1"><p>Open Tender Sale</p><div><a class="readmore-link" href="/index.php/en/annoucements/99-sale">Read more...</a></div></div>'''
        self.assertEqual(parse_tender_records(sale_only), [])


class MteEngineTests(unittest.TestCase):
    def test_baseline_is_one_archive_fetch_signal_free_and_never_fetches_images_or_detail(self) -> None:
        listing = (FIXTURES / "mte_announcements.html").read_bytes()
        registry = _registry()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            fetcher = SinglePageFetcher(listing)
            result = run_source(
                "S32",
                registry=registry,
                now=datetime(2026, 9, 7, 6, 0, tzinfo=UTC),
                fetcher=fetcher,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "mte-baseline"},
            )
            self.assertTrue(result["baseline"])
            self.assertTrue(result["listing_complete"])
            self.assertEqual(result["items"], 2)
            self.assertEqual(result["tenders"], 2)
            self.assertEqual(result["details_attempted"], 0)
            self.assertEqual(result["changed"], 2)
            self.assertEqual(result["signals_created"], 0)
            self.assertEqual(fetcher.calls, [MTE_ANNOUNCEMENTS_URL])

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S32'").fetchone()[0], 2)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S32'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S32'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM discovery_items WHERE source_id='S32'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT details_attempted,tenders_parsed,items_parsed FROM scheduler_runs WHERE source_id='S32'").fetchone(), (0, 2, 2))
                self.assertEqual(conn.execute("SELECT publication_date,deadline FROM canonical_items WHERE canonical_key='mte:1600'").fetchone(), (None, None))


if __name__ == "__main__":
    unittest.main()
