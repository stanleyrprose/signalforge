from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .assurance import MANDATORY_COVERAGE_SOURCES, coverage_has_reviewed_external_recovery

HARNESS_VERSION = 1
DEFAULT_MAX_RETRIES = 3
DONE_SENSOR_IDS = ("S0", "S1", "S2", "S3")
GOAL_ID = "high_quality_government_soe_tender_intelligence"


def default_checkpoint_path(database: Path) -> Path:
    return database.parent / "harness-checkpoint.json"


def _sensor(status: str, reason_code: str, **details: object) -> dict[str, object]:
    if status not in {"PASS", "FAIL", "UNKNOWN"}:
        raise ValueError(f"invalid sensor status: {status}")
    return {"status": status, "reason_code": reason_code, **details}


def _business_items(briefing: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    attention = briefing.get("attention") or []
    if isinstance(attention, list):
        rows.extend(item for item in attention if isinstance(item, dict))
    watchlist = briefing.get("watchlist") or {}
    if isinstance(watchlist, dict):
        watch_items = watchlist.get("items") or []
        if isinstance(watch_items, list):
            rows.extend(item for item in watch_items if isinstance(item, dict))
    return rows


def evaluate_harness(
    *,
    status_snapshot: dict[str, object],
    assurance: dict[str, object],
    briefing: dict[str, object],
    telegram_dry_run: dict[str, object],
    db_quick_check: str,
    now: datetime | None = None,
) -> dict[str, object]:
    observed = (now or datetime.now(UTC)).astimezone(UTC)

    counts = status_snapshot.get("counts") or {}
    if not isinstance(counts, dict):
        counts = {}
    s0_ok = (
        db_quick_check == "ok"
        and status_snapshot.get("canonical_node") == "bangkok"
        and all(int(counts.get(key, 0) or 0) >= 0 for key in ("canonical_items", "signals", "scheduler_runs"))
    )
    sensors: dict[str, dict[str, object]] = {
        "S0": _sensor(
            "PASS" if s0_ok else "FAIL",
            "INTEGRITY_OK" if s0_ok else "INTEGRITY_FAILED",
            db_quick_check=db_quick_check,
            canonical_node=status_snapshot.get("canonical_node"),
        )
    }

    acquisition_ok = (
        status_snapshot.get("status") == "PASS"
        and status_snapshot.get("signalforge_health") == "GREEN"
        and int(counts.get("recovery_backlog", 0) or 0) == 0
    )
    sensors["S1"] = _sensor(
        "PASS" if acquisition_ok else "FAIL",
        "ACQUISITION_HEALTHY" if acquisition_ok else "ACQUISITION_DEGRADED",
        signalforge_status=status_snapshot.get("status"),
        signalforge_health=status_snapshot.get("signalforge_health"),
        recovery_backlog=int(counts.get("recovery_backlog", 0) or 0),
    )

    assurance_counts = assurance.get("counts") or {}
    if not isinstance(assurance_counts, dict):
        assurance_counts = {}
    coverage_rows = assurance.get("coverage") or []
    if not isinstance(coverage_rows, list):
        coverage_rows = []
    coverage_rows_by_source = {
        str(row.get("source_id")): row
        for row in coverage_rows
        if isinstance(row, dict) and row.get("source_id")
    }
    coverage_by_source = {
        source_id: str(row.get("status") or "NOT_RUN")
        for source_id, row in coverage_rows_by_source.items()
    }
    mandatory_coverage_recovered = [
        {"source_id": source_id, "status": coverage_by_source.get(source_id, "NOT_RUN")}
        for source_id in MANDATORY_COVERAGE_SOURCES
        if coverage_has_reviewed_external_recovery(coverage_rows_by_source.get(source_id) or {})
    ]
    recovered_source_ids = {str(row["source_id"]) for row in mandatory_coverage_recovered}
    mandatory_coverage_gaps = [
        {"source_id": source_id, "status": coverage_by_source.get(source_id, "NOT_RUN")}
        for source_id in MANDATORY_COVERAGE_SOURCES
        if coverage_by_source.get(source_id, "NOT_RUN") in {"GAP", "PARTIAL", "UNPROVEN"}
        and source_id not in recovered_source_ids
    ]
    mandatory_coverage_unknown = [
        {"source_id": source_id, "status": coverage_by_source.get(source_id, "NOT_RUN")}
        for source_id in MANDATORY_COVERAGE_SOURCES
        if coverage_by_source.get(source_id, "NOT_RUN") in {"CHECK_FAILED", "NOT_RUN"}
    ]
    briefing_assurance = briefing.get("assurance") or {}
    if not isinstance(briefing_assurance, dict):
        briefing_assurance = {}
    items = _business_items(briefing)
    missing_scope = [
        str(item.get("canonical_key") or "")
        for item in items
        if not str(item.get("scope_excerpt") or "").strip()
    ]
    low_quality = [
        str(item.get("canonical_key") or "")
        for item in items
        if str(item.get("signal_quality_band") or "").upper() == "LOW"
    ]
    open_red_misses = int(assurance_counts.get("open_red_misses", 0) or 0)
    metric_validity = str(briefing_assurance.get("metric_validity") or "NOT_RUN")
    output_quality_gap = (
        open_red_misses > 0
        or bool(missing_scope)
        or bool(low_quality)
        or metric_validity == "RED"
        or bool(mandatory_coverage_gaps)
    )
    if output_quality_gap:
        s2_status = "FAIL"
        s2_reason = "BUSINESS_OUTPUT_QUALITY_GAP"
    elif mandatory_coverage_unknown:
        s2_status = "UNKNOWN"
        s2_reason = "BUSINESS_COVERAGE_UNVERIFIED"
    elif mandatory_coverage_recovered:
        s2_status = "UNKNOWN"
        s2_reason = "BUSINESS_COVERAGE_RECOVERED_BUT_DIRECT_DISCOVERY_PARTIAL"
    else:
        s2_status = "PASS"
        s2_reason = "BUSINESS_OUTPUT_QUALITY_OK"
    sensors["S2"] = _sensor(
        s2_status,
        s2_reason,
        current_business_items=len(items),
        missing_scope_keys=missing_scope,
        low_quality_keys=low_quality,
        open_red_misses=open_red_misses,
        metric_validity=metric_validity,
        mandatory_coverage_gaps=mandatory_coverage_gaps,
        mandatory_coverage_unknown=mandatory_coverage_unknown,
        mandatory_coverage_recovered=mandatory_coverage_recovered,
    )

    pending = telegram_dry_run.get("pending") or []
    if not isinstance(pending, list):
        pending = []
    malformed_pending = [
        str(item.get("canonical_key") or item.get("promotion_id") or "")
        for item in pending
        if isinstance(item, dict) and not str(item.get("message") or "").strip()
    ]
    pending_count = int(telegram_dry_run.get("pending_count", 0) or 0)
    delivery_ok = telegram_dry_run.get("status") == "PASS" and pending_count == 0 and not malformed_pending
    sensors["S3"] = _sensor(
        "PASS" if delivery_ok else "FAIL",
        "TELEGRAM_OUTCOME_CLOSED" if delivery_ok else "TELEGRAM_OUTCOME_PENDING",
        telegram_status=telegram_dry_run.get("status"),
        pending_count=pending_count,
        malformed_pending_keys=malformed_pending,
    )

    done = all(sensors[sensor_id]["status"] == "PASS" for sensor_id in DONE_SENSOR_IDS)
    return {
        "harness_version": HARNESS_VERSION,
        "goal": GOAL_ID,
        "observed_at": observed.isoformat().replace("+00:00", "Z"),
        "definition_of_done": {
            "passed": done,
            "required_sensors": list(DONE_SENSOR_IDS),
            "rule": "S0 integrity + S1 acquisition + S2 business quality + S3 Telegram outcome",
        },
        "sensors": sensors,
    }


def _failure_signature(report: dict[str, object]) -> str | None:
    dod = report.get("definition_of_done") or {}
    if isinstance(dod, dict) and dod.get("passed") is True:
        return None
    sensors = report.get("sensors") or {}
    failures: list[str] = []
    if isinstance(sensors, dict):
        for sensor_id in DONE_SENSOR_IDS:
            sensor = sensors.get(sensor_id)
            if isinstance(sensor, dict) and sensor.get("status") != "PASS":
                failures.append(f"{sensor_id}:{sensor.get('reason_code')}")
    material = "|".join(failures) or "UNKNOWN_FAILURE"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _load_checkpoint(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def persist_checkpoint(
    report: dict[str, object],
    *,
    path: Path,
    max_retries: int = DEFAULT_MAX_RETRIES,
    advance_retry: bool = True,
) -> dict[str, object]:
    if max_retries < 1:
        raise ValueError("max_retries must be >= 1")

    previous = _load_checkpoint(path)
    signature = _failure_signature(report)
    done = signature is None

    previous_retry = previous.get("retry") if isinstance(previous, dict) else None
    if not isinstance(previous_retry, dict):
        previous_retry = {}
    previous_signature = previous_retry.get("failure_signature")
    previous_attempt = int(previous_retry.get("attempt", 0) or 0)

    if done:
        attempt = 0
    elif not advance_retry:
        attempt = previous_attempt if previous_signature == signature else 0
    elif previous_signature == signature:
        attempt = min(max_retries, previous_attempt + 1)
    else:
        attempt = 1

    escalated = not done and attempt >= max_retries
    if done:
        phase = "DONE"
        next_action = "close_or_continue_observation"
    elif escalated:
        phase = "ESCALATE"
        next_action = "reinspect_assumptions_or_operator_review"
    else:
        phase = "VERIFY"
        sensor_rows = report.get("sensors") or {}
        failed_ids = [
            sensor_id
            for sensor_id in DONE_SENSOR_IDS
            if isinstance(sensor_rows, dict)
            and isinstance(sensor_rows.get(sensor_id), dict)
            and sensor_rows[sensor_id].get("status") != "PASS"
        ]
        mapping = {
            "S0": "fix_integrity",
            "S1": "diagnose_acquisition_health",
            "S2": "fix_extraction_or_business_quality",
            "S3": "close_telegram_delivery",
        }
        next_action = mapping.get(failed_ids[0], "diagnose_failure") if failed_ids else "diagnose_failure"

    checkpoint = {
        **report,
        "phase": phase,
        "retry": {
            "attempt": attempt,
            "max": max_retries,
            "failure_signature": signature,
            "advance_retry": advance_retry,
        },
        "next_action": next_action,
        "checkpoint_path": str(path),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(checkpoint, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return checkpoint
