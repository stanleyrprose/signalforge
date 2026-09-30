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
                INSERT INTO pilot_delivery_receipts(
                    delivery_key,channel,profile_id,canonical_key,signal_id,attention_action,
                    priority_band,profile_match_score,payload_sha256,provider_message_id,sent_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "delivery-1",
                    "telegram",
                    "pilot-ict",
                    "mpt:pilot-1",
                    "sig-pilot-1",
                    "PRIORITIZE",
                    "HIGH",
                    75,
                    "payload-1",
                    "1001",
                    "2026-09-29T00:01:00Z",
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

    def test_feedback_dimensions_are_mutually_exclusive_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            self._seed(database)
            fixed_now = datetime(2026, 9, 29, 2, 0, tzinfo=UTC)

            for event_type in ("RELEVANT", "CLICKED", "WOULD_PAY"):
                record_pilot_feedback(
                    profile_id="pilot-ict",
                    canonical_key="mpt:pilot-1",
                    signal_id="sig-pilot-1",
                    event_type=event_type,
                    database=database,
                    now=fixed_now,
                )

            report = pilot_validation_report(profile_id="pilot-ict", database=database)
            self.assertEqual(report["relevance_response_rate"], 1.0)
            self.assertEqual(report["relevant_rate"], 1.0)
            self.assertEqual(report["engagement_response_rate"], 1.0)
            self.assertEqual(report["clicked_rate"], 1.0)
            self.assertEqual(report["pay_intent_response_rate"], 1.0)
            self.assertEqual(report["would_pay_rate"], 1.0)

            record_pilot_feedback(
                profile_id="pilot-ict",
                canonical_key="mpt:pilot-1",
                signal_id="sig-pilot-1",
                event_type="NOT_RELEVANT",
                database=database,
                now=fixed_now,
            )
            with connect(database) as conn:
                rows = [
                    row["event_type"]
                    for row in conn.execute(
                        """
                        SELECT event_type FROM pilot_feedback_events
                        WHERE profile_id='pilot-ict' AND canonical_key='mpt:pilot-1'
                        ORDER BY event_type
                        """
                    )
                ]
            self.assertNotIn("RELEVANT", rows)
            self.assertIn("NOT_RELEVANT", rows)
            self.assertIn("CLICKED", rows)
            self.assertIn("WOULD_PAY", rows)

            report = pilot_validation_report(profile_id="pilot-ict", database=database)
            self.assertEqual(report["relevance_response_rate"], 1.0)
            self.assertEqual(report["relevant_rate"], 0.0)
            self.assertEqual(report["clicked_rate"], 1.0)
            self.assertEqual(report["would_pay_rate"], 1.0)

    def test_owner_feed_receipts_are_excluded_from_pilot_denominator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                conn.execute(
                    """
                    INSERT INTO delivery_receipts(
                        delivery_key,channel,canonical_key,signal_id,attention_action,priority_band,
                        payload_sha256,provider_message_id,sent_at,profile_id,profile_match_score
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "owner-delivery",
                        "telegram",
                        "owner:tender",
                        "owner-signal",
                        "PRIORITIZE",
                        "HIGH",
                        "payload-owner",
                        "2001",
                        "2026-09-29T00:02:00Z",
                        None,
                        None,
                    ),
                )

            report = pilot_validation_report(database=database)
            self.assertEqual(report["delivery_count"], 0)
            self.assertEqual(report["unique_tenders_delivered"], 0)
            self.assertEqual(report["profiles_with_attributed_delivery"], 0)
            self.assertIsNone(report["worth_reviewing_rate"])
            self.assertIsNone(report["action_rate"])
            self.assertIsNone(report["bid_or_quote_rate"])

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
