from __future__ import annotations

import unittest

from signalforge.official_media import (
    OfficialMediaParseError,
    extract_gnlm_pdf_urls,
    parse_gnlm_listing,
    parse_gnlm_text_signal,
    parse_mdn_detail,
    parse_mdn_listing,
    parse_mitv_detail,
    parse_mitv_listing,
)
from signalforge.source_adapters import ADAPTERS, SourceAdapterError

MITV_URL = "https://www.myanmaritv.com/news/e-government-implementation-vice-president-addresses-coordination-meeting"
MDN_PATH = "/my/duttiysmmtt-uunnyiuceaa-e-government-uucheaangkeaamttii-nnyiniungacnnyawe12026-siu"
MDN_URL = "https://mdn.gov.mm" + MDN_PATH
GNLM_URL = "https://www.moi.gov.mm/nlm/30-september-2026"


class OfficialMediaParserTests(unittest.TestCase):
    def test_mitv_listing_and_detail_capture_digital_government_signal(self) -> None:
        listing = b"""
        <div class="view-news-page-list">
          <div class="views-row views-row-1">
            <span class="date-display-single" content="2026-09-30T09:55:00+06:30">30 September 2026</span>
            <div class="title"><a href="/news/e-government-implementation-vice-president-addresses-coordination-meeting">
              e-Government Implementation: Vice President addresses coordination meeting
            </a></div>
          </div>
          <div class="views-row views-row-2">
            <span class="date-display-single" content="2026-09-30T12:00:00+06:30">30 September 2026</span>
            <div class="title"><a href="/news/friendly-football-match">Friendly football match</a></div>
          </div>
        </div>
        """
        entries = parse_mitv_listing(listing)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].url, MITV_URL)
        self.assertEqual(entries[0].lastmod, "2026-09-30T09:55:00+06:30")

        detail = b"""
        <article class="node node-news">
          <span property="dc:title" content="e-Government Implementation: Vice President addresses coordination meeting"></span>
          <span class="date-display-single" content="2026-09-30T09:55:00+06:30">30 September 2026</span>
          <div class="field field-name-body"><div class="body">
            The government will implement e-Government and transition to Digital Government through
            Public-Private Partnership (PPP) frameworks. Single Window and One-Stop Digital Services
            platforms, information security and cybersecurity, the National Digital Development
            Strategy 2030 and the Digital Development Law were discussed.
          </div></div>
        </article>
        """
        item = parse_mitv_detail(detail, MITV_URL)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.publication_date, "2026-09-30")
        self.assertEqual(item.precursor_stage_hint, "PPP_FORMATION")
        self.assertIn("DIGITAL_GOVERNMENT", item.relevance_categories)
        self.assertIn("CYBERSECURITY", item.relevance_categories)
        self.assertEqual(item.payload()["business_stage"], "PROJECT_PRECURSOR_CANDIDATE")

    def test_mitv_irrelevant_or_open_tender_is_rejected(self) -> None:
        irrelevant = b"""
        <span property="dc:title" content="Sports exchange programme"></span>
        <span class="date-display-single" content="2026-09-30T09:55:00+06:30"></span>
        <div class="field field-name-body">Teams played a friendly football match.</div>
        """
        self.assertIsNone(parse_mitv_detail(irrelevant, MITV_URL))
        tender = b"""
        <span property="dc:title" content="Digital Government open tender"></span>
        <span class="date-display-single" content="2026-09-30T09:55:00+06:30"></span>
        <div class="field field-name-body">Invitation to tender for an e-Government platform is now open.</div>
        """
        self.assertIsNone(parse_mitv_detail(tender, MITV_URL))

    def test_mdn_listing_and_detail_capture_burmese_e_government_signal(self) -> None:
        listing = f"""
        <div class="view-content-wrap">
          <div class="item"><div class="views-field"><span class="field-content">
            <div class="card mb-3 shadow"><div class="card-body">
              <h5 class="card-title"><a href="{MDN_PATH}">ဒုတိယသမ္မတ ဦးညိုစော e-Government ဦးဆောင်ကော်မတီ ညှိနှိုင်းအစည်းအဝေး</a></h5>
              <p class="card-text"><i class="fa fa-clock-o"></i>30/09/26</p>
            </div></div>
          </span></div></div>
        </div>
        """.encode()
        entries = parse_mdn_listing(listing)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].url, MDN_URL)
        self.assertEqual(entries[0].lastmod, "2026-09-30T00:00:00+06:30")

        detail = f"""
        <html><head>
          <meta property="og:title" content="ဒုတိယသမ္မတ ဦးညိုစော e-Government ဦးဆောင်ကော်မတီ ညှိနှိုင်းအစည်းအဝေး">
          <link rel="canonical" href="{MDN_URL}">
        </head><body>
          <div class="post-meta"><span class="fa fa-calendar">Sep 30,2026</span><span class="post-created">10:27</span></div>
          <div property="schema:text" class="field field--name-body">
            e-Government လုပ်ငန်းစဉ်များကို အကောင်အထည်ဖော်ပြီး Digital Government သို့ ကူးပြောင်းရန်
            Public-Private Partnership (PPP) မူဘောင်၊ Single Window၊ One-Stop Digital Services Platform၊
            cybersecurity နှင့် Digital Development Strategy 2030 ကို ဆွေးနွေးသည်။
          </div>
        </body></html>
        """.encode()
        item = parse_mdn_detail(detail, MDN_URL)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.publication_date, "2026-09-30")
        self.assertIn("DIGITAL_GOVERNMENT", item.relevance_categories)
        self.assertEqual(item.precursor_stage_hint, "PPP_FORMATION")

    def test_gnlm_listing_attachment_and_text_filter(self) -> None:
        listing = b"""
        <div class="views-row"><div class="news-container">
          <div class="a-title"><a href="/nlm/30-september-2026">30 September 2026</a></div>
          <div class="a-pdf"><a href="/nlm/file-download/download/public/5478" type="application/pdf">Download</a></div>
        </div></div>
        """
        entries = parse_gnlm_listing(listing)
        self.assertEqual([(e.url, e.lastmod) for e in entries], [
            (GNLM_URL, "2026-09-30T00:00:00+06:30")
        ])

        issue = b"""
        <a class="download-pdf" href="http://www.moi.gov.mm/nlm/sites/default/files/newspaper-pdf/2026-09/30%20September%202026.pdf">Download</a>
        """
        urls = extract_gnlm_pdf_urls(issue, GNLM_URL)
        self.assertEqual(urls, [
            "https://www.moi.gov.mm/nlm/sites/default/files/newspaper-pdf/2026-09/30%20September%202026.pdf"
        ])

        text = """
        Vice-President U Nyo Saw chairs the e-Government Steering Committee.
        Push to Transition from E-Government to Digital Governance
        The government highlighted effective implementation of e-government processes and
        transition to a digital government. Public-Private Partnership (PPP) frameworks,
        Single Window and One-Stop Digital Services Platforms, information security,
        cybersecurity, the National Digital Development Strategy 2030 and Digital Development Law
        will support the programme.
        """
        item = parse_gnlm_text_signal(text, page_url=GNLM_URL)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.title, "Push to Transition from E-Government to Digital Governance")
        self.assertEqual(item.publication_date, "2026-09-30")
        self.assertEqual(item.precursor_stage_hint, "PPP_FORMATION")
        self.assertIn("DIGITAL_GOVERNMENT", item.relevance_categories)
        self.assertIsNone(parse_gnlm_text_signal(
            "Football teams met for a friendly match and cultural exchange.",
            page_url=GNLM_URL,
        ))

    def test_gnlm_adapter_fails_closed_without_required_pdf(self) -> None:
        adapter = ADAPTERS["official_media_gnlm"]
        with self.assertRaisesRegex(SourceAdapterError, "requires"):
            adapter.parse_detail(b"<html></html>", GNLM_URL)
        with self.assertRaises(OfficialMediaParseError):
            from signalforge.official_media import parse_gnlm_detail_with_attachments
            parse_gnlm_detail_with_attachments(b"<html></html>", GNLM_URL, [])


if __name__ == "__main__":
    unittest.main()
