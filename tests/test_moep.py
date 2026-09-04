from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.moep import parse_tender_detail, parse_tender_listing


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://moep.gov.mm/mm/ignite/page/62"
NODE_7141 = "https://moep.gov.mm/mm/ignite/contentView/7141"
NODE_7124 = "https://moep.gov.mm/mm/ignite/contentView/7124"
PDF_7141 = "https://moep.gov.mm/mm/userfile/EPGE1833_Tender.pdf"


class MapFetcher:
    def __init__(self, mapping: dict[str, bytes]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        try:
            return self.mapping[url]
        except KeyError as exc:
            raise AssertionError(f"unexpected fetch: {url}") from exc


def _detail_7124(detail: bytes) -> bytes:
    return (
        detail.replace(b"7141", b"7124")
        .replace(b"02-Sep-2026", b"27-Aug-2026")
        .replace("လျှပ်စစ်ဓာတ်အားထုတ်လုပ်ရေးလုပ်ငန်း(EPGE)".encode(), "ရေအားလျှပ်စစ်အကောင်အထည်ဖော်ရေးဦးစီးဌာန(DHPI)".encode())
        .replace(b"EPGE1833_Tender.pdf", b"DHPI-_2098.pdf")
    )


def _moep_registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S20"]
    source["bootstrap_seed_urls"] = [NODE_7124]
    source["baseline_detail_limit"] = 2
    source["delta_detail_limit"] = 2
    source["request_delay_ms"] = 0
    source["poll_interval_seconds"] = 3600
    source["health_policy"]["parse_probe_interval_seconds"] = 3600
    raw["sources"] = {"S20": source}
    return Registry(raw)


class MoepParserTests(unittest.TestCase):
    def test_category_discovers_current_content_ids_and_dates(self) -> None:
        entries = parse_tender_listing((FIXTURES / "moep_tender_list.html").read_bytes())
        self.assertEqual(
            [(entry.url, entry.lastmod) for entry in entries],
            [
                (NODE_7141, "2026-09-02T00:00:00Z"),
                (NODE_7124, "2026-08-27T00:00:00Z"),
            ],
        )

    def test_detail_preserves_partial_html_and_attachment_metadata_without_claiming_pdf_content(self) -> None:
        tender = parse_tender_detail((FIXTURES / "moep_tender_7141.html").read_bytes(), NODE_7141)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.source_record_id, "7141")
        self.assertEqual(tender.reference_no, "MOEP-CONTENT-7141")
        self.assertEqual(tender.canonical_key, "moep:7141:2026-09-02")
        self.assertEqual(tender.publication_date, "2026-09-02")
        self.assertEqual(tender.deadline, None)
        self.assertIn("EPGE", tender.issuer)
        self.assertEqual(tender.attachment_name, "EPGE1833_Tender.pdf")
        self.assertEqual(tender.attachment_url, PDF_7141)
        self.assertEqual(tender.payload()["detail_completeness"], "HTML_PARTIAL_ATTACHMENT_METADATA")
        self.assertEqual(tender.payload()["reference_no_kind"], "issuer_record_id")

    def test_non_tender_or_non_content_url_fails_closed(self) -> None:
        html = b'<meta property="og:title" content="ordinary news"><meta property="og:description" content="news">'
        self.assertIsNone(parse_tender_detail(html, "https://moep.gov.mm/mm/ignite/contentView/9999"))
        self.assertIsNone(parse_tender_detail((FIXTURES / "moep_tender_7141.html").read_bytes(), "https://moep.gov.mm/mm/ignite/page/62"))


class MoepEngineTests(unittest.TestCase):
    def test_baseline_is_signal_free_pdf_is_never_fetched_and_latest_html_update_signals_once(self) -> None:
        registry = _moep_registry()
        listing = (FIXTURES / "moep_tender_list.html").read_bytes()
        detail_7141 = (FIXTURES / "moep_tender_7141.html").read_bytes()
        detail_7124 = _detail_7124(detail_7141)

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"

            baseline_fetcher = MapFetcher({LIST_URL: listing, NODE_7141: detail_7141, NODE_7124: detail_7124})
            baseline = run_source(
                "S20",
                registry=registry,
                now=datetime(2026, 9, 4, 1, 0, tzinfo=UTC),
                fetcher=baseline_fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "moep-baseline"},
            )
            self.assertTrue(baseline["baseline"])
            self.assertEqual(baseline["details_attempted"], 2)
            self.assertEqual(baseline["details_succeeded"], 2)
            self.assertEqual(baseline["tenders"], 2)
            self.assertEqual(baseline["signals_created"], 0)
            self.assertNotIn(PDF_7141, baseline_fetcher.calls)

            changed = detail_7141.replace(
                "အောက်ဖော်ပြပါ အိတ်ဖွင့်တင်ဒါအား".encode(),
                "Transformer Spare Parts အောက်ဖော်ပြပါ အိတ်ဖွင့်တင်ဒါအား".encode(),
            )
            probe_fetcher = MapFetcher({LIST_URL: listing, NODE_7141: changed})
            probe = run_source(
                "S20",
                registry=registry,
                now=datetime(2026, 9, 4, 2, 1, tzinfo=UTC),
                fetcher=probe_fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "moep-probe"},
            )
            self.assertTrue(probe["health_probe"])
            self.assertEqual(probe["candidates"], 1)
            self.assertEqual(probe["changed"], 1)
            self.assertEqual(probe["signals_created"], 1)
            self.assertEqual(probe_fetcher.calls, [LIST_URL, NODE_7141])

            with sqlite3.connect(db) as conn:
                signal = conn.execute("SELECT source_id,signal_type,canonical_key FROM signals").fetchone()
                row = conn.execute(
                    "SELECT reference_no,deadline,payload_json FROM canonical_items WHERE canonical_key='moep:7141:2026-09-02'"
                ).fetchone()
            self.assertEqual(signal, ("S20", "UPDATED", "moep:7141:2026-09-02"))
            self.assertEqual(row[0], "MOEP-CONTENT-7141")
            self.assertIsNone(row[1])
            self.assertIn("Transformer Spare Parts", row[2])


if __name__ == "__main__":
    unittest.main()
