from __future__ import annotations

import unittest

from signalforge.ptd_policy import PtdPolicyParseError, parse_policy_records


class PtdPolicyTests(unittest.TestCase):
    def test_selects_strategic_telecom_policy_rows(self) -> None:
        html = b'''<html><body><table id="ContentPlaceHolder1_gvnews">
        <tr><th>title</th><th>file</th><th>date</th></tr>
        <tr><td><h6>ASEAN Digital Master Plan 2026-2030 (ADM 2030)</h6></td>
          <td><a href="../Uploads/LawFP/Attach/22026/ADM-2030.pdf">read</a></td><td>January 16, 2026</td></tr>
        <tr><td><h6>Spectrum Roadmap (2022-2026)</h6></td>
          <td><a href="../Uploads/LawFP/Attach/92023/Spectrum%20Roadmap%20(2022-2026).pdf">read</a></td><td>October 31, 2022</td></tr>
        <tr><td><h6>Unrelated Administrative Policy</h6></td>
          <td><a href="../Uploads/LawFP/Attach/12020/admin.pdf">read</a></td><td>January 1, 2020</td></tr>
        </table></body></html>'''
        items = parse_policy_records(html)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].publication_date, "2026-01-16")
        self.assertEqual(items[0].payload()["telecom_signal_kind"], "DIGITAL_CONNECTIVITY_POLICY")
        self.assertEqual(items[1].publication_date, "2022-10-31")
        self.assertEqual(items[1].payload()["telecom_signal_kind"], "SPECTRUM_5G_POLICY")
        self.assertEqual(items[1].item_kind, "REGULATORY_NOTICE")
        self.assertEqual(items[1].payload()["business_stage"], "STRATEGIC_INTELLIGENCE")
        self.assertTrue(items[1].url.startswith("https://www.ptd.gov.mm/Uploads/LawFP/Attach/"))

    def test_missing_policy_table_fails_closed(self) -> None:
        with self.assertRaises(PtdPolicyParseError):
            parse_policy_records(b"<html><body>changed</body></html>")


if __name__ == "__main__":
    unittest.main()
