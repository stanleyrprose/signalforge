from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.config import Registry
from signalforge.energy import (
    EnergyParseError,
    extract_tender_pdf_urls,
    parse_detail_metadata,
    parse_tender_detail_with_attachments,
    parse_tender_listing,
)
from signalforge.engine import run_source
from signalforge.source_adapters import adapter_for

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://energy.gov.mm/tenders"
DETAIL_IDS = (235, 233, 234, 232)
DETAIL_URLS = {item: f"https://energy.gov.mm/tenders/{item}" for item in DETAIL_IDS}


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class EnergyParserTests(unittest.TestCase):
    def test_listing_exposes_current_numeric_tender_records(self) -> None:
        entries = parse_tender_listing(_fixture("energy-tenders.html"))
        by_url = {entry.url: entry for entry in entries}
        self.assertEqual(set(by_url), set(DETAIL_URLS.values()))
        self.assertEqual(by_url[DETAIL_URLS[235]].lastmod, "2026-09-04T00:00:00+06:30")
        self.assertEqual(by_url[DETAIL_URLS[233]].lastmod, "2026-08-14T00:00:00+06:30")
        self.assertEqual(by_url[DETAIL_URLS[232]].lastmod, "2026-08-04T00:00:00+06:30")

    def test_detail_metadata_requires_one_same_issuer_pdf(self) -> None:
        metadata = parse_detail_metadata(_fixture("energy-235.html"), DETAIL_URLS[235])
        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertEqual(metadata.record_id, "235")
        self.assertEqual(metadata.publication_date, "2026-09-04")
        self.assertEqual(
            metadata.pdf_url,
            "https://energy.gov.mm/storage/tenders/ZN0mM90uR0Ik1KJNCSY8GbcyK1YAgs8BMmbMxUvG.pdf",
        )
        self.assertEqual(extract_tender_pdf_urls(_fixture("energy-235.html"), DETAIL_URLS[235]), [metadata.pdf_url])
        self.assertIsNone(parse_detail_metadata(_fixture("energy-235.html"), "https://example.com/tenders/235"))
        self.assertIsNone(parse_detail_metadata(_fixture("energy-235.html"), f"{DETAIL_URLS[235]}?x=1"))

    def test_text_native_pdfs_extract_reference_scope_and_deadline(self) -> None:
        expected = {
            235: ("ENERGY-27-2026-2027", "2026-09-18", "13:00", ("API 5L", "IOT Module", "Desktop Computer")),
            233: ("ENERGY-24-2026", "2026-08-28", "13:00", ("Computing Server", "Storage Server")),
            234: ("ENERGY-25-2026-2027", "2026-08-28", "13:00", ("Online UPS", "Transmitter", "ISO 17025")),
            232: ("ENERGY-23-2026-2027", "2026-08-18", "13:00", ("Fuel Lab Equipment", "Solar System")),
        }
        for record_id, (reference, deadline, deadline_time, scope_tokens) in expected.items():
            with self.subTest(record_id=record_id):
                html = _fixture(f"energy-{record_id}.html")
                pdf = _fixture(f"energy-{record_id}.pdf")
                metadata = parse_detail_metadata(html, DETAIL_URLS[record_id])
                assert metadata is not None
                parsed = parse_tender_detail_with_attachments(html, DETAIL_URLS[record_id], [(metadata.pdf_url, pdf)])
                self.assertEqual(len(parsed), 1)
                tender = parsed[0]
                self.assertEqual(tender.canonical_key, f"energy:{record_id}")
                self.assertEqual(tender.reference_no, reference)
                self.assertEqual(tender.deadline, deadline)
                self.assertEqual(tender.deadline_time, deadline_time)
                for token in scope_tokens:
                    self.assertIn(token, tender.scope_summary)
                self.assertEqual(tender.payload()["attachment_policy"], "SINGLE_TEXT_PDF_REQUIRED")

    def test_attachment_mismatch_and_non_pdf_fail_closed(self) -> None:
        html = _fixture("energy-235.html")
        pdf = _fixture("energy-235.pdf")
        with self.assertRaises(EnergyParseError):
            parse_tender_detail_with_attachments(
                html,
                DETAIL_URLS[235],
                [("https://energy.gov.mm/storage/tenders/wrong.pdf", pdf)],
            )
        metadata = parse_detail_metadata(html, DETAIL_URLS[235])
        assert metadata is not None
        with self.assertRaises(EnergyParseError):
            parse_tender_detail_with_attachments(html, DETAIL_URLS[235], [(metadata.pdf_url, b"not a pdf")])


