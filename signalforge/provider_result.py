from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

from .config import evidence_root
from .db import connect
from .provider_invocation import ProviderInvocationError, validate_final_url_policy
from .provider_queue import ProviderQueueError, complete_provider_claim, initialize_provider_queue

RESULT_MANIFEST_MAX_BYTES = 16 * 1024
RESULT_ARTIFACT_MAX_BYTES = 16 * 1024 * 1024
RESULT_STATE = "SUCCEEDED"

class ProviderResultError(RuntimeError):
    pass

@dataclass(frozen=True)
class ParsedProviderResult:
    manifest: dict[str, Any]
    artifact: bytes

def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

def parse_result_stream(stream: BinaryIO) -> ParsedProviderResult:
    line = stream.readline(RESULT_MANIFEST_MAX_BYTES + 2)
    if not line or len(line) > RESULT_MANIFEST_MAX_BYTES + 1 or not line.endswith(b"\n"):
        raise ProviderResultError("provider result manifest framing invalid")
    try:
        manifest = json.loads(line[:-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderResultError("provider result manifest is not valid UTF-8 JSON") from exc
    if not isinstance(manifest, dict):
        raise ProviderResultError("provider result manifest must be an object")
    expected = {"contract_version","provider_request_id","provider_attempt_id","claim_token","browser_job_id","request_sha256","state","mcp_tool","final_url","http_status","media_type","artifact_bytes","artifact_sha256"}
    if set(manifest) != expected:
        raise ProviderResultError("provider result manifest fields do not match contract")
    if manifest.get("contract_version") != 1 or manifest.get("state") != RESULT_STATE:
        raise ProviderResultError("provider result contract/state invalid")
    size = manifest.get("artifact_bytes")
    if not isinstance(size, int) or not 0 <= size <= RESULT_ARTIFACT_MAX_BYTES:
        raise ProviderResultError("provider artifact size outside contract")
    artifact = stream.read(size)
    if len(artifact) != size:
        raise ProviderResultError("provider artifact truncated")
    if stream.read(1):
        raise ProviderResultError("provider result stream contains trailing bytes")
    digest = _sha256(artifact)
    if manifest.get("artifact_sha256") != digest:
        raise ProviderResultError("provider artifact SHA-256 mismatch")
    if not isinstance(manifest.get("media_type"), str) or not manifest["media_type"]:
        raise ProviderResultError("provider media_type missing")
    status = manifest.get("http_status")
    if status is not None and (not isinstance(status, int) or status < 100 or status > 599):
        raise ProviderResultError("provider http_status invalid")
    for field in ("provider_request_id","provider_attempt_id","claim_token","browser_job_id","request_sha256","mcp_tool","final_url"):
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            raise ProviderResultError(f"provider result field missing: {field}")
    return ParsedProviderResult(manifest=manifest, artifact=artifact)

def _validate_claim_metadata(manifest: dict[str, Any], *, database: Path) -> dict[str, Any]:
    initialize_provider_queue(database)
    with connect(database) as conn:
        row = conn.execute("SELECT * FROM provider_requests WHERE provider_request_id=?", (manifest["provider_request_id"],)).fetchone()
    if row is None:
        raise ProviderResultError("provider request not found")
    if str(row["state"]) == "SUCCEEDED":
        if str(row["result_sha256"]) == str(manifest["artifact_sha256"]) and str(row["browser_job_id"]) == str(manifest["browser_job_id"]):
            return dict(row)
        raise ProviderResultError("provider result idempotency conflict")
    if str(row["state"]) != "CLAIMED":
        raise ProviderResultError(f"provider request is not CLAIMED: {row['state']}")
    if str(row["current_provider_attempt_id"]) != str(manifest["provider_attempt_id"]):
        raise ProviderResultError("provider attempt does not own current claim")
    import secrets
    token_hash = hashlib.sha256(str(manifest["claim_token"]).encode("utf-8")).hexdigest()
    if not secrets.compare_digest(str(row["claim_token_sha256"]), token_hash):
        raise ProviderResultError("provider claim token mismatch")
    if str(row["request_sha256"]) != str(manifest["request_sha256"]):
        raise ProviderResultError("provider result request SHA mismatch")
    request = json.loads(str(row["request_json"]))
    request_max_bytes = request.get("max_bytes")
    if not isinstance(request_max_bytes, int) or int(manifest["artifact_bytes"]) > request_max_bytes:
        raise ProviderResultError("provider artifact exceeds request max_bytes")
    if str(request.get("mcp_tool")) != str(manifest["mcp_tool"]):
        raise ProviderResultError("provider result MCP tool mismatch")
    try:
        validate_final_url_policy(request.get("final_url_policy"), str(manifest["final_url"]))
    except ProviderInvocationError as exc:
        raise ProviderResultError(str(exc)) from exc
    return dict(row)

def accept_result_stream(stream: BinaryIO, *, database: Path, evidence_directory: Path | None = None, now: datetime | None = None) -> dict[str, Any]:
    parsed = parse_result_stream(stream)
    manifest = parsed.manifest
    observed_now = (now or datetime.now(UTC)).astimezone(UTC)
    row = _validate_claim_metadata(manifest, database=database)
    if str(row["state"]) == "SUCCEEDED":
        return {"status": "ALREADY_ACCEPTED", "provider_request_id": manifest["provider_request_id"]}
    root = evidence_directory or (evidence_root() / "provider-results")
    target_dir = root / str(manifest["provider_request_id"])
    target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    target_dir.chmod(0o700)
    artifact_path = target_dir / "response.bin"
    if artifact_path.exists():
        if _sha256(artifact_path.read_bytes()) != manifest["artifact_sha256"]:
            raise ProviderResultError("provider result path already contains different artifact")
    else:
        tmp = target_dir / ".response.bin.part"
        tmp.write_bytes(parsed.artifact)
        tmp.chmod(0o600)
        os.replace(tmp, artifact_path)
        artifact_path.chmod(0o640)
    manifest_path = target_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)
    try:
        result = complete_provider_claim(provider_request_id=str(manifest["provider_request_id"]), provider_attempt_id=str(manifest["provider_attempt_id"]), claim_token=str(manifest["claim_token"]), result_sha256=str(manifest["artifact_sha256"]), browser_job_id=str(manifest["browser_job_id"]), database=database, result_media_type=str(manifest["media_type"]), result_artifact_bytes=int(manifest["artifact_bytes"]), result_artifact_path=str(artifact_path), result_final_url=str(manifest["final_url"]), result_http_status=manifest["http_status"], result_request_sha256=str(manifest["request_sha256"]), now=observed_now)
    except ProviderQueueError as exc:
        raise ProviderResultError(str(exc)) from exc
    return {**result, "artifact_path": str(artifact_path), "artifact_sha256": str(manifest["artifact_sha256"]), "artifact_bytes": int(manifest["artifact_bytes"]), "media_type": str(manifest["media_type"])}
