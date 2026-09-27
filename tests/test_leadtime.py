from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.db import connect, migrate
from signalforge.leadtime import (
    leadtime_report,
    link_procurement,
    precursor_candidates,
    procurement_link_suggestions,
    promote_precursor_from_canonical,
    record_project_event,
)


class ProjectLeadtimeTests(unittest.TestCase):
    @staticmethod
    def _insert_tender(
        database: Path,
        *,
        canonical_key: str,
        publication_date: str | None,
        created_at: str,
        title: str,
    ) -> None:
        with connect(database) as conn, conn:
            conn.execute(
                """
                INSERT INTO canonical_items(
                    canonical_key,source_id,item_kind,title,reference_no,project_name,
                    publication_date,deadline,location,url,content_hash,evidence_sha256,
                    payload_json,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    canonical_key,
                    "S43",
                    "TENDER",
                    title,
                    canonical_key,
                    title,
                    publication_date,
                    "2026-10-20",
                    None,
                    f"https://official.test/{canonical_key}",
                    f"hash-{canonical_key}",
                    f"sha-{canonical_key}",
                    json.dumps({"business_stage": "OPPORTUNITY"}),
                    created_at,
                    created_at,
                ),
            )

    def test_prefers_official_publication_date_over_late_ingestion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            self._insert_tender(
                database,
                canonical_key="tender:bridge-1",
                publication_date="2026-09-20",
                created_at="2026-09-25T02:00:00Z",
                title="Bridge rehabilitation tender",
            )

            record_project_event(
                project_key="moc:bridge-rehab-1",
                source_id="S01",
                stage="PROJECT_ANNOUNCEMENT",
                title="Government announces bridge rehabilitation",
                url="https://official.test/announcement",
                detected_at=datetime(2026, 8, 21, 2, 0, tzinfo=UTC),
                database=database,
            )
            record_project_event(
                project_key="moc:bridge-rehab-1",
                source_id="S43",
                stage="PRE_PROCUREMENT",
                title="Bridge work enters preparation",
                detected_at=datetime(2026, 9, 5, 2, 0, tzinfo=UTC),
                database=database,
            )
            link_procurement(
                project_key="moc:bridge-rehab-1",
                canonical_key="tender:bridge-1",
                link_basis="reviewed exact issuer + project identity",
                database=database,
            )

            report = leadtime_report(database=database)
            self.assertEqual(report["summary"]["linked_projects"], 1)
            self.assertEqual(report["summary"]["median_lead_days"], 30.0)
            self.assertEqual(report["summary"]["official_publication_basis_projects"], 1)
            self.assertEqual(report["summary"]["ingestion_fallback_projects"], 0)
            row = report["projects"][0]
            self.assertEqual(row["first_stage"], "PROJECT_ANNOUNCEMENT")
            self.assertEqual(row["procurement_formed_at"], "2026-09-20")
            self.assertEqual(row["canonical_ingested_at"], "2026-09-25T02:00:00Z")
            self.assertEqual(row["leadtime_basis"], "OFFICIAL_PUBLICATION_DATE")
            self.assertEqual(row["leadtime_precision"], "CALENDAR_DAY")
            self.assertEqual(row["lead_days"], 30.0)

    def test_summary_uses_all_reviewed_links_even_when_output_is_limited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            self._insert_tender(
                database,
                canonical_key="tender:official",
                publication_date="2026-09-20",
                created_at="2026-09-25T02:00:00Z",
                title="Official-date tender",
            )
            self._insert_tender(
                database,
                canonical_key="tender:fallback",
                publication_date=None,
                created_at="2026-09-20T02:00:00Z",
                title="Fallback tender",
            )
            record_project_event(
                project_key="project:official",
                source_id="S01",
                stage="PROJECT_ANNOUNCEMENT",
                title="Official precursor",
                detected_at=datetime(2026, 8, 21, 2, 0, tzinfo=UTC),
                database=database,
            )
            record_project_event(
                project_key="project:fallback",
                source_id="S01",
                stage="PRE_PROCUREMENT",
                title="Fallback precursor",
                detected_at=datetime(2026, 9, 10, 2, 0, tzinfo=UTC),
                database=database,
            )
            link_procurement(
                project_key="project:official",
                canonical_key="tender:official",
                link_basis="reviewed",
                database=database,
            )
            link_procurement(
                project_key="project:fallback",
                canonical_key="tender:fallback",
                link_basis="reviewed",
                database=database,
            )

            report = leadtime_report(database=database, limit=1)
            summary = report["summary"]
            self.assertEqual(summary["tracked_projects"], 2)
            self.assertEqual(summary["linked_projects_total"], 2)
            self.assertEqual(summary["linked_projects"], 2)
            self.assertEqual(summary["measurement_coverage_rate"], 1.0)
            self.assertEqual(summary["official_publication_basis_projects"], 1)
            self.assertEqual(summary["ingestion_fallback_projects"], 1)
            self.assertEqual(summary["median_lead_days"], 20.0)
            self.assertEqual(summary["mean_lead_days"], 20.0)
            self.assertEqual(summary["min_lead_days"], 10.0)
            self.assertEqual(summary["max_lead_days"], 30.0)
            self.assertEqual(summary["returned_projects"], 1)
            self.assertEqual(len(report["projects"]), 1)
            self.assertTrue(report["semantics"]["measurement_coverage_is_not_conversion_rate"])

    def test_requires_explicit_reviewed_link_and_real_procurement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with self.assertRaises(ValueError):
                link_procurement(
                    project_key="x",
                    canonical_key="missing",
                    link_basis="reviewed",
                    database=database,
                )
            with self.assertRaises(ValueError):
                record_project_event(
                    project_key="x",
                    source_id="S01",
                    stage="GUESS",
                    title="bad stage",
                    database=database,
                )


    def test_reviewed_precursor_promotion_uses_first_retained_time_not_publication_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            created_at = "2026-09-25T03:00:00Z"
            with connect(database) as conn, conn:
                conn.execute(
                    """
                    INSERT INTO canonical_items(
                        canonical_key,source_id,item_kind,title,reference_no,project_name,
                        publication_date,deadline,location,url,content_hash,evidence_sha256,
                        payload_json,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "moi-project:83043", "S48", "REGULATORY_NOTICE",
                        "Yadanabon Cyber City project coordination meeting", "MOI-NEWS-83043",
                        "Yadanabon Cyber City project coordination meeting", "2026-05-22", None, "Myanmar",
                        "https://www.moi.gov.mm/news/83043", "hash-83043", "a" * 64,
                        json.dumps({
                            "business_stage": "PROJECT_PRECURSOR_CANDIDATE",
                            "precursor_review_required": True,
                            "precursor_stage_hint": "PROJECT_ANNOUNCEMENT",
                            "precursor_selection_basis": "PROJECT_MARKER+TARGET_SECTOR+FORWARD_ACTION",
                            "relevance_categories": ["CONSTRUCTION", "TELECOM"],
                        }),
                        created_at, created_at,
                    ),
                )
            queue = precursor_candidates(database=database)
            self.assertEqual(queue["summary"]["pending_review"], 1)
            self.assertEqual(queue["candidates"][0]["first_retained_at"], created_at)
            self.assertEqual(queue["candidates"][0]["publication_date"], "2026-05-22")
            promoted = promote_precursor_from_canonical(
                canonical_key="moi-project:83043",
                project_key="yadanabon-cyber-city",
                stage="PROJECT_ANNOUNCEMENT",
                review_basis="reviewed exact project identity",
                reviewed_by="operator",
                database=database,
            )
            self.assertEqual(promoted["detected_at"], created_at)
            self.assertEqual(promoted["publication_date"], "2026-05-22")
            queue = precursor_candidates(database=database)
            self.assertEqual(queue["summary"]["tracked"], 1)
            self.assertEqual(queue["candidates"][0]["project_key"], "yadanabon-cyber-city")

    def test_precursor_promotion_rejects_non_candidate_and_tender_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                conn.execute(
                    """
                    INSERT INTO canonical_items(
                        canonical_key,source_id,item_kind,title,reference_no,project_name,
                        publication_date,deadline,location,url,content_hash,evidence_sha256,
                        payload_json,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "notice:ordinary", "S46", "REGULATORY_NOTICE", "Ordinary policy",
                        "ordinary", "Ordinary policy", "2026-09-24", None, "Myanmar",
                        "https://official.test/ordinary", "hash", "sha",
                        json.dumps({"business_stage": "STRATEGIC_INTELLIGENCE"}),
                        "2026-09-24T00:00:00Z", "2026-09-24T00:00:00Z",
                    ),
                )
            with self.assertRaisesRegex(ValueError, "not a project precursor candidate"):
                promote_precursor_from_canonical(
                    canonical_key="notice:ordinary", project_key="x", stage="PROJECT_ANNOUNCEMENT",
                    review_basis="reviewed", reviewed_by="operator", database=database,
                )
            with self.assertRaisesRegex(ValueError, "invalid precursor stage"):
                promote_precursor_from_canonical(
                    canonical_key="notice:ordinary", project_key="x", stage="TENDER",
                    review_basis="reviewed", reviewed_by="operator", database=database,
                )


    def test_procurement_link_suggestions_are_review_only_and_temporally_causal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            created_at = "2026-09-01T03:00:00Z"
            with connect(database) as conn, conn:
                conn.execute(
                    """
                    INSERT INTO canonical_items(
                        canonical_key,source_id,item_kind,title,reference_no,project_name,
                        publication_date,deadline,location,url,content_hash,evidence_sha256,
                        payload_json,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "construction-project:ycc",
                        "S49",
                        "REGULATORY_NOTICE",
                        "Yadanabon Cyber City project approved for implementation",
                        "MOC-NEWS-YCC",
                        "Yadanabon Cyber City project",
                        "2026-09-01",
                        None,
                        "Myanmar",
                        "https://construction.gov.mm/new-detail/ycc",
                        "hash-ycc",
                        "a" * 64,
                        json.dumps(
                            {
                                "business_stage": "PROJECT_PRECURSOR_CANDIDATE",
                                "precursor_review_required": True,
                                "precursor_stage_hint": "APPROVAL",
                                "relevance_categories": ["TELECOM"],
                                "issuer": "Ministry of Construction, Myanmar",
                            }
                        ),
                        created_at,
                        created_at,
                    ),
                )
            promote_precursor_from_canonical(
                canonical_key="construction-project:ycc",
                project_key="yadanabon-cyber-city",
                stage="PROJECT_ANNOUNCEMENT",
                review_basis="reviewed exact project identity",
                reviewed_by="operator",
                database=database,
            )
            self._insert_tender(
                database,
                canonical_key="tender:ycc:before",
                publication_date="2026-08-31",
                created_at="2026-09-20T02:00:00Z",
                title="Yadanabon Cyber City water pipeline tender",
            )
            self._insert_tender(
                database,
                canonical_key="tender:ycc:after",
                publication_date="2026-09-20",
                created_at="2026-09-20T02:00:00Z",
                title="Water pipeline construction for Yadanabon Cyber City project",
            )
            self._insert_tender(
                database,
                canonical_key="tender:unrelated",
                publication_date="2026-09-21",
                created_at="2026-09-21T02:00:00Z",
                title="Mandalay highway drainage rehabilitation tender",
            )

            queue = procurement_link_suggestions(database=database)
            self.assertEqual(queue["summary"]["tracked_projects"], 1)
            self.assertEqual(queue["summary"]["already_linked_projects"], 0)
            self.assertEqual(queue["summary"]["projects_with_suggestions"], 1)
            self.assertEqual(queue["summary"]["suggestions"], 1)
            row = queue["suggestions"][0]
            self.assertEqual(row["project_key"], "yadanabon-cyber-city")
            self.assertEqual(row["procurement_canonical_key"], "tender:ycc:after")
            self.assertNotEqual(row["procurement_canonical_key"], "tender:ycc:before")
            self.assertEqual(row["authority"], "REVIEW_ONLY_NO_LINK_WRITE")
            self.assertIn("yadanabon", row["evidence"]["shared_identity_terms"])
            self.assertTrue(queue["semantics"]["suggestion_score_is_ranking_not_probability"])

            with connect(database) as conn:
                count = conn.execute("SELECT COUNT(*) FROM project_procurement_links").fetchone()[0]
            self.assertEqual(count, 0)

            link_procurement(
                project_key="yadanabon-cyber-city",
                canonical_key="tender:ycc:after",
                link_basis="human reviewed exact Yadanabon Cyber City identity",
                database=database,
            )
            queue = procurement_link_suggestions(database=database)
            self.assertEqual(queue["summary"]["already_linked_projects"], 1)
            self.assertEqual(queue["summary"]["unlinked_projects"], 0)
            self.assertEqual(queue["summary"]["suggestions"], 0)

    def test_procurement_link_suggestions_allow_cross_sector_pinpet_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            created_at = "2026-09-01T04:00:00Z"
            precursor_title = (
                "ပင်းပက် သံမဏိစက်ရုံအတွင်း တည်ဆောက်မည့် "
                "ကျောက်မီးသွေးသုံးရေနွေးငွေ့ဓာတ်အားပေးစက်ရုံ အခြေအနေ"
            )
            with connect(database) as conn, conn:
                conn.execute(
                    """
                    INSERT INTO canonical_items(
                        canonical_key,source_id,item_kind,title,reference_no,project_name,
                        publication_date,deadline,location,url,content_hash,evidence_sha256,
                        payload_json,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "moee-project:7133:pinpet",
                        "S50",
                        "REGULATORY_NOTICE",
                        precursor_title,
                        "MOEE-NEWS-7133-pinpet",
                        precursor_title,
                        "2026-08-30",
                        None,
                        "Myanmar",
                        "https://moep.gov.mm/mm/ignite/contentView/7133",
                        "hash-pinpet",
                        "b" * 64,
                        json.dumps(
                            {
                                "business_stage": "PROJECT_PRECURSOR_CANDIDATE",
                                "precursor_review_required": True,
                                "precursor_stage_hint": "PROJECT_ANNOUNCEMENT",
                                "relevance_categories": ["ENERGY"],
                                "issuer": "Ministry of Electricity and Energy, Myanmar",
                            },
                            ensure_ascii=False,
                        ),
                        created_at,
                        created_at,
                    ),
                )
            promote_precursor_from_canonical(
                canonical_key="moee-project:7133:pinpet",
                project_key="pinpet-steel-factory-power",
                stage="PROJECT_ANNOUNCEMENT",
                review_basis="reviewed Pinpet named asset",
                reviewed_by="operator",
                database=database,
            )
            self._insert_tender(
                database,
                canonical_key="industry:pinpet:pump-house",
                publication_date="2026-09-18",
                created_at="2026-09-18T02:00:00Z",
                title="အမှတ်(၂)သံမဏိစက်ရုံ(ပင်းပက်)စီမံကိန်း Pump House equipment tender",
            )

            queue = procurement_link_suggestions(database=database)
            self.assertEqual(queue["summary"]["suggestions"], 1)
            row = queue["suggestions"][0]
            self.assertEqual(row["procurement_canonical_key"], "industry:pinpet:pump-house")
            self.assertIn("ပင်းပက်", row["evidence"]["shared_identity_terms"])
            self.assertIn("သံမဏိစက်ရုံ", row["evidence"]["shared_identity_terms"])
            self.assertFalse(row["evidence"]["sector_match"])

    def test_procurement_link_suggestions_reject_location_and_sector_as_identity_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            created_at = "2026-09-01T02:00:00Z"
            with connect(database) as conn, conn:
                conn.execute(
                    """
                    INSERT INTO canonical_items(
                        canonical_key,source_id,item_kind,title,reference_no,project_name,
                        publication_date,deadline,location,url,content_hash,evidence_sha256,
                        payload_json,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "moi-project:npt-grid",
                        "S48",
                        "REGULATORY_NOTICE",
                        "New 230kV substation will be constructed in Naypyidaw",
                        "MOI-NEWS-NPT",
                        "New 230kV substation in Naypyidaw",
                        "2026-09-01",
                        None,
                        "Naypyidaw",
                        "https://www.moi.gov.mm/news/npt-grid",
                        "hash-npt",
                        "a" * 64,
                        json.dumps(
                            {
                                "business_stage": "PROJECT_PRECURSOR_CANDIDATE",
                                "precursor_review_required": True,
                                "precursor_stage_hint": "PROJECT_ANNOUNCEMENT",
                                "relevance_categories": ["ENERGY"],
                                "issuer": "Ministry of Electricity and Energy, Myanmar",
                                "project_location_hint": "Naypyidaw",
                            }
                        ),
                        created_at,
                        created_at,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO canonical_items(
                        canonical_key,source_id,item_kind,title,reference_no,project_name,
                        publication_date,deadline,location,url,content_hash,evidence_sha256,
                        payload_json,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "tender:npt-transformer",
                        "S39",
                        "TENDER",
                        "Transformer supply tender for Naypyidaw electricity works",
                        "T-NPT-1",
                        "Transformer supply in Naypyidaw",
                        "2026-09-20",
                        "2026-10-20",
                        "Naypyidaw",
                        "https://official.test/tender:npt-transformer",
                        "hash-tender-npt",
                        "b" * 64,
                        json.dumps(
                            {
                                "business_stage": "OPPORTUNITY",
                                "relevance_categories": ["ENERGY"],
                                "issuer": "Ministry of Electricity and Energy, Myanmar",
                                "project_location_hint": "Naypyidaw",
                                "scope_summary": "Supply transformers for Naypyidaw electricity works",
                            }
                        ),
                        "2026-09-20T02:00:00Z",
                        "2026-09-20T02:00:00Z",
                    ),
                )

            promote_precursor_from_canonical(
                canonical_key="moi-project:npt-grid",
                project_key="naypyidaw-grid-upgrade",
                stage="PROJECT_ANNOUNCEMENT",
                review_basis="reviewed named grid project",
                reviewed_by="operator",
                database=database,
            )
            queue = procurement_link_suggestions(database=database)
            self.assertEqual(queue["summary"]["tracked_projects"], 1)
            self.assertEqual(queue["summary"]["suggestions"], 0)

    def test_procurement_link_suggestions_reject_generic_asset_only_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            record_project_event(
                project_key="grid-upgrade",
                source_id="S50",
                stage="PROJECT_ANNOUNCEMENT",
                title="New 230kV substation project",
                detected_at=datetime(2026, 9, 1, 2, 0, tzinfo=UTC),
                database=database,
            )
            self._insert_tender(
                database,
                canonical_key="tender:generic-substation",
                publication_date="2026-09-20",
                created_at="2026-09-20T02:00:00Z",
                title="New 230kV substation construction tender",
            )

            queue = procurement_link_suggestions(database=database)
            self.assertEqual(queue["summary"]["tracked_projects"], 1)
            self.assertEqual(queue["summary"]["suggestions"], 0)


if __name__ == "__main__":
    unittest.main()
