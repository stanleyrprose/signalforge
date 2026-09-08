from __future__ import annotations

import socket
import ssl
import urllib.error
from enum import Enum
from typing import Any


ACQUISITION_SCHEMA_VERSION = 1
LOCAL_PROVIDER_ID = "bkk-local"
LOCAL_PROVIDER_BASELINE_VERSION = 1
LOCAL_EXECUTION_SCOPE = "LOCAL_BANGKOK"


class AcquisitionContractError(RuntimeError):
    pass


class AcquisitionFailure(str, Enum):
    DNS_FAILURE = "DNS_FAILURE"
    TLS_FAILURE = "TLS_FAILURE"
    CONNECT_TIMEOUT = "CONNECT_TIMEOUT"
    HTTP_403 = "HTTP_403"
    HTTP_404 = "HTTP_404"
    HTTP_429 = "HTTP_429"
    HTTP_5XX = "HTTP_5XX"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    BOT_BLOCKED = "BOT_BLOCKED"
    JS_RENDER_REQUIRED = "JS_RENDER_REQUIRED"
    CONTENT_EMPTY = "CONTENT_EMPTY"
    CONTENT_TYPE_MISMATCH = "CONTENT_TYPE_MISMATCH"
    CONTENT_VALIDATION_FAILURE = "CONTENT_VALIDATION_FAILURE"
    TRANSPORT_UNKNOWN = "TRANSPORT_UNKNOWN"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_REQUEST_EXPIRED = "PROVIDER_REQUEST_EXPIRED"
    PROVIDER_POLICY_REJECTED = "PROVIDER_POLICY_REJECTED"
    PROVIDER_CONTRACT_MISMATCH = "PROVIDER_CONTRACT_MISMATCH"
    PROVIDER_LEASE_CONFLICT = "PROVIDER_LEASE_CONFLICT"
    PROVIDER_RESULT_INVALID = "PROVIDER_RESULT_INVALID"
    PROVIDER_ARTIFACT_HASH_MISMATCH = "PROVIDER_ARTIFACT_HASH_MISMATCH"
    PROVIDER_IDEMPOTENCY_CONFLICT = "PROVIDER_IDEMPOTENCY_CONFLICT"


class ProcessingFailure(str, Enum):
    HTML_PARSE_FAILURE = "HTML_PARSE_FAILURE"
    PDF_PARSE_FAILURE = "PDF_PARSE_FAILURE"
    PARSER_DRIFT = "PARSER_DRIFT"
    NORMALIZATION_FAILURE = "NORMALIZATION_FAILURE"
    CANONICAL_VALIDATION_FAILURE = "CANONICAL_VALIDATION_FAILURE"
    PROCESSING_UNKNOWN = "PROCESSING_UNKNOWN"


REQUEST_REASONS = {
    "SCHEDULED",
    "MANUAL",
    "RECONCILIATION",
    "HEALTH_PROBE",
    "DIAGNOSTIC",
}

ALLOWED_POLICY_ACTIONS = {
    "RETRY",
    "REVIEW",
    "FAIL",
    "REVIEW_CAPABILITY",
    "REAUDIT",
}


