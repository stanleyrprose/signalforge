from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.mofa import (
    MOFA_LIST_URL,
    MofaParseError,
    extract_tender_pdf_urls,
    parse_tender_detail,
    parse_tender_detail_with_attachments,
    parse_tender_listing,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LISTING = (FIXTURES / "mofa_announcement_list.html").read_bytes()
ENTRIES = parse_tender_listing(LISTING)
URL_59800 = ENTRIES[0].url
URL_56952 = ENTRIES[1].url


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
    raw["sources"] = {"S30": raw["sources"]["S30"]}
    return Registry(raw)


class MofaParserTests(unittest.TestCase):
    def test_listing_selects_open_tenders_and_excludes_award_and_jobs(self) -> None:
        entries = parse_tender_listing(LISTING)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[0].url.endswith("-386/"))
        self.assertEqual(entries[0].lastmod, "2026-09-04T13:11:15+06:30")
        self.assertTrue(entries[1].url.endswith("-353/"))
        self.assertEqual(entries[1].lastmod, "2026-06-23T16:16:07+06:30")

    def test_listing_fails_closed_when_announcement_shape_disappears(self) -> None:
        with self.assertRaises(MofaParseError):
            parse_tender_listing(b"<html><body><article class='post'>News</article></body></html>")

    def test_latest_detail_uses_post_id_html_scope_and_pdf_metadata_only(self) -> None:
        tender = parse_tender_detail((FIXTURES / "mofa_tender_59800.html").read_bytes(), URL_59800)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "mofa:59800")
        self.assertEqual(tender.reference_no, "MOFA-POST-59800")
        self.assertEqual(tender.publication_date, "2026-09-04")
        self.assertIsNone(tender.deadline)
        self.assertIn("မြန်မာကျပ်ငွေဖြင့် ဝယ်ယူ", tender.scope_summary or "")
        self.assertEqual(tender.attachment_name, "Tender-Announcement.pdf")
        self.assertTrue((tender.attachment_url or "").endswith("/Tender-Announcement.pdf"))
        self.assertEqual(tender.payload()["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")
        self.assertEqual(tender.payload()["deadline_evidence"], "UNKNOWN_NOT_IN_HTML_TEXT")

    def test_latest_pdf_enriches_current_ict_opportunity_scope_and_deadline(self) -> None:
        html = (FIXTURES / "mofa_tender_59800.html").read_bytes()
        pdf = (FIXTURES / "mofa_tender_59800.pdf").read_bytes()
        urls = extract_tender_pdf_urls(html, URL_59800)
        self.assertEqual(len(urls), 1)
        parsed = parse_tender_detail_with_attachments(html, URL_59800, [(urls[0], pdf)])
        self.assertEqual(len(parsed), 1)
        tender = parsed[0]
        self.assertEqual(tender.canonical_key, "mofa:59800")
        self.assertEqual(tender.deadline, "2026-09-18")
        self.assertEqual(tender.deadline_time, "16:30")
        self.assertIn("PowerEdge R750-XS", tender.scope_summary or "")
        self.assertIn("Windows Server 2025 Standard", tender.scope_summary or "")
        self.assertIn("Microsoft SQL Server 2022 Standard", tender.scope_summary or "")
        self.assertEqual(tender.payload()["attachment_policy"], "OPTIONAL_TEXT_PDF_ENRICHMENT")
        self.assertEqual(tender.payload()["deadline_evidence"], "OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME")

    def test_older_detail_accepts_official_image_metadata_without_ocr(self) -> None:
        tender = parse_tender_detail((FIXTURES / "mofa_tender_56952.html").read_bytes(), URL_56952)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "mofa:56952")
        self.assertEqual(tender.publication_date, "2026-06-23")
        self.assertTrue((tender.attachment_url or "").lower().endswith(".jpg"))
        self.assertIn("Lot (၇) ခု", tender.scope_summary or "")


