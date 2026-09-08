from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from urllib.parse import unquote, urlparse


PIC_SCHEMA_VERSION = 1
PIC_CONTRACT_NAME = "provider-invocation-v1"
PIC_PROVIDER_ID = "mac-mm-01"
PIC_TRANSPORT = "pull_ssh_v1"


class ProviderInvocationError(RuntimeError):
    pass


class ProviderCapability(str, Enum):
    C0_FETCH = "C0_FETCH"
    C1_RENDER = "C1_RENDER"
    C2_INSPECT = "C2_INSPECT"
    C3_BROWSER_USE = "C3_BROWSER_USE"


CAPABILITY_TOOL_MAP = {
    ProviderCapability.C0_FETCH.value: "browser_fetch",
    ProviderCapability.C1_RENDER.value: "browser_render",
    ProviderCapability.C2_INSPECT.value: "browser_inspect",
    ProviderCapability.C3_BROWSER_USE.value: "browser_use",
}

READ_ONLY_CAPABILITIES = {
    ProviderCapability.C0_FETCH.value,
    ProviderCapability.C1_RENDER.value,
    ProviderCapability.C2_INSPECT.value,
}

C3_SIDE_EFFECT_CLASS = "READ_ONLY_NAVIGATION"
C3_ALLOWED_ACTIONS = {
    "snapshot",
    "navigate",
    "click",
    "wait",
    "type",
    "select",
    "scroll",
    "screenshot",
}

