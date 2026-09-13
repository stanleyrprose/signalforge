from __future__ import annotations

import unittest
from pathlib import Path

from signalforge.industry import parse_tender_detail, parse_tender_listing

ROOT = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://www.industrymsme.gov.mm/announcements"
DETAIL_URL = "https://www.industrymsme.gov.mm/announcements/1036"


def _detail_html(*, title: str, date: str, body: str) -> bytes:
    return f"""<html><body>
    <h3 class="title-bg">{title}</h3>
    <span class="date">{date}</span>
    <span class="author">Official business unit</span>
    <div class="member-desc"><p>{body}</p></div>
    </body></html>""".encode("utf-8")


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


    def test_detail_accepts_live_issuer_close_label_variants(self) -> None:
        cases = [
            (
                "1042",
                "အမှတ်(၃)အကြီးစားစက်မှုလုပ်ငန်း၊ အမှတ်(၈)အထည်စက်ရုံခွဲ (ရမည်းသင်း)တွင် ၁/၇ ပီစီချည်(ရောင်စုံ) ၄၉,၄၆ဝ ပေါင် ဝယ်ယူရန် အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
                "Fri 11-09-2026",
                "တင်ဒါစတင်ရောင်းချမည့်ရက် - ၁၁-၉-၂၀၂၆ (၉:၃၀)နာရီ တင်ဒါပိတ်ရက် - ၁၈-၉-၂၀၂၆ (၁၆:၃၀)နာရီ",
                "2026-09-18",
                "16:30",
            ),
            (
                "1040",
                "အမှတ်(၁)အကြီးစားစက်မှုလုပ်ငန်း၊ အမှတ်(၁)သံမဏိစက်ရုံ(မြင်းခြံ)ရှိ သံရည်ပျက်တုံး (၅၀၀)တန် ဖြတ်တောက်ခြင်းလုပ်ငန်းကို လုပ်ငန်းအပ်နှံဆောင်ရွက်လိုပါသဖြင့် အိတ်ဖွင့်တင်ဒါဖိတ်ခေါ်ခြင်း",
                "Tue 08-09-2026",
                "တင်ဒါပုံစံစတင်ရောင်းချမည့်ရက် - ၈- ၉ - ၂ဝ၂၆ ရက် (ရုံးချိန်အတွင်း) တင်ဒါပိတ်ရက် - ၂၃ - ၉ - ၂ဝ၂၆ ရက် (၁၆ : ၀၀)နာရီ",
                "2026-09-23",
                "16:00",
            ),
            (
                "1038",
                "မြန်မာ့ဆေးဝါးလုပ်ငန်းမှ ဆေးဝါးကုန်ကြမ်းနှင့် ထုပ်ပိုးခွံများ သယ်ယူပို့ဆောင်ရန် ကုန်သေတ္တာတင်ယာဉ် ငှားရမ်းခ အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
                "Mon 07-09-2026",
                "ဈေးနှုန်းတင်သွင်းလွှာပုံစံများ စတင်ရောင်းချမည့်ရက် - ၇. ၉ .၂၀၂၆ တင်ဒါပိတ်မည့်ရက်နှင့်အချိန် - ၆. ၁၀.၂၀၂၆ ၊ (၁၆:၀၀)နာရီ",
                "2026-10-06",
                "16:00",
            ),
            (
                "1026",
                "Fluid Control Unit ပစ္စည်း (၁၀) မျိုး ဝယ်ယူရန် အိတ်ဖွင့်တင်ဒါ ခေါ်ယူခြင်း",
                "Fri 28-08-2026",
                "တင်ဒါပိတ်ရက်နှင့်အချိန် - (၁၄.၉.၂၀၂၆) ရက်နေ့၊ (၁၆း၀၀)နာရီ",
                "2026-09-14",
                "16:00",
            ),
            (
                "1032",
                "ဆောက်လုပ်ရေးလုပ်ငန်း အိတ်ဖွင့်တင်ဒါ (သက်တမ်းတိုး) ခေါ်ယူခြင်း",
                "Fri 28-08-2026",
                "တင်ဒါပိတ်သိမ်းမည့် ရက်နှင့်အချိန် - (၁၀.၉.၂၀၂၆) ရက်နေ့၊ (၁၆း၀၀) နာရီ",
                "2026-09-10",
                "16:00",
            ),
            (
                "1024",
                "အားကစားရုံ ပြင်ဆင်ခြင်းလုပ်ငန်း အိတ်ဖွင့်တင်ဒါ (သက်တမ်းတိုး) ခေါ်ယူခြင်း",
                "Thu 27-08-2026",
                "တင်ဒါပိတ်မည့်နေ့ရက်၊ အချိန် - (၄.၉.၂၀၂၆)ရက်နေ့ (၁၆း၀၀)နာရီအထိ",
                "2026-09-04",
                "16:00",
            ),
            (
                "1023",
                "ဓာတ်ခွဲခန်းသုံးစက်ပစ္စည်းများ ဝယ်ယူတပ်ဆင်ခြင်းဆောင်ရွက်ရန် အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
                "Mon 24-08-2026",
                "တင်ဒါပိတ်မည့်ရက်နှင့်အချိန် - (၁၈. ၉. ၂၀၂၆) ရက်နေ့ (၁၆း၀၀)နာရီ",
                "2026-09-18",
                "16:00",
            ),
        ]
        for record_id, title, date, body, expected_date, expected_time in cases:
            with self.subTest(record_id=record_id):
                tender = parse_tender_detail(
                    _detail_html(title=title, date=date, body=body),
                    f"https://www.industrymsme.gov.mm/announcements/{record_id}",
                )
                self.assertIsNotNone(tender)
                assert tender is not None
                self.assertEqual(tender.deadline, expected_date)
                self.assertEqual(tender.deadline_time, expected_time)

    def test_detail_does_not_treat_sale_date_as_deadline_without_close_label(self) -> None:
        payload = _detail_html(
            title="အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
            date="Fri 11-09-2026",
            body="တင်ဒါစတင်ရောင်းချမည့်ရက် - ၁၁-၉-၂၀၂၆ (၉:၃၀)နာရီ",
        )
        self.assertIsNone(parse_tender_detail(payload, "https://www.industrymsme.gov.mm/announcements/9999"))

    def test_detail_fails_closed_for_wrong_issuer_url(self) -> None:
        payload = (ROOT / "industry-1036.html").read_bytes()
        self.assertIsNone(parse_tender_detail(payload, "https://example.com/announcements/1036"))


if __name__ == "__main__":
    unittest.main()
