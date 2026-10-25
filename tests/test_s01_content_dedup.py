import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode
from signalforge.s01_daily_ledger import S01Ledger, article_identity, content_fingerprint, edition_identity
from signalforge.s01_daily_sender import deliver
from signalforge.s01_daily_prepare import prepare


URL = "https://myanmar.gov.mm/news/example?assetEntryId=12345"


class ContentDedupTests(unittest.TestCase):
    def seed(self, path):
        ledger = S01Ledger(path)
        fingerprint = content_fingerprint("same article body")
        ident = ledger.upsert_article(URL, "a"*64, review={"content_sha256": fingerprint})
        ledger.record_delivery("old", "pdf", "SUCCESS", 11)
        ledger.record_delivery("old", "digest", "SUCCESS", 12)
        ledger.mark_delivered([(ident, "a"*64)], "old")
        ledger.close()
        return ident, fingerprint

    def test_nested_asset_id_is_stable_across_redirect_pagination(self):
        identities = []
        for page in (1, 9):
            nested = "https://myanmar.gov.mm/news?" + urlencode({"cur":page,"_portal_assetEntryId":"12345"})
            url = "https://myanmar.gov.mm/news/example?" + urlencode({"_portal_redirect":nested})
            identities.append(article_identity(url))
        self.assertEqual(identities, ["s01:asset:12345"]*2)
        self.assertEqual(content_fingerprint("same\n article  body"), content_fingerprint("same article body"))

    def test_changed_html_without_changed_body_never_prepares_pdf(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _ident, fingerprint = self.seed(root/"ledger.sqlite")
            audit = {"included":1,"unresolved":0,"excluded":0,"total_discovered":1,
                     "items":[{"url":URL,"detail_sha256":"b"*64,"content_sha256":fingerprint,
                               "disposition":"INCLUDED","ai_review":{"chinese_title":"政策新闻"}}]}
            (root/"audit.json").write_text(json.dumps(audit))
            (root/"s01-news-coverage-audit.json").write_text(json.dumps({"candidate_urls":[URL]}))
            with patch("signalforge.s01_daily_prepare.render_pdf") as render:
                result = prepare(root/"audit.json", root/"ledger.sqlite", root/"outbox",
                                 day="2026-10-25", fontfile=root/"font")
            self.assertEqual(result["status"], "NO_NEW_ARTICLES")
            render.assert_not_called()

    def test_bangkok_blocks_same_content_before_any_telegram_or_article_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            ident, fingerprint = self.seed(root/"ledger.sqlite")
            pdf = root/"edition.pdf"
            pdf.write_bytes(b"%PDF-test")
            article = {"identity":ident,"url":URL,"detail_sha":"b"*64,"content_sha256":fingerprint}
            manifest = {"date":"2026-10-25","edition_id":edition_identity("2026-10-25",[(ident,"b"*64)]),
                        "articles":[article],"pdf":pdf.name,"pdf_sha256":hashlib.sha256(pdf.read_bytes()).hexdigest(),
                        "digest":"政策新闻","caption":"新闻"}
            path = root/"manifest.json"
            path.write_text(json.dumps(manifest))
            transport = MagicMock()
            with self.assertRaisesRegex(ValueError, "already delivered article content"):
                deliver(root/"ledger.sqlite", path, transport=transport)
            transport._credentials.assert_not_called()
            ledger = S01Ledger(root/"ledger.sqlite")
            self.assertEqual(ledger.db.execute("SELECT detail_sha FROM articles WHERE identity=?",(ident,)).fetchone()[0],"a"*64)
            ledger.close()

    def test_receipt_confirmed_unchanged_translation_reuses_ai_without_provider_call(self):
        from signalforge import s01_codex_review_runner as runner
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _ident, fingerprint = self.seed(root/"ledger.sqlite")
            ai = {"source_url":URL,"importance":70,"chinese_title":"政策新闻",
                  "chinese_summary":"据官方报道，发布了公共服务政策。",
                  "category":"政策","rationale":"涉及公共服务。","evidence_limitations":"官方单一来源。"}
            ledger = S01Ledger(root/"ledger.sqlite")
            ledger.upsert_article(URL,"a"*64,review={"content_sha256":fingerprint,"ai_review":ai})
            ledger.close()
            conn = MagicMock()
            conn.__enter__.return_value = conn
            conn.execute.return_value.fetchall.return_value = [(URL,"Policy","same article body","b"*64)]
            report = {"total_discovered":1,"included":1,"excluded":0,"unresolved":0,"digest_publish_gate":"PASS"}
            with patch.object(runner,"connect",return_value=conn), \
                 patch.object(runner,"reconcile_ai_digest",return_value=report), \
                 patch.object(runner,"render_chinese_digest",return_value="审核"), \
                 patch.object(runner.subprocess,"run") as invoke:
                result = runner.run(root/"review.sqlite",root/"working",cache_ledger=root/"ledger.sqlite")
            self.assertEqual(result["included"],1)
            invoke.assert_not_called()

    def test_unconfirmed_new_revision_is_not_treated_as_delivered_content(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            ident, _old = self.seed(root/"ledger.sqlite")
            ledger = S01Ledger(root/"ledger.sqlite")
            new = content_fingerprint("changed article body")
            ledger.upsert_article(URL, "b"*64, review={"content_sha256":new})
            self.assertNotIn(new, ledger.delivered_versions()[ident]["content"])
            ledger.close()
