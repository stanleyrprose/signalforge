from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Registry, db_path, repo_root
from .db import connect, migrate
from .provider_invocation import (
    CAPABILITY_TOOL_MAP,
    ProviderCapability,
    ProviderInvocationError,
    build_provider_request,
    validate_contract_projection,
    validate_final_url_policy,
)
from .provider_queue import enqueue_provider_request, initialize_provider_queue


R3_SOURCE_ID = "S38"
R3_TARGET_ROLE = "LISTING"
R3_URL = "https://www.industrymsme.gov.mm/announcements"
R3_CONTRACT_NAME = "Provider-Invocation-Contract-v1-r3-evidence-only.json"
R3_CAPABILITIES = (
    ProviderCapability.C0_FETCH.value,
    ProviderCapability.C1_RENDER.value,
    ProviderCapability.C2_INSPECT.value,
    ProviderCapability.C3_BROWSER_USE.value,
)
R3_EXPECTED_ENGINES = {
    ProviderCapability.C1_RENDER.value: "c1-playwright",
    ProviderCapability.C2_INSPECT.value: "c2-readonly-inspect",
    ProviderCapability.C3_BROWSER_USE.value: "c3-browser-use",
}
R3_FAILURE_STATES = {"FAILED", "EXPIRED", "CANCELLED"}


class ProviderR3Error(RuntimeError):
    pass


def _contract_path(path: Path | None = None) -> Path:
    return path or (repo_root() / "registry" / R3_CONTRACT_NAME)


def load_r3_contract(path: Path | None = None) -> dict[str, Any]:
    target = _contract_path(path)
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderR3Error(f"cannot load R3 evidence-only contract: {exc}") from exc
    if not isinstance(value, dict):
        raise ProviderR3Error("R3 evidence-only contract must be an object")
    try:
        validate_contract_projection(value)
    except ProviderInvocationError as exc:
        raise ProviderR3Error(str(exc)) from exc
    if value.get("enabled") is not False or value.get("verification_mode") != "EVIDENCE_ONLY":
        raise ProviderR3Error("R3 contract must remain disabled and EVIDENCE_ONLY")
    policies = value.get("source_policies")
    if not isinstance(policies, dict) or set(policies) != {R3_SOURCE_ID}:
        raise ProviderR3Error("R3 contract must authorize exactly isolated source S38")
    source = policies[R3_SOURCE_ID]
    if not isinstance(source, dict) or source.get("enabled") is not True:
        raise ProviderR3Error("R3 S38 source policy must be explicitly enabled inside the isolated contract")
    if set(source.get("allowed_capabilities") or []) != set(R3_CAPABILITIES):
        raise ProviderR3Error("R3 S38 must project exactly C0+C1+C2+C3")
    targets = source.get("targets")
    target_policy = targets.get(R3_TARGET_ROLE) if isinstance(targets, dict) else None
    if not isinstance(target_policy, dict):
        raise ProviderR3Error("R3 LISTING target policy missing")
    if target_policy.get("exact_urls") != [R3_URL]:
        raise ProviderR3Error("R3 target URL must remain pinned to Ministry of Industry announcements")
    if set(target_policy.get("capabilities") or []) != set(R3_CAPABILITIES):
        raise ProviderR3Error("R3 LISTING target must allow exactly C0+C1+C2+C3")
    return value


