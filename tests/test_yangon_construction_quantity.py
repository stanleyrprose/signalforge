import unittest

from signalforge.yangon_construction import _explicit_work_count


class YangonConstructionQuantityTests(unittest.TestCase):
    def test_explicit_work_count(self):
        self.assertEqual(_explicit_work_count("တည်ဆောက်ရေး လုပ်ငန်း (၇) ခု"), "7 လုပ်ငန်း")

    def test_no_inference_from_reference(self):
        self.assertIsNone(_explicit_work_count("Tender 7/2026 road construction"))

    def test_no_deadline_from_unrelated_dates(self):
        from signalforge.yangon_construction import _deadline
        self.assertIsNone(_deadline("လုပ်ငန်းစတင်ရက် ၁၂.၁၀.၂၀၂၆ ပြီးစီးရက် ၂၂.၁၂.၂၀၂၆"))

    def test_explicit_submission_window_uses_last_date(self):
        from signalforge.yangon_construction import _deadline
        self.assertEqual(
            _deadline("တင်ဒါလျှောက်လွှာတင်သွင်းရမည့် ရက် (၁၅.၆.၂၀၂၆) မှ (၂၄.၆.၂၀၂၆) အထိ"),
            "2026-06-24",
        )

    def test_no_inference_from_dates(self):
        self.assertIsNone(_explicit_work_count("တင်ဒါပိတ်မည့်နေ့ 12.10.2026"))


if __name__ == "__main__":
    unittest.main()
