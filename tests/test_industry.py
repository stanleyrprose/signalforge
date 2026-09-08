from __future__ import annotations

import unittest
from pathlib import Path

from signalforge.industry import parse_tender_detail, parse_tender_listing

ROOT = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://www.industrymsme.gov.mm/announcements"
DETAIL_URL = "https://www.industrymsme.gov.mm/announcements/1036"


class IndustryTests(unittest.TestCase):
    def test_listing_selects_current_tenders_with_native_ids(self) -> None:
        entries = parse_tender_listing((ROOT / "industry-listing.html").read_bytes())
        by_url = {entry.url: entry for entry in entries}
        self.assertGreaterEqual(len(entries), 16)
        self.assertEqual(by_url[DETAIL_URL].lastmod, "2026-09-03T00:00:00+06:30")
        self.assertIn("https://www.industrymsme.gov.mm/announcements/1033", by_url)
        self.assertIn("https://www.industrymsme.gov.mm/announcements/1027", by_url)

    def test_detail_extracts_business_scope_and_explicit_close_time(self) -> None:
        tender = parse_tender_detail((ROOT / "industry-1036.html").read_bytes(), DETAIL_URL)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "industry:1036")
        self.assertEqual(tender.reference_no, "INDUSTRY-ANN-1036")
        self.assertEqual(tender.publication_date, "2026-09-03")
        self.assertEqual(tender.deadline, "2026-09-24")
        self.assertEqual(tender.deadline_time, "16:00")
        self.assertEqual(tender.business_unit, "No.1 Heavy Industrial Enterprise")
        self.assertIn("Chemical Reagent", tender.scope_summary)
        self.assertIn("Sample Gas", tender.scope_summary)

    def test_detail_fails_closed_for_wrong_issuer_url(self) -> None:
        payload = (ROOT / "industry-1036.html").read_bytes()
        self.assertIsNone(parse_tender_detail(payload, "https://example.com/announcements/1036"))


if __name__ == "__main__":
    unittest.main()
