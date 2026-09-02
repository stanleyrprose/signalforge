from __future__ import annotations

import argparse
import json
import sys

from .config import Registry, db_path
from .db import connect, migrate
from .engine import run_due, run_source


def status() -> dict[str, object]:
    database = db_path()
    migrate(database)
    registry = Registry.load()
    with connect(database) as conn:
        sources = [dict(row) for row in conn.execute("SELECT * FROM source_state ORDER BY source_id")]
        counts = {
            "canonical_items": int(conn.execute("SELECT COUNT(*) FROM canonical_items").fetchone()[0]),
            "signals": int(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]),
            "scheduler_runs": int(conn.execute("SELECT COUNT(*) FROM scheduler_runs").fetchone()[0]),
            "failed_runs": int(conn.execute("SELECT COUNT(*) FROM scheduler_runs WHERE status='FAILED'").fetchone()[0]),
        }
        recent = [
            dict(row)
            for row in conn.execute(
                "SELECT app_run_id,source_id,worker_run_id,started_at,finished_at,status,changed,signals_created,baseline,error "
                "FROM scheduler_runs ORDER BY started_at DESC LIMIT 10"
            )
        ]
    source_warnings = sum(1 for source in sources if source.get("last_error"))
    return {
        "status": "DEGRADED" if source_warnings else "PASS",
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