class MofaEngineTests(unittest.TestCase):
    def test_baseline_fetches_optional_pdf_and_probe_updates_same_post(self) -> None:
        registry = _registry()
        detail_59800 = (FIXTURES / "mofa_tender_59800.html").read_bytes()
        detail_56952 = (FIXTURES / "mofa_tender_56952.html").read_bytes()
        pdf_59800 = (FIXTURES / "mofa_tender_59800.pdf").read_bytes()
        pdf_url = extract_tender_pdf_urls(detail_59800, URL_59800)[0]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            first_fetcher = MapFetcher({MOFA_LIST_URL: LISTING, URL_59800: detail_59800, pdf_url: pdf_59800, URL_56952: detail_56952})
            first = run_source(
                "S30", registry=registry, now=datetime(2026, 9, 6, 8, 0, tzinfo=UTC),
                fetcher=first_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "mofa-baseline"},
            )
            self.assertTrue(first["baseline"])
            self.assertEqual(first["details_attempted"], 2)
            self.assertEqual(first["details_succeeded"], 2)
            self.assertEqual(first["tenders"], 2)
            self.assertEqual(first["signals_created"], 0)
            self.assertEqual(first_fetcher.calls, [MOFA_LIST_URL, URL_59800, pdf_url, URL_56952])

            changed = detail_59800.replace("အောက်ပါပစ္စည်းများအား".encode(), "အောက်ပါပစ္စည်းအသစ်များအား".encode(), 1)
            second_fetcher = MapFetcher({MOFA_LIST_URL: LISTING, URL_59800: changed, pdf_url: pdf_59800})
            second = run_source(
                "S30", registry=registry, now=datetime(2026, 9, 6, 10, 1, tzinfo=UTC),
                fetcher=second_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "mofa-probe"},
            )
            self.assertFalse(second["baseline"])
            self.assertTrue(second["health_probe"])
            self.assertEqual(second["details_attempted"], 1)
            self.assertEqual(second["details_succeeded"], 1)
            self.assertEqual(second["changed"], 1)
            self.assertEqual(second["signals_created"], 1)
            self.assertEqual(second_fetcher.calls, [MOFA_LIST_URL, URL_59800, pdf_url])

            with sqlite3.connect(db) as conn:
                canonical = conn.execute("SELECT count(*) FROM canonical_items WHERE source_id='S30'").fetchone()[0]
                signal = conn.execute("SELECT signal_type,canonical_key FROM signals WHERE source_id='S30'").fetchone()
                lifecycle = tuple(conn.execute(q).fetchone()[0] for q in [
                    "SELECT count(*) FROM acquisition_requests WHERE source_id='S30'",
                    "SELECT count(*) FROM acquisition_attempts WHERE source_id='S30'",
                    "SELECT count(*) FROM evidence_envelopes WHERE source_id='S30'",
                    "SELECT count(*) FROM processing_records WHERE source_id='S30'",
                ])
                attachment_fetches = conn.execute(
                    "SELECT count(*) FROM evidence_envelopes WHERE source_id='S30' AND (lower(requested_url) LIKE '%.pdf%' OR lower(requested_url) LIKE '%.jpg%')"
                ).fetchone()[0]
            self.assertEqual(canonical, 2)
            self.assertEqual(signal, ("UPDATED", "mofa:59800"))
            self.assertEqual(lifecycle, (7, 7, 7, 5))
            self.assertEqual(attachment_fetches, 2)

    def test_optional_pdf_fetch_failure_falls_back_to_html_metadata(self) -> None:
        registry = _registry()
        detail_59800 = (FIXTURES / "mofa_tender_59800.html").read_bytes()
        detail_56952 = (FIXTURES / "mofa_tender_56952.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            fetcher = MapFetcher({MOFA_LIST_URL: LISTING, URL_59800: detail_59800, URL_56952: detail_56952})
            result = run_source(
                "S30", registry=registry, now=datetime(2026, 9, 6, 8, 0, tzinfo=UTC),
                fetcher=fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "mofa-optional-pdf-fallback"},
            )
            self.assertEqual(result["status"], "SUCCESS")
            self.assertEqual(result["details_attempted"], 2)
            self.assertEqual(result["details_succeeded"], 2)
            self.assertEqual(result["detail_errors"], 0)
            with sqlite3.connect(db) as conn:
                row = conn.execute("SELECT deadline,payload_json FROM canonical_items WHERE canonical_key='mofa:59800'").fetchone()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertIsNone(row[0])
            self.assertEqual(json.loads(row[1])["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")


if __name__ == "__main__":
    unittest.main()
