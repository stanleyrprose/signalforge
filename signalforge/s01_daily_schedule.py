"""Daily S01 due check with durable completion and immutable-manifest recovery."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .s01_daily_runner import _lock, run
from .s01_daily_transfer import transfer

YANGON = ZoneInfo("Asia/Yangon")


def _save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def execute(root: Path, *, now: datetime | None = None) -> dict:
    now = (now or datetime.now(YANGON)).astimezone(YANGON)
    due = (now if now.hour >= 17 else now - timedelta(days=1)).date().isoformat()
    root = root.resolve()
    with _lock(root / ".schedule.lock"):
        folder = root / "daily-schedule"
        pending, invalid = [], []
        for path in sorted(folder.glob("????-??-??.json")):
            try:
                state = json.loads(path.read_text())
                if not isinstance(state, dict) or state.get("date") != path.stem:
                    raise ValueError("journal date/path mismatch")
                if path.stem < due and state["status"] not in ("DELIVERED", "NO_NEW_ARTICLES"):
                    pending.append(path.stem)
            except (OSError, ValueError, KeyError):
                invalid.append(path.name)
        # Current day first; at most one older day per invocation. Both are
        # attempted even if the other fails, without rewriting successful receipts.
        dates = [due] + pending[:1]
        results, errors = [], []
        for day in dates:
            try:
                results.append(_execute_day(root, day, now))
            except Exception as exc:
                errors.append(exc)
                path = folder / (day + ".json")
                try:
                    state = json.loads(path.read_text())
                    if not isinstance(state, dict):
                        continue
                    state.update(last_error_type=type(exc).__name__, last_error_at=now.isoformat())
                    _save(path, state)
                except (OSError, ValueError):
                    pass
        if errors:
            raise errors[0]
        result = results[0]
        if len(results) > 1:
            result = {**result, "historical_recovery": results[1]}
        if invalid:
            result = {**result, "invalid_journals": invalid}
        return result


def _execute_day(root: Path, day: str, now: datetime) -> dict:
    path = root / "daily-schedule" / (day + ".json")
    state = json.loads(path.read_text()) if path.exists() else None
    if state and state["date"] != day:
        raise ValueError("journal date/path mismatch")
    if state and state["status"] in ("DELIVERED", "NO_NEW_ARTICLES"):
        if state["status"] == "DELIVERED":
            state["mac_evidence_cleanup"] = cleanup_evidence(root, day)
            _save(path, state)
        return {"status": "ALREADY_COMPLETED", "date": day}
    if state is None:
        state = {"date": day, "status": "STARTED"}
        _save(path, state)
    outbox = root / "outbox"
    manifests = sorted(outbox.glob("S01-manifest-" + day + "-*.json"))
    if len(manifests) > 1:
        raise RuntimeError("multiple S01 manifests for one day; reconcile before retry")
    if manifests:
        manifest = manifests[0]
        edition = json.loads(manifest.read_text())["edition_id"]
        state.update(status="PREPARED", edition_id=edition)
        _save(path, state)
        result = transfer(manifest, root / "s01-delivery.sqlite", outbox,
                          host="vps-bangkok",
                          remote_inbox="/srv/signalforge/state/s01-news-inbox",
                          remote_ledger="/srv/signalforge/state/s01-news-ledger.sqlite",
                          python="/srv/signalforge/active/.venv/bin/python")
        result = {**result, "status": "DELIVERED"}
    elif state.get("edition_id"):
        # A completed transfer removes its manifest only after receipts and
        # both staging cleanups. Recover a crash before saving this journal.
        with sqlite3.connect(root / "s01-delivery.sqlite") as conn:
            rows = dict(conn.execute(
                "SELECT part,message_id FROM deliveries WHERE edition_id=? AND status='SUCCESS'",
                (state["edition_id"],)).fetchall())
        from .s01_attachment import paired_receipts
        if not paired_receipts(rows):
            raise RuntimeError("missing prepared manifest without confirmed receipts")
        result = {"status": "DELIVERED", "edition_id": state["edition_id"]}
    else:
        # Prepare first, journal identity before any Telegram side effect.
        result = run(root, day=day)
        if result["status"] == "READY_NOT_PUBLISHED":
            state.update(status="PREPARED", edition_id=result["edition_id"])
            _save(path, state)
            return execute_prepared(root, path, state, result["manifest"])
    if result["status"] in ("DELIVERED", "NO_NEW_ARTICLES"):
        if result["status"] == "DELIVERED":
            result["mac_evidence_cleanup"] = cleanup_evidence(root, day)
        state.update(result, date=day, completed_at=now.isoformat())
        _save(path, state)
    return result


def execute_prepared(root: Path, path: Path, state: dict, manifest: str) -> dict:
    result = transfer(Path(manifest), root / "s01-delivery.sqlite", root / "outbox",
                      host="vps-bangkok",
                      remote_inbox="/srv/signalforge/state/s01-news-inbox",
                      remote_ledger="/srv/signalforge/state/s01-news-ledger.sqlite",
                      python="/srv/signalforge/active/.venv/bin/python")
    result["mac_evidence_cleanup"] = cleanup_evidence(root, state["date"])
    state.update(result, status="DELIVERED", completed_at=datetime.now(YANGON).isoformat())
    _save(path, state)
    return state


def cleanup_evidence(root: Path, day: str) -> dict:
    # Cleanup retries require minimum durable receipts, never retained payloads.
    from .s01_content_cleanup import cleanup_day
    journal = root / "daily-schedule" / (day + ".json")
    try:
        state = json.loads(journal.read_text(encoding="utf-8"))
        return cleanup_day(root, day, state["edition_id"])
    except (OSError, ValueError, KeyError) as exc:
        return {"status": "PENDING", "reason": type(exc).__name__}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.root), ensure_ascii=False))


if __name__ == "__main__":
    main()
