from __future__ import annotations

import unittest

from signalforge.source_scorecard import PORTFOLIO_TIERS
from signalforge.yangon_construction import parse_tender_detail, parse_tender_listing


class ConstructionTenderSourceTests(unittest.TestCase):
    def test_yangon_construction_selects_tender_and_parses_deadline(self) -> None:
        listing = b'''<html><body>
        <article id="post-3691" class="post category-ministry-of-construction category-tenders">
          <h2 class="entry-title"><a href="https://www.yangon.gov.mm/road-open-tender/">Road Department (1/2026-2027) Open Tender</a></h2>
          <span class="updated">2026-06-09T19:12:02+06:30</span>
        </article>
        <article id="post-2057"><h2 class="entry-title"><a href="https://www.yangon.gov.mm/covid/">COVID update</a></h2></article>
        </body></html>'''
        entries = parse_tender_listing(listing)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].url, "https://www.yangon.gov.mm/road-open-tender/")

        detail = '''<html><head><meta property="article:published_time" content="2026-06-09T19:12:02+06:30"></head>
        <body class="postid-3691"><h1 class="entry-title">Road Department (1/2026-2027) Open Tender</h1>
        <div class="entry-content"><p>Road and bridge construction.</p>
        <p>တင်ဒါလျှောက်လွှာတင်သွင်းရမည့် ရက် - (၁၅.၆.၂၀၂၆) ရက်နေ့မှ (၂၄.၆.၂၀၂၆) ရက်နေ့အထိ</p></div></body></html>'''.encode()
        item = parse_tender_detail(detail, entries[0].url)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.canonical_key, "yangon-construction:3691")
        self.assertEqual(item.publication_date, "2026-06-09")
        self.assertEqual(item.deadline, "2026-06-24")
        self.assertEqual(item.item_kind, "TENDER")
        self.assertEqual(item.payload()["relevance_categories"], ["CONSTRUCTION"])

    def test_construction_tender_remains_in_scorecard_portfolio(self) -> None:
        self.assertEqual(PORTFOLIO_TIERS["S43"], "STRATEGIC_WATCH")
        self.assertNotIn("S44", PORTFOLIO_TIERS)
        self.assertNotIn("S45", PORTFOLIO_TIERS)
        self.assertNotIn("S48", PORTFOLIO_TIERS)


if __name__ == "__main__":
    unittest.main()
