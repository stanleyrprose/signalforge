from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.business_profile import BusinessProfile
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
                "quantity_or_lot_summary": "2 servers plus installation service.",
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
    def setUp(self) -> None:
        self._translation_patch = patch(
            "signalforge.telegram_delivery.translate_tender_fields_to_zh_hans",
            side_effect=lambda values, **_kwargs: (values, False),
        )
        self._translation_patch.start()

    def tearDown(self) -> None:
        self._translation_patch.stop()

    def test_matched_only_profile_filters_irrelevant_tender_before_delivery(self) -> None:
        profile = BusinessProfile.from_dict(
            {
                "profile_id": "medical-only",
                "delivery_mode": "MATCHED_ONLY",
                "relevance_categories": ["MEDICAL"],
                "keywords": ["surgical"],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing()):
                result = telegram_deliver(database=database, dry_run=True, business_profile=profile)
        self.assertEqual(result["pending_count"], 0)
        self.assertEqual(result["signal_pending_count"], 0)
        self.assertEqual(result["filtered_out_count"], 1)
        self.assertEqual(result["business_profile_id"], "medical-only")
        self.assertEqual(result["business_profile_delivery_mode"], "MATCHED_ONLY")

    def test_matching_profile_adds_customer_relevance_to_message(self) -> None:
        profile = BusinessProfile.from_dict(
            {
                "profile_id": "ict-pilot",
                "delivery_mode": "MATCHED_ONLY",
                "relevance_categories": ["ICT"],
                "keywords": ["server"],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing()):
                result = telegram_deliver(database=database, dry_run=True, business_profile=profile)
        self.assertEqual(result["pending_count"], 1)
        self.assertEqual(result["filtered_out_count"], 0)
        pending = result["pending"][0]
        self.assertEqual(pending["business_profile_id"], "ict-pilot")
        self.assertGreaterEqual(pending["business_profile_match_score"], 45)
        self.assertIn("🎯 与你业务关联：", pending["message"])
        self.assertIn("ICT", pending["message"])


    def test_real_profile_delivery_persists_profile_attribution(self) -> None:
        profile = BusinessProfile.from_dict(
            {
                "profile_id": "ict-pilot",
                "delivery_mode": "MATCHED_ONLY",
                "relevance_categories": ["ICT"],
                "keywords": ["server"],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing()), patch(
                "signalforge.telegram_delivery._send_message", return_value="303"
            ):
                result = telegram_deliver(
                    database=database,
                    bot_token="secret",
                    chat_id="42",
                    business_profile=profile,
                )
            self.assertEqual(result["sent_count"], 1)
            with connect(database) as conn:
                row = conn.execute(
                    "SELECT profile_id,profile_match_score FROM pilot_delivery_receipts WHERE canonical_key='mofa:1'"
                ).fetchone()
            self.assertEqual(row["profile_id"], "ict-pilot")
            self.assertGreaterEqual(int(row["profile_match_score"]), 45)

    def test_same_signal_can_be_delivered_once_to_each_pilot_profile(self) -> None:
        profile_a = BusinessProfile.from_dict(
            {
                "profile_id": "ict-pilot-a",
                "delivery_mode": "MATCHED_ONLY",
                "relevance_categories": ["ICT"],
                "keywords": ["server"],
            }
        )
        profile_b = BusinessProfile.from_dict(
            {
                "profile_id": "ict-pilot-b",
                "delivery_mode": "MATCHED_ONLY",
                "relevance_categories": ["ICT"],
                "keywords": ["server"],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing()), patch(
                "signalforge.telegram_delivery._send_message", return_value="404"
            ) as send:
                first = telegram_deliver(
                    database=database,
                    bot_token="secret",
                    chat_id="chat-a",
                    business_profile=profile_a,
                )
                second = telegram_deliver(
                    database=database,
                    bot_token="secret",
                    chat_id="chat-b",
                    business_profile=profile_b,
                )
                repeated_a = telegram_deliver(
                    database=database,
                    bot_token="secret",
                    chat_id="chat-a",
                    business_profile=profile_a,
                )
            self.assertEqual(first["sent_count"], 1)
            self.assertEqual(second["sent_count"], 1)
            self.assertEqual(repeated_a["sent_count"], 0)
            self.assertEqual(send.call_count, 2)
            with connect(database) as conn:
                profiles = [
                    row["profile_id"]
                    for row in conn.execute(
                        "SELECT profile_id FROM pilot_delivery_receipts ORDER BY profile_id"
                    )
                ]
                owner_receipts = conn.execute("SELECT COUNT(*) FROM delivery_receipts").fetchone()[0]
            self.assertEqual(profiles, ["ict-pilot-a", "ict-pilot-b"])
            self.assertEqual(owner_receipts, 0)

    def test_pilot_readiness_rejects_unknown_deadline(self) -> None:
        profile = BusinessProfile.from_dict(
            {"profile_id": "ict-pilot", "delivery_mode": "MATCHED_ONLY", "relevance_categories": ["ICT"]}
        )
        briefing = _briefing()
        briefing["attention"][0]["deadline_status"] = "UNKNOWN"
        briefing["attention"][0]["deadline"] = None
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=briefing):
                result = telegram_deliver(database=database, dry_run=True, business_profile=profile)
        self.assertEqual(result["pending_count"], 0)
        self.assertEqual(result["quality_filtered_count"], 1)
        self.assertIn("DEADLINE_NOT_CONFIRMED_OPEN", result["quality_filtered"][0]["reasons"])

    def test_pilot_readiness_rejects_missing_quantity_or_scale(self) -> None:
        profile = BusinessProfile.from_dict(
            {"profile_id": "ict-pilot", "delivery_mode": "MATCHED_ONLY", "relevance_categories": ["ICT"]}
        )
        briefing = _briefing()
        briefing["attention"][0]["quantity_or_lot_summary"] = None
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=briefing):
                result = telegram_deliver(database=database, dry_run=True, business_profile=profile)
        self.assertEqual(result["pending_count"], 0)
        self.assertIn("QUANTITY_OR_SCALE_NOT_EXPLAINED", result["quality_filtered"][0]["reasons"])

    def test_real_pilot_delivery_fails_closed_when_myanmar_remains(self) -> None:
        profile = BusinessProfile.from_dict(
            {"profile_id": "ict-pilot", "delivery_mode": "MATCHED_ONLY", "relevance_categories": ["ICT"]}
        )
        briefing = _briefing()
        briefing["attention"][0]["title"] = "အိတ်ဖွင့်တင်ဒါ"
        briefing["attention"][0]["issuer"] = "ဝန်ကြီးဌာန"
        briefing["attention"][0]["scope_excerpt"] = "ဆာဗာနှစ်လုံး ဝယ်ယူခြင်းနှင့် တပ်ဆင်ခြင်း"
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=briefing), patch(
                "signalforge.telegram_delivery._send_message", return_value="999"
            ) as send:
                result = telegram_deliver(
                    database=database,
                    bot_token="secret",
                    chat_id="42",
                    business_profile=profile,
                )
        self.assertEqual(result["sent_count"], 0)
        self.assertEqual(result["quality_filtered_count"], 1)
        self.assertEqual(result["quality_filtered"][0]["reasons"], ["UNTRANSLATED_MYANMAR_PRESENT"])
        send.assert_not_called()

    def test_translated_preview_uses_production_translation_path_without_receipt(self) -> None:
        profile = BusinessProfile.from_dict(
            {"profile_id": "ict-pilot", "delivery_mode": "MATCHED_ONLY", "relevance_categories": ["ICT"]}
        )
        briefing = _briefing()
        briefing["attention"][0]["title"] = "အိတ်ဖွင့်တင်ဒါ"
        briefing["attention"][0]["issuer"] = "ဝန်ကြီးဌာန"
        briefing["attention"][0]["scope_excerpt"] = "ဆာဗာနှစ်လုံး ဝယ်ယူခြင်းနှင့် တပ်ဆင်ခြင်း"
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=briefing), patch(
                "signalforge.telegram_delivery.translate_tender_fields_to_zh_hans",
                side_effect=lambda values, **_kwargs: (
                    ["服务器采购", "政府采购方", "采购2台服务器并完成安装", *values[3:]],
                    True,
                ),
            ) as translate:
                result = telegram_deliver(
                    database=database,
                    dry_run=True,
                    translate_preview=True,
                    business_profile=profile,
                )
            with connect(database) as conn:
                receipts = conn.execute("SELECT COUNT(*) FROM pilot_delivery_receipts").fetchone()[0]
        self.assertEqual(result["pending_count"], 1)
        self.assertTrue(result["translate_preview"])
        self.assertEqual(result["quality_filtered_count"], 0)
        self.assertNotIn("UNKNOWN", result["pending"][0]["message"])
        self.assertNotIn("ဆာဗာ", result["pending"][0]["message"])
        self.assertIn("采购2台服务器并完成安装", result["pending"][0]["message"])
        self.assertEqual(receipts, 0)
        translate.assert_called_once()

    def test_unknown_deadline_renderer_uses_customer_language_not_internal_sentinel(self) -> None:
        item = dict(_briefing()["attention"][0])
        item["deadline_status"] = "UNKNOWN"
        item["deadline"] = None
        text = render_telegram_message(item, translator=lambda values: (values, False))
        self.assertIn("未在已核验材料中确认", text)
        self.assertNotIn("UNKNOWN", text)

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

    def test_action_upgrade_without_new_signal_is_not_redelivered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery._send_message", return_value="101"):
                with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing(action="PRIORITIZE")):
                    telegram_deliver(database=database, bot_token="secret", chat_id="42")
                with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing(action="ACT_NOW")):
                    upgraded = telegram_deliver(database=database, bot_token="secret", chat_id="42")
                    repeated = telegram_deliver(database=database, bot_token="secret", chat_id="42")
            self.assertEqual(upgraded["sent_count"], 0)
            self.assertEqual(repeated["sent_count"], 0)
            with connect(database) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM delivery_receipts").fetchone()[0], 1)

    def test_deadline_crossing_does_not_redeliver_without_new_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            payload = {
                "item_kind": "TENDER",
                "business_stage": "OPPORTUNITY",
                "issuer": "Ministry of Industry, Myanmar",
                "title": "Electrical spare parts for industrial plant",
                "project_name": "Electrical spare parts for industrial plant",
                "reference_no": "INDUSTRY-ELECTRICAL-72H",
                "publication_date": "2026-09-01",
                "deadline": "2026-09-14",
                "deadline_time": "16:00",
                "deadline_evidence": "EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME",
                "scope_summary": "Electrical spare parts and Mechanical spare parts for industrial plant operations.",
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

            self.assertEqual(before["sent_count"], 1)
            self.assertEqual(upgraded["sent_count"], 0)
            self.assertEqual(repeated["sent_count"], 0)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(before["sent"][0]["canonical_key"], "industry:test-72h")
            with connect(database) as conn:
                row = conn.execute(
                    "SELECT signal_id,attention_action,priority_band FROM delivery_receipts WHERE canonical_key='industry:test-72h'"
                ).fetchone()
            self.assertEqual(tuple(row), ("sig-test-72h", "PRIORITIZE", "MEDIUM"))

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
        self.assertIn("📢 <b>政府/国企招标 · 新招标</b>", text)
        self.assertIn("🏛 采购方：Ministry &lt;Foreign&gt; &amp; Affairs", text)
        self.assertIn("Data Server &amp; SQL &lt;Tender&gt;", text)
        self.assertIn("⏰ 截止：<b>2026-09-18 16:30</b>", text)
        self.assertIn("🔎 证据：官方 HTML + 官方文本 PDF", text)
        self.assertIn("🔗 <a href=", text)
        scope_line = next(line for line in text.splitlines() if line.startswith("📦 采购内容："))
        self.assertLessEqual(scope_line.count("x"), 240)
        self.assertNotIn("<Foreign>", text)

    def test_explicit_money_is_rendered_without_inference(self) -> None:
        item = _briefing()["attention"][0]
        assert isinstance(item, dict)
        item["price_or_budget_summary"] = "4 billion MMK"
        text = render_telegram_message(item)
        self.assertIn("💰 金额（原文）：4 billion MMK", text)

    def test_focus_references_are_rendered_separately_from_full_reference_bundle(self) -> None:
        item = _briefing()["attention"][0]
        assert isinstance(item, dict)
        item["reference_numbers"] = ["DMP/L-026(26-27)", "DMP/L-040(26-27)", "DMP/L-067(26-27)"]
        item["focus_reference_numbers"] = ["DMP/L-026(26-27)", "DMP/L-067(26-27)"]
        item["scope_excerpt"] = "DMP/L-026 Communication and Information Technology | DMP/L-067 IOT Module"
        text = render_telegram_message(item)
        self.assertIn("📌 招标编号：DMP/L-026(26-27), DMP/L-040(26-27), DMP/L-067(26-27)", text)
        self.assertIn("🧩 相关分包：DMP/L-026(26-27), DMP/L-067(26-27)", text)
        self.assertIn("📦 采购内容：DMP/L-026 Communication and Information Technology | DMP/L-067 IOT Module", text)

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
            "action_time": "08:30",
            "quantity_or_lot_summary": "Approximately 6,243 tons of teak/hardwood logs and sawn timber",
            "location": "Myanma Timber Enterprise, Gyogon Forest Compound, Insein Township, Yangon",
            "next_action_summary": "Complete the prescribed tender/auction application and pre-submit the required Earnest Money by Payment Order.",
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
        self.assertIn("🗓 活动日：<b>2026-09-15 08:30</b>", text)
        self.assertIn("🔢 数量/规模：Approximately 6,243 tons of teak/hardwood logs and sawn timber", text)
        self.assertIn("📍 地点：Myanma Timber Enterprise, Gyogon Forest Compound, Insein Township, Yangon", text)
        self.assertIn("➡️ 下一步：Complete the prescribed tender/auction application", text)
        self.assertNotIn("Signal质量", text)
        self.assertNotIn("⏰ 截止：", text)
        self.assertNotIn("为什么", text)

    def test_signal_type_controls_tender_notification_label(self) -> None:
        item = _briefing()["attention"][0]
        assert isinstance(item, dict)
        self.assertIn("新招标", render_telegram_message(item))
        item["latest_signal_type"] = "UPDATED"
        self.assertIn("招标更新", render_telegram_message(item))


    def test_burmese_fields_are_translated_for_telegram_display_only(self) -> None:
        item = _briefing()["attention"][0]
        assert isinstance(item, dict)
        item.update({
            "issuer": "ကျန်းမာရေးဝန်ကြီးဌာန",
            "title": "ဆေးပစ္စည်း အိတ်ဖွင့်တင်ဒါ",
            "scope_excerpt": "ဆေးရုံသုံးပစ္စည်းများ ဝယ်ယူရန်",
            "quantity_or_lot_summary": "ပစ္စည်း ၁၀၀ စုံ",
            "location": "ရန်ကုန်",
            "next_action_summary": "တင်ဒါစာရွက်စာတမ်း ရယူပါ",
        })

        def fake_translator(values: list[str]) -> tuple[list[str], bool]:
            self.assertEqual(len(values), 7)
            return [
                "医疗物资公开招标",
                "卫生部",
                "采购医院使用的医疗物资",
                "100套",
                "",
                "仰光",
                "获取招标文件",
            ], True

        text = render_telegram_message(item, translator=fake_translator)
        self.assertIn("<b>医疗物资公开招标</b>", text)
        self.assertIn("🏛 采购方：卫生部", text)
        self.assertIn("📦 采购内容：采购医院使用的医疗物资", text)
        self.assertIn("🔢 数量/规模：100套", text)
        self.assertIn("📍 地点：仰光", text)
        self.assertIn("➡️ 下一步：获取招标文件", text)
        self.assertIn("🌐 原文内容已机器翻译为中文", text)
        self.assertNotIn("ဆေးပစ္စည်း", text)

    def test_credentials_required_only_for_real_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with patch("signalforge.telegram_delivery.business_briefing", return_value=_briefing()):
                with self.assertRaisesRegex(TelegramDeliveryError, "credentials are not configured"):
                    telegram_deliver(database=database)


if __name__ == "__main__":
    unittest.main()
