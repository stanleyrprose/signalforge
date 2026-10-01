from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.db import connect, migrate
from signalforge.pilot_validation import pilot_validation_report
from signalforge.telegram_feedback import (
    TelegramFeedbackError,
    feedback_callback_data,
    feedback_reply_markup,
    record_feedback_callback,
    telegram_feedback_poll,
)


class TelegramFeedbackTests(unittest.TestCase):
    def _seed(self, database: Path) -> str:
        migrate(database)
        delivery_key = "a" * 64
        with connect(database) as conn, conn:
            conn.execute(
                """
                INSERT INTO canonical_items(
                    canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,
                    deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "mpt:feedback-1",
                    "S13",
                    "TENDER",
                    "Pilot telecom tender",
                    "MPT-FEEDBACK-1",
                    "Pilot telecom tender",
                    "2026-10-01",
                    "2026-10-10",
                    "Yangon",
                    "https://example.test/tender",
                    "hash-feedback-1",
                    "evidence-feedback-1",
                    json.dumps({"item_kind": "TENDER"}),
                    "2026-10-01T00:00:00Z",
                    "2026-10-01T00:00:00Z",
                ),
            )
            conn.execute(
                "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                ("sig-feedback-1", "S13", "mpt:feedback-1", "NEW", "2026-10-01T00:00:00Z", "{}"),
            )
            conn.execute(
                """
                INSERT INTO pilot_delivery_receipts(
                    delivery_key,channel,profile_id,canonical_key,signal_id,attention_action,
                    priority_band,profile_match_score,payload_sha256,provider_message_id,sent_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    delivery_key,
                    "telegram",
                    "pilot-ict",
                    "mpt:feedback-1",
                    "sig-feedback-1",
                    "PRIORITIZE",
                    "HIGH",
                    80,
                    "payload-feedback-1",
                    "1001",
                    "2026-10-01T00:01:00Z",
                ),
            )
        return delivery_key

    def _callback(
        self,
        delivery_key: str,
        event_type: str,
        *,
        callback_id: str = "callback-1",
    ) -> dict[str, object]:
        return {
            "id": callback_id,
            "from": {"id": 42, "username": "pilot_user"},
            "message": {"message_id": 1001},
            "data": feedback_callback_data(delivery_key, event_type),
        }

    def test_markup_is_compact_and_contains_three_pilot_actions(self) -> None:
        markup = feedback_reply_markup("a" * 64)
        rows = markup["inline_keyboard"]
        assert isinstance(rows, list)
        buttons = [button for row in rows for button in row]
        self.assertEqual(
            [button["text"] for button in buttons],
            ["👍 Relevant", "👎 Not Relevant", "🚀 Took Action"],
        )
        self.assertTrue(all(len(str(button["callback_data"]).encode("utf-8")) <= 64 for button in buttons))

    def test_callback_records_into_existing_pilot_validation_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            delivery_key = self._seed(database)

            result = record_feedback_callback(
                self._callback(delivery_key, "RELEVANT"),
                database=database,
                now=datetime(2026, 10, 1, 1, 0, tzinfo=UTC),
            )

            self.assertEqual(result["status"], "RECORDED")
            self.assertEqual(result["event_type"], "RELEVANT")
            report = pilot_validation_report(profile_id="pilot-ict", database=database)
            self.assertEqual(report["relevance_response_rate"], 1.0)
            self.assertEqual(report["relevant_rate"], 1.0)

    def test_relevance_callback_can_be_replaced_by_not_relevant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            delivery_key = self._seed(database)

            record_feedback_callback(
                self._callback(delivery_key, "RELEVANT", callback_id="callback-r"),
                database=database,
            )
            record_feedback_callback(
                self._callback(delivery_key, "NOT_RELEVANT", callback_id="callback-n"),
                database=database,
            )

            with connect(database) as conn:
                events = [
                    row["event_type"]
                    for row in conn.execute(
                        "SELECT event_type FROM pilot_feedback_events WHERE profile_id='pilot-ict' ORDER BY event_type"
                    )
                ]
            self.assertNotIn("RELEVANT", events)
            self.assertIn("NOT_RELEVANT", events)

    def test_callback_message_must_match_delivery_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            delivery_key = self._seed(database)
            callback = self._callback(delivery_key, "ACTION_TAKEN")
            callback["message"] = {"message_id": 9999}

            with self.assertRaisesRegex(TelegramFeedbackError, "does not match"):
                record_feedback_callback(callback, database=database)

    def test_poll_fails_closed_when_webhook_is_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch(
                "signalforge.telegram_feedback._telegram_api",
                return_value={"url": "https://example.test/telegram-webhook"},
            ):
                with self.assertRaisesRegex(TelegramFeedbackError, "webhook is configured"):
                    telegram_feedback_poll(
                        database=database,
                        bot_token="[REDACTED_SECRET]",
                    )

    def test_poll_records_callback_answers_and_persists_update_offset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            delivery_key = self._seed(database)
            callback = self._callback(delivery_key, "ACTION_TAKEN", callback_id="callback-action")
            calls: list[tuple[str, dict[str, object]]] = []

            def fake_api(
                *,
                bot_token: str,
                method: str,
                payload: dict[str, object],
                timeout: int = 15,
            ) -> object:
                calls.append((method, payload))
                if method == "getWebhookInfo":
                    return {"url": ""}
                if method == "getUpdates":
                    return [{"update_id": 77, "callback_query": callback}]
                if method == "answerCallbackQuery":
                    return True
                raise AssertionError(method)

            with patch("signalforge.telegram_feedback._telegram_api", side_effect=fake_api):
                result = telegram_feedback_poll(
                    database=database,
                    bot_token="[REDACTED_SECRET]",
                )

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["processed_count"], 1)
            self.assertEqual(result["last_update_id"], 77)
            self.assertEqual(
                [method for method, _payload in calls],
                ["getWebhookInfo", "getUpdates", "answerCallbackQuery"],
            )
            with connect(database) as conn:
                state = conn.execute("SELECT last_update_id FROM telegram_update_state").fetchone()
            self.assertEqual(state["last_update_id"], 77)

            report = pilot_validation_report(profile_id="pilot-ict", database=database)
            self.assertEqual(report["action_rate"], 1.0)

    def test_ack_failure_does_not_replay_durable_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            delivery_key = self._seed(database)
            callback = self._callback(delivery_key, "RELEVANT", callback_id="expired-callback")
            calls: list[tuple[str, dict[str, object]]] = []

            def fake_api(
                *,
                bot_token: str,
                method: str,
                payload: dict[str, object],
                timeout: int = 15,
            ) -> object:
                calls.append((method, payload))
                if method == "getWebhookInfo":
                    return {"url": ""}
                if method == "getUpdates":
                    return [{"update_id": 88, "callback_query": callback}]
                if method == "answerCallbackQuery":
                    raise TelegramFeedbackError("telegram answerCallbackQuery HTTP 400")
                raise AssertionError(method)

            with patch("signalforge.telegram_feedback._telegram_api", side_effect=fake_api):
                result = telegram_feedback_poll(
                    database=database,
                    bot_token="[REDACTED_SECRET]",
                )

            self.assertEqual(result["status"], "DEGRADED")
            self.assertEqual(result["processed_count"], 1)
            self.assertEqual(result["failed_count"], 0)
            self.assertEqual(result["ack_failed_count"], 1)
            self.assertEqual(result["last_update_id"], 88)

            with connect(database) as conn:
                state = conn.execute("SELECT last_update_id FROM telegram_update_state").fetchone()
                events = conn.execute(
                    "SELECT event_type,recorded_by FROM pilot_feedback_events WHERE profile_id='pilot-ict'"
                ).fetchall()
            self.assertEqual(state["last_update_id"], 88)
            self.assertEqual([(row["event_type"], row["recorded_by"].split(":")[0]) for row in events], [("RELEVANT", "telegram")])


if __name__ == "__main__":
    unittest.main()
