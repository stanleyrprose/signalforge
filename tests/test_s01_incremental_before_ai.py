"""Regression cases for pre-AI filtering after confirmed content cleanup."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from signalforge.db import connect, migrate
from signalforge import s01_codex_review_runner as runner
from signalforge.s01_daily_ledger import S01Ledger, content_fingerprint
from signalforge.s01_daily_prepare import prepare
from signalforge.s01_news_review import acquire_news_review


OLD = "https://myanmar.gov.mm/en/news-media/news/latest-news/-/asset_publisher/idasset354/content/old?assetEntryId=12345"
NEW = "https://myanmar.gov.mm/en/news-media/news/latest-news/-/asset_publisher/idasset354/content/new?assetEntryId=67890"
BODY = "official policy with amount 100 " * 8


class IncrementalBeforeAITests(unittest.TestCase):
    def setup_case(self, root, *, changed=False, new=False, confirmed=True):
        db, ledger_path = root / "review.sqlite", root / "ledger.sqlite"
        migrate(db)
        links = f'<a href="{OLD}">Official policy announcement old</a>'
        if new:
            links += f'<a href="{NEW}">Official policy announcement new</a>'
        acquire_news_review(db, root, payload=links.encode())
        with connect(db) as conn, conn:
            conn.execute("""CREATE TABLE s01_news_detail_review
                (url TEXT PRIMARY KEY,detail_sha256 TEXT NOT NULL,detail_evidence_path TEXT NOT NULL,
                 body_text TEXT NOT NULL,body_chars INTEGER NOT NULL,review_status TEXT NOT NULL,
                 acquired_at TEXT NOT NULL)""")
            urls = [r[0] for r in conn.execute("SELECT url FROM s01_news_review ORDER BY url")]
            for url in urls:
                body = BODY.replace("100", "101") if changed and "assetEntryId=12345" in url else BODY
                conn.execute("INSERT INTO s01_news_detail_review VALUES (?,?,?,?,?,?,?)",
                             (url, "b" * 64, "source.html", body, len(body),
                              "DETAIL_EXTRACTED_UNCORROBORATED", "now"))
        old_url = next(url for url in urls if "assetEntryId=12345" in url)
        ledger = S01Ledger(ledger_path)
        identity = ledger.upsert_article(old_url, "a" * 64,
                                        review={"content_sha256": content_fingerprint(BODY)})
        if confirmed:
            ledger.record_delivery("prior", "markdown", "SUCCESS", 11)
            ledger.record_delivery("prior", "digest", "SUCCESS", 12)
            ledger.mark_delivered([(identity, "a" * 64)], "prior")
            ledger.purge_delivered_review_content("prior")
        ledger.close()
        (root / "s01-news-coverage-audit.json").write_text(json.dumps({"candidate_urls": urls}))
        return db, ledger_path

    def model(self, calls):
        def invoke(args, *, stdin, **kwargs):
            payload = json.loads(stdin.read().decode().split("\n\n")[-1])
            calls.append(payload)
            result = {"items": [{
                "item_id": item["item_id"], "chinese_title": "政策消息",
                "chinese_summary": "官方政策消息，金额等数据以原文为准。",
                "importance": 70, "category": "政策", "rationale": "公共政策",
                "evidence_limitations": "官方单一来源"
            } for item in payload]}
            Path(args[args.index("-o") + 1]).write_text(json.dumps(result))
            return SimpleNamespace(returncode=0, stderr="")
        return invoke

    def test_cleaned_old_content_never_calls_ai_and_prepares_no_new(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            db, ledger = self.setup_case(root)
            with patch.object(runner.subprocess, "run") as call:
                report = runner.run(db, root, cache_ledger=ledger)
            call.assert_not_called()
            self.assertEqual((report["included"], report["already_delivered"], report["unresolved"]),
                             (0, 1, 0))
            audit = json.loads((root / "coverage-audit.json").read_text())
            self.assertEqual(audit["items"][0]["disposition"], "ALREADY_DELIVERED")
            self.assertIsNone(audit["items"][0]["ai_review"])
            result = prepare(root / "coverage-audit.json", ledger, root / "outbox",
                             day="2026-10-27", fontfile=root / "unused")
            self.assertEqual(result["status"], "NO_NEW_ARTICLES")
            self.assertFalse((root / "outbox").exists())

    def test_mixed_batch_only_translates_new_and_resume_reuses_validated_batch(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            db, ledger = self.setup_case(root, new=True)
            calls = []
            with patch.object(runner.subprocess, "run", side_effect=self.model(calls)):
                report = runner.run(db, root, batch_size=4, cache_ledger=ledger)
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(calls[0]), 1)
            self.assertIn("assetEntryId=67890", calls[0][0]["url"])
            self.assertEqual((report["included"], report["already_delivered"]), (1, 1))
            with patch.object(runner.subprocess, "run") as call:
                runner.run(db, root, batch_size=4, cache_ledger=ledger)
            call.assert_not_called()
            prepared = prepare(root / "coverage-audit.json", ledger, root / "outbox",
                               day="2026-10-27", fontfile=root / "unused")
            manifest = json.loads(Path(prepared["manifest"]).read_text())
            self.assertEqual(len(manifest["articles"]), 1)
            self.assertEqual(manifest["pending_articles"], [])
            self.assertEqual(manifest["incomplete_count"], 0)

    def test_real_body_change_or_unconfirmed_delivery_still_requires_ai(self):
        for options in ({"changed": True}, {"confirmed": False}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as t:
                root = Path(t)
                db, ledger = self.setup_case(root, **options)
                calls = []
                with patch.object(runner.subprocess, "run", side_effect=self.model(calls)):
                    report = runner.run(db, root, cache_ledger=ledger)
                self.assertEqual(len(calls[0]), 1)
                self.assertEqual((report["included"], report["already_delivered"]), (1, 0))

    def test_daily_runner_completes_all_old_without_ai_or_transfer(self):
        import hashlib
        from signalforge.s01_daily_runner import run as daily_run
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            db, ledger = self.setup_case(root)
            evidence = root / "evidence" / "2026-10-27"
            evidence.mkdir(parents=True)
            db.rename(evidence / "s01-news-review.sqlite")
            ledger.rename(root / "s01-delivery.sqlite")
            (root / "s01-news-coverage-audit.json").rename(evidence / "s01-news-coverage-audit.json")
            (evidence / "acquisition-checkpoint.json").write_text(json.dumps({
                "date": "2026-10-27", "pagination": {"unique_candidates": 1},
                "db_sha256": hashlib.sha256((evidence / "s01-news-review.sqlite").read_bytes()).hexdigest()
            }))
            with patch.object(runner.subprocess, "run") as model, patch(
                    "signalforge.s01_daily_runner.transfer") as send:
                result = daily_run(root, day="2026-10-27", publish=True)
            self.assertEqual(result["status"], "NO_NEW_ARTICLES")
            model.assert_not_called()
            send.assert_not_called()

    def test_forged_skip_is_rejected_by_preparer(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            db, ledger = self.setup_case(root, new=True)
            calls = []
            with patch.object(runner.subprocess, "run", side_effect=self.model(calls)):
                runner.run(db, root, cache_ledger=ledger)
            audit_path = root / "coverage-audit.json"
            audit = json.loads(audit_path.read_text())
            for item in audit["items"]:
                item["disposition"] = "ALREADY_DELIVERED"
                item["ai_review"] = None
            audit.update(included=0, already_delivered=2)
            audit_path.write_text(json.dumps(audit))
            with self.assertRaisesRegex(ValueError, "receipt-confirmed"):
                prepare(audit_path, ledger, root / "outbox",
                        day="2026-10-27", fontfile=root / "unused")
