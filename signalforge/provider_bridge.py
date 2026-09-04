from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .acquisition_contract import ACQUISITION_SCHEMA_VERSION
from .config import Registry, db_path, evidence_root
from .db import connect, migrate


BRIDGE_SCHEMA_VERSION = 1
BRIDGE_NAME = "manual-provider-v0"


class ProviderBridgeError(RuntimeError):
    pass


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderBridgeError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProviderBridgeError(f"JSON root must be an object: {path}")
    return value


def _private_write_json(path: Path, value: dict[str, Any]) -> None:
    parent_existed = path.parent.exists()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not parent_existed:
        path.parent.chmod(0o700)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _manual_candidate(registry: Registry, source_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    bridge = registry.raw.get("manual_provider_bridge")
    if not isinstance(bridge, dict) or bridge.get("schema_version") != BRIDGE_SCHEMA_VERSION:
        raise ProviderBridgeError("manual provider bridge contract missing or unsupported")
    if bridge.get("bridge_name") != BRIDGE_NAME:
        raise ProviderBridgeError("manual provider bridge name mismatch")

    provider_id = bridge.get("provider_id")
    providers = registry.raw.get("providers")
    provider = providers.get(provider_id) if isinstance(providers, dict) and isinstance(provider_id, str) else None
    if not isinstance(provider, dict):
        raise ProviderBridgeError("manual provider bridge provider missing")
    if provider.get("production_enabled") is not False:
        raise ProviderBridgeError("manual bridge requires provider production_enabled=false")
    if provider.get("invocation_mode") != "manual_or_future_contract":
        raise ProviderBridgeError("manual bridge requires manual_or_future_contract provider")
    if (provider.get("network") or {}).get("direct") is not True:
        raise ProviderBridgeError("manual bridge requires direct Mac network capability")
    capabilities = provider.get("capabilities") or {}
    if capabilities.get("c0_fetch") is not True or capabilities.get("c0_raw_artifact") is not True:
        raise ProviderBridgeError("manual bridge v0 requires Mac C0 fetch/raw artifact capability")
    if capabilities.get("remote_invocation") is not False:
        raise ProviderBridgeError("manual bridge v0 must not enable remote invocation")

    candidates = bridge.get("candidates")
    candidate = candidates.get(source_id) if isinstance(candidates, dict) else None
    if not isinstance(candidate, dict):
        raise ProviderBridgeError(f"source is not approved for manual provider bridge: {source_id}")
    deferred = registry.raw.get("deferred_sources") or {}
    if source_id not in deferred:
        raise ProviderBridgeError(f"manual bridge v0 candidate must remain deferred: {source_id}")
    if candidate.get("task_type") != "fetch" or candidate.get("egress") != "direct":
        raise ProviderBridgeError(f"manual bridge v0 supports direct C0 fetch only: {source_id}")
    url = candidate.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ProviderBridgeError(f"manual bridge candidate must use an HTTPS URL: {source_id}")
    expected = candidate.get("expected_content_types")
    if not isinstance(expected, list) or not expected or not all(isinstance(item, str) and item for item in expected):
        raise ProviderBridgeError(f"manual bridge candidate expected_content_types invalid: {source_id}")
    return bridge, provider, candidate


def build_provider_request(source_id: str, *, registry: Registry | None = None, requested_at: str | None = None) -> dict[str, Any]:
    registry = registry or Registry.load()
    bridge, _provider, candidate = _manual_candidate(registry, source_id)
    provider_request_id = str(uuid.uuid4())
    signalforge_job_id = str(uuid.uuid4())
    acquisition_request_id = str(uuid.uuid4())
    acquisition_attempt_id = str(uuid.uuid4())
    requested_at = requested_at or _now()
    url = str(candidate["url"])

    return {
        "task_type": "fetch",
        "url": url,
        "egress": "direct",
        "profile": str(candidate.get("profile", "public-research")),
        "profile_mode": str(candidate.get("profile_mode", "ephemeral")),
        "queue_timeout_sec": int(candidate.get("queue_timeout_sec", 60)),
        "max_run_sec": int(candidate.get("max_run_sec", 30)),
        "evidence_policy": "always",
        "retry_policy": "none",
        "allow_egress_fallback": False,
        "idempotency_key": f"sf-provider:{provider_request_id}",
        "_provider_request": {
            "schema_version": BRIDGE_SCHEMA_VERSION,
            "bridge_name": BRIDGE_NAME,
            "signalforge_job_id": signalforge_job_id,
            "acquisition_request_id": acquisition_request_id,
            "acquisition_attempt_id": acquisition_attempt_id,
            "provider_request_id": provider_request_id,
            "provider_id": str(bridge["provider_id"]),
            "provider_baseline_version": int(bridge.get("provider_baseline_version", 1)),
            "source_id": source_id,
            "source_policy_version": int(candidate.get("source_policy_version", 1)),
            "requested_at": requested_at,
            "requested_url": url,
            "target_kind": str(candidate.get("target_kind", "HTML")),
            "expected_content_types": list(candidate["expected_content_types"]),
            "egress_profile": str(candidate.get("egress_profile", "mac-direct")),
        },
    }


def write_provider_request(source_id: str, output: Path, *, registry: Registry | None = None) -> dict[str, Any]:
    request = build_provider_request(source_id, registry=registry)
    _private_write_json(output, request)
    metadata = request["_provider_request"]
    assert isinstance(metadata, dict)
    return {
        "status": "PROVIDER_REQUEST_CREATED",
        "source_id": source_id,
        "provider_id": metadata["provider_id"],
        "provider_request_id": metadata["provider_request_id"],
        "signalforge_job_id": metadata["signalforge_job_id"],
        "acquisition_request_id": metadata["acquisition_request_id"],
        "acquisition_attempt_id": metadata["acquisition_attempt_id"],
        "output": str(output),
    }


def _base_media_type(value: str | None) -> str:
    return (value or "").split(";", 1)[0].strip().lower()


def _validated_request(request: dict[str, Any], registry: Registry) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    metadata = request.get("_provider_request")
    if not isinstance(metadata, dict):
        raise ProviderBridgeError("provider request metadata missing")
    if metadata.get("schema_version") != BRIDGE_SCHEMA_VERSION or metadata.get("bridge_name") != BRIDGE_NAME:
        raise ProviderBridgeError("provider request bridge version mismatch")
    source_id = metadata.get("source_id")
    if not isinstance(source_id, str):
        raise ProviderBridgeError("provider request source_id missing")
    bridge, provider, candidate = _manual_candidate(registry, source_id)
    if metadata.get("provider_id") != bridge.get("provider_id"):
        raise ProviderBridgeError("provider request provider_id mismatch")
    if int(metadata.get("provider_baseline_version", -1)) != int(bridge.get("provider_baseline_version", 1)):
        raise ProviderBridgeError("provider request baseline version mismatch")
    if metadata.get("requested_url") != candidate.get("url") or request.get("url") != candidate.get("url"):
        raise ProviderBridgeError("provider request URL does not match approved candidate")
    if metadata.get("source_policy_version") != candidate.get("source_policy_version"):
        raise ProviderBridgeError("provider request source policy version mismatch")
    if metadata.get("target_kind") != candidate.get("target_kind"):
        raise ProviderBridgeError("provider request target kind mismatch")
    if metadata.get("expected_content_types") != candidate.get("expected_content_types"):
        raise ProviderBridgeError("provider request expected content types mismatch")
    if metadata.get("egress_profile") != candidate.get("egress_profile"):
        raise ProviderBridgeError("provider request egress profile mismatch")
    if request.get("task_type") != "fetch" or request.get("egress") != "direct":
        raise ProviderBridgeError("manual provider bridge v0 accepts direct C0 fetch requests only")
    if request.get("profile") != candidate.get("profile") or request.get("profile_mode") != candidate.get("profile_mode"):
        raise ProviderBridgeError("provider request profile contract mismatch")
    if request.get("allow_egress_fallback") is not False:
        raise ProviderBridgeError("manual provider bridge v0 forbids egress fallback")
    provider_request_id = metadata.get("provider_request_id")
    if not isinstance(provider_request_id, str) or request.get("idempotency_key") != f"sf-provider:{provider_request_id}":
        raise ProviderBridgeError("provider request idempotency correlation mismatch")
    for key in ("signalforge_job_id", "acquisition_request_id", "acquisition_attempt_id", "requested_at"):
        if not isinstance(metadata.get(key), str) or not metadata[key]:
            raise ProviderBridgeError(f"provider request correlation missing: {key}")
    return metadata, provider, candidate


def import_provider_result(
    *,
    request_path: Path,
    result_path: Path,
    artifact_path: Path | None = None,
    database: Path | None = None,
    evidence_directory: Path | None = None,
    registry: Registry | None = None,
) -> dict[str, Any]:
    registry = registry or Registry.load()
    request = _load_json(request_path)
    metadata, _provider, candidate = _validated_request(request, registry)
    browser_result = _load_json(result_path)

    if browser_result.get("state") != "SUCCEEDED":
        raise ProviderBridgeError(f"browser job is not SUCCEEDED: {browser_result.get('state')}")
    browser_job_id = browser_result.get("job_id")
    if not isinstance(browser_job_id, str) or not browser_job_id:
        raise ProviderBridgeError("browser result job_id missing")
    result = browser_result.get("result")
    if not isinstance(result, dict) or result.get("engine") != "c0-fetch":
        raise ProviderBridgeError("manual provider bridge v0 accepts c0-fetch results only")
    status = result.get("status")
    if not isinstance(status, int) or status < 200 or status >= 300:
        raise ProviderBridgeError(f"provider result HTTP status is not successful: {status}")
    final_url = result.get("url")
    if not isinstance(final_url, str) or final_url != candidate.get("url"):
        raise ProviderBridgeError("provider result final URL does not match approved candidate")

    source_artifact = artifact_path
    if source_artifact is None:
        raw_artifact_path = result.get("artifact_path")
        if not isinstance(raw_artifact_path, str) or not raw_artifact_path:
            raise ProviderBridgeError("provider result artifact_path missing; pass --artifact after cross-host transfer")
        source_artifact = Path(raw_artifact_path)
    source_artifact = source_artifact.expanduser()
    try:
        payload = source_artifact.read_bytes()
    except OSError as exc:
        raise ProviderBridgeError(f"cannot read provider artifact {source_artifact}: {exc}") from exc

    digest = hashlib.sha256(payload).hexdigest()
    if result.get("sha256") != digest:
        raise ProviderBridgeError("provider artifact SHA-256 mismatch")
    if int(result.get("body_bytes", -1)) != len(payload):
        raise ProviderBridgeError("provider artifact byte count mismatch")
    content_type = str(result.get("content_type") or "application/octet-stream")
    expected_types = metadata.get("expected_content_types")
    if not isinstance(expected_types, list):
        raise ProviderBridgeError("provider request expected_content_types missing")
    if _base_media_type(content_type) not in {_base_media_type(str(item)) for item in expected_types}:
        raise ProviderBridgeError(f"provider result content type not approved: {content_type}")

    target_database = database or db_path()
    target_evidence_root = evidence_directory or evidence_root()
    migrate(target_database)

    request_id = str(metadata["acquisition_request_id"])
    attempt_id = str(metadata["acquisition_attempt_id"])
    signalforge_job_id = str(metadata["signalforge_job_id"])
    provider_request_id = str(metadata["provider_request_id"])
    source_id = str(metadata["source_id"])
    provider_id = str(metadata["provider_id"])
    requested_at = str(metadata["requested_at"])
    source_policy_version = int(metadata["source_policy_version"])
    provider_baseline_version = int(metadata["provider_baseline_version"])
    egress_profile = str(metadata["egress_profile"])
    target_kind = str(metadata["target_kind"])

    with connect(target_database) as conn:
        existing = conn.execute(
            "SELECT evidence_id,artifact_sha256,provider_id FROM evidence_envelopes WHERE request_id=?",
            (request_id,),
        ).fetchone()
    if existing is not None:
        if str(existing["artifact_sha256"]) != digest or str(existing["provider_id"]) != provider_id:
            raise ProviderBridgeError("existing provider import conflicts with supplied artifact/provider")
        return {
            "status": "ALREADY_IMPORTED",
            "source_id": source_id,
            "provider_id": provider_id,
            "provider_request_id": provider_request_id,
            "browser_job_id": browser_job_id,
            "acquisition_request_id": request_id,
            "acquisition_attempt_id": attempt_id,
            "evidence_id": str(existing["evidence_id"]),
            "sha256": digest,
        }

    import_dir = target_evidence_root / source_id / "provider" / provider_request_id
    import_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    import_dir.chmod(0o700)
    suffix = source_artifact.suffix if source_artifact.suffix and len(source_artifact.suffix) <= 10 else ".bin"
    stored_artifact = import_dir / f"response{suffix}"
    if stored_artifact.exists():
        if hashlib.sha256(stored_artifact.read_bytes()).hexdigest() != digest:
            raise ProviderBridgeError("provider import evidence path already contains different bytes")
    else:
        tmp = stored_artifact.with_suffix(stored_artifact.suffix + ".part")
        shutil.copyfile(source_artifact, tmp)
        tmp.chmod(0o640)
        tmp.replace(stored_artifact)
        stored_artifact.chmod(0o640)
    _private_write_json(import_dir / "request.json", request)
    _private_write_json(import_dir / "browser-result.json", browser_result)

    evidence_id = str(uuid.uuid4())
    processing_id = str(uuid.uuid4())
    started_at = str(browser_result.get("started_at") or requested_at)
    finished_at = str(browser_result.get("finished_at") or _now())

    with connect(target_database) as conn, conn:
        conn.execute(
            """
            INSERT INTO scheduler_runs(
                app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,finished_at,status,
                changed,signals_created,baseline,recovery,backlog_remaining,details_attempted,details_succeeded,
                tenders_parsed,items_parsed,error
            ) VALUES (?,?,?,?,?,?,?,?,0,0,0,0,0,0,0,0,0,NULL)
            """,
            (
                signalforge_job_id,
                provider_request_id,
                "MANUAL_PROVIDER",
                source_id,
                browser_job_id,
                started_at,
                finished_at,
                "SUCCESS",
            ),
        )
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
                signalforge_job_id,
                provider_request_id,
                source_id,
                source_policy_version,
                "manual_provider_bridge",
                "MANUAL",
                egress_profile,
                requested_at,
                "PROVIDER_C0",
                target_kind,
                int(request.get("max_run_sec", 30)),
                _json(expected_types),
            ),
        )
        conn.execute(
            """
            INSERT INTO acquisition_attempts(
                attempt_id,schema_version,request_id,attempt_number,source_id,source_policy_version,method,egress_profile,
                started_at,finished_at,status,acquisition_failure_class
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL)
            """,
            (
                attempt_id,
                ACQUISITION_SCHEMA_VERSION,
                request_id,
                1,
                source_id,
                source_policy_version,
                "PROVIDER_C0",
                egress_profile,
                started_at,
                finished_at,
                "SUCCESS",
            ),
        )
        conn.execute(
            """
            INSERT INTO evidence_envelopes(
                evidence_id,schema_version,request_id,attempt_id,scheduler_run_id,app_job_ref,source_id,source_policy_version,
                execution_scope,provider_id,provider_baseline_version,egress_profile,fetch_method,started_at,fetched_at,
                requested_url,final_url,http_status,media_type,content_length,artifact_id,artifact_sha256,artifact_bytes,
                artifact_media_type,acquisition_failure_class
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)
            """,
            (
                evidence_id,
                ACQUISITION_SCHEMA_VERSION,
                request_id,
                attempt_id,
                signalforge_job_id,
                provider_request_id,
                source_id,
                source_policy_version,
                "MAC_LOCAL_MANUAL_BRIDGE",
                provider_id,
                provider_baseline_version,
                egress_profile,
                "C0_FETCH",
                started_at,
                finished_at,
                str(metadata["requested_url"]),
                final_url,
                status,
                content_type,
                len(payload),
                f"sha256:{digest}",
                digest,
                len(payload),
                content_type,
            ),
        )
        conn.execute(
            """
            INSERT INTO processing_records(
                processing_id,schema_version,evidence_id,request_id,attempt_id,source_id,parser_version,normalizer_version,
                canonicalizer_version,started_at,finished_at,status,processing_failure_class,items_found,
                canonical_items,signals_created
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL,0,0,0)
            """,
            (
                processing_id,
                ACQUISITION_SCHEMA_VERSION,
                evidence_id,
                request_id,
                attempt_id,
                source_id,
                "none",
                "none",
                "none",
                finished_at,
                finished_at,
                "EVIDENCE_ONLY",
            ),
        )

    return {
        "status": "IMPORTED_EVIDENCE_ONLY",
        "source_id": source_id,
        "provider_id": provider_id,
        "provider_request_id": provider_request_id,
        "browser_job_id": browser_job_id,
        "signalforge_job_id": signalforge_job_id,
        "acquisition_request_id": request_id,
        "acquisition_attempt_id": attempt_id,
        "evidence_id": evidence_id,
        "processing_id": processing_id,
        "processing_status": "EVIDENCE_ONLY",
        "artifact_path": str(stored_artifact),
        "sha256": digest,
        "artifact_bytes": len(payload),
        "content_type": content_type,
    }
