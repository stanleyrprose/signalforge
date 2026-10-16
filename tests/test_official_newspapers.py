"""Official MOI newspaper sources: issue retrieval only + conservative tender gate."""
from __future__ import annotations

import io
import unittest

from pypdf import PdfWriter

from signalforge.config import Registry
from signalforge.official_newspapers import (
    parse_kyemon_issues, parse_myanma_alinn_issues,
    parse_official_newspaper_pdf,
)


class OfficialNewspaperSourcesTests(unittest.TestCase):
    def test_two_issues_are_discovered_independently(self):
        km = b'''<html><a href="/km/16-october-26">16 October 26</a>
        <a href="/km/file-download/download/public/5395">Download</a>
        <a href="/km/15-october-26">15 October 26</a>
        <a href="/km/file-download/download/public/5393">Download</a></html>'''
        mal = b'''<html><a href="/mal/16-oct-26">16 Oct 26</a>
        <a href="/mal/file-download/download/public/5762">Download</a></html>'''
        self.assertEqual(
            [e.url for e in parse_kyemon_issues(km)],
            ["https://www.moi.gov.mm/km/file-download/download/public/5395",
             "https://www.moi.gov.mm/km/file-download/download/public/5393"],
        )
        self.assertEqual(
            [e.url for e in parse_myanma_alinn_issues(mal)],
            ["https://www.moi.gov.mm/mal/file-download/download/public/5762"],
        )

    def test_untrusted_downloads_cannot_enter_discovery(self):
        html = b'''<a href="/km/16-october-26">16 October 26</a>
        <a href="https://example.com/km/file-download/download/public/5395">Download</a>'''
        with self.assertRaisesRegex(ValueError, "no official"):
            parse_kyemon_issues(html)

    def test_newspaper_pdf_without_proven_tender_does_not_create_candidate(self):
        pdf = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=300)
        writer.write(pdf)
        self.assertEqual(
            parse_official_newspaper_pdf(
                pdf.getvalue(),
                "https://www.moi.gov.mm/km/file-download/download/public/5395",
            ), []
        )
        self.assertEqual(
            parse_official_newspaper_pdf(
                pdf.getvalue(),
                "https://example.com/foreign.pdf",
            ), []
        )

    def test_two_registry_sources_use_pdf_details_and_daily_cycle(self):
        d = Registry.load(__import__("pathlib").Path(__file__).resolve().parents[1])
        for source_id, path in (("S52", "/km/"), ("S53", "/mal/")):
            source = d.raw["sources"][source_id]
            self.assertEqual(source["poll_interval_seconds"], 86400)
            self.assertEqual(source["detail_target_kind"], "PDF")
            self.assertEqual(source["engine"], "direct_http")
            self.assertTrue(source["discovery_url"].endswith(path))
            self.assertFalse(source["first_baseline_customer_signal"])


if __name__ == "__main__":
    unittest.main()
