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

    egress_profile = source.get("egress_profile")
    if egress_profile != "mm-intl-datacenter":
        raise AcquisitionContractError(f"v1.5 local source must use mm-intl-datacenter: {source_id}")

    policy = source.get("acquisition_policy")
    if not isinstance(policy, dict) or policy.get("enabled") is not True:
        raise AcquisitionContractError(f"active source acquisition policy missing: {source_id}")

    primary = policy.get("primary")
    if not isinstance(primary, dict):
        raise AcquisitionContractError(f"acquisition primary policy missing: {source_id}")
    if primary.get("method") != "DIRECT_HTTP":
        raise AcquisitionContractError(f"v1.5 P0 primary method must be DIRECT_HTTP: {source_id}")
    if primary.get("target_kind") != "HTML":
        raise AcquisitionContractError(f"v1.5 P0 primary target_kind must be HTML: {source_id}")

    supplementary = policy.get("supplementary")
    if not isinstance(supplementary, list):
        raise AcquisitionContractError(f"acquisition supplementary policy must be a list: {source_id}")

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
