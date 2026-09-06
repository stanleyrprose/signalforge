from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.yangon_region import YangonRegionParseError, parse_tender_detail, parse_tender_listing

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://www.yangon.gov.mm/category/tenders/"
URL_3742 = "https://www.yangon.gov.mm/ycdc-open-tender-72/"
URL_3718 = "https://www.yangon.gov.mm/yesc-open-tender-10-11/"


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


class YangonRegionParserTests(unittest.TestCase):
    def test_listing_uses_stable_wordpress_posts_and_excludes_results(self) -> None:
        entries = parse_tender_listing((FIXTURES / "yangon_region_tender_list.html").read_bytes())
        self.assertEqual([entry.url for entry in entries], [URL_3742, URL_3718])
        self.assertEqual(entries[0].lastmod, "2026-08-18T18:10:19+06:30")
        self.assertEqual(entries[1].lastmod, "2026-07-20T18:13:08+06:30")

    def test_listing_fails_closed_when_tender_category_shape_disappears(self) -> None:
        with self.assertRaises(YangonRegionParseError):
            parse_tender_listing(b"<html><body><article class='post'>News</article></body></html>")

    def test_detail_extracts_structured_business_fields_and_stable_identity(self) -> None:
        tender = parse_tender_detail((FIXTURES / "yangon_region_tender_3718.html").read_bytes(), URL_3718)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "yangon-region:3718")
        self.assertEqual(tender.publication_date, "2026-07-20")
        self.assertEqual(tender.tender_form_sale_date, "2026-07-21")
        self.assertEqual(tender.deadline, "2026-08-04")
        self.assertEqual(tender.reference_no_kind, "issuer_tender_reference")
        self.assertIn("10(T)/YESC", tender.reference_no)
        self.assertIn("11(T)/YESC", tender.reference_no)
        self.assertIn("ရန်ကုန်လျှပ်စစ်", tender.department or "")
        self.assertIn("True Online UPS", tender.scope_summary or "")
        payload = tender.payload()
        self.assertEqual(payload["publisher_scope"], "REGIONAL_MULTI_AGENCY")
        self.assertEqual(payload["deadline_evidence"], "VISIBLE_STRUCTURED_CLOSING_DATE")
        self.assertEqual(payload["cross_source_overlap_policy"], "REVIEW_BEFORE_DIRECT_AGENCY_ONBOARDING")

    def test_detail_without_tender_number_falls_back_to_post_id(self) -> None:
        tender = parse_tender_detail((FIXTURES / "yangon_region_tender_3742.html").read_bytes(), URL_3742)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "yangon-region:3742")
        self.assertEqual(tender.reference_no, "YRG-POST-3742")
        self.assertEqual(tender.reference_no_kind, "wordpress_post_id")
        self.assertEqual(tender.publication_date, "2026-08-18")
        self.assertEqual(tender.deadline, "2026-09-01")
        self.assertEqual(tender.estimated_value, None)

    def test_detail_fails_closed_when_visible_post_date_disagrees_with_updated_date(self) -> None:
        payload = (FIXTURES / "yangon_region_tender_3742.html").read_bytes().replace(b">18<", b">17<", 1)
        self.assertIsNone(parse_tender_detail(payload, URL_3742))


class YangonRegionEngineTests(unittest.TestCase):
    def test_baseline_is_signal_free_and_health_probe_updates_same_post(self) -> None:
        registry = _registry()
        listing = (FIXTURES / "yangon_region_tender_list.html").read_bytes()
        detail_3742 = (FIXTURES / "yangon_region_tender_3742.html").read_bytes()
        detail_3718 = (FIXTURES / "yangon_region_tender_3718.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            first_fetcher = MapFetcher({LIST_URL: listing, URL_3742: detail_3742, URL_3718: detail_3718})
            first = run_source(
                "S30", registry=registry, now=datetime(2026, 9, 6, 0, 0, tzinfo=UTC),
                fetcher=first_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "yangon-baseline"},
            )
            self.assertTrue(first["baseline"])
            self.assertEqual(first["details_attempted"], 2)
            self.assertEqual(first["details_succeeded"], 2)
            self.assertEqual(first["tenders"], 2)
            self.assertEqual(first["signals_created"], 0)
            self.assertEqual(first_fetcher.calls, [LIST_URL, URL_3742, URL_3718])

            changed_3742 = detail_3742.replace("1 September, 2026".encode(), "2 September, 2026".encode(), 1)
            changed_3742 = changed_3742.replace("ဘိလပ်မြေ၊ ကတ္တရာ".encode(), "ဘိလပ်မြေ၊ ကတ္တရာ၊ သံချောင်း".encode(), 1)
            second_fetcher = MapFetcher({LIST_URL: listing, URL_3742: changed_3742})
            second = run_source(
                "S30", registry=registry, now=datetime(2026, 9, 6, 2, 1, tzinfo=UTC),
                fetcher=second_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "yangon-probe"},
            )
            self.assertFalse(second["baseline"])
            self.assertTrue(second["health_probe"])
            self.assertEqual(second["details_attempted"], 1)
            self.assertEqual(second["details_succeeded"], 1)
            self.assertEqual(second["changed"], 1)
            self.assertEqual(second["signals_created"], 1)
            self.assertEqual(second_fetcher.calls, [LIST_URL, URL_3742])

            with sqlite3.connect(db) as conn:
                canonical = conn.execute("SELECT count(*) FROM canonical_items WHERE source_id='S30'").fetchone()[0]
                signal = conn.execute("SELECT signal_type,canonical_key FROM signals WHERE source_id='S30'").fetchone()
                lifecycle = tuple(conn.execute(q).fetchone()[0] for q in [
                    "SELECT count(*) FROM acquisition_requests WHERE source_id='S30'",
                    "SELECT count(*) FROM acquisition_attempts WHERE source_id='S30'",
                    "SELECT count(*) FROM evidence_envelopes WHERE source_id='S30'",
                    "SELECT count(*) FROM processing_records WHERE source_id='S30'",
                ])
                attachment_requests = conn.execute(
                    "SELECT count(*) FROM evidence_envelopes WHERE source_id='S30' AND (lower(requested_url) LIKE '%.pdf%' OR lower(requested_url) LIKE '%.jpg%' OR lower(requested_url) LIKE '%.png%')"
                ).fetchone()[0]
            self.assertEqual(canonical, 2)
            self.assertEqual(signal, ("UPDATED", "yangon-region:3742"))
            self.assertEqual(lifecycle, (5, 5, 5, 5))
            self.assertEqual(attachment_requests, 0)


if __name__ == "__main__":
    unittest.main()
