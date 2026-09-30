from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable

from .config import db_path
from .db import connect
from .provider_queue import initialize_provider_queue

PUBLIC_READ_CAPABILITY = "PUBLIC_READ_ACQUIRE"
TERMINAL_FAILURE_STATES = {"FAILED", "EXPIRED", "CANCELLED"}
MIN_OBSERVATION_HOURS = 24
MIN_INSTRUMENTED_REQUESTS = 10


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 3)


def _counter_dict(values: Iterable[str | None]) -> dict[str, int]:
    return dict(sorted(Counter(value or "NONE" for value in values).items()))


def _load_route(value: str | None) -> dict[str, object] | None:
    if not value:
        return None
    try:
        route = json.loads(value)
    except json.JSONDecodeError:
        return None
    return route if isinstance(route, dict) else None


def _initialize_alert_table(database: Path) -> None:
    with connect(database) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS public_read_telemetry_alert_receipts (
                alert_fingerprint TEXT PRIMARY KEY,
                observed_at TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                telegram_message_id TEXT
            )
            """
        )


def public_read_telemetry_report(
    *,
    database: Path | None = None,
    now: datetime | None = None,
    window_hours: int = 24,
    min_observation_hours: int = MIN_OBSERVATION_HOURS,
    min_instrumented_requests: int = MIN_INSTRUMENTED_REQUESTS,
) -> dict[str, object]:
    if window_hours < 1 or window_hours > 24 * 30:
        raise ValueError("window_hours must be 1..720")
    if min_observation_hours < 1:
        raise ValueError("min_observation_hours must be positive")
    if min_instrumented_requests < 1:
        raise ValueError("min_instrumented_requests must be positive")

    target = database or db_path()
    initialize_provider_queue(target)
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    cutoff = observed - timedelta(hours=window_hours)

    with connect(target) as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT provider_request_id,source_id,state,created_at,requested_at,completed_at,
                       result_sha256,browser_job_id,result_media_type,result_artifact_bytes,
                       result_http_status,result_route_json,failure_class
                FROM provider_requests
                WHERE capability=?
                  AND created_at>=?
                ORDER BY created_at ASC
                """,
                (PUBLIC_READ_CAPABILITY, _iso(cutoff)),
            )
        ]
        first_instrumented_row = conn.execute(
            """
            SELECT provider_request_id,source_id,created_at,completed_at,result_route_json
            FROM provider_requests
            WHERE capability=? AND state='SUCCEEDED' AND result_route_json IS NOT NULL
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (PUBLIC_READ_CAPABILITY,),
        ).fetchone()

    state_counts = _counter_dict(str(row["state"]) for row in rows)
    source_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        source_counts[str(row["source_id"])][str(row["state"])] += 1

    successes = [row for row in rows if row["state"] == "SUCCEEDED"]
    latency_seconds: list[float] = []
    artifact_bytes: list[int] = []
    routes: list[dict[str, object]] = []
    route_parse_errors = 0
    for row in successes:
        created = _parse_time(row.get("created_at"))
        completed = _parse_time(row.get("completed_at"))
        if created and completed and completed >= created:
            latency_seconds.append((completed - created).total_seconds())
        if isinstance(row.get("result_artifact_bytes"), int):
            artifact_bytes.append(int(row["result_artifact_bytes"]))
        if row.get("result_route_json"):
            route = _load_route(str(row["result_route_json"]))
            if route is None:
                route_parse_errors += 1
            else:
                routes.append(route)

    selected_capabilities = _counter_dict(str(route.get("selected_capability") or "NONE") for route in routes)
    selected_transports = _counter_dict(str(route.get("selected_transport") or "NONE") for route in routes)
    selected_engines = _counter_dict(str(route.get("selected_engine") or "NONE") for route in routes)
    render_triggers = _counter_dict(str(route.get("render_trigger") or "NONE") for route in routes)
    c1_routes = [route for route in routes if route.get("selected_capability") == "C1_RENDER"]

    first_instrumented_at: datetime | None = None
    first_natural_c1: dict[str, object] | None = None
    observation_rows: list[dict[str, object]] = []
    if first_instrumented_row is not None:
        first_instrumented_at = _parse_time(str(first_instrumented_row["created_at"] or ""))
        if first_instrumented_at is not None:
            with connect(target) as conn:
                observation_rows = [
                    dict(row)
                    for row in conn.execute(
                        """
                        SELECT provider_request_id,source_id,state,created_at,completed_at,
                               result_sha256,browser_job_id,result_media_type,result_artifact_bytes,
                               result_route_json,failure_class
                        FROM provider_requests
                        WHERE capability=?
                          AND COALESCE(completed_at,created_at)>=?
                        ORDER BY COALESCE(completed_at,created_at) ASC
                        """,
                        (PUBLIC_READ_CAPABILITY, _iso(first_instrumented_at)),
                    )
                ]
                c1_row = conn.execute(
                    """
                    SELECT provider_request_id,source_id,completed_at,result_route_json
                    FROM provider_requests
                    WHERE capability=? AND state='SUCCEEDED' AND result_route_json IS NOT NULL
                      AND completed_at>=?
                    ORDER BY completed_at ASC
                    """,
                    (PUBLIC_READ_CAPABILITY, _iso(first_instrumented_at)),
                ).fetchall()
            for row in c1_row:
                route = _load_route(str(row["result_route_json"]))
                if route and route.get("selected_capability") == "C1_RENDER":
                    first_natural_c1 = {
                        "provider_request_id": str(row["provider_request_id"]),
                        "source_id": str(row["source_id"]),
                        "completed_at": str(row["completed_at"]),
                        "render_trigger": route.get("render_trigger"),
                        "selected_engine": route.get("selected_engine"),
                        "selected_browser_engine": route.get("selected_browser_engine"),
                    }
                    break

    observation_successes = [row for row in observation_rows if row["state"] == "SUCCEEDED"]
    current_post_instrumentation: list[dict[str, object]] = []
    if first_instrumented_at is not None:
        for row in rows:
            created_at = _parse_time(str(row.get("created_at") or ""))
            if created_at is not None and created_at >= first_instrumented_at:
                current_post_instrumentation.append(row)
    terminal_failures = [
        row for row in current_post_instrumentation if row["state"] in TERMINAL_FAILURE_STATES
    ]
    current_successes = [
        row for row in current_post_instrumentation if row["state"] == "SUCCEEDED"
    ]
    missing_route_after_start = [
        row for row in current_successes if not row.get("result_route_json")
    ]
    integrity_anomalies = [
        row
        for row in current_successes
        if not row.get("result_sha256")
        or not row.get("browser_job_id")
        or not row.get("result_media_type")
        or not isinstance(row.get("result_artifact_bytes"), int)
    ]

    anomalies: list[dict[str, object]] = []
    if terminal_failures:
        anomalies.append(
            {
                "code": "PUBLIC_READ_TERMINAL_FAILURE",
                "count": len(terminal_failures),
                "latest_provider_request_id": str(terminal_failures[-1]["provider_request_id"]),
                "latest_source_id": str(terminal_failures[-1]["source_id"]),
                "latest_state": str(terminal_failures[-1]["state"]),
                "latest_failure_class": terminal_failures[-1].get("failure_class"),
            }
        )
    if missing_route_after_start:
        anomalies.append(
            {
                "code": "ROUTE_SUMMARY_MISSING_AFTER_INSTRUMENTATION",
                "count": len(missing_route_after_start),
                "latest_provider_request_id": str(missing_route_after_start[-1]["provider_request_id"]),
                "latest_source_id": str(missing_route_after_start[-1]["source_id"]),
            }
        )
    if integrity_anomalies:
        anomalies.append(
            {
                "code": "PUBLIC_READ_RESULT_INTEGRITY_INCOMPLETE",
                "count": len(integrity_anomalies),
                "latest_provider_request_id": str(integrity_anomalies[-1]["provider_request_id"]),
            }
        )
    if route_parse_errors:
        anomalies.append({"code": "ROUTE_SUMMARY_PARSE_ERROR", "count": route_parse_errors})

    observation_hours = (
        max(0.0, (observed - first_instrumented_at).total_seconds() / 3600.0)
        if first_instrumented_at
        else 0.0
    )
    instrumented_count = sum(1 for row in observation_successes if row.get("result_route_json"))
    if first_instrumented_at is None:
        gate_status = "NO_DATA"
    elif anomalies:
        gate_status = "FAIL"
    elif observation_hours < min_observation_hours or instrumented_count < min_instrumented_requests:
        gate_status = "OBSERVING"
    else:
        gate_status = "PASS"

    return {
        "status": "DEGRADED" if anomalies else "PASS",
        "as_of": _iso(observed),
        "window_hours": window_hours,
        "requests_total": len(rows),
        "state_counts": state_counts,
        "success_rate": round(len(successes) / len(rows), 4) if rows else None,
        "by_source": {source: dict(sorted(counts.items())) for source, counts in sorted(source_counts.items())},
        "routes": {
            "instrumented_successes_in_window": len(routes),
            "legacy_missing_route_in_window": sum(
                1 for row in successes if not row.get("result_route_json")
            ),
            "selected_capabilities": selected_capabilities,
            "selected_transports": selected_transports,
            "selected_engines": selected_engines,
            "render_triggers": render_triggers,
            "c1_count": len(c1_routes),
            "first_natural_c1": first_natural_c1,
        },
        "latency_seconds": {
            "count": len(latency_seconds),
            "p50": _percentile(latency_seconds, 0.50),
            "p95": _percentile(latency_seconds, 0.95),
            "max": round(max(latency_seconds), 3) if latency_seconds else None,
            "scope": "provider_e2e_created_to_completed",
        },
        "artifact_bytes": {
            "count": len(artifact_bytes),
            "total": sum(artifact_bytes),
            "max": max(artifact_bytes) if artifact_bytes else None,
        },
        "anomalies": anomalies,
        "verification_gate": {
            "status": gate_status,
            "first_instrumented_at": _iso(first_instrumented_at) if first_instrumented_at else None,
            "observed_hours": round(observation_hours, 3),
            "required_hours": min_observation_hours,
            "instrumented_successes": instrumented_count,
            "required_instrumented_successes": min_instrumented_requests,
            "terminal_failures_in_window": len(terminal_failures),
            "missing_route_in_window": len(missing_route_after_start),
            "integrity_anomalies_in_window": len(integrity_anomalies),
            "natural_c1_observed": first_natural_c1 is not None,
        },
    }


def _alert_fingerprint(report: dict[str, object]) -> str:
    anomalies = report.get("anomalies")
    payload = anomalies if isinstance(anomalies, list) else []
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _render_alert(report: dict[str, object]) -> str:
    gate = report.get("verification_gate") or {}
    routes = report.get("routes") or {}
    states = report.get("state_counts") or {}
    anomalies = report.get("anomalies") or []
    anomaly_text = "; ".join(
        f"{item.get('code')}={item.get('count', 1)}"
        for item in anomalies
        if isinstance(item, dict)
    )
    selected = routes.get("selected_capabilities") if isinstance(routes, dict) else {}
    transports = routes.get("selected_transports") if isinstance(routes, dict) else {}
    return "\n".join(
        [
            "⚠️ SignalForge Public Read Health",
            "Status: DEGRADED",
            f"Window: {report.get('window_hours')}H",
            f"Anomalies: {anomaly_text or 'UNKNOWN'}",
            f"States: {json.dumps(states, ensure_ascii=False, sort_keys=True)}",
            f"Routes: {json.dumps(selected, ensure_ascii=False, sort_keys=True)}",
            f"Transports: {json.dumps(transports, ensure_ascii=False, sort_keys=True)}",
            f"24H Gate: {gate.get('status') if isinstance(gate, dict) else 'UNKNOWN'}",
        ]
    )


def public_read_telemetry_alert(
    *,
    database: Path | None = None,
    now: datetime | None = None,
    window_hours: int = 24,
    bot_token: str | None = None,
    chat_id: str | None = None,
    sender: Callable[..., str] | None = None,
) -> dict[str, object]:
    target = database or db_path()
    report = public_read_telemetry_report(database=target, now=now, window_hours=window_hours)
    anomalies = report.get("anomalies")
    if not isinstance(anomalies, list) or not anomalies:
        return {"status": "QUIET", "sent": False, "report": report}

    _initialize_alert_table(target)
    fingerprint = _alert_fingerprint(report)
    with connect(target) as conn:
        existing = conn.execute(
            "SELECT telegram_message_id,sent_at FROM public_read_telemetry_alert_receipts WHERE alert_fingerprint=?",
            (fingerprint,),
        ).fetchone()
    if existing is not None:
        return {
            "status": "DEDUPLICATED",
            "sent": False,
            "fingerprint": fingerprint,
            "previous_sent_at": str(existing["sent_at"]),
            "report": report,
        }

    token = bot_token or os.environ.get("SIGNALFORGE_TELEGRAM_BOT_TOKEN", "")
    target_chat = chat_id or os.environ.get("SIGNALFORGE_TELEGRAM_CHAT_ID", "")
    if not token or not target_chat:
        raise RuntimeError("telegram credentials are not configured for public-read telemetry alert")

    message = _render_alert(report)
    if sender is None:
        from .telegram_delivery import _send_message
        sender = _send_message
    message_id = sender(bot_token=token, chat_id=target_chat, text=message)
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    with connect(target) as conn, conn:
        conn.execute(
            """
            INSERT INTO public_read_telemetry_alert_receipts(
                alert_fingerprint,observed_at,sent_at,payload_json,telegram_message_id
            ) VALUES (?,?,?,?,?)
            """,
            (
                fingerprint,
                str(report["as_of"]),
                _iso(observed),
                json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                message_id,
            ),
        )
    return {
        "status": "ALERT_SENT",
        "sent": True,
        "fingerprint": fingerprint,
        "telegram_message_id": message_id,
        "report": report,
    }
