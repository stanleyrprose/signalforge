from __future__ import annotations

import unittest

from signalforge.construction_project_precursor import (
    ConstructionProjectPrecursorParseError,
    parse_project_detail,
    parse_project_listing,
)

LIST_ID = "f87c94b0-d396-11ec-a8be-e9291a621227"
CYBER_ID = "d2b2b0b0-a74b-11f1-8072-0dacc5c29ae0"
CYBER_URL = f"https://construction.gov.mm/new-detail/{CYBER_ID}"
ROAD_ID = "30c35050-afec-11f1-9bf7-fd9ee667c8de"
ROAD_URL = f"https://construction.gov.mm/new-detail/{ROAD_ID}"
OVERPASS_ID = "11111111-2222-3333-4444-555555555555"
OVERPASS_URL = f"https://construction.gov.mm/new-detail/{OVERPASS_ID}"


def _card(*, record_id: str, title: str, date: str = "Sep 03 2026") -> str:
    return f"""
    <div class="card shadow mb-3">
      <div class="row g-0">
        <div class="col-md-8">
          <div class="card-body">
            <a href="https://construction.gov.mm/new-detail/{record_id}"
               class="card-title head-4 fw-bolder sidemenu">{title}</a>
            <p class="card-text mt-2 mb-1 news-p">summary</p>
            <p class="card-text"><small class="text-muted">{date}</small></p>
          </div>
        </div>
      </div>
    </div>
    """


def _listing(*cards: str) -> bytes:
    return ("<html><body>" + "".join(cards) + "</body></html>").encode()


def _detail(*, title: str, primary: str, later: str = "", date: str = "Sep 03 2026") -> bytes:
    return f"""
    <html><body>
      <main>
        <div class="px-2 px-sm-2 px-md-5 mb-5 custom-container summernote_content">
          <div class="col-md-12">
            <div class="card mt-4">
              <h5 class="fw-bolder mt-4 mb-4 text-center head-3 mx-4">{title}</h5>
              <div class="row mt-2">
                <div class="col-md-11 mx-auto">
                  <p>နေပြည်တော် စက်တင်ဘာ ၁</p>
                  <p>{primary}</p>
                  <p>{later}</p>
                </div>
              </div>
              <p class="card-text mb-5 me-4">
                <small class="text-primary float-end">{date}</small>
              </p>
            </div>
          </div>
        </div>
      </main>
    </body></html>
    """.encode()


