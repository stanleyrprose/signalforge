"""R06 acceptance delivery is idempotent and not a tender business push."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
SPEC=importlib.util.spec_from_file_location("r06_tg",ROOT/"tools/send_newspaper_r06_review_tg.py")
assert SPEC and SPEC.loader
mod=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class R06SendTests(unittest.TestCase):
    def test_two_pdfs_and_explanation_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for _,name,_ in mod.DOCS:
                (root/name).write_bytes(b"%PDF-MOCK")
            receipt=root/"send-receipts.json"
            with patch.object(mod,"ROOT",root), patch.object(mod,"RECEIPTS",receipt), \
                 patch.object(mod,"_credentials",return_value=("mock","chat")), \
                 patch.object(mod,"_send_document",side_effect=(601,602)) as docs, \
                 patch.object(mod,"_send_text",return_value=603) as txt:
                mod.main()
                mod.main()
                self.assertEqual(docs.call_count,2)
                self.assertEqual(txt.call_count,1)
                values=json.loads(receipt.read_text())
                self.assertEqual(values,{"R06.edition":601,"R06.ledger":602,"R06.instructions":603})

    def test_missing_pdf_has_no_side_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.object(mod,"ROOT",root), \
                 patch.object(mod,"RECEIPTS",root/"send-receipts.json"), \
                 patch.object(mod,"_credentials",return_value=("mock","chat")), \
                 patch.object(mod,"_send_document") as docs:
                with self.assertRaisesRegex(RuntimeError,"Missing approved"):
                    mod.main()
                docs.assert_not_called()

if __name__=="__main__":
    unittest.main()
