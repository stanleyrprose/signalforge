"""Daily acquisition barrier, durable progress and Chinese Telegram coverage report.

The scheduler invokes this once per day. Re-entry never reruns acquisition after
its checkpoint was committed; tender receipts handle per-item retry separately.
"""
from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .engine import run_due
from .telegram_delivery import _send_message, telegram_deliver

YANGON = ZoneInfo("Asia/Yangon")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Atomic checkpoint within the state filesystem."""
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def _coverage_report(day: str, acquisition: dict[str, object], delivery: dict[str, object]) -> str:
    results = acquisition.get("results") or []
    if not isinstance(results, list):
        raise ValueError("daily acquisition results must be a list")
    failed = [r for r in results if isinstance(r, dict) and r.get("status") == "FAILED"]
    succeeded = [r for r in results if isinstance(r, dict) and r.get("status") != "FAILED"]
    lines = [
        f"📋 SignalForge 政府/国企招标日报 · {day}（仰光）",
        f"采集覆盖：{len(results)} 源；完成 {len(succeeded)}；失败 {len(failed)}。",
        f"有效招标通知：{delivery.get('sent_count', 0)} 条；"
        f"质量过滤：{delivery.get('quality_filtered_count', 0)} 条。",
    ]
    if failed:
        lines.append("⚠️ 未成功采集来源：")
        for item in failed[:28]:
            source_id = str(item.get("source_id") or "?")
            error = str(item.get("error") or "采集失败").replace("\n", " ")
            lines.append(f"• {source_id}: {error[:100]}")
    else:
        lines.append("所有来源本次采集流程均已结束；不代表所有来源都有有效招标。")
    lines.append("说明：无新增有效招标不等于未采集；具体物项、数量、截止日期以独立通知为准。")
    return "\n".join(lines)


def daily_cycle() -> dict[str, object]:
    """Complete source acquisition before any delivery; checkpoint each phase.

    The completion marker suppresses repeat daily reports. Telegram cannot
    guarantee exactly-once transmission if the process dies after API success
    but before local receipt persistence; the underlying tender delivery
    receipts provide at-least-once semantics.
    """
    state_root = Path(os.environ.get("SIGNALFORGE_STATE_ROOT", "/srv/signalforge/state"))
    state_root.mkdir(parents=True, exist_ok=True)
    day = datetime.now(YANGON).date().isoformat()
    prefix = f"daily-cycle-{day}"
    acquisition_path = state_root / f"{prefix}-acquisition.json"
    delivery_path = state_root / f"{prefix}-delivery.json"
    report_path = state_root / f"{prefix}-report.json"
    complete_path = state_root / f"{prefix}-complete.json"
    with (state_root / "daily-cycle.lock").open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if complete_path.exists():
            return {"status": "ALREADY_COMPLETE", "day": day}
        if acquisition_path.exists():
            acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
        else:
            try:
                acquisition = run_due()
                if not isinstance(acquisition, dict) or not isinstance(acquisition.get("results"), list):
                    raise ValueError("run_due returned incomplete source results")
            except Exception as exc:
                return {"status": "ACQUISITION_ABORTED", "day": day,
                        "error": f"{type(exc).__name__}: {exc}"[:300]}
            _write_json(acquisition_path, acquisition)
        if delivery_path.exists():
            delivery = json.loads(delivery_path.read_text(encoding="utf-8"))
        else:
            try:
                delivery = telegram_deliver()
                if not isinstance(delivery, dict) or delivery.get("status") != "PASS" or delivery.get("dry_run"):
                    raise ValueError("Telegram delivery did not complete successfully")
            except Exception as exc:
                return {"status": "DELIVERY_FAILED", "day": day,
                        "error": f"{type(exc).__name__}: {exc}"[:300]}
            _write_json(delivery_path, delivery)
        if not report_path.exists():
            token = os.environ.get("SIGNALFORGE_TELEGRAM_BOT_TOKEN", "")
            chat = os.environ.get("SIGNALFORGE_TELEGRAM_CHAT_ID", "")
            if not token or not chat:
                return {"status": "REPORT_FAILED", "day": day, "error": "Telegram credentials unavailable"}
            try:
                message_id = _send_message(
                    bot_token=token, chat_id=chat,
                    text=_coverage_report(day, acquisition, delivery),
                )
            except Exception as exc:
                return {"status": "REPORT_FAILED", "day": day,
                        "error": f"{type(exc).__name__}: {exc}"[:300]}
            _write_json(report_path, {"message_id": message_id, "day": day})
        failures = [r for r in acquisition["results"]
                    if isinstance(r, dict) and r.get("status") == "FAILED"]
        outcome = {
            "status": "COMPLETE_WITH_SOURCE_FAILURES" if failures else "COMPLETE",
            "day": day, "source_count": len(acquisition["results"]),
            "failed_source_count": len(failures),
            "sent_count": delivery.get("sent_count", 0),
        }
        _write_json(complete_path, outcome)
        return outcome