class ConstructionProjectPrecursorParserTests(unittest.TestCase):
    def test_listing_routes_exact_project_approval_and_planned_capital_work(self) -> None:
        html = _listing(
            _card(
                record_id=CYBER_ID,
                title="ရတနာပုံဆိုက်ဘာစီးတီးစီမံကိန်း ကြီးကြပ်မှုကော်မတီ၏ ခွင့်ပြုချက်ဖြင့် စီမံကိန်းလုပ်ငန်းများကို အကောင်အထည်ဖော်ဆောင်ရွက်ရန်",
            ),
            _card(
                record_id=OVERPASS_ID,
                title="သာစည်နှင့် ပျော်ဘွယ်မြို့တို့တွင် ရထားလမ်းခုံးကျော်တံတားများ တည်ဆောက်မည်",
                date="Sep 20 2026",
            ),
        )
        entries = parse_project_listing(html)
        self.assertEqual([entry.url for entry in entries], [CYBER_URL, OVERPASS_URL])
        self.assertEqual(entries[0].lastmod, "2026-09-03T00:00:00+06:30")

    def test_listing_rejects_generic_cooperation_and_started_work(self) -> None:
        html = _listing(
            _card(
                record_id=ROAD_ID,
                title="မြန်မာ - အိန္ဒိယ နှစ်နိုင်ငံ လမ်းပန်းဆက်သွယ်ရေးကဏ္ဍ အကောင်အထည်ဖော်ဆောင်ရွက်မည့် လုပ်ငန်းစဉ်များ ဆွေးနွေး",
                date="Sep 14 2026",
            ),
            _card(
                record_id="87a6be60-b0b7-11f1-8d3d-c595813e041f",
                title="ရန်ကုန် - မန္တလေး အမြန်လမ်း ပြုပြင်ထိန်းသိမ်းခြင်းလုပ်ငန်းများ ဆောင်ရွက်လျက်ရှိ",
                date="Sep 15 2026",
            ),
            _card(
                record_id="64217930-a74b-11f1-aa24-cb9383822e2f",
                title="ဝန်ထမ်းအိမ်ရာများ အစားထိုးပြန်လည်တည်ဆောက်လျက်ရှိ",
                date="Sep 03 2026",
            ),
        )
        self.assertEqual(parse_project_listing(html), [])

    def test_detail_accepts_cyber_city_primary_project_even_when_later_paragraph_mentions_other_started_work(self) -> None:
        title = (
            "ရတနာပုံဆိုက်ဘာစီးတီးစီမံကိန်း ကြီးကြပ်မှုကော်မတီ၏ ခွင့်ပြုချက်ဖြင့် "
            "စီမံကိန်းလုပ်ငန်းများကို အကောင်အထည်ဖော်ဆောင်ရွက်ရန်"
        )
        primary = (
            "ရတနာပုံဆိုက်ဘာစီးတီးစီမံကိန်းကြီးကြပ်မှုကော်မတီ၏ ခွင့်ပြုချက်ဖြင့် "
            "စီမံကိန်းလုပ်ငန်းများကို အကောင်အထည်ဖော်ဆောင်ရွက်ရန် ဒုတိယဝန်ကြီးက မှာကြားသည်။"
        )
        later = (
            "ယမန်နေ့က ဝန်ထမ်းအိမ်ရာများ အသစ်ပြန်လည်တည်ဆောက်နေသည့် လုပ်ငန်းခွင်ကို "
            "ကြည့်ရှုစစ်ဆေးခဲ့ပြီး တံတားတည်ဆောက်ရေးစီမံကိန်းလုပ်ငန်းခွင်ကိုလည်း ကြည့်ရှုခဲ့သည်။"
        )
        item = parse_project_detail(_detail(title=title, primary=primary, later=later), CYBER_URL)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.canonical_key, f"construction-project:{CYBER_ID}")
        self.assertEqual(item.publication_date, "2026-09-03")
        self.assertEqual(item.precursor_stage_hint, "APPROVAL")
        self.assertIn("TELECOM", item.relevance_categories)
        payload = item.payload()
        self.assertEqual(payload["business_stage"], "PROJECT_PRECURSOR_CANDIDATE")
        self.assertTrue(payload["precursor_review_required"])
        self.assertEqual(payload["selection_policy_version"], 1)

    def test_detail_accepts_planned_overpass_without_literal_project_word(self) -> None:
        title = "သာစည်နှင့် ပျော်ဘွယ်မြို့တို့တွင် ရထားလမ်းခုံးကျော်တံတားများ တည်ဆောက်မည်"
        primary = "လမ်းပန်းဆက်သွယ်ရေးကောင်းမွန်စေရန် ခုံးကျော်တံတားနှစ်စင်း တည်ဆောက်ရန် လျာထားသည်။"
        item = parse_project_detail(
            _detail(title=title, primary=primary, date="Sep 20 2026"),
            OVERPASS_URL,
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertIn("CONSTRUCTION", item.relevance_categories)

    def test_detail_rejects_generic_bilateral_framework_without_exact_project_identity(self) -> None:
        title = "မြန်မာ - အိန္ဒိယ နှစ်နိုင်ငံ လမ်းပန်းဆက်သွယ်ရေးကဏ္ဍ အကောင်အထည်ဖော်ဆောင်ရွက်မည့် လုပ်ငန်းစဉ်များ ဆွေးနွေး"
        body = (
            "နှစ်နိုင်ငံ ပူးပေါင်းဆောင်ရွက်မည့် လမ်းပန်းဆက်သွယ်ရေးလုပ်ငန်းစဉ်များနှင့် "
            "Quick Impact Project စီမံကိန်းလုပ်ငန်းများကို ဆွေးနွေးသည်။"
        )
        self.assertIsNone(parse_project_detail(_detail(title=title, primary=body), ROAD_URL))

    def test_detail_rejects_started_primary_project_and_open_tender(self) -> None:
        title = "ရန်ကုန် - မန္တလေး အမြန်လမ်း တံတားတည်ဆောက်ရေးစီမံကိန်း"
        underway = "တံတားတည်ဆောက်ရေးစီမံကိန်းလုပ်ငန်းခွင်တွင် ဆောင်ရွက်လျက်ရှိပြီး အမြန်ပြီးစီးရေး မှာကြားသည်။"
        self.assertIsNone(
            parse_project_detail(
                _detail(title=title, primary=underway, date="Sep 15 2026"),
                "https://construction.gov.mm/new-detail/87a6be60-b0b7-11f1-8d3d-c595813e041f",
            )
        )

        tender_title = "မြို့ပြအိမ်ရာစီမံကိန်း အသစ်တည်ဆောက်ရန်"
        tender_body = "စီမံကိန်းအတွက် အိတ်ဖွင့်တင်ဒါခေါ်ယူထားပြီး လုပ်ငန်းရှင်များအား ဖိတ်ခေါ်သည်။"
        self.assertIsNone(
            parse_project_detail(
                _detail(title=tender_title, primary=tender_body),
                "https://construction.gov.mm/new-detail/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            )
        )

    def test_structural_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(ConstructionProjectPrecursorParseError, "news card structure"):
            parse_project_listing(b"<html><body><div>changed</div></body></html>")
        with self.assertRaisesRegex(ConstructionProjectPrecursorParseError, "detail structure"):
            parse_project_detail(b"<html><body>changed</body></html>", CYBER_URL)


if __name__ == "__main__":
    unittest.main()
