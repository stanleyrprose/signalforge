import html
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from signalforge import daily_cycle as cycle
from signalforge import s01_failure_notice as notice
from signalforge import s01_codex_review_runner as review

class QuotaNoticeTests(unittest.TestCase):
    def test_one_quota_notice_with_its_own_receipt_and_no_false_daily_success(self):
        with tempfile.TemporaryDirectory() as t:
            transport=MagicMock()
            transport._credentials.return_value=("secret","configured")
            transport._send_text.return_value=901
            first=notice.send("2026-10-25",152,202,root=Path(t),transport=transport)
            second=notice.send("2026-10-25",152,202,root=Path(t),transport=transport)
            self.assertEqual(first["message_id"],901)
            self.assertEqual(second["status"],"ALREADY_SENT")
            self.assertIn("PDF 和 Digest 尚未投递",transport._send_text.call_args.args[2])
            transport._send_text.assert_called_once()

    def test_unknown_quota_notice_is_not_repeated(self):
        with tempfile.TemporaryDirectory() as t:
            transport=MagicMock()
            transport._credentials.return_value=("secret","configured")
            transport._send_text.side_effect=TimeoutError()
            with self.assertRaises(TimeoutError):notice.send("2026-10-25",1,2,root=Path(t),transport=transport)
            with self.assertRaisesRegex(RuntimeError,"unresolved"):notice.send("2026-10-25",1,2,root=Path(t),transport=transport)
            transport._send_text.assert_called_once()

    def test_usage_limit_is_not_retried_three_times(self):
        with tempfile.TemporaryDirectory() as t:
            conn=MagicMock();conn.__enter__.return_value=conn
            conn.execute.return_value.fetchall.return_value=[("https://myanmar.gov.mm/news/example","title","body","a"*64)]
            with patch.object(review,"connect",return_value=conn),patch.object(
                review.subprocess,"run",return_value=subprocess.CompletedProcess(["codex"],1,stderr="ERROR: You've hit your usage limit.")) as model:
                with self.assertRaises(review.AIUsageLimitError) as caught:
                    review.run(Path(t)/"db",Path(t))
                self.assertEqual(caught.exception.total,1)
                model.assert_called_once()

    def test_daily_quota_failure_notifies_bangkok_and_reuses_acquisition(self):
        from signalforge import s01_daily_runner as daily
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);folder=root/"evidence/2026-10-25";folder.mkdir(parents=True)
            (folder/"s01-news-review.sqlite").write_bytes(b"mock source snapshot")
            with patch.object(daily,"acquire_paginated_news_review",return_value={"pagination_incomplete":False,"unique_candidates":202}) as acquire, patch.object(
                daily,"acquire_news_details",return_value={}), patch.object(
                daily,"review",side_effect=review.AIUsageLimitError(152,202)), patch(
                "signalforge.s01_failure_notice.notify_from_mac",return_value={"status":"SUCCESS","message_id":901}) as notify:
                for _ in range(2):
                    with self.assertRaises(review.AIUsageLimitError):daily.run(root,day="2026-10-25")
                acquire.assert_called_once()
                self.assertEqual(notify.call_count,2)  # remote durable receipt performs dedup
                notify.assert_called_with("2026-10-25",152,202)
            self.assertTrue((folder/"s01-news-review.sqlite").exists())
            self.assertTrue((folder/"failure-notice.json").exists())

class ReportTests(unittest.TestCase):
    def test_source_failure_text_is_escaped_and_utf16_bounded(self):
        raw="S20 <urlopen error timed out> & other\n"+("😀"*5000)
        parts=cycle._report_parts(raw)
        self.assertEqual(html.unescape("".join(parts)),raw)
        self.assertTrue(all(len(x.encode("utf-16-le"))//2<=3800 for x in parts))
        self.assertNotIn("<urlopen","".join(parts))

    def test_report_parts_reuse_success_receipts_after_known_rejection(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"report.json"
            with patch.object(cycle,"_send_message",side_effect=["100",RuntimeError("telegram HTTP 400")]):
                with self.assertRaises(RuntimeError):
                    cycle._send_report(path,"2026-10-25","a"*5000,"secret","configured")
            with patch.object(cycle,"_send_message",return_value="101") as send:
                result=cycle._send_report(path,"2026-10-25","a"*5000,"secret","configured")
            self.assertEqual(result["message_ids"],["100","101"])
            send.assert_called_once()
