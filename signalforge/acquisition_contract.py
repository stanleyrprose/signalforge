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
        if primary.get("provider_id") != "mac-mm-01" or primary.get("capability") != "PUBLIC_READ_ACQUIRE":
            raise AcquisitionContractError(
                f"provider primary policy must pin mac-mm-01 PUBLIC_READ_ACQUIRE: {source_id}"
            )

    detail_target_kind = str(source.get("detail_target_kind") or "HTML").upper()
    if detail_target_kind not in {"HTML", "PDF"}:
        raise AcquisitionContractError(f"unsupported detail_target_kind: {source_id}")
    if detail_target_kind == "PDF" and engine != "direct_http":
        raise AcquisitionContractError(f"PDF detail target requires Direct HTTP: {source_id}")

    supplementary = policy.get("supplementary")
    if not isinstance(supplementary, list):
        raise AcquisitionContractError(f"acquisition supplementary policy must be a list: {source_id}")
    expected_supplementary_method = "DIRECT_HTTP" if engine == "direct_http" else "MAC_BROWSER_PROVIDER"
    for item in supplementary:
        if not isinstance(item, dict):
            raise AcquisitionContractError(f"supplementary acquisition policy entry invalid: {source_id}")
        if item.get("method") != expected_supplementary_method or item.get("target_kind") != "PDF":
            raise AcquisitionContractError(
                f"supplementary acquisition must be {expected_supplementary_method} PDF: {source_id}"
            )
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


    tls_policy = source.get("tls_policy")
    if tls_policy is not None:
        if source_id != "S55":
            raise AcquisitionContractError(f"insecure TLS policy is restricted to S55: {source_id}")
        if source.get("http_fetch_profile") != "myawady_insecure_readonly_v2":
            raise AcquisitionContractError("S55 insecure TLS policy requires the reviewed Myawady fetch profile")
        if not isinstance(tls_policy, dict):
            raise AcquisitionContractError("S55 tls_policy must be an object")
        expected = {
            "mode": "INSECURE_READONLY_ALWAYS",
            "allowed_hosts": ["myawady.net.mm", "www.myawady.net.mm"],
            "read_only": True,
            "no_credentials": True,
            "same_origin_redirects_only": True,
        }
        if tls_policy != expected:
            raise AcquisitionContractError("S55 tls_policy does not match the reviewed read-only exception")

    document_ocr_detail = source.get("document_ocr_detail")
    if document_ocr_detail is not None:
        if source_id != "S56":
            raise AcquisitionContractError(f"detail DOCUMENT_OCR policy is restricted to S56: {source_id}")
        if source.get("adapter") != "official_media_myanma_alinn":
            raise AcquisitionContractError("S56 detail DOCUMENT_OCR requires the Myanma Alinn adapter")
        if not isinstance(document_ocr_detail, dict):
            raise AcquisitionContractError("S56 document_ocr_detail must be an object")
        if document_ocr_detail.get("enabled") is not True:
            raise AcquisitionContractError("S56 document_ocr_detail must be enabled")
        if (
            document_ocr_detail.get("provider_id") != "mac-mm-01"
            or document_ocr_detail.get("capability") != "DOCUMENT_OCR"
            or document_ocr_detail.get("target_role") != "OFFICIAL_NEWSPAPER"
        ):
            raise AcquisitionContractError("S56 document_ocr_detail provider boundary invalid")
        if document_ocr_detail.get("allowed_https_hosts") != ["www.moi.gov.mm"]:
            raise AcquisitionContractError("S56 document_ocr_detail host allowlist invalid")
        if document_ocr_detail.get("allowed_path_prefix") != "/mal/sites/default/files/newspaper-pdf/":
            raise AcquisitionContractError("S56 document_ocr_detail path boundary invalid")
        max_bytes = document_ocr_detail.get("max_bytes")
        timeout_seconds = document_ocr_detail.get("timeout_seconds")
        if not isinstance(max_bytes, int) or max_bytes < 1 or max_bytes > 8_000_000:
            raise AcquisitionContractError("S56 document_ocr_detail max_bytes invalid")
        if not isinstance(timeout_seconds, int) or timeout_seconds < 1 or timeout_seconds > 300:
            raise AcquisitionContractError("S56 document_ocr_detail timeout invalid")
        if supplementary:
            raise AcquisitionContractError("S56 detail DOCUMENT_OCR must not duplicate Bangkok PDF acquisition")


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
