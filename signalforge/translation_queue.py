from __future__ import annotations

import hashlib
import json
import re
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .db import connect

TRANSLATION_QUEUE_SCHEMA_VERSION = 1
TRANSLATION_PROVIDER_ID = "mac-oauth-llm"
TRANSLATION_SOURCE_LANGUAGE = "my"
TRANSLATION_TARGET_LANGUAGE = "zh-Hans"
MAX_VALUES = 12
MAX_TEXT_CHARS = 12_000
MAX_RESULT_CHARS = 36_000
REQUEST_STATES = {"PENDING", "CLAIMED", "SUCCEEDED", "FAILED", "EXPIRED", "CANCELLED"}
ATTEMPT_STATES = {"CLAIMED", "SUCCEEDED", "FAILED", "LEASE_EXPIRED"}
_PROTECTED_TOKEN = re.compile(
    r"(?<![\w])(?:"
    r"[A-Za-z][A-Za-z0-9]*[-/][A-Za-z0-9][A-Za-z0-9./()_-]*"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?"
    r"|\d+(?:[./:-]\d+)+"
    r"|\d+"
    r")(?![\w])"
)


class TranslationQueueError(RuntimeError):
    pass


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise TranslationQueueError("translation queue timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize_values(values: list[str]) -> list[str]:
    if not isinstance(values, list) or not values or len(values) > MAX_VALUES:
        raise TranslationQueueError(f"translation values must contain 1..{MAX_VALUES} entries")
    normalized = [str(value or "") for value in values]
    if sum(len(value) for value in normalized) > MAX_TEXT_CHARS:
        raise TranslationQueueError("translation input exceeds character limit")
    return normalized


def protected_tokens(value: str) -> list[str]:
    return sorted(set(_PROTECTED_TOKEN.findall(value)), key=lambda token: (len(token), token))


def translation_cache_key(values: list[str]) -> str:
    normalized = _normalize_values(values)
    body = {
        "schema_version": TRANSLATION_QUEUE_SCHEMA_VERSION,
        "source_language": TRANSLATION_SOURCE_LANGUAGE,
        "target_language": TRANSLATION_TARGET_LANGUAGE,
        "values": normalized,
    }
    return _sha256_bytes(_canonical_json(body))


def initialize_translation_queue(database: Path) -> None:
    with connect(database) as conn, conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS translation_requests (
                translation_request_id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                provider_id TEXT NOT NULL,
                source_language TEXT NOT NULL,
                target_language TEXT NOT NULL,
                cache_key TEXT NOT NULL,
                request_sha256 TEXT NOT NULL,
                request_json TEXT NOT NULL,
                state TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                claimed_at TEXT,
                claim_expires_at TEXT,
                current_translation_attempt_id TEXT,
                claim_token_sha256 TEXT,
                completed_at TEXT,
                result_sha256 TEXT,
                result_json TEXT,
                failure_class TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_translation_requests_claim
                ON translation_requests(provider_id,state,priority DESC,created_at ASC);
            CREATE INDEX IF NOT EXISTS idx_translation_requests_cache
                ON translation_requests(cache_key,created_at DESC);

            CREATE TABLE IF NOT EXISTS translation_attempts (
                translation_attempt_id TEXT PRIMARY KEY,
                translation_request_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                claimed_at TEXT NOT NULL,
                claim_expires_at TEXT NOT NULL,
                finished_at TEXT,
                state TEXT NOT NULL,
                failure_class TEXT,
                result_sha256 TEXT,
                model TEXT,
                duration_ms INTEGER,
                FOREIGN KEY(translation_request_id) REFERENCES translation_requests(translation_request_id)
            );
            CREATE INDEX IF NOT EXISTS idx_translation_attempts_request
                ON translation_attempts(translation_request_id,claimed_at DESC);

            CREATE TABLE IF NOT EXISTS translation_provider_state (
                provider_id TEXT PRIMARY KEY,
                last_poll_at TEXT,
                last_success_at TEXT,
                updated_at TEXT NOT NULL
            );
            """
        )


def _build_request(values: list[str], *, now: datetime, ttl_seconds: int) -> dict[str, Any]:
    normalized = _normalize_values(values)
    if ttl_seconds < 15 or ttl_seconds > 600:
        raise TranslationQueueError("translation request TTL must be 15..600 seconds")
    request_id = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "schema_version": TRANSLATION_QUEUE_SCHEMA_VERSION,
        "translation_request_id": request_id,
        "provider_id": TRANSLATION_PROVIDER_ID,
        "source_language": TRANSLATION_SOURCE_LANGUAGE,
        "target_language": TRANSLATION_TARGET_LANGUAGE,
        "values": normalized,
        "protected_tokens": [protected_tokens(value) for value in normalized],
        "requested_at": _iso(now),
        "expires_at": _iso(now + timedelta(seconds=ttl_seconds)),
        "cache_key": translation_cache_key(normalized),
    }
    payload["request_sha256"] = _sha256_bytes(_canonical_json(payload))
    return payload


def enqueue_translation_request(
    values: list[str],
    *,
    database: Path,
    priority: int = 0,
    now: datetime | None = None,
    ttl_seconds: int = 120,
) -> dict[str, Any]:
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    normalized = _normalize_values(values)
    cache_key = translation_cache_key(normalized)
    initialize_translation_queue(database)
    with connect(database) as conn:
        cached = conn.execute(
            "SELECT translation_request_id,result_json,result_sha256 FROM translation_requests "
            "WHERE cache_key=? AND state='SUCCEEDED' ORDER BY completed_at DESC LIMIT 1",
            (cache_key,),
        ).fetchone()
        if cached is not None:
            return {
                "status": "CACHED",
                "translation_request_id": str(cached["translation_request_id"]),
                "result_json": str(cached["result_json"]),
                "result_sha256": str(cached["result_sha256"]),
            }
        active = conn.execute(
            "SELECT translation_request_id,state FROM translation_requests "
            "WHERE cache_key=? AND state IN ('PENDING','CLAIMED') AND expires_at>? "
            "ORDER BY created_at DESC LIMIT 1",
            (cache_key, _iso(observed)),
        ).fetchone()
        if active is not None:
            return {
                "status": "ALREADY_ENQUEUED",
                "translation_request_id": str(active["translation_request_id"]),
                "state": str(active["state"]),
            }

    request = _build_request(normalized, now=observed, ttl_seconds=ttl_seconds)
    body = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with connect(database) as conn, conn:
        conn.execute(
            """
            INSERT INTO translation_requests(
                translation_request_id,schema_version,provider_id,source_language,target_language,
                cache_key,request_sha256,request_json,state,priority,created_at,requested_at,expires_at
            ) VALUES (?,?,?,?,?,?,?,?, 'PENDING', ?,?,?,?)
            """,
            (
                request["translation_request_id"],
                TRANSLATION_QUEUE_SCHEMA_VERSION,
                TRANSLATION_PROVIDER_ID,
                TRANSLATION_SOURCE_LANGUAGE,
                TRANSLATION_TARGET_LANGUAGE,
                request["cache_key"],
                request["request_sha256"],
                body,
                priority,
                _iso(observed),
                request["requested_at"],
                request["expires_at"],
            ),
        )
    return {
        "status": "ENQUEUED",
        "translation_request_id": request["translation_request_id"],
        "state": "PENDING",
    }


def _heartbeat(conn: Any, now: datetime, *, success: bool = False) -> None:
    now_text = _iso(now)
    conn.execute(
        """
        INSERT INTO translation_provider_state(provider_id,last_poll_at,last_success_at,updated_at)
        VALUES (?,?,?,?)
        ON CONFLICT(provider_id) DO UPDATE SET
            last_poll_at=excluded.last_poll_at,
            last_success_at=CASE WHEN excluded.last_success_at IS NOT NULL THEN excluded.last_success_at ELSE translation_provider_state.last_success_at END,
            updated_at=excluded.updated_at
        """,
        (TRANSLATION_PROVIDER_ID, now_text, now_text if success else None, now_text),
    )


def _recover_leases_and_expire(conn: Any, now: datetime) -> None:
    now_text = _iso(now)
    stale = conn.execute(
        "SELECT translation_request_id,current_translation_attempt_id FROM translation_requests "
        "WHERE state='CLAIMED' AND claim_expires_at<=? AND expires_at>?",
        (now_text, now_text),
    ).fetchall()
    for row in stale:
        attempt = row["current_translation_attempt_id"]
        if attempt:
            conn.execute(
                "UPDATE translation_attempts SET state='LEASE_EXPIRED',finished_at=? "
                "WHERE translation_attempt_id=? AND state='CLAIMED'",
                (now_text, str(attempt)),
            )
    conn.execute(
        """
        UPDATE translation_requests
        SET state='PENDING',claimed_at=NULL,claim_expires_at=NULL,
            current_translation_attempt_id=NULL,claim_token_sha256=NULL
        WHERE state='CLAIMED' AND claim_expires_at<=? AND expires_at>?
        """,
        (now_text, now_text),
    )
    expiring = conn.execute(
        "SELECT translation_request_id,current_translation_attempt_id FROM translation_requests "
        "WHERE state IN ('PENDING','CLAIMED') AND expires_at<=?",
        (now_text,),
    ).fetchall()
    for row in expiring:
        attempt = row["current_translation_attempt_id"]
        if attempt:
            conn.execute(
                "UPDATE translation_attempts SET state='FAILED',failure_class='TRANSLATION_REQUEST_EXPIRED',finished_at=? "
                "WHERE translation_attempt_id=? AND state='CLAIMED'",
                (now_text, str(attempt)),
            )
    conn.execute(
        """
        UPDATE translation_requests
        SET state='EXPIRED',completed_at=?,failure_class='TRANSLATION_REQUEST_EXPIRED',claim_token_sha256=NULL
        WHERE state IN ('PENDING','CLAIMED') AND expires_at<=?
        """,
        (now_text, now_text),
    )


def claim_next_translation_request(
    *,
    database: Path,
    now: datetime | None = None,
    lease_seconds: int = 45,
) -> dict[str, Any]:
    if lease_seconds < 15 or lease_seconds > 120:
        raise TranslationQueueError("translation lease must be 15..120 seconds")
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    initialize_translation_queue(database)
    token = secrets.token_urlsafe(32)
    attempt_id = str(uuid.uuid4())
    claim_expires = observed + timedelta(seconds=lease_seconds)
    with connect(database) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _heartbeat(conn, observed)
        _recover_leases_and_expire(conn, observed)
        row = conn.execute(
            "SELECT * FROM translation_requests WHERE provider_id=? AND state='PENDING' AND expires_at>? "
            "ORDER BY priority DESC,created_at ASC LIMIT 1",
            (TRANSLATION_PROVIDER_ID, _iso(observed)),
        ).fetchone()
        if row is None:
            conn.commit()
            return {"status": "NO_WORK", "provider_id": TRANSLATION_PROVIDER_ID}
        request_id = str(row["translation_request_id"])
        updated = conn.execute(
            """
            UPDATE translation_requests SET state='CLAIMED',claimed_at=?,claim_expires_at=?,
                current_translation_attempt_id=?,claim_token_sha256=?
            WHERE translation_request_id=? AND state='PENDING'
            """,
            (_iso(observed), _iso(claim_expires), attempt_id, _token_hash(token), request_id),
        ).rowcount
        if updated != 1:
            conn.rollback()
            raise TranslationQueueError("translation claim compare-and-swap failed")
        conn.execute(
            """
            INSERT INTO translation_attempts(
                translation_attempt_id,translation_request_id,provider_id,claimed_at,claim_expires_at,state
            ) VALUES (?,?,?,?,?,'CLAIMED')
            """,
            (attempt_id, request_id, TRANSLATION_PROVIDER_ID, _iso(observed), _iso(claim_expires)),
        )
        conn.commit()
    request = json.loads(str(row["request_json"]))
    return {
        "status": "CLAIMED",
        "provider_id": TRANSLATION_PROVIDER_ID,
        "translation_request_id": request_id,
        "translation_attempt_id": attempt_id,
        "claim_token": token,
        "claim_expires_at": _iso(claim_expires),
        "request": request,
    }


def _validate_claim(
    *,
    conn: Any,
    translation_request_id: str,
    translation_attempt_id: str,
    claim_token: str,
) -> Any:
    row = conn.execute(
        "SELECT * FROM translation_requests WHERE translation_request_id=?",
        (translation_request_id,),
    ).fetchone()
    if row is None:
        raise TranslationQueueError("translation request not found")
    if str(row["state"]) != "CLAIMED":
        raise TranslationQueueError(f"translation request is not CLAIMED: {row['state']}")
    if str(row["current_translation_attempt_id"]) != translation_attempt_id:
        raise TranslationQueueError("translation attempt does not own current claim")
    if not secrets.compare_digest(str(row["claim_token_sha256"]), _token_hash(claim_token)):
        raise TranslationQueueError("translation claim token mismatch")
    return row


def _validated_result(request: dict[str, Any], values: object) -> list[str]:
    originals = request.get("values")
    protected = request.get("protected_tokens")
    if not isinstance(originals, list) or not isinstance(protected, list):
        raise TranslationQueueError("translation request payload invalid")
    if not isinstance(values, list) or len(values) != len(originals):
        raise TranslationQueueError("translation result count mismatch")
    result: list[str] = []
    total = 0
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise TranslationQueueError("translation result contains empty/non-string value")
        text = value.strip()
        total += len(text)
        if total > MAX_RESULT_CHARS:
            raise TranslationQueueError("translation result exceeds character limit")
        required = protected[index] if index < len(protected) and isinstance(protected[index], list) else []
        for token in required:
            if isinstance(token, str) and token and token not in text:
                raise TranslationQueueError(f"translation result changed protected token: {token}")
        result.append(text)
    return result


def complete_translation_claim(
    *,
    translation_request_id: str,
    translation_attempt_id: str,
    claim_token: str,
    request_sha256: str,
    values: object,
    model: str,
    duration_ms: int | None,
    usage: object | None,
    database: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    initialize_translation_queue(database)
    with connect(database) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = _validate_claim(
            conn=conn,
            translation_request_id=translation_request_id,
            translation_attempt_id=translation_attempt_id,
            claim_token=claim_token,
        )
        if str(row["request_sha256"]) != request_sha256:
            conn.rollback()
            raise TranslationQueueError("translation result request SHA mismatch")
        request = json.loads(str(row["request_json"]))
        translated = _validated_result(request, values)
        result = {
            "schema_version": TRANSLATION_QUEUE_SCHEMA_VERSION,
            "provider_id": TRANSLATION_PROVIDER_ID,
            "source_language": TRANSLATION_SOURCE_LANGUAGE,
            "target_language": TRANSLATION_TARGET_LANGUAGE,
            "values": translated,
            "model": str(model or "unknown"),
            "duration_ms": duration_ms if isinstance(duration_ms, int) and duration_ms >= 0 else None,
            "usage": usage if isinstance(usage, dict) else None,
        }
        result_json = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = _sha256_bytes(result_json.encode("utf-8"))
        now_text = _iso(observed)
        conn.execute(
            """
            UPDATE translation_requests SET state='SUCCEEDED',completed_at=?,result_sha256=?,result_json=?,
                failure_class=NULL,claim_token_sha256=NULL
            WHERE translation_request_id=?
            """,
            (now_text, digest, result_json, translation_request_id),
        )
        conn.execute(
            """
            UPDATE translation_attempts SET state='SUCCEEDED',finished_at=?,result_sha256=?,model=?,duration_ms=?
            WHERE translation_attempt_id=?
            """,
            (now_text, digest, str(model or "unknown"), duration_ms, translation_attempt_id),
        )
        _heartbeat(conn, observed, success=True)
        conn.commit()
    return {
        "status": "SUCCEEDED",
        "translation_request_id": translation_request_id,
        "result_sha256": digest,
    }


def fail_translation_claim(
    *,
    translation_request_id: str,
    translation_attempt_id: str,
    claim_token: str,
    failure_class: str,
    database: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    initialize_translation_queue(database)
    failure = str(failure_class or "TRANSLATION_PROVIDER_FAILED")[:128]
    with connect(database) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _validate_claim(
            conn=conn,
            translation_request_id=translation_request_id,
            translation_attempt_id=translation_attempt_id,
            claim_token=claim_token,
        )
        now_text = _iso(observed)
        conn.execute(
            "UPDATE translation_requests SET state='FAILED',completed_at=?,failure_class=?,claim_token_sha256=NULL "
            "WHERE translation_request_id=?",
            (now_text, failure, translation_request_id),
        )
        conn.execute(
            "UPDATE translation_attempts SET state='FAILED',finished_at=?,failure_class=? WHERE translation_attempt_id=?",
            (now_text, failure, translation_attempt_id),
        )
        _heartbeat(conn, observed)
        conn.commit()
    return {"status": "FAILED", "translation_request_id": translation_request_id, "failure_class": failure}


def translation_request_result(*, translation_request_id: str, database: Path) -> dict[str, Any] | None:
    initialize_translation_queue(database)
    with connect(database) as conn:
        row = conn.execute(
            "SELECT state,result_json,result_sha256,failure_class FROM translation_requests WHERE translation_request_id=?",
            (translation_request_id,),
        ).fetchone()
    if row is None:
        return None
    result: dict[str, Any] = {"state": str(row["state"]), "translation_request_id": translation_request_id}
    if row["result_json"]:
        result["result"] = json.loads(str(row["result_json"]))
        result["result_sha256"] = str(row["result_sha256"])
    if row["failure_class"]:
        result["failure_class"] = str(row["failure_class"])
    return result


def request_translation_and_wait(
    values: list[str],
    *,
    database: Path,
    wait_seconds: float = 20.0,
    poll_seconds: float = 0.25,
    ttl_seconds: int = 120,
) -> tuple[list[str], bool]:
    normalized = _normalize_values(values)
    queued = enqueue_translation_request(normalized, database=database, ttl_seconds=ttl_seconds)
    if queued.get("status") == "CACHED":
        try:
            payload = json.loads(str(queued["result_json"]))
            translated = _validated_result(
                {"values": normalized, "protected_tokens": [protected_tokens(value) for value in normalized]},
                payload.get("values") if isinstance(payload, dict) else None,
            )
            return translated, True
        except (json.JSONDecodeError, TranslationQueueError):
            return normalized, False
    request_id = str(queued["translation_request_id"])
    deadline = time.monotonic() + max(0.0, wait_seconds)
    while True:
        current = translation_request_result(translation_request_id=request_id, database=database)
        if current and current.get("state") == "SUCCEEDED":
            payload = current.get("result")
            try:
                translated = _validated_result(
                    {"values": normalized, "protected_tokens": [protected_tokens(value) for value in normalized]},
                    payload.get("values") if isinstance(payload, dict) else None,
                )
                return translated, True
            except TranslationQueueError:
                return normalized, False
        if current and current.get("state") in {"FAILED", "EXPIRED", "CANCELLED"}:
            return normalized, False
        if time.monotonic() >= deadline:
            return normalized, False
        time.sleep(max(0.05, min(1.0, poll_seconds)))


def translation_queue_status(*, database: Path, now: datetime | None = None) -> dict[str, Any]:
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    initialize_translation_queue(database)
    with connect(database) as conn, conn:
        _recover_leases_and_expire(conn, observed)
        rows = conn.execute(
            "SELECT state,COUNT(*) AS n FROM translation_requests GROUP BY state"
        ).fetchall()
        provider = conn.execute(
            "SELECT last_poll_at,last_success_at,updated_at FROM translation_provider_state WHERE provider_id=?",
            (TRANSLATION_PROVIDER_ID,),
        ).fetchone()
    counts = {state: 0 for state in sorted(REQUEST_STATES)}
    for row in rows:
        counts[str(row["state"])] = int(row["n"])
    last_poll_at = str(provider["last_poll_at"]) if provider is not None and provider["last_poll_at"] else None
    age_seconds: int | None = None
    if last_poll_at:
        age_seconds = max(0, int((observed - _parse_time(last_poll_at)).total_seconds()))
    return {
        "status": "PASS",
        "provider_id": TRANSLATION_PROVIDER_ID,
        "source_language": TRANSLATION_SOURCE_LANGUAGE,
        "target_language": TRANSLATION_TARGET_LANGUAGE,
        "counts": counts,
        "last_poll_at": last_poll_at,
        "last_success_at": str(provider["last_success_at"]) if provider is not None and provider["last_success_at"] else None,
        "poll_age_seconds": age_seconds,
        "ready": age_seconds is not None and age_seconds <= 30,
    }
