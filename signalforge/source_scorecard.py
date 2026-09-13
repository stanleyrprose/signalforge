from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from .auditor import audit
from .config import Registry, db_path
from .db import connect
from .opportunities import current_opportunities

SCORECARD_VERSION = 2
DEFAULT_WINDOW_DAYS = 30

# Provisional portfolio tiers frozen by the 2026-09-10 business-yield audit.
# They are analytical labels only and MUST NOT mutate runtime role/priority/polling.
PORTFOLIO_TIERS: dict[str, str] = {
    **{sid: "CORE" for sid in ("S13", "S20", "S21", "S30", "S38", "S39")},
    **{sid: "STRATEGIC_WATCH" for sid in ("S16", "S22", "S27", "S34", "S35", "S41", "S43", "S44", "S45")},
    **{sid: "CONTEXT" for sid in ("S05A", "S07", "S08A", "S10", "S12", "S26")},
    **{sid: "OBSERVATION" for sid in ("S25", "S28", "S29", "S31", "S32", "S33", "S36", "S37", "S40")},
}

# Historical business-accounting exclusions only. They do not delete signals and
# do not alter delivery. S25's two audited batches were normalization-only
# UPDATED noise; the S13 id is the audited parser-only historical UPDATED row.
S13_PARSER_ONLY_SIGNAL_ID = "67f9c7a2-b930-439c-84cc-d05cdecbe695"
S25_NOISE_TIMESTAMPS = {
    "2026-09-08T11:00:17.140857Z",
    "2026-09-08T12:05:15.676253Z",
}


