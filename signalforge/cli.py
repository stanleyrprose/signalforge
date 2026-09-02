from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime

from .config import Registry, db_path
from .db import connect, migrate
from .engine import run_due, run_source


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def status() -> dict[str, object]:
    database = db_path()
    migrate(database)
    registry = Registry.load()
    now = datetime.now(UTC)
    with connect(database) as conn:
        sources: list[dict[str, object]] = []
        for row in conn.execute("SELECT * FROM source_state ORDER BY source_id"):
            source = dict(row)
            source_id = str(source["source_id"])
            policy = registry.source(source_id)
            pending = conn.execute(
                "SELECT COUNT(*) AS count,MIN(pending_since_at) AS oldest FROM discovery_items WHERE source_id=? AND pending_since_at IS NOT NULL",
                (source_id,),
            ).fetchone()
            backlog = int(pending["count"])
            oldest = pending["oldest"]
            oldest_dt = _parse_iso(oldest)
            oldest_age = max(0, int((now - oldest_dt).total_seconds())) if oldest_dt else 0
            recovery_slo = int(policy.get("recovery_slo_seconds", 1800))
            if backlog == 0:
                recovery_health = "GREEN"
            elif oldest_age <= recovery_slo:
                recovery_health = "YELLOW"
            else:
                recovery_health = "RED"
            failures = int(source.get("consecutive_failures") or 0)
            fetch_health = "RED" if failures >= 3 else "YELLOW" if failures else "GREEN"
            source["health"] = {
                "fetch_health": fetch_health,
                "recovery_backlog_health": recovery_health,
                "recovery_backlog": backlog,
                "recovery_oldest_pending_at": oldest,
                "recovery_oldest_age_seconds": oldest_age,
                "recovery_slo_seconds": recovery_slo,
                "availability_class": (policy.get("availability_policy") or {}).get("class"),
            }
            sources.append(source)

        counts = {
            "canonical_items": int(conn.execute("SELECT COUNT(*) FROM canonical_items").fetchone()[0]),
            "signals": int(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]),
            "scheduler_runs": int(conn.execute("SELECT COUNT(*) FROM scheduler_runs").fetchone()[0]),
            "failed_runs": int(conn.execute("SELECT COUNT(*) FROM scheduler_runs WHERE status='FAILED'").fetchone()[0]),
            "recovery_backlog": int(conn.execute("SELECT COUNT(*) FROM discovery_items WHERE pending_since_at IS NOT NULL").fetchone()[0]),
        }
        recent = [
            dict(row)
            for row in conn.execute(
                "SELECT app_run_id,source_id,worker_run_id,started_at,finished_at,status,changed,signals_created,baseline,"
                "trigger_kind,recovery,outage_window_start,outage_window_end,backlog_remaining,error "
                "FROM scheduler_runs ORDER BY started_at DESC LIMIT 10"
            )
        ]
    degraded = any(
        source.get("last_error")
        or (source.get("health") or {}).get("recovery_backlog_health") in {"YELLOW", "RED"}
        or (source.get("health") or {}).get("fetch_health") in {"YELLOW", "RED"}
        for source in sources
    )
    return {
        "status": "DEGRADED" if degraded else "PASS",
        "canonical_node": registry.raw["production_policy"]["canonical_node"],
        "browser_production_approved": registry.raw["production_policy"]["browser_production_approved"],
        "sources": sources,
        "counts": counts,
        "recent_runs": recent,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="signalforge")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate")
    sub.add_parser("run-due")
    run_source_parser = sub.add_parser("run-source")
    run_source_parser.add_argument("source_id")
    run_source_parser.add_argument("--force", action="store_true")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "migrate":
            migrate()
            result: object = {"status": "PASS"}
        elif args.cmd == "run-due":
            result = run_due()
        elif args.cmd == "run-source":
            result = run_source(args.source_id, force=args.force)
        else:
            result = status()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
