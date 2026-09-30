from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from signalforge.db import migrate


class DatabaseMigrationTests(unittest.TestCase):
    def test_gate_o_v1_state_upgrades_without_false_recovery_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "signalforge.db"
            with sqlite3.connect(db) as conn:
                conn.executescript(
                    """
                    CREATE TABLE schema_meta(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
                    INSERT INTO schema_meta VALUES (1,'2026-09-02T12:00:00Z');
                    CREATE TABLE source_state(
                        source_id TEXT PRIMARY KEY,
                        baseline_complete INTEGER NOT NULL DEFAULT 0,
                        sitemap_hash TEXT,
                        last_success_at TEXT,
                        next_due_at TEXT,
                        last_error TEXT,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE discovery_items(
                        source_id TEXT NOT NULL,
                        url TEXT NOT NULL,
                        lastmod TEXT,
                        content_hash TEXT,
                        canonical_key TEXT,
                        first_seen_at TEXT NOT NULL,
                        last_seen_at TEXT NOT NULL,
                        last_fetched_at TEXT,
                        PRIMARY KEY(source_id,url)
                    );
                    CREATE TABLE canonical_items(
                        canonical_key TEXT PRIMARY KEY,source_id TEXT NOT NULL,reference_no TEXT NOT NULL,
                        project_name TEXT NOT NULL,publication_date TEXT,deadline TEXT,location TEXT,url TEXT NOT NULL,
                        content_hash TEXT NOT NULL,evidence_sha256 TEXT NOT NULL,payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,updated_at TEXT NOT NULL
                    );
                    INSERT INTO canonical_items VALUES(
                        'mpt:EXISTING','S13','EXISTING','Existing Tender','2026-09-01',NULL,NULL,
                        'https://mpt.com.mm/en/existing/','hash','evidence','{}','2026-09-02T12:00:00Z','2026-09-02T12:00:00Z'
                    );
                    CREATE TABLE signals(
                        signal_id TEXT PRIMARY KEY,source_id TEXT NOT NULL,canonical_key TEXT NOT NULL,
                        signal_type TEXT NOT NULL,created_at TEXT NOT NULL,payload_json TEXT NOT NULL,
                        UNIQUE(source_id,canonical_key,signal_type,payload_json)
                    );
                    CREATE TABLE scheduler_runs(
                        app_run_id TEXT PRIMARY KEY,trigger_id TEXT NOT NULL,trigger_kind TEXT NOT NULL,
                        source_id TEXT NOT NULL,worker_run_id TEXT NOT NULL,started_at TEXT NOT NULL,
                        finished_at TEXT,status TEXT NOT NULL,changed INTEGER NOT NULL DEFAULT 0,
                        signals_created INTEGER NOT NULL DEFAULT 0,baseline INTEGER NOT NULL DEFAULT 0,error TEXT
                    );
                    INSERT INTO source_state VALUES(
                        'S13',1,'sitemap-hash','2026-09-02T12:00:00Z','2026-09-02T12:15:00Z',NULL,'2026-09-02T12:00:00Z'
                    );
                    INSERT INTO discovery_items VALUES(
                        'S13','https://mpt.com.mm/en/existing/','2026-09-02T11:00:00+00:00','content','mpt:EXISTING',
                        '2026-09-02T12:00:00Z','2026-09-02T12:00:00Z','2026-09-02T12:00:00Z'
                    );
                    """
                )

            migrate(db)

            with sqlite3.connect(db) as conn:
                discovery = conn.execute(
                    "SELECT lastmod,fetched_lastmod,pending_since_at,suppress_signal_once FROM discovery_items"
                ).fetchone()
                state = conn.execute(
                    "SELECT last_snapshot_at,last_successful_reconciliation_at,consecutive_failures,recovery_window_start,recovery_window_end FROM source_state"
                ).fetchone()
                versions = [row[0] for row in conn.execute("SELECT version FROM schema_meta ORDER BY version")]
                scheduler_columns = {row[1] for row in conn.execute("PRAGMA table_info(scheduler_runs)")}
                canonical_columns = {row[1] for row in conn.execute("PRAGMA table_info(canonical_items)")}
                canonical = conn.execute("SELECT item_kind,title,project_name FROM canonical_items WHERE canonical_key='mpt:EXISTING'").fetchone()
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

            self.assertEqual(discovery, ("2026-09-02T11:00:00+00:00", "2026-09-02T11:00:00+00:00", None, 0))
            self.assertEqual(state, ("2026-09-02T12:00:00Z", "2026-09-02T12:00:00Z", 0, None, None))
            self.assertEqual(versions, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
            self.assertEqual(canonical, ("TENDER", "Existing Tender", "Existing Tender"))
            self.assertTrue({"item_kind", "title"} <= canonical_columns)
            self.assertTrue({"recovery", "outage_window_start", "outage_window_end", "backlog_remaining", "details_attempted", "details_succeeded", "tenders_parsed", "items_parsed"} <= scheduler_columns)
            self.assertTrue({"acquisition_requests", "acquisition_attempts", "evidence_envelopes", "processing_records"} <= tables)


    def test_v9_delivery_receipts_upgrade_adds_profile_columns_before_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "signalforge-v9.db"
            migrate(db)
            with sqlite3.connect(db) as conn:
                conn.executescript(
                    """
                    DROP INDEX IF EXISTS idx_delivery_receipts_profile_sent;
                    DROP TABLE delivery_receipts;
                    CREATE TABLE delivery_receipts (
                        delivery_key TEXT PRIMARY KEY,
                        channel TEXT NOT NULL,
                        canonical_key TEXT NOT NULL,
                        signal_id TEXT NOT NULL,
                        attention_action TEXT NOT NULL,
                        priority_band TEXT NOT NULL,
                        payload_sha256 TEXT NOT NULL,
                        provider_message_id TEXT,
                        sent_at TEXT NOT NULL,
                        UNIQUE(channel, canonical_key, signal_id, attention_action)
                    );
                    CREATE INDEX idx_delivery_receipts_channel_sent
                        ON delivery_receipts(channel, sent_at DESC);
                    INSERT INTO delivery_receipts(
                        delivery_key,channel,canonical_key,signal_id,attention_action,priority_band,
                        payload_sha256,provider_message_id,sent_at
                    ) VALUES (
                        'legacy-delivery','telegram','mpt:legacy','sig-legacy','PRIORITIZE','HIGH',
                        'payload','100','2026-09-29T00:00:00Z'
                    );
                    DELETE FROM schema_meta WHERE version>=10;
                    """
                )

            migrate(db)

            with sqlite3.connect(db) as conn:
                columns = {row[1] for row in conn.execute("PRAGMA table_info(delivery_receipts)")}
                indexes = {row[1] for row in conn.execute("PRAGMA index_list(delivery_receipts)")}
                row = conn.execute(
                    "SELECT canonical_key,profile_id,profile_match_score FROM delivery_receipts WHERE delivery_key='legacy-delivery'"
                ).fetchone()
                version = conn.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0]

            self.assertTrue({"profile_id", "profile_match_score"} <= columns)
            self.assertIn("idx_delivery_receipts_profile_sent", indexes)
            self.assertEqual(row, ("mpt:legacy", None, None))
            self.assertEqual(version, 11)


    def test_v4_scheduler_history_backfills_items_parsed_from_tenders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "signalforge-v4.db"
            with sqlite3.connect(db) as conn:
                conn.executescript(
                    """
                    CREATE TABLE schema_meta(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
                    INSERT INTO schema_meta VALUES (4,'2026-09-04T00:00:00Z');
                    CREATE TABLE scheduler_runs(
                        app_run_id TEXT PRIMARY KEY,trigger_id TEXT NOT NULL,trigger_kind TEXT NOT NULL,
                        source_id TEXT NOT NULL,worker_run_id TEXT NOT NULL,started_at TEXT NOT NULL,
                        finished_at TEXT,status TEXT NOT NULL,changed INTEGER NOT NULL DEFAULT 0,
                        signals_created INTEGER NOT NULL DEFAULT 0,baseline INTEGER NOT NULL DEFAULT 0,
                        recovery INTEGER NOT NULL DEFAULT 0,outage_window_start TEXT,outage_window_end TEXT,
                        backlog_remaining INTEGER NOT NULL DEFAULT 0,details_attempted INTEGER NOT NULL DEFAULT 0,
                        details_succeeded INTEGER NOT NULL DEFAULT 0,tenders_parsed INTEGER NOT NULL DEFAULT 0,error TEXT
                    );
                    INSERT INTO scheduler_runs(
                        app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,status,tenders_parsed
                    ) VALUES ('run-1','poll:S13:1','POLL','S13','worker-1','2026-09-04T00:00:00Z','SUCCESS',7);
                    """
                )

            migrate(db)

            with sqlite3.connect(db) as conn:
                row = conn.execute(
                    "SELECT tenders_parsed,items_parsed FROM scheduler_runs WHERE app_run_id='run-1'"
                ).fetchone()
                versions = [value[0] for value in conn.execute("SELECT version FROM schema_meta ORDER BY version")]

            self.assertEqual(row, (7, 7))
            self.assertEqual(versions, [4, 5, 6, 7, 8, 9, 10, 11])


if __name__ == "__main__":
    unittest.main()
