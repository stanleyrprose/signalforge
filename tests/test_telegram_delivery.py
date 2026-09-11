from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
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

    def test_deadline_crossing_72h_escalates_same_signal_without_source_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            payload = {
                "item_kind": "TENDER",
                "business_stage": "OPPORTUNITY",
                "issuer": "Ministry of Industry, Myanmar",
                "title": "Industrial chemical supply tender",
                "project_name": "Industrial chemical supply tender",
                "reference_no": "INDUSTRY-TEST-72H",
                "publication_date": "2026-09-01",
                "deadline": "2026-09-14",
                "deadline_time": "16:00",
                "deadline_evidence": "EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME",
                "scope_summary": "Chemical materials for industrial production and plant operations.",
                "detail_completeness": "HTML_BUSINESS_SCOPE_AND_DEADLINE_NO_ATTACHMENT_REQUIRED",
                "url": "https://www.industrymsme.gov.mm/announcements/test-72h",
            }
            with connect(database) as conn, conn:
                conn.execute(
                    """
                    INSERT INTO canonical_items(
                        canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,
                        content_hash,evidence_sha256,payload_json,created_at,updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "industry:test-72h",
                        "S38",
                        "TENDER",
                        payload["title"],
                        payload["reference_no"],
                        payload["project_name"],
                        payload["publication_date"],
                        payload["deadline"],
                        None,
                        payload["url"],
                        "hash-test-72h",
                        "evidence-test-72h",
                        json.dumps(payload, sort_keys=True),
                        "2026-09-09T00:00:00Z",
                        "2026-09-09T00:00:00Z",
                    ),
                )
                conn.execute(
                    "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                    (
                        "sig-test-72h",
                        "S38",
                        "industry:test-72h",
                        "NEW",
                        "2026-09-09T00:00:00Z",
                        json.dumps({"signal_type": "NEW", "canonical_key": "industry:test-72h"}, sort_keys=True),
                    ),
                )

            before_threshold = datetime(2026, 9, 11, 9, 29, tzinfo=UTC)
            after_threshold = datetime(2026, 9, 11, 9, 31, tzinfo=UTC)
            with patch("signalforge.telegram_delivery._send_message", return_value="202") as send:
                before = telegram_deliver(
                    database=database,
                    now=before_threshold,
                    bot_token="secret",
                    chat_id="42",
                )
                upgraded = telegram_deliver(
                    database=database,
                    now=after_threshold,
                    bot_token="secret",
                    chat_id="42",
                )
                repeated = telegram_deliver(
                    database=database,
                    now=after_threshold,
                    bot_token="secret",
                    chat_id="42",
                )

            self.assertEqual(before["sent_count"], 0)
            self.assertEqual(upgraded["sent_count"], 1)
            self.assertEqual(repeated["sent_count"], 0)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(upgraded["sent"][0]["canonical_key"], "industry:test-72h")
            self.assertEqual(upgraded["sent"][0]["attention_action"], "ACT_NOW")
            with connect(database) as conn:
                row = conn.execute(
                    "SELECT signal_id,attention_action,priority_band FROM delivery_receipts WHERE canonical_key='industry:test-72h'"
                ).fetchone()
            self.assertEqual(tuple(row), ("sig-test-72h", "ACT_NOW", "HIGH"))

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

    def test_focus_references_are_rendered_separately_from_full_reference_bundle(self) -> None:
        item = _briefing()["attention"][0]
        assert isinstance(item, dict)
        item["reference_numbers"] = ["DMP/L-026(26-27)", "DMP/L-040(26-27)", "DMP/L-067(26-27)"]
        item["focus_reference_numbers"] = ["DMP/L-026(26-27)", "DMP/L-067(26-27)"]
        item["scope_excerpt"] = "DMP/L-026 Communication and Information Technology | DMP/L-067 IOT Module"
        text = render_telegram_message(item)
        self.assertIn("📌 编号：DMP/L-026(26-27), DMP/L-040(26-27), DMP/L-067(26-27)", text)
        self.assertIn("🧩 相关分包：DMP/L-026(26-27), DMP/L-067(26-27)", text)
        self.assertIn("📦 范围：DMP/L-026 Communication and Information Technology | DMP/L-067 IOT Module", text)

    def test_ptd_participation_deadline_is_not_rendered_as_generic_bid_deadline(self) -> None:
        item = _briefing()["attention"][0]
        assert isinstance(item, dict)
        item["deadline_kind"] = "TENDER_FORM_SALE_CLOSE"
        item["tender_opening_date"] = "2026-09-20"
        item["tender_opening_time"] = "13:30"
        text = render_telegram_message(item)
        self.assertIn("⏰ 获取标书截止：<b>2026-09-18 16:30</b>", text)
        self.assertIn("🗓 开标：<b>2026-09-20 13:30</b>", text)
        self.assertNotIn("⏰ 截止：", text)

    def test_deadline_kind_labels_distinguish_bid_and_application_close(self) -> None:
        item = _briefing()["attention"][0]
        assert isinstance(item, dict)
        item["deadline_kind"] = "BID_SUBMISSION_DEADLINE"
        self.assertIn("⏰ 投标截止：<b>2026-09-18 16:30</b>", render_telegram_message(item))
        item["deadline_kind"] = "TENDER_APPLICATION_ACCEPTANCE_CLOSE"
        self.assertIn("⏰ 投标申请接收截止：<b>2026-09-18 16:30</b>", render_telegram_message(item))


    def test_commercial_tender_sale_renders_seller_and_action_date_without_fake_deadline(self) -> None:
        item = _briefing(action="REVIEW")["attention"][0]
        assert isinstance(item, dict)
        item.update({
            "item_kind": "AUCTION_NOTICE",
            "commercial_direction": "BUY_FROM_ISSUER",
            "issuer": "Myanma Timber Enterprise",
            "title": "Local Marketing and Milling Department, Open Tender No (6/2026-2027)(15.9.2026)",
            "reference_no": "MTE-LOCAL-6/2026-2027",
            "deadline": None,
            "deadline_time": None,
            "deadline_status": "UNKNOWN",
            "action_date": "2026-09-15",
            "action_time": None,
            "why_now": ["COMMERCIAL_EVENT_DATE_KNOWN", "TRUSTED_EVENT_PARTIAL_ACTIONABILITY"],
            "scope_excerpt": "Official commercial tender event; image supplement carries lot details.",
            "primary_relevance": "OTHER",
            "priority_band": "REVIEW",
            "trust_grade": "B",
            "signal_quality_score": 59,
            "signal_quality_band": "MEDIUM",
        })
        text = render_telegram_message(item)
        self.assertIn("🏛 卖方：Myanma Timber Enterprise", text)
        self.assertIn("🗓 活动日：<b>2026-09-15</b>", text)
        self.assertIn("🧭 Signal质量：<b>59/100 · MEDIUM</b>", text)
        self.assertNotIn("⏰ 截止：", text)
        self.assertIn("官方商业活动日期明确", text)
        self.assertIn("事件可信但行动信息不完整", text)

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
