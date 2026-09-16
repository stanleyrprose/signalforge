from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.assurance import (
    _aggregator_canonical_equivalent,
    _coverage_from_aggregator_surface,
    list_missed_signals,
    run_assurance,
)
from signalforge.config import Registry
from signalforge.db import connect, migrate
from signalforge.national_portal import national_portal_page_url, parse_current_high_value_tender_leads


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


def _card(*, title: str, agency: str, closing: str, href: str) -> bytes:
    return f"""
    <html><body><div class="smallcardstyle"><div><a href="{href}"><h2 class="fontsize18">{title}</h2></a>
    <p><span class="graycolor col-sm-3">Agency:</span><span class="blueColor1">{agency}</span></p>
    <p><span class="graycolor col-sm-3">Closing Date::</span><span class="blueColor1">{closing}</span></p></div></div></body></html>
    """.encode()


S38_TITLE = "အမှတ်(၁)သံမဏိစက်ရုံ(မြင်းခြံ)အတွက် စက်ဆီ၊ချောဆီ (၉)မျိုး၊ Electrical စက်အရန် ပစ္စည်း (၂၃)မျိုးနှင့် Mechanical စက်အရန်ပစ္စည်း (၄၃)မျိုး ဝယ်ယူရန် အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"
IWT_TITLE = "ပြည်တွင်းရေကြောင်းပို့ဆောင်ရေးဌာနမှ အိတ်ဖွင့်တင်ဒါအပြိုင်ဈေးနှုန်းလွှာခေါ်ယူခြင်း"
IWT_PORTAL_URL = "https://myanmar.gov.mm/documents/20143/0/IWT_1+Costal+Vessel+Tender+25-8-2026.pdf/60c6bd08-57aa-511a-d47d-0da361fb323b"


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

    def test_assurance_surface_accepts_verified_external_mpt_coverage_and_canonical_later_supersedes_it(self) -> None:
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
            self.assertEqual(gap["status"], "PASS")
            self.assertEqual(gap["official"], 1)
            self.assertEqual(gap["covered"], 1)
            self.assertEqual(gap["missing"], [])
            verified = gap["details"]["verified_external_leads"]
            self.assertEqual(verified[0]["coverage_resolution"], "VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY")
            self.assertEqual(verified[0]["verified_external"]["source_id"], "S13")
            self.assertTrue(gap["details"]["issuer_page_coverage_debt_retained"])
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
            self.assertEqual(covered["details"]["covered_leads"][0]["coverage_resolution"], "CANONICAL")
            self.assertEqual(covered["details"]["verified_external_leads"], [])


    def test_mission_radar_rejects_fuel_and_pharma_logistics_false_positives(self) -> None:
        fuel = _card(
            title="မန္တလေးမြို့တော် စက်ရုံနှင့်မော်တော်ယာဉ်ဌာန ဒီဇယ်ဆီ နှင့် Octane-92 ဝယ်ယူရန် အိတ်ဖွင့်တင်ဒါ",
            agency="Mandalay City Development Committee",
            closing="September 18, 2026",
            href="https://myanmar.gov.mm/documents/fuel.jpg/00000000-0000-0000-0000-000000000001",
        )
        pharma = _card(
            title="မြန်မာ့ဆေးဝါးလုပ်ငန်း စက်နှင့်စက်အရန်ပစ္စည်းများ သယ်ယူပို့ဆောင်ရန် ကုန်သေတ္တာတင်ယာဉ် ငှားရမ်းခ အိတ်ဖွင့်တင်ဒါ",
            agency="Ministry of Industry and MSME Development",
            closing="October 06, 2026",
            href="https://industrymsme.gov.mm/announcements/1038",
        )
        for payload in (fuel, pharma):
            self.assertEqual(
                parse_current_high_value_tender_leads(
                    payload, base_url="https://myanmar.gov.mm/tenders", today=date(2026, 9, 16)
                ),
                [],
            )

    def test_cross_surface_equivalence_uses_strict_identity_not_portal_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                conn.execute(
                    """INSERT INTO canonical_items(canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        "industry:1039", "S38", "TENDER", S38_TITLE, "INDUSTRY-ANN-1039", S38_TITLE,
                        "2026-09-07", "2026-09-25", None, "https://www.industrymsme.gov.mm/announcements/1039",
                        "h1", "e1", '{"title": ' + repr(S38_TITLE).replace("'", '"') + '}',
                        "2026-09-07T00:00:00Z", "2026-09-07T00:00:00Z",
                    ),
                )
                conn.execute(
                    """INSERT INTO canonical_items(canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        "iwt:1038:2026-08-25", "S22", "TENDER", "long project text", "IWT-NODE-1038", "long project text",
                        "2026-08-25", "2026-11-03", None, "https://iwt.gov.mm/my/node/1038",
                        "h2", "e2", '{"title": ' + repr(IWT_TITLE).replace("'", '"') + ', "attachment_name": "IWT_1 Costal Vessel Tender 25-8-2026.pdf"}',
                        "2026-08-25T00:00:00Z", "2026-08-25T00:00:00Z",
                    ),
                )
                s38 = _aggregator_canonical_equivalent(conn, {
                    "target_source_hint": "S38",
                    "title": S38_TITLE,
                    "url": "https://industrymsme.gov.mm/announcements/1039",
                    "closing_date_hint": "2099-01-01",
                })
                iwt = _aggregator_canonical_equivalent(conn, {
                    "target_source_hint": "S22",
                    "title": IWT_TITLE,
                    "url": IWT_PORTAL_URL,
                    "closing_date_hint": "2099-01-01",
                })
            self.assertEqual(s38["proof"], "EXACT_OFFICIAL_PATH_WWW_HOST_ALIAS")
            self.assertEqual(s38["canonical_key"], "industry:1039")
            self.assertEqual(iwt["proof"], "EXACT_ISSUER_TITLE_AND_ATTACHMENT_NAME")
            self.assertEqual(iwt["canonical_key"], "iwt:1038:2026-08-25")

    def test_bounded_mission_radar_covers_verified_and_cross_surface_equivalents(self) -> None:
        registry = Registry.load(Path(__file__).resolve().parents[1])
        policy = registry.raw["assurance_surfaces"]["S01"]
        base = "https://myanmar.gov.mm/tenders"
        pages = {
            national_portal_page_url(base, 1): _listing(),
            national_portal_page_url(base, 2): _card(
                title=S38_TITLE, agency="Ministry of Industry and MSME Development", closing="September 25, 2026",
                href="https://industrymsme.gov.mm/announcements/1039",
            ),
            national_portal_page_url(base, 3): _card(
                title=IWT_TITLE, agency="Ministry of Transport", closing="November 03, 2026", href=IWT_PORTAL_URL,
            ),
        }
        for page in (4, 5, 6):
            pages[national_portal_page_url(base, page)] = _card(
                title=f"Colored yarn ordinary commodity page {page}",
                agency="Ministry of Industry and MSME Development",
                closing="October 20, 2026",
                href=f"https://industrymsme.gov.mm/announcements/noise-{page}",
            )
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                conn.execute(
                    """INSERT INTO canonical_items(canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    ("industry:1039", "S38", "TENDER", S38_TITLE, "INDUSTRY-ANN-1039", S38_TITLE, "2026-09-07", "2026-09-25", None, "https://www.industrymsme.gov.mm/announcements/1039", "h1", "e1", '{}', "2026-09-07T00:00:00Z", "2026-09-07T00:00:00Z"),
                )
                conn.execute(
                    """INSERT INTO canonical_items(canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    ("iwt:1038:2026-08-25", "S22", "TENDER", "long project text", "IWT-NODE-1038", "long project text", "2026-08-25", "2026-11-03", None, "https://iwt.gov.mm/my/node/1038", "h2", "e2", '{"title": ' + repr(IWT_TITLE).replace("'", '"') + ', "attachment_name": "IWT_1 Costal Vessel Tender 25-8-2026.pdf"}', "2026-08-25T00:00:00Z", "2026-08-25T00:00:00Z"),
                )
            with patch("signalforge.assurance.fetch_bytes", side_effect=lambda url, **_: pages[url]):
                with connect(database) as conn:
                    result = _coverage_from_aggregator_surface(
                        conn, source_id="S01", policy=policy, network=True,
                        now=datetime(2026, 9, 16, 5, 0, tzinfo=UTC),
                    )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["official"], 3)
        self.assertEqual(result["covered"], 3)
        self.assertEqual(result["missing"], [])
        self.assertEqual(len(result["details"]["verified_external_leads"]), 1)
        self.assertEqual(len(result["details"]["canonical_equivalent_leads"]), 2)
        self.assertEqual(result["details"]["unresolved_leads"], [])
        self.assertEqual([row["page"] for row in result["details"]["pages_scanned"]], [1, 2, 3, 4, 5, 6])

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
            verified_coverage = {
                "source_id": "S01",
                "method": "official-aggregator-discovery-lead-resolution",
                "status": "PASS",
                "official": 1,
                "covered": 1,
                "missing": [],
                "details": {
                    "verified_external_leads": [{"url": MPT_URL}],
                    "confirmed_gaps": [],
                    "unresolved_leads": [],
                },
            }
            with patch("signalforge.assurance._coverage_from_aggregator_surface", return_value=verified_coverage):
                resolved_result = run_assurance(
                    database=database, registry=registry, network=False, noise_sample_size=0,
                    now=datetime(2026, 9, 16, 6, 0, tzinfo=UTC),
                )
            all_misses = list_missed_signals(database=database, status=None)["misses"]
        self.assertEqual(result["supplemental_coverage"][0]["status"], "GAP")
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(misses), 1)
        self.assertEqual(misses[0]["source_id"], "S13")
        self.assertEqual(misses[0]["detected_by"], "AGGREGATOR_COVERAGE_AUDIT")
        self.assertEqual(misses[0]["severity"], "RED")
        self.assertEqual(resolved_result["supplemental_coverage"][0]["status"], "PASS")
        self.assertEqual(resolved_result["verified_resolved_aggregator_misses"], 1)
        self.assertEqual(all_misses[0]["status"], "RESOLVED")
        self.assertEqual(all_misses[0]["resolved_by"], "ASSURANCE_VERIFIED_EXTERNAL")



if __name__ == "__main__":
    unittest.main()
