from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import db_path


SCHEMA_VERSION = 8


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


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(conn: sqlite3.Connection, table: str, definition: str) -> bool:
    name = definition.split()[0]
    if name in _columns(conn, table):
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")
    return True


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
                last_snapshot_at TEXT,
                last_success_at TEXT,
                last_successful_reconciliation_at TEXT,
                next_due_at TEXT,
                last_error TEXT,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                recovery_window_start TEXT,
                recovery_window_end TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS discovery_items (
                source_id TEXT NOT NULL,
                url TEXT NOT NULL,
                lastmod TEXT,
                fetched_lastmod TEXT,
                pending_since_at TEXT,
                suppress_signal_once INTEGER NOT NULL DEFAULT 0,
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
                item_kind TEXT NOT NULL DEFAULT 'TENDER',
                title TEXT,
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
            CREATE TABLE IF NOT EXISTS delivery_receipts (
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
            CREATE INDEX IF NOT EXISTS idx_delivery_receipts_channel_sent
                ON delivery_receipts(channel, sent_at DESC);
            CREATE TABLE IF NOT EXISTS digest_delivery_receipts (
                digest_key TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                digest_date TEXT NOT NULL,
                window_start TEXT NOT NULL,
                window_end TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                provider_message_id TEXT,
                sent_at TEXT NOT NULL,
                UNIQUE(channel, digest_date)
            );
            CREATE INDEX IF NOT EXISTS idx_digest_delivery_channel_sent
                ON digest_delivery_receipts(channel, sent_at DESC);
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
                recovery INTEGER NOT NULL DEFAULT 0,
                outage_window_start TEXT,
                outage_window_end TEXT,
                backlog_remaining INTEGER NOT NULL DEFAULT 0,
                details_attempted INTEGER NOT NULL DEFAULT 0,
                details_succeeded INTEGER NOT NULL DEFAULT 0,
                tenders_parsed INTEGER NOT NULL DEFAULT 0,
                items_parsed INTEGER NOT NULL DEFAULT 0,
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_scheduler_source_started
                ON scheduler_runs(source_id, started_at DESC);
            CREATE TABLE IF NOT EXISTS acquisition_requests (
                request_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                scheduler_run_id TEXT NOT NULL,
                app_job_ref TEXT,
                source_id TEXT NOT NULL,
                source_policy_version INTEGER NOT NULL,
                mode TEXT NOT NULL,
                reason TEXT NOT NULL,
                egress_profile TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                primary_method TEXT NOT NULL,
                target_kind TEXT NOT NULL,
                timeout_seconds INTEGER NOT NULL,
                expected_content_types_json TEXT NOT NULL,
                FOREIGN KEY(scheduler_run_id) REFERENCES scheduler_runs(app_run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_acquisition_requests_source_requested
                ON acquisition_requests(source_id, requested_at DESC);
            CREATE INDEX IF NOT EXISTS idx_acquisition_requests_scheduler
                ON acquisition_requests(scheduler_run_id);
            CREATE TABLE IF NOT EXISTS acquisition_attempts (
                attempt_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                request_id TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                source_id TEXT NOT NULL,
                source_policy_version INTEGER NOT NULL,
                method TEXT NOT NULL,
                egress_profile TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                acquisition_failure_class TEXT,
                UNIQUE(request_id, attempt_number),
                FOREIGN KEY(request_id) REFERENCES acquisition_requests(request_id)
            );
            CREATE INDEX IF NOT EXISTS idx_acquisition_attempts_request
                ON acquisition_attempts(request_id, attempt_number);
            CREATE TABLE IF NOT EXISTS evidence_envelopes (
                evidence_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                request_id TEXT NOT NULL,
                attempt_id TEXT NOT NULL UNIQUE,
                scheduler_run_id TEXT NOT NULL,
                app_job_ref TEXT,
                source_id TEXT NOT NULL,
                source_policy_version INTEGER NOT NULL,
                execution_scope TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                provider_baseline_version INTEGER NOT NULL,
                egress_profile TEXT NOT NULL,
                fetch_method TEXT NOT NULL,
                started_at TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                requested_url TEXT NOT NULL,
                final_url TEXT,
                http_status INTEGER,
                media_type TEXT,
                content_length INTEGER NOT NULL,
                artifact_id TEXT NOT NULL,
                artifact_sha256 TEXT NOT NULL,
                artifact_bytes INTEGER NOT NULL,
                artifact_media_type TEXT NOT NULL,
                acquisition_failure_class TEXT,
                FOREIGN KEY(request_id) REFERENCES acquisition_requests(request_id),
                FOREIGN KEY(attempt_id) REFERENCES acquisition_attempts(attempt_id),
                FOREIGN KEY(scheduler_run_id) REFERENCES scheduler_runs(app_run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_evidence_source_fetched
                ON evidence_envelopes(source_id, fetched_at DESC);
            CREATE TABLE IF NOT EXISTS processing_records (
                processing_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                evidence_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                attempt_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                parser_version TEXT NOT NULL,
                normalizer_version TEXT NOT NULL,
                canonicalizer_version TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                status TEXT NOT NULL,
                processing_failure_class TEXT,
                items_found INTEGER NOT NULL DEFAULT 0,
                canonical_items INTEGER NOT NULL DEFAULT 0,
                signals_created INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(evidence_id) REFERENCES evidence_envelopes(evidence_id),
                FOREIGN KEY(request_id) REFERENCES acquisition_requests(request_id),
                FOREIGN KEY(attempt_id) REFERENCES acquisition_attempts(attempt_id)
            );
            CREATE INDEX IF NOT EXISTS idx_processing_source_finished
                ON processing_records(source_id, finished_at DESC);

            CREATE TABLE IF NOT EXISTS assurance_runs (
                assurance_run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                network_checks INTEGER NOT NULL DEFAULT 1,
                summary_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_assurance_runs_started
                ON assurance_runs(started_at DESC);

            CREATE TABLE IF NOT EXISTS coverage_audit_results (
                coverage_audit_id TEXT PRIMARY KEY,
                assurance_run_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                audit_method TEXT NOT NULL,
                status TEXT NOT NULL,
                official_candidate_count INTEGER NOT NULL DEFAULT 0,
                canonical_covered_count INTEGER NOT NULL DEFAULT 0,
                missing_count INTEGER NOT NULL DEFAULT 0,
                checked_at TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(assurance_run_id) REFERENCES assurance_runs(assurance_run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_coverage_audit_run_source
                ON coverage_audit_results(assurance_run_id, source_id);
            CREATE INDEX IF NOT EXISTS idx_coverage_audit_source_checked
                ON coverage_audit_results(source_id, checked_at DESC);

            CREATE TABLE IF NOT EXISTS noise_review_samples (
                noise_sample_id TEXT PRIMARY KEY,
                assurance_run_id TEXT,
                source_id TEXT NOT NULL,
                candidate_kind TEXT NOT NULL,
                candidate_ref TEXT NOT NULL,
                evidence_url TEXT,
                sample_basis TEXT NOT NULL,
                sampled_at TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                review_status TEXT NOT NULL DEFAULT 'PENDING',
                reviewed_at TEXT,
                reviewed_by TEXT,
                review_note TEXT,
                UNIQUE(source_id, candidate_kind, candidate_ref),
                FOREIGN KEY(assurance_run_id) REFERENCES assurance_runs(assurance_run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_noise_review_status_sampled
                ON noise_review_samples(review_status, sampled_at DESC);

            CREATE TABLE IF NOT EXISTS missed_signals (
                miss_id TEXT PRIMARY KEY,
                dedupe_key TEXT NOT NULL UNIQUE,
                source_id TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                detected_by TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT,
                reason TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                canonical_key TEXT,
                resolution_note TEXT,
                resolved_at TEXT,
                resolved_by TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_missed_signals_status_detected
                ON missed_signals(status, detected_at DESC);
            CREATE INDEX IF NOT EXISTS idx_missed_signals_source_status
                ON missed_signals(source_id, status);

            CREATE TABLE IF NOT EXISTS manual_promotions (
                promotion_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                url TEXT,
                reason TEXT NOT NULL,
                priority_band TEXT NOT NULL,
                deadline TEXT,
                location TEXT,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                resolved_at TEXT,
                resolved_by TEXT,
                resolution_note TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_manual_promotions_status_created
                ON manual_promotions(status, created_at DESC);

            CREATE TABLE IF NOT EXISTS manual_delivery_receipts (
                delivery_key TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                promotion_id TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                provider_message_id TEXT,
                sent_at TEXT NOT NULL,
                UNIQUE(channel, promotion_id),
                FOREIGN KEY(promotion_id) REFERENCES manual_promotions(promotion_id)
            );
            CREATE INDEX IF NOT EXISTS idx_manual_delivery_channel_sent
                ON manual_delivery_receipts(channel, sent_at DESC);

            CREATE TABLE IF NOT EXISTS metric_reviews (
                metric_review_id TEXT PRIMARY KEY,
                assurance_run_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                window_days INTEGER NOT NULL,
                status TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                conclusions_json TEXT NOT NULL,
                FOREIGN KEY(assurance_run_id) REFERENCES assurance_runs(assurance_run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_metric_reviews_observed
                ON metric_reviews(observed_at DESC);
            """
        )

        # Upgrade an existing R5 Gate O database in place without discarding
        # canonical/evidence state. Existing discovery rows represent the last
        # acknowledged sitemap snapshot, so they are backfilled as processed.
        discovery_had_fetched_lastmod = "fetched_lastmod" in _columns(conn, "discovery_items")
        source_had_reconciliation = "last_successful_reconciliation_at" in _columns(conn, "source_state")

        _add_column(conn, "source_state", "last_snapshot_at TEXT")
        _add_column(conn, "source_state", "last_successful_reconciliation_at TEXT")
        _add_column(conn, "source_state", "consecutive_failures INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, "source_state", "recovery_window_start TEXT")
        _add_column(conn, "source_state", "recovery_window_end TEXT")

        _add_column(conn, "discovery_items", "fetched_lastmod TEXT")
        _add_column(conn, "discovery_items", "pending_since_at TEXT")
        _add_column(conn, "discovery_items", "suppress_signal_once INTEGER NOT NULL DEFAULT 0")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_discovery_source_pending ON discovery_items(source_id,pending_since_at)"
        )

        _add_column(conn, "scheduler_runs", "recovery INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, "scheduler_runs", "outage_window_start TEXT")
        _add_column(conn, "scheduler_runs", "outage_window_end TEXT")
        _add_column(conn, "scheduler_runs", "backlog_remaining INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, "scheduler_runs", "details_attempted INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, "scheduler_runs", "details_succeeded INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, "scheduler_runs", "tenders_parsed INTEGER NOT NULL DEFAULT 0")
        items_parsed_added = _add_column(conn, "scheduler_runs", "items_parsed INTEGER NOT NULL DEFAULT 0")
        if items_parsed_added:
            conn.execute("UPDATE scheduler_runs SET items_parsed=tenders_parsed")

        _add_column(conn, "canonical_items", "item_kind TEXT NOT NULL DEFAULT 'TENDER'")
        _add_column(conn, "canonical_items", "title TEXT")
        conn.execute("UPDATE canonical_items SET item_kind='TENDER' WHERE item_kind IS NULL OR item_kind=''")
        conn.execute("UPDATE canonical_items SET title=project_name WHERE title IS NULL OR title=''")

        for acquisition_table in (
            "acquisition_requests",
            "acquisition_attempts",
            "evidence_envelopes",
            "processing_records",
        ):
            _add_column(conn, acquisition_table, "schema_version INTEGER NOT NULL DEFAULT 1")

        if not discovery_had_fetched_lastmod:
            conn.execute(
                "UPDATE discovery_items SET fetched_lastmod=lastmod,pending_since_at=NULL,suppress_signal_once=0"
            )
        if not source_had_reconciliation:
            conn.execute(
                """
                UPDATE source_state
                SET last_snapshot_at=COALESCE(last_snapshot_at,last_success_at),
                    last_successful_reconciliation_at=COALESCE(last_successful_reconciliation_at,last_success_at)
                """
            )

        existing_versions = [int(row[0]) for row in conn.execute("SELECT version FROM schema_meta ORDER BY version")]
        if existing_versions:
            first_version = min(existing_versions)
            for historical_version in range(first_version + 1, SCHEMA_VERSION):
                if conn.execute("SELECT 1 FROM schema_meta WHERE version=?", (historical_version,)).fetchone() is None:
                    conn.execute(
                        "INSERT INTO schema_meta(version, applied_at) VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
                        (historical_version,),
                    )

        exists = conn.execute("SELECT 1 FROM schema_meta WHERE version=?", (SCHEMA_VERSION,)).fetchone()
        if exists is None:
            conn.execute(
                "INSERT INTO schema_meta(version, applied_at) VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
                (SCHEMA_VERSION,),
            )
