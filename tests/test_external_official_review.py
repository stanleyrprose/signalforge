from __future__ import annotations

import hashlib
import unittest
import uuid
from unittest.mock import patch

from signalforge.external_official_review import build_external_official_review_packet


class _Page:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _Reader:
    text = ""

    def __init__(self, _stream) -> None:  # type: ignore[no-untyped-def]
        self.pages = [_Page(self.text)]


def _lead(url: str = "https://myanmar.gov.mm/documents/20143/0/mpt.pdf/abc") -> dict[str, object]:
    return {
        "lead_id": "national-portal:abc",
        "title": "MPT official tender",
        "agency": "Ministry of Digital Development and Communications",
        "closing_date_hint": "2026-09-29",
        "url": url,
        "target_source_hint": "S13",
        "evidence_kind": "NATIONAL_PORTAL_HOSTED_DOCUMENT",
        "mission_sector_hint": "CONSTRUCTION",
        "aggregator_only": True,
        "canonical_truth": False,
    }


def _native_mpt_text(*, deadline_time: str = "14း00") -> str:
    return f"""
    Ministry of Digital Development and Communications
    Myanma Posts and Telecommunications
    Open Tender Invitation
    1။ MPT invites construction tender - နေပြည်တော် ပုဗ္ဗသီရိ exchange office RC wall and roof repair.
    2။ Tender form sale starts (11-09-2026)
    3။ Tender form sale closes (24-09-2026) ညနေ(04း30)
    4။ site survey (25-09-20 26)
    5။ Tender closes (29-09-2026) 09း30 to {deadline_time}
    6။ Tender submission place Yangon procurement office.
    """


def _ocr_mpt_text(*, deadline_time: str = "14း00") -> str:
    return f"""
    ဒီဂျစ်တယ်ဖွံ့ဖြိုးတိုးတက်ရေးနှင့် ဆက်သွယ်ရေးဝန်ကြီးဌာန
    မြန်မာ့ဆက်သွယ်ရေးလုပ်ငန်း
    အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း
    နေပြည်တော်ကောင်စီ ပုဗ္ဗသီရိမြို့နယ် exchange office RC wall and roof repair
    ၂ တင်ဒါပုံစံစတင်ရောင်းချမည့်နေ့ရက်/အချိန် - (၁၁-၀၉-၂၀၂၆)ရက်
    ၃ တင်ဒါပုံစံအရောင်းပိတ်မည့်နေ့ရက်/အချိန် - (၂၄-၀၉-၂၀၂၆)ရက်/ ညနေ(၀၄း၃၀)
    ၄ site survey ဆင်းရမည့်ရက်/အချိန် - (၂၅-၀၉-၂၀၂၆)ရက်
    ၅ တင်ဒါပိတ်မည့်နေ့ရက်/အချိန် - (၂၉-၀၉-၂၀၂၆)ရက်/ (၀၉း၃၀)နာရီမှ({deadline_time})နာရီအထိ
    """


def _ocr_result(
    payload: bytes,
    text: str,
    *,
    provider_fetch_sha256: str | None = None,
    input_sha256: str | None = None,
    page_count: int = 1,
    processed_pages: int = 1,
    truncated: bool = False,
) -> dict[str, object]:
    digest = hashlib.sha256(payload).hexdigest()
    return {
        "provider_contract_version": 1,
        "provider_request_id": str(uuid.uuid4()),
        "provider_fetch_sha256": provider_fetch_sha256 or digest,
        "input_sha256": input_sha256 or digest,
        "input_bytes": len(payload),
        "engine": "tesseract",
        "rasterizer": "macOS PDFKit",
        "model_profile": "tessdata_best",
        "languages": ["mya", "eng"],
        "psm": 6,
        "page_count": page_count,
        "processed_pages": processed_pages,
        "page_limit_truncated": truncated,
        "pages": [{"page": i + 1, "text": text if i == 0 else ""} for i in range(processed_pages)],
        "text": text,
        "mean_confidence": 78.5,
        "network_access": False,
        "intermediate_images_retained": False,
    }


