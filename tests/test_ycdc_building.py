from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.ycdc_building import (
    YCDC_BUILDING_URL,
    YcdcBuildingParseError,
    is_building_implementation_opportunity,
    parse_explicit_deadline,
    parse_tender_records,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class SinglePageFetcher:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url != YCDC_BUILDING_URL:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.payload


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S16"]
    raw["sources"] = {"S16": source}
    return Registry(raw)


class YcdcBuildingParserTests(unittest.TestCase):
    def test_classifier_keeps_ppp_and_excludes_lease_sale_auction(self) -> None:
        self.assertTrue(is_building_implementation_opportunity("တင်ဒါခေါ်ယူခြင်း PPP ပူးပေါင်းဆောင်ရွက် ဆောက်လုပ်ရန်"))
        self.assertFalse(is_building_implementation_opportunity("တင်ဒါခေါ်ယူခြင်း အငှားချထားဆောင်ရွက်မည်"))
        self.assertFalse(is_building_implementation_opportunity("တင်ဒါခေါ်ယူခြင်း ဖြိုဖျက်ရောင်းချမည်"))
        self.assertFalse(is_building_implementation_opportunity("လေလံခေါ်ယူခြင်း ဆောက်လုပ်ရေးပစ္စည်း"))

    def test_myanmar_digit_deadline_is_explicit(self) -> None:
        self.assertEqual(parse_explicit_deadline("တင်သွင်းရမည့်နောက်ဆုံးရက် - ၂၇-၂-၂၀၂၆"), "2026-02-27")

    def test_archive_parses_only_implementation_opportunities(self) -> None:
        rows = parse_tender_records((FIXTURES / "ycdc_building_tenders.html").read_bytes())
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.deadline, "2026-02-27")
        self.assertIsNone(row.publication_date)
        self.assertTrue(row.canonical_key.startswith("ycdc-building:2026-02-27:"))
        payload = row.payload()
        self.assertEqual(payload["deadline_evidence"], "EXPLICIT_HTML_FINAL_SUBMISSION_DATE")
        self.assertEqual(payload["publication_date_evidence"], "UNKNOWN_NOT_EXPOSED_IN_STABLE_ARCHIVE_HTML")
        self.assertEqual(payload["opportunity_kind"], "PPP_OR_BUILDING_IMPLEMENTATION")

    def test_structural_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(YcdcBuildingParseError, "archive table structure"):
            parse_tender_records(b"<html><body>changed</body></html>")

    def test_same_identity_different_block_fails_closed(self) -> None:
        base = (FIXTURES / "ycdc_building_tenders.html").read_text(encoding="utf-8")
        selected = base.split("<table><tbody><tr><td>", 2)[2].split("</td></tr></tbody></table>", 1)[0]
        changed = selected.replace("၆-၂-၂၀၂၆", "၇-၂-၂၀၂၆")
        html = f"<table><tr><td>{selected}</td></tr></table><table><tr><td>{changed}</td></tr></table>".encode()
        with self.assertRaisesRegex(YcdcBuildingParseError, "identity collision"):
            parse_tender_records(html)


class YcdcBuildingEngineTests(unittest.TestCase):
    def test_baseline_is_one_html_fetch_and_signal_free(self) -> None:
        payload = (FIXTURES / "ycdc_building_tenders.html").read_bytes()
        registry = _registry()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            fetcher = SinglePageFetcher(payload)
            result = run_source(
                "S16",
                registry=registry,
                now=datetime(2026, 9, 7, 9, 0, tzinfo=UTC),
                fetcher=fetcher,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "ycdc-building-baseline"},
            )
            self.assertTrue(result["baseline"])
            self.assertTrue(result["listing_complete"])
            self.assertEqual(result["items"], 1)
            self.assertEqual(result["tenders"], 1)
            self.assertEqual(result["details_attempted"], 0)
            self.assertEqual(result["changed"], 1)
            self.assertEqual(result["signals_created"], 0)
            self.assertEqual(fetcher.calls, [YCDC_BUILDING_URL])

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S16'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S16'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S16'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT details_attempted,tenders_parsed,items_parsed FROM scheduler_runs WHERE source_id='S16'").fetchone(), (0, 1, 1))


if __name__ == "__main__":
    unittest.main()
