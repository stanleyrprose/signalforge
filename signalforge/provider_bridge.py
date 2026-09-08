from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .acquisition_contract import ACQUISITION_SCHEMA_VERSION
from .config import Registry, db_path, evidence_root
from .db import connect, migrate


BRIDGE_SCHEMA_VERSION = 1
BRIDGE_NAME = "manual-provider-v0"


class ProviderBridgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImportedProviderArtifact:
    source_id: str
    provider_request_id: str
    acquisition_request_id: str
    evidence_id: str
    target_role: str
    target_kind: str
    requested_url: str
    content_type: str
    sha256: str
    artifact_path: Path
    payload: bytes


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
    if not isinstance(provider.get("production_enabled"), bool):
        raise ProviderBridgeError("manual bridge provider production state invalid")
    if provider.get("invocation_mode") not in {"manual_or_future_contract", "pull_ssh_v1"}:
        raise ProviderBridgeError("manual bridge provider invocation mode unsupported")
    if (provider.get("network") or {}).get("direct") is not True:
        raise ProviderBridgeError("manual bridge requires direct Mac network capability")
    capabilities = provider.get("capabilities") or {}
    if capabilities.get("c0_fetch") is not True or capabilities.get("c0_raw_artifact") is not True:
        raise ProviderBridgeError("manual bridge v0 requires Mac C0 fetch/raw artifact capability")
    if not isinstance(capabilities.get("remote_invocation"), bool):
        raise ProviderBridgeError("manual bridge provider remote capability state invalid")

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


def _resolve_manual_target(
    candidate: dict[str, Any],
    *,
    target_role: str = "LISTING",
    url: str | None = None,
) -> dict[str, Any]:
    role = str(target_role or "LISTING").upper()
    if role == "LISTING":
        expected_url = candidate.get("url")
        if not isinstance(expected_url, str) or not expected_url.startswith("https://"):
            raise ProviderBridgeError("manual bridge listing URL missing")
        if url is not None and url != expected_url:
            raise ProviderBridgeError("manual bridge LISTING URL must equal approved candidate URL")
        expected_types = candidate.get("expected_content_types")
        if not isinstance(expected_types, list) or not expected_types:
            raise ProviderBridgeError("manual bridge listing content types missing")
        return {
            "target_role": "LISTING",
            "url": expected_url,
            "target_kind": str(candidate.get("target_kind", "HTML")),
            "expected_content_types": list(expected_types),
        }

    targets = candidate.get("manual_targets")
    target = targets.get(role) if isinstance(targets, dict) else None
    if not isinstance(target, dict):
        raise ProviderBridgeError(f"manual bridge target role is not approved: {role}")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ProviderBridgeError(f"manual bridge {role} URL must be explicit HTTPS")
    parsed = urlparse(url)
    approved_host = target.get("https_host")
    if (
        parsed.scheme != "https"
        or parsed.hostname != approved_host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        raise ProviderBridgeError(f"manual bridge {role} URL violates HTTPS host/path boundary")
    decoded_path = unquote(parsed.path)
    if ".." in decoded_path.split("/"):
        raise ProviderBridgeError(f"manual bridge {role} URL path traversal is forbidden")
    prefix = target.get("path_prefix")
    suffix = target.get("path_suffix")
    if not isinstance(prefix, str) or not parsed.path.startswith(prefix):
        raise ProviderBridgeError(f"manual bridge {role} URL path is outside approved prefix")
    if isinstance(suffix, str) and suffix and not parsed.path.lower().endswith(suffix.lower()):
        raise ProviderBridgeError(f"manual bridge {role} URL path suffix is not approved")
    expected_types = target.get("expected_content_types")
    if not isinstance(expected_types, list) or not expected_types or not all(isinstance(item, str) and item for item in expected_types):
        raise ProviderBridgeError(f"manual bridge {role} expected_content_types invalid")
    target_kind = target.get("target_kind")
    if target_kind not in {"HTML", "PDF"}:
        raise ProviderBridgeError(f"manual bridge {role} target_kind invalid")
    return {
        "target_role": role,
        "url": url,
        "target_kind": str(target_kind),
        "expected_content_types": list(expected_types),
    }


def build_provider_request(
    source_id: str,
    *,
    registry: Registry | None = None,
    requested_at: str | None = None,
    url: str | None = None,
    target_role: str = "LISTING",
) -> dict[str, Any]:
    registry = registry or Registry.load()
    bridge, _provider, candidate = _manual_candidate(registry, source_id)
    target = _resolve_manual_target(candidate, target_role=target_role, url=url)
    provider_request_id = str(uuid.uuid4())
    signalforge_job_id = str(uuid.uuid4())
    acquisition_request_id = str(uuid.uuid4())
    acquisition_attempt_id = str(uuid.uuid4())
    requested_at = requested_at or _now()
    requested_url = str(target["url"])

    return {
        "task_type": "fetch",
        "url": requested_url,
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
            "requested_url": requested_url,
            "target_role": str(target["target_role"]),
            "target_kind": str(target["target_kind"]),
            "expected_content_types": list(target["expected_content_types"]),
            "egress_profile": str(candidate.get("egress_profile", "mac-direct")),
        },
    }