def _parse_iso(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _is_known_historical_noise(row: object) -> bool:
    source_id = str(row["source_id"])
    signal_id = str(row["signal_id"])
    if signal_id == S13_PARSER_ONLY_SIGNAL_ID:
        return True
    return (
        source_id == "S25"
        and str(row["signal_type"]) == "UPDATED"
        and str(row["created_at"]) in S25_NOISE_TIMESTAMPS
    )


def _yield_state(*, current_opportunities: int, telegram_alerts: int, effective_signals: int, raw_signals: int, canonical: int) -> str:
    if current_opportunities > 0 or telegram_alerts > 0:
        return "ACTIONABLE_PROVEN"
    if effective_signals > 0:
        return "SIGNAL_PROVEN"
    if raw_signals > 0:
        return "NOISE_ONLY_HISTORY"
    if canonical > 0:
        return "BASELINE_ONLY"
    return "EMPTY"


def _recommendation(*, portfolio_tier: str, yield_state: str, observation_days: float) -> str:
    if yield_state == "ACTIONABLE_PROVEN":
        return "KEEP_PROVEN"
    if portfolio_tier in {"CORE", "STRATEGIC_WATCH"}:
        return "KEEP_STRATEGIC"
    if observation_days < 30:
        return "OBSERVE_TO_30D"
    if yield_state in {"SIGNAL_PROVEN", "BASELINE_ONLY"}:
        return "KEEP_OBSERVE"
    return "REAUDIT_BEFORE_PRUNING"


def source_scorecard(
    *,
    database: Path | None = None,
    now: datetime | None = None,
    registry: Registry | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict[str, object]:
    if window_days <= 0 or window_days > 365:
        raise ValueError("window_days must be between 1 and 365")
    target = database or db_path()
    now = (now or datetime.now(UTC)).astimezone(UTC)
    cutoff = now - timedelta(days=window_days)
    cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")
    registry = registry or Registry.load()

    opportunities_result = current_opportunities(database=target, now=now, registry=registry, limit=500)
    opportunity_rows = opportunities_result.get("opportunities") or []
    assert isinstance(opportunity_rows, list)
    opportunity_by_source: dict[str, list[dict[str, object]]] = {}
    for item in opportunity_rows:
        if not isinstance(item, dict):
            continue
        opportunity_by_source.setdefault(str(item.get("source_id") or ""), []).append(item)

    audit_result = audit(database=target, registry=registry, now=now, network=False)
    checks = audit_result.get("checks") or {}
    source_health = checks.get("source_health") if isinstance(checks, dict) else {}
    health_rows = source_health.get("sources") if isinstance(source_health, dict) else []
    health_by_source = {
        str(item.get("source_id")): item
        for item in (health_rows or [])
        if isinstance(item, dict) and item.get("source_id")
    }

    with connect(target) as conn:
        canonical_rows = {
            str(row["source_id"]): row
            for row in conn.execute(
                """
                SELECT source_id,COUNT(*) AS n,MAX(publication_date) AS latest_publication,MAX(updated_at) AS latest_update
                FROM canonical_items GROUP BY source_id
                """
            )
        }
        signal_rows = list(conn.execute("SELECT signal_id,source_id,signal_type,created_at FROM signals"))
        signal_by_source: dict[str, dict[str, int]] = {}
        latest_signal: dict[str, str] = {}
        for row in signal_rows:
            sid = str(row["source_id"])
            bucket = signal_by_source.setdefault(sid, {"raw_total": 0, "effective_total": 0, "known_noise_total": 0, "raw_window": 0, "known_noise_window": 0, "effective_window": 0})
            bucket["raw_total"] += 1
            created_at = str(row["created_at"])
            if created_at > str(latest_signal.get(sid) or ""):
                latest_signal[sid] = created_at
            in_window = created_at >= cutoff_iso
            if in_window:
                bucket["raw_window"] += 1
            if _is_known_historical_noise(row):
                bucket["known_noise_total"] += 1
                if in_window:
                    bucket["known_noise_window"] += 1
                continue
            bucket["effective_total"] += 1
            if in_window:
                bucket["effective_window"] += 1

        delivery_rows = {
            str(row["source_id"]): row
            for row in conn.execute(
                """
                SELECT s.source_id,COUNT(*) AS n,MAX(d.sent_at) AS latest_sent
                FROM delivery_receipts d JOIN signals s ON s.signal_id=d.signal_id
                WHERE d.channel='telegram'
                GROUP BY s.source_id
                """
            )
        }
        run_rows = {
            str(row["source_id"]): row
            for row in conn.execute(
                """
                SELECT source_id,MIN(started_at) AS first_run,MAX(started_at) AS last_run,
                       COUNT(*) AS run_count,SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END) AS success_runs,
                       SUM(CASE WHEN changed>0 THEN 1 ELSE 0 END) AS changed_runs
                FROM scheduler_runs GROUP BY source_id
                """
            )
        }
        database_totals = {
            "canonical_items": int(conn.execute("SELECT COUNT(*) FROM canonical_items").fetchone()[0]),
            "signals": int(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]),
        }

    rows: list[dict[str, object]] = []
    sources_raw = registry.raw.get("sources") or {}
    for source_id, policy in registry.enabled_sources():
        policy = sources_raw.get(source_id) if isinstance(sources_raw, dict) else policy
        policy = policy if isinstance(policy, dict) else {}
        canon = canonical_rows.get(source_id)
        sig = signal_by_source.get(source_id, {"raw_total": 0, "effective_total": 0, "known_noise_total": 0, "raw_window": 0, "known_noise_window": 0, "effective_window": 0})
        delivery = delivery_rows.get(source_id)
        run = run_rows.get(source_id)
        opps = opportunity_by_source.get(source_id, [])
        priority_counts = {band: sum(1 for item in opps if item.get("priority_band") == band) for band in ("HIGH", "MEDIUM", "REVIEW", "LOW")}
        strategic_opportunities = sum(
            1
            for item in opps
            if {str(v) for v in (item.get("relevance_categories") or [])} & {"ICT", "TELECOM"}
        )
        first_run = _parse_iso(run["first_run"] if run is not None else None)
        observation_days = max(0.0, (now - first_run).total_seconds() / 86400.0) if first_run else 0.0
        canonical_count = int(canon["n"] if canon is not None else 0)
        tg_count = int(delivery["n"] if delivery is not None else 0)
        portfolio_tier = PORTFOLIO_TIERS.get(source_id, "UNCLASSIFIED")
        yield_state = _yield_state(
            current_opportunities=len(opps),
            telegram_alerts=tg_count,
            effective_signals=int(sig["effective_total"]),
            raw_signals=int(sig["raw_total"]),
            canonical=canonical_count,
        )
        health = health_by_source.get(source_id) or {}
        rows.append(
            {
                "source_id": source_id,
                "name": policy.get("name"),
                "registry_role": policy.get("role"),
                "priority": policy.get("priority"),
                "poll_interval_seconds": policy.get("poll_interval_seconds"),
                "portfolio_tier": portfolio_tier,
                "observed_yield": yield_state,
                "recommendation": _recommendation(portfolio_tier=portfolio_tier, yield_state=yield_state, observation_days=observation_days),
                "health": health.get("source_health"),
                "observation_days": round(observation_days, 2),
                "first_observed_at": run["first_run"] if run is not None else None,
                "last_run_at": run["last_run"] if run is not None else None,
                "run_count": int(run["run_count"] if run is not None else 0),
                "success_runs": int(run["success_runs"] if run is not None else 0),
                "changed_runs": int(run["changed_runs"] if run is not None else 0),
                "canonical_count": canonical_count,
                "latest_publication": canon["latest_publication"] if canon is not None else None,
                "latest_canonical_update": canon["latest_update"] if canon is not None else None,
                "raw_signals_total": int(sig["raw_total"]),
                "known_noise_signals": int(sig["known_noise_total"]),
                "raw_signals_window": int(sig["raw_window"]),
                "known_noise_signals_window": int(sig["known_noise_window"]),
                "effective_signals_total": int(sig["effective_total"]),
                "effective_signals_window": int(sig["effective_window"]),
                "latest_signal_at": latest_signal.get(source_id),
                "current_opportunities": len(opps),
                "current_priority_counts": priority_counts,
                "current_ict_telecom_opportunities": strategic_opportunities,
                "telegram_alerts_total": tg_count,
                "latest_telegram_at": delivery["latest_sent"] if delivery is not None else None,
            }
        )

    tier_rank = {"CORE": 0, "STRATEGIC_WATCH": 1, "CONTEXT": 2, "OBSERVATION": 3, "UNCLASSIFIED": 4}
    yield_rank = {"ACTIONABLE_PROVEN": 0, "SIGNAL_PROVEN": 1, "BASELINE_ONLY": 2, "NOISE_ONLY_HISTORY": 3, "EMPTY": 4}
    rows.sort(
        key=lambda item: (
            yield_rank.get(str(item["observed_yield"]), 9),
            -int(item["current_opportunities"]),
            -int(item["telegram_alerts_total"]),
            -int(item["effective_signals_total"]),
            tier_rank.get(str(item["portfolio_tier"]), 9),
            -int(item.get("priority") or 0),
            str(item["source_id"]),
        )
    )

    active_canonical = sum(int(row["canonical_count"]) for row in rows)
    active_raw_signals = sum(int(row["raw_signals_total"]) for row in rows)
    summary = {
        "active_sources": len(rows),
        "health_green": sum(1 for row in rows if row["health"] == "GREEN"),
        "active_source_canonical_items": active_canonical,
        "database_canonical_items": database_totals["canonical_items"],
        "non_active_canonical_items": database_totals["canonical_items"] - active_canonical,
        "raw_signals": active_raw_signals,
        "database_signals": database_totals["signals"],
        "non_active_signals": database_totals["signals"] - active_raw_signals,
        "known_noise_signals": sum(int(row["known_noise_signals"]) for row in rows),
        "effective_signals": sum(int(row["effective_signals_total"]) for row in rows),
        "current_opportunities": sum(int(row["current_opportunities"]) for row in rows),
        "current_ict_telecom_opportunities": sum(int(row["current_ict_telecom_opportunities"]) for row in rows),
        "telegram_alerts": sum(int(row["telegram_alerts_total"]) for row in rows),
        "yield_states": {
            state: sum(1 for row in rows if row["observed_yield"] == state)
            for state in ("ACTIONABLE_PROVEN", "SIGNAL_PROVEN", "BASELINE_ONLY", "NOISE_ONLY_HISTORY", "EMPTY")
        },
        "portfolio_tiers": {
            tier: sum(1 for row in rows if row["portfolio_tier"] == tier)
            for tier in ("CORE", "STRATEGIC_WATCH", "CONTEXT", "OBSERVATION", "UNCLASSIFIED")
        },
    }
    return {
        "status": "PASS",
        "scorecard_version": SCORECARD_VERSION,
        "as_of": now.isoformat().replace("+00:00", "Z"),
        "window_days": window_days,
        "pruning_gate_days": 30,
        "summary": summary,
        "sources": rows,
        "policy": {
            "portfolio_tier_is_analytical_only": True,
            "observed_yield_is_not_strategic_value": True,
            "known_historical_noise_is_accounting_only": True,
            "no_runtime_role_priority_polling_changes": True,
            "pruning_before_30d_requires_concrete_failure_or_noise_evidence": True,
        },
    }
