from __future__ import annotations

import unittest
from pathlib import Path

from signalforge.mpt import parse_sitemap, parse_tender_detail


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"


class MptParserTests(unittest.TestCase):
    def test_real_bangkok_tender_fixture(self) -> None:
        html = (FIXTURES / "mpt_tender_detail.html").read_bytes()
        url = "https://mpt.com.mm/en/purchasing-of-top-up-card-with-qr-code-4/"
        tender = parse_tender_detail(html, url)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.reference_no, "CCO-2026-001")
        self.assertEqual(tender.project_name, "Purchasing of Top-up Card with QR code")
        self.assertEqual(tender.publication_date, "2026-07-17")
        self.assertEqual(tender.deadline, "2026-08-06")
        self.assertEqual(tender.location, "Yangon,Myanmar")
        self.assertEqual(tender.canonical_key, "mpt:CCO-2026-001")
        self.assertIn("4 billion MMK", tender.company_size or "")
        self.assertEqual(tender.deadline_evidence, "EXPLICIT_HTML_DEADLINE_DATE")
        self.assertEqual(tender.deadline_candidates, ("2026-08-06",))
        self.assertEqual(tender.business_stage, "OPPORTUNITY")
        self.assertEqual(tender.detail_completeness, "HTML_BUSINESS_SCOPE_AND_DEADLINE")
        self.assertIn("Purchasing of Top-up Card", tender.scope_summary)
        self.assertEqual(tender.payload()["business_stage"], "OPPORTUNITY")


    def test_abbreviated_month_deadline_is_supported(self) -> None:
        html = b"""
        <html><body><table>
          <tr><td>Date</td><td>March 31, 2025</td></tr>
          <tr><td>Reference No</td><td>202503-CTO-022</td></tr>
          <tr><td>Project Name</td><td>Drive Test Pay As You Use FY2025&amp;2026</td></tr>
          <tr><td>Location</td><td>Entire Myanmar</td></tr>
          <tr><td>Required quantity</td><td>To be described in RFP document</td></tr>
        </table>
        <p>complete vendor registration before the deadline 10 th Apr 2025.</p>
        <p>Based on your information, we will conduct the Pre-Qualification stage.</p>
        </body></html>
        """
        tender = parse_tender_detail(html, "https://mpt.com.mm/en/drive-test/")
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.deadline, "2025-04-10")
        self.assertEqual(tender.business_stage, "OPPORTUNITY")
        self.assertEqual(tender.scope_summary, "Drive Test Pay As You Use FY2025&2026")
        self.assertEqual(tender.procurement_stage, "PRE_QUALIFICATION")

    def test_pre_publication_deadlines_fail_closed_as_official_conflict(self) -> None:
        html = b"""
        <html><body><table>
          <tr><td>Date</td><td>April 8, 2026</td></tr>
          <tr><td>Reference No</td><td>202604-CTO-029</td></tr>
          <tr><td>Project Name</td><td>BTS Battery Purchasing Project FY26</td></tr>
          <tr><td>Required quantity</td><td>Supply of 2V and 12V batteries for BTS sites.</td></tr>
        </table>
        <p>deadline 6 th March 2026.</p>
        <p>deadline 6 th March 2025.</p>
        </body></html>
        """
        tender = parse_tender_detail(html, "https://mpt.com.mm/en/bts-battery/")
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertIsNone(tender.deadline)
        self.assertEqual(tender.deadline_evidence, "OFFICIAL_HTML_DEADLINE_CONFLICT")
        self.assertEqual(tender.deadline_candidates, ("2026-03-06", "2025-03-06"))
        self.assertEqual(tender.business_stage, "TENDER_NOTICE")
        self.assertEqual(tender.detail_completeness, "HTML_BUSINESS_SCOPE_DEADLINE_CONFLICT")

    def test_stale_duplicate_deadline_is_ignored_when_one_valid_candidate_remains(self) -> None:
        html = b"""
        <html><body><table>
          <tr><td>Date</td><td>March 29, 2025</td></tr>
          <tr><td>Reference No</td><td>CCO-25-003</td></tr>
          <tr><td>Project Name</td><td>Purchasing of Local Top-up Card</td></tr>
        </table>
        <p>deadline 24 th April 2025.</p>
        <p>deadline 24 th Apr 2024.</p>
        </body></html>
        """
        tender = parse_tender_detail(html, "https://mpt.com.mm/en/topup/")
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.deadline, "2025-04-24")
        self.assertEqual(tender.deadline_candidates, ("2025-04-24", "2024-04-24"))
        self.assertEqual(tender.deadline_evidence, "EXPLICIT_HTML_DEADLINE_DATE")
        self.assertEqual(tender.business_stage, "OPPORTUNITY")

    def test_sitemap_is_official_english_discovery_filter(self) -> None:
        entries = parse_sitemap((FIXTURES / "mpt_page_sitemap.xml").read_bytes())
        self.assertEqual(len(entries), 2)
        urls = {item.url for item in entries}
        self.assertIn("https://mpt.com.mm/en/purchasing-of-top-up-card-with-qr-code-4/", urls)
        self.assertIn("https://mpt.com.mm/en/mpt4u/", urls)
        self.assertNotIn("https://mpt.com.mm/mm/purchasing-of-top-up-card-with-qr-code-3/", urls)

    def test_normal_page_is_not_tender(self) -> None:
        self.assertIsNone(parse_tender_detail(b"<html><h1>MPT4U</h1><p>consumer page</p></html>", "https://mpt.com.mm/en/mpt4u/"))


if __name__ == "__main__":
    unittest.main()