_SOURCE_ID = re.compile(r"^[A-Z][A-Z0-9]{0,15}$")


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def request_sha256(request: dict[str, Any]) -> str:
    payload = dict(request)
    payload.pop("request_sha256", None)
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _parse_time(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ProviderInvocationError(f"{field} missing")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ProviderInvocationError(f"{field} invalid") from exc
    if parsed.tzinfo is None:
        raise ProviderInvocationError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _require_uuid(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProviderInvocationError(f"{field} missing")
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise ProviderInvocationError(f"{field} must be UUID") from exc
    return value


def validate_contract_projection(contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise ProviderInvocationError("provider invocation contract missing")
    if contract.get("schema_version") != PIC_SCHEMA_VERSION:
        raise ProviderInvocationError("provider invocation schema version mismatch")
    if contract.get("contract_name") != PIC_CONTRACT_NAME:
        raise ProviderInvocationError("provider invocation contract name mismatch")
    if contract.get("provider_id") != PIC_PROVIDER_ID:
        raise ProviderInvocationError("provider invocation provider mismatch")
    if contract.get("transport") != PIC_TRANSPORT:
        raise ProviderInvocationError("provider invocation transport mismatch")

    capabilities = contract.get("allowed_capabilities")
    if not isinstance(capabilities, list) or set(capabilities) != set(CAPABILITY_TOOL_MAP):
        raise ProviderInvocationError("PIC v1 must project C0+C1+C2+C3 exactly")

    tool_map = contract.get("tool_map")
    if tool_map != CAPABILITY_TOOL_MAP:
        raise ProviderInvocationError("provider MCP tool map mismatch")

    limits = contract.get("limits")
    if not isinstance(limits, dict):
        raise ProviderInvocationError("provider invocation limits missing")
    for field in ("max_run_seconds", "max_request_ttl_seconds", "max_bytes"):
        value = limits.get(field)
        if not isinstance(value, int) or value < 1:
            raise ProviderInvocationError(f"invalid provider invocation limit: {field}")

    security = contract.get("security")
    if not isinstance(security, dict):
        raise ProviderInvocationError("provider invocation security contract missing")
    required_security = {
        "https_only": True,
        "arbitrary_url_allowed": False,
        "arbitrary_shell_allowed": False,
        "public_mac_listener_allowed": False,
        "off_host_redirect_allowed": False,
        "personal_chrome_profile_allowed": False,
    }
    for key, expected in required_security.items():
        if security.get(key) is not expected:
            raise ProviderInvocationError(f"provider invocation security boundary violated: {key}")

    source_policies = contract.get("source_policies")
    if not isinstance(source_policies, dict):
        raise ProviderInvocationError("provider invocation source_policies must be an object")
    return contract


def _source_policy(contract: dict[str, Any], source_id: str) -> dict[str, Any]:
    if not _SOURCE_ID.fullmatch(source_id):
        raise ProviderInvocationError("invalid provider source_id")
    source_policies = contract.get("source_policies")
    policy = source_policies.get(source_id) if isinstance(source_policies, dict) else None
    if not isinstance(policy, dict) or policy.get("enabled") is not True:
        raise ProviderInvocationError(f"source is not authorized for provider invocation: {source_id}")
    version = policy.get("source_policy_version")
    if not isinstance(version, int) or version < 1:
        raise ProviderInvocationError(f"invalid provider source policy version: {source_id}")
    allowed = policy.get("allowed_capabilities")
    if not isinstance(allowed, list) or not allowed or not set(allowed).issubset(CAPABILITY_TOOL_MAP):
        raise ProviderInvocationError(f"invalid provider capability allowlist: {source_id}")
    targets = policy.get("targets")
    if not isinstance(targets, dict) or not targets:
        raise ProviderInvocationError(f"provider target policy missing: {source_id}")
    return policy


def _validate_url(target: dict[str, Any], requested_url: str) -> None:
    parsed = urlparse(requested_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ProviderInvocationError("provider URL violates HTTPS authority boundary")

    decoded = unquote(parsed.path)
    if ".." in decoded.split("/"):
        raise ProviderInvocationError("provider URL path traversal is forbidden")

    exact_urls = target.get("exact_urls")
    if isinstance(exact_urls, list) and exact_urls:
        if requested_url not in exact_urls:
            raise ProviderInvocationError("provider URL is not an approved exact target")
        return

    host = target.get("https_host")
    if not isinstance(host, str) or parsed.hostname != host:
        raise ProviderInvocationError("provider URL host is not approved")
    prefix = target.get("path_prefix")
    if not isinstance(prefix, str) or not parsed.path.startswith(prefix):
        raise ProviderInvocationError("provider URL path is outside approved prefix")
    suffix = target.get("path_suffix")
    if isinstance(suffix, str) and suffix and not parsed.path.lower().endswith(suffix.lower()):
        raise ProviderInvocationError("provider URL suffix is not approved")
    if parsed.query and target.get("allow_query") is not True:
        raise ProviderInvocationError("provider URL query is not approved")
    if parsed.fragment and target.get("allow_fragment") is not True:
        raise ProviderInvocationError("provider URL fragment is not approved")


def _validate_interaction_plan(capability: str, plan: object) -> None:
    if capability != ProviderCapability.C3_BROWSER_USE.value:
        if plan is not None:
            raise ProviderInvocationError("interaction_plan is only valid for C3_BROWSER_USE")
        return

    if not isinstance(plan, dict):
        raise ProviderInvocationError("C3_BROWSER_USE requires interaction_plan")
    if plan.get("side_effect_class") != C3_SIDE_EFFECT_CLASS:
        raise ProviderInvocationError("C3 side_effect_class must be READ_ONLY_NAVIGATION")
    retry_safe = plan.get("retry_safe")
    if not isinstance(retry_safe, bool):
        raise ProviderInvocationError("C3 retry_safe must be explicit boolean")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps or len(steps) > 64:
        raise ProviderInvocationError("C3 interaction steps must contain 1..64 entries")
    for step in steps:
        if not isinstance(step, dict) or step.get("action") not in C3_ALLOWED_ACTIONS:
            raise ProviderInvocationError("C3 interaction action is not authorized")
        if any(key in step for key in ("shell", "javascript", "script", "command")):
            raise ProviderInvocationError("C3 arbitrary execution fields are forbidden")


def validate_provider_request(
    request: dict[str, Any],
    *,
    contract: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    validate_contract_projection(contract)
    if not isinstance(request, dict):
        raise ProviderInvocationError("provider request must be an object")
    if request.get("contract_version") != PIC_SCHEMA_VERSION:
        raise ProviderInvocationError("provider request contract_version mismatch")
    if request.get("provider_id") != contract.get("provider_id"):
        raise ProviderInvocationError("provider request provider_id mismatch")

    for field in (
        "provider_request_id",
        "signalforge_job_id",
        "acquisition_request_id",
        "acquisition_attempt_id",
    ):
        _require_uuid(request.get(field), field=field)

    source_id = request.get("source_id")
    if not isinstance(source_id, str):
        raise ProviderInvocationError("provider request source_id missing")
    policy = _source_policy(contract, source_id)
    if request.get("source_policy_version") != policy.get("source_policy_version"):
        raise ProviderInvocationError("provider request source policy version mismatch")

    capability = request.get("capability")
    if capability not in CAPABILITY_TOOL_MAP:
        raise ProviderInvocationError("provider request capability unknown")
    if capability not in policy.get("allowed_capabilities", []):
        raise ProviderInvocationError("provider request capability is not source-authorized")
    if request.get("mcp_tool") != CAPABILITY_TOOL_MAP[capability]:
        raise ProviderInvocationError("provider request MCP tool mismatch")

    target_role = request.get("target_role")
    targets = policy.get("targets")
    target = targets.get(target_role) if isinstance(targets, dict) and isinstance(target_role, str) else None
    if not isinstance(target, dict):
        raise ProviderInvocationError("provider request target_role is not authorized")
    target_capabilities = target.get("capabilities")
    if not isinstance(target_capabilities, list) or capability not in target_capabilities:
        raise ProviderInvocationError("provider capability is not authorized for target_role")
    requested_url = request.get("requested_url")
    if not isinstance(requested_url, str):
        raise ProviderInvocationError("provider request requested_url missing")
    _validate_url(target, requested_url)

    limits = contract["limits"]
    max_bytes = request.get("max_bytes")
    max_run_seconds = request.get("max_run_seconds")
    if not isinstance(max_bytes, int) or not 1 <= max_bytes <= int(limits["max_bytes"]):
        raise ProviderInvocationError("provider request max_bytes exceeds contract")
    if not isinstance(max_run_seconds, int) or not 1 <= max_run_seconds <= int(limits["max_run_seconds"]):
        raise ProviderInvocationError("provider request max_run_seconds exceeds contract")
    target_max_bytes = target.get("max_bytes")
    if isinstance(target_max_bytes, int) and max_bytes > target_max_bytes:
        raise ProviderInvocationError("provider request max_bytes exceeds target policy")
    target_max_run = target.get("max_run_seconds")
    if isinstance(target_max_run, int) and max_run_seconds > target_max_run:
        raise ProviderInvocationError("provider request max_run_seconds exceeds target policy")

    requested_at = _parse_time(request.get("requested_at"), field="requested_at")
    expires_at = _parse_time(request.get("expires_at"), field="expires_at")
    if expires_at <= requested_at:
        raise ProviderInvocationError("provider request expires_at must be after requested_at")
    if (expires_at - requested_at).total_seconds() > int(limits["max_request_ttl_seconds"]):
        raise ProviderInvocationError("provider request TTL exceeds contract")
    observed_now = (now or datetime.now(UTC)).astimezone(UTC)
    if expires_at <= observed_now:
        raise ProviderInvocationError("provider request expired")

    provider_request_id = request["provider_request_id"]
    if request.get("idempotency_key") != f"sf-provider:{provider_request_id}":
        raise ProviderInvocationError("provider request idempotency key mismatch")
    _validate_interaction_plan(capability, request.get("interaction_plan"))

    supplied_hash = request.get("request_sha256")
    if not isinstance(supplied_hash, str) or supplied_hash != request_sha256(request):
        raise ProviderInvocationError("provider request SHA-256 mismatch")
    return request


def build_provider_request(
    *,
    contract: dict[str, Any],
    source_id: str,
    source_policy_version: int,
    capability: str,
    target_role: str,
    requested_url: str,
    signalforge_job_id: str,
    acquisition_request_id: str,
    acquisition_attempt_id: str,
    max_bytes: int,
    max_run_seconds: int,
    interaction_plan: dict[str, Any] | None = None,
    now: datetime | None = None,
    ttl_seconds: int = 90,
) -> dict[str, Any]:
    validate_contract_projection(contract)
    observed_now = (now or datetime.now(UTC)).astimezone(UTC)
    provider_request_id = str(uuid.uuid4())
    request = {
        "contract_version": PIC_SCHEMA_VERSION,
        "provider_request_id": provider_request_id,
        "provider_id": PIC_PROVIDER_ID,
        "signalforge_job_id": signalforge_job_id,
        "acquisition_request_id": acquisition_request_id,
        "acquisition_attempt_id": acquisition_attempt_id,
        "source_id": source_id,
        "source_policy_version": source_policy_version,
        "capability": capability,
        "mcp_tool": CAPABILITY_TOOL_MAP.get(capability),
        "target_role": target_role,
        "requested_url": requested_url,
        "max_bytes": max_bytes,
        "max_run_seconds": max_run_seconds,
        "requested_at": observed_now.isoformat().replace("+00:00", "Z"),
        "expires_at": (observed_now + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z"),
        "idempotency_key": f"sf-provider:{provider_request_id}",
        "interaction_plan": interaction_plan,
    }
    request["request_sha256"] = request_sha256(request)
    return validate_provider_request(request, contract=contract, now=observed_now)
