from __future__ import annotations

import hashlib
import unittest
from unittest.mock import patch

from signalforge.auditor import _reviewed_mte_evidence_findings
from signalforge.mte_reviewed_enrichment import apply_reviewed_mte_overlay, reviewed_mte_overlay


class MteReviewedEnrichmentTests(unittest.TestCase):
    def test_exact_reviewed_identity_returns_bounded_overlay(self) -> None:
        result = reviewed_mte_overlay(
            canonical_key="mte:1605",
            source_id="S32",
            item_kind="AUCTION_NOTICE",
            reference_no="MTE-LOCAL-6/2026-2027",
            action_date="2026-09-15",
        )
        self.assertEqual(result["action_time"], "08:30")
        self.assertEqual(result["quantity_or_lot_summary"], "Approximately 6,243 tons of teak/hardwood logs and sawn timber")
        self.assertEqual(result["quantity_or_lot_evidence"], "REVIEWED_OFFICIAL_IMAGE_EXPLICIT_APPROX_TONNAGE")
        self.assertEqual(result["quantity_or_lot_confidence"], "HIGH")
        self.assertEqual(result["reviewed_enrichment_version"], 1)
        self.assertTrue(result["reviewed_enrichment_read_only"])
        self.assertEqual(
            result["reviewed_image_sha256"],
            "6a6c2452cf8ae18bf4985c3bd77f63bbd77ec710ad5b37ae3db51409854348e1",
        )

    def test_identity_mismatch_fails_closed(self) -> None:
        base = dict(
            canonical_key="mte:1605",
            source_id="S32",
            item_kind="AUCTION_NOTICE",
            reference_no="MTE-LOCAL-6/2026-2027",
            action_date="2026-09-15",
            url="https://mte.gov.mm/index.php/en/annoucements/17-tenders/local-milling-marketing-dept-tender/1605-392026",
        )
        for field, value in (
            ("source_id", "S31"),
            ("item_kind", "TENDER"),
            ("reference_no", "MTE-LOCAL-5/2026-2027"),
            ("action_date", "2026-09-16"),
            ("canonical_key", "mte:1604"),
            ("url", "https://mte.gov.mm/wrong"),
        ):
            args = dict(base)
            args[field] = value
            self.assertEqual(reviewed_mte_overlay(**args), {})

    def test_overlay_only_fills_gaps_and_never_overwrites_canonical_facts(self) -> None:
        payload = {
            "action_date": "2026-09-15",
            "action_time": "10:15",
            "location": "Canonical issuer location",
            "reference_no": "MTE-LOCAL-6/2026-2027",
        }
        result = apply_reviewed_mte_overlay(
            payload,
            canonical_key="mte:1605",
            source_id="S32",
            item_kind="AUCTION_NOTICE",
            reference_no="MTE-LOCAL-6/2026-2027",
        )
        self.assertEqual(result["action_time"], "10:15")
        self.assertEqual(result["location"], "Canonical issuer location")
        self.assertIn("Earnest Money", result["next_action_summary"])
        self.assertTrue(result["reviewed_enrichment_read_only"])

    def test_auditor_revalidates_reviewed_image_sha_and_detects_change(self) -> None:
        payload = b"official-image-bytes"
        sha = hashlib.sha256(payload).hexdigest()
        records = {
            "mte:test": {
                "image_url": "https://mte.gov.mm/images/test.jpg",
                "image_sha256": sha,
            }
        }
        with patch("signalforge.auditor.reviewed_mte_records", return_value=records):
            findings, summary = _reviewed_mte_evidence_findings(lambda *_a, **_k: payload)
            self.assertEqual(findings, [])
            self.assertEqual(summary["status"], "PASS")
            self.assertEqual(summary["sha_matches"], 1)

            findings, summary = _reviewed_mte_evidence_findings(lambda *_a, **_k: b"changed")
            self.assertEqual(summary["status"], "CHECK_FAILED")
            self.assertEqual(findings[0]["code"], "MTE_REVIEWED_IMAGE_SHA_MISMATCH")
            self.assertEqual(findings[0]["severity"], "RED")


if __name__ == "__main__":
    unittest.main()
