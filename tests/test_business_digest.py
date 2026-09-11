from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.business_digest import business_digest, render_business_digest, telegram_digest
from signalforge.db import connect, migrate


class _Registry:
    def enabled_sources(self):
        return [("S13", {}), ("S41", {})]


def _briefing() -> dict[str, object]:
    return {
        "current_opportunities": 3,
        "current_counts": {"OPEN": 2, "UNKNOWN": 1, "EXPIRED": 0},
        "qualification_counts": {
            "priority_band": {"HIGH": 1, "MEDIUM": 1, "REVIEW": 1},
            "signal_quality_band": {"VERY_HIGH": 1, "HIGH": 1, "MEDIUM": 0, "REVIEW": 1, "LOW": 0},
            "signal_quality_score_avg": 68.0,
        },
        "attention_count": 2,
        "attention_action_counts": {"ACT_NOW": 0, "PRIORITIZE": 1, "REVIEW": 1},
        "attention": [
            {
                "canonical_key": "energy:235",
                "attention_action": "PRIORITIZE",
                "priority_band": "HIGH",
                "issuer": "Ministry of Energy, Myanmar",
                "primary_relevance": "ICT",
                "deadline": "2026-09-18",
                "deadline_time": "13:00",
                "deadline_status": "OPEN",
                "focus_reference_count": 4,
                "signal_quality_score": 81,
                "signal_quality_band": "HIGH",
            },
            {
                "canonical_key": "doms:1",
                "attention_action": "REVIEW",
                "priority_band": "REVIEW",
                "issuer": "Department of Medical Services",
                "primary_relevance": "MEDICAL",
                "deadline": None,
                "deadline_time": None,
                "deadline_status": "UNKNOWN",
                "focus_reference_count": None,
                "signal_quality_score": 40,
                "signal_quality_band": "REVIEW",
            },
        ],
        "watchlist": {"count": 1, "primary_relevance_counts": {"INDUSTRIAL": 1}, "canonical_keys": ["industry:1"]},
    }


def _audit() -> dict[str, object]:
    return {
        "status": "PASS",
        "finding_count": 0,
        "checks": {
            "source_health": {"checked_sources": 2, "non_green_sources": 0},
            "strategic_coverage": {
                "S13": {"status": "PASS", "missing": 0},
                "S41": {"status": "PASS", "canonical_keys": 15, "official_keys": 15, "missing": []},
            },
            "atom_surface_trigger": {"status": "NO_TRIGGER"},
        },
        "assurance": {"external_completeness": "NOT_PROVEN"},
    }


def _scorecard() -> dict[str, object]:
    return {
        "status": "PASS",
        "summary": {
            "active_sources": 2,
            "effective_signals": 1,
            "yield_states": {
                "ACTIONABLE_PROVEN": 1,
                "SIGNAL_PROVEN": 0,
                "BASELINE_ONLY": 1,
                "NOISE_ONLY_HISTORY": 0,
                "EMPTY": 0,
            },
        },
    }


