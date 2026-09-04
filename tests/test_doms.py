from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.doms import DomsParseError, parse_tender_detail, parse_tender_listing
from signalforge.engine import run_source

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://www.doms.gov.mm/category/tender/"
URL_12634 = "https://www.doms.gov.mm/2026/08/10/7dms-2026-2027l/"
URL_12491 = "https://www.doms.gov.mm/2026/07/09/open-tender-ct-mri/"


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
    raw["sources"] = {"S26": raw["sources"]["S26"]}
    return Registry(raw)


class DomsParserTests(unittest.TestCase):
    def test_listing_selects_opportunities_and_excludes_procurement_stages(self) -> None:
        entries = parse_tender_listing((FIXTURES / "doms_tender_list.html").read_bytes())
        self.assertEqual([entry.url for entry in entries], [URL_12634, URL_12491])
        self.assertEqual(entries[0].lastmod, "2026-08-10T00:00:00+06:30")
        self.assertEqual(entries[1].lastmod, "2026-07-09T00:00:00+06:30")

    def test_listing_fails_closed_when_wordpress_tender_shape_disappears(self) -> None:
        with self.assertRaises(DomsParseError):
            parse_tender_listing(b"<html><body><article class='post'>News</article></body></html>")

    def test_detail_uses_stable_post_id_dedupes_official_attachments_and_keeps_deadline_unknown(self) -> None:
        tender = parse_tender_detail((FIXTURES / "doms_tender_12634.html").read_bytes(), URL_12634)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "doms:12634")
        self.assertEqual(tender.reference_no, "7DMS/2026-2027(L)")
        self.assertEqual(tender.reference_no_kind, "issuer_tender_reference")
        self.assertEqual(tender.publication_date, "2026-08-10")
        self.assertIsNone(tender.deadline)
        self.assertEqual(len(tender.attachments), 2)
        self.assertEqual(tender.attachments[0][0], "18. Oncology Medicine")
        self.assertTrue(all("doms.gov.mm/wp-content/uploads/" in url for _name, url in tender.attachments))
        self.assertEqual(tender.payload()["deadline_evidence"], "UNKNOWN_NOT_IN_HTML_TEXT")
        self.assertEqual(tender.payload()["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")

    def test_detail_without_tender_reference_uses_post_id_and_html_scope(self) -> None:
        tender = parse_tender_detail((FIXTURES / "doms_tender_12491.html").read_bytes(), URL_12491)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "doms:12491")
        self.assertEqual(tender.reference_no, "DOMS-POST-12491")
        self.assertEqual(tender.reference_no_kind, "wordpress_post_id")
        self.assertIn("CT (Computed Tomography)", tender.scope_summary or "")
        self.assertIn("Preventive Maintenance", tender.scope_summary or "")
        self.assertEqual(tender.attachments, ())


class DomsEngineTests(unittest.TestCase):
    def test_baseline_is_signal_free_pdf_is_never_fetched_and_health_probe_updates_same_post(self) -> None:
        registry = _registry()
        listing = (FIXTURES / "doms_tender_list.html").read_bytes()
        detail_12634 = (FIXTURES / "doms_tender_12634.html").read_bytes()
        detail_12491 = (FIXTURES / "doms_tender_12491.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            first_fetcher = MapFetcher({LIST_URL: listing, URL_12634: detail_12634, URL_12491: detail_12491})
            first = run_source(
                "S26", registry=registry, now=datetime(2026, 9, 4, 10, 0, tzinfo=UTC),
                fetcher=first_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "doms-baseline"},
            )
            self.assertTrue(first["baseline"])
            self.assertEqual(first["details_attempted"], 2)
            self.assertEqual(first["details_succeeded"], 2)
            self.assertEqual(first["tenders"], 2)
            self.assertEqual(first["signals_created"], 0)
            self.assertEqual(first_fetcher.calls, [LIST_URL, URL_12634, URL_12491])

            changed_12634 = detail_12634.replace(b"18. Oncology Medicine", b"18. Oncology Medicines", 1)
            second_fetcher = MapFetcher({LIST_URL: listing, URL_12634: changed_12634})
            second = run_source(
                "S26", registry=registry, now=datetime(2026, 9, 4, 12, 1, tzinfo=UTC),
                fetcher=second_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "doms-probe"},
            )
            self.assertFalse(second["baseline"])
            self.assertTrue(second["health_probe"])
            self.assertEqual(second["details_attempted"], 1)
            self.assertEqual(second["details_succeeded"], 1)
            self.assertEqual(second["changed"], 1)
            self.assertEqual(second["signals_created"], 1)
            self.assertEqual(second_fetcher.calls, [LIST_URL, URL_12634])

            with sqlite3.connect(db) as conn:
                canonical = conn.execute("SELECT count(*) FROM canonical_items WHERE source_id='S26'").fetchone()[0]
                signal = conn.execute("SELECT signal_type,canonical_key FROM signals WHERE source_id='S26'").fetchone()
                lifecycle = tuple(conn.execute(q).fetchone()[0] for q in [
                    "SELECT count(*) FROM acquisition_requests WHERE source_id='S26'",
                    "SELECT count(*) FROM acquisition_attempts WHERE source_id='S26'",
                    "SELECT count(*) FROM evidence_envelopes WHERE source_id='S26'",
                    "SELECT count(*) FROM processing_records WHERE source_id='S26'",
                ])
                pdf_requests = conn.execute("SELECT count(*) FROM evidence_envelopes WHERE source_id='S26' AND lower(requested_url) LIKE '%.pdf%'").fetchone()[0]
            self.assertEqual(canonical, 2)
            self.assertEqual(signal, ("UPDATED", "doms:12634"))
            self.assertEqual(lifecycle, (5, 5, 5, 5))
            self.assertEqual(pdf_requests, 0)


if __name__ == "__main__":
    unittest.main()
