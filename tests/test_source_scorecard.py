from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.db import connect, migrate
from signalforge.source_scorecard import PORTFOLIO_TIERS, SCORECARD_VERSION, S13_PARSER_ONLY_SIGNAL_ID, source_scorecard


class _Registry:
    raw = {
        "sources": {
            "S13": {"name": "MPT Tender Information", "role": "ACTIVE_SELECTIVE", "priority": 100, "poll_interval_seconds": 900},
            "S40": {"name": "Ministry of Labour Procurement Invitations", "role": "ACTIVE_SELECTIVE", "priority": 87, "poll_interval_seconds": 1800},
        }
    }

    def enabled_sources(self):
        return [("S13", self.raw["sources"]["S13"]), ("S40", self.raw["sources"]["S40"])]


def _audit() -> dict[str, object]:
    return {
        "status": "PASS",
        "checks": {
            "source_health": {
                "sources": [
                    {"source_id": "S13", "source_health": "GREEN"},
                    {"source_id": "S40", "source_health": "GREEN"},
                ]
            }
        },
    }


def _opportunities() -> dict[str, object]:
    return {
        "opportunities": [
            {
                "source_id": "S13",
                "canonical_key": "mpt:new",
                "priority_band": "HIGH",
                "relevance_categories": ["TELECOM"],
            }
        ]
    }


