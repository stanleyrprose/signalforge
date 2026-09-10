from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.ptd import (
    PTD_LIST_URL,
    PtdParseError,
    extract_tender_pdf_urls,
    parse_tender_detail,
    parse_tender_detail_with_attachments,
    parse_tender_listing,
)

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
        self.assertEqual(tender.payload()["attachment_policy"], "SINGLE_TEXT_PDF_REQUIRED")
        self.assertTrue(tender.canonical_key.startswith("ptd:2026-07-31:"))

    def test_text_pdf_extracts_participation_close_and_opening_without_inventing_bid_deadline(self) -> None:
        html = (FIXTURES / "ptd_tender_spares.html").read_bytes()
        base = parse_tender_detail(html, ENTRIES[1].url)
        self.assertIsNotNone(base)
        assert base is not None
        pdf_text = """
        ၂။ တင်ဒါပုံစံစတင်ရောင်းချမည့်နေ့ - ၂၈ - ၇ - ၂၀၂၆ ရက်
        ၃။ တင်ဒါပုံစံအရောင်းပိတ်မည့်နေ့ - ၁၄ - ၈ - ၂၀၂၆ ရက်
        ၅။ တင်ဒါတင်သွင်းရမည့်နေရာ - ရုံးအမှတ်(၂)
        ၆။ တင်ဒါဖွင့်ဖောက်မည့်နေ့ရက်နှင့်အချိန် - ၁၈ - ၈ - ၂၀၂၆ ရက်
        (၁၀:၃၀)နာရီ
        """
        with patch("signalforge.ptd._extract_pdf_text", return_value=pdf_text):
            parsed = parse_tender_detail_with_attachments(
                html,
                ENTRIES[1].url,
                [(base.attachment_url or "", b"pdf")],
            )
        self.assertEqual(len(parsed), 1)
        tender = parsed[0]
        payload = tender.payload()
        self.assertEqual(payload["deadline"], "2026-08-14")
        self.assertIsNone(payload["deadline_time"])
        self.assertEqual(payload["deadline_kind"], "TENDER_FORM_SALE_CLOSE")
        self.assertEqual(payload["deadline_evidence"], "OFFICIAL_TEXT_NATIVE_PDF_TENDER_FORM_SALE_CLOSE_DATE")
        self.assertEqual(payload["tender_opening_date"], "2026-08-18")
        self.assertEqual(payload["tender_opening_time"], "10:30")
        self.assertEqual(payload["detail_completeness"], "HTML_EVENT_SCOPE_TEXT_PDF_PARTICIPATION_CLOSE")

    def test_text_pdf_schedule_stays_unknown_when_section_date_is_corrupt(self) -> None:
        html = (FIXTURES / "ptd_tender_spares.html").read_bytes()
        base = parse_tender_detail(html, ENTRIES[1].url)
        self.assertIsNotNone(base)
        assert base is not None
        corrupt = """
        ၃။ တင်ဒါပုံစံအရောင်းပိတ်မည့်နေ့ - ၁၁ - - ၂၀၂၆ ရက်
        ၆။ တင်ဒါဖွင့်ဖောက်မည့်နေ့ရက်နှင့်အချိန် - ၁ - - ၂၀၂၆ (၁၃: )
        """
        with patch("signalforge.ptd._extract_pdf_text", return_value=corrupt):
            tender = parse_tender_detail_with_attachments(
                html,
                ENTRIES[1].url,
                [(base.attachment_url or "", b"pdf")],
            )[0]
        payload = tender.payload()
        self.assertIsNone(payload["deadline"])
        self.assertIsNone(payload["tender_opening_date"])
        self.assertEqual(payload["deadline_evidence"], "UNKNOWN_IN_TEXT_NATIVE_PDF_SCHEDULE_UNREADABLE")
        self.assertEqual(payload["detail_completeness"], "HTML_EVENT_SCOPE_TEXT_PDF_SCHEDULE_UNREADABLE")

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
    def test_baseline_fetches_listing_four_details_and_required_pdfs_without_signals(self) -> None:
        registry = _registry()
        details = [
            (FIXTURES / "ptd_tender_earthquake.html").read_bytes(),
            (FIXTURES / "ptd_tender_spares.html").read_bytes(),
            (FIXTURES / "ptd_tender_bago.html").read_bytes(),
            (FIXTURES / "ptd_tender_dns.html").read_bytes(),
        ]
        payloads: dict[str, bytes] = {PTD_LIST_URL: LISTING}
        expected_calls = [PTD_LIST_URL]
        for entry, detail in zip(ENTRIES, details):
            attachment_url = extract_tender_pdf_urls(detail, entry.url)[0]
            payloads[entry.url] = detail
            payloads[attachment_url] = b"pdf"
            expected_calls.extend([entry.url, attachment_url])
        pdf_text = """
        ၃။ တင်ဒါပုံစံအရောင်းပိတ်မည့်နေ့ - ၃၀ - ၉ - ၂၀၂၆ ရက်
        ၆။ တင်ဒါဖွင့်ဖောက်မည့်နေ့ရက်နှင့်အချိန် - ၁ - ၁၀ - ၂၀၂၆ ရက်
        (၁၃:၃၀)နာရီ
        """
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.ptd._extract_pdf_text", return_value=pdf_text):
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
            self.assertEqual(fetcher.calls, expected_calls)
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S34'").fetchone()[0], 4)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S34'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S34'").fetchone()[0], 9)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S34' AND lower(requested_url) LIKE '%.pdf%'").fetchone()[0], 4)

    def test_initial_pdf_semantic_enrichment_updates_canonical_without_historical_signal(self) -> None:
        raw = json.loads(json.dumps(Registry.load(ROOT).raw))
        source = raw["sources"]["S34"]
        source["baseline_detail_limit"] = 1
        source["delta_detail_limit"] = 1
        registry = Registry({**raw, "sources": {"S34": source}})
        detail = (FIXTURES / "ptd_tender_earthquake.html").read_bytes()
        entry = ENTRIES[0]
        attachment_url = extract_tender_pdf_urls(detail, entry.url)[0]
        payloads = {PTD_LIST_URL: LISTING, entry.url: detail, attachment_url: b"pdf"}
        pdf_text = """
        ၃။ တင်ဒါပုံစံအရောင်းပိတ်မည့်နေ့ - ၂၀ - ၈ - ၂၀၂၆ ရက်
        ၆။ တင်ဒါဖွင့်ဖောက်မည့်နေ့ရက်နှင့်အချိန် - ၂၅ - ၈ - ၂၀၂၆ ရက်
        (၁၄:၃၀)နာရီ
        """
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.ptd._extract_pdf_text", return_value=pdf_text) as extract_pdf_text:
            base = Path(tmp)
            db = base / "signalforge.db"
            baseline = run_source(
                "S34", registry=registry, now=datetime(2026, 9, 7, 10, 0, tzinfo=UTC),
                fetcher=MapFetcher(payloads), sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "ptd-enrichment-baseline"},
            )
            self.assertEqual(baseline["signals_created"], 0)

            old = parse_tender_detail(detail, entry.url)
            self.assertIsNotNone(old)
            assert old is not None
            old_payload = old.payload()
            old_payload["attachment_policy"] = "METADATA_ONLY_NON_BLOCKING"
            with sqlite3.connect(db) as conn:
                canonical_key = conn.execute(
                    "SELECT canonical_key FROM discovery_items WHERE source_id='S34' AND url=?",
                    (entry.url,),
                ).fetchone()[0]
                conn.execute(
                    "UPDATE discovery_items SET content_hash=? WHERE source_id='S34' AND url=?",
                    ("previous-aspnet-dynamic-html-sha", entry.url),
                )
                conn.execute(
                    "UPDATE canonical_items SET content_hash='pre-pdf-semantic',payload_json=? WHERE canonical_key=?",
                    (json.dumps(old_payload, ensure_ascii=False), canonical_key),
                )
                conn.commit()

            probe = run_source(
                "S34", registry=registry, now=datetime(2026, 9, 7, 11, 1, tzinfo=UTC),
                fetcher=MapFetcher(payloads), sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "ptd-initial-pdf-enrichment"},
            )
            self.assertTrue(probe["health_probe"])
            self.assertEqual(probe["changed"], 1)
            self.assertEqual(probe["signals_created"], 0)
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S34'").fetchone()[0], 0)
                payload = json.loads(conn.execute(
                    "SELECT payload_json FROM canonical_items WHERE canonical_key=?", (canonical_key,)
                ).fetchone()[0])
            self.assertEqual(payload["deadline"], "2026-08-20")
            self.assertEqual(payload["deadline_kind"], "TENDER_FORM_SALE_CLOSE")

            extract_pdf_text.return_value = """
            ၃။ တင်ဒါပုံစံအရောင်းပိတ်မည့်နေ့ - ၂၁ - ၈ - ၂၀၂၆ ရက်
            ၆။ တင်ဒါဖွင့်ဖောက်မည့်နေ့ရက်နှင့်အချိန် - ၂၆ - ၈ - ၂၀၂၆ ရက်
            (၁၄:၃၀)နာရီ
            """
            changed_pdf = run_source(
                "S34", registry=registry, now=datetime(2026, 9, 7, 12, 2, tzinfo=UTC),
                fetcher=MapFetcher(payloads), sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "ptd-later-pdf-change"},
            )
            self.assertTrue(changed_pdf["health_probe"])
            self.assertEqual(changed_pdf["changed"], 1)
            self.assertEqual(changed_pdf["signals_created"], 1)
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S34'").fetchone()[0], 1)
                signal_type = conn.execute(
                    "SELECT signal_type FROM signals WHERE source_id='S34' ORDER BY created_at DESC LIMIT 1"
                ).fetchone()[0]
            self.assertEqual(signal_type, "UPDATED")


if __name__ == "__main__":
    unittest.main()
