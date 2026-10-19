"""Read-only delivery evidence, independent of Public Read route telemetry.

Usage:
    python tools/delivery_health_readonly.py --tender-db /path/to/signalforge.db \
        --news-ledger /path/to/s01-ledger.db

No Telegram messages, writes, scheduling or provider calls occur.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _read(path: Path):
    if not path.is_file():
        return None
    return sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)


def tender_health(path: Path, since: str) -> dict:
    conn = _read(path)
    if conn is None:
        return {"status": "UNKNOWN", "reason": "tender database unavailable"}
    try:
        recent = conn.execute(
            "SELECT status, COUNT(*) FROM scheduler_runs WHERE started_at >= ? GROUP BY status",
            (since,),
        ).fetchall()
        delivered = conn.execute(
            "SELECT COUNT(*) FROM delivery_receipts WHERE sent_at >= ? AND "
            "provider_message_id IS NOT NULL AND provider_message_id != ''", (since,),
        ).fetchone()[0]
        states = dict(recent)
        if not recent:
            status = "UNKNOWN"
            reason = "no recent source scheduler evidence"
        elif any(str(k).upper() in ("FAILED", "ERROR") for k in states):
            status = "WARN"
            reason = "source scheduler failures; inspect daily-cycle and delivery"
        else:
            status = "WARN"
            reason = "source attempts observed; daily-cycle completion and zero-send rationale not confirmed"
        return {"status": status, "reason": reason, "source_run_states": states,
                "telegram_receipts": delivered,
                "delivery_verdict": "UNKNOWN" if delivered == 0 else "RECEIPTS_OBSERVED"}
    except sqlite3.DatabaseError as exc:
        return {"status": "UNKNOWN", "reason": f"tender evidence unavailable: {type(exc).__name__}"}
    finally:
        conn.close()


def news_health(path: Path, since: str) -> dict:
    conn = _read(path)
    if conn is None:
        return {"status": "UNKNOWN", "reason": "S01 ledger unavailable"}
    try:
        rows = conn.execute(
            "SELECT edition_id, part, status, message_id, updated_at "
            "FROM deliveries WHERE updated_at >= ? ORDER BY updated_at DESC", (since,)
        ).fetchall()
        editions: dict[str, dict] = {}
        for edition, part, state, message_id, updated_at in rows:
            editions.setdefault(edition, {})[part] = {
                "status": state, "message_id": message_id, "updated_at": updated_at
            }
        complete = [
            key for key, parts in editions.items()
            if all(parts.get(part, {}).get("status") == "SUCCESS"
                   and isinstance(parts[part].get("message_id"), int)
                   and parts[part]["message_id"] > 0 for part in ("pdf", "digest"))
        ]
        invalid = any(
            receipt["status"] in ("FAILED", "UNKNOWN", "PENDING")
            for parts in editions.values() for receipt in parts.values()
        )
        return {
            "status": "WARN" if invalid else ("PASS" if complete else "UNKNOWN"),
            "reason": ("unresolved/failed delivery receipt" if invalid else
                       "both S01 PDF and Digest receipts observed" if complete else
                       "no complete recent S01 PDF/Digest receipt pair"),
            "complete_editions": len(complete), "recent_editions": len(editions),
            "note": "S01 receipts only; source coverage, scheduler and other newspapers not assessed",
        }
    except sqlite3.DatabaseError as exc:
        return {"status": "UNKNOWN", "reason": f"news evidence unavailable: {type(exc).__name__}"}
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tender-db", type=Path, required=True)
    parser.add_argument("--news-ledger", type=Path, required=True)
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()
    if not 1 <= args.hours <= 168:
        parser.error("--hours must be 1..168")
    since = (datetime.now(timezone.utc) - timedelta(hours=args.hours)).isoformat()
    print(json.dumps({
        "since": since,
        "tender": tender_health(args.tender_db, since),
        "news_s01": news_health(args.news_ledger, since),
        "provider_route_telemetry": "NOT_ASSESSED_SEPARATELY",
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
