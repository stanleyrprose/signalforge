from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from signalforge.translation import contains_myanmar, translate_myanmar_to_zh_hans


class _Response:
    def __init__(self, payload: object):
        self.payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit: int) -> bytes:
        return self.payload


class TranslationTests(unittest.TestCase):
    def test_detects_myanmar_unicode_blocks(self) -> None:
        self.assertTrue(contains_myanmar("အိတ်ဖွင့်တင်ဒါ"))
        self.assertTrue(contains_myanmar("English + မြန်မာ"))
        self.assertFalse(contains_myanmar("Open Tender No. 6/2026"))

    def test_without_key_fails_open_without_network(self) -> None:
        values = ["English", "အိတ်ဖွင့်တင်ဒါ"]
        with patch.dict("os.environ", {}, clear=True), patch("signalforge.translation.urlopen") as request:
            result, translated = translate_myanmar_to_zh_hans(values)
        self.assertEqual(result, values)
        self.assertFalse(translated)
        request.assert_not_called()

    def test_batches_only_myanmar_values_to_microsoft_translator(self) -> None:
        payload = [{"translations": [{"text": "公开招标", "to": "zh-Hans"}]}]
        values = ["Keep English", "အိတ်ဖွင့်တင်ဒါ"]
        with patch("signalforge.translation.urlopen", return_value=_Response(payload)) as request:
            result, translated = translate_myanmar_to_zh_hans(
                values,
                key="test-key",
                region="southeastasia",
                endpoint="https://translator.test",
            )
        self.assertEqual(result, ["Keep English", "公开招标"])
        self.assertTrue(translated)
        req = request.call_args.args[0]
        self.assertIn("from=my", req.full_url)
        self.assertIn("to=zh-Hans", req.full_url)
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body, [{"Text": "အိတ်ဖွင့်တင်ဒါ"}])
        self.assertEqual(req.get_header("Ocp-apim-subscription-key"), "test-key")
        self.assertEqual(req.get_header("Ocp-apim-subscription-region"), "southeastasia")

    def test_transport_failure_keeps_original_burmese(self) -> None:
        values = ["အိတ်ဖွင့်တင်ဒါ"]
        with patch("signalforge.translation.urlopen", side_effect=URLError("offline")):
            result, translated = translate_myanmar_to_zh_hans(values, key="test-key")
        self.assertEqual(result, values)
        self.assertFalse(translated)


if __name__ == "__main__":
    unittest.main()
