from __future__ import annotations

import hashlib
import unittest
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


class ExternalOfficialReviewTests(unittest.TestCase):
    def test_text_native_pdf_builds_proposed_review_packet_without_verifying_it(self) -> None:
        _Reader.text = """
        Ministry of Digital Development and Communications
        Myanma Posts and Telecommunications
        Open Tender Invitation
        1။ MPT invites construction tender - နေပြည်တော် ပုဗXသီရိ exchange office RC wall and roof repair.
        2။ Tender form sale starts (11-09-2026)
        3။ Tender form sale closes (24-09-2026) ညနေ(04း30)
        4။ site survey (25-09-20 26)
        5။ Tender closes (29-09-2026) 09း30 to 14း00
        6။ Tender submission place Yangon procurement office.
        """
        payload = b"%PDF-1.4 fake fixture"
        with patch("signalforge.external_official_review.PdfReader", _Reader):
            packet = build_external_official_review_packet(
                _lead(),
                fetcher=lambda *_args, **_kwargs: payload,
            )

        self.assertEqual(packet["status"], "TEXT_NATIVE_REVIEW_READY")
        self.assertEqual(packet["template_profile"], "S13_MPT_NUMBERED_TENDER_V0")
        self.assertEqual(packet["document_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(packet["authority"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(packet["production_effect"], "NONE")
        self.assertEqual(packet["writes"], "NONE")
        self.assertEqual(packet["review_state"], "PENDING_HUMAN_CONFIRMATION")
        self.assertFalse(packet["canonical_truth"])
        self.assertFalse(packet["verified_external"])
        self.assertTrue(packet["human_confirmation_required"])

        fields = packet["proposed_fields"]
        self.assertEqual(fields["issuer_hint"], "Ministry of Digital Development and Communications")
        self.assertIn("Myanma Posts and Telecommunications", fields["issuer_document_evidence"])
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
        self.assertIn("Yangon procurement office", fields["submission_location_evidence"])

    def test_generic_portal_pdf_does_not_reuse_mpt_section_semantics(self) -> None:
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
        with patch("signalforge.external_official_review.PdfReader", _Reader):
            packet = build_external_official_review_packet(
                generic,
                fetcher=lambda *_args, **_kwargs: payload,
            )
        self.assertEqual(packet["status"], "PARTIAL_REVIEW_PACKET")
        self.assertEqual(packet["template_profile"], "GENERIC_TEXT_ONLY_V0")
        self.assertEqual(packet["reason"], "UNREVIEWED_DOCUMENT_TEMPLATE_SEMANTICS")
        fields = packet["proposed_fields"]
        self.assertIn("Myanma Railways", fields["issuer_document_evidence"])
        self.assertIn("Bridge repair works", fields["scope_excerpt"])
        self.assertIsNone(fields["proposed_deadline"])
        self.assertIsNone(fields["tender_form_sale_close"])
        self.assertIsNone(fields["next_action_summary"])

    def test_sparse_text_pdf_requires_ocr_or_manual_review(self) -> None:
        _Reader.text = "scan"
        payload = b"%PDF-1.4 fake scan"
        with patch("signalforge.external_official_review.PdfReader", _Reader):
            packet = build_external_official_review_packet(
                _lead(),
                fetcher=lambda *_args, **_kwargs: payload,
            )
        self.assertEqual(packet["status"], "NEEDS_OCR_OR_MANUAL_REVIEW")
        self.assertEqual(packet["reason"], "TEXT_NATIVE_EXTRACTION_TOO_SPARSE")
        self.assertFalse(packet["verified_external"])

    def test_rejects_non_portal_document_without_fetch(self) -> None:
        called = False

        def fetcher(*_args, **_kwargs) -> bytes:
            nonlocal called
            called = True
            return b"%PDF-1.4"

        packet = build_external_official_review_packet(
            _lead("https://example.com/file.pdf"),
            fetcher=fetcher,
        )
        self.assertEqual(packet["status"], "REJECTED_INPUT")
        self.assertFalse(called)

    def test_fetch_failure_stays_review_only(self) -> None:
        def fetcher(*_args, **_kwargs) -> bytes:
            raise TimeoutError("timeout")

        packet = build_external_official_review_packet(_lead(), fetcher=fetcher)
        self.assertEqual(packet["status"], "FETCH_FAILED")
        self.assertEqual(packet["authority"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(packet["production_effect"], "NONE")
        self.assertFalse(packet["verified_external"])


if __name__ == "__main__":
    unittest.main()