class EnergyEngineTests(unittest.TestCase):
    def _fixture_map(self) -> dict[str, bytes]:
        values = {LIST_URL: _fixture("energy-tenders.html")}
        for record_id in DETAIL_IDS:
            html = _fixture(f"energy-{record_id}.html")
            metadata = parse_detail_metadata(html, DETAIL_URLS[record_id])
            assert metadata is not None
            values[DETAIL_URLS[record_id]] = html
            values[metadata.pdf_url] = _fixture(f"energy-{record_id}.pdf")
        return values

    def test_baseline_persists_html_and_pdf_acquisition_with_zero_signals(self) -> None:
        registry = Registry.load(ROOT)
        fixtures = self._fixture_map()
        calls: list[str] = []

        def fetcher(url: str, **_kwargs) -> bytes:
            calls.append(url)
            try:
                return fixtures[url]
            except KeyError as exc:
                raise AssertionError(f"unexpected fetch: {url}") from exc

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            database = base / "signalforge.db"
            evidence = base / "evidence"
            result = run_source(
                "S39",
                registry=registry,
                now=datetime(2026, 9, 8, 15, 30, tzinfo=UTC),
                fetcher=fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=database,
                evidence=evidence,
                worker_context={"run_id": "energy-baseline-worker"},
            )

            self.assertTrue(result["baseline"])
            self.assertEqual(result["status"], "SUCCESS")
            self.assertEqual(result["discovered"], 4)
            self.assertEqual(result["details_attempted"], 4)
            self.assertEqual(result["details_succeeded"], 4)
            self.assertEqual(result["detail_errors"], 0)
            self.assertEqual(result["tenders"], 4)
            self.assertEqual(result["changed"], 4)
            self.assertEqual(result["signals_created"], 0)
            self.assertEqual(result["backlog_remaining"], 0)
            self.assertEqual(len(calls), 9)
            self.assertEqual(sum(url.endswith(".pdf") for url in calls), 4)

            with sqlite3.connect(database) as conn:
                canonical = conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S39'").fetchone()[0]
                signals = conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S39'").fetchone()[0]
                target_counts = dict(conn.execute(
                    "SELECT target_kind,COUNT(*) FROM acquisition_requests WHERE source_id='S39' GROUP BY target_kind"
                ))
                evidence_count = conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S39'").fetchone()[0]
                processing_count = conn.execute(
                    "SELECT COUNT(*) FROM processing_records WHERE source_id='S39' AND status='SUCCESS'"
                ).fetchone()[0]
                detail_processing_count = conn.execute(
                    "SELECT COUNT(*) FROM processing_records WHERE source_id='S39' AND status='SUCCESS' AND parser_version='energy-html-plus-text-pdf-v1'"
                ).fetchone()[0]
                evidence_sha = conn.execute(
                    "SELECT evidence_sha256 FROM canonical_items WHERE canonical_key='energy:235'"
                ).fetchone()[0]
            self.assertEqual(canonical, 4)
            self.assertEqual(signals, 0)
            self.assertEqual(target_counts, {"DISCOVERY": 1, "HTML": 4, "PDF": 4})
            self.assertEqual(evidence_count, 9)
            self.assertEqual(processing_count, 5)
            self.assertEqual(detail_processing_count, 4)
            self.assertEqual(evidence_sha, hashlib.sha256(_fixture("energy-235.pdf")).hexdigest())
            self.assertEqual(len(list((evidence / "S39").glob("*.pdf"))), 4)

            promoted = run_source(
                "S39",
                registry=registry,
                now=datetime(2026, 9, 8, 16, 0, tzinfo=UTC),
                fetcher=fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=database,
                evidence=evidence,
                worker_context={"run_id": "energy-actionable-reconcile-worker"},
            )
            self.assertFalse(promoted["baseline"])
            self.assertEqual(promoted["changed"], 0)
            self.assertEqual(promoted["signals_created"], 1)
            self.assertEqual(len(calls), 10)

            idempotent = run_source(
                "S39",
                registry=registry,
                now=datetime(2026, 9, 8, 16, 31, tzinfo=UTC),
                fetcher=fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=database,
                evidence=evidence,
                worker_context={"run_id": "energy-actionable-idempotent-worker"},
            )
            self.assertEqual(idempotent["signals_created"], 0)
            self.assertEqual(len(calls), 11)

            with sqlite3.connect(database) as conn:
                signal_rows = conn.execute(
                    "SELECT signal_type,canonical_key,payload_json FROM signals WHERE source_id='S39'"
                ).fetchall()
            self.assertEqual(len(signal_rows), 1)
            self.assertEqual(signal_rows[0][0:2], ("NEW", "energy:235"))
            signal_payload = __import__("json").loads(signal_rows[0][2])
            self.assertEqual(signal_payload["signal_reason"], "ACTIONABLE_BASELINE_RECONCILIATION")
            self.assertEqual(signal_payload["deadline"], "2026-09-18")

    def test_same_origin_guard_rejects_adapter_supplied_external_pdf_before_fetch(self) -> None:
        registry = Registry.load(ROOT)
        fixtures = self._fixture_map()
        calls: list[str] = []
        real_adapter = adapter_for("S39", registry.source("S39"))
        poisoned = replace(
            real_adapter,
            extract_detail_attachments=lambda _html, _url: ["https://evil.example/tender.pdf"],
        )

        def fetcher(url: str, **_kwargs) -> bytes:
            calls.append(url)
            if url.startswith("https://evil.example"):
                raise AssertionError("engine must reject off-origin attachment before fetch")
            return fixtures[url]

        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.engine.adapter_for", return_value=poisoned):
            with self.assertRaisesRegex(RuntimeError, "all bounded detail candidates failed"):
                run_source(
                    "S39",
                    registry=registry,
                    now=datetime(2026, 9, 8, 15, 30, tzinfo=UTC),
                    fetcher=fetcher,
                    sleeper=lambda _seconds: None,
                    force=True,
                    database=Path(tmp) / "signalforge.db",
                    evidence=Path(tmp) / "evidence",
                    worker_context={"run_id": "energy-origin-guard"},
                )
        self.assertFalse(any(url.startswith("https://evil.example") for url in calls))


if __name__ == "__main__":
    unittest.main()
