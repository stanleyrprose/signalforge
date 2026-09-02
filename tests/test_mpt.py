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