class BusinessDigestTests(unittest.TestCase):
    def _db(self, root: str) -> Path:
        database = Path(root) / "signalforge.db"
        migrate(database)
        with connect(database) as conn, conn:
            conn.execute(
                """INSERT INTO scheduler_runs(app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,finished_at,status,changed,signals_created,items_parsed,tenders_parsed) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("run-1", "t", "SCHEDULE", "S13", "w", "2026-09-10T10:00:00Z", "2026-09-10T10:01:00Z", "SUCCESS", 2, 1, 5, 2),
            )
            conn.execute(
                """INSERT INTO scheduler_runs(app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,finished_at,status,changed,signals_created,items_parsed,tenders_parsed) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("run-2", "t", "SCHEDULE", "S41", "w", "2026-09-10T11:00:00Z", "2026-09-10T11:01:00Z", "SUCCESS", 0, 0, 3, 3),
            )
            conn.execute(
                "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                ("sig-1", "S13", "mpt:1", "NEW", "2026-09-10T10:02:00Z", json.dumps({"x": 1})),
            )
            conn.execute(
                "INSERT INTO delivery_receipts(delivery_key,channel,canonical_key,signal_id,attention_action,priority_band,payload_sha256,provider_message_id,sent_at) VALUES (?,?,?,?,?,?,?,?,?)",
                ("d-1", "telegram", "mpt:1", "sig-1", "PRIORITIZE", "HIGH", "sha", "101", "2026-09-10T10:03:00Z"),
            )
        return database

    def test_digest_reports_24h_pipeline_and_current_business_funnel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            result = business_digest(
                database=self._db(tmp),
                registry=_Registry(),  # type: ignore[arg-type]
                now=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            )
        self.assertEqual(result["digest_date"], "2026-09-10")
        self.assertEqual(result["sources"], {"monitored": 2, "green": 2, "non_green": 0, "polled_24h": 2, "changed_24h": 1})
        self.assertEqual(result["activity_24h"]["records_changed"], 2)
        self.assertEqual(result["activity_24h"]["signals"], 1)
        self.assertEqual(result["business"]["current_opportunities"], 3)
        self.assertEqual(result["business"]["watchlist_count"], 1)
        self.assertEqual(result["pipeline_totals"]["telegram_alerts"], 1)

    def test_render_makes_business_output_visible_not_only_system_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            digest = business_digest(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,10,12,0,tzinfo=UTC))  # type: ignore[arg-type]
        text = render_business_digest(digest)
        self.assertIn("Sources：<b>2</b> monitored", text)
        self.assertIn("Signals：<b>1</b>", text)
        self.assertIn("当前机会：<b>3</b> · HIGH 1 · MEDIUM 1 · REVIEW 1", text)
        self.assertIn("Signal质量：均分 68.0 · VERY_HIGH 1 · HIGH 1 · MEDIUM 0 · REVIEW 1", text)
        self.assertIn("Q81/HIGH", text)
        self.assertIn("Ministry of Energy", text)
        self.assertIn("相关分包 4", text)
        self.assertIn("Watchlist：1 条 MEDIUM", text)
        self.assertIn("MYTEL 15/15", text)
        self.assertIn("Source产出：<b>1/2</b> proven", text)
        self.assertIn("1 effective / 1 raw signals", text)

    def test_dry_run_does_not_write_digest_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()):
            database = self._db(tmp)
            result = telegram_digest(database=database, now=datetime(2026,9,10,12,0,tzinfo=UTC), dry_run=True, audit_network=False)
            self.assertEqual(result["pending_count"], 1)
            with connect(database) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM digest_delivery_receipts").fetchone()[0], 0)

    def test_real_delivery_is_once_per_myanmar_calendar_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.business_digest.business_briefing", return_value=_briefing()), patch(
            "signalforge.business_digest.audit", return_value=_audit()
        ), patch("signalforge.business_digest.source_scorecard", return_value=_scorecard()), patch("signalforge.business_digest._send_message", return_value="501") as send:
            database = self._db(tmp)
            first = telegram_digest(database=database, now=datetime(2026,9,10,12,0,tzinfo=UTC), bot_token="secret", chat_id="42", audit_network=False)
            second = telegram_digest(database=database, now=datetime(2026,9,10,15,0,tzinfo=UTC), bot_token="secret", chat_id="42", audit_network=False)
            next_day = telegram_digest(database=database, now=datetime(2026,9,11,2,0,tzinfo=UTC), bot_token="secret", chat_id="42", audit_network=False)
            with connect(database) as conn:
                receipt_count = conn.execute("SELECT COUNT(*) FROM digest_delivery_receipts").fetchone()[0]
        self.assertEqual(first["sent_count"], 1)
        self.assertEqual(second["sent_count"], 0)
        self.assertTrue(second["deduplicated"])
        self.assertEqual(next_day["sent_count"], 1)
        self.assertEqual(send.call_count, 2)
        self.assertEqual(receipt_count, 2)

    def test_migration_creates_digest_receipt_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            with connect(database) as conn:
                names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                version = conn.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0]
        self.assertIn("digest_delivery_receipts", names)
        self.assertEqual(version, 7)


if __name__ == "__main__":
    unittest.main()
