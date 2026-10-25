import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

from signalforge.s01_attachment import render_markdown
from signalforge.s01_daily_ledger import S01Ledger, article_identity, edition_identity
from signalforge.s01_daily_sender import deliver
from signalforge.s01_daily_handoff import stage
from signalforge.s01_daily_receipt import import_receipt
from signalforge.s01_daily_cleanup import cleanup


class MarkdownDeliveryTests(unittest.TestCase):
    def case(self, root, kind="markdown"):
        url = "https://myanmar.gov.mm/news/example?assetEntryId=123"
        entry = {"identity": article_identity(url), "url": url, "detail_sha": "a"*64}
        edition = edition_identity("2026-10-25", [(entry["identity"],entry["detail_sha"])])
        payload = root / ("news.md" if kind == "markdown" else "news.pdf")
        payload.write_text("# 正文\n中文新闻")
        data = {"date":"2026-10-25","edition_id":edition,"articles":[entry],
                kind:payload.name,kind+"_sha256":hashlib.sha256(payload.read_bytes()).hexdigest(),
                "digest":"中文 Digest","caption":"正文"}
        path = root/"manifest.json"
        path.write_text(json.dumps(data))
        transport = MagicMock()
        transport._credentials.return_value = ("test","chat")
        transport._send_text.side_effect = [101,103,104]
        transport._send_document.return_value = 102
        return path,payload,data,transport

    def test_markdown_receipts_import_cleanup_and_idempotency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path,payload,data,t=self.case(root)
            outbox=root/"outbox"
            staged=Path(stage(path,outbox)["directory"])
            result=deliver(root/"remote.sqlite",staged/"manifest.json",transport=t)
            self.assertEqual(result["receipts"],{"digest":101,"markdown":102})
            self.assertEqual(deliver(root/"remote.sqlite",staged/"manifest.json",transport=t)["status"],"SUCCESS")
            self.assertEqual(t._send_text.call_count,1)
            self.assertEqual(t._send_document.call_count,1)
            import_receipt(root/"mac.sqlite",staged/"manifest.json",Path(result["receipt_path"]))
            cleanup(outbox,data["edition_id"],ledger=root/"mac.sqlite")
            self.assertFalse(staged.exists())

    def test_missing_attachment_does_not_block_digest_and_notifies_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path,payload,data,t=self.case(root)
            payload.unlink()
            staged=Path(stage(path,root/"outbox")["directory"])
            result=deliver(root/"ledger",staged/"manifest.json",transport=t)
            self.assertEqual(result["status"],"PARTIAL")
            self.assertEqual(result["receipts"]["digest"],101)
            self.assertIn("校验",t._send_text.call_args_list[1].args[2])
            t._send_document.assert_not_called()
            deliver(root/"ledger",staged/"manifest.json",transport=t)
            self.assertEqual(t._send_text.call_count,2)

    def test_prior_unknown_attachment_does_not_block_new_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,payload,data,t=self.case(root)
            ledger=S01Ledger(root/"ledger")
            ledger.record_delivery(data["edition_id"],"markdown","UNKNOWN");ledger.close()
            result=deliver(root/"ledger",path,transport=t)
            self.assertEqual(result["receipts"]["digest"],101)
            self.assertEqual(result["status"],"PARTIAL")
            t._send_document.assert_not_called()

    def test_digest_failure_still_attempts_attachment_and_notifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,payload,data,t=self.case(root)
            t._send_text.side_effect=[RuntimeError("Telegram HTTP 400"),103]
            result=deliver(root/"ledger",path,transport=t)
            self.assertEqual(result["receipts"]["markdown"],102)
            self.assertIn("HTTP 400",result["failures"]["digest"])
            self.assertIn("HTTP 400",t._send_text.call_args_list[1].args[2])
            self.assertFalse(path.with_suffix(".receipt.json").exists())

    def test_attachment_timeout_retains_digest_and_never_resends_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,payload,data,t=self.case(root)
            t._send_document.side_effect=TimeoutError("timed out")
            self.assertEqual(deliver(root/"ledger",path,transport=t)["status"],"PARTIAL")
            self.assertEqual(deliver(root/"ledger",path,transport=t)["status"],"PARTIAL")
            self.assertEqual(t._send_document.call_count,1)
            self.assertEqual(t._send_text.call_count,2)
            self.assertTrue(payload.exists())

    def test_digest_only_sends_without_attachment_and_reuses_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,payload,data,t=self.case(root)
            payload.unlink()
            result=deliver(root/"ledger",path,transport=t,digest_only=True)
            self.assertEqual(result["receipts"],{"digest":101})
            self.assertEqual(result["status"],"DIGEST_ONLY")
            t._send_document.assert_not_called()
            self.assertEqual(t._send_text.call_count,1)
            self.assertFalse(path.with_suffix(".receipt.json").exists())

    def test_prepare_generates_markdown_without_pdf_font(self):
        from signalforge.s01_daily_prepare import prepare
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,payload,data,t=self.case(root)
            url=data["articles"][0]["url"]
            ai={"chinese_title":"新闻","chinese_summary":"全部中文正文","category":"政策",
                "importance":80,"rationale":"民生","evidence_limitations":"官方来源待核"}
            audit={"total_discovered":1,"included":1,"excluded":0,"unresolved":0,
                   "items":[{"url":url,"detail_sha256":"a"*64,"disposition":"INCLUDED","ai_review":ai}]}
            (root/"audit.json").write_text(json.dumps(audit))
            (root/"s01-news-coverage-audit.json").write_text(json.dumps({"candidate_urls":[url]}))
            result=prepare(root/"audit.json",root/"ledger",root/"out",day="2026-10-25",fontfile=root/"missingfont")
            manifest=json.loads(Path(result["manifest"]).read_text())
            self.assertNotIn("pdf",manifest)
            self.assertIn("全部中文正文",Path(manifest["markdown"]).read_text())

    def test_legacy_pdf_manifest_still_delivers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,payload,data,t=self.case(root,"pdf")
            self.assertEqual(deliver(root/"ledger",path,transport=t)["receipts"],{"digest":101,"pdf":102})

    def test_markdown_keeps_every_story_source_and_uncertainty(self):
        ai={"chinese_title":"政策","chinese_summary":"中文正文","category":"政策","importance":80,
            "rationale":"民生","evidence_limitations":"待核：低置信度"}
        report={"items":[{"disposition":"INCLUDED","ai_review":ai,"url":"https://myanmar.gov.mm/a"}],
                "pending_articles":[{"url":"https://myanmar.gov.mm/b","reason":"无法读取"}]}
        text=render_markdown(report,edition_date="2026-10-25")
        for word in ("中文正文","待核","https://myanmar.gov.mm/a","无法读取","https://myanmar.gov.mm/b"):
            self.assertIn(word,text)
