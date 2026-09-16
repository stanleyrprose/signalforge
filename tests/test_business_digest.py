from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.business_digest import business_digest, render_business_digest, telegram_digest
from signalforge.db import connect, migrate


class _Registry:
    def enabled_sources(self):
        return [("S13", {}), ("S41", {})]


def _briefing() -> dict[str, object]:
    return {
        "current_opportunities": 3,
        "current_counts": {"OPEN": 2, "UNKNOWN": 1, "EXPIRED": 0},
        "qualification_counts": {
            "priority_band": {"HIGH": 1, "MEDIUM": 1, "REVIEW": 1},
            "signal_quality_band": {"VERY_HIGH": 1, "HIGH": 1, "MEDIUM": 0, "REVIEW": 1, "LOW": 0},
            "signal_quality_score_avg": 68.0,
        },
        "attention_count": 2,
        "attention_action_counts": {"ACT_NOW": 0, "PRIORITIZE": 1, "REVIEW": 1},
        "attention": [
            {
                "canonical_key": "energy:235",
                "attention_action": "PRIORITIZE",
                "priority_band": "HIGH",
                "issuer": "Ministry of Energy, Myanmar",
                "primary_relevance": "ICT",
                "deadline": "2026-09-18",
                "deadline_time": "13:00",
                "deadline_status": "OPEN",
                "focus_reference_count": 4,
                "signal_quality_score": 81,
                "signal_quality_band": "HIGH",
            },
            {
                "canonical_key": "doms:1",
                "attention_action": "REVIEW",
                "priority_band": "REVIEW",
                "issuer": "Department of Medical Services",
                "primary_relevance": "MEDICAL",
                "deadline": None,
                "deadline_time": None,
                "deadline_status": "UNKNOWN",
                "focus_reference_count": None,
                "signal_quality_score": 40,
                "signal_quality_band": "REVIEW",
            },
        ],
        "watchlist": {"count": 1, "primary_relevance_counts": {"INDUSTRIAL": 1}, "canonical_keys": ["industry:1"]},
    }


def _audit() -> dict[str, object]:
    return {
        "status": "PASS",
        "finding_count": 0,
        "checks": {
            "source_health": {"checked_sources": 2, "non_green_sources": 0},
            "strategic_coverage": {
                "S13": {"status": "PASS", "missing": 0},
                "S41": {"status": "PASS", "canonical_keys": 15, "official_keys": 15, "missing": []},
            },
            "atom_surface_trigger": {"status": "NO_TRIGGER"},
        },
        "assurance": {"external_completeness": "NOT_PROVEN"},
    }


def _scorecard() -> dict[str, object]:
    return {
        "status": "PASS",
        "summary": {
            "active_sources": 2,
            "effective_signals": 1,
            "yield_states": {
                "ACTIONABLE_PROVEN": 1,
                "SIGNAL_PROVEN": 0,
                "BASELINE_ONLY": 1,
                "NOISE_ONLY_HISTORY": 0,
                "EMPTY": 0,
            },
        },
    }


