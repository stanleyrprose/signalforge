from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.ptd import PTD_LIST_URL, PtdParseError, parse_tender_detail, parse_tender_listing

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LISTING = (FIXTURES / "ptd_tender_list.html").read_bytes()
ENTRIES = parse_tender_listing(LISTING)


class MapFetcher:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url not in self.payloads:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.payloads[url]


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    raw["sources"] = {"S34": raw["sources"]["S34"]}
    return Registry(raw)


class PtdParserTests(unittest.TestCase):
    def test_listing_selects_open_tenders_and_excludes_awards(self) -> None:
        entries = parse_tender_listing(LISTING)
        self.assertEqual(len(entries), 4)
        self.assertEqual(entries[0].lastmod, "2026-07-31T00:00:00+06:30")
        self.assertEqual(entries[1].lastmod, "2026-07-30T00:00:00+06:30")
        self.assertEqual(entries[2].lastmod, "2026-07-30T00:00:00+06:30")
        self.assertEqual(entries[3].lastmod, "2026-05-19T00:00:00+06:30")
        self.assertIn("%2F", entries[3].url)

    def test_listing_fails_closed_when_category_shape_disappears(self) -> None:
        with self.assertRaisesRegex(PtdParseError, "category table"):
            parse_tender_listing(b"<html><body>changed</body></html>")

    def test_detail_extracts_html_scope_and_pdf_metadata_only(self) -> None:
        tender = parse_tender_detail((FIXTURES / "ptd_tender_earthquake.html").read_bytes(), ENTRIES[0].url)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.publication_date, "2026-07-31")
        self.assertIsNone(tender.deadline)
        self.assertIn("ရေဒီယိုလှိုင်းနှုန်းတိုင်းတာရေးစနစ်", tender.scope_summary)
        self.assertTrue((tender.attachment_url or "").endswith("Earthquake%20Recovery%20Rules%2026-27.pdf"))
        self.assertEqual(tender.payload()["deadline_evidence"], "UNKNOWN_IN_PDF_ATTACHMENT_NOT_PARSED")
        self.assertEqual(tender.payload()["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")
        self.assertTrue(tender.canonical_key.startswith("ptd:2026-07-31:"))

    def test_same_day_generic_tenders_have_distinct_business_identity(self) -> None:
        spare = parse_tender_detail((FIXTURES / "ptd_tender_spares.html").read_bytes(), ENTRIES[1].url)
        bago = parse_tender_detail((FIXTURES / "ptd_tender_bago.html").read_bytes(), ENTRIES[2].url)
        self.assertIsNotNone(spare)
        self.assertIsNotNone(bago)
        assert spare is not None and bago is not None
        self.assertEqual(spare.publication_date, bago.publication_date)
        self.assertNotEqual(spare.canonical_key, bago.canonical_key)
        self.assertIn("Synthesizer for TCI RF monitoring System", spare.scope_summary)
        self.assertIn("ပဲခူး", bago.scope_summary)

    def test_dns_tender_preserves_high_value_scope(self) -> None:
        tender = parse_tender_detail((FIXTURES / "ptd_tender_dns.html").read_bytes(), ENTRIES[3].url)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertIn(".mm Root DNS System", tender.scope_summary)
        self.assertEqual(tender.publication_date, "2026-05-19")


class PtdEngineTests(unittest.TestCase):
    def test_baseline_fetches_listing_and_four_details_without_pdf(self) -> None:
        registry = _registry()
        details = [
            (FIXTURES / "ptd_tender_earthquake.html").read_bytes(),
            (FIXTURES / "ptd_tender_spares.html").read_bytes(),
            (FIXTURES / "ptd_tender_bago.html").read_bytes(),
            (FIXTURES / "ptd_tender_dns.html").read_bytes(),
        ]
        payloads = {PTD_LIST_URL: LISTING, **{entry.url: detail for entry, detail in zip(ENTRIES, details)}}
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            fetcher = MapFetcher(payloads)
            result = run_source(
                "S34", registry=registry, now=datetime(2026, 9, 7, 10, 0, tzinfo=UTC),
                fetcher=fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "ptd-baseline"},
            )
            self.assertTrue(result["baseline"])
            self.assertEqual(result["details_attempted"], 4)
            self.assertEqual(result["details_succeeded"], 4)
            self.assertEqual(result["tenders"], 4)
            self.assertEqual(result["changed"], 4)
            self.assertEqual(result["signals_created"], 0)
            self.assertEqual(fetcher.calls, [PTD_LIST_URL, *[entry.url for entry in ENTRIES]])
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S34'").fetchone()[0], 4)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S34'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S34'").fetchone()[0], 5)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S34' AND lower(requested_url) LIKE '%.pdf%'").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
