from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from signalforge.cli import main, verb_manifest
from signalforge.config import Registry
from signalforge.mpa import (
    MpaParseError,
    classify_item_kind,
    extract_detail_pdf_url,
    extract_wordpress_post_id,
    parse_listing_records,
    preview_summary,
)


ROOT = Path(__file__).resolve().parents[1]


LISTING = """
<html><body><table><tbody>
<tr>
  <td class="text-center">02/06/2026</td>
  <td class="ps-4"><a href="https://www.mpa.gov.mm/announcements/open-tender-invitation-for-three-tugs-2//#announcements">Open Tender Invitation for three Tugs</a></td>
</tr>
<tr>
  <td class="text-center">21/08/2026</td>
  <td class="ps-4"><a href="https://www.mpa.gov.mm/announcements/auction-cargo//#announcements">ကုန်ပစ္စည်းများအား လေလံတင်ရောင်းချရန် အိတ်ဖွင့် တင်ဒါဖိတ်ခေါ်ခြင်း</a></td>
</tr>
</tbody></table></body></html>
""".encode("utf-8")


class MpaPreviewTests(unittest.TestCase):
    def test_listing_parser_extracts_and_classifies_rows(self) -> None:
        records = parse_listing_records(LISTING)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].publication_date, "2026-06-02")
        self.assertEqual(records[0].provisional_item_kind, "TENDER")
        self.assertEqual(records[0].provisional_source_id, "open-tender-invitation-for-three-tugs-2")
        self.assertEqual(records[0].identity_status, "PROVISIONAL_SLUG")
        self.assertEqual(records[0].classification_status, "TITLE_ONLY_REQUIRES_DETAIL_PDF")
        self.assertIsNone(records[0].wordpress_post_id)
        self.assertEqual(records[0].url, "https://www.mpa.gov.mm/announcements/open-tender-invitation-for-three-tugs-2/")
        self.assertEqual(records[1].provisional_item_kind, "AUCTION_NOTICE")

    def test_preview_summary_keeps_identity_provisional(self) -> None:
        summary = preview_summary(parse_listing_records(LISTING))
        self.assertEqual(summary["status"], "PREVIEW_ONLY")
        self.assertEqual(summary["source_id"], "S15A")
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["provisional_tender"], 1)
        self.assertEqual(summary["provisional_auction_notice"], 1)
        self.assertEqual(summary["provisional_unclassified"], 0)
        self.assertEqual(summary["identity"], "PROVISIONAL_SLUG_UNTIL_DETAIL_SHORTLINK")
        self.assertEqual(summary["classification"], "TITLE_ONLY_REQUIRES_DETAIL_PDF_FOR_FINAL_ITEM_KIND")

    def test_detail_shortlink_and_pdf_iframe_are_extractable(self) -> None:
        detail = b"""<html><head><link rel='shortlink' href='https://www.mpa.gov.mm/?p=37867' /></head>
        <body><iframe data-src='https://www.mpa.gov.mm/wp-content/uploads/2026/06/Three-Tug-Tender-Eng.pdf'></iframe></body></html>"""
        self.assertEqual(extract_wordpress_post_id(detail), 37867)
        self.assertEqual(
            extract_detail_pdf_url(detail),
            "https://www.mpa.gov.mm/wp-content/uploads/2026/06/Three-Tug-Tender-Eng.pdf",
        )

    def test_detail_without_shortlink_fails_closed(self) -> None:
        with self.assertRaisesRegex(MpaParseError, "shortlink post ID"):
            extract_wordpress_post_id(b"<html><head></head></html>")

    def test_detail_pdf_locator_fails_closed_when_ambiguous(self) -> None:
        detail = b"""<html><body>
        <iframe data-src='https://www.mpa.gov.mm/wp-content/uploads/a.pdf'></iframe>
        <iframe data-src='https://www.mpa.gov.mm/wp-content/uploads/b.pdf'></iframe>
        </body></html>"""
        with self.assertRaisesRegex(MpaParseError, "exactly one MPA detail PDF"):
            extract_detail_pdf_url(detail)

    def test_classifier_prioritizes_auction_and_disposal_semantics(self) -> None:
        self.assertEqual(classify_item_kind("Open Tender Invitation"), "TENDER")
        self.assertEqual(classify_item_kind("အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"), "TENDER")
        self.assertEqual(classify_item_kind("လေလံတင်ရောင်းချရန် အိတ်ဖွင့်တင်ဒါ"), "AUCTION_NOTICE")
        self.assertEqual(classify_item_kind("ပစ္စည်းများအား ရောင်းချရန် အိတ်ဖွင့်တင်ဒါ"), "AUCTION_NOTICE")
        self.assertEqual(classify_item_kind("သက်တမ်းလွန်ရေယာဉ်အား စာရင်းမှ ပယ်ဖျက်နိုင်ရေး အိတ်ဖွင့်တင်ဒါ"), "AUCTION_NOTICE")
        self.assertEqual(classify_item_kind("အသုံးပြုရန် မလိုအပ်တော့သည့် ပစ္စည်းများအား အိတ်ဖွင့်တင်ဒါ"), "AUCTION_NOTICE")
        self.assertEqual(classify_item_kind("ကုန်သေတ္တာအခွံ(၂၈)လုံးအား အိတ်ဖွင့်တင်ဒါ"), "AUCTION_NOTICE")
        self.assertEqual(classify_item_kind("General announcement"), "UNCLASSIFIED")

    def test_cli_preview_reads_file_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mpa.html"
            path.write_bytes(LISTING)
            self.assertEqual(main(["mpa-preview", "--html", str(path)]), 0)

    def test_preview_command_is_not_worker_verb(self) -> None:
        verbs = verb_manifest()["verbs"]
        self.assertNotIn("mpa-preview", verbs)
        self.assertNotIn("signalforge-mpa-preview", verbs)

    def test_s15a_remains_deferred_and_inactive(self) -> None:
        registry = Registry.load(ROOT)
        self.assertIn("S15A", registry.raw["deferred_sources"])
        self.assertNotIn("S15A", {source_id for source_id, _source in registry.enabled_sources()})
        self.assertFalse(registry.raw["providers"]["mac-mm-01"]["production_enabled"])
        self.assertFalse(registry.raw["providers"]["mac-mm-01"]["capabilities"]["remote_invocation"])


if __name__ == "__main__":
    unittest.main()
