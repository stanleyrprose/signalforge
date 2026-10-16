"""R05 two-PDF review and full official issue send: no duplicate Telegram sends."""
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
    "r05_manual_tg", ROOT / "tools/send_newspaper_r05_review_tg.py",
)
assert SPEC and SPEC.loader
r05 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r05)


class NewspaperR05TelegramTests(unittest.TestCase):
    def test_three_review_pdf_and_note_sent_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for _key, name, _caption in r05.DELIVERIES:
                (root / name).write_bytes(b"%PDF-FAKE")
            with patch.object(r05, "ROOT", root), \
                 patch.object(r05, "RECEIPTS", root / "receipts.json"), \
                 patch.object(r05, "_credentials", return_value=("fake", "allowed")), \
                 patch.object(r05, "_send_document", side_effect=(501, 502, 503)) as docs, \
                 patch.object(r05, "_send_text", return_value=504) as messages:
                r05.main()
                r05.main()
                self.assertEqual(docs.call_count, 3)
                self.assertEqual(messages.call_count, 1)
            receipts = json.loads((root / "receipts.json").read_text())
            self.assertEqual(receipts, {
                "R05.official": 501,
                "R05.highlights": 502,
                "R05.coverage": 503,
                "R05.instructions": 504,
            })

    def test_missing_review_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(r05, "ROOT", root), \
                 patch.object(r05, "RECEIPTS", root / "receipts.json"), \
                 patch.object(r05, "_credentials", return_value=("fake", "allowed")), \
                 patch.object(r05, "_send_document") as send:
                with self.assertRaisesRegex(RuntimeError, "Missing preapproved"):
                    r05.main()
                send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
