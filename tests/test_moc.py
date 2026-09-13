from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from signalforge.config import ConfigError, Registry
from signalforge.moc import MOC_TENDER_URL, MocParseError, parse_tender_records
from signalforge.source_adapters import ADAPTERS

ROOT = Path(__file__).resolve().parents[1]


def _card(*, record_id: str, title: str, region: str, deadline: str, pdf_name: str) -> str:
    return f'''<div class="col-sm-6 col-md-4 col-lg-3">
      <div class="card shadow mt-3">
        <a class="link-canvas-{record_id} custom_canvas position-relative"
           href="/storage/TinDar/{pdf_name}" target="_blank">
          <span class="badge bg-warning mt-1 mb-2 text-dark position-absolute">{region}</span>
          <div class="pdf-canvas"><i class="fa fa-spinner"></i></div>
        </a>
        <div class="card-body">
          <h5 class="card-title">{title}</h5>
          <div>End Date - <span class="badge bg-success mt-1 mb-2 text-light">{deadline}</span></div>
          <a class="btn btn-outline-primary w-100 download-btn"
             href="https://construction.gov.mm/letter-download/{record_id}">Download</a>
        </div>
      </div>
    </div>'''


class MinistryOfConstructionTests(unittest.TestCase):
    def test_live_shape_parses_stable_uuid_region_end_date_and_pdf_metadata(self) -> None:
        html = (
            "<html><body>"
            + _card(
                record_id="18be5b60-accb-11f1-b41f-3517e3a380a0",
                title="လမ်းဦးစီးဌာန၊ အမြန်လမ်းမကြီးထိန်းသိမ်းပြုပြင်ရေးနှင့် ကြီးကြပ်ရေးအဖွဲ့မှ အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
                region="နေပြည်တော်တိုင်းဒေသကြီး",
                deadline="2026-09-23",
                pdf_name="tindar_1789012371_Main Tinder(2026-2027)အပေါ်စာ (1)-1.pdf",
            )
            + _card(
                record_id="0f39a580-a813-11f1-97b9-bbf17f490ccf",
                title="တံတားဦးစီးဌာန၊ တည်ဆောက်ရေးအဖွဲ့(၄)၊ တံတားအထူးအဖွဲ့(၁၆)မှ အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
                region="ဧရာဝတီတိုင်းဒေသကြီး",
                deadline="2026-09-16",
                pdf_name="tindar_1788493523_bridge.pdf",
            )
            + "</body></html>"
        ).encode("utf-8")

        items = parse_tender_records(html)
        self.assertEqual(len(items), 2)
        by_key = {item.canonical_key: item for item in items}

        highway = by_key["moc:18be5b60-accb-11f1-b41f-3517e3a380a0"]
        self.assertEqual(highway.deadline, "2026-09-23")
        self.assertIsNone(highway.deadline_time)
        self.assertEqual(highway.location, "နေပြည်တော်တိုင်းဒေသကြီး")
        self.assertEqual(
            highway.url,
            "https://construction.gov.mm/letter-download/18be5b60-accb-11f1-b41f-3517e3a380a0",
        )
        self.assertTrue(highway.attachment_url.startswith("https://construction.gov.mm/storage/TinDar/"))
        payload = highway.payload()
        self.assertEqual(payload["item_kind"], "TENDER")
        self.assertEqual(payload["business_stage"], "OPPORTUNITY")
        self.assertEqual(payload["deadline_kind"], "TENDER_END_DATE")
        self.assertEqual(payload["deadline_evidence"], "EXPLICIT_OFFICIAL_LISTING_END_DATE")
        self.assertEqual(payload["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")

        bridge = by_key["moc:0f39a580-a813-11f1-97b9-bbf17f490ccf"]
        self.assertEqual(bridge.deadline, "2026-09-16")
        self.assertEqual(bridge.location, "ဧရာဝတီတိုင်းဒေသကြီး")

    def test_duplicate_uuid_is_deduplicated_and_result_stage_is_excluded(self) -> None:
        record_id = "18be5b60-accb-11f1-b41f-3517e3a380a0"
        tender = _card(
            record_id=record_id,
            title="အမြန်လမ်း အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
            region="နေပြည်တော်တိုင်းဒေသကြီး",
            deadline="2026-09-23",
            pdf_name="tender.pdf",
        )
        result = _card(
            record_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            title="Tender Result / Winner",
            region="Yangon",
            deadline="2026-09-30",
            pdf_name="result.pdf",
        )
        items = parse_tender_records(("<html><body>" + tender + tender + result + "</body></html>").encode())
        self.assertEqual([item.canonical_key for item in items], [f"moc:{record_id}"])

    def test_wrong_listing_url_and_invalid_cards_fail_closed(self) -> None:
        with self.assertRaises(MocParseError):
            parse_tender_records(b"<html></html>", "https://example.com/tenders")
        invalid = b'''<html><body><div class="card shadow mt-3">
          <h5 class="card-title">Open Tender</h5>
          <span class="badge bg-warning">Yangon</span>
          <span class="badge bg-success">2026-09-30</span>
          <a class="download-btn" href="https://evil.example/letter-download/18be5b60-accb-11f1-b41f-3517e3a380a0">Download</a>
        </div></body></html>'''
        with self.assertRaises(MocParseError):
            parse_tender_records(invalid)

    def test_s23_is_fully_defined_but_scheduler_inactive_until_tls_gate_passes(self) -> None:
        registry = Registry.load(ROOT)
        source = registry.raw["sources"]["S23"]
        self.assertFalse(source["enabled"])
        self.assertEqual(source["adapter"], "moc_tender")
        self.assertEqual(source["engine"], "direct_http")
        self.assertEqual(source["discovery_url"], MOC_TENDER_URL)
        self.assertTrue(source["listing_complete_business_records"])
        self.assertFalse(source["attachment_policy"]["fetch_in_primary_pipeline"])
        self.assertEqual(source["activation_gate"]["type"], "STRICT_TLS_HTTPS")
        self.assertEqual(source["activation_gate"]["status"], "BLOCKED_ISSUER_CERT_EXPIRED")
        self.assertTrue(source["activation_gate"]["enable_only_after_gate_pass"])
        self.assertTrue(source["actionable_baseline_signal_policy"]["enabled"])
        with self.assertRaisesRegex(ConfigError, "source is not active"):
            registry.source("S23")

        raw = json.loads(json.dumps(registry.raw))
        raw["sources"]["S23"]["enabled"] = True
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "registry").mkdir()
            (root / "registry" / "Source-Registry-v1.yaml").write_text(
                json.dumps(raw, ensure_ascii=False), encoding="utf-8"
            )
            with self.assertRaisesRegex(ConfigError, "source activation gate not passed: S23"):
                Registry.load(root)

        adapter = ADAPTERS["moc_tender"]
        self.assertEqual(adapter.discovery_parser_version, "moc-national-tender-board-v1")
        self.assertEqual(adapter.canonicalizer_version, "moc-issuer-uuid-v1")
        self.assertIsNotNone(adapter.parse_discovery_records)


if __name__ == "__main__":
    unittest.main()
