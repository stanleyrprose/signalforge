from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
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
from .db import connect


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
