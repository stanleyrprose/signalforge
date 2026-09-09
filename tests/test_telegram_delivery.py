from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signalforge.db import connect, migrate
from signalforge.telegram_delivery import TelegramDeliveryError, render_telegram_message, telegram_deliver


def _briefing(*, signal_id: str = "sig-1", action: str = "PRIORITIZE") -> dict[str, object]:
    return {
        "status": "PASS",
        "attention": [
            {
                "canonical_key": "mofa:1",
                "attention_action": action,
                "priority_band": "HIGH",
                "trust_grade": "A",
                "primary_relevance": "ICT",
                "relevance_categories": ["ICT"],
                "urgency": "URGENT" if action == "ACT_NOW" else "NORMAL",
                "issuer": "Ministry <Foreign> & Affairs",
                "title": "Data Server & SQL <Tender>",
                "reference_no": "MOFA-1",
                "reference_numbers": None,
                "deadline": "2026-09-18",
                "deadline_time": "16:30",
                "deadline_at": "2026-09-18T16:30:00+06:30",
                "deadline_status": "OPEN",
                "evidence_level": "OFFICIAL_HTML_PLUS_TEXT_PDF",
                "completeness": "FULL",
                "scope_excerpt": "Dell PowerEdge, Windows Server, SQL Server and installation.",
                "why_now": ["STRATEGIC_FIT_ICT_TELECOM", "A_GRADE_BUSINESS_EVIDENCE"],
                "latest_signal_id": signal_id,
                "latest_signal_type": "NEW",
                "latest_signal_at": "2026-09-09T10:00:00Z",
                "signal_count": 1,
                "url": "https://example.test/a?x=1&y=2",
            }
        ],
    }


class TelegramDeliveryTests(unittest.TestCase):
    def test_dry_run_needs_no_credentials_and_does_not_write_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing()):
                result = telegram_deliver(database=database, dry_run=True)
            self.assertEqual(result["pending_count"], 1)
            self.assertTrue(result["dry_run"])
            with connect(database) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM delivery_receipts").fetchone()[0], 0)

    def test_success_receipt_deduplicates_same_signal_and_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing()), patch(
                "signalforge.telegram_delivery._send_message", return_value="101"
            ) as send:
                first = telegram_deliver(database=database, bot_token="secret", chat_id="42")
                second = telegram_deliver(database=database, bot_token="secret", chat_id="42")
            self.assertEqual(first["sent_count"], 1)
            self.assertEqual(second["sent_count"], 0)
            self.assertEqual(send.call_count, 1)
            with connect(database) as conn:
                row = conn.execute("SELECT signal_id,attention_action,provider_message_id FROM delivery_receipts").fetchone()
                self.assertEqual(tuple(row), ("sig-1", "PRIORITIZE", "101"))

    def test_action_upgrade_with_same_signal_is_delivered_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery._send_message", return_value="101"):
                with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing(action="PRIORITIZE")):
                    telegram_deliver(database=database, bot_token="secret", chat_id="42")
                with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing(action="ACT_NOW")):
                    upgraded = telegram_deliver(database=database, bot_token="secret", chat_id="42")
                    repeated = telegram_deliver(database=database, bot_token="secret", chat_id="42")
            self.assertEqual(upgraded["sent_count"], 1)
            self.assertEqual(repeated["sent_count"], 0)
            with connect(database) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM delivery_receipts").fetchone()[0], 2)

    def test_new_signal_same_action_is_delivered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery._send_message", return_value="101"):
                with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing(signal_id="sig-1")):
                    telegram_deliver(database=database, bot_token="secret", chat_id="42")
                with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing(signal_id="sig-2")):
                    result = telegram_deliver(database=database, bot_token="secret", chat_id="42")
            self.assertEqual(result["sent_count"], 1)

    def test_failed_transport_does_not_create_success_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing()), patch(
                "signalforge.telegram_delivery._send_message", side_effect=TelegramDeliveryError("telegram transport failed")
            ):
                with self.assertRaises(TelegramDeliveryError):
                    telegram_deliver(database=database, bot_token="secret", chat_id="42")
            with connect(database) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM delivery_receipts").fetchone()[0], 0)

    def test_message_is_html_escaped_and_bounded(self) -> None:
        item = _briefing()["attention"][0]
        assert isinstance(item, dict)
        item["scope_excerpt"] = "x" * 10000
        text = render_telegram_message(item)
        self.assertLessEqual(len(text), 4096)
        self.assertIn("🔴 <b>优先关注</b> · HIGH · A级 · ICT", text)
        self.assertIn("🏛 买方：Ministry &lt;Foreign&gt; &amp; Affairs", text)
        self.assertIn("Data Server &amp; SQL &lt;Tender&gt;", text)
        self.assertIn("⏰ 截止：<b>2026-09-18 16:30</b>", text)
        self.assertIn("🔎 证据：官方 HTML + 官方文本 PDF", text)
        self.assertIn("📡 Signal：NEW", text)
        self.assertIn("🔗 <a href=", text)
        scope_line = next(line for line in text.splitlines() if line.startswith("📦 范围："))
        self.assertLessEqual(scope_line.count("x"), 240)
        self.assertNotIn("<Foreign>", text)

    def test_action_labels_are_compact_and_deterministic(self) -> None:
        expected = {
            "ACT_NOW": "立即行动",
            "PRIORITIZE": "优先关注",
            "REVIEW": "人工复核",
        }
        for action, label in expected.items():
            item = _briefing(action=action)["attention"][0]
            assert isinstance(item, dict)
            text = render_telegram_message(item)
            self.assertIn(f"<b>{label}</b>", text)

    def test_credentials_required_only_for_real_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing()):
                with self.assertRaisesRegex(TelegramDeliveryError, "credentials are not configured"):
                    telegram_deliver(database=database)


if __name__ == "__main__":
    unittest.main()
