from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.iwt import parse_tender_detail, parse_tender_listing


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://iwt.gov.mm/tenders"
NODE_1038 = "https://iwt.gov.mm/my/node/1038"
NODE_1037 = "https://iwt.gov.mm/my/node/1037"


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


def _detail_1037(detail: bytes) -> bytes:
    return (
        detail.replace(b'1038', b'1037')
        .replace(b'2026-08-25T08:51:07Z', b'2026-07-25T04:12:54Z')
        .replace(b'2026-11-03T03:30:00Z', b'2026-08-25T10:00:00Z')
        .replace("IWT_1 Costal Vessel Tender 25-8-2026.pdf".encode(), "Dala Dockyard Tender 25-7-2026.pdf".encode())
    )


def _iwt_registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S22"]
    # Intentionally keep the older node as the only static seed. The health
    # probe must still choose the newest discovery item (1038), not the seed.
    source["bootstrap_seed_urls"] = [NODE_1037]
    source["baseline_detail_limit"] = 2
    source["delta_detail_limit"] = 2
    source["request_delay_ms"] = 0
    source["poll_interval_seconds"] = 3600
    source["health_policy"]["parse_probe_interval_seconds"] = 3600
    raw["sources"] = {"S22": source}
    return Registry(raw)


class IwtParserTests(unittest.TestCase):
    def test_listing_discovers_current_drupal_tender_nodes_in_source_order(self) -> None:
        entries = parse_tender_listing((FIXTURES / "iwt_tender_list.html").read_bytes())
        self.assertEqual(len(entries), 4)
        self.assertEqual(entries[0].url, NODE_1038)
        self.assertEqual(entries[0].lastmod, "2026-08-25T08:51:07Z")
        self.assertEqual(entries[1].url, NODE_1037)
        self.assertEqual(entries[1].lastmod, "2026-07-25T04:12:54Z")

    def test_detail_extracts_scope_dates_attachment_and_stable_issuer_record_identity(self) -> None:
        tender = parse_tender_detail((FIXTURES / "iwt_tender_1038.html").read_bytes(), NODE_1038)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.source_record_id, "1038")
        self.assertEqual(tender.reference_no, "IWT-NODE-1038")
        self.assertEqual(tender.canonical_key, "iwt:1038:2026-08-25")
        self.assertEqual(tender.publication_date, "2026-08-25")
        self.assertEqual(tender.deadline, "2026-11-03")
        self.assertEqual(tender.deadline_datetime_utc, "2026-11-03T03:30:00Z")
        self.assertEqual(tender.deadline_datetime_local, "2026-11-03T10:00:00+06:30")
        self.assertIn("ရေယာဉ် ၁ စီး", tender.project_name)
        self.assertEqual(tender.attachment_name, "IWT_1 Costal Vessel Tender 25-8-2026.pdf")
        self.assertEqual(tender.attachment_url, "https://iwt.gov.mm/my/file-download/download/public/1708")
        self.assertEqual(tender.payload()["reference_no_kind"], "issuer_record_id")

    def test_non_tender_page_fails_closed(self) -> None:
        payload = b'<article data-history-node-id="1038" class="node node--type-page"><span class="field-name-title">x</span></article>'
        self.assertIsNone(parse_tender_detail(payload, NODE_1038))


