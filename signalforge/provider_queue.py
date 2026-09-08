from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .db import connect
from .provider_invocation import ProviderInvocationError, validate_provider_request


PROVIDER_QUEUE_SCHEMA_VERSION = 1
REQUEST_STATES = {"PENDING", "CLAIMED", "SUCCEEDED", "FAILED", "EXPIRED", "CANCELLED"}
ATTEMPT_STATES = {"CLAIMED", "SUCCEEDED", "FAILED", "LEASE_EXPIRED"}


class ProviderQueueError(RuntimeError):
    pass


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ProviderQueueError("queue timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def initialize_provider_queue(database: Path) -> None:
    with connect(database) as conn, conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS provider_requests (
                provider_request_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                provider_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                capability TEXT NOT NULL,
                target_role TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                request_sha256 TEXT NOT NULL,
                request_json TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                claimed_at TEXT,
                claim_expires_at TEXT,
                current_provider_attempt_id TEXT,
                claim_token_sha256 TEXT,
                completed_at TEXT,
                result_sha256 TEXT,
                browser_job_id TEXT,
                failure_class TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_provider_requests_claim
                ON provider_requests(provider_id, state, priority DESC, created_at ASC);
            CREATE INDEX IF NOT EXISTS idx_provider_requests_source_created
                ON provider_requests(source_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS provider_attempts (
                provider_attempt_id TEXT PRIMARY KEY,
                provider_request_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                claimed_at TEXT NOT NULL,
                claim_expires_at TEXT NOT NULL,
                finished_at TEXT,
                state TEXT NOT NULL,
                failure_class TEXT,
                result_sha256 TEXT,
                browser_job_id TEXT,
                FOREIGN KEY(provider_request_id) REFERENCES provider_requests(provider_request_id)
            );
            CREATE INDEX IF NOT EXISTS idx_provider_attempts_request
                ON provider_attempts(provider_request_id, claimed_at DESC);
            """
        )


def enqueue_provider_request(
    request: dict[str, Any],
    *,
    contract: dict[str, Any],
    database: Path,
    priority: int = 0,
    now: datetime | None = None,
) -> dict[str, Any]:
    observed_now = (now or datetime.now(UTC)).astimezone(UTC)
    validate_provider_request(request, contract=contract, now=observed_now)
    if not isinstance(priority, int):
        raise ProviderQueueError("provider request priority must be integer")
    initialize_provider_queue(database)

    provider_request_id = str(request["provider_request_id"])
    digest = str(request["request_sha256"])
    body = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with connect(database) as conn, conn:
        existing = conn.execute(
            "SELECT request_sha256,state FROM provider_requests WHERE provider_request_id=?",
            (provider_request_id,),
        ).fetchone()
        if existing is not None:
            if str(existing["request_sha256"]) != digest:
                raise ProviderQueueError("provider request idempotency conflict")
            return {
                "status": "ALREADY_ENQUEUED",
                "provider_request_id": provider_request_id,
                "state": str(existing["state"]),
            }
        conn.execute(
            """
            INSERT INTO provider_requests(
                provider_request_id,schema_version,provider_id,source_id,capability,target_role,
                priority,request_sha256,request_json,state,created_at,requested_at,expires_at
            ) VALUES (?,?,?,?,?,?,?,?,?,'PENDING',?,?,?)
            """,
            (
                provider_request_id,
                PROVIDER_QUEUE_SCHEMA_VERSION,
                str(request["provider_id"]),
                str(request["source_id"]),
                str(request["capability"]),
                str(request["target_role"]),
                priority,
                digest,
                body,
                _iso(observed_now),
                str(request["requested_at"]),
                str(request["expires_at"]),
            ),
        )
    return {"status": "ENQUEUED", "provider_request_id": provider_request_id, "state": "PENDING"}


def _recover_leases_and_expire(conn: sqlite3.Connection, now: datetime) -> None:
    now_text = _iso(now)
    stale = conn.execute(
        """
        SELECT provider_request_id,current_provider_attempt_id
        FROM provider_requests
        WHERE state='CLAIMED' AND claim_expires_at<=? AND expires_at>?
        """,
        (now_text, now_text),
    ).fetchall()
    for row in stale:
        attempt_id = row["current_provider_attempt_id"]
        if attempt_id:
            conn.execute(
                "UPDATE provider_attempts SET state='LEASE_EXPIRED',finished_at=? WHERE provider_attempt_id=? AND state='CLAIMED'",
                (now_text, str(attempt_id)),
            )
    conn.execute(
        """
        UPDATE provider_requests
        SET state='PENDING',claimed_at=NULL,claim_expires_at=NULL,
            current_provider_attempt_id=NULL,claim_token_sha256=NULL
        WHERE state='CLAIMED' AND claim_expires_at<=? AND expires_at>?
        """,
        (now_text, now_text),
    )

    expiring = conn.execute(
        """
        SELECT current_provider_attempt_id FROM provider_requests
        WHERE state IN ('PENDING','CLAIMED') AND expires_at<=?
        """,
        (now_text,),
    ).fetchall()
    for row in expiring:
        attempt_id = row["current_provider_attempt_id"]
        if attempt_id:
            conn.execute(
                "UPDATE provider_attempts SET state='FAILED',failure_class='PROVIDER_REQUEST_EXPIRED',finished_at=? WHERE provider_attempt_id=? AND state='CLAIMED'",
                (now_text, str(attempt_id)),
            )
    conn.execute(
        """
        UPDATE provider_requests
        SET state='EXPIRED',completed_at=?,failure_class='PROVIDER_REQUEST_EXPIRED',
            claim_token_sha256=NULL
        WHERE state IN ('PENDING','CLAIMED') AND expires_at<=?
        """,
        (now_text, now_text),
    )


def claim_next_provider_request(
    *,
    provider_id: str,
    database: Path,
    now: datetime | None = None,
    lease_seconds: int = 60,
) -> dict[str, Any]:
    if not provider_id:
        raise ProviderQueueError("provider_id missing")
    if not isinstance(lease_seconds, int) or lease_seconds < 1 or lease_seconds > 300:
        raise ProviderQueueError("lease_seconds must be 1..300")
    initialize_provider_queue(database)
    observed_now = (now or datetime.now(UTC)).astimezone(UTC)
    now_text = _iso(observed_now)

    with connect(database) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _recover_leases_and_expire(conn, observed_now)
        row = conn.execute(
            """
            SELECT * FROM provider_requests
            WHERE provider_id=? AND state='PENDING' AND expires_at>?
            ORDER BY priority DESC,created_at ASC,provider_request_id ASC
            LIMIT 1
            """,
            (provider_id, now_text),
        ).fetchone()
        if row is None:
            conn.commit()
            return {"status": "NO_WORK", "provider_id": provider_id}

        attempt_id = str(uuid.uuid4())
        claim_token = secrets.token_urlsafe(32)
        claim_expires_at = min(
            observed_now + timedelta(seconds=lease_seconds),
            _parse_time(str(row["expires_at"])),
        )
        claim_expires_text = _iso(claim_expires_at)
        conn.execute(
            """
            INSERT INTO provider_attempts(
                provider_attempt_id,provider_request_id,provider_id,claimed_at,claim_expires_at,state
            ) VALUES (?,?,?,?,?,'CLAIMED')
            """,
            (attempt_id, str(row["provider_request_id"]), provider_id, now_text, claim_expires_text),
        )
        updated = conn.execute(
            """
            UPDATE provider_requests
            SET state='CLAIMED',claimed_at=?,claim_expires_at=?,current_provider_attempt_id=?,claim_token_sha256=?
            WHERE provider_request_id=? AND state='PENDING'
            """,
            (
                now_text,
                claim_expires_text,
                attempt_id,
                _token_hash(claim_token),
                str(row["provider_request_id"]),
            ),
        )
        if updated.rowcount != 1:
            conn.rollback()
            raise ProviderQueueError("atomic provider claim lost")
        conn.commit()

    return {
        "status": "CLAIMED",
        "provider_id": provider_id,
        "provider_request_id": str(row["provider_request_id"]),
        "provider_attempt_id": attempt_id,
        "claim_token": claim_token,
        "claim_expires_at": claim_expires_text,
        "request": json.loads(str(row["request_json"])),
    }


def complete_provider_claim(
    *,
    provider_request_id: str,
    provider_attempt_id: str,
    claim_token: str,
    result_sha256: str,
    browser_job_id: str,
    database: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not _valid_sha256(result_sha256):
        raise ProviderQueueError("result_sha256 invalid")
    if not browser_job_id:
        raise ProviderQueueError("browser_job_id missing")
    initialize_provider_queue(database)
    observed_now = (now or datetime.now(UTC)).astimezone(UTC)
    now_text = _iso(observed_now)

    with connect(database) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM provider_requests WHERE provider_request_id=?",
            (provider_request_id,),
        ).fetchone()
        if row is None:
            conn.rollback()
            raise ProviderQueueError("provider request not found")
        if str(row["state"]) == "SUCCEEDED":
            same = str(row["result_sha256"]) == result_sha256 and str(row["browser_job_id"]) == browser_job_id
            conn.commit()
            if same:
                return {"status": "ALREADY_ACCEPTED", "provider_request_id": provider_request_id}
            raise ProviderQueueError("provider result idempotency conflict")
        if str(row["state"]) != "CLAIMED":
            conn.rollback()
            raise ProviderQueueError(f"provider request is not CLAIMED: {row['state']}")
        if str(row["current_provider_attempt_id"]) != provider_attempt_id:
            conn.rollback()
            raise ProviderQueueError("provider attempt does not own current claim")
        if not secrets.compare_digest(str(row["claim_token_sha256"]), _token_hash(claim_token)):
            conn.rollback()
            raise ProviderQueueError("provider claim token mismatch")
        if _parse_time(str(row["expires_at"])) <= observed_now:
            conn.rollback()
            raise ProviderQueueError("provider request expired before completion")
        if _parse_time(str(row["claim_expires_at"])) <= observed_now:
            conn.rollback()
            raise ProviderQueueError("provider claim lease expired before completion")

        conn.execute(
            """
            UPDATE provider_requests
            SET state='SUCCEEDED',completed_at=?,result_sha256=?,browser_job_id=?,claim_token_sha256=NULL
            WHERE provider_request_id=?
            """,
            (now_text, result_sha256, browser_job_id, provider_request_id),
        )
        conn.execute(
            """
            UPDATE provider_attempts
            SET state='SUCCEEDED',finished_at=?,result_sha256=?,browser_job_id=?
            WHERE provider_attempt_id=?
            """,
            (now_text, result_sha256, browser_job_id, provider_attempt_id),
        )
        conn.commit()
    return {"status": "ACCEPTED", "provider_request_id": provider_request_id, "state": "SUCCEEDED"}


def fail_provider_claim(
    *,
    provider_request_id: str,
    provider_attempt_id: str,
    claim_token: str,
    failure_class: str,
    database: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not failure_class.startswith("PROVIDER_"):
        raise ProviderQueueError("provider failure_class must use PROVIDER_ namespace")
    initialize_provider_queue(database)
    observed_now = (now or datetime.now(UTC)).astimezone(UTC)
    now_text = _iso(observed_now)
    with connect(database) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM provider_requests WHERE provider_request_id=?",
            (provider_request_id,),
        ).fetchone()
        if row is None or str(row["state"]) != "CLAIMED":
            conn.rollback()
            raise ProviderQueueError("provider request is not actively claimed")
        if str(row["current_provider_attempt_id"]) != provider_attempt_id:
            conn.rollback()
            raise ProviderQueueError("provider attempt does not own current claim")
        if not secrets.compare_digest(str(row["claim_token_sha256"]), _token_hash(claim_token)):
            conn.rollback()
            raise ProviderQueueError("provider claim token mismatch")
        conn.execute(
            """
            UPDATE provider_requests
            SET state='FAILED',completed_at=?,failure_class=?,claim_token_sha256=NULL
            WHERE provider_request_id=?
            """,
            (now_text, failure_class, provider_request_id),
        )
        conn.execute(
            """
            UPDATE provider_attempts
            SET state='FAILED',finished_at=?,failure_class=?
            WHERE provider_attempt_id=?
            """,
            (now_text, failure_class, provider_attempt_id),
        )
        conn.commit()
    return {"status": "FAILED_ACCEPTED", "provider_request_id": provider_request_id, "state": "FAILED"}


def provider_queue_status(*, provider_id: str, database: Path, now: datetime | None = None) -> dict[str, Any]:
    initialize_provider_queue(database)
    observed_now = (now or datetime.now(UTC)).astimezone(UTC)
    with connect(database) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _recover_leases_and_expire(conn, observed_now)
        rows = conn.execute(
            "SELECT state,COUNT(*) AS n FROM provider_requests WHERE provider_id=? GROUP BY state",
            (provider_id,),
        ).fetchall()
        conn.commit()
    counts = {state: 0 for state in sorted(REQUEST_STATES)}
    for row in rows:
        counts[str(row["state"])] = int(row["n"])
    return {"provider_id": provider_id, "counts": counts}
