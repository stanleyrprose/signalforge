"""Explicit row-local railway tender quantities; do not infer tender references as amounts."""
import unittest

from signalforge.railways import _row_quantity


class RailwayQuantityTests(unittest.TestCase):
    def test_explicit_english_units(self):
        self.assertEqual(_row_quantity("Supply 12 sets of network switches"), "12 sets")

    def test_myanmar_digits(self):
        self.assertEqual(_row_quantity("စက်ပစ္စည်း ၁၅ စီး ဝယ်ယူရန်"), "15 စီး")

    def test_tender_reference_is_not_quantity(self):
        self.assertIsNone(_row_quantity("Tender No. 12/2026 bridge maintenance"))

    def test_no_quantity_without_unit(self):
        self.assertIsNone(_row_quantity("Rail bridge renovation at mile 15"))

    def test_row_local_multiple_quantities(self):
        self.assertEqual(_row_quantity("3 units and 2 sets"), "3 units; 2 sets")


if __name__ == "__main__":
    unittest.main()
