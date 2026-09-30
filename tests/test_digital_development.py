from __future__ import annotations

import unittest
from pathlib import Path

from signalforge.config import Registry
from signalforge.digital_development import (
    parse_digital_development_listing,
    parse_digital_development_text,
)
from signalforge.source_adapters import ADAPTERS

ROOT = Path(__file__).resolve().parents[1]
URL = "https://myanmar.gov.mm/documents/20143/0/newspaper+%287%29.pdf/bbf2a100-02b1-4024-716f-e1763c2556d1"


class DigitalDevelopmentTests(unittest.TestCase):
    def test_listing_selects_only_ddd_portal_document(self) -> None:
        html = f"""
        <html><body>
          <div class="smallcardstyle">
            <a href="{URL}"><h2>ဒီဂျစ်တယ်ဖွံ့ဖြိုးတိုးတက်ရေးဦးစီးဌာန၏ အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း</h2></a>
            <p><span class="graycolor">Agency:</span><span class="blueColor1">Ministry of Digital Development and Communications</span></p>
            <p><span class="graycolor">Closing Date:</span><span class="blueColor1">16 October 2026</span></p>
          </div>
          <div class="smallcardstyle">
            <a href="https://example.test/other"><h2>Other tender</h2></a>
            <p><span class="graycolor">Agency:</span><span class="blueColor1">Other Agency</span></p>
            <p><span class="graycolor">Closing Date:</span><span class="blueColor1">16 October 2026</span></p>
          </div>
        </body></html>
        """.encode()
        entries = parse_digital_development_listing(html)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].url, URL)
        self.assertEqual(entries[0].lastmod, "2026-10-16T00:00:00+06:30")

    def test_text_parser_builds_actionable_tender(self) -> None:
        text = """
        ဒီဂျစ်တယ်ဖွံ့ဖြိုးတိုးတက်ရေးဦးစီးဌာန
        အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း၊ တင်ဒါအမှတ်စဉ် (DD – ၁ /၂၀၂၆)
        Supply of Shared ICT Hardware for the mmGov Platform and the Public Service Exchange Platform (Phase -1)
        Switch များအား ဝယ်ယူလိုပါသည်။
        တင်ဒါပုံစံ စတင်ရောင်းချမည့်ရက် - ၁-၁၀-၂၀၂၆
        တင်ဒါပုံစံ အရောင်းပိတ်မည့်ရက် - ၁၅-၁၀-၂၀၂၆
        တင်ဒါပုံစံတစ်စုံကျသင့်ငွေ - ကျပ် ၁၀,၀၀၀/-
        တင်ဒါနောက်ဆုံးတင်သွင်းရမည့် - ၁၆-၁၀-၂၀၂၆ (၁၃:၀၀) နာရီ
        """
        tender = parse_digital_development_text(text, URL)
        self.assertIsNotNone(tender)
        assert tender is not None
        payload = tender.payload()
        self.assertEqual(tender.canonical_key, "digital-development:dd-1/2026")
        self.assertEqual(payload["reference_no"], "DD-1/2026")
        self.assertEqual(payload["deadline"], "2026-10-16")
        self.assertEqual(payload["deadline_time"], "13:00")
        self.assertEqual(payload["tender_document_fee_mmk"], 10000)
        self.assertEqual(payload["evidence_level"], "OFFICIAL_TEXT_PDF")
        self.assertIn("budget not disclosed", str(payload["price_or_budget_summary"]).lower())
        self.assertIn("tender form fee: MMK 10,000", str(payload["price_or_budget_summary"]))
        self.assertIn("Switch", str(payload["scope_excerpt"]))
        self.assertTrue(payload["quantity_or_lot_summary"])

    def test_future_server_tender_is_not_hard_coded_to_switch(self) -> None:
        text = """
        ဒီဂျစ်တယ်ဖွံ့ဖြိုးတိုးတက်ရေးဦးစီးဌာန
        အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း၊ တင်ဒါအမှတ်စဉ် (DD-၂/၂၀၂၆)
        Supply of Data Center Server Hardware အတွက် Server 12 Units ဝယ်ယူမည်။
        တင်ဒါပုံစံ စတင်ရောင်းချမည့်ရက် - ၁-၁၁-၂၀၂၆
        တင်ဒါပုံစံ အရောင်းပိတ်မည့်ရက် - ၁၅-၁၁-၂၀၂၆
        တင်ဒါနောက်ဆုံးတင်သွင်းရမည့် - ၁၆-၁၁-၂၀၂၆ (၁၄:၃၀) နာရီ
        နေပြည်တော်
        """
        tender = parse_digital_development_text(text, URL)
        self.assertIsNotNone(tender)
        assert tender is not None
        payload = tender.payload()
        self.assertEqual(payload["reference_no"], "DD-2/2026")
        self.assertIn("Data Center Server Hardware", str(payload["title"]))
        self.assertIn("Server", str(payload["scope_summary"]))
        self.assertEqual(payload["quantity_or_lot_summary"], "12 Units")
        self.assertEqual(payload["deadline"], "2026-11-16")
        self.assertEqual(payload["deadline_time"], "14:30")

    def test_registry_activates_s51_with_pdf_detail(self) -> None:
        registry = Registry.load(ROOT)
        source = registry.source("S51")
        self.assertTrue(source["enabled"])
        self.assertEqual(source["adapter"], "digital_development_tender")
        self.assertEqual(source["detail_target_kind"], "PDF")
        self.assertEqual(source["engine"], "direct_http")
        self.assertNotIn("S51", registry.raw.get("deferred_sources", {}))
        adapter = ADAPTERS["digital_development_tender"]
        self.assertEqual(adapter.detail_parser_version, "ddd-issuer-text-pdf-v1")


if __name__ == "__main__":
    unittest.main()
