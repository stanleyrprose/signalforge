from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.mcrd import MCRD_TENDER_URL, McrdParseError, is_procurement_invitation, parse_tender_records

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class SinglePageFetcher:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url != MCRD_TENDER_URL:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.payload


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S33"]
    raw["sources"] = {"S33": source}
    return Registry(raw)


class McrdParserTests(unittest.TestCase):
    def test_invitation_filter_excludes_award_stage(self) -> None:
        self.assertTrue(is_procurement_invitation("ပြည်ထောင်စုဝန်ကြီးရုံး အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"))
        self.assertFalse(is_procurement_invitation("တင်ဒါအောင်မြင်သည့်ကုမ္ပဏီများစာရင်း"))

    def test_board_parses_rows_and_uses_event_fingerprint(self) -> None:
        rows = parse_tender_records((FIXTURES / "mcrd_tenders.html").read_bytes())
        self.assertEqual(len(rows), 2)
        current, older = rows
        self.assertEqual(current.deadline, "2026-05-15")
        self.assertIsNone(current.publication_date)
        self.assertEqual(current.department, "ဝန်ကြီးရုံး")
        self.assertEqual(current.attachment_name, "Minister.pdf")
        self.assertTrue(current.canonical_key.startswith("mcrd:2026-05-15:"))
        self.assertNotEqual(current.canonical_key, older.canonical_key)
        payload = current.payload()
        self.assertEqual(payload["deadline_evidence"], "EXPLICIT_TENDER_BOARD_CLOSING_DATE")
        self.assertEqual(payload["publication_date_evidence"], "UNKNOWN_NOT_EXPOSED_IN_TENDER_BOARD_HTML")
        self.assertEqual(payload["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")

    def test_same_event_with_different_primary_document_fails_closed(self) -> None:
        base = (FIXTURES / "mcrd_tenders.html").read_text(encoding="utf-8")
        first = base.split('<div class="alert alert-info">', 2)[1].split('</div>', 1)[0]
        duplicate = first.replace("Minister.pdf", "Minister-replaced.pdf")
        html = f'<div class="alert alert-info">{first}</div><div class="alert alert-info">{duplicate}</div>'.encode()
        with self.assertRaisesRegex(McrdParseError, "identity collision"):
            parse_tender_records(html)

    def test_structural_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(McrdParseError, "board structure"):
            parse_tender_records(b"<html><body>changed</body></html>")


class McrdEngineTests(unittest.TestCase):
    def test_baseline_is_one_html_fetch_and_signal_free(self) -> None:
        payload = (FIXTURES / "mcrd_tenders.html").read_bytes()
        registry = _registry()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            fetcher = SinglePageFetcher(payload)
            result = run_source(
                "S33",
                registry=registry,
                now=datetime(2026, 9, 7, 6, 40, tzinfo=UTC),
                fetcher=fetcher,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "mcrd-baseline"},
            )
            self.assertTrue(result["baseline"])
            self.assertTrue(result["listing_complete"])
            self.assertEqual(result["items"], 2)
            self.assertEqual(result["tenders"], 2)
            self.assertEqual(result["details_attempted"], 0)
            self.assertEqual(result["changed"], 2)
            self.assertEqual(result["signals_created"], 0)
            self.assertEqual(fetcher.calls, [MCRD_TENDER_URL])

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S33'").fetchone()[0], 2)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S33'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S33'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT details_attempted,tenders_parsed,items_parsed FROM scheduler_runs WHERE source_id='S33'").fetchone(), (0, 2, 2))


if __name__ == "__main__":
    unittest.main()
