from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.dast import DAST_LIST_URL, DastParseError, parse_tender_detail, parse_tender_listing
from signalforge.engine import run_source

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LISTING = (FIXTURES / "dast_tender_list.html").read_bytes()
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
    raw["sources"] = {"S35": raw["sources"]["S35"]}
    return Registry(raw)


class DastParserTests(unittest.TestCase):
    def test_listing_uses_native_post_ids_and_rewrites_legacy_host(self) -> None:
        entries = parse_tender_listing(LISTING)
        self.assertEqual(len(entries), 3)
        self.assertEqual([e.url for e in entries], [
            "https://www.dast.gov.mm/?p=2631",
            "https://www.dast.gov.mm/?p=2625",
            "https://www.dast.gov.mm/?p=2595",
        ])
        self.assertEqual(entries[0].lastmod, "2026-08-06T00:00:00+06:30")
        self.assertFalse(any("dast.edu.mm" in e.url for e in entries))

    def test_listing_fails_closed_when_tender_article_shape_disappears(self) -> None:
        with self.assertRaisesRegex(DastParseError, "tender archive article structure"):
            parse_tender_listing(b"<html><body><article class='post'>news</article></body></html>")

    def test_qa_qc_detail_uses_wordpress_id_scope_deadline_and_rewritten_attachment(self) -> None:
        tender = parse_tender_detail((FIXTURES / "dast_tender_2631.html").read_bytes(), ENTRIES[0].url)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "dast:2631")
        self.assertEqual(tender.reference_no, "DAST-POST-2631")
        self.assertEqual(tender.publication_date, "2026-08-06")
        self.assertEqual(tender.deadline, "2026-08-14")
        self.assertIn("Polytechnic University (မြစ်ကြီးနား)", tender.scope_summary)
        self.assertIn("Kyaing Tong", tender.scope_summary)
        self.assertIn("Lot-2", tender.scope_summary)
        self.assertNotIn("SHOULD NOT ENTER", tender.scope_summary)
        self.assertEqual(len(tender.attachment_urls), 1)
        self.assertTrue(tender.attachment_urls[0].startswith("https://www.dast.gov.mm/wp-content/uploads/"))
        self.assertEqual(tender.payload()["deadline_evidence"], "EXPLICIT_HTML_SUBMISSION_DATE")
        self.assertEqual(tender.payload()["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")

    def test_construction_range_uses_latest_explicit_submission_date(self) -> None:
        tender = parse_tender_detail((FIXTURES / "dast_tender_2625.html").read_bytes(), ENTRIES[1].url)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "dast:2625")
        self.assertEqual(tender.deadline, "2026-07-21")
        self.assertIn("တည်ဆောက်ရေးလုပ်ငန်း (၆) ခု", tender.scope_summary)

    def test_reference_book_accepts_https_and_http_legacy_attachment_metadata(self) -> None:
        tender = parse_tender_detail((FIXTURES / "dast_tender_2595.html").read_bytes(), ENTRIES[2].url)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.deadline, "2026-05-22")
        self.assertEqual(len(tender.attachment_urls), 2)
        self.assertTrue(all(url.startswith("https://www.dast.gov.mm/") for url in tender.attachment_urls))
        self.assertIn("Reference Book", tender.scope_summary)

    def test_detail_fails_closed_on_post_id_mismatch(self) -> None:
        self.assertIsNone(parse_tender_detail((FIXTURES / "dast_tender_2631.html").read_bytes(), ENTRIES[1].url))


class DastEngineTests(unittest.TestCase):
    def test_baseline_and_second_poll_do_not_fetch_pdf_or_repeat_unchanged_details(self) -> None:
        registry = _registry()
        details = [
            (FIXTURES / "dast_tender_2631.html").read_bytes(),
            (FIXTURES / "dast_tender_2625.html").read_bytes(),
            (FIXTURES / "dast_tender_2595.html").read_bytes(),
        ]
        first_payloads = {DAST_LIST_URL: LISTING, **{entry.url: detail for entry, detail in zip(ENTRIES, details)}}
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            first_fetcher = MapFetcher(first_payloads)
            first = run_source(
                "S35", registry=registry, now=datetime(2026, 9, 7, 11, 30, tzinfo=UTC),
                fetcher=first_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "dast-baseline"},
            )
            self.assertTrue(first["baseline"])
            self.assertEqual(first["details_attempted"], 3)
            self.assertEqual(first["details_succeeded"], 3)
            self.assertEqual(first["tenders"], 3)
            self.assertEqual(first["changed"], 3)
            self.assertEqual(first["signals_created"], 0)
            self.assertEqual(first_fetcher.calls, [DAST_LIST_URL, *[entry.url for entry in ENTRIES]])

            second_fetcher = MapFetcher({DAST_LIST_URL: LISTING})
            second = run_source(
                "S35", registry=registry, now=datetime(2026, 9, 7, 11, 31, tzinfo=UTC),
                fetcher=second_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "dast-second"},
            )
            self.assertFalse(second["baseline"])
            self.assertEqual(second["details_attempted"], 0)
            self.assertEqual(second["changed"], 0)
            self.assertEqual(second["signals_created"], 0)
            self.assertEqual(second_fetcher.calls, [DAST_LIST_URL])

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S35'").fetchone()[0], 3)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S35'").fetchone()[0], 0)
                lifecycle = tuple(conn.execute(q).fetchone()[0] for q in [
                    "SELECT COUNT(*) FROM acquisition_requests WHERE source_id='S35'",
                    "SELECT COUNT(*) FROM acquisition_attempts WHERE source_id='S35'",
                    "SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S35'",
                    "SELECT COUNT(*) FROM processing_records WHERE source_id='S35'",
                ])
                pdf_evidence = conn.execute(
                    "SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S35' AND lower(requested_url) LIKE ?", ("%.pdf%",)
                ).fetchone()[0]
            self.assertEqual(lifecycle, (5, 5, 5, 5))
            self.assertEqual(pdf_evidence, 0)


if __name__ == "__main__":
    unittest.main()
