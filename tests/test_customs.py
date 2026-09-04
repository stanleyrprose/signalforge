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
from signalforge.customs import CustomsParseError, normalize_reference, parse_notification_records
from signalforge.engine import run_source


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://customs.gov.mm/notifications"


class SinglePageFetcher:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url != LIST_URL:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.payload


def _customs_registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S07"]
    source["poll_interval_seconds"] = 1800
    raw["sources"] = {"S07": source}
    return Registry(raw)


class CustomsParserTests(unittest.TestCase):
    def test_reference_normalizes_myanmar_digits_and_spacing(self) -> None:
        self.assertEqual(normalize_reference("အမိန့်ကြော်ငြာစာအမှတ်(၁၂၄/၂၀၂၆)"), "124/2026")
        self.assertEqual(normalize_reference("အမိန့်ကြော်ငြာစာအမှတ် ၁၀၃/ ၂၀၂၆"), "103/2026")
        self.assertEqual(normalize_reference("Notification No.143/2025"), "143/2025")

    def test_listing_rows_are_complete_regulatory_records(self) -> None:
        notices = parse_notification_records((FIXTURES / "customs_notifications.html").read_bytes())
        self.assertEqual([notice.reference_no for notice in notices], ["124/2026", "123/2026", "103/2026", "104/2026", "87/2026"])
        self.assertTrue(all(notice.item_kind == "REGULATORY_NOTICE" for notice in notices))
        self.assertTrue(all(notice.url == LIST_URL for notice in notices))
        self.assertEqual(notices[0].canonical_key, "customs-notice:124/2026")
        self.assertEqual(notices[0].notice_category, "CUSTOMS_TARIFF")
        self.assertEqual(notices[0].publication_date, None)
        self.assertEqual(notices[0].deadline, None)
        self.assertEqual(notices[0].attachment_name, "124^2026 HSD.pdf")
        self.assertTrue(str(notices[0].attachment_url).endswith("124^2026 HSD.pdf"))
        self.assertEqual(notices[0].payload()["detail_completeness"], "LISTING_EVENT_METADATA_ATTACHMENT_ONLY")

    def test_parser_fails_closed_when_table_shape_disappears(self) -> None:
        with self.assertRaises(CustomsParseError):
            parse_notification_records(b"<html><body><p>no notification table</p></body></html>")


class CustomsEngineTests(unittest.TestCase):
    def test_listing_complete_baseline_is_one_fetch_signal_free_and_update_signals_once(self) -> None:
        registry = _customs_registry()
        listing = (FIXTURES / "customs_notifications.html").read_bytes()

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"

            baseline_fetcher = SinglePageFetcher(listing)
            baseline = run_source(
                "S07",
                registry=registry,
                now=datetime(2026, 9, 4, 3, 0, tzinfo=UTC),
                fetcher=baseline_fetcher,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "customs-baseline"},
            )
            self.assertTrue(baseline["baseline"])
            self.assertTrue(baseline["listing_complete"])
            self.assertEqual(baseline["items"], 5)
            self.assertEqual(baseline["tenders"], 0)
            self.assertEqual(baseline["details_attempted"], 0)
            self.assertEqual(baseline["details_succeeded"], 0)
            self.assertEqual(baseline["changed"], 5)
            self.assertEqual(baseline["signals_created"], 0)
            self.assertEqual(baseline_fetcher.calls, [LIST_URL])

            with sqlite3.connect(db) as conn:
                canonical = conn.execute(
                    "SELECT canonical_key,item_kind,publication_date,deadline FROM canonical_items WHERE source_id='S07' ORDER BY canonical_key"
                ).fetchall()
                counts = tuple(
                    conn.execute(query).fetchone()[0]
                    for query in (
                        "SELECT COUNT(*) FROM acquisition_requests WHERE source_id='S07'",
                        "SELECT COUNT(*) FROM acquisition_attempts WHERE source_id='S07'",
                        "SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S07'",
                        "SELECT COUNT(*) FROM processing_records WHERE source_id='S07'",
                        "SELECT COUNT(*) FROM discovery_items WHERE source_id='S07'",
                    )
                )
                run_metrics = conn.execute(
                    "SELECT details_attempted,details_succeeded,tenders_parsed,items_parsed FROM scheduler_runs WHERE source_id='S07'"
                ).fetchone()
                requested_urls = [row[0] for row in conn.execute("SELECT requested_url FROM evidence_envelopes WHERE source_id='S07'")]
            self.assertEqual(len(canonical), 5)
            self.assertTrue(all(row[1] == "REGULATORY_NOTICE" for row in canonical))
            self.assertTrue(all(row[2] is None and row[3] is None for row in canonical))
            self.assertEqual(counts, (1, 1, 1, 1, 0))
            self.assertEqual(run_metrics, (0, 0, 0, 5))
            self.assertEqual(requested_urls, [LIST_URL])

            changed_listing = listing.replace(
                "ဒီဇယ်ဆီ HSD (500 ppm) ၏ အကောက်ခွန်နှုန်းလျော့ချသည့် ကာလသက်တမ်းတိုးမြှင့်ခြင်း".encode(),
                "ဒီဇယ်ဆီ HSD (500 ppm) ၏ အကောက်ခွန်နှုန်းလျော့ချသည့် ကာလသက်တမ်းတိုးမြှင့်ခြင်း - ပြင်ဆင်ချက်".encode(),
            )
            update_fetcher = SinglePageFetcher(changed_listing)
            update = run_source(
                "S07",
                registry=registry,
                now=datetime(2026, 9, 4, 3, 31, tzinfo=UTC),
                fetcher=update_fetcher,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "customs-update"},
            )
            self.assertFalse(update["baseline"])
            self.assertEqual(update["changed"], 1)
            self.assertEqual(update["signals_created"], 1)
            self.assertEqual(update_fetcher.calls, [LIST_URL])

            with sqlite3.connect(db) as conn:
                signal = conn.execute(
                    "SELECT source_id,signal_type,canonical_key,payload_json FROM signals WHERE source_id='S07'"
                ).fetchone()
                counts_after = tuple(
                    conn.execute(query).fetchone()[0]
                    for query in (
                        "SELECT COUNT(*) FROM acquisition_requests WHERE source_id='S07'",
                        "SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S07'",
                        "SELECT COUNT(*) FROM processing_records WHERE source_id='S07'",
                    )
                )
            self.assertEqual(signal[:3], ("S07", "UPDATED", "customs-notice:124/2026"))
            self.assertIn("ပြင်ဆင်ချက်", signal[3])
            self.assertEqual(counts_after, (2, 2, 2))

            with patch.dict(os.environ, {"SIGNALFORGE_DB": str(db), "SIGNALFORGE_REPO_ROOT": str(ROOT)}, clear=False):
                health = status(now=datetime(2026, 9, 4, 3, 32, tzinfo=UTC), registry=registry)
            source_health = health["sources"][0]["health"]
            self.assertEqual(source_health["parse_sample_source"], "BUSINESS_PROCESSING")
            self.assertEqual(source_health["parse_attempts"], 2)
            self.assertEqual(source_health["parse_successes"], 2)
            self.assertEqual(source_health["parse_health"], "GREEN")


if __name__ == "__main__":
    unittest.main()
