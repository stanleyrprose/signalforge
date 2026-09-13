from __future__ import annotations

import json
import unittest

from signalforge.atom_network import parse_network_records as parse_atom_network_records
from signalforge.mpt_network import parse_network_records as parse_mpt_network_records
from signalforge.source_scorecard import PORTFOLIO_TIERS
from signalforge.yangon_construction import parse_tender_detail, parse_tender_listing


class ConstructionTelecomSourceTests(unittest.TestCase):
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

    def test_atom_api_filters_for_network_technology(self) -> None:
        payload = json.dumps({"media": {"data": [
            {"id": 625, "slug": "scholarship", "type": {"key": 2}, "date": "25 Aug, 2026", "publish_time": "2026-08-25 12:00:00", "title": "Scholarship", "description": "Student support", "keywords": "education"},
            {"id": 620, "slug": "atom-network-future", "type": {"key": 2}, "date": "19 Jun, 2026", "publish_time": "2026-06-19 12:00:00", "title": "ATOM strengthens 4G network", "description": "Modernizing radio, core, transport, fiber and cloud infrastructure", "keywords": "network readiness 5G"},
        ]}}).encode()
        items = parse_atom_network_records(payload)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.canonical_key, "atom-network:620")
        self.assertEqual(item.publication_date, "2026-06-19")
        self.assertEqual(item.item_kind, "REGULATORY_NOTICE")
        self.assertEqual(item.payload()["telecom_signal_kind"], "NETWORK_TECHNOLOGY")
        self.assertEqual(item.url, "https://www.atom.com.mm/en/press-release/atom-network-future")

    def test_new_sources_begin_as_strategic_watch(self) -> None:
        self.assertEqual(PORTFOLIO_TIERS["S43"], "STRATEGIC_WATCH")
        self.assertEqual(PORTFOLIO_TIERS["S44"], "STRATEGIC_WATCH")
        self.assertEqual(PORTFOLIO_TIERS["S45"], "STRATEGIC_WATCH")

    def test_mpt_listing_filters_for_network_technology(self) -> None:
        html = b'''<html><body>
        <div class="pressrelease_box"><div class="pressrelease_des">
          <span class="date">Published 24 Jul 2026</span><div class="press_info"><h4 class="main-title">TeamFit Yoga</h4><p>Employee well-being.</p><a class="btn-blue" href="https://mpt.com.mm/en/teamfit/">Read More</a></div>
        </div></div>
        <div class="pressrelease_box"><div class="pressrelease_des">
          <span class="date">Published 14 Jul 2026</span><div class="press_info"><h4 class="main-title">MPT Brings Stronger Connections with Expanded Network</h4><p>27 new network sites and nine 4G LTE upgrades.</p><a class="btn-blue" href="https://mpt.com.mm/en/expanded-network/">Read More</a></div>
        </div></div>
        </body></html>'''
        items = parse_mpt_network_records(html)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.canonical_key, "mpt-network:expanded-network")
        self.assertEqual(item.publication_date, "2026-07-14")
        self.assertEqual(item.item_kind, "REGULATORY_NOTICE")
        self.assertEqual(item.payload()["relevance_categories"], ["TELECOM"])


if __name__ == "__main__":
    unittest.main()
