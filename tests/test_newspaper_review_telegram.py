"""No-network checks for the explicitly user-approved newspaper QA send path."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "tools" / "send_newspaper_acceptance_tg.py"
SPEC = importlib.util.spec_from_file_location("newspaper_manual_tg", FILE)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class NewspaperReviewTelegramTests(unittest.TestCase):
    def test_user_scoped_review_images_and_text_send_once_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for prefix in ("km", "mal"):
                (root / f"{prefix}-p28.jpg").write_bytes(b"\xff\xd8mock-jpeg")
                (root / f"{prefix}-p28-zh.txt").write_text("人工审核：原文识别不清", encoding="utf-8")
            receipt = root / "receipts.json"
            with (
                patch.object(mod, "INPUT_ROOT", root),
                patch.object(mod, "RECEIPTS", receipt),
                patch.object(mod, "_credentials", return_value=("fake-token", "allowed-chat")),
                patch.object(mod, "_send_photo", side_effect=(101, 103)) as photos,
                patch.object(mod, "_send_message", side_effect=(102, 104)) as messages,
            ):
                mod.main()
                self.assertEqual(photos.call_count, 2)
                self.assertEqual(messages.call_count, 2)
                self.assertEqual(
                    json.loads(receipt.read_text()),
                    {
                        "R01.source_photo": 101, "R01.translation": 102,
                        "R02.source_photo": 103, "R02.translation": 104,
                    },
                )
                mod.main()
                self.assertEqual(photos.call_count, 2)
                self.assertEqual(messages.call_count, 2)

    def test_bounded_photo_requires_jpeg_and_does_not_invoke_telegram(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "bad.jpg"
            image.write_bytes(b"not-image")
            with self.assertRaisesRegex(RuntimeError, "bounded JPEG"):
                mod._send_photo("fake-token", "allowed-chat", image, "review")


if __name__ == "__main__":
    unittest.main()
