from __future__ import annotations

import unittest

from signalforge.iwt_reviewed_enrichment import reviewed_iwt_overlay


class IwtReviewedEnrichmentTests(unittest.TestCase):
    def _overlay(self, **overrides: object) -> dict[str, object]:
        args: dict[str, object] = {
            "canonical_key": "iwt:1038:2026-08-25",
            "source_id": "S22",
            "item_kind": "TENDER",
            "reference_no": "IWT-NODE-1038",
            "publication_date": "2026-08-25",
            "article_url": "https://iwt.gov.mm/my/node/1038",
            "attachment_url": "https://iwt.gov.mm/my/file-download/download/public/1708",
        }
        args.update(overrides)
        return reviewed_iwt_overlay(**args)  # type: ignore[arg-type]

    def test_exact_identity_returns_reviewed_ocr_location(self) -> None:
        overlay = self._overlay()
        self.assertEqual(
            overlay["location"],
            "Inland Water Transport, Administration Department / Supply Division, No. 50 Pansodan Road, Yangon Region",
        )
        self.assertEqual(overlay["location_evidence"], "IWT_SOURCE_NATIVE_SCANNED_PDF_REVIEWED_OCR")
        self.assertEqual(
            overlay["reviewed_document_sha256"],
            "41d2614635fa440c0e226d682b5817f81e2f3c4ca31d9e4e0355332004436386",
        )
        self.assertEqual(
            overlay["reviewed_rendered_image_sha256"],
            "4f547056c203400c392eeee332ec3bac046e5ee5e444f5643f1647c4328b947a",
        )
        ocr = overlay["reviewed_ocr"]
        self.assertIsInstance(ocr, dict)
        self.assertEqual(ocr["critical_field_policy"], "ADDRESS_REQUIRES_MULTI_PSM_AND_VISUAL_CROSSCHECK")
        self.assertIs(overlay["reviewed_enrichment_read_only"], True)

    def test_wrong_reference_or_article_fails_closed(self) -> None:
        self.assertEqual(self._overlay(reference_no="IWT-NODE-9999"), {})
        self.assertEqual(self._overlay(article_url="https://iwt.gov.mm/my/node/9999"), {})

    def test_wrong_attachment_or_source_fails_closed(self) -> None:
        self.assertEqual(
            self._overlay(attachment_url="https://iwt.gov.mm/my/file-download/download/public/9999"),
            {},
        )
        self.assertEqual(self._overlay(source_id="S30"), {})


if __name__ == "__main__":
    unittest.main()
