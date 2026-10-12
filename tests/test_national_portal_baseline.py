"""S01 undated document cards must be eligible for first baseline acquisition."""
import unittest
from datetime import UTC, datetime
from signalforge.engine import _baseline_candidates
from signalforge.mpt import SitemapEntry

class NationalPortalBaselineTests(unittest.TestCase):
    def test_undated_opt_in(self):
        entries = [SitemapEntry("https://myanmar.gov.mm/documents/example", None)]
        source = {"baseline_lookback_days": 45, "baseline_detail_limit": 4,
                  "bootstrap_seed_urls": [], "baseline_include_undated": True}
        self.assertEqual(_baseline_candidates(entries, now=datetime(2026, 10, 12, tzinfo=UTC), source=source), entries)
        source["baseline_include_undated"] = False
        self.assertEqual(_baseline_candidates(entries, now=datetime(2026, 10, 12, tzinfo=UTC), source=source), [])
