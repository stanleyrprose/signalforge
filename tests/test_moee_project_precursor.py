from __future__ import annotations

import unittest

from signalforge.moee_project_precursor import (
    MoeeProjectPrecursorParseError,
    parse_project_detail,
    parse_project_listing,
)

LIST_URL = "https://moep.gov.mm/mm/ignite/page/12"
PINPET_ID = "7133"
PINPET_URL = f"https://moep.gov.mm/mm/ignite/contentView/{PINPET_ID}"


def _news_card(*, content_id: str, title: str, date: str) -> str:
    return f"""
    <div class="content-data-list mid-padding mid-side-padding small-margin clearfix">
      <div class="row">
        <div class="col-md-8">
          <strong class="text-primary">{title}</strong>
          <div class="summary-text">summary</div>
          <a href="ignite/contentView/{content_id}">Read More...</a>
        </div>
      </div>
      <div class="text-right small-height">
        <i class="fa fa-calendar-o text-warning"></i> : {date}
      </div>
    </div>
    """


def _listing(*cards: str, sidebar: str = "") -> bytes:
    return f"""
    <html><body>
      <div class="col-md-7">
        <h3 class="text-info">နောက်ဆုံးရသတင်း</h3>
        {''.join(cards)}
      </div>
      <div class="col-md-3 sidebar-right">
        <div class="tender">
          <h4 class="tender-title">နောက်ဆုံးရ တင်ဒါသတင်းများ</h4>
          {sidebar}
        </div>
      </div>
    </body></html>
    """.encode()


def _detail(*, content_id: str, title: str, paragraphs: list[str], date: str = "30-Aug-2026") -> bytes:
    body = "".join(f'<p style="text-align: justify;">{value}</p>' for value in paragraphs)
    return f"""
    <html lang="my"><head>
      <meta property="og:url" content="ignite/contentView/{content_id}" />
      <meta property="og:type" content="website" />
      <meta property="og:title" content="{title}" />
    </head><body>
      <div class="photo-grid">images</div>
      <div class="mid-margin">
        <p></p>
        <p style="text-align: center;">နေပြည်တော်</p>
        {body}
      </div>
      <div class="text-right small-height">
        Post under by : ဝန်ကြီးရုံး<br/>
        <i class="fa fa-calendar-o text-danger"></i> <i>{date}</i>
      </div>
      <div class="mid-margin"><div class="fb-share-button">share</div></div>
      <div class="col-md-3 sidebar-right">
        <div class="tender">
          <a href="ignite/contentView/7157">အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း</a>
        </div>
      </div>
    </body></html>
    """.encode()