class IwtEngineTests(unittest.TestCase):
    def test_baseline_is_signal_free_and_latest_detail_probe_detects_deadline_update(self) -> None:
        registry = _iwt_registry()
        listing = (FIXTURES / "iwt_tender_list.html").read_bytes()
        detail_1038 = (FIXTURES / "iwt_tender_1038.html").read_bytes()
        detail_1037 = _detail_1037(detail_1038)

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"

            baseline_fetcher = MapFetcher(
                {LIST_URL: listing, NODE_1038: detail_1038, NODE_1037: detail_1037}
            )
            baseline = run_source(
                "S22",
                registry=registry,
                now=datetime(2026, 9, 4, 0, 0, tzinfo=UTC),
                fetcher=baseline_fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "iwt-baseline"},
            )
            self.assertTrue(baseline["baseline"])
            self.assertEqual(baseline["details_attempted"], 2)
            self.assertEqual(baseline["details_succeeded"], 2)
            self.assertEqual(baseline["tenders"], 2)
            self.assertEqual(baseline["changed"], 2)
            self.assertEqual(baseline["signals_created"], 0)

            changed_detail = detail_1038.replace(
                b'2026-11-03T03:30:00Z', b'2026-11-10T03:30:00Z'
            ).replace(b'11/03/2026 - 10:00', b'11/10/2026 - 10:00')
            probe_fetcher = MapFetcher({LIST_URL: listing, NODE_1038: changed_detail})
            probe = run_source(
                "S22",
                registry=registry,
                now=datetime(2026, 9, 4, 1, 1, tzinfo=UTC),
                fetcher=probe_fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "iwt-probe"},
            )
            self.assertFalse(probe["baseline"])
            self.assertTrue(probe["health_probe"])
            self.assertEqual(probe["candidates"], 1)
            self.assertEqual(probe["details_attempted"], 1)
            self.assertEqual(probe["details_succeeded"], 1)
            self.assertEqual(probe["tenders"], 1)
            self.assertEqual(probe["changed"], 1)
            self.assertEqual(probe["signals_created"], 1)
            self.assertEqual(probe_fetcher.calls, [LIST_URL, NODE_1038])

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items").fetchone()[0], 2)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0], 1)
                signal = conn.execute(
                    "SELECT source_id,signal_type,canonical_key FROM signals"
                ).fetchone()
                updated = conn.execute(
                    "SELECT deadline,reference_no FROM canonical_items WHERE canonical_key='iwt:1038:2026-08-25'"
                ).fetchone()
                marker = conn.execute(
                    "SELECT canonical_key FROM discovery_items WHERE source_id='S22' AND url=?",
                    (NODE_1038,),
                ).fetchone()[0]
            self.assertEqual(signal, ("S22", "UPDATED", "iwt:1038:2026-08-25"))
            self.assertEqual(updated, ("2026-11-10", "IWT-NODE-1038"))
            self.assertEqual(marker, "iwt:1038:2026-08-25")

    def test_actionable_baseline_reconciliation_promotes_only_still_future_iwt_tender(self) -> None:
        registry = _iwt_registry()
        listing = (FIXTURES / "iwt_tender_list.html").read_bytes()
        detail_1038 = (FIXTURES / "iwt_tender_1038.html").read_bytes()
        detail_1037 = _detail_1037(detail_1038)
        mapping = {LIST_URL: listing, NODE_1038: detail_1038, NODE_1037: detail_1037}
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            baseline = run_source(
                "S22", registry=registry, now=datetime(2026, 9, 11, 1, 0, tzinfo=UTC),
                fetcher=MapFetcher(mapping), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "iwt-reconcile-baseline"},
            )
            self.assertEqual(baseline["signals_created"], 0)
            reconciled = run_source(
                "S22", registry=registry, now=datetime(2026, 9, 11, 2, 1, tzinfo=UTC),
                fetcher=MapFetcher({LIST_URL: listing, NODE_1038: detail_1038}), sleeper=lambda _seconds: None, force=True,
                database=db, evidence=evidence, worker_context={"run_id": "iwt-reconcile-delta"},
            )
            self.assertEqual(reconciled["changed"], 0)
            self.assertEqual(reconciled["signals_created"], 1)
            with sqlite3.connect(db) as conn:
                row = conn.execute("SELECT canonical_key,payload_json FROM signals").fetchone()
            assert row is not None
            self.assertEqual(row[0], "iwt:1038:2026-08-25")
            payload = json.loads(row[1])
            self.assertEqual(payload["signal_reason"], "ACTIONABLE_BASELINE_RECONCILIATION")
            self.assertEqual(payload["deadline"], "2026-11-03")



if __name__ == "__main__":
    unittest.main()
