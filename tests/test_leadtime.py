from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.db import connect, migrate
from signalforge.leadtime import leadtime_report, link_procurement, record_project_event


class ProjectLeadtimeTests(unittest.TestCase):
    def test_measures_days_from_first_precursor_to_procurement_creation(self) -> None:
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
                        "tender:bridge-1","S43","TENDER","Bridge rehabilitation tender","BR-1",
                        "Bridge rehabilitation","2026-09-20","2026-10-20",None,
                        "https://official.test/tender","hash","sha",
                        json.dumps({"business_stage":"OPPORTUNITY"}),
                        "2026-09-20T02:00:00Z","2026-09-20T02:00:00Z",
                    ),
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
            row = report["projects"][0]
            self.assertEqual(row["first_stage"], "PROJECT_ANNOUNCEMENT")
            self.assertEqual(row["lead_days"], 30.0)

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