def validate_source_acquisition_policy(source_id: str, source: dict[str, Any]) -> None:
    version = source.get("source_policy_version")
    if not isinstance(version, int) or version < 1:
        raise AcquisitionContractError(f"invalid source_policy_version: {source_id}")

    engine = source.get("engine")
    egress_profile = source.get("egress_profile")
    if engine == "direct_http":
        if egress_profile != "mm-intl-datacenter":
            raise AcquisitionContractError(f"Direct HTTP source must use mm-intl-datacenter: {source_id}")
    elif engine == "provider":
        if egress_profile != "mac-direct":
            raise AcquisitionContractError(f"Provider source must use mac-direct: {source_id}")
        if source.get("provider_id") != "mac-mm-01":
            raise AcquisitionContractError(f"Provider source must use mac-mm-01: {source_id}")
    else:
        raise AcquisitionContractError(f"unsupported acquisition engine: {source_id}")

    policy = source.get("acquisition_policy")
    if not isinstance(policy, dict) or policy.get("enabled") is not True:
        raise AcquisitionContractError(f"active source acquisition policy missing: {source_id}")

    primary = policy.get("primary")
    if not isinstance(primary, dict):
        raise AcquisitionContractError(f"acquisition primary policy missing: {source_id}")
    expected_method = "DIRECT_HTTP" if engine == "direct_http" else "MAC_BROWSER_PROVIDER"
    if primary.get("method") != expected_method:
        raise AcquisitionContractError(f"primary acquisition method mismatch for {source_id}: expected {expected_method}")
    if primary.get("target_kind") != "HTML":
        raise AcquisitionContractError(f"primary target_kind must be HTML: {source_id}")
    if engine == "provider":
        if primary.get("provider_id") != "mac-mm-01" or primary.get("capability") != "C0_FETCH":
            raise AcquisitionContractError(f"provider primary policy must pin mac-mm-01 C0_FETCH: {source_id}")

    supplementary = policy.get("supplementary")
    if not isinstance(supplementary, list):
        raise AcquisitionContractError(f"acquisition supplementary policy must be a list: {source_id}")
    for item in supplementary:
        if not isinstance(item, dict):
            raise AcquisitionContractError(f"supplementary acquisition policy entry invalid: {source_id}")
        if engine != "direct_http":
            raise AcquisitionContractError(f"provider source supplementary acquisition is not authorized: {source_id}")
        if item.get("method") != "DIRECT_HTTP" or item.get("target_kind") != "PDF":
            raise AcquisitionContractError(f"supplementary acquisition must be Direct HTTP PDF: {source_id}")
        if item.get("same_origin_only") is not True:
            raise AcquisitionContractError(f"supplementary PDF must be same-origin: {source_id}")
        if not isinstance(item.get("required"), bool):
            raise AcquisitionContractError(f"supplementary PDF required flag missing: {source_id}")
        max_count = item.get("max_count")
        if not isinstance(max_count, int) or max_count < 1 or max_count > 4:
            raise AcquisitionContractError(f"supplementary PDF max_count invalid: {source_id}")

    escalation = policy.get("escalation")
    if not isinstance(escalation, dict):
        raise AcquisitionContractError(f"acquisition escalation policy missing: {source_id}")

    known_failures = {item.value for item in AcquisitionFailure} | {item.value for item in ProcessingFailure}
    for failure, rule in escalation.items():
        if failure not in known_failures:
            raise AcquisitionContractError(f"unknown acquisition policy failure {failure}: {source_id}")
        if not isinstance(rule, dict) or rule.get("action") not in ALLOWED_POLICY_ACTIONS:
            raise AcquisitionContractError(f"invalid acquisition policy action for {failure}: {source_id}")

    if (escalation.get("TLS_FAILURE") or {}).get("action") != "FAIL":
        raise AcquisitionContractError(f"TLS_FAILURE must fail closed: {source_id}")
    if (escalation.get("JS_RENDER_REQUIRED") or {}).get("action") != "REVIEW_CAPABILITY":
        raise AcquisitionContractError(f"JS_RENDER_REQUIRED must require capability review: {source_id}")
    if (escalation.get("PARSER_DRIFT") or {}).get("action") != "REAUDIT":
        raise AcquisitionContractError(f"PARSER_DRIFT must require re-audit: {source_id}")


def request_reason(trigger_kind: str, *, health_probe: bool = False) -> str:
    if health_probe:
        return "HEALTH_PROBE"
    mapping = {
        "POLL": "SCHEDULED",
        "MANUAL": "MANUAL",
        "RECONCILIATION": "RECONCILIATION",
    }
    try:
        return mapping[trigger_kind]
    except KeyError as exc:
        raise AcquisitionContractError(f"unsupported acquisition trigger kind: {trigger_kind}") from exc


def _walk_exception(exc: BaseException):  # type: ignore[no-untyped-def]
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        cause = current.__cause__ or current.__context__
        current = cause if isinstance(cause, BaseException) else None


def classify_acquisition_failure(exc: BaseException) -> AcquisitionFailure:
    chain = list(_walk_exception(exc))
    text = " ".join(str(item) for item in chain).lower()

    for item in chain:
        if isinstance(item, urllib.error.HTTPError):
            code = int(item.code)
            if code == 403:
                return AcquisitionFailure.HTTP_403
            if code == 404:
                return AcquisitionFailure.HTTP_404
            if code == 429:
                return AcquisitionFailure.HTTP_429
            if 500 <= code <= 599:
                return AcquisitionFailure.HTTP_5XX
        if isinstance(item, ssl.SSLError):
            return AcquisitionFailure.TLS_FAILURE
        if isinstance(item, (TimeoutError, socket.timeout)):
            return AcquisitionFailure.CONNECT_TIMEOUT
        if isinstance(item, socket.gaierror):
            return AcquisitionFailure.DNS_FAILURE

    if "http 403" in text:
        return AcquisitionFailure.HTTP_403
    if "http 404" in text:
        return AcquisitionFailure.HTTP_404
    if "http 429" in text:
        return AcquisitionFailure.HTTP_429
    if any(f"http {code}" in text for code in range(500, 600)):
        return AcquisitionFailure.HTTP_5XX
    if "certificate" in text or "tls" in text or "ssl" in text:
        return AcquisitionFailure.TLS_FAILURE
    if "timed out" in text or "timeout" in text:
        return AcquisitionFailure.CONNECT_TIMEOUT
    if "name or service not known" in text or "nodename nor servname" in text or "temporary failure in name resolution" in text:
        return AcquisitionFailure.DNS_FAILURE
    return AcquisitionFailure.TRANSPORT_UNKNOWN
