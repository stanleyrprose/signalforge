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

            self.assertEqual(discovery, ("2026-09-02T11:00:00+00:00", "2026-09-02T11:00:00+00:00", None, 0))
            self.assertEqual(state, ("2026-09-02T12:00:00Z", "2026-09-02T12:00:00Z", 0, None, None))
            self.assertEqual(versions, [1, 2])
            self.assertTrue({"recovery", "outage_window_start", "outage_window_end", "backlog_remaining"} <= scheduler_columns)


if __name__ == "__main__":
    unittest.main()
