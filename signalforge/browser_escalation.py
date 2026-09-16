from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .config import Registry, db_path
from .db import connect


REPORT_VERSION = 1
DEFAULT_WINDOW_DAYS = 7
DEFAULT_LIMIT = 20

# These failure classes are evidence that rendering/automation capability may add
# acquisition value. They authorize an A/B diagnostic only; they never authorize
# a source-routing change by themselves.
_BROWSER_AB_FAILURES = {
    "BOT_BLOCKED": (100, "browser_or_automation_block_evidence"),
    "JS_RENDER_REQUIRED": (95, "javascript_render_required"),
    "CONTENT_EMPTY": (85, "html_fetch_returned_no_usable_content"),
}

# A generic 403 is deliberately not a browser trigger. Authentication,
# authorization, region policy, rate limiting/WAF policy and account state can all
# produce 403. Repeated real-fetcher 403s are surfaced for human review first.
_REVIEW_FAILURES = {
    "HTTP_403": "verify_403_is_automation_challenge_before_browser_ab",
    "TRANSPORT_UNKNOWN": "classify_transport_failure_before_browser_ab",
}

# These are explicitly not browser-engine selection problems.
_NOT_BROWSER_FAILURES = {
    "DNS_FAILURE": "network_dns_failure",
    "TLS_FAILURE": "strict_tls_failure",
    "CONNECT_TIMEOUT": "network_or_origin_timeout",
    "HTTP_404": "issuer_path_or_content_missing",
    "HTTP_429": "rate_limit",
    "HTTP_5XX": "issuer_server_failure",
    "AUTH_REQUIRED": "authentication_or_authorization_required",
    "CONTENT_TYPE_MISMATCH": "content_contract_mismatch",
    "CONTENT_VALIDATION_FAILURE": "content_validation_or_parser_boundary",
    "PROVIDER_TIMEOUT": "provider_transport_timeout",
    "PROVIDER_REQUEST_EXPIRED": "provider_request_lifecycle",
    "PROVIDER_POLICY_REJECTED": "provider_policy_rejection",
    "PROVIDER_CONTRACT_MISMATCH": "provider_contract_failure",
    "PROVIDER_LEASE_CONFLICT": "provider_runtime_contention",
    "PROVIDER_RESULT_INVALID": "provider_result_contract_failure",
    "PROVIDER_ARTIFACT_HASH_MISMATCH": "provider_integrity_failure",
    "PROVIDER_IDEMPOTENCY_CONFLICT": "provider_idempotency_failure",
}


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _classify(failure_counts: Counter[str]) -> tuple[str, int, list[str], str]:
    strong = [
        (score, failure, reason)
        for failure, (score, reason) in _BROWSER_AB_FAILURES.items()
        if failure_counts.get(failure, 0) > 0
    ]
    if strong:
        score, failure, reason = max(strong)
        return (
            "AB_TEST_CANDIDATE",
            score,
            [f"{failure}:{failure_counts[failure]}", reason],
            "Run bounded same-URL Chrome vs nodriver vs Camoufox A/B; do not change production routing from this report alone.",
        )

    reviews = [
        (failure, reason)
        for failure, reason in _REVIEW_FAILURES.items()
        if failure_counts.get(failure, 0) > 0
    ]
    if reviews:
        failure, reason = sorted(reviews)[0]
        count = failure_counts[failure]
        return (
            "REVIEW_FIRST",
            60 if failure == "HTTP_403" and count >= 2 else 50,
            [f"{failure}:{count}", reason],
            "Classify the failure cause first. Generic HTTP 403/unknown transport must not auto-promote a browser engine.",
        )

    known_not_browser = [
        (failure, reason)
        for failure, reason in _NOT_BROWSER_FAILURES.items()
        if failure_counts.get(failure, 0) > 0
    ]
    if known_not_browser:
        failure, reason = max(
            known_not_browser,
            key=lambda item: failure_counts[item[0]],
        )
        return (
            "NOT_BROWSER",
            0,
            [f"{failure}:{failure_counts[failure]}", reason],
            "Fix or observe the transport/source/contract condition; browser-engine A/B is not justified by this evidence.",
        )

    return (
        "UNCLASSIFIED",
        10,
        ["failure_class_not_mapped"],
        "Review the acquisition evidence before selecting any browser engine.",
    )


