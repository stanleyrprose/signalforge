from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.cli import main
from signalforge.db import connect, migrate
from signalforge.opportunities import _deadline_kind, _reference_bundle, _reference_focus, current_opportunities
from signalforge.mpt import parse_tender_detail


def _insert_canonical(conn, *, key: str, source_id: str, payload: dict[str, object]) -> None:  # type: ignore[no-untyped-def]
    conn.execute(
        """
        INSERT INTO canonical_items(
            canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,
            content_hash,evidence_sha256,payload_json,created_at,updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            key,
            source_id,
            str(payload.get("item_kind") or "TENDER"),
            str(payload.get("title") or key),
            str(payload.get("reference_no") or key),
            str(payload.get("project_name") or payload.get("title") or key),
            payload.get("publication_date"),
            payload.get("deadline"),
            payload.get("location"),
            str(payload.get("url") or f"https://example.test/{key}"),
            f"hash-{key}",
            f"evidence-{key}",
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
            "2026-09-01T00:00:00Z",
            "2026-09-09T00:00:00Z",
        ),
    )


def _insert_signal(conn, *, signal_id: str, source_id: str, key: str, created_at: str, signal_type: str = "NEW", reason: str | None = None) -> None:  # type: ignore[no-untyped-def]
    payload: dict[str, object] = {"signal_type": signal_type, "canonical_key": key}
    if reason is not None:
        payload["signal_reason"] = reason
    conn.execute(
        "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
        (signal_id, source_id, key, signal_type, created_at, json.dumps(payload, sort_keys=True)),
    )


class OpportunityViewTests(unittest.TestCase):
    def test_deadline_kind_derivation_is_source_scoped_and_canonical_first(self) -> None:
        pdf_close = {"deadline_evidence": "OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME"}
        html_close = {"deadline_evidence": "EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME"}
        self.assertEqual(_deadline_kind(pdf_close, "S30"), "BID_SUBMISSION_DEADLINE")
        self.assertEqual(_deadline_kind(pdf_close, "S39"), "BID_SUBMISSION_DEADLINE")
        self.assertEqual(_deadline_kind(html_close, "S38"), "BID_SUBMISSION_DEADLINE")
        self.assertIsNone(_deadline_kind(pdf_close, "S37"))
        self.assertIsNone(_deadline_kind(html_close, "S30"))
        self.assertEqual(
            _deadline_kind(
                {"deadline_kind": "TENDER_FORM_SALE_CLOSE", "deadline_evidence": "EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME"},
                "S38",
            ),
            "TENDER_FORM_SALE_CLOSE",
        )

    def test_energy_dmp_multi_reference_derivation_is_source_scoped_and_fail_closed(self) -> None:
        payload = {
            "detail_completeness": "HTML_ID_PUBLICATION_PLUS_TEXT_PDF_SCOPE_DEADLINE",
            "scope_summary": (
                "(1) DMP/L-026(26-27) CAP Accessories | "
                "(2) DMP/L- 067(26-27) CAP IOT Module | "
                "(3) DMP/L-089(26-27) Desktop Computer | "
                "duplicate DMP/L-026(26-27)"
            ),
        }
        refs, count, evidence = _reference_bundle(payload, "S39")
        self.assertEqual(refs, ["DMP/L-026(26-27)", "DMP/L-067(26-27)", "DMP/L-089(26-27)"])
        self.assertEqual(count, 3)
        self.assertEqual(evidence, "OFFICIAL_TEXT_NATIVE_PDF_SCOPE_DMP_REFERENCE_PATTERN")
        self.assertEqual(_reference_bundle(payload, "S30"), (None, None, None))
        self.assertEqual(_reference_bundle(dict(payload, scope_summary="DMP/L-026(26-27) only"), "S39"), (None, None, None))
        self.assertEqual(_reference_bundle(dict(payload, detail_completeness="HTML_ONLY"), "S39"), (None, None, None))
        explicit = dict(payload, reference_numbers=["EXPLICIT-1", "EXPLICIT-2"], reference_count=2, reference_numbers_evidence="CANONICAL")
        self.assertEqual(_reference_bundle(explicit, "S39"), (["EXPLICIT-1", "EXPLICIT-2"], 2, "CANONICAL"))

    def test_energy_dmp_focus_references_are_narrow_and_source_scoped(self) -> None:
        scope = (
            "DMP/L-026(26-27)CAP Accessories for Communication and Information Ks | (Second Retender) Technology (2) Groups | "
            "DMP/L-040(26-27) 6 API 5L Coated Steel Line Pipe | "
            "DMP/L-067(26-27)CAP IOT Module (Siemens) | "
            "DMP/L-073(26-27)CAP ICDD PDF-2 Software | "
            "DMP/L-089(26-27)CAP Book Scanner, Motorized Screen, Desktop Computer and UPS | "
            "DMP/L-104(26-27) Mud Chemical"
        )
        payload = {
            "detail_completeness": "HTML_ID_PUBLICATION_PLUS_TEXT_PDF_SCOPE_DEADLINE",
            "scope_summary": scope,
        }
        refs = [
            "DMP/L-026(26-27)",
            "DMP/L-040(26-27)",
            "DMP/L-067(26-27)",
            "DMP/L-073(26-27)",
            "DMP/L-089(26-27)",
            "DMP/L-104(26-27)",
        ]
        focus, count, relevance, focus_scope = _reference_focus(payload, "S39", refs)
        self.assertEqual(
            focus,
            ["DMP/L-026(26-27)", "DMP/L-067(26-27)", "DMP/L-073(26-27)", "DMP/L-089(26-27)"],
        )
        self.assertEqual(count, 4)
        self.assertEqual(relevance, "ICT_TELECOM")
        self.assertIn("Communication and Information", focus_scope)
        self.assertIn("IOT Module", focus_scope)
        self.assertIn("Software", focus_scope)
        self.assertIn("Desktop Computer", focus_scope)
        self.assertNotIn("Line Pipe", focus_scope)
        self.assertNotIn("Mud Chemical", focus_scope)
        self.assertNotRegex(focus_scope, r"\|\s*\(?\d+\)?(?:\s*\||$)")
        self.assertEqual(_reference_focus(payload, "S30", refs), (None, None, None, None))
        self.assertEqual(_reference_focus(payload, "S39", [refs[0]]), (None, None, None, None))

    def test_energy_multi_reference_flows_through_signal_backed_read_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            payload = {
                "item_kind": "TENDER",
                "business_stage": "OPPORTUNITY",
                "title": "Energy multi-lot tender",
                "reference_no": "ENERGY-27-2026-2027",
                "publication_date": "2026-09-04",
                "deadline": "2026-09-18",
                "deadline_time": "13:00",
                "deadline_evidence": "OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME",
                "scope_summary": "DMP/L-026(26-27) CAP Accessories | DMP/L- 067(26-27) IOT Module | DMP/L-089(26-27) Desktop Computer",
                "detail_completeness": "HTML_ID_PUBLICATION_PLUS_TEXT_PDF_SCOPE_DEADLINE",
                "url": "https://energy.gov.mm/tenders/235",
            }
            with connect(database) as conn, conn:
                _insert_canonical(conn, key="energy:multi", source_id="S39", payload=payload)
                _insert_signal(conn, signal_id="sig-energy", source_id="S39", key="energy:multi", created_at="2026-09-08T11:00:00Z")

            result = current_opportunities(database=database, now=datetime(2026, 9, 9, 4, 0, tzinfo=UTC), source_id="S39")
            self.assertEqual(result["count"], 1)
            row = result["opportunities"][0]
            self.assertEqual(row["reference_numbers"], ["DMP/L-026(26-27)", "DMP/L-067(26-27)", "DMP/L-089(26-27)"])
            self.assertEqual(row["reference_count"], 3)
            self.assertEqual(row["reference_numbers_evidence"], "OFFICIAL_TEXT_NATIVE_PDF_SCOPE_DMP_REFERENCE_PATTERN")
            self.assertEqual(row["focus_reference_numbers"], ["DMP/L-067(26-27)", "DMP/L-089(26-27)"])
            self.assertEqual(row["focus_reference_count"], 2)
            self.assertEqual(row["focus_relevance"], "ICT_TELECOM")
            self.assertIn("IOT Module", row["focus_scope_summary"])
            self.assertIn("Desktop Computer", row["focus_scope_summary"])
            self.assertEqual(row["reference_no"], "ENERGY-27-2026-2027")
            self.assertEqual(row["deadline_kind"], "BID_SUBMISSION_DEADLINE")


    def test_commercial_auction_notice_uses_action_date_without_fake_deadline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            payload = {
                "item_kind": "AUCTION_NOTICE",
                "business_stage": "OPPORTUNITY",
                "title": "Local Marketing and Milling Department, Open Tender No (6/2026-2027)(15.9.2026)",
                "reference_no": "MTE-LOCAL-6/2026-2027",
                "deadline": None,
                "deadline_evidence": "UNKNOWN_IN_IMAGE_SUPPLEMENT_NOT_PARSED",
                "action_date": "2026-09-15",
                "action_date_kind": "TENDER_EVENT_DATE",
                "action_date_evidence": "EXPLICIT_OFFICIAL_TITLE_DATE",
                "commercial_event_type": "SELLER_OPEN_TENDER_SALE",
                "commercial_direction": "BUY_FROM_ISSUER",
                "issuer": "Myanma Timber Enterprise",
                "scope_summary": "Local Marketing and Milling Department open tender sale; official image carries supplementary lot details.",
                "detail_completeness": "HTML_EVENT_SCOPE_REFERENCE_IMAGE_SUPPLEMENT_UNPARSED",
                "url": "https://mte.gov.mm/index.php/en/annoucements/17-tenders/local-milling-marketing-dept-tender/1605-392026",
            }
            with connect(database) as conn, conn:
                _insert_canonical(conn, key="mte:1605", source_id="S32", payload=payload)
                _insert_signal(conn, signal_id="sig-mte-1605", source_id="S32", key="mte:1605", created_at="2026-09-11T02:00:00Z")
            result = current_opportunities(database=database, now=datetime(2026, 9, 11, 2, 0, tzinfo=UTC), source_id="S32")
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["counts"], {"OPEN": 1, "UNKNOWN": 0, "EXPIRED": 0})
            row = result["opportunities"][0]
            self.assertEqual(row["item_kind"], "AUCTION_NOTICE")
            self.assertEqual(row["deadline_status"], "UNKNOWN")
            self.assertIsNone(row["deadline_at"])
            self.assertEqual(row["action_date"], "2026-09-15")
            self.assertEqual(row["action_date_kind"], "TENDER_EVENT_DATE")
            self.assertEqual(row["action_time"], "08:30")
            self.assertEqual(row["action_at"], "2026-09-15T08:30:00+06:30")
            self.assertEqual(row["location"], "Myanma Timber Enterprise, Gyogon Forest Compound, Insein Township, Yangon")
            self.assertEqual(row["quantity_or_lot_confidence"], "HIGH")
            self.assertEqual(row["quantity_or_lot_summary"], "Approximately 6,243 tons of teak/hardwood logs and sawn timber")
            self.assertIn("Earnest Money", row["next_action_summary"])
            self.assertEqual(row["reviewed_image_sha256"], "6a6c2452cf8ae18bf4985c3bd77f63bbd77ec710ad5b37ae3db51409854348e1")
            self.assertTrue(row["reviewed_enrichment_read_only"])
            self.assertEqual(row["opportunity_status"], "OPEN")
            self.assertEqual(row["actionability"], "OPEN")
            self.assertEqual(row["trust_grade"], "B")
            self.assertEqual(row["priority_band"], "REVIEW")
            self.assertEqual(row["signal_quality_score"], 86)
            self.assertEqual(row["signal_quality_band"], "VERY_HIGH")
            self.assertIn("REVIEWED_QUANTIFIED_SCOPE", row["signal_quality_strengths"])
            self.assertNotIn("QUANTITY_DETAIL_REVIEW_CONFIDENCE_MEDIUM", row["signal_quality_gaps"])
            self.assertIn("EXPLICIT_ACTION_DATE", row["qualification_reasons"])
            self.assertNotIn("DEADLINE_UNKNOWN", row["qualification_reasons"])
            self.assertEqual(row["commercial_direction"], "BUY_FROM_ISSUER")

    def test_default_view_is_signal_backed_deduped_and_active_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                _insert_canonical(
                    conn,
                    key="open:1",
                    source_id="S38",
                    payload={
                        "item_kind": "TENDER",
                        "business_stage": "OPPORTUNITY",
                        "title": "Open tender",
                        "reference_no": "OPEN-1",
                        "publication_date": "2026-09-08",
                        "deadline": "2026-09-18",
                        "deadline_time": "16:30",
                        "scope_summary": "Data Server with configuration, installation and maintenance",
                        "detail_completeness": "HTML_BUSINESS_SCOPE_AND_DEADLINE_NO_ATTACHMENT_REQUIRED",
                        "deadline_evidence": "EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME",
                        "url": "https://example.test/open/1",
                    },
                )
                _insert_signal(conn, signal_id="sig-1", source_id="S38", key="open:1", created_at="2026-09-08T10:00:00Z")
                _insert_signal(
                    conn,
                    signal_id="sig-2",
                    source_id="S38",
                    key="open:1",
                    created_at="2026-09-09T01:00:00Z",
                    signal_type="UPDATED",
                    reason="BUSINESS_ENRICHMENT",
                )
                _insert_canonical(
                    conn,
                    key="unknown:1",
                    source_id="S26",
                    payload={
                        "item_kind": "TENDER",
                        "business_stage": "OPPORTUNITY",
                        "title": "Unknown deadline tender",
                        "reference_no": "8DMS/2026-2027(L)",
                        "reference_numbers": ["8DMS/2026-2027(L)", "9DMS/2026-2027(L)", "10DMS/2026-2027(F)"],
                        "reference_count": 3,
                        "reference_numbers_evidence": "HTML_TITLE",
                        "deadline": None,
                        "url": "https://example.test/unknown/1",
                    },
                )
                _insert_signal(conn, signal_id="sig-3", source_id="S26", key="unknown:1", created_at="2026-09-09T02:00:00Z")
                _insert_canonical(
                    conn,
                    key="expired:1",
                    source_id="S25",
                    payload={
                        "item_kind": "TENDER",
                        "business_stage": "OPPORTUNITY",
                        "title": "Expired tender",
                        "reference_no": "EXPIRED-1",
                        "deadline": "2026-09-01",
                        "deadline_time": "16:00",
                        "url": "https://example.test/expired/1",
                    },
                )
                _insert_signal(conn, signal_id="sig-4", source_id="S25", key="expired:1", created_at="2026-09-01T01:00:00Z")
                _insert_canonical(
                    conn,
                    key="silent:1",
                    source_id="S39",
                    payload={
                        "item_kind": "TENDER",
                        "business_stage": "OPPORTUNITY",
                        "title": "Never signaled",
                        "reference_no": "SILENT-1",
                        "deadline": "2026-10-01",
                        "deadline_time": "13:00",
                        "url": "https://example.test/silent/1",
                    },
                )

            result = current_opportunities(database=database, now=datetime(2026, 9, 9, 4, 0, tzinfo=UTC))
            self.assertEqual(result["count"], 2)
            self.assertEqual(result["counts"], {"OPEN": 1, "UNKNOWN": 1, "EXPIRED": 0})
            self.assertEqual(result["qualification_policy_version"], 1)
            self.assertEqual(result["qualification_counts"]["trust_grade"], {"A": 1, "B": 1, "C": 0})
            self.assertEqual(result["qualification_counts"]["priority_band"], {"HIGH": 1, "MEDIUM": 0, "REVIEW": 1, "LOW": 0})
            rows = result["opportunities"]
            assert isinstance(rows, list)
            self.assertEqual([row["canonical_key"] for row in rows], ["open:1", "unknown:1"])
            self.assertEqual(rows[0]["deadline_status"], "OPEN")
            self.assertEqual(rows[0]["deadline_kind"], "BID_SUBMISSION_DEADLINE")
            self.assertEqual(rows[0]["deadline_at"], "2026-09-18T16:30:00+06:30")
            self.assertEqual(rows[0]["signal_count"], 2)
            self.assertEqual(rows[0]["latest_signal_id"], "sig-2")
            self.assertEqual(rows[0]["latest_signal_type"], "UPDATED")
            self.assertEqual(rows[0]["latest_signal_reason"], "BUSINESS_ENRICHMENT")
            self.assertEqual(rows[0]["trust_grade"], "A")
            self.assertEqual(rows[0]["priority_band"], "HIGH")
            self.assertEqual(rows[0]["source_engine"], "provider")
            self.assertEqual(rows[0]["evidence_level"], "OFFICIAL_HTML_VIA_PROVIDER")
            self.assertIn("ICT", rows[0]["relevance_categories"])
            self.assertEqual(rows[1]["deadline_status"], "UNKNOWN")
            self.assertEqual(rows[1]["trust_grade"], "B")
            self.assertEqual(rows[1]["priority_band"], "REVIEW")
            self.assertEqual(rows[1]["primary_relevance"], "MEDICAL")
            self.assertEqual(
                rows[1]["reference_numbers"],
                ["8DMS/2026-2027(L)", "9DMS/2026-2027(L)", "10DMS/2026-2027(F)"],
            )
            self.assertEqual(rows[1]["reference_count"], 3)
            self.assertEqual(rows[1]["reference_numbers_evidence"], "HTML_TITLE")

    def test_moep_signal_backed_legacy_tender_enters_current_view_with_bounded_unknown_freshness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                _insert_canonical(
                    conn,
                    key="moep:current",
                    source_id="S20",
                    payload={
                        "item_kind": "TENDER",
                        "title": "MOEP current tender",
                        "project_name": "Database Creation and Modification for 500kV Substation SCADA-EMS System",
                        "reference_no": "MOEP-CONTENT-1",
                        "publication_date": "2026-09-11",
                        "deadline": None,
                        "url": "https://moep.gov.mm/mm/ignite/contentView/1",
                    },
                )
                _insert_signal(conn, signal_id="sig-moep-current", source_id="S20", key="moep:current", created_at="2026-09-11T10:00:00Z")
                _insert_canonical(
                    conn,
                    key="moep:stale",
                    source_id="S20",
                    payload={
                        "item_kind": "TENDER",
                        "title": "MOEP stale tender",
                        "project_name": "Old tender with unknown deadline",
                        "reference_no": "MOEP-CONTENT-OLD",
                        "publication_date": "2026-07-01",
                        "deadline": None,
                        "url": "https://moep.gov.mm/mm/ignite/contentView/2",
                    },
                )
                _insert_signal(conn, signal_id="sig-moep-stale", source_id="S20", key="moep:stale", created_at="2026-07-01T10:00:00Z")

            result = current_opportunities(database=database, now=datetime(2026, 9, 16, 4, 0, tzinfo=UTC), source_id="S20")
            self.assertEqual(result["count"], 1)
            row = result["opportunities"][0]
            self.assertEqual(row["canonical_key"], "moep:current")
            self.assertEqual(row["deadline_status"], "UNKNOWN")
            self.assertEqual(row["opportunity_status"], "UNKNOWN")
            self.assertEqual(row["scope_summary"], "Database Creation and Modification for 500kV Substation SCADA-EMS System")
            self.assertEqual(row["primary_relevance"], "ICT")
            self.assertIn("ENERGY", row["relevance_categories"])

    def test_ptd_deadline_kind_and_opening_semantics_flow_through_read_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            payload = {
                "item_kind": "TENDER",
                "business_stage": "OPPORTUNITY",
                "title": "PTD radio frequency monitoring tender",
                "reference_no": "PTD-20260910-1",
                "publication_date": "2026-09-10",
                "deadline": "2026-09-18",
                "deadline_time": None,
                "deadline_kind": "TENDER_FORM_SALE_CLOSE",
                "deadline_evidence": "OFFICIAL_TEXT_NATIVE_PDF_TENDER_FORM_SALE_CLOSE_DATE",
                "tender_opening_date": "2026-09-22",
                "tender_opening_time": "13:30",
                "scope_summary": "Radio frequency monitoring equipment and associated telecommunications services.",
                "detail_completeness": "HTML_EVENT_SCOPE_TEXT_PDF_PARTICIPATION_CLOSE",
                "url": "https://www.ptd.gov.mm/AnnouncementDetail.aspx?id=test",
            }
            with connect(database) as conn, conn:
                _insert_canonical(conn, key="ptd:test", source_id="S34", payload=payload)
                _insert_signal(conn, signal_id="ptd-sig", source_id="S34", key="ptd:test", created_at="2026-09-10T01:00:00Z")

            result = current_opportunities(
                database=database,
                now=datetime(2026, 9, 10, 2, 0, tzinfo=UTC),
                source_id="S34",
            )
            self.assertEqual(result["count"], 1)
            row = result["opportunities"][0]
            self.assertEqual(row["deadline_kind"], "TENDER_FORM_SALE_CLOSE")
            self.assertEqual(row["tender_opening_date"], "2026-09-22")
            self.assertEqual(row["tender_opening_time"], "13:30")
            self.assertEqual(row["deadline_status"], "OPEN")
            self.assertEqual(row["primary_relevance"], "TELECOM")
            self.assertEqual(row["evidence_level"], "OFFICIAL_HTML_PLUS_TEXT_PDF")

    def test_future_mpt_tender_flows_to_a_high_telecom_opportunity(self) -> None:
        html = b"""
        <html><body><table>
          <tr><td>Date</td><td>September 9, 2026</td></tr>
          <tr><td>Reference No</td><td>202609-CTO-099</td></tr>
          <tr><td>Project Name</td><td>Mobile Network Fiber Maintenance FY26</td></tr>
          <tr><td>Location</td><td>Myanmar, Nationwide</td></tr>
          <tr><td>Company Size</td><td>Vendor annual turnover must exceed 2 Billion MMK.</td></tr>
          <tr><td>Required quantity</td><td>Mobile network BTS fiber maintenance, corrective maintenance and field support nationwide.</td></tr>
        </table>
        <p>Complete vendor registration before the deadline 18 th September 2026.</p>
        <p>Based on your information, we will conduct the Pre-Qualification stage.</p>
        </body></html>
        """
        tender = parse_tender_detail(html, "https://mpt.com.mm/en/mobile-network-fiber-maintenance-fy26/")
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.business_stage, "OPPORTUNITY")
        self.assertEqual(tender.deadline, "2026-09-18")
        self.assertEqual(tender.deadline_evidence, "EXPLICIT_HTML_DEADLINE_DATE")

        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            payload = tender.payload()
            payload["item_kind"] = "TENDER"
            payload["title"] = tender.project_name
            with connect(database) as conn, conn:
                _insert_canonical(conn, key=tender.canonical_key, source_id="S13", payload=payload)
                _insert_signal(
                    conn,
                    signal_id="mpt-future-sig",
                    source_id="S13",
                    key=tender.canonical_key,
                    created_at="2026-09-09T12:00:00Z",
                )

            result = current_opportunities(
                database=database,
                now=datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
                source_id="S13",
            )
            self.assertEqual(result["count"], 1)
            row = result["opportunities"][0]
            self.assertEqual(row["canonical_key"], "mpt:202609-CTO-099")
            self.assertEqual(row["deadline_status"], "OPEN")
            self.assertEqual(row["trust_grade"], "A")
            self.assertEqual(row["priority_band"], "HIGH")
            self.assertEqual(row["primary_relevance"], "TELECOM")
            self.assertIn("TELECOM", row["relevance_categories"])
            self.assertEqual(row["source_engine"], "direct_http")
            self.assertEqual(row["evidence_level"], "OFFICIAL_HTML")

    def test_include_expired_source_filter_and_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                for index, deadline in enumerate(("2026-09-10", "2026-09-11", "2026-09-01"), start=1):
                    key = f"item:{index}"
                    _insert_canonical(
                        conn,
                        key=key,
                        source_id="S38",
                        payload={
                            "item_kind": "TENDER",
                            "business_stage": "OPPORTUNITY",
                            "title": key,
                            "reference_no": key,
                            "deadline": deadline,
                            "deadline_time": "16:00",
                            "url": f"https://example.test/{key}",
                        },
                    )
                    _insert_signal(conn, signal_id=f"sig-{index}", source_id="S38", key=key, created_at=f"2026-09-0{index}T00:00:00Z")

            result = current_opportunities(
                database=database,
                now=datetime(2026, 9, 9, 4, 0, tzinfo=UTC),
                source_id="S38",
                include_expired=True,
                limit=2,
            )
            self.assertEqual(result["count"], 2)
            self.assertEqual(result["total_matching"], 3)
            self.assertEqual(result["counts"], {"OPEN": 2, "UNKNOWN": 0, "EXPIRED": 1})
            rows = result["opportunities"]
            assert isinstance(rows, list)
            self.assertEqual([row["canonical_key"] for row in rows], ["item:1", "item:2"])

    def test_cli_command_is_read_only_surface_not_worker_verb(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                _insert_canonical(
                    conn,
                    key="cli:1",
                    source_id="S39",
                    payload={
                        "item_kind": "TENDER",
                        "business_stage": "OPPORTUNITY",
                        "title": "CLI tender",
                        "reference_no": "CLI-1",
                        "deadline": "2026-09-18",
                        "deadline_time": "13:00",
                        "url": "https://example.test/cli/1",
                    },
                )
                _insert_signal(conn, signal_id="cli-sig", source_id="S39", key="cli:1", created_at="2026-09-09T01:00:00Z")

            output = io.StringIO()
            with patch.dict(os.environ, {"SIGNALFORGE_DB": str(database)}), redirect_stdout(output):
                code = main(["opportunities", "--source-id", "S39", "--limit", "5"])
            self.assertEqual(code, 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["opportunities"][0]["canonical_key"], "cli:1")


if __name__ == "__main__":
    unittest.main()
