from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from .acquisition_contract import (
    ACQUISITION_SCHEMA_VERSION,
    LOCAL_EXECUTION_SCOPE,
    LOCAL_PROVIDER_BASELINE_VERSION,
    LOCAL_PROVIDER_ID,
    ProcessingFailure,
    REQUEST_REASONS,
    classify_acquisition_failure,
)
from .config import repo_root
from .db import connect
from .provider_invocation import ProviderCapability, build_provider_request, validate_contract_projection
from .provider_queue import enqueue_provider_request, initialize_provider_queue


Fetcher = Callable[..., bytes]


@dataclass(frozen=True)
class AcquisitionCapture:
    payload: bytes
    request_id: str
    attempt_id: str
    evidence_id: str
    sha256: str


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _app_job_ref(source_id: str, target_ref: str) -> str:
    digest = hashlib.sha256(target_ref.encode("utf-8")).hexdigest()[:20]
    return f"{source_id}:{digest}"


def acquire_local_bytes(
    *,
    database: Path,
    scheduler_run_id: str,
    source_id: str,
    source_policy_version: int,
    reason: str,
    egress_profile: str,
    target_kind: str,
    url: str,
    timeout_seconds: int,
    max_bytes: int,
    expected_content_types: list[str],
    observed_at: str,
    fetcher: Fetcher,
) -> AcquisitionCapture:
    if reason not in REQUEST_REASONS:
        raise ValueError(f"unsupported acquisition reason: {reason}")
    if target_kind not in {"DISCOVERY", "HTML"}:
        raise ValueError(f"unsupported v1.5 local target kind: {target_kind}")
    if not expected_content_types or not all(isinstance(item, str) and item for item in expected_content_types):
        raise ValueError("expected_content_types must be non-empty strings")

    request_id = str(uuid.uuid4())
    attempt_id = str(uuid.uuid4())
    app_job_ref = _app_job_ref(source_id, url)

    with connect(database) as conn, conn:
        conn.execute(
            """
            INSERT INTO acquisition_requests(
                request_id,schema_version,scheduler_run_id,app_job_ref,source_id,source_policy_version,mode,reason,
                egress_profile,requested_at,primary_method,target_kind,timeout_seconds,expected_content_types_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                request_id,
                ACQUISITION_SCHEMA_VERSION,
                scheduler_run_id,
                app_job_ref,
                source_id,
                source_policy_version,
                "production",
                reason,
                egress_profile,
                observed_at,
                "DIRECT_HTTP",
                target_kind,
                timeout_seconds,
                _json(expected_content_types),
            ),
        )
        conn.execute(
            """
            INSERT INTO acquisition_attempts(
                attempt_id,schema_version,request_id,attempt_number,source_id,source_policy_version,method,egress_profile,
                started_at,status
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                attempt_id,
                ACQUISITION_SCHEMA_VERSION,
                request_id,
                1,
                source_id,
                source_policy_version,
                "DIRECT_HTTP",
                egress_profile,
                observed_at,
                "RUNNING",
            ),
        )

    try:
        payload = fetcher(url, timeout=timeout_seconds, max_bytes=max_bytes)
    except Exception as exc:
        failure = classify_acquisition_failure(exc).value
        with connect(database) as conn, conn:
            conn.execute(
                "UPDATE acquisition_attempts SET finished_at=?,status='FAILED',acquisition_failure_class=? WHERE attempt_id=?",
                (observed_at, failure, attempt_id),
            )
        raise

    digest = hashlib.sha256(payload).hexdigest()
    evidence_id = str(uuid.uuid4())
    media_type = expected_content_types[0] if expected_content_types else "application/octet-stream"
    with connect(database) as conn, conn:
        conn.execute(
            "UPDATE acquisition_attempts SET finished_at=?,status='SUCCESS',acquisition_failure_class=NULL WHERE attempt_id=?",
            (observed_at, attempt_id),
        )
        conn.execute(
            """
            INSERT INTO evidence_envelopes(
                evidence_id,schema_version,request_id,attempt_id,scheduler_run_id,app_job_ref,source_id,source_policy_version,
                execution_scope,provider_id,provider_baseline_version,egress_profile,fetch_method,started_at,fetched_at,
                requested_url,final_url,http_status,media_type,content_length,artifact_id,artifact_sha256,artifact_bytes,
                artifact_media_type,acquisition_failure_class
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                evidence_id,
                ACQUISITION_SCHEMA_VERSION,
                request_id,
                attempt_id,
                scheduler_run_id,
                app_job_ref,
                source_id,
                source_policy_version,
                LOCAL_EXECUTION_SCOPE,
                LOCAL_PROVIDER_ID,
                LOCAL_PROVIDER_BASELINE_VERSION,
                egress_profile,
                "DIRECT_HTTP",
                observed_at,
                observed_at,
                url,
                None,
                200,
                media_type,
                len(payload),
                f"sha256:{digest}",
                digest,
                len(payload),
                media_type,
                None,
            ),
        )
    return AcquisitionCapture(payload, request_id, attempt_id, evidence_id, digest)


PROVIDER_EXECUTION_SCOPE = "REMOTE_MAC_PROVIDER"
PROVIDER_ID = "mac-mm-01"
PROVIDER_BASELINE_VERSION = 1
PROVIDER_CONTRACT_NAME = "Provider-Invocation-Contract-v1.json"
PROVIDER_TERMINAL_FAILURES = {"FAILED", "EXPIRED", "CANCELLED"}


def _load_provider_contract() -> dict:
    path = repo_root() / "registry" / PROVIDER_CONTRACT_NAME
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot load production provider contract: {exc}") from exc
    validate_contract_projection(value)
    if value.get("enabled") is not True:
        raise RuntimeError("production provider contract is disabled")
    return value


def acquire_provider_bytes(
    *,
    database: Path,
    scheduler_run_id: str,
    source_id: str,
    source_policy_version: int,
    reason: str,
    egress_profile: str,
    target_kind: str,
    target_role: str,
    url: str,
    timeout_seconds: int,
    max_bytes: int,
    expected_content_types: list[str],
    observed_at: str,
    capability: str = ProviderCapability.C0_FETCH.value,
    poll_interval_seconds: float = 0.5,
    sleeper: Callable[[float], None] = time.sleep,
) -> AcquisitionCapture:
    if reason not in REQUEST_REASONS:
        raise ValueError(f"unsupported acquisition reason: {reason}")
    if target_kind not in {"DISCOVERY", "HTML"}:
        raise ValueError(f"unsupported provider target kind: {target_kind}")
    if egress_profile != "mac-direct":
        raise ValueError("provider acquisition must use mac-direct")
    if not expected_content_types or not all(isinstance(item, str) and item for item in expected_content_types):
        raise ValueError("expected_content_types must be non-empty strings")

    contract = _load_provider_contract()
    request_id = str(uuid.uuid4())
    attempt_id = str(uuid.uuid4())
    app_job_ref = _app_job_ref(source_id, url)
    requested_time = datetime.fromisoformat(observed_at.replace("Z", "+00:00")).astimezone(UTC)
    ttl_seconds = min(int(contract["limits"]["max_request_ttl_seconds"]), max(timeout_seconds + 30, 60))

    with connect(database) as conn, conn:
        conn.execute(
            """
            INSERT INTO acquisition_requests(
                request_id,schema_version,scheduler_run_id,app_job_ref,source_id,source_policy_version,mode,reason,
                egress_profile,requested_at,primary_method,target_kind,timeout_seconds,expected_content_types_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                request_id, ACQUISITION_SCHEMA_VERSION, scheduler_run_id, app_job_ref, source_id, source_policy_version,
                "production", reason, egress_profile, observed_at, "MAC_BROWSER_PROVIDER", target_kind,
                timeout_seconds, _json(expected_content_types),
            ),
        )
        conn.execute(
            """
            INSERT INTO acquisition_attempts(
                attempt_id,schema_version,request_id,attempt_number,source_id,source_policy_version,method,egress_profile,
                started_at,status
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (attempt_id, ACQUISITION_SCHEMA_VERSION, request_id, 1, source_id, source_policy_version,
             "MAC_BROWSER_PROVIDER", egress_profile, observed_at, "RUNNING"),
        )

    provider_request = build_provider_request(
        contract=contract,
        source_id=source_id,
        source_policy_version=source_policy_version,
        capability=capability,
        target_role=target_role,
        requested_url=url,
        signalforge_job_id=scheduler_run_id,
        acquisition_request_id=request_id,
        acquisition_attempt_id=attempt_id,
        max_bytes=max_bytes,
        max_run_seconds=min(timeout_seconds, int(contract["limits"]["max_run_seconds"])),
        now=requested_time,
        ttl_seconds=ttl_seconds,
    )
    initialize_provider_queue(database)
    enqueue_provider_request(provider_request, contract=contract, database=database, priority=100, now=requested_time)

    deadline = time.monotonic() + timeout_seconds
    row = None
    while time.monotonic() < deadline:
        with connect(database) as conn:
            row = conn.execute(
                "SELECT * FROM provider_requests WHERE provider_request_id=?",
                (provider_request["provider_request_id"],),
            ).fetchone()
        if row is not None and str(row["state"]) == "SUCCEEDED":
            break
        if row is not None and str(row["state"]) in PROVIDER_TERMINAL_FAILURES:
            failure = str(row["failure_class"] or "PROVIDER_RESULT_INVALID")
            with connect(database) as conn, conn:
                conn.execute(
                    "UPDATE acquisition_attempts SET finished_at=?,status='FAILED',acquisition_failure_class=? WHERE attempt_id=?",
                    (observed_at, failure, attempt_id),
                )
            raise RuntimeError(f"provider acquisition failed: {failure}")
        sleeper(max(0.05, poll_interval_seconds))
    else:
        with connect(database) as conn, conn:
            conn.execute(
                "UPDATE acquisition_attempts SET finished_at=?,status='FAILED',acquisition_failure_class='PROVIDER_TIMEOUT' WHERE attempt_id=?",
                (observed_at, attempt_id),
            )
        raise TimeoutError(f"provider acquisition timed out: {source_id} {target_role}")

    assert row is not None
    try:
        artifact_path = Path(str(row["result_artifact_path"] or ""))
        if not artifact_path.is_file():
            raise RuntimeError("provider result artifact missing")
        payload = artifact_path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != str(row["result_sha256"] or "") or len(payload) != int(row["result_artifact_bytes"] or -1):
            raise RuntimeError("provider artifact integrity mismatch")
        media_type = str(row["result_media_type"] or "")
        if media_type not in expected_content_types:
            raise RuntimeError(f"provider content type mismatch: {media_type}")
        if str(row["result_request_sha256"] or "") != str(provider_request["request_sha256"]):
            raise RuntimeError("provider request/result correlation mismatch")
    except Exception as exc:
        failure = "PROVIDER_ARTIFACT_HASH_MISMATCH" if "integrity" in str(exc) else "PROVIDER_RESULT_INVALID"
        with connect(database) as conn, conn:
            conn.execute(
                "UPDATE acquisition_attempts SET finished_at=?,status='FAILED',acquisition_failure_class=? WHERE attempt_id=?",
                (str(row["completed_at"] or observed_at), failure, attempt_id),
            )
        raise

    evidence_id = str(uuid.uuid4())
    with connect(database) as conn, conn:
        conn.execute(
            "UPDATE acquisition_attempts SET finished_at=?,status='SUCCESS',acquisition_failure_class=NULL WHERE attempt_id=?",
            (str(row["completed_at"] or observed_at), attempt_id),
        )
        conn.execute(
            """
            INSERT INTO evidence_envelopes(
                evidence_id,schema_version,request_id,attempt_id,scheduler_run_id,app_job_ref,source_id,source_policy_version,
                execution_scope,provider_id,provider_baseline_version,egress_profile,fetch_method,started_at,fetched_at,
                requested_url,final_url,http_status,media_type,content_length,artifact_id,artifact_sha256,artifact_bytes,
                artifact_media_type,acquisition_failure_class
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                evidence_id, ACQUISITION_SCHEMA_VERSION, request_id, attempt_id, scheduler_run_id, app_job_ref,
                source_id, source_policy_version, PROVIDER_EXECUTION_SCOPE, PROVIDER_ID, PROVIDER_BASELINE_VERSION,
                egress_profile, f"PROVIDER_{capability}", observed_at, str(row["completed_at"] or observed_at),
                url, row["result_final_url"], row["result_http_status"], media_type, len(payload),
                f"sha256:{digest}", digest, len(payload), media_type, None,
            ),
        )
    return AcquisitionCapture(payload, request_id, attempt_id, evidence_id, digest)


def record_processing(
    *,
    database: Path,
    capture: AcquisitionCapture,
    source_id: str,
    observed_at: str,
    parser_version: str,
    normalizer_version: str,
    canonicalizer_version: str,
    status: str,
    items_found: int,
    canonical_items: int,
    signals_created: int,
    failure: ProcessingFailure | None = None,
) -> str:
    processing_id = str(uuid.uuid4())
    with connect(database) as conn, conn:
        conn.execute(
            """
            INSERT INTO processing_records(
                processing_id,schema_version,evidence_id,request_id,attempt_id,source_id,parser_version,normalizer_version,
                canonicalizer_version,started_at,finished_at,status,processing_failure_class,items_found,
                canonical_items,signals_created
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                processing_id,
                ACQUISITION_SCHEMA_VERSION,
                capture.evidence_id,
                capture.request_id,
                capture.attempt_id,
                source_id,
                parser_version,
                normalizer_version,
                canonicalizer_version,
                observed_at,
                observed_at,
                status,
                failure.value if failure is not None else None,
                items_found,
                canonical_items,
                signals_created,
            ),
        )
    return processing_id