def browser_escalation_candidates(
    *,
    database: Path | None = None,
    registry: Registry | None = None,
    now: datetime | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, object]:
    """Build a read-only browser-escalation candidate report from acquisition history.

    This report never executes a browser, changes source policy, writes the DB, or
    treats a generic HTTP 403 as evidence of automation blocking.
    """

    if not 1 <= window_days <= 90:
        raise ValueError("window_days must be between 1 and 90")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    target = database or db_path()
    registry = registry or Registry.load()
    now = (now or datetime.now(UTC)).astimezone(UTC)
    cutoff = now - timedelta(days=window_days)
    cutoff_iso = _iso(cutoff)
    enabled = {source_id: source for source_id, source in registry.enabled_sources()}

    with connect(target) as conn:
        attempt_rows = list(
            conn.execute(
                """
                SELECT a.source_id,a.acquisition_failure_class,a.started_at,a.finished_at,
                       a.method,a.egress_profile,r.target_kind
                FROM acquisition_attempts a
                JOIN acquisition_requests r ON r.request_id=a.request_id
                WHERE a.status='FAILED'
                  AND a.started_at>=?
                  AND r.target_kind IN ('DISCOVERY','HTML')
                ORDER BY a.started_at DESC
                """,
                (cutoff_iso,),
            )
        )
        source_state = {
            str(row["source_id"]): row
            for row in conn.execute(
                """
                SELECT source_id,last_success_at,last_error,consecutive_failures,updated_at
                FROM source_state
                """
            )
        }

    by_source: dict[str, list[object]] = {}
    for row in attempt_rows:
        source_id = str(row["source_id"])
        if source_id in enabled:
            by_source.setdefault(source_id, []).append(row)

    rows: list[dict[str, object]] = []
    for source_id, failures in by_source.items():
        policy = enabled[source_id]
        failure_counts = Counter(
            str(row["acquisition_failure_class"] or "UNCLASSIFIED") for row in failures
        )
        decision, score, reasons, recommendation = _classify(failure_counts)
        state = source_state.get(source_id)
        latest = failures[0]
        rows.append(
            {
                "source_id": source_id,
                "name": policy.get("name"),
                "registry_role": policy.get("role"),
                "priority": policy.get("priority"),
                "current_engine": policy.get("engine"),
                "http_fetch_profile": policy.get("http_fetch_profile"),
                "discovery_url": policy.get("discovery_url"),
                "decision": decision,
                "candidate_score": score,
                "browser_ab_eligible": decision == "AB_TEST_CANDIDATE",
                "reasons": reasons,
                "recommendation": recommendation,
                "failed_html_attempts_window": len(failures),
                "failure_counts": dict(sorted(failure_counts.items())),
                "latest_failure_class": str(latest["acquisition_failure_class"] or "UNCLASSIFIED"),
                "latest_failure_at": latest["started_at"],
                "latest_method": latest["method"],
                "latest_egress_profile": latest["egress_profile"],
                "current_consecutive_failures": int(state["consecutive_failures"] if state is not None else 0),
                "current_last_error": state["last_error"] if state is not None else None,
                "last_success_at": state["last_success_at"] if state is not None else None,
            }
        )

    decision_rank = {
        "AB_TEST_CANDIDATE": 0,
        "REVIEW_FIRST": 1,
        "UNCLASSIFIED": 2,
        "NOT_BROWSER": 3,
    }
    rows.sort(
        key=lambda item: (
            decision_rank.get(str(item["decision"]), 9),
            -int(item["candidate_score"]),
            -int(item.get("priority") or 0),
            str(item["source_id"]),
        )
    )
    rows = rows[:limit]
    candidates = [row for row in rows if row["decision"] == "AB_TEST_CANDIDATE"]

    return {
        "status": "PASS",
        "report_version": REPORT_VERSION,
        "as_of": _iso(now),
        "window_days": window_days,
        "summary": {
            "enabled_sources": len(enabled),
            "sources_with_failed_html_attempts": len(by_source),
            "browser_ab_candidates": sum(
                1
                for source_failures in by_source.values()
                if _classify(Counter(str(row["acquisition_failure_class"] or "UNCLASSIFIED") for row in source_failures))[0]
                == "AB_TEST_CANDIDATE"
            ),
            "review_first": sum(
                1
                for source_failures in by_source.values()
                if _classify(Counter(str(row["acquisition_failure_class"] or "UNCLASSIFIED") for row in source_failures))[0]
                == "REVIEW_FIRST"
            ),
            "not_browser": sum(
                1
                for source_failures in by_source.values()
                if _classify(Counter(str(row["acquisition_failure_class"] or "UNCLASSIFIED") for row in source_failures))[0]
                == "NOT_BROWSER"
            ),
        },
        "candidates": candidates,
        "sources": rows,
        "policy": {
            "read_only": True,
            "executes_browser": False,
            "changes_source_routing": False,
            "generic_http_403_is_browser_trigger": False,
            "tls_dns_timeout_auth_are_browser_triggers": False,
            "ab_result_required_before_any_routing_change": True,
        },
    }
