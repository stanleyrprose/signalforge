from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import db_path


SCHEMA_VERSION = 1


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    target = path or db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
    finally:
        conn.close()


def migrate(path: Path | None = None) -> None:
    with connect(path) as conn, conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS source_state (
                source_id TEXT PRIMARY KEY,
                baseline_complete INTEGER NOT NULL DEFAULT 0,
                sitemap_hash TEXT,
                last_success_at TEXT,
                next_due_at TEXT,
                last_error TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS discovery_items (
                source_id TEXT NOT NULL,
                url TEXT NOT NULL,
                lastmod TEXT,
                content_hash TEXT,
                canonical_key TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                last_fetched_at TEXT,
                PRIMARY KEY(source_id, url)
            );
            CREATE INDEX IF NOT EXISTS idx_discovery_source_lastmod
                ON discovery_items(source_id, lastmod);
            CREATE TABLE IF NOT EXISTS canonical_items (
                canonical_key TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                reference_no TEXT NOT NULL,
                project_name TEXT NOT NULL,
                publication_date TEXT,
                deadline TEXT,
                location TEXT,
                url TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_canonical_source_updated
                ON canonical_items(source_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                canonical_key TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                UNIQUE(source_id, canonical_key, signal_type, payload_json)
            );
            CREATE INDEX IF NOT EXISTS idx_signals_created
                ON signals(created_at DESC);
            CREATE TABLE IF NOT EXISTS scheduler_runs (
                app_run_id TEXT PRIMARY KEY,
                trigger_id TEXT NOT NULL,
                trigger_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                worker_run_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                changed INTEGER NOT NULL DEFAULT 0,
                signals_created INTEGER NOT NULL DEFAULT 0,
                baseline INTEGER NOT NULL DEFAULT 0,
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_scheduler_source_started
                ON scheduler_runs(source_id, started_at DESC);
            """
        )
        exists = conn.execute("SELECT 1 FROM schema_meta WHERE version=?", (SCHEMA_VERSION,)).fetchone()
        if exists is None:
            conn.execute(
                "INSERT INTO schema_meta(version, applied_at) VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
                (SCHEMA_VERSION,),
            )
