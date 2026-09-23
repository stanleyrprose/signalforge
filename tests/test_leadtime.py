from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.db import connect, migrate
from signalforge.leadtime import leadtime_report, link_procurement, record_project_event


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


if __name__ == "__main__":
    unittest.main()
