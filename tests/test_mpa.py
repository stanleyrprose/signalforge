from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter

from signalforge.cli import main, verb_manifest
from signalforge.config import Registry
from signalforge.mpa import (
    MpaParseError,
    MpaPdfFields,
    build_manual_bundle_preview,
    classify_item_kind,
    classify_pdf_text,
    extract_deadline,
    extract_detail_pdf_url,
    extract_reference_no,
    extract_wordpress_post_id,
    parse_listing_records,
    parse_pdf_business_fields,
    parse_tender_detail_with_attachments,
    parse_tender_listing,
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
        self.assertEqual(
            classify_item_kind("AWPT, MIP ဆိပ်ကမ်းများရှိ ID မရှိ လိုင်စင်မရှိ ကုန်သေတ္တာ(၆)လုံးအတွင်းရှိ ကုန်ပစ္စည်းများအား အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"),
            "AUCTION_NOTICE",
        )
        self.assertEqual(
            classify_item_kind("AWPT, MIP & MITT ဆိပ်ကမ်းတွင် ပြည်သူ့ဘဏ္ဍာသိမ်းဆည်းခဲ့သော ကုန်သေတ္တာ ၄၂ လုံး အတွင်းရှိ ကုန်ပစ္စည်းများအား အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"),
            "AUCTION_NOTICE",
        )
        self.assertEqual(classify_item_kind("General announcement"), "UNCLASSIFIED")

    def test_manual_bundle_preview_joins_listing_detail_pdf_without_writing_state(self) -> None:
        detail_url = "https://www.mpa.gov.mm/announcements/open-tender-invitation-for-three-tugs-2/"
        pdf_url = "https://www.mpa.gov.mm/wp-content/uploads/2026/06/Three-Tug-Tender-Eng.pdf"
        detail = f"""<html><head><link rel='shortlink' href='https://www.mpa.gov.mm/?p=37867' /></head>
        <body><iframe data-src='{pdf_url}'></iframe></body></html>""".encode()
        fields = MpaPdfFields(
            final_item_kind="AUCTION_NOTICE",
            classification_status="DETERMINISTIC_PDF",
            classification_basis="AUCTION_EN",
            deadline_local="2026-06-25T13:00:00",
            deadline_timezone="Asia/Yangon",
            deadline_status="FOUND",
            reference_no=None,
            scope_excerpt="three Tugs will be auctioned through an open tender system",
            page_count=2,
            text_chars=1941,
        )
        with patch("signalforge.mpa.parse_pdf_business_fields", return_value=fields):
            result = build_manual_bundle_preview(
                LISTING, detail, b"pdf-bytes", detail_url=detail_url, pdf_url=pdf_url
            )
        self.assertEqual(result["status"], "READY_FOR_MANUAL_COMMIT")
        candidate = result["candidate"]
        self.assertEqual(candidate["canonical_key"], "mpa:37867")
        self.assertEqual(candidate["item_kind"], "AUCTION_NOTICE")
        self.assertEqual(candidate["publication_date"], "2026-06-02")
        self.assertEqual(candidate["deadline"], "2026-06-25T13:00:00+06:30")
        self.assertEqual(candidate["reference_no"], "MPA-POST-37867")
        self.assertEqual(candidate["reference_no_kind"], "wordpress_post_id")
        self.assertEqual(candidate["pdf_url"], pdf_url)
        self.assertEqual(candidate["listing_provisional_item_kind"], "TENDER")

    def test_manual_bundle_preview_fails_closed_on_evidence_relationship_mismatch(self) -> None:
        detail_url = "https://www.mpa.gov.mm/announcements/open-tender-invitation-for-three-tugs-2/"
        pdf_url = "https://www.mpa.gov.mm/wp-content/uploads/2026/06/Three-Tug-Tender-Eng.pdf"
        detail = f"""<html><head><link rel='shortlink' href='https://www.mpa.gov.mm/?p=37867' /></head>
        <body><iframe data-src='{pdf_url}'></iframe></body></html>""".encode()
        with self.assertRaisesRegex(MpaParseError, "exactly one listing row"):
            build_manual_bundle_preview(
                LISTING, detail, b"pdf",
                detail_url="https://www.mpa.gov.mm/announcements/not-in-listing/",
                pdf_url=pdf_url,
            )
        with self.assertRaisesRegex(MpaParseError, "PDF URL does not match"):
            build_manual_bundle_preview(
                LISTING, detail, b"pdf",
                detail_url=detail_url,
                pdf_url="https://www.mpa.gov.mm/wp-content/uploads/2026/06/other.pdf",
            )

    def test_pdf_classifier_uses_authoritative_disposal_semantics(self) -> None:
        text = (
            "Open Tender Invitation. The following three Tugs will be auctioned through an open tender system. "
            "Date & Time (to submit): 25-6-2026 (1300)."
        )
        item_kind, status, basis, excerpt = classify_pdf_text(text)
        self.assertEqual(item_kind, "AUCTION_NOTICE")
        self.assertEqual(status, "DETERMINISTIC_PDF")
        self.assertEqual(basis, "AUCTION_EN")
        self.assertIn("auctioned", excerpt or "")
        self.assertEqual(extract_deadline(text), ("2026-06-25T13:00:00", "FOUND"))

    def test_pdf_classifier_does_not_treat_tender_form_purchase_as_procurement(self) -> None:
        text = (
            "အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း။ တင်ဒါပုံစံနှင့် စည်းကမ်းချက်များကို "
            "ရုံးတွင် ဆက်သွယ် ဝယ်ယူနိုင်ပြီး အသေးစိတ်မေးမြန်းနိုင်ပါသည်။"
        )
        self.assertEqual(classify_pdf_text(text)[:3], (None, "REVIEW_REQUIRED", None))

    def test_pdf_classifier_recognizes_procurement_and_myanmar_deadline(self) -> None:
        text = "Battery (With Acid)(9-Items) ဝယ်ယူရန် အိတ်ဖွင့်တင်ဒါ ၂၉-၅-၂၀၂၅ (၁၃:၀၀) နောက်ဆုံးထား တင်သွင်းရန်"
        item_kind, status, basis, _excerpt = classify_pdf_text(text)
        self.assertEqual(item_kind, "TENDER")
        self.assertEqual(status, "DETERMINISTIC_PDF")
        self.assertEqual(basis, "PURCHASE_MY")
        self.assertEqual(extract_deadline(text), ("2025-05-29T13:00:00", "FOUND"))

    def test_pdf_reference_and_service_semantics(self) -> None:
        text = "Port EDI Operation and Maintenance လုပ်ငန်းအတွက် ဝန်ဆောင်မှုရယူရန် တင်ဒါအမှတ် MPA-IR&HRD/01- 2026"
        item_kind, status, basis, _excerpt = classify_pdf_text(text)
        self.assertEqual(item_kind, "TENDER")
        self.assertEqual(status, "DETERMINISTIC_PDF")
        self.assertIn(basis, {"SERVICE_MY", "SERVICE_EN"})
        self.assertEqual(extract_reference_no(text), "MPA-IR&HRD/01-2026")
        self.assertEqual(extract_deadline(text), (None, "NOT_FOUND"))

    def test_pdf_classifier_recognizes_port_edi_infrastructure_refreshment(self) -> None:
        text = (
            "Port EDI Mini Data Center Hardware Device Infrastructure Refreshment Phase II (1 Lot) "
            "Tender No. MPA-IR&HRD/03-2026. Date & Time to submit: 18-6-2026 (13:00)."
        )
        item_kind, status, basis, excerpt = classify_pdf_text(text)
        self.assertEqual(item_kind, "TENDER")
        self.assertEqual(status, "DETERMINISTIC_PDF")
        self.assertEqual(basis, "INFRA_REFRESH_EN")
        self.assertIn("Infrastructure Refreshment", excerpt or "")
        self.assertEqual(extract_reference_no(text), "MPA-IR&HRD/03-2026")
        self.assertEqual(extract_deadline(text), ("2026-06-18T13:00:00", "FOUND"))

    def test_pdf_classifier_fails_closed_without_decisive_business_semantics(self) -> None:
        self.assertEqual(classify_pdf_text("Open Tender Invitation general notice")[:3], (None, "REVIEW_REQUIRED", None))
        buffer = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.write(buffer)
        with self.assertRaisesRegex(MpaParseError, "text too short"):
            parse_pdf_business_fields(buffer.getvalue())

    def test_automation_listing_prefilters_explicit_auction_titles(self) -> None:
        entries = parse_tender_listing(LISTING)
        self.assertEqual(
            [entry.url for entry in entries],
            ["https://www.mpa.gov.mm/announcements/open-tender-invitation-for-three-tugs-2/"],
        )

    def test_automation_pdf_semantics_override_procurement_looking_title(self) -> None:
        detail_url = "https://www.mpa.gov.mm/announcements/open-tender-invitation-for-three-tugs-2/"
        pdf_url = "https://www.mpa.gov.mm/wp-content/uploads/2026/06/Three-Tug-Tender-Eng.pdf"
        detail = f"""<html><head>
        <title>Open Tender Invitation for three Tugs - Myanma Port Authority</title>
        <link rel='shortlink' href='https://www.mpa.gov.mm/?p=37867' />
        <script type='application/ld+json'>{{"datePublished":"2026-06-02T05:00:00+00:00"}}</script>
        </head><body><iframe data-src='{pdf_url}'></iframe></body></html>""".encode()
        auction = MpaPdfFields(
            final_item_kind="AUCTION_NOTICE",
            classification_status="DETERMINISTIC_PDF",
            classification_basis="AUCTION_EN",
            deadline_local="2026-06-25T13:00:00",
            deadline_timezone="Asia/Yangon",
            deadline_status="FOUND",
            reference_no=None,
            scope_excerpt="three Tugs will be auctioned through an open tender system",
            page_count=2,
            text_chars=1941,
        )
        with patch("signalforge.mpa.parse_pdf_business_fields", return_value=auction):
            items = parse_tender_detail_with_attachments(detail, detail_url, [(pdf_url, b"pdf")])
        self.assertEqual(items, [])

    def test_automation_builds_canonical_procurement_only_from_detail_plus_pdf(self) -> None:
        detail_url = "https://www.mpa.gov.mm/announcements/port-edi-refresh/"
        pdf_url = "https://www.mpa.gov.mm/wp-content/uploads/2026/05/port-edi.pdf"
        detail = f"""<html><head>
        <title>Myanma Port Authority</title>
        <meta property='og:title' content='Port EDI Mini Data Center Infrastructure Refreshment Phase II (1 Lot) - Myanma Port Authority' />
        <link rel='shortlink' href='https://www.mpa.gov.mm/?p=38500' />
        <script type='application/ld+json'>{{"datePublished":"2026-05-29T05:00:00+00:00"}}</script>
        </head><body><iframe data-src='{pdf_url}'></iframe></body></html>""".encode()
        procurement = MpaPdfFields(
            final_item_kind="TENDER",
            classification_status="DETERMINISTIC_PDF",
            classification_basis="INFRA_REFRESH_EN",
            deadline_local="2026-06-18T13:00:00",
            deadline_timezone="Asia/Yangon",
            deadline_status="FOUND",
            reference_no="MPA-IR&HRD/03-2026",
            scope_excerpt="Port EDI Mini Data Center Hardware Device Infrastructure Refreshment Phase II (1 Lot)",
            page_count=1,
            text_chars=1200,
        )
        with patch("signalforge.mpa.parse_pdf_business_fields", return_value=procurement):
            items = parse_tender_detail_with_attachments(detail, detail_url, [(pdf_url, b"pdf")])
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.canonical_key, "mpa:38500")
        payload = item.payload()
        self.assertEqual(payload["item_kind"], "TENDER")
        self.assertEqual(payload["deadline"], "2026-06-18")
        self.assertEqual(payload["deadline_time"], "13:00")
        self.assertEqual(payload["reference_no"], "MPA-IR&HRD/03-2026")
        self.assertEqual(payload["title"], "Port EDI Mini Data Center Infrastructure Refreshment Phase II (1 Lot)")
        self.assertEqual(payload["scope_excerpt"], payload["title"])
        self.assertEqual(payload["quantity_or_lot_summary"], "1 Lot")
        self.assertEqual(payload["quantity_or_lot_confidence"], "HIGH")

    def test_provider_target_budgets_are_applied_per_target(self) -> None:
        from signalforge.engine import _acquire_source_bytes

        source = Registry.load(ROOT).source("S15A")
        cases = [
            ("DISCOVERY", "https://www.mpa.gov.mm/tenders-and-announcement/", ["text/html"], 2_000_000, 90, "LISTING"),
            ("HTML", "https://www.mpa.gov.mm/announcements/example/", ["text/html"], 2_000_000, 90, "DETAIL"),
            ("PDF", "https://www.mpa.gov.mm/wp-content/uploads/example.pdf", ["application/pdf"], 10_485_760, 120, "PDF"),
        ]
        for target_kind, url, types, max_bytes, timeout, role in cases:
            with patch("signalforge.engine.acquire_provider_bytes", return_value=object()) as provider:
                _acquire_source_bytes(
                    source=source,
                    database=Path("/tmp/unused.db"),
                    scheduler_run_id="00000000-0000-0000-0000-000000000001",
                    source_id="S15A",
                    reason="DIAGNOSTIC",
                    target_kind=target_kind,
                    url=url,
                    expected_content_types=types,
                    observed_at="2026-10-01T00:00:00Z",
                    fetcher=lambda *_args, **_kwargs: b"",
                )
            kwargs = provider.call_args.kwargs
            self.assertEqual(kwargs["max_bytes"], max_bytes)
            self.assertEqual(kwargs["timeout_seconds"], timeout)
            self.assertEqual(kwargs["target_role"], role)

    def test_cli_preview_reads_file_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mpa.html"
            path.write_bytes(LISTING)
            self.assertEqual(main(["mpa-preview", "--html", str(path)]), 0)

    def test_preview_commands_are_not_worker_verbs(self) -> None:
        verbs = verb_manifest()["verbs"]
        self.assertNotIn("mpa-preview", verbs)
        self.assertNotIn("signalforge-mpa-preview", verbs)
        self.assertNotIn("mpa-pdf-preview", verbs)
        self.assertNotIn("signalforge-mpa-pdf-preview", verbs)
        self.assertNotIn("mpa-provider-bundle-preview", verbs)
        self.assertNotIn("signalforge-mpa-provider-bundle-preview", verbs)

    def test_s15a_is_active_with_bounded_provider_listing_detail_pdf(self) -> None:
        registry = Registry.load(ROOT)
        source = registry.source("S15A")
        self.assertNotIn("S15A", registry.raw["deferred_sources"])
        self.assertIn("S15A", {source_id for source_id, _source in registry.enabled_sources()})
        self.assertEqual(source["adapter"], "mpa_tender")
        self.assertEqual(source["engine"], "provider")
        self.assertEqual(source["provider_id"], "mac-mm-01")
        self.assertEqual(source["provider_capability"], "PUBLIC_READ_ACQUIRE")
        self.assertEqual(
            source["provider_target_roles"],
            {"DISCOVERY": "LISTING", "HTML": "DETAIL", "PDF": "PDF"},
        )
        self.assertEqual(
            source["provider_target_limits"],
            {
                "DISCOVERY": {"max_bytes": 2000000, "timeout_seconds": 90},
                "HTML": {"max_bytes": 2000000, "timeout_seconds": 90},
                "PDF": {"max_bytes": 10485760, "timeout_seconds": 120},
            },
        )
        self.assertEqual(
            source["acquisition_policy"]["supplementary"],
            [{
                "method": "MAC_BROWSER_PROVIDER",
                "target_kind": "PDF",
                "required": True,
                "max_count": 1,
                "same_origin_only": True,
            }],
        )
        self.assertTrue(source["attachment_policy"]["fetch_in_primary_pipeline"])
        self.assertEqual(source["attachment_policy"]["required_primary_attachments"], 1)
        self.assertTrue(registry.raw["providers"]["mac-mm-01"]["production_enabled"])
        self.assertEqual(registry.raw["providers"]["mac-mm-01"]["invocation_mode"], "pull_ssh_v1")
        self.assertTrue(registry.raw["providers"]["mac-mm-01"]["capabilities"]["remote_invocation"])


if __name__ == "__main__":
    unittest.main()
