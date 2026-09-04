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
from signalforge.customs_announcements import (
    CustomsAnnouncementParseError,
    is_auction_notice,
    parse_auction_records,
    parse_visible_publication_date,
)
from signalforge.engine import run_source


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://customs.gov.mm/Announcements"


class SinglePageFetcher:
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
    source = raw["sources"]["S08A"]
    raw["sources"] = {"S08A": source}
    return Registry(raw)


class CustomsAnnouncementParserTests(unittest.TestCase):
    def test_visible_publication_date_is_authoritative_not_stale_datetime_attribute(self) -> None:
        self.assertEqual(parse_visible_publication_date("Friday August 21, 2026"), "2026-08-21")
        self.assertEqual(parse_visible_publication_date("August 21, 2026"), "2026-08-21")
        self.assertIsNone(parse_visible_publication_date("2025-05-13T10:03:13+00:00"))

    def test_auction_selection_excludes_tender_award_result(self) -> None:
        self.assertTrue(is_auction_notice("လေလံတင်ရောင်းချရေးကြော်ငြာ"))
        self.assertFalse(is_auction_notice("တင်ဒါအောင်မြင်ကြောင်းကြေညာခြင်း"))

    def test_current_listing_shape_yields_four_auction_items_and_encodes_pdf_paths(self) -> None:
        rows = parse_auction_records((FIXTURES / "customs_announcements.html").read_bytes())
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row.item_kind == "AUCTION_NOTICE" for row in rows))
        self.assertEqual([row.publication_date for row in rows], ["2026-08-21", "2026-08-21", "2026-08-15", "2026-08-08"])
        self.assertTrue(all("2025-05-13" not in row.canonical_key for row in rows))
        self.assertTrue(all(row.attachment_url.startswith("https://customs.gov.mm/admin/storage/files/") for row in rows))
        self.assertIn("%20", rows[-1].attachment_url)
        self.assertNotIn(" ", rows[-1].attachment_url)
        self.assertEqual(rows[0].payload()["reference_no_kind"], "issuer_archive_record_fingerprint")

    def test_parser_fails_closed_without_selected_auction(self) -> None:
        html = b'<article><h2 class="entry-title"><a href="x.pdf">Other</a></h2></article>'
        with self.assertRaises(CustomsAnnouncementParseError):
            parse_auction_records(html)


class CustomsAnnouncementEngineTests(unittest.TestCase):
    def test_auction_baseline_is_single_fetch_signal_free_and_pdf_is_not_fetched(self) -> None:
        listing = (FIXTURES / "customs_announcements.html").read_bytes()
        registry = _registry()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            fetcher = SinglePageFetcher(listing)
            result = run_source(
                "S08A",
                registry=registry,
                now=datetime(2026, 9, 4, 5, 30, tzinfo=UTC),
                fetcher=fetcher,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "customs-auction-baseline"},
            )
            self.assertTrue(result["baseline"])
            self.assertTrue(result["listing_complete"])
            self.assertEqual(result["items"], 4)
            self.assertEqual(result["tenders"], 0)
            self.assertEqual(result["details_attempted"], 0)
            self.assertEqual(result["changed"], 4)
            self.assertEqual(result["signals_created"], 0)
            self.assertEqual(fetcher.calls, [LIST_URL])

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S08A'").fetchone()[0], 4)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S08A'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM discovery_items WHERE source_id='S08A'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S08A' AND lower(requested_url) LIKE '%.pdf%'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT item_kind,COUNT(*) FROM canonical_items WHERE source_id='S08A' GROUP BY item_kind").fetchone(), ("AUCTION_NOTICE", 4))
                self.assertEqual(conn.execute("SELECT details_attempted,tenders_parsed,items_parsed FROM scheduler_runs WHERE source_id='S08A'").fetchone(), (0, 0, 4))

            with patch.dict(os.environ, {"SIGNALFORGE_DB": str(db), "SIGNALFORGE_REPO_ROOT": str(ROOT)}, clear=False):
                health = status(now=datetime(2026, 9, 4, 5, 31, tzinfo=UTC), registry=registry)
            source_health = health["sources"][0]["health"]
            self.assertEqual(source_health["parse_sample_source"], "BUSINESS_PROCESSING")
            self.assertEqual(source_health["parse_attempts"], 1)
            self.assertEqual(source_health["parse_successes"], 1)
            self.assertEqual(source_health["parse_health"], "GREEN")


if __name__ == "__main__":
    unittest.main()
