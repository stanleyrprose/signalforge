import unittest
from signalforge.s01_daily_pdf import render_digest


class DigestReadabilityTests(unittest.TestCase):
    def test_digest_has_facts_reason_and_pdf_reference_within_telegram_limit(self):
        items = [{"disposition": "INCLUDED", "ai_review": {
            "importance": 90, "chinese_title": "标题"*100, "category": "政治与政策",
            "chinese_summary": "据官方报道，实施新政策。" * 100,
            "rationale": "涉及公共服务与民生。" * 100}} for _ in range(15)]
        result = render_digest({"items": items, "unresolved": 0}, edition_date="2026-10-25")
        self.assertIn("据官方报道", result)
        self.assertIn("关注：", result)
        self.assertIn("随附PDF第10条", result)
        self.assertNotIn("随附PDF第11条", result)
        self.assertLessEqual(len(result.encode("utf-16-le"))//2, 4096)