class SourceScorecardTests(unittest.TestCase):
    def _db(self, root: str) -> Path:
        database = Path(root) / "signalforge.db"
        migrate(database)
        with connect(database) as conn, conn:
            conn.execute(
                """INSERT INTO canonical_items(canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("mpt:new", "S13", "TENDER", "MPT", "MPT-1", "MPT", "2026-09-09", "2026-09-20", None, "https://example.test/mpt", "h", "e", "{}", "2026-09-09T00:00:00Z", "2026-09-09T00:00:00Z"),
            )
            conn.execute(
                """INSERT INTO canonical_items(canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("mpa:manual", "S15A", "TENDER", "MPA", "MPA-1", "MPA", "2026-09-01", None, None, "https://example.test/mpa", "hm", "em", "{}", "2026-09-01T00:00:00Z", "2026-09-01T00:00:00Z"),
            )
            conn.execute(
                "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                (S13_PARSER_ONLY_SIGNAL_ID, "S13", "mpt:new", "UPDATED", "2026-09-09T17:15:12.735583Z", json.dumps({"x": 1})),
            )
            conn.execute(
                "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                ("sig-real", "S13", "mpt:new", "NEW", "2026-09-10T10:00:00Z", json.dumps({"x": 2})),
            )
            conn.execute(
                "INSERT INTO delivery_receipts(delivery_key,channel,canonical_key,signal_id,attention_action,priority_band,payload_sha256,provider_message_id,sent_at) VALUES (?,?,?,?,?,?,?,?,?)",
                ("d", "telegram", "mpt:new", "sig-real", "PRIORITIZE", "HIGH", "sha", "101", "2026-09-10T10:01:00Z"),
            )
            for sid, started in (("S13", "2026-09-01T00:00:00Z"), ("S40", "2026-09-09T00:00:00Z")):
                conn.execute(
                    """INSERT INTO scheduler_runs(app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,finished_at,status,changed,signals_created) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (f"run-{sid}", "t", "SCHEDULE", sid, "w", started, started, "SUCCESS", 0, 0),
                )
        return database

    def test_scorecard_separates_strategic_tier_from_observed_yield(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.source_scorecard.audit", return_value=_audit()), patch(
            "signalforge.source_scorecard.current_opportunities", return_value=_opportunities()
        ):
            result = source_scorecard(
                database=self._db(tmp),
                registry=_Registry(),  # type: ignore[arg-type]
                now=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            )
        by_id = {row["source_id"]: row for row in result["sources"]}
        self.assertEqual(by_id["S13"]["portfolio_tier"], "CORE")
        self.assertEqual(by_id["S13"]["observed_yield"], "ACTIONABLE_PROVEN")
        self.assertEqual(by_id["S13"]["recommendation"], "KEEP_PROVEN")
        self.assertEqual(by_id["S40"]["portfolio_tier"], "OBSERVATION")
        self.assertEqual(by_id["S40"]["observed_yield"], "EMPTY")
        self.assertEqual(by_id["S40"]["recommendation"], "OBSERVE_TO_30D")

    def test_known_parser_only_signal_is_accounted_as_noise_not_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.source_scorecard.audit", return_value=_audit()), patch(
            "signalforge.source_scorecard.current_opportunities", return_value=_opportunities()
        ):
            result = source_scorecard(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,10,12,0,tzinfo=UTC))  # type: ignore[arg-type]
        row = next(row for row in result["sources"] if row["source_id"] == "S13")
        self.assertEqual(row["raw_signals_total"], 2)
        self.assertEqual(row["known_noise_signals"], 1)
        self.assertEqual(row["effective_signals_total"], 1)
        self.assertEqual(result["summary"]["raw_signals"], 2)
        self.assertEqual(result["summary"]["known_noise_signals"], 1)
        self.assertEqual(result["summary"]["effective_signals"], 1)
        self.assertEqual(result["summary"]["active_source_canonical_items"], 1)
        self.assertEqual(result["summary"]["database_canonical_items"], 2)
        self.assertEqual(result["summary"]["non_active_canonical_items"], 1)

    def test_current_opportunity_and_telegram_contribution_are_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("signalforge.source_scorecard.audit", return_value=_audit()), patch(
            "signalforge.source_scorecard.current_opportunities", return_value=_opportunities()
        ):
            result = source_scorecard(database=self._db(tmp), registry=_Registry(), now=datetime(2026,9,10,12,0,tzinfo=UTC))  # type: ignore[arg-type]
        row = next(row for row in result["sources"] if row["source_id"] == "S13")
        self.assertEqual(row["current_opportunities"], 1)
        self.assertEqual(row["current_priority_counts"]["HIGH"], 1)
        self.assertEqual(row["current_ict_telecom_opportunities"], 1)
        self.assertEqual(row["telegram_alerts_total"], 1)


    def test_s25_historical_noise_window_does_not_hide_later_real_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                for signal_id, created_at in (
                    ("noise", "2026-09-08T11:00:17.140857Z"),
                    ("real", "2026-09-09T11:00:17.140857Z"),
                ):
                    conn.execute(
                        "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                        (signal_id, "S25", "monpifer:test", "UPDATED", created_at, json.dumps({"id": signal_id})),
                    )
            class RegistryS25:
                raw = {"sources": {"S25": {"name": "MONPIFER Ministry Tenders", "role": "ACTIVE_PRIMARY", "priority": 70, "poll_interval_seconds": 1800}}}
                def enabled_sources(self):
                    return [("S25", self.raw["sources"]["S25"])]
            audit_result = {"status": "PASS", "checks": {"source_health": {"sources": [{"source_id": "S25", "source_health": "GREEN"}]}}}
            with patch("signalforge.source_scorecard.audit", return_value=audit_result), patch(
                "signalforge.source_scorecard.current_opportunities", return_value={"opportunities": []}
            ):
                result = source_scorecard(database=database, registry=RegistryS25(), now=datetime(2026,9,10,12,0,tzinfo=UTC))  # type: ignore[arg-type]
        row = result["sources"][0]
        self.assertEqual(row["raw_signals_total"], 2)
        self.assertEqual(row["known_noise_signals"], 1)
        self.assertEqual(row["effective_signals_total"], 1)
        self.assertEqual(row["observed_yield"], "SIGNAL_PROVEN")


    def test_portfolio_v2_promotes_s21_only_after_repeated_actionable_yield(self) -> None:
        self.assertEqual(SCORECARD_VERSION, 2)
        self.assertEqual(PORTFOLIO_TIERS["S21"], "CORE")
        self.assertEqual(PORTFOLIO_TIERS["S22"], "STRATEGIC_WATCH")
        self.assertEqual(PORTFOLIO_TIERS["S32"], "OBSERVATION")

    def test_window_days_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 365"):
            source_scorecard(registry=_Registry(), window_days=0)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "between 1 and 365"):
            source_scorecard(registry=_Registry(), window_days=366)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
