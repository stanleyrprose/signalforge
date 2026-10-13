"""Human-reviewed S01 tender facts: regression guardrails (no live network)."""
import json
import unittest
from pathlib import Path

_FIXTURE = Path(__file__).parent / "fixtures" / "s01_human_review_20261013.json"


class S01HumanReviewRegression(unittest.TestCase):
    def setUp(self):
        self.samples = {s["review_id"]: s for s in json.loads(_FIXTURE.read_text(encoding="utf-8"))["samples"]}

    def test_fuel_quantities_and_document_fees(self):
        fuel = self.samples["S01-20261013-01"]
        self.assertEqual([x["quantity"] for x in fuel["items"]], [85000, 20000, 45000])
        self.assertEqual(sum(x["quantity"] for x in fuel["items"]), fuel["total_quantity_gallons"])
        self.assertEqual([x["document_fee_mmk"] for x in fuel["items"]], [15000, 10000, 15000])
        self.assertTrue(fuel["formal_procurement_tender"])

    def test_document_sale_end_is_not_bid_deadline(self):
        fuel = self.samples["S01-20261013-01"]
        self.assertEqual(fuel["document_sale_end"], "2026-10-16")
        self.assertIsNone(fuel["bid_submission_deadline"])
        self.assertEqual(fuel["bid_opening_date"], "2026-10-29")

    def test_asset_lease_not_procurement(self):
        lease = self.samples["S01-20261013-02"]
        self.assertFalse(lease["formal_procurement_tender"])
        self.assertEqual(lease["classification"], "GOVERNMENT_ASSET_LEASING")
        self.assertEqual(lease["bid_submission_deadline"], "2026-11-02T12:00:00+06:30")
        self.assertEqual(lease["bid_opening_at"], "2026-11-09T14:00:00+06:30")


if __name__ == "__main__":
    unittest.main()
