"""Bounded idempotent Bangkok Chinese-news Digest plus PDF delivery tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import json
import hashlib
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
SPEC=importlib.util.spec_from_file_location("daily_digest_sender",ROOT/"tools/send_newspaper_daily_digest_tg.py")
assert SPEC and SPEC.loader
mod=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class DigestDeliveryTests(unittest.TestCase):
    def fixture(self,folder:Path):
        pdf=folder/"Chinese_News_Review.pdf"
        pdf.write_bytes(b"%PDF-1.7\nFAKE")
        item={"publication_id":"N001","title":"Myanmar news"}
        data={
            "schema_version":"newspaper-digest-v1",
            "paper":"mal","date":"2026-10-16",
            "source_pdf_sha256":"a"*64,
            "edition_pdf_basename":pdf.name,
            "edition_pdf_sha256":hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "paper_label":"缅甸之光",
            "selected_count":1,"edition_news_count":115,"selected":[item],
            "messages":["重要政策更新\n↳ N001｜原报第1页"],
        }
        digest=folder/"digest.json"
        digest.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        return digest,pdf

    def test_digest_first_then_full_pdf_exactly_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bundle,pdf=self.fixture(root)
            with patch.object(mod,"_credentials",return_value=("fake","allowed-chat")),\
                 patch.object(mod,"_send_text",return_value=710) as text_send,\
                 patch.object(mod,"_send_document",return_value=711) as pdf_send:
                a=mod.send_issue(bundle,pdf,receipts=root/"receipts")
                b=mod.send_issue(bundle,pdf,receipts=root/"receipts")
                self.assertEqual(text_send.call_count,1)
                self.assertEqual(pdf_send.call_count,1)
                self.assertEqual(a["digest_ids"],[710])
                self.assertEqual(b["pdf_message_id"],711)

    def test_r06_preview_sends_digest_but_not_duplicate_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bundle,pdf=self.fixture(root)
            with patch.object(mod,"_credentials",return_value=("fake","allowed-chat")),\
                 patch.object(mod,"_send_text",return_value=712) as text_send,\
                 patch.object(mod,"_send_document") as pdf_send:
                out=mod.send_issue(bundle,pdf,receipts=root/"receipts",
                                   digest_only=True,preview=True)
                self.assertEqual(out["digest_ids"],[712])
                self.assertIsNone(out["pdf_message_id"])
                self.assertIn("人工验收",text_send.call_args.args[2])
                pdf_send.assert_not_called()

    def test_v2_ai_manifest_must_cover_every_article_and_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bundle,pdf=self.fixture(root)
            data=json.loads(bundle.read_text())
            data.update({
                "schema_version":"newspaper-digest-v2",
                "selection_method":"AI_SEMANTIC_WITH_RULES",
                "ai_assessed_count":115,
                "novelty_baseline":"NO_HISTORY",
                "ai_input_fingerprint":"b"*64,
            })
            data["selected"][0].update({
                "novelty_status":"UNKNOWN",
                "why_it_matters":"该事件对公众政策落实与经济环境存在影响。"
            })
            mod.validate_bundle(data,pdf)
            data["ai_assessed_count"]=114
            with self.assertRaisesRegex(ValueError,"Incomplete AI"):
                mod.validate_bundle(data,pdf)
            data["ai_assessed_count"]=115
            data["selected"][0]["novelty_status"]="NEW_DEVELOPMENT"
            with self.assertRaisesRegex(ValueError,"without history"):
                mod.validate_bundle(data,pdf)
            data["selected"][0]["novelty_status"]="UNKNOWN"
            data["selection_method"]="RULES_V1_EXPLICIT"
            with self.assertRaisesRegex(ValueError,"AI assessment"):
                mod.validate_bundle(data,pdf)

    def test_v2_human_review_keeps_v1_receipt_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bundle,pdf=self.fixture(root)
            existing=mod._receipt_file(root/"receipts",{
                "paper":"mal","date":"2026-10-16","schema_version":"newspaper-digest-v1",
            })
            existing.parent.mkdir(parents=True)
            existing.write_text('{"delivery":"existing-v1"}',encoding="utf-8")
            preview=mod._receipt_file(root/"receipts",{
                "paper":"mal","date":"2026-10-16","schema_version":"newspaper-digest-v2",
            },preview=True)
            self.assertNotEqual(existing,preview)
            self.assertIn("human-review",str(preview))
            self.assertEqual(json.loads(existing.read_text())["delivery"],"existing-v1")

    def test_v2_point_one_preview_receipt_is_revision_scoped(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bundle,pdf=self.fixture(root)
            data=json.loads(bundle.read_text())
            data.update({
                "schema_version":"newspaper-digest-v2",
                "selection_method":"AI_SEMANTIC_WITH_RULES",
                "ai_assessed_count":115,
                "novelty_baseline":"NO_HISTORY",
                "ai_input_fingerprint":"b"*64,
                "editorial_policy_version":"digest-editorial-v2.1",
            })
            data["selected"][0].update({
                "novelty_status":"UNKNOWN",
                "why_it_matters":"该事项涉及政策与经济环境，值得继续观察。",
            })
            bundle.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
            old=mod._receipt_file(root/"receipts",data,preview=True)
            new=mod._receipt_file(root/"receipts",data,preview=True,review_tag="v2-1")
            self.assertNotEqual(old,new)
            with patch.object(mod,"_credentials",return_value=("fake","allowed-chat")), \
                 patch.object(mod,"_send_text",return_value=718) as msg, \
                 patch.object(mod,"_send_document") as document:
                first=mod.send_issue(bundle,pdf,receipts=root/"receipts",
                                      preview=True,digest_only=True,review_tag="v2-1")
                second=mod.send_issue(bundle,pdf,receipts=root/"receipts",
                                      preview=True,digest_only=True,review_tag="v2-1")
                self.assertEqual(msg.call_count,1)
                document.assert_not_called()
                self.assertEqual(first["digest_ids"],[718])
                self.assertEqual(second["digest_ids"],[718])
            self.assertFalse(old.exists())
            self.assertTrue(new.exists())
            with self.assertRaisesRegex(ValueError,"Review tag"):
                mod._receipt_file(root/"receipts",data,preview=True,review_tag="../old")
            with self.assertRaisesRegex(ValueError,"requires preview"):
                mod._receipt_file(root/"receipts",data,preview=False,review_tag="v2-1")

    def test_pdf_sha_change_fails_before_sending(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bundle,pdf=self.fixture(root)
            pdf.write_bytes(b"%PDF-1.7\nREPLACEMENT")
            with self.assertRaisesRegex(ValueError,"modified"):
                mod.validate_bundle(json.loads(bundle.read_text()),pdf)

    def test_duplicate_or_inconsistent_selected_count_is_invalid(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bundle,pdf=self.fixture(root)
            data=json.loads(bundle.read_text())
            data["selected_count"]=2
            with self.assertRaisesRegex(ValueError,"count mismatch"):
                mod.validate_bundle(data,pdf)


if __name__=="__main__":
    unittest.main()
