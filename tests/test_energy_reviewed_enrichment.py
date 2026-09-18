from __future__ import annotations

import unittest

from signalforge.energy_reviewed_enrichment import reviewed_energy_overlay


class EnergyReviewedEnrichmentTests(unittest.TestCase):
    def _overlay(self, **overrides: object) -> dict[str, object]:
        args: dict[str, object] = {
            "canonical_key": "energy:235",
            "source_id": "S39",
            "item_kind": "TENDER",
            "reference_no": "ENERGY-27-2026-2027",
            "publication_date": "2026-09-04",
            "article_url": "https://energy.gov.mm/tenders/235",
            "attachment_urls": [
                "https://energy.gov.mm/storage/tenders/ZN0mM90uR0Ik1KJNCSY8GbcyK1YAgs8BMmbMxUvG.pdf"
            ],
            "evidence_sha256": "4d2ef1694aa6a7221b1a2d46799eadba7f8edb9ef46a2045c573e07c1760c94b",
        }
        args.update(overrides)
        return reviewed_energy_overlay(**args)  # type: ignore[arg-type]

    def test_exact_source_native_pdf_identity_returns_reviewed_participation_fields(self) -> None:
        overlay = self._overlay()
        self.assertEqual(
            overlay["location"],
            "Ministry of Energy, Office No.6, Yadana Hall, Nay Pyi Taw",
        )
        self.assertIn("9/18 13:00", str(overlay["next_action_summary"]))
        self.assertEqual(overlay["reviewed_enrichment_status"], "REVIEWED_SOURCE_NATIVE_OFFICIAL_PDF")
        self.assertEqual(
            overlay["reviewed_document_sha256"],
            "4d2ef1694aa6a7221b1a2d46799eadba7f8edb9ef46a2045c573e07c1760c94b",
        )
        self.assertIs(overlay["reviewed_enrichment_read_only"], True)

    def test_wrong_pdf_hash_fails_closed(self) -> None:
        self.assertEqual(self._overlay(evidence_sha256="0" * 64), {})

    def test_wrong_attachment_or_source_fails_closed(self) -> None:
        self.assertEqual(
            self._overlay(attachment_urls=["https://energy.gov.mm/storage/tenders/other.pdf"]),
            {},
        )
        self.assertEqual(self._overlay(source_id="S20"), {})


if __name__ == "__main__":
    unittest.main()