class BusinessDigestTests(unittest.TestCase):
    def _db(self, root: str) -> Path:
        database = Path(root) / "signalforge.db"
        migrate(database)
        with connect(database) as conn, conn:
            conn.execute(
                """INSERT INTO scheduler_runs(app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,finished_at,status,changed,signals_created,items_parsed,tenders_parsed) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("run-1", "t", "SCHEDULE", "S13", "w", "2026-09-10T10:00:00Z", "2026-09-10T10:01:00Z", "SUCCESS", 2, 1, 5, 2),
            )
            conn.execute(
                """INSERT INTO scheduler_runs(app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,finished_at,status,changed,signals_created,items_parsed,tenders_parsed) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("run-2", "t", "SCHEDULE", "S41", "w", "2026-09-10T11:00:00Z", "2026-09-10T11:01:00Z", "SUCCESS", 0, 0, 3, 3),
            )
            conn.execute(
                "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                ("sig-1", "S13", "mpt:1", "NEW", "2026-09-10T10:02:00Z", json.dumps({"x": 1})),
            )
            conn.execute(
                "INSERT INTO delivery_receipts(delivery_key,channel,canonical_key,signal_id,attention_action,priority_band,payload_sha256,provider_message_id,sent_at) VALUES (?,?,?,?,?,?,?,?,?)",
                ("d-1", "telegram", "mpt:1", "sig-1", "PRIORITIZE", "HIGH", "sha", "101", "2026-09-10T10:03:00Z"),
            )
        return database

    def test_digest_reports_24h_pipeline_and_current_business_funnel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            result = business_digest(
                database=self._db(tmp),
                registry=_Registry(),  # type: ignore[arg-type]
                now=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            )
        self.assertEqual(result["digest_date"], "2026-09-10")
        self.assertEqual(result["sources"], {"monitored": 2, "green": 2, "non_green": 0, "polled_24h": 2, "changed_24h": 1})
        self.assertEqual(result["activity_24h"]["records_changed"], 2)
        self.assertEqual(result["activity_24h"]["signals"], 1)
        self.assertEqual(result["business"]["current_opportunities"], 3)
        self.assertEqual(result["business"]["watchlist_count"], 1)
        self.assertEqual(result["pipeline_totals"]["telegram_alerts"], 1)

    def test_render_makes_business_output_visible_not_only_system_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,10,12,0,tzinfo=UTC))  # type: ignore[arg-type]
        text = render_business_digest(digest)
        self.assertIn("SignalForge Myanmar 商机日报", text)
        self.assertIn("当前有效机会 + 过去24小时变化", text)
        self.assertIn("🔥 今天先看：2 条需处理", text)
        self.assertIn("Ministry of Energy", text)
        self.assertIn("优先跟进", text)
        self.assertIn("相关分包 4", text)
        self.assertIn("后续跟进：1 条 MEDIUM", text)
        self.assertIn("业务概览</b>：当前 <b>3</b> 个机会 · HIGH 1 · MEDIUM 1 · REVIEW 1", text)
        self.assertIn("2/2源 GREEN", text)
        self.assertIn("Assurance", text)
        self.assertNotIn("Source产出", text)
        self.assertNotIn("Signal质量：均分", text)
        self.assertNotIn("Q81/HIGH", text)


    def test_digest_surfaces_which_source_is_buying_what(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            database = self._db(tmp)
            payload = {
                "item_kind": "TENDER",
                "issuer": "Ministry of Industry, Myanmar",
                "title": "Steel Scrap (HMS-1) 1,000 tons procurement",
                "reference_no": "HIE-1/Myingyan/26-27/Steel Scrap/015",
                "deadline": "2026-09-14",
                "deadline_time": "16:00",
                "deadline_status": "OPEN",
                "scope_summary": "Purchase Steel Scrap (HMS-1), 1,000 tons",
                "url": "https://www.industrymsme.gov.mm/announcements/1027",
            }
            with connect(database) as conn, conn:
                conn.execute(
                    """INSERT INTO canonical_items(canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    ("industry:1027", "S38", "TENDER", payload["title"], payload["reference_no"], payload["title"], "2026-09-13", payload["deadline"], None, payload["url"], "h2", "e2", json.dumps(payload), "2026-09-13T11:00:00Z", "2026-09-13T11:00:00Z"),
                )
                conn.execute(
                    "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                    ("sig-industry", "S38", "industry:1027", "NEW", "2026-09-14T01:00:00Z", json.dumps({"signal_type": "NEW", "canonical_key": "industry:1027", **payload})),
                )
            digest = business_digest(database=database, registry=_Registry(), now=datetime(2026,9,14,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        changes = digest["activity_24h"]["business_changes"]
        self.assertEqual(changes[0]["source_id"], "S38")
        text = render_business_digest(digest)
        self.assertIn("🆕 24h 新增/更新", text)
        self.assertIn("Ministry of Industry</b> · [S38]", text)
        self.assertIn("采购内容：<b>Steel Scrap (HMS-1) 1,000 tons", text)
        self.assertIn("2026-09-14 16:00", text)
        self.assertIn('href="https://www.industrymsme.gov.mm/announcements/1027"', text)

    def test_digest_prefers_concrete_procurement_facts_over_generic_titles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,15,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        digest["business"]["attention"] = [
            {
                "canonical_key": "energy:235",
                "source_id": "S39",
                "item_kind": "TENDER",
                "attention_action": "PRIORITIZE",
                "primary_relevance": "ICT",
                "issuer": "Ministry of Energy, Myanmar",
                "title": "Open Tender 27/2026-2027",
                "scope_excerpt": "DMP/L-026(26-27)CAP Accessories for Communication and Information Ks | (Second Retender) Technology (2) Groups | DMP/L-067(26-27)CAP IOT Module (Siemens) (6) Nos Ks | DMP/L-073(26-27)CAP ICDD PDF-2 Software (1) Lot Ks | DMP/L-089(26-27)CAP Book Scanner, Motorized Screen, Desktop Computer and UPS (2) Groups Ks",
                "deadline": "2026-09-18",
                "deadline_time": "13:00",
                "deadline_status": "OPEN",
            },
            {
                "canonical_key": "mofa:59800",
                "source_id": "S30",
                "item_kind": "TENDER",
                "attention_action": "PRIORITIZE",
                "primary_relevance": "ICT",
                "issuer": "Ministry of Foreign Affairs, Myanmar",
                "title": "Open Tender",
                "scope_excerpt": "Tender invitation | (a) Data Server (1) Set | Windows Server 2025 Standard 24 Core with Microsoft License | Microsoft SQL Server 2022 Standard",
                "deadline": "2026-09-18",
                "deadline_time": "16:30",
                "deadline_status": "OPEN",
            },
            {
                "canonical_key": "doms:12735",
                "source_id": "S26",
                "item_kind": "TENDER",
                "attention_action": "REVIEW",
                "primary_relevance": "MEDICAL",
                "issuer": "Department of Medical Services",
                "title": "Tender Nos 8DMS/2026-2027(L), 9DMS/2026-2027(L), 10DMS/2026-2027(F)",
                "scope_excerpt": "8DMS(2026-2027)(L)_ad9e1cc0-dc4c-4e87-8b04-8ca27e94ce68 9DMS(2026-2027)(L)_99c2e627-1816-4a8a-9b27-8f0b5d94acf0",
                "deadline": None,
                "deadline_status": "UNKNOWN",
            },
        ]
        text = render_business_digest(digest)
        self.assertIn("Accessories for Communication and Information Technology ×2组", text)
        self.assertIn("IOT Module (Siemens) ×6", text)
        self.assertIn("ICDD PDF-2 Software ×1 Lot", text)
        self.assertIn("Book Scanner, Motorized Screen, Desktop Computer and UPS ×2组", text)
        self.assertIn("Data Server ×1套", text)
        self.assertIn("Windows Server 2025 Standard 24 Core", text)
        self.assertIn("SQL Server 2022 Standard", text)
        self.assertIn("采购明细尚未从官方附件抽取", text)
        self.assertNotIn("采购内容：<b>Open Tender 27/2026-2027", text)

    def test_digest_uses_reviewed_doms_ocr_scope_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,16,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        digest["business"]["attention"] = [{
            "canonical_key": "doms:12735",
            "source_id": "S26",
            "item_kind": "TENDER",
            "attention_action": "REVIEW",
            "primary_relevance": "MEDICAL",
            "issuer": "Department of Medical Services",
            "title": "Tender Nos 8DMS/2026-2027(L), 9DMS/2026-2027(L), 10DMS/2026-2027(F)",
            "scope_excerpt": "8DMS：Normalizer 135/165/220 KVA ×4/2/4；Orthopaedic Instrument Set ×5。9DMS：Pleuro Bronchoscope；OCT AngioPlex ×2。10DMS：300 mA Digital X-Ray；Mammography X-Ray。",
            "reviewed_enrichment_status": "REVIEWED_OCR_SCOPE",
            "deadline": None,
            "deadline_status": "UNKNOWN",
        }]
        text = render_business_digest(digest, translator=lambda values: (values, False))
        self.assertIn("Normalizer 135/165/220 KVA ×4/2/4", text)
        self.assertIn("OCT AngioPlex ×2", text)
        self.assertIn("300 mA Digital X-Ray", text)
        self.assertNotIn("采购明细尚未从官方附件抽取", text)

    def test_digest_extracts_industry_lot_procurement_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,15,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        digest["business"]["attention"] = [{
            "canonical_key": "industry:1023",
            "source_id": "S38",
            "item_kind": "TENDER",
            "attention_action": "PRIORITIZE",
            "primary_relevance": "INDUSTRIAL",
            "issuer": "Ministry of Industry, Myanmar",
            "title": "Laboratory equipment tender",
            "scope_excerpt": "Lot-1 သံ၊ သံမဏိဓာတ်ခွဲခန်းသုံး စက်ပစ္စည်း (၁၆)မျိုး Lot-2 ဘိလပ်မြေ ဓာတ်ခွဲခန်းသုံး စက်ပစ္စည်း (၃၁)မျိုး Lot-3 သံ၊ သံမဏိ ဓာတ်ခွဲခန်းသုံးစက်ပစ္စည်း (၉) မျိုး",
            "deadline": "2026-09-18",
            "deadline_status": "OPEN",
        }]
        text = render_business_digest(digest)
        self.assertIn("Lot 1：钢铁实验室设备 16类", text)
        self.assertIn("Lot 2：水泥实验室设备 31类", text)
        self.assertIn("Lot 3：钢铁实验室设备 9类", text)

    def test_digest_extracts_industry_yarn_item_without_translation_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,15,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        digest["business"]["attention"] = [{
            "canonical_key": "industry:1042",
            "source_id": "S38",
            "item_kind": "TENDER",
            "attention_action": "PRIORITIZE",
            "primary_relevance": "INDUSTRIAL",
            "issuer": "Ministry of Industry, Myanmar",
            "title": "အမှတ်(၃)အကြီးစားစက်မှုလုပ်ငန်း၊ အမှတ်(၈)အထည်စက်ရုံခွဲတွင် ၁/၇ ပီစီချည်(ရောင်စုံ) ၄၉,၄၆ဝ ပေါင် ဝယ်ယူရန် အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း",
            "deadline": "2026-09-18",
            "deadline_status": "OPEN",
        }]
        text = render_business_digest(digest, translator=lambda values: (values, False))
        self.assertIn("1/7 PC 彩色纱线 49,460 磅", text)
        self.assertNotIn("ပီစီချည်", text)

    def test_digest_extracts_current_medium_procurement_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,16,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        digest["business"]["attention"] = []
        digest["business"]["watchlist_count"] = 3
        digest["business"]["watchlist_items"] = [
            {
                "canonical_key": "industry:1035", "source_id": "S38", "item_kind": "TENDER",
                "issuer": "Ministry of Industry, Myanmar", "title": "Raw materials tender",
                "scope_excerpt": "Refractory (၅၀) မျိုး Castable Mortar (၁၀) မျိုး Consumable (၄) မျိုး Scrap ကုန်ကြမ်း HMS-1 (2000) Tons HMS-2 (1495) Tons",
                "deadline": "2026-10-02", "deadline_status": "OPEN",
            },
            {
                "canonical_key": "industry:1039", "source_id": "S38", "item_kind": "TENDER",
                "issuer": "Ministry of Industry, Myanmar", "title": "Spares tender",
                "scope_excerpt": "စက်ဆီ၊ချောဆီ (၉)မျိုး Electrical စက်အရန် ပစ္စည်း (၂၃)မျိုး Mechanical စက်အရန်ပစ္စည်း (၄၃)မျိုး",
                "deadline": "2026-09-25", "deadline_status": "OPEN",
            },
            {
                "canonical_key": "iwt:1038:2026-08-25", "source_id": "S22", "item_kind": "TENDER",
                "issuer": "Inland Water Transport (Myanmar)",
                "title": "အောက်ဖော်ပြပါရေယာဉ် ၁ စီးကို ဝယ်ယူရန် အပြိုင်ဈေးနှုန်းလွှာများ တင်သွင်းရန် ဖိတ်ခေါ်အပ်ပါသည်။",
                "deadline": "2026-11-03", "deadline_status": "OPEN",
            },
        ]
        text = render_business_digest(digest, translator=lambda values: (values, False))
        self.assertIn("Refractory 50类", text)
        self.assertIn("HMS-1 2000吨", text)
        self.assertIn("HMS-2 1495吨", text)
        self.assertIn("润滑油 9类", text)
        self.assertIn("Electrical 备件 23类", text)
        self.assertIn("Mechanical 备件 43类", text)
        self.assertIn("Coastal Cargo Vessel ×1艘", text)

    def test_render_keeps_distinct_opportunities_from_same_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,14,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        digest["business"]["attention"] = [
            {
                "canonical_key": "industry:steel",
                "source_id": "S38",
                "item_kind": "TENDER",
                "attention_action": "ACT_NOW",
                "primary_relevance": "INDUSTRIAL",
                "issuer": "Ministry of Industry, Myanmar",
                "title": "Steel Scrap (HMS-1) 1,000 tons procurement",
                "deadline": "2026-09-14",
                "deadline_time": "16:00",
                "deadline_status": "OPEN",
                "url": "https://www.industrymsme.gov.mm/announcements/1027",
            },
            {
                "canonical_key": "industry:oxygen",
                "source_id": "S38",
                "item_kind": "TENDER",
                "attention_action": "ACT_NOW",
                "primary_relevance": "INDUSTRIAL",
                "issuer": "Ministry of Industry, Myanmar",
                "title": "Industrial Oxygen Gas procurement",
                "deadline": "2026-09-14",
                "deadline_time": "16:00",
                "deadline_status": "OPEN",
                "url": "https://www.industrymsme.gov.mm/announcements/1028",
            },
        ]
        text = render_business_digest(digest)
        self.assertIn("Steel Scrap (HMS-1) 1,000 tons procurement", text)
        self.assertIn("Industrial Oxygen Gas procurement", text)
        self.assertGreaterEqual(text.count("[S38]"), 2)

    def test_digest_renders_recent_strategic_notice_with_official_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            database = self._db(tmp)
            payload = {
                "item_kind": "REGULATORY_NOTICE",
                "business_stage": "STRATEGIC_INTELLIGENCE",
                "issuer": "Posts and Telecommunications Department",
                "title": "Spectrum Roadmap 2026-2030",
                "publication_date": "2026-09-10",
                "telecom_signal_kind": "SPECTRUM_5G_POLICY",
                "url": "https://www.ptd.gov.mm/Uploads/LawFP/Attach/policy.pdf",
            }
            with connect(database) as conn, conn:
                conn.execute(
                    """INSERT INTO canonical_items(canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    ("ptd-policy:1", "S46", "REGULATORY_NOTICE", payload["title"], "PTD-POLICY-1", payload["title"], "2026-09-10", None, "Myanmar", payload["url"], "h", "e", json.dumps(payload), "2026-09-10T10:00:00Z", "2026-09-10T10:00:00Z"),
                )
                conn.execute(
                    "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                    ("sig-strategic", "S46", "ptd-policy:1", "NEW", "2026-09-10T11:00:00Z", json.dumps({"signal_type": "NEW", "canonical_key": "ptd-policy:1", **payload})),
                )
            digest = business_digest(database=database, registry=_Registry(), now=datetime(2026,9,10,12,0,tzinfo=UTC))  # type: ignore[arg-type]
        notices = digest["activity_24h"]["strategic_notices"]
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]["source_id"], "S46")
        text = render_business_digest(digest)
        self.assertIn("📡 战略动态", text)
        self.assertIn("Spectrum Roadmap 2026-2030", text)
        self.assertIn("SPECTRUM_5G_POLICY", text)
        self.assertIn('href="https://www.ptd.gov.mm/Uploads/LawFP/Attach/policy.pdf"', text)

    def test_digest_translates_burmese_attention_issuers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,10,12,0,tzinfo=UTC))  # type: ignore[arg-type]
        attention = digest["business"]["attention"]
        attention[0]["issuer"] = "စွမ်းအင်ဝန်ကြီးဌာန"
        attention[1]["issuer"] = "ဆေးဘက်ဆိုင်ရာဝန်ဆောင်မှုဌာန"

        def fake_translator(values: list[str]) -> tuple[list[str], bool]:
            self.assertEqual(len(values), 2)
            return ["能源部", "医疗服务部"], True

        text = render_business_digest(digest, translator=fake_translator)
        self.assertIn("能源部", text)
        self.assertIn("医疗服务部", text)
        self.assertIn("🌐 缅文内容已机器翻译为中文", text)
        self.assertNotIn("စွမ်းအင်", text)

    def test_digest_chunks_large_burmese_translation_batches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,14,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        digest["business"]["attention"] = [
            {
                "canonical_key": f"my:{index}",
                "source_id": "S21",
                "item_kind": "TENDER",
                "attention_action": "ACT_NOW",
                "primary_relevance": "OTHER",
                "issuer": "Myanma Railways",
                "title": f"စက်ပစ္စည်း ဝယ်ယူရန် {index}",
                "deadline": "2026-09-18",
                "deadline_status": "OPEN",
            }
            for index in range(5)
        ]
        batch_sizes: list[int] = []

        def fake_translator(values: list[str]) -> tuple[list[str], bool]:
            batch_sizes.append(len(values))
            return [f"中文采购项目 {len(batch_sizes)}-{index}" for index, _ in enumerate(values)], True

        text = render_business_digest(digest, translator=fake_translator)
        self.assertEqual(batch_sizes, [2, 2, 1])
        self.assertIn("中文采购项目", text)
        self.assertNotIn("စက်ပစ္စည်း", text)

    def test_attention_renders_all_current_rows_without_hidden_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,14,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        rows = []
        for index in range(8):
            rows.append({
                "canonical_key": f"opp:{index}",
                "source_id": f"S{30 + index}",
                "item_kind": "TENDER",
                "attention_action": "PRIORITIZE",
                "primary_relevance": "ICT" if index in {4, 5} else "INDUSTRIAL",
                "issuer": f"Issuer {index}",
                "title": f"Opportunity {index}",
                "deadline": "2026-09-18",
                "deadline_status": "OPEN",
            })
        digest["business"]["attention"] = rows
        text = render_business_digest(digest)
        self.assertIn("今天先看：8 条需处理", text)
        self.assertNotIn("展示前 6 条", text)
        for index in range(8):
            self.assertIn(f"Opportunity {index}", text)

    def test_moep_attention_uses_concrete_procurement_summaries_and_short_issuer_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,16,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        digest["business"]["attention"] = [
            {"canonical_key":"moep:7144","source_id":"S20","item_kind":"TENDER","attention_action":"REVIEW","issuer":"DPTSC","title":"Tender","scope_excerpt":"Database Creation and Modification for 500kV Phayagyi, Hlaingtharyar and Taungoo Substation in Existing SCADA- EMS System","deadline_status":"UNKNOWN"},
            {"canonical_key":"moep:7151","source_id":"S20","item_kind":"TENDER","attention_action":"REVIEW","issuer":"EPGE","title":"Tender","scope_excerpt":"ရေအားလျှပ်စစ်ဓာတ်အားပေးစက်ရုံများတွင် အသုံးပြုရန် စက်မှုနှင့် လျှပ်စစ်ပိုင်းဆိုင်ရာစက်အရံပစ္စည်း(၁၂)မျိုးဝယ်ယူခြင်း","deadline_status":"UNKNOWN"},
            {"canonical_key":"moep:7157","source_id":"S20","item_kind":"TENDER","attention_action":"REVIEW","issuer":"DPTSC","title":"Tender","scope_excerpt":"၂၃၀ကေဗွီ ကမာနတ်-လှော်ကားဓာတ်အား လိုင်း(၃၈.၄)မိုင်ရှိ ACSR Conductor ကြိုးအား ACCC Conductor ကြိုးဖြင့် အစားထိုးလဲလှယ်ရန် လိုအပ်သော ပစ္စည်းများ","deadline_status":"UNKNOWN"},
        ]
        text = render_business_digest(digest, translator=lambda values: (values, False))
        self.assertIn("MOEP / DPTSC", text)
        self.assertIn("MOEP / EPGE", text)
        self.assertIn("500kV Phayagyi、Hlaingtharyar、Taungoo", text)
        self.assertIn("水电站机械及电气备件 12类", text)
        self.assertIn("ACSR→ACCC 导线更换所需材料", text)

    def test_reviewed_customs_attention_shows_business_event_not_generic_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,16,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        digest["business"]["attention"] = [{
            "canonical_key":"customs-auction:2026-09-08:de1e5fca89686a1f",
            "source_id":"S08A",
            "item_kind":"AUCTION_NOTICE",
            "attention_action":"REVIEW",
            "issuer":"Myanmar Customs Department",
            "title":"Generic Customs auction announcement",
            "scope_excerpt":"海关拍卖：钢铁/塑料原料/一般消费品",
            "deadline_status":"UNKNOWN",
            "action_date":"2026-09-28",
            "action_time":"10:00",
            "location":"Yangon Customs Training School",
            "next_action_summary":"9/16–18买表格；9/21–25缴保证金/看货；9/28 10:00拍卖",
            "reference_no":"CUSTOMS-AUCTION-20260908-de1e5fca",
            "reviewed_enrichment_status":"REVIEWED_TEXT_PDF_CURRENT_EVENT",
            "url":"https://customs.gov.mm/Announcements",
        }]
        text = render_business_digest(digest, translator=lambda values: (values, False))
        self.assertIn("Myanmar Customs", text)
        self.assertIn("竞买内容：<b>海关拍卖：钢铁/塑料原料/一般消费品</b>", text)
        self.assertIn("活动日 2026-09-28 10:00", text)
        self.assertIn("下一步 9/16–18买表格；9/21–25缴保证金/看货；9/28 10:00拍卖", text)
        self.assertNotIn("Generic Customs auction announcement", text)
        self.assertNotIn("CUSTOMS-AUCTION-20260908", text)

    def test_watchlist_renders_all_current_medium_opportunities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,14,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        digest["business"]["attention"] = []
        digest["business"]["watchlist_items"] = [
            {
                "canonical_key": f"watch:{index}",
                "source_id": "S38" if index < 4 else "S22",
                "item_kind": "TENDER",
                "issuer": "Issuer",
                "title": f"Medium opportunity {index}",
                "deadline": f"2026-09-{20 + index:02d}",
                "deadline_status": "OPEN",
            }
            for index in range(7)
        ]
        digest["business"]["watchlist_count"] = 7
        text = render_business_digest(digest)
        self.assertIn("后续跟进：7 条 MEDIUM", text)
        self.assertNotIn("展示前 2 条", text)
        for index in range(7):
            self.assertIn(f"Medium opportunity {index}", text)

    def test_render_truncates_only_at_line_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,14,2,0,tzinfo=UTC))  # type: ignore[arg-type]
        rows = []
        for index in range(12):
            rows.append({
                "canonical_key": f"industry:{index}",
                "source_id": "S38",
                "item_kind": "TENDER",
                "attention_action": "ACT_NOW",
                "primary_relevance": "INDUSTRIAL",
                "issuer": "Ministry of Industry, Myanmar",
                "title": (f"Procurement package {index} " + "X" * 160),
                "reference_no": f"REF-{index}-" + "R" * 40,
                "deadline": "2026-09-16",
                "deadline_time": "16:00",
                "deadline_status": "OPEN",
                "location": "Nay Pyi Taw " + "L" * 50,
                "next_action_summary": "Collect tender documents and validate commercial fit " + "N" * 90,
                "url": f"https://example.gov.mm/tender/{index}",
            })
        digest["business"]["attention"] = rows
        digest["activity_24h"]["business_changes"] = [dict(item, signal_type="NEW") for item in rows[6:12]]
        digest["business"]["watchlist_items"] = [dict(item, canonical_key=f"watch:{index}") for index, item in enumerate(rows[:2])]
        digest["business"]["watchlist_count"] = 2
        text = render_business_digest(digest)
        self.assertLessEqual(len(text), 4096)
        self.assertEqual(text.count("<b>"), text.count("</b>"))
        self.assertEqual(text.count("<a href="), text.count("</a>"))

    def test_dry_run_does_not_write_digest_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            database = self._db(tmp)
            result = telegram_digest(database=database, now=datetime(2026,9,10,12,0,tzinfo=UTC), dry_run=True, audit_network=False)
            self.assertEqual(result["pending_count"], 1)
            with connect(database) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM digest_delivery_receipts").fetchone()[0], 0)

    def test_real_delivery_is_once_per_myanmar_calendar_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()), patch("signalforge.business_digest._send_message", return_value="501") as send:
            database = self._db(tmp)
            first = telegram_digest(database=database, now=datetime(2026,9,10,12,0,tzinfo=UTC), bot_token="secret", chat_id="42", audit_network=False)
            second = telegram_digest(database=database, now=datetime(2026,9,10,15,0,tzinfo=UTC), bot_token="secret", chat_id="42", audit_network=False)
            next_day = telegram_digest(database=database, now=datetime(2026,9,11,2,0,tzinfo=UTC), bot_token="secret", chat_id="42", audit_network=False)
            with connect(database) as conn:
                receipt_count = conn.execute("SELECT COUNT(*) FROM digest_delivery_receipts").fetchone()[0]
        self.assertEqual(first["sent_count"], 1)
        self.assertEqual(second["sent_count"], 0)
        self.assertTrue(second["deduplicated"])
        self.assertEqual(next_day["sent_count"], 1)
        self.assertEqual(send.call_count, 2)
        self.assertEqual(receipt_count, 2)

    def test_migration_creates_digest_receipt_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            with connect(database) as conn:
                names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                version = conn.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0]
        self.assertIn("digest_delivery_receipts", names)
        self.assertEqual(version, 8)


if __name__ == "__main__":
    unittest.main()