def write_provider_request(
    source_id: str,
    output: Path,
    *,
    registry: Registry | None = None,
    url: str | None = None,
    target_role: str = "LISTING",
) -> dict[str, Any]:
    request = build_provider_request(source_id, registry=registry, url=url, target_role=target_role)
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
        "target_role": metadata["target_role"],
        "requested_url": metadata["requested_url"],
        "output": str(output),
    }


def _base_media_type(value: str | None) -> str:
    return (value or "").split(";", 1)[0].strip().lower()


def _validated_request(
    request: dict[str, Any], registry: Registry
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
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
    requested_url = metadata.get("requested_url")
    if not isinstance(requested_url, str):
        raise ProviderBridgeError("provider request requested_url missing")
    target_role = str(metadata.get("target_role") or "LISTING")
    target = _resolve_manual_target(candidate, target_role=target_role, url=requested_url)
    if request.get("url") != target.get("url"):
        raise ProviderBridgeError("provider request URL does not match approved target")
    if metadata.get("source_policy_version") != candidate.get("source_policy_version"):
        raise ProviderBridgeError("provider request source policy version mismatch")
    if metadata.get("target_kind") != target.get("target_kind"):
        raise ProviderBridgeError("provider request target kind mismatch")
    if metadata.get("expected_content_types") != target.get("expected_content_types"):
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
    return metadata, provider, candidate, target


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
    metadata, _provider, candidate, target = _validated_request(request, registry)
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
    if not isinstance(final_url, str) or final_url != target.get("url"):
        raise ProviderBridgeError("provider result final URL does not match approved target")

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
    expected_types = target.get("expected_content_types")
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
    target_kind = str(target["target_kind"])

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
        "target_role": str(metadata.get("target_role") or "LISTING"),
        "artifact_path": str(stored_artifact),
        "sha256": digest,
        "artifact_bytes": len(payload),
        "content_type": content_type,
    }


def load_imported_provider_artifact(
    provider_request_id: str,
    *,
    database: Path | None = None,
    evidence_directory: Path | None = None,
    registry: Registry | None = None,
) -> ImportedProviderArtifact:
    registry = registry or Registry.load()
    target_database = database or db_path()
    target_evidence_root = evidence_directory or evidence_root()
    with connect(target_database) as conn:
        rows = conn.execute(
            """
            SELECT ar.request_id,ar.target_kind,e.evidence_id,e.app_job_ref,e.source_id,e.requested_url,e.media_type,
                   e.provider_id,e.execution_scope,e.fetch_method,e.artifact_sha256,e.artifact_bytes
            FROM acquisition_requests ar
            JOIN evidence_envelopes e ON e.request_id=ar.request_id
            WHERE ar.app_job_ref=?
            """,
            (provider_request_id,),
        ).fetchall()
        if not rows:
            raise ProviderBridgeError(f"imported provider artifact not found: {provider_request_id}")
        if len(rows) != 1:
            raise ProviderBridgeError(f"imported provider artifact correlation is not unique: {provider_request_id}")
        row = rows[0]
        evidence_only = conn.execute(
            "SELECT COUNT(*) FROM processing_records WHERE evidence_id=? AND status='EVIDENCE_ONLY'",
            (str(row["evidence_id"]),),
        ).fetchone()[0]
        if int(evidence_only) < 1:
            raise ProviderBridgeError("provider artifact does not have EVIDENCE_ONLY processing provenance")

    source_id = str(row["source_id"])
    import_dir = target_evidence_root / source_id / "provider" / provider_request_id
    request_path = import_dir / "request.json"
    request = _load_json(request_path)
    metadata, _provider, _candidate, target = _validated_request(request, registry)
    if metadata.get("provider_request_id") != provider_request_id:
        raise ProviderBridgeError("stored provider request id does not match evidence path")
    candidates = [
        item
        for item in import_dir.iterdir()
        if item.is_file() and item.name.startswith("response.") and not item.name.endswith(".part")
    ] if import_dir.exists() else []
    if len(candidates) != 1:
        raise ProviderBridgeError(f"expected exactly one stored provider response artifact, found {len(candidates)}")
    artifact_path = candidates[0]
    payload = artifact_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != str(row["artifact_sha256"]) or len(payload) != int(row["artifact_bytes"]):
        raise ProviderBridgeError("stored provider response artifact fails durable hash/size verification")
    if str(row["requested_url"]) != str(target["url"]):
        raise ProviderBridgeError("stored provider requested_url does not match current target contract")
    return ImportedProviderArtifact(
        source_id=source_id,
        provider_request_id=provider_request_id,
        acquisition_request_id=str(row["request_id"]),
        evidence_id=str(row["evidence_id"]),
        target_role=str(metadata.get("target_role") or "LISTING"),
        target_kind=str(row["target_kind"]),
        requested_url=str(row["requested_url"]),
        content_type=str(row["media_type"] or "application/octet-stream"),
        sha256=digest,
        artifact_path=artifact_path,
        payload=payload,
    )
