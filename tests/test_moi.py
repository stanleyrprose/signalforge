from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.moi import MOI_LIST_URL, MoiParseError, is_ministerial_office_tender, parse_tender_detail, parse_tender_listing

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LISTING = (FIXTURES / "moi_department_announcements.html").read_bytes()
DETAIL = (FIXTURES / "moi_announcement_81536.html").read_bytes()
ENTRY = parse_tender_listing(LISTING)[0]


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
    raw["sources"] = {"S37": raw["sources"]["S37"]}
    return Registry(raw)


class MoiParserTests(unittest.TestCase):
    def test_selection_is_issuer_specific_and_opportunity_stage_only(self) -> None:
        good = "ပြန်ကြားရေးဝန်ကြီးဌာန၊ ဝန်ကြီးရုံး ရုံးသုံးပစ္စည်းများ အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"
        self.assertTrue(is_ministerial_office_tender(good))
        self.assertFalse(is_ministerial_office_tender("အခြားဝန်ကြီးဌာန ရုံးသုံးပစ္စည်းများ အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"))
        self.assertFalse(is_ministerial_office_tender("ပြန်ကြားရေးဝန်ကြီးဌာန ရုံးသုံးပစ္စည်းများ အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"))
        self.assertFalse(is_ministerial_office_tender("ပြန်ကြားရေးဝန်ကြီးဌာန၊ ဝန်ကြီးရုံး အိတ်ဖွင့်တင်ဒါအောင်စာရင်း ထုတ်ပြန်ခြင်း"))

    def test_listing_selects_one_native_drupal_node_and_visible_date(self) -> None:
        entries = parse_tender_listing(LISTING)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].url, "https://www.moi.gov.mm/announcements/81536")
        self.assertEqual(entries[0].lastmod, "2026-04-09T00:00:00+06:30")

    def test_listing_structural_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(MoiParseError, "card structure"):
            parse_tender_listing(b"<html><body>changed</body></html>")

    def test_detail_extracts_scope_sale_window_deadline_and_node_identity(self) -> None:
        tender = parse_tender_detail(DETAIL, ENTRY.url)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "moi:81536")
        self.assertEqual(tender.reference_no, "MOI-NODE-81536")
        self.assertEqual(tender.publication_date, "2026-04-09")
        self.assertEqual(tender.tender_form_sale_start, "2026-04-20")
        self.assertEqual(tender.tender_form_sale_end, "2026-05-11")
        self.assertEqual(tender.deadline, "2026-05-15")
        self.assertIn("ရုံးသုံးစက်ပစ္စည်း(၄) မျိုး", tender.scope_summary)
        self.assertIn("ပရိဘောဂ(၁)မျိုး", tender.scope_summary)
        payload = tender.payload()
        self.assertEqual(payload["reference_no_kind"], "drupal_node_id")
        self.assertEqual(payload["publication_date_evidence"], "DETAIL_VISIBLE_MM_DD_YYYY")
        self.assertEqual(payload["deadline_evidence"], "EXPLICIT_HTML_FINAL_SUBMISSION_DATE")
        self.assertEqual(payload["attachment_policy"], "HTML_ONLY_NO_ATTACHMENT_REQUIRED")

    def test_detail_fails_closed_on_node_mismatch_or_missing_deadline(self) -> None:
        self.assertIsNone(parse_tender_detail(DETAIL, "https://www.moi.gov.mm/announcements/81537"))
        no_deadline = DETAIL.replace("နောက်ဆုံးထား".encode(), "တင်သွင်းရန်".encode())
        self.assertIsNone(parse_tender_detail(no_deadline, ENTRY.url))


class MoiEngineTests(unittest.TestCase):
    def test_baseline_fetches_listing_and_detail_then_unchanged_poll_fetches_listing_only(self) -> None:
        registry = _registry()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            first_fetcher = MapFetcher({MOI_LIST_URL: LISTING, ENTRY.url: DETAIL})
            first = run_source(
                "S37", registry=registry, now=datetime(2026, 9, 7, 14, 30, tzinfo=UTC),
                fetcher=first_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "moi-baseline"},
            )
            self.assertTrue(first["baseline"])
            self.assertEqual(first["items"], 1)
            self.assertEqual(first["tenders"], 1)
            self.assertEqual(first["details_attempted"], 1)
            self.assertEqual(first["details_succeeded"], 1)
            self.assertEqual(first["changed"], 1)
            self.assertEqual(first["signals_created"], 0)
            self.assertEqual(first_fetcher.calls, [MOI_LIST_URL, ENTRY.url])

            second_fetcher = MapFetcher({MOI_LIST_URL: LISTING})
            second = run_source(
                "S37", registry=registry, now=datetime(2026, 9, 7, 14, 31, tzinfo=UTC),
                fetcher=second_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "moi-second"},
            )
            self.assertFalse(second["baseline"])
            self.assertEqual(second["details_attempted"], 0)
            self.assertEqual(second["changed"], 0)
            self.assertEqual(second["signals_created"], 0)
            self.assertEqual(second_fetcher.calls, [MOI_LIST_URL])

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S37'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S37'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT publication_date,deadline FROM canonical_items WHERE canonical_key='moi:81536'").fetchone(), ("2026-04-09", "2026-05-15"))
                lifecycle = tuple(conn.execute(q).fetchone()[0] for q in [
                    "SELECT COUNT(*) FROM acquisition_requests WHERE source_id='S37'",
                    "SELECT COUNT(*) FROM acquisition_attempts WHERE source_id='S37'",
                    "SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S37'",
                    "SELECT COUNT(*) FROM processing_records WHERE source_id='S37'",
                ])
                non_html = conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S37' AND media_type != 'text/html'").fetchone()[0]
            self.assertEqual(lifecycle, (3, 3, 3, 3))
            self.assertEqual(non_html, 0)


if __name__ == "__main__":
    unittest.main()
