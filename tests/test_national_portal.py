from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.assurance import _coverage_from_aggregator_surface, list_missed_signals, run_assurance
from signalforge.config import Registry
from signalforge.db import connect, migrate
from signalforge.national_portal import parse_current_high_value_tender_leads


MPT_URL = (
    "https://myanmar.gov.mm/documents/20143/0/"
    "Newspaper+advertiement+10082026.pdf/aa3cebae-2f59-5c3c-e840-640c99f0cb92"
)


def _listing() -> bytes:
    return f"""
    <html><body>
      <div class="smallcardstyle">
        <div><a href="{MPT_URL}?t=1789445374206" target="_blank">
          <h2 class="fontsize18">ဒီဂျစ်တယ်ဖွံ့ဖြိုးတိုးတက်ရေးနှင့် ဆက်သွယ်ရေးဝန်ကြီးဌာန မြန်မာ့ဆက်သွယ်ရေးလုပ်ငန်း အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း</h2>
        </a>
        <p><span class="graycolor col-sm-3">Agency:</span><span class="blueColor1">Ministry of Digital Development and Communications</span></p>
        <p><span class="graycolor col-sm-3">Closing Date::</span><span class="blueColor1">September 29, 2026</span></p></div>
      </div>
      <div class="smallcardstyle">
        <div><a href="https://industrymsme.gov.mm/announcements/1042"><h2 class="fontsize18">1/7 PC colored yarn 49,460 lb tender</h2></a>
        <p><span class="graycolor col-sm-3">Agency:</span><span class="blueColor1">Ministry of Industry and MSME Development</span></p>
        <p><span class="graycolor col-sm-3">Closing Date::</span><span class="blueColor1">September 18, 2026</span></p></div>
      </div>
      <div class="smallcardstyle">
        <div><a href="#"><h2 class="fontsize18">Generic MOEP tender</h2></a>
        <p><span class="graycolor col-sm-3">Agency:</span><span class="blueColor1">Ministry Of Electricity And Energy</span></p>
        <p><span class="graycolor col-sm-3">Closing Date::</span><span class="blueColor1">September 30, 2026</span></p></div>
      </div>
    </body></html>
    """.encode()


class NationalPortalTests(unittest.TestCase):
    def test_parser_selects_current_high_value_gap_without_promoting_aggregator_truth(self) -> None:
        leads = parse_current_high_value_tender_leads(
            _listing(),
            base_url="https://myanmar.gov.mm/tenders",
            today=date(2026, 9, 16),
        )
        self.assertEqual(len(leads), 1)
        lead = leads[0]
        self.assertEqual(lead["lead_id"], "national-portal:aa3cebae-2f59-5c3c-e840-640c99f0cb92")
        self.assertEqual(lead["closing_date_hint"], "2026-09-29")
        self.assertEqual(lead["target_source_hint"], "S13")
        self.assertEqual(lead["evidence_kind"], "NATIONAL_PORTAL_HOSTED_DOCUMENT")
        self.assertEqual(lead["url"], MPT_URL)
        self.assertFalse(lead["canonical_truth"])
        self.assertTrue(lead["aggregator_only"])

    def test_assurance_surface_marks_reviewed_mpt_gap_but_exact_canonical_url_closes_it(self) -> None:
        registry = Registry.load(Path(__file__).resolve().parents[1])
        policy = registry.raw["assurance_surfaces"]["S01"]
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.assurance.fetch_bytes", return_value=_listing()):
                with connect(database) as conn:
                    gap = _coverage_from_aggregator_surface(
                        conn,
                        source_id="S01",
                        policy=policy,
                        network=True,
                        now=datetime(2026, 9, 16, 5, 0, tzinfo=UTC),
                    )
            self.assertEqual(gap["status"], "GAP")
            self.assertEqual(gap["official"], 1)
            self.assertEqual(gap["covered"], 0)
            self.assertEqual(gap["missing"], [MPT_URL])
            confirmed = gap["details"]["confirmed_gaps"]
            self.assertEqual(confirmed[0]["reviewed_gap"]["source_id"], "S13")
            self.assertEqual(gap["details"]["closing_date_semantics"], "HINT_ONLY_NOT_CANONICAL")

            with connect(database) as conn, conn:
                conn.execute(
                    """
                    INSERT INTO canonical_items(
                        canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,
                        deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "mpt:future-equivalent", "S13", "TENDER", "Pobbathiri repair", "REF", "Pobbathiri repair",
                        "2026-09-20", "2026-09-29", "Nay Pyi Taw", MPT_URL, "h", "e", "{}",
                        "2026-09-20T00:00:00Z", "2026-09-20T00:00:00Z",
                    ),
                )
            with patch("signalforge.assurance.fetch_bytes", return_value=_listing()):
                with connect(database) as conn:
                    covered = _coverage_from_aggregator_surface(
                        conn,
                        source_id="S01",
                        policy=policy,
                        network=True,
                        now=datetime(2026, 9, 20, 5, 0, tzinfo=UTC),
                    )
            self.assertEqual(covered["status"], "PASS")
            self.assertEqual(covered["covered"], 1)
            self.assertEqual(covered["missing"], [])


    def test_s01_is_assurance_only_and_not_an_active_source(self) -> None:
        registry = Registry.load(Path(__file__).resolve().parents[1])
        self.assertNotIn("S01", dict(registry.enabled_sources()))
        self.assertNotIn("S01", registry.raw["sources"])
        surface = registry.raw["assurance_surfaces"]["S01"]
        self.assertTrue(surface["enabled"])
        self.assertEqual(surface["role"], "DISCOVERY_AGGREGATOR_ONLY")
        self.assertFalse(surface["canonical_truth"])
        self.assertTrue(surface["closing_date_is_hint_only"])

    def test_run_assurance_opens_red_miss_for_reviewed_s01_gap(self) -> None:
        registry = Registry.load(Path(__file__).resolve().parents[1])
        reviewed_gap = {
            "source_id": "S01",
            "method": "official-aggregator-discovery-lead-resolution",
            "status": "GAP",
            "official": 1,
            "covered": 0,
            "missing": [MPT_URL],
            "details": {
                "confirmed_gaps": [{
                    "lead_id": "national-portal:aa3cebae-2f59-5c3c-e840-640c99f0cb92",
                    "title": "Portal lead",
                    "url": MPT_URL,
                    "closing_date_hint": "2026-09-29",
                    "target_source_hint": "S13",
                    "reviewed_gap": {
                        "gap_id": "S13:aa3cebae-2f59-5c3c-e840-640c99f0cb92",
                        "source_id": "S13",
                        "title": "Pobbathiri Exchange Office earthquake damage repair tender",
                        "deadline": "2026-09-29",
                        "url": MPT_URL,
                    },
                }]
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.assurance._coverage_from_aggregator_surface", return_value=reviewed_gap):
                result = run_assurance(
                    database=database, registry=registry, network=False, noise_sample_size=0,
                    now=datetime(2026, 9, 16, 5, 0, tzinfo=UTC),
                )
            misses = list_missed_signals(database=database)["misses"]
        self.assertEqual(result["supplemental_coverage"][0]["status"], "GAP")
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(misses), 1)
        self.assertEqual(misses[0]["source_id"], "S13")
        self.assertEqual(misses[0]["detected_by"], "AGGREGATOR_COVERAGE_AUDIT")
        self.assertEqual(misses[0]["severity"], "RED")



if __name__ == "__main__":
    unittest.main()
