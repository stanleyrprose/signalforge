from __future__ import annotations

import unittest

from signalforge.mofa_reviewed_enrichment import reviewed_mofa_overlay


class MofaReviewedEnrichmentTests(unittest.TestCase):
    def _overlay(self, **overrides: object) -> dict[str, object]:
        args: dict[str, object] = {
            "canonical_key": "mofa:59800",
            "source_id": "S30",
            "item_kind": "TENDER",
            "reference_no": "MOFA-POST-59800",
            "publication_date": "2026-09-04",
            "article_url": "https://www.mofa.gov.mm/%E1%80%94%E1%80%AD%E1%80%AF%E1%80%84%E1%80%BA%E1%80%84%E1%80%B6%E1%80%81%E1%80%BC%E1%80%AC%E1%80%B8%E1%80%9B%E1%80%B1%E1%80%B8%E1%80%9D%E1%80%94%E1%80%BA%E1%80%80%E1%80%BC%E1%80%AE%E1%80%B8-386/",
            "attachment_url": "https://www.mofa.gov.mm/wp-content/uploads/2026/09/Tender-Announcement.pdf",
            "evidence_sha256": "aad5b2c3e51ffc289edb5018254f364896b01d14bee8fa3be7e362e756e130c7",
        }
        args.update(overrides)
        return reviewed_mofa_overlay(**args)  # type: ignore[arg-type]

    def test_exact_source_native_pdf_identity_returns_reviewed_participation_fields(self) -> None:
        overlay = self._overlay()
        self.assertEqual(
            overlay["location"],
            "Ministry of Foreign Affairs, Office No.9, Nay Pyi Taw",
        )
        self.assertIn("9/18 16:30", str(overlay["next_action_summary"]))
        self.assertEqual(overlay["reviewed_enrichment_status"], "REVIEWED_SOURCE_NATIVE_OFFICIAL_PDF")
        self.assertEqual(
            overlay["reviewed_document_sha256"],
            "aad5b2c3e51ffc289edb5018254f364896b01d14bee8fa3be7e362e756e130c7",
        )
        self.assertIs(overlay["reviewed_enrichment_read_only"], True)

    def test_wrong_pdf_hash_fails_closed(self) -> None:
        self.assertEqual(self._overlay(evidence_sha256="0" * 64), {})

    def test_wrong_attachment_or_source_fails_closed(self) -> None:
        self.assertEqual(
            self._overlay(attachment_url="https://www.mofa.gov.mm/wp-content/uploads/2026/09/other.pdf"),
            {},
        )
        self.assertEqual(self._overlay(source_id="S39"), {})


if __name__ == "__main__":
    unittest.main()
