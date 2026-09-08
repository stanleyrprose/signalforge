from __future__ import annotations

import re
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.mol import (
    MolParseError,
    extract_tender_pdf_urls,
    parse_detail_metadata,
    parse_tender_detail_with_attachments,
    parse_tender_listing,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://www.mol.gov.mm/tender/"


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _detail_url(record_id: int) -> str:
    text = _fixture(f"mol-{record_id}.html").decode("utf-8", errors="ignore")
    match = re.search(r'<link rel="canonical" href="([^"]+)"', text)
    if match is None:
        match = re.search(r'<meta property="og:url" content="([^"]+)"', text)
    assert match is not None
    return match.group(1)


class MolParserTests(unittest.TestCase):
    def test_current_page1_is_healthy_but_contains_no_opportunity_stage_rows(self) -> None:
        self.assertEqual(parse_tender_listing(_fixture("mol-tenders.html")), [])

    def test_historical_page2_fixture_selects_only_open_opportunities(self) -> None:
        entries = parse_tender_listing(_fixture("mol-tenders-page2.html"))
        self.assertEqual(len(entries), 4)
        self.assertEqual([entry.lastmod[:10] for entry in entries], ["2026-06-25", "2026-06-19", "2026-06-02", "2026-06-01"])
        urls = "\n".join(entry.url for entry in entries)
        self.assertIn("%E1%81%82%E1%81%80%E1%81%82%E1%81%86", urls)
        self.assertNotIn("?_page=", urls)

    def test_smart_id_pdf_extracts_post_identity_scope_and_pm_deadline(self) -> None:
        url = _detail_url(43883)
        html = _fixture("mol-43883.html")
        metadata = parse_detail_metadata(html, url)
        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertEqual(metadata.post_id, "43883")
        self.assertEqual(metadata.publication_date, "2026-06-25")
        self.assertNotIn("ကြော်ငြာ", metadata.pdf_url)
        self.assertIn("Card%E1%80%80%E1%80%BC%E1%80%B1", metadata.pdf_url)
        self.assertEqual(extract_tender_pdf_urls(html, url), [metadata.pdf_url])
        parsed = parse_tender_detail_with_attachments(html, url, [(metadata.pdf_url, _fixture("mol-43883.pdf"))])
        self.assertEqual(len(parsed), 1)
        tender = parsed[0]
        self.assertEqual(tender.canonical_key, "mol:43883")
        self.assertEqual(tender.reference_no, "MOL-POST-43883")
        self.assertEqual(tender.deadline, "2026-07-14")
        self.assertEqual(tender.deadline_time, "16:30")
        self.assertIn("Smart ID Card Printing", tender.scope_summary)
        self.assertEqual(tender.payload()["business_stage"], "OPPORTUNITY")

    def test_medical_equipment_pdf_extracts_items_and_deadline(self) -> None:
        url = _detail_url(43840)
        html = _fixture("mol-43840.html")
        metadata = parse_detail_metadata(html, url)
        assert metadata is not None
        parsed = parse_tender_detail_with_attachments(html, url, [(metadata.pdf_url, _fixture("mol-43840.pdf"))])
        self.assertEqual(len(parsed), 1)
        tender = parsed[0]
        self.assertEqual(tender.canonical_key, "mol:43840")
        self.assertEqual(tender.deadline, "2026-07-13")
        self.assertEqual(tender.deadline_time, "16:30")
        self.assertIn("Electric High Speed Drill", tender.scope_summary)
        self.assertIn("Fibroscan", tender.scope_summary)
        self.assertEqual(tender.business_unit, "Social Security Board")

    def test_attachment_mismatch_and_non_pdf_fail_closed(self) -> None:
        url = _detail_url(43840)
        html = _fixture("mol-43840.html")
        metadata = parse_detail_metadata(html, url)
        assert metadata is not None
        with self.assertRaises(MolParseError):
            parse_tender_detail_with_attachments(html, url, [("https://www.mol.gov.mm/wp-content/uploads/wrong.pdf", _fixture("mol-43840.pdf"))])
        with self.assertRaises(MolParseError):
            parse_tender_detail_with_attachments(html, url, [(metadata.pdf_url, b"not-pdf")])
        self.assertIsNone(parse_detail_metadata(html, f"{url}?x=1"))


class MolEngineTests(unittest.TestCase):
    def test_current_page1_zero_opportunity_baseline_is_success_not_parser_failure(self) -> None:
        registry = Registry.load(ROOT)
        calls: list[str] = []

        def fetcher(url: str, **_kwargs) -> bytes:
            calls.append(url)
            if url != LIST_URL:
                raise AssertionError(f"unexpected fetch: {url}")
            return _fixture("mol-tenders.html")

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            database = base / "signalforge.db"
            result = run_source(
                "S40",
                registry=registry,
                now=datetime(2026, 9, 8, 16, 30, tzinfo=UTC),
                fetcher=fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=database,
                evidence=base / "evidence",
                worker_context={"run_id": "mol-zero-baseline"},
            )
            self.assertEqual(result["status"], "SUCCESS")
            self.assertTrue(result["baseline"])
            self.assertEqual(result["discovered"], 0)
            self.assertEqual(result["candidates"], 0)
            self.assertEqual(result["details_attempted"], 0)
            self.assertEqual(result["changed"], 0)
            self.assertEqual(result["signals_created"], 0)
            self.assertEqual(result["backlog_remaining"], 0)
            self.assertEqual(calls, [LIST_URL])
            with sqlite3.connect(database) as conn:
                canonical = conn.execute("select count(*) from canonical_items where source_id='S40'").fetchone()[0]
                signals = conn.execute("select count(*) from signals where source_id='S40'").fetchone()[0]
                target_counts = dict(conn.execute("select target_kind,count(*) from acquisition_requests where source_id='S40' group by target_kind"))
                evidence = conn.execute("select count(*) from evidence_envelopes where source_id='S40'").fetchone()[0]
                processing = conn.execute("select count(*) from processing_records where source_id='S40' and status='SUCCESS'").fetchone()[0]
            self.assertEqual(canonical, 0)
            self.assertEqual(signals, 0)
            self.assertEqual(target_counts, {"DISCOVERY": 1})
            self.assertEqual(evidence, 1)
            self.assertEqual(processing, 1)


if __name__ == "__main__":
    unittest.main()