class MoeeProjectPrecursorParserTests(unittest.TestCase):
    def test_listing_captures_main_news_cards_and_ignores_sidebar_tenders(self) -> None:
        sidebar = '<a href="ignite/contentView/7157">Tender</a><span>11-Sep-2026</span>'
        html = _listing(
            _news_card(
                content_id="7184",
                title="Electricity enforcement news",
                date="23-Sep-2026",
            ),
            _news_card(
                content_id="7171",
                title="Minister inspects main substations",
                date="16-Sep-2026",
            ),
            sidebar=sidebar,
        )
        entries = parse_project_listing(html)
        self.assertEqual(
            [entry.url for entry in entries],
            [
                "https://moep.gov.mm/mm/ignite/contentView/7184",
                "https://moep.gov.mm/mm/ignite/contentView/7171",
            ],
        )
        self.assertEqual(entries[0].lastmod, "2026-09-23T00:00:00+06:30")

    def test_listing_does_not_require_project_keywords_in_title(self) -> None:
        html = _listing(
            _news_card(
                content_id=PINPET_ID,
                title="ဒုတိယဝန်ကြီး လျှပ်စစ်နှင့်စွမ်းအင်ဆိုင်ရာလုပ်ငန်းများ ကြည့်ရှုစစ်ဆေး",
                date="30-Aug-2026",
            )
        )
        self.assertEqual(len(parse_project_listing(html)), 1)

    def test_detail_extracts_pinpet_future_plant_but_rejects_underway_switchbay_in_same_paragraph(self) -> None:
        title = "ဒုတိယဝန်ကြီး လျှပ်စစ်နှင့်စွမ်းအင်ဆိုင်ရာလုပ်ငန်းများ ကြည့်ရှုစစ်ဆေး"
        mixed = (
            "တောင်ကြီးမြို့ ၆၆/၁၁ ကေဗွီ ဓာတ်အားခွဲရုံ၊ "
            "ဟိုပုန်းမြို့ ၆၆/၃၃ ကေဗွီ ဓာတ်အားခွဲရုံ၊ "
            "ပင်းပက် သံမဏိစက်ရုံအတွင်း တည်ဆောက်မည့် "
            "ကျောက်မီးသွေးသုံးရေနွေးငွေ့ဓာတ်အားပေးစက်ရုံ အခြေအနေနှင့်"
            "တောင်ကြီးပင်မဓာတ်အားခွဲရုံအတွင်း တိုးချဲ့တည်ဆောက်လျှက်ရှိသည့် "
            "၂၃၀/၁၃၂ ကေဗွီ၊ ၁၅၀ အမ်ဗွီအေ Switchbay တည်ဆောက်နေမှုအခြေအနေများအား ကြည့်ရှုစစ်ဆေးခဲ့သည်။"
        )
        results = parse_project_detail(
            _detail(
                content_id=PINPET_ID,
                title=title,
                paragraphs=[
                    "တီကျစ် ကျောက်မီးသွေးသုံး ဓာတ်အားပေးစက်ရုံ လည်ပတ်နေမှုအား ကြည့်ရှုစစ်ဆေးခဲ့သည်။",
                    mixed,
                    "၂၀၃၀ ပြည့်နှစ်တွင် တစ်နိုင်ငံလုံးမီးလင်းရေးအတွက် ကြိုတင်ပြင်ဆင်ဆောင်ရွက်ရန် မှာကြားခဲ့သည်။",
                ],
            ),
            PINPET_URL,
        )
        self.assertEqual(len(results), 1)
        item = results[0]
        self.assertIn("ပင်းပက်", item.project_name)
        self.assertIn("တည်ဆောက်မည့်", item.project_name)
        self.assertIn("ဓာတ်အားပေးစက်ရုံ", item.project_name)
        self.assertNotIn("Switchbay", item.project_name)
        self.assertEqual(item.publication_date, "2026-08-30")
        self.assertEqual(item.precursor_stage_hint, "PROJECT_ANNOUNCEMENT")
        self.assertEqual(item.relevance_categories, ("ENERGY",))
        self.assertTrue(item.canonical_key.startswith("moee-project:7133:"))

    def test_detail_can_emit_two_independent_future_energy_projects(self) -> None:
        results = parse_project_detail(
            _detail(
                content_id="7200",
                title="Planned electricity works",
                paragraphs=[
                    "New 230kV substation will be constructed in Area A.",
                    "A new transmission line will be built in Area B.",
                ],
                date="27-Sep-2026",
            ),
            "https://moep.gov.mm/mm/ignite/contentView/7200",
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(len({item.canonical_key for item in results}), 2)

    def test_detail_stage_hints_cover_finance_and_planning(self) -> None:
        results = parse_project_detail(
            _detail(
                content_id="7201",
                title="Power development update",
                paragraphs=[
                    "Loan approved for a new power plant to be constructed in Region A.",
                    "Detailed design for a new substation will be prepared in Region B.",
                ],
                date="27-Sep-2026",
            ),
            "https://moep.gov.mm/mm/ignite/contentView/7201",
        )
        self.assertEqual([item.precursor_stage_hint for item in results], ["BUDGET_FINANCE", "PLANNING_DESIGN"])

    def test_detail_accepts_valid_page_date_without_post_under_by(self) -> None:
        html = _detail(
            content_id="7206",
            title="Electricity enforcement news",
            paragraphs=["No project candidate is present."],
            date="23-Sep-2026",
        ).decode()
        html = html.replace("Post under by : ဝန်ကြီးရုံး<br/>", "")
        results = parse_project_detail(
            html.encode(),
            "https://moep.gov.mm/mm/ignite/contentView/7206",
        )
        self.assertEqual(results, [])

    def test_detail_rejects_operating_underway_completed_and_open_tender_assets(self) -> None:
        results = parse_project_detail(
            _detail(
                content_id="7202",
                title="Electricity works inspection",
                paragraphs=[
                    "The power plant is operating normally.",
                    "A 230kV substation construction is underway.",
                    "A transmission line project has been completed.",
                    "Open tender for a new substation will be constructed next year.",
                ],
                date="27-Sep-2026",
            ),
            "https://moep.gov.mm/mm/ignite/contentView/7202",
        )
        self.assertEqual(results, [])

    def test_generic_system_notice_and_hiring_do_not_become_precursors(self) -> None:
        for content_id, title, paragraph in (
            ("7203", "System Breakdown notice", "The grid is being stabilized and customers are informed."),
            ("7204", "Junior engineer recruitment", "Applications are invited for electrical engineering positions."),
        ):
            self.assertEqual(
                parse_project_detail(
                    _detail(
                        content_id=content_id,
                        title=title,
                        paragraphs=[paragraph],
                        date="27-Sep-2026",
                    ),
                    f"https://moep.gov.mm/mm/ignite/contentView/{content_id}",
                ),
                [],
            )

    def test_candidate_hash_is_stable_for_same_project_clause(self) -> None:
        html = _detail(
            content_id="7205",
            title="Future power work",
            paragraphs=["New 230kV substation will be constructed in Area A."],
            date="27-Sep-2026",
        )
        first = parse_project_detail(html, "https://moep.gov.mm/mm/ignite/contentView/7205")
        second = parse_project_detail(html, "https://moep.gov.mm/mm/ignite/contentView/7205")
        self.assertEqual(first[0].canonical_key, second[0].canonical_key)

    def test_structural_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(MoeeProjectPrecursorParseError, "latest-news card structure"):
            parse_project_listing(b"<html><body><div>changed</div></body></html>")
        with self.assertRaisesRegex(MoeeProjectPrecursorParseError, "detail structure"):
            parse_project_detail(
                b'<html><head><meta property="og:title" content="x"></head><body>changed</body></html>',
                PINPET_URL,
            )


if __name__ == "__main__":
    unittest.main()
