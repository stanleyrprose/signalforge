"""S01 undated document cards must be eligible for first baseline acquisition."""
import sqlite3
import unittest
from datetime import UTC, datetime
from signalforge.engine import _baseline_candidates, _schedule_undated_discovery_recovery, _upsert_discovery_snapshot
from signalforge.mpt import SitemapEntry
from signalforge.national_portal_tender import PortalTender, _QTY, _MYANMAR_DIGITS

class NationalPortalBaselineTests(unittest.TestCase):
    def test_undated_opt_in(self):
        entries = [SitemapEntry("https://myanmar.gov.mm/documents/example", None)]
        source = {"baseline_lookback_days": 45, "baseline_detail_limit": 4,
                  "bootstrap_seed_urls": [], "baseline_include_undated": True}
        self.assertEqual(_baseline_candidates(entries, now=datetime(2026, 10, 12, tzinfo=UTC), source=source), entries)
        source["baseline_include_undated"] = False
        self.assertEqual(_baseline_candidates(entries, now=datetime(2026, 10, 12, tzinfo=UTC), source=source), [])

    def test_recover_only_never_fetched_undated_documents(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("""CREATE TABLE discovery_items(source_id TEXT,url TEXT,lastmod TEXT,
            fetched_lastmod TEXT,last_fetched_at TEXT,canonical_key TEXT,
            pending_since_at TEXT,suppress_signal_once INTEGER DEFAULT 0)""")
        for suffix, fetched in (("a", None), ("b", "2026-10-10")):
            conn.execute("INSERT INTO discovery_items(source_id,url,last_fetched_at) VALUES(?,?,?)",
                         ("S01", "https://myanmar.gov.mm/documents/" + suffix, fetched))
        entries = [SitemapEntry("https://myanmar.gov.mm/documents/" + x, None) for x in ("a", "b")]
        source = {"baseline_include_undated": True, "delta_detail_limit": 4}
        self.assertEqual(_schedule_undated_discovery_recovery(conn, "S01", source, entries, "2026-10-12"), 1)
        self.assertEqual(_schedule_undated_discovery_recovery(conn, "S01", source, entries, "2026-10-12"), 0)
        self.assertIsNotNone(conn.execute("SELECT pending_since_at FROM discovery_items WHERE url LIKE '%/a'").fetchone()[0])
        self.assertIsNone(conn.execute("SELECT pending_since_at FROM discovery_items WHERE url LIKE '%/b'").fetchone()[0])

    def test_undated_pending_survives_next_discovery_snapshot(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("""CREATE TABLE discovery_items(source_id TEXT,url TEXT,lastmod TEXT,
            fetched_lastmod TEXT,last_fetched_at TEXT,canonical_key TEXT,
            pending_since_at TEXT,suppress_signal_once INTEGER DEFAULT 0,
            first_seen_at TEXT,last_seen_at TEXT)""")
        entry = SitemapEntry("https://myanmar.gov.mm/documents/unfetched", None)
        _upsert_discovery_snapshot(conn, "S01", [entry], "2026-10-12", baseline=False)
        _upsert_discovery_snapshot(conn, "S01", [entry], "2026-10-13", baseline=False)
        self.assertEqual(conn.execute("SELECT pending_since_at FROM discovery_items").fetchone()[0], "2026-10-12")
        conn.execute("UPDATE discovery_items SET last_fetched_at='2026-10-13',pending_since_at=NULL")
        _upsert_discovery_snapshot(conn, "S01", [entry], "2026-10-14", baseline=False)
        self.assertIsNone(conn.execute("SELECT pending_since_at FROM discovery_items").fetchone()[0])

    def test_portal_quantity_unknown_is_not_a_rejection_reason(self):
        tender = PortalTender("https://myanmar.gov.mm/documents/123", "Ministry of Construction",
                              "Road repair", None, "2026-10-20", "Road repair", "abc")
        self.assertIsNone(tender.payload()["quantity_or_lot_summary"])
        self.assertEqual(tender.payload()["quantity_disclosure_status"], "NOT_EXTRACTED")

    def test_portal_quantity_myanmar_digits_and_no_word_prefix(self):
        self.assertEqual(_QTY.search("၁၂ ခု".translate(_MYANMAR_DIGITS)).group(0), "12 ခု")
        self.assertIsNone(_QTY.search("4 setting"))
