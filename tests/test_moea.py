from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.moea import (
    MOEA_LIST_URL,
    MoeaParseError,
    is_procurement_invitation,
    parse_explicit_deadline,
    parse_tender_records,
    parse_visible_publication_date,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class SinglePageFetcher:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url != MOEA_LIST_URL:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.payload


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S31"]
    raw["sources"] = {"S31": source}
    return Registry(raw)


class MoeaParserTests(unittest.TestCase):
    def test_visible_date_and_explicit_myanmar_digit_deadline(self) -> None:
        self.assertEqual(parse_visible_publication_date("27 July 2026"), "2026-07-27")
        self.assertEqual(parse_explicit_deadline("တင်ဒါတင်သွင်းရမည့်နောက်ဆုံးရက် - (၇-၈-၂၀၂၆) ရက်"), "2026-08-07")
        self.assertIsNone(parse_explicit_deadline("တင်ဒါပုံစံရောင်းချမည့်ရက် ၂၉-၅-၂၀၂၆ မှ ၁၀-၆-၂၀၂၆"))

    def test_selection_excludes_awards_and_non_procurement_leases(self) -> None:
        self.assertTrue(is_procurement_invitation("အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"))
        self.assertFalse(is_procurement_invitation("တင်ဒါအောင်မြင်သော ကုမ္ပဏီများစာရင်း"))
        self.assertFalse(is_procurement_invitation("ဆိုင်ခန်း ငှားရမ်းရန် တင်ဒါခေါ်ယူခြင်း"))

    def test_listing_yields_three_procurement_records_without_fetching_attachments(self) -> None:
        rows = parse_tender_records((FIXTURES / "moea_tenders.html").read_bytes())
        self.assertEqual(len(rows), 3)
        self.assertEqual([row.publication_date for row in rows], ["2026-07-27", "2026-05-28", "2026-02-04"])
        self.assertEqual(rows[0].deadline, "2026-08-07")
        self.assertIsNone(rows[1].deadline)
        self.assertIn("သက်မွေးပညာသင်တန်းစင်တာ", rows[0].scope_summary or "")
        self.assertEqual(rows[0].location, "နေပြည်တော်")
        self.assertEqual(rows[0].attachment_name, "1785147339.pdf")
        self.assertEqual(rows[0].payload()["reference_no_kind"], "issuer_archive_event_fingerprint")
        self.assertEqual(rows[0].payload()["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")
        self.assertTrue(rows[0].canonical_key.startswith("moea:2026-07-27:"))

    def test_structural_drift_fails_closed_but_valid_empty_is_allowed(self) -> None:
        with self.assertRaisesRegex(MoeaParseError, "listing structure"):
            parse_tender_records(b"<html><body>changed</body></html>")
        award_only = b'''<div class="tender-content"><h4 class="tender-title">Tender Award Result</h4><ul><li>27 July 2026</li><li>Nay Pyi Taw</li></ul><div class="tender-action"><a href="news_images/pdf/1.pdf">View</a></div></div>'''
        self.assertEqual(parse_tender_records(award_only), [])

    def test_identity_collision_with_different_attachment_fails_closed(self) -> None:
        html = b'''<div class="tender-content"><h4 class="tender-title">Open Tender Invitation</h4><ul><li>27 July 2026</li><li>Nay Pyi Taw</li></ul><div class="tender-action"><a href="news_images/pdf/a.pdf">View</a></div></div><div class="tender-content"><h4 class="tender-title">Open Tender Invitation</h4><ul><li>27 July 2026</li><li>Nay Pyi Taw</li></ul><div class="tender-action"><a href="news_images/pdf/b.pdf">View</a></div></div>'''
        with self.assertRaisesRegex(MoeaParseError, "identity collision"):
            parse_tender_records(html)


class MoeaEngineTests(unittest.TestCase):
    def test_baseline_is_one_html_fetch_signal_free_and_pdf_is_not_fetched(self) -> None:
        listing = (FIXTURES / "moea_tenders.html").read_bytes()
        registry = _registry()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            fetcher = SinglePageFetcher(listing)
            result = run_source(
                "S31",
                registry=registry,
                now=datetime(2026, 9, 7, 4, 0, tzinfo=UTC),
                fetcher=fetcher,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "moea-baseline"},
            )
            self.assertTrue(result["baseline"])
            self.assertTrue(result["listing_complete"])
            self.assertEqual(result["items"], 3)
            self.assertEqual(result["tenders"], 3)
            self.assertEqual(result["details_attempted"], 0)
            self.assertEqual(result["changed"], 3)
            self.assertEqual(result["signals_created"], 0)
            self.assertEqual(fetcher.calls, [MOEA_LIST_URL])

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S31'").fetchone()[0], 3)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S31'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S31'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S31' AND lower(requested_url) LIKE '%.pdf%'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT details_attempted,tenders_parsed,items_parsed FROM scheduler_runs WHERE source_id='S31'").fetchone(), (0, 3, 3))


if __name__ == "__main__":
    unittest.main()
