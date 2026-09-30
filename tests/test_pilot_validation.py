from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.db import connect, migrate
from signalforge.pilot_validation import PilotFeedbackError, pilot_validation_report, record_pilot_feedback


class PilotValidationTests(unittest.TestCase):
    def _seed(self, database: Path) -> None:
        migrate(database)
        with connect(database) as conn, conn:
            conn.execute(
                """
                INSERT INTO canonical_items(
                    canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,
                    deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "mpt:pilot-1",
                    "S13",
                    "TENDER",
                    "Pilot telecom tender",
                    "MPT-PILOT-1",
                    "Pilot telecom tender",
                    "2026-09-29",
                    "2026-10-10",
                    "Yangon",
                    "https://example.test/tender",
                    "hash-1",
                    "evidence-1",
                    json.dumps({"item_kind": "TENDER"}),
                    "2026-09-29T00:00:00Z",
                    "2026-09-29T00:00:00Z",
                ),
            )
            conn.execute(
                "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                ("sig-pilot-1", "S13", "mpt:pilot-1", "NEW", "2026-09-29T00:00:00Z", "{}"),
            )
            conn.execute(
                """
                INSERT INTO delivery_receipts(
                    delivery_key,channel,canonical_key,signal_id,attention_action,priority_band,
                    payload_sha256,provider_message_id,sent_at,profile_id,profile_match_score
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "delivery-1",
                    "telegram",
                    "mpt:pilot-1",
                    "sig-pilot-1",
                    "PRIORITIZE",
                    "HIGH",
                    "payload-1",
                    "1001",
                    "2026-09-29T00:01:00Z",
                    "pilot-ict",
                    75,
                ),
            )

    def test_feedback_requires_attributed_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            self._seed(database)
            with self.assertRaises(PilotFeedbackError):
                record_pilot_feedback(
                    profile_id="other-profile",
                    canonical_key="mpt:pilot-1",
                    signal_id="sig-pilot-1",
                    event_type="ACTION_TAKEN",
                    database=database,
                )

    def test_feedback_is_idempotent_and_report_tracks_business_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            self._seed(database)
            fixed_now = datetime(2026, 9, 29, 1, 0, tzinfo=UTC)

            for event_type in ("WORTH_REVIEWING", "ACTION_TAKEN", "BID_OR_QUOTE_INITIATED"):
                record_pilot_feedback(
                    profile_id="pilot-ict",
                    canonical_key="mpt:pilot-1",
                    signal_id="sig-pilot-1",
                    event_type=event_type,
                    note="pilot customer confirmed",
                    database=database,
                    now=fixed_now,
                )

            duplicate = record_pilot_feedback(
                profile_id="pilot-ict",
                canonical_key="mpt:pilot-1",
                signal_id="sig-pilot-1",
                event_type="ACTION_TAKEN",
                database=database,
                now=fixed_now,
            )
            self.assertEqual(duplicate["status"], "PASS")

            report = pilot_validation_report(profile_id="pilot-ict", database=database)
            self.assertEqual(report["unique_tenders_delivered"], 1)
            self.assertEqual(report["profiles_with_attributed_delivery"], 1)
            self.assertEqual(report["worth_reviewing_rate"], 1.0)
            self.assertEqual(report["action_rate"], 1.0)
            self.assertEqual(report["bid_or_quote_rate"], 1.0)
            self.assertEqual(report["feedback_by_type"]["ACTION_TAKEN"]["events"], 1)
            self.assertEqual(len(report["recent_feedback"]), 3)

    def test_invalid_event_type_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            self._seed(database)
            with self.assertRaises(PilotFeedbackError):
                record_pilot_feedback(
                    profile_id="pilot-ict",
                    canonical_key="mpt:pilot-1",
                    event_type="LIKED_IT",
                    database=database,
                )


if __name__ == "__main__":
    unittest.main()
