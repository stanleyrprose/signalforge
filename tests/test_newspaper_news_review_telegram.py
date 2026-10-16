"""Offline review message idempotency for news-only R03/R04 acceptance."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
SPEC = importlib.util.spec_from_file_location(
    "news_review_dispatch", ROOT / "tools/send_newspaper_news_review_tg.py"
)
assert SPEC and SPEC.loader
dispatch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dispatch)


class NewspaperNewsReviewTelegramTests(unittest.TestCase):
    def test_documents_and_explanations_do_not_resend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for prefix in ("R03", "R04"):
                (root / (prefix + "-source.pdf")).write_bytes(b"%PDF-FAKE")
                (root / (prefix + "-news-zh.pdf")).write_bytes(b"%PDF-FAKE")
            receipt = root / "receipts.json"
            with patch.object(dispatch, "ROOT", root), \
                 patch.object(dispatch, "RECEIPTS", receipt), \
                 patch.object(dispatch, "_credentials", return_value=("fake-token", "allowlisted-chat")), \
                 patch.object(dispatch, "_send_document", side_effect=(301, 302, 304, 305)) as docs, \
                 patch.object(dispatch, "_send_text", side_effect=(303, 306)) as texts:
                dispatch.main()
                dispatch.main()
                self.assertEqual(docs.call_count, 4)
                self.assertEqual(texts.call_count, 2)
            state = json.loads(receipt.read_text())
            self.assertEqual(state["R03.source"], 301)
            self.assertEqual(state["R03.news"], 302)
            self.assertEqual(state["R03.instructions"], 303)
            self.assertEqual(state["R04.instructions"], 306)

    def test_pdf_gate_rejects_arbitrary_nonpdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.pdf"
            bad.write_bytes(b"notpdf")
            with self.assertRaisesRegex(RuntimeError, "PDF"):
                dispatch._send_document("fake", "chat", bad, "caption")


if __name__ == "__main__":
    unittest.main()