class ExternalOfficialReviewTests(unittest.TestCase):
    def test_native_text_alone_can_never_be_review_ready(self) -> None:
        _Reader.text = _native_mpt_text()
        payload = b"%PDF-1.4 native-only fixture"
        with patch("signalforge.external_official_review.PdfReader", _Reader):
            packet = build_external_official_review_packet(
                _lead(),
                fetcher=lambda *_args, **_kwargs: payload,
            )
        self.assertEqual(packet["status"], "OCR_REQUIRED_NOT_AVAILABLE")
        self.assertTrue(packet["ocr_required"])
        self.assertEqual(packet["review_state"], "PENDING_HUMAN_CONFIRMATION")
        self.assertFalse(packet["verified_external"])

    def test_mpt_v1_dual_evidence_packet_requires_a_equals_b_equals_c(self) -> None:
        _Reader.text = _native_mpt_text()
        payload = b"%PDF-1.4 dual-evidence fixture"
        ocr = _ocr_result(payload, _ocr_mpt_text())
        with patch("signalforge.external_official_review.PdfReader", _Reader):
            packet = build_external_official_review_packet(
                _lead(),
                fetcher=lambda *_args, **_kwargs: payload,
                ocr_provider=lambda _url: ocr,
            )

        digest = hashlib.sha256(payload).hexdigest()
        self.assertEqual(packet["status"], "DUAL_EVIDENCE_REVIEW_READY")
        self.assertEqual(packet["template_profile"], "S13_MPT_NUMBERED_TENDER_V1")
        self.assertEqual(packet["document_sha256"], digest)
        self.assertEqual(packet["provider_fetch_sha256"], digest)
        self.assertEqual(packet["ocr_input_sha256"], digest)
        self.assertEqual(packet["authority"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(packet["production_effect"], "NONE")
        self.assertEqual(packet["writes"], "NONE")
        self.assertFalse(packet["canonical_truth"])
        self.assertFalse(packet["verified_external"])
        self.assertTrue(packet["human_confirmation_required"])

        reconciliation = packet["reconciliation"]
        self.assertTrue(reconciliation["sha_a_equals_b_equals_c"])
        for key in (
            "project_location_hint",
            "tender_form_sale_close",
            "tender_form_sale_close_time",
            "site_survey_date",
            "proposed_deadline",
            "tender_submission_start_time",
            "proposed_deadline_time",
        ):
            self.assertEqual(reconciliation["field_statuses"][key], "AGREED", key)

        fields = packet["proposed_fields"]
        self.assertEqual(fields["project_location_hint"], "Pobbathiri Township, Nay Pyi Taw")
        self.assertEqual(fields["tender_form_sale_start"], "2026-09-11")
        self.assertEqual(fields["tender_form_sale_close"], "2026-09-24")
        self.assertEqual(fields["tender_form_sale_close_time"], "16:30")
        self.assertEqual(fields["site_survey_date"], "2026-09-25")
        self.assertEqual(fields["proposed_deadline"], "2026-09-29")
        self.assertEqual(fields["tender_submission_start_time"], "09:30")
        self.assertEqual(fields["proposed_deadline_time"], "14:00")
        self.assertIn("Bid submission 2026-09-29 09:30-14:00", fields["next_action_summary"])
        self.assertIn("RC wall and roof repair", fields["scope_excerpt"])

    def test_conflicting_deadline_time_fails_closed_and_preserves_both_values(self) -> None:
        _Reader.text = _native_mpt_text(deadline_time="14း00")
        payload = b"%PDF-1.4 conflict fixture"
        ocr = _ocr_result(payload, _ocr_mpt_text(deadline_time="၁၆း၀၀"))
        with patch("signalforge.external_official_review.PdfReader", _Reader):
            packet = build_external_official_review_packet(
                _lead(),
                fetcher=lambda *_args, **_kwargs: payload,
                ocr_provider=lambda _url: ocr,
            )

        self.assertEqual(packet["status"], "DUAL_EVIDENCE_CONFLICT")
        self.assertIn("proposed_deadline_time", packet["reconciliation"]["conflict_fields"])
        evidence = packet["reconciliation"]["field_evidence"]["proposed_deadline_time"]
        self.assertEqual(evidence["native"], "14:00")
        self.assertEqual(evidence["ocr"], "16:00")
        self.assertEqual(evidence["status"], "CONFLICT")
        self.assertIsNone(packet["proposed_fields"]["proposed_deadline_time"])
        self.assertIsNone(packet["proposed_fields"]["next_action_summary"])

    def test_scanned_pdf_can_be_ocr_only_but_never_dual_evidence_ready(self) -> None:
        _Reader.text = "scan"
        payload = b"%PDF-1.4 scan fixture"
        ocr = _ocr_result(payload, _ocr_mpt_text())
        with patch("signalforge.external_official_review.PdfReader", _Reader):
            packet = build_external_official_review_packet(
                _lead(),
                fetcher=lambda *_args, **_kwargs: payload,
                ocr_provider=lambda _url: ocr,
            )

        self.assertEqual(packet["status"], "OCR_ONLY_REVIEW_PACKET")
        self.assertTrue(packet["reconciliation"]["sha_a_equals_b_equals_c"])
        self.assertEqual(packet["reconciliation"]["field_statuses"]["proposed_deadline"], "OCR_ONLY_PROPOSED")
        self.assertEqual(packet["proposed_fields"]["proposed_deadline"], "2026-09-29")
        self.assertIsNone(packet["proposed_fields"]["next_action_summary"])

    def test_ocr_failure_never_falls_back_to_native_ready(self) -> None:
        _Reader.text = _native_mpt_text()
        payload = b"%PDF-1.4 OCR failure fixture"

        def fail(_url: str) -> dict[str, object]:
            raise TimeoutError("provider OCR timeout")

        with patch("signalforge.external_official_review.PdfReader", _Reader):
            packet = build_external_official_review_packet(
                _lead(),
                fetcher=lambda *_args, **_kwargs: payload,
                ocr_provider=fail,
            )
        self.assertEqual(packet["status"], "OCR_REQUIRED_FAILED")
        self.assertIn("provider OCR timeout", packet["reason"])
        self.assertFalse(packet["verified_external"])

    def test_multi_page_truncation_is_not_review_ready(self) -> None:
        _Reader.text = _native_mpt_text()
        payload = b"%PDF-1.4 multi-page fixture"
        ocr = _ocr_result(
            payload,
            _ocr_mpt_text(),
            page_count=20,
            processed_pages=12,
            truncated=True,
        )
        with patch("signalforge.external_official_review.PdfReader", _Reader):
            packet = build_external_official_review_packet(
                _lead(),
                fetcher=lambda *_args, **_kwargs: payload,
                ocr_provider=lambda _url: ocr,
            )
        self.assertEqual(packet["status"], "OCR_PAGE_LIMIT_REVIEW_REQUIRED")
        self.assertEqual(packet["ocr_page_count"], 20)
        self.assertEqual(packet["ocr_processed_pages"], 12)

    def test_sha_a_b_c_conflict_fails_closed(self) -> None:
        _Reader.text = _native_mpt_text()
        payload = b"%PDF-1.4 sha fixture"
        ocr = _ocr_result(
            payload,
            _ocr_mpt_text(),
            provider_fetch_sha256="b" * 64,
            input_sha256="c" * 64,
        )
        with patch("signalforge.external_official_review.PdfReader", _Reader):
            packet = build_external_official_review_packet(
                _lead(),
                fetcher=lambda *_args, **_kwargs: payload,
                ocr_provider=lambda _url: ocr,
            )
        self.assertEqual(packet["status"], "EVIDENCE_SHA_CONFLICT")
        self.assertEqual(packet["reason"], "PROVIDER_FETCH_AND_OCR_PDF_SHA256_DIFFER")

    def test_generic_portal_pdf_gets_ocr_but_does_not_reuse_mpt_section_semantics(self) -> None:
        generic = _lead()
        generic["agency"] = "Ministry of Transport and Communications"
        generic["target_source_hint"] = "S21"
        _Reader.text = """
        Myanma Railways
        Open Tender
        1။ Bridge repair works.
        2။ Some unrelated milestone (11-09-2026)
        3။ Another milestone (24-09-2026) 04း30
        4။ Another milestone (25-09-2026)
        5။ Another milestone (29-09-2026) 09း30 to 14း00
        """
        payload = b"%PDF-1.4 generic fixture"
        ocr = _ocr_result(payload, "Myanma Railways bridge repair 29-09-2026 09:30 14:00")
        with patch("signalforge.external_official_review.PdfReader", _Reader):
            packet = build_external_official_review_packet(
                generic,
                fetcher=lambda *_args, **_kwargs: payload,
                ocr_provider=lambda _url: ocr,
            )
        self.assertEqual(packet["status"], "PARTIAL_REVIEW_PACKET")
        self.assertEqual(packet["template_profile"], "GENERIC_TEXT_ONLY_V1")
        self.assertEqual(packet["reason"], "UNREVIEWED_DOCUMENT_TEMPLATE_SEMANTICS")
        fields = packet["proposed_fields"]
        self.assertIn("Myanma Railways", fields["issuer_document_evidence"])
        self.assertIn("Bridge repair works", fields["scope_excerpt"])
        self.assertIsNone(fields["proposed_deadline"])
        self.assertIsNone(fields["next_action_summary"])

    def test_native_fetch_failure_still_requires_human_review_even_when_ocr_succeeds(self) -> None:
        payload = b"%PDF-1.4 provider-side-only fixture"
        ocr = _ocr_result(payload, _ocr_mpt_text())

        def fetcher(*_args, **_kwargs) -> bytes:
            raise TimeoutError("native fetch timeout")

        packet = build_external_official_review_packet(
            _lead(),
            fetcher=fetcher,
            ocr_provider=lambda _url: ocr,
        )
        self.assertEqual(packet["status"], "OCR_ONLY_REVIEW_PACKET")
        self.assertIsNone(packet["reconciliation"]["native_sha256"])
        self.assertFalse(packet["reconciliation"]["sha_a_equals_b_equals_c"])
        self.assertIsNone(packet["proposed_fields"]["next_action_summary"])

    def test_rejects_unsafe_portal_url_before_fetch_or_ocr(self) -> None:
        invalid = (
            "https://myanmar.gov.mm/documents/../admin.pdf",
            "https://myanmar.gov.mm/documents/abc.pdf?x=1",
            "https://myanmar.gov.mm/documents/abc.pdf#frag",
            "https://user:pass@myanmar.gov.mm/documents/abc.pdf",
        )
        for url in invalid:
            fetch_called = False
            ocr_called = False

            def fetcher(*_args, **_kwargs) -> bytes:
                nonlocal fetch_called
                fetch_called = True
                return b"%PDF-1.4"

            def ocr_provider(_url: str) -> dict[str, object]:
                nonlocal ocr_called
                ocr_called = True
                return {}

            packet = build_external_official_review_packet(
                _lead(url), fetcher=fetcher, ocr_provider=ocr_provider
            )
            self.assertEqual(packet["status"], "REJECTED_INPUT", url)
            self.assertFalse(fetch_called, url)
            self.assertFalse(ocr_called, url)

    def test_rejects_non_portal_document_before_fetch_or_ocr(self) -> None:
        fetch_called = False
        ocr_called = False

        def fetcher(*_args, **_kwargs) -> bytes:
            nonlocal fetch_called
            fetch_called = True
            return b"%PDF-1.4"

        def ocr_provider(_url: str) -> dict[str, object]:
            nonlocal ocr_called
            ocr_called = True
            return {}

        packet = build_external_official_review_packet(
            _lead("https://example.com/file.pdf"),
            fetcher=fetcher,
            ocr_provider=ocr_provider,
        )
        self.assertEqual(packet["status"], "REJECTED_INPUT")
        self.assertFalse(fetch_called)
        self.assertFalse(ocr_called)


if __name__ == "__main__":
    unittest.main()
