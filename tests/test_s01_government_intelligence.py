import json
import tempfile
import unittest
from pathlib import Path

from signalforge.db import connect, migrate
from signalforge.s01_government_intelligence import refresh_s01_government_intelligence


class GovernmentIntelligenceTests(unittest.TestCase):
    def test_review_only_separate_from_tender(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'registry').mkdir()
            records = {
                'a' * 64: {'review_status': 'HUMAN_APPROVED_SOURCE_IMAGE', 'formal_procurement_tender': True,
                           'issuer': 'MCDC', 'title': 'Fuel tender', 'scope_summary': 'Fuel'},
                'b' * 64: {'review_status': 'HUMAN_APPROVED_SOURCE_IMAGE', 'formal_procurement_tender': False,
                           'issuer': 'MCDC', 'title': 'Convention Centre lease', 'scope_summary': 'Venue rental'},
            }
            (root / 'registry' / 'S01-Reviewed-Issuer-Images-v1.json').write_text(
                json.dumps({'schema_version': 1, 'records': records}))
            database = root / 'test.db'
            migrate(database)
            for _ in range(2):
                result = refresh_s01_government_intelligence(database, root=root)
                self.assertEqual(result['candidates'], 1)
                self.assertEqual(result['telegram_sent'], 0)
            with connect(database) as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM government_intelligence_items').fetchone()[0], 1)
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM canonical_items').fetchone()[0], 0)
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0], 0)

    def test_preview_is_evidence_linked_and_not_falsely_translated(self):
        from signalforge.s01_government_intelligence import intelligence_review_preview
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'registry').mkdir()
            (root / 'registry' / 'S01-Reviewed-Issuer-Images-v1.json').write_text(json.dumps({
                'schema_version': 1, 'records': {
                    'b' * 64: {'review_status': 'HUMAN_APPROVED_SOURCE_IMAGE',
                               'formal_procurement_tender': False, 'issuer': 'MCDC',
                               'title': 'Convention Centre lease', 'scope_summary': 'Venue rental'}}}))
            database = root / 'test.db'
            migrate(database)
            refresh_s01_government_intelligence(database, root=root)
            preview = intelligence_review_preview(database)
            self.assertEqual(preview['count'], 1)
            self.assertEqual(preview['items'][0]['证据SHA256'], 'b' * 64)
            self.assertEqual(preview['items'][0]['中文翻译状态'], '待翻译与人工验收')

    def test_audit_does_not_claim_full_coverage(self):
        from signalforge.s01_government_intelligence import intelligence_coverage_audit, render_intelligence_digest
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / 'test.db'
            migrate(database)
            with connect(database) as conn, conn:
                conn.execute('CREATE TABLE s01_image_review (url TEXT PRIMARY KEY, review_status TEXT)')
                conn.execute("INSERT INTO s01_image_review VALUES ('https://myanmar.gov.mm/documents/test.jpg','OCR_REVIEW_REQUIRED')")
            (root / 'registry').mkdir()
            (root / 'registry' / 'S01-Reviewed-Issuer-Images-v1.json').write_text(json.dumps({'schema_version':1,'records':{}}))
            refresh_s01_government_intelligence(database, root=root)
            audit = intelligence_coverage_audit(database)
            self.assertEqual(audit['image_candidates'], 1)
            self.assertFalse(audit['coverage_complete'])
            self.assertIn('全站覆盖：未验证', render_intelligence_digest(database))