def prepare_r3_gate(
    *,
    database: Path | None = None,
    contract_path: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    contract = load_r3_contract(contract_path)
    registry = Registry.load()
    production_sources = registry.raw.get("sources")
    production_provider = (registry.raw.get("providers") or {}).get("mac-mm-01") or {}
    if (
        (isinstance(production_sources, dict) and R3_SOURCE_ID in production_sources)
        or registry.raw["production_policy"].get("browser_production_approved") is not False
        or production_provider.get("production_enabled") is not False
        or (production_provider.get("capabilities") or {}).get("remote_invocation") is not False
    ):
        raise ProviderR3Error("R3 is historical after R4 production enablement and must not be rerun")
    target_db = database or db_path()
    migrate(target_db)
    initialize_provider_queue(target_db)
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    gate_id = str(uuid.uuid4())
    requests: list[dict[str, Any]] = []

    for capability in R3_CAPABILITIES:
        interaction_plan = None
        if capability == ProviderCapability.C3_BROWSER_USE.value:
            interaction_plan = {
                "side_effect_class": "READ_ONLY_NAVIGATION",
                "retry_safe": True,
                "steps": [{"action": "snapshot"}],
            }
        request = build_provider_request(
            contract=contract,
            source_id=R3_SOURCE_ID,
            source_policy_version=1,
            capability=capability,
            target_role=R3_TARGET_ROLE,
            requested_url=R3_URL,
            signalforge_job_id=gate_id,
            acquisition_request_id=str(uuid.uuid4()),
            acquisition_attempt_id=str(uuid.uuid4()),
            max_bytes=1_000_000,
            max_run_seconds=120,
            interaction_plan=interaction_plan,
            now=observed,
            ttl_seconds=180,
        )
        enqueue_provider_request(
            request,
            contract=contract,
            database=target_db,
            priority=100,
            now=observed,
        )
        requests.append(
            {
                "provider_request_id": request["provider_request_id"],
                "capability": capability,
                "mcp_tool": CAPABILITY_TOOL_MAP[capability],
                "expires_at": request["expires_at"],
            }
        )

    return {
        "status": "R3_EVIDENCE_ONLY_PREPARED",
        "verification_mode": "EVIDENCE_ONLY",
        "provider_contract_enabled": False,
        "source_id": R3_SOURCE_ID,
        "gate_id": gate_id,
        "requested_url": R3_URL,
        "requests": requests,
        "customer_signal_path_enabled": False,
    }


def _gate_rows(database: Path, gate_id: str) -> list[dict[str, Any]]:
    initialize_provider_queue(database)
    with connect(database) as conn:
        rows = conn.execute(
            "SELECT * FROM provider_requests WHERE source_id=? ORDER BY created_at,provider_request_id",
            (R3_SOURCE_ID,),
        ).fetchall()
    matched: list[dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        try:
            request = json.loads(str(record["request_json"]))
        except json.JSONDecodeError:
            continue
        if request.get("signalforge_job_id") == gate_id:
            record["request"] = request
            matched.append(record)
    return matched


def _business_side_effect_counts(database: Path) -> dict[str, int]:
    with connect(database) as conn:
        return {
            "scheduler_runs": int(conn.execute("SELECT COUNT(*) FROM scheduler_runs WHERE source_id=?", (R3_SOURCE_ID,)).fetchone()[0]),
            "canonical_items": int(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id=?", (R3_SOURCE_ID,)).fetchone()[0]),
            "signals": int(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id=?", (R3_SOURCE_ID,)).fetchone()[0]),
        }


def _verify_success(record: dict[str, Any]) -> tuple[bool, str | None]:
    request = record["request"]
    capability = str(record["capability"])
    if record.get("result_request_sha256") != record.get("request_sha256"):
        return False, "result request SHA does not match ProviderRequest"
    path_value = record.get("result_artifact_path")
    if not isinstance(path_value, str) or not path_value:
        return False, "durable result artifact path missing"
    artifact_path = Path(path_value)
    if not artifact_path.is_file():
        return False, "durable result artifact file missing"
    artifact = artifact_path.read_bytes()
    if hashlib.sha256(artifact).hexdigest() != record.get("result_sha256"):
        return False, "durable result artifact SHA mismatch"
    if len(artifact) != record.get("result_artifact_bytes"):
        return False, "durable result artifact byte count mismatch"
    try:
        validate_final_url_policy(request.get("final_url_policy"), str(record.get("result_final_url") or ""))
    except ProviderInvocationError as exc:
        return False, str(exc)

    media_type = str(record.get("result_media_type") or "")
    if capability == ProviderCapability.C0_FETCH.value:
        if media_type != "text/html":
            return False, "C0 evidence must be text/html"
        return True, None

    if media_type != "application/json":
        return False, f"{capability} evidence must be application/json"
    try:
        payload = json.loads(artifact)
    except json.JSONDecodeError:
        return False, f"{capability} evidence JSON invalid"
    if not isinstance(payload, dict) or payload.get("job_id") != record.get("browser_job_id") or payload.get("state") != "SUCCEEDED":
        return False, f"{capability} Browser job correlation invalid"
    result = payload.get("result")
    if not isinstance(result, dict) or result.get("engine") != R3_EXPECTED_ENGINES[capability]:
        return False, f"{capability} Browser engine evidence invalid"
    return True, None


def r3_gate_status(
    gate_id: str,
    *,
    database: Path | None = None,
) -> dict[str, Any]:
    try:
        uuid.UUID(gate_id)
    except ValueError as exc:
        raise ProviderR3Error("gate_id must be UUID") from exc
    target_db = database or db_path()
    migrate(target_db)
    rows = _gate_rows(target_db, gate_id)
    side_effects = _business_side_effect_counts(target_db)
    side_effect_free = all(value == 0 for value in side_effects.values())

    by_capability: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for record in rows:
        capability = str(record["capability"])
        if capability in by_capability:
            failures.append(f"duplicate ProviderRequest for {capability}")
            continue
        verified = False
        verification_error = None
        if record["state"] == "SUCCEEDED":
            verified, verification_error = _verify_success(record)
            if not verified and verification_error:
                failures.append(f"{capability}: {verification_error}")
        elif record["state"] in R3_FAILURE_STATES:
            failures.append(f"{capability}: terminal state {record['state']} ({record.get('failure_class')})")
        by_capability[capability] = {
            "provider_request_id": record["provider_request_id"],
            "state": record["state"],
            "browser_job_id": record.get("browser_job_id"),
            "result_media_type": record.get("result_media_type"),
            "result_artifact_bytes": record.get("result_artifact_bytes"),
            "result_final_url": record.get("result_final_url"),
            "verified": verified,
            "verification_error": verification_error,
        }

    missing = sorted(set(R3_CAPABILITIES) - set(by_capability))
    if missing:
        failures.append(f"missing capabilities: {','.join(missing)}")
    if not side_effect_free:
        failures.append("EVIDENCE_ONLY boundary violated by S38 business-side effects")

    complete = set(by_capability) == set(R3_CAPABILITIES)
    passed = complete and side_effect_free and not failures and all(item["verified"] for item in by_capability.values())
    terminal_failure = bool(failures)
    status = "PASS" if passed else ("FAIL" if terminal_failure else "WAITING")
    return {
        "status": status,
        "verification_mode": "EVIDENCE_ONLY",
        "source_id": R3_SOURCE_ID,
        "gate_id": gate_id,
        "capabilities": by_capability,
        "business_side_effect_counts": side_effects,
        "failures": failures,
    }
