from __future__ import annotations

import json
import unittest
from pathlib import Path

from signalforge.moba import parse_tender_detail, parse_tender_listing
from signalforge.provider_invocation import ProviderInvocationError, build_provider_request

REPO = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://moba.gov.mm/my/tender"
DETAIL_URL = "https://moba.gov.mm/my/tender/3475"


class MobaTests(unittest.TestCase):
    def test_listing_selects_opportunities_and_excludes_outcomes(self) -> None:
        entries = parse_tender_listing((ROOT / "moba_listing.html").read_bytes())
        by_url = {entry.url: entry for entry in entries}
        self.assertIn(DETAIL_URL, by_url)
        self.assertEqual(by_url[DETAIL_URL].lastmod, "2026-09-08T00:00:00+06:30")
        self.assertIn("https://moba.gov.mm/my/tender/3395", by_url)
        self.assertNotIn("https://moba.gov.mm/my/tender/3400", by_url)
        self.assertNotIn("https://moba.gov.mm/my/tender/3401", by_url)

    def test_detail_uses_native_node_identity_and_explicit_html_dates(self) -> None:
        tender = parse_tender_detail((ROOT / "moba_detail_3475.html").read_bytes(), DETAIL_URL)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "moba:3475")
        self.assertEqual(tender.reference_no, "MOBA-TENDER-3475")
        self.assertIsNone(tender.publication_date)
        self.assertEqual(tender.sale_start_date, "2026-08-24")
        self.assertEqual(tender.deadline, "2026-09-08")
        self.assertIn("ရန်ကုန်တိုင်းဒေသကြီး", tender.title)
        self.assertEqual(len(tender.attachment_urls), 2)
        self.assertTrue(all(url.startswith("https://moba.gov.mm/sites/default/files/") for url in tender.attachment_urls))
        payload = tender.payload()
        self.assertEqual(payload["deadline_evidence"], "EXPLICIT_HTML_TENDER_FORM_CLOSE_DATE")
        self.assertEqual(payload["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")

    def test_detail_fails_closed_for_wrong_host_or_query(self) -> None:
        payload = (ROOT / "moba_detail_3475.html").read_bytes()
        self.assertIsNone(parse_tender_detail(payload, "https://example.com/my/tender/3475"))
        self.assertIsNone(parse_tender_detail(payload, f"{DETAIL_URL}?page=1"))

    def test_production_provider_contract_is_c0_only_and_url_bounded(self) -> None:
        contract = json.loads((REPO / "registry" / "Provider-Invocation-Contract-v1.json").read_text())
        ids = {
            "signalforge_job_id": "11111111-1111-4111-8111-111111111111",
            "acquisition_request_id": "22222222-2222-4222-8222-222222222222",
            "acquisition_attempt_id": "33333333-3333-4333-8333-333333333333",
        }
        listing = build_provider_request(
            contract=contract,
            source_id="S27",
            source_policy_version=1,
            capability="C0_FETCH",
            target_role="LISTING",
            requested_url=LIST_URL,
            max_bytes=1_000_000,
            max_run_seconds=90,
            **ids,
        )
        self.assertEqual(listing["mcp_tool"], "browser_fetch")
        detail = build_provider_request(
            contract=contract,
            source_id="S27",
            source_policy_version=1,
            capability="C0_FETCH",
            target_role="DETAIL",
            requested_url=DETAIL_URL,
            max_bytes=1_000_000,
            max_run_seconds=90,
            **ids,
        )
        self.assertEqual(detail["final_url_policy"]["https_host"], "moba.gov.mm")
        with self.assertRaises(ProviderInvocationError):
            build_provider_request(
                contract=contract,
                source_id="S27",
                source_policy_version=1,
                capability="C1_RENDER",
                target_role="LISTING",
                requested_url=LIST_URL,
                max_bytes=1_000_000,
                max_run_seconds=90,
                **ids,
            )
        with self.assertRaises(ProviderInvocationError):
            build_provider_request(
                contract=contract,
                source_id="S27",
                source_policy_version=1,
                capability="C0_FETCH",
                target_role="DETAIL",
                requested_url=f"{DETAIL_URL}?page=1",
                max_bytes=1_000_000,
                max_run_seconds=90,
                **ids,
            )


if __name__ == "__main__":
    unittest.main()
