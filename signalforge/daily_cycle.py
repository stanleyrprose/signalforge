"""Daily acquisition barrier, durable progress and Chinese Telegram coverage report.

The scheduler invokes this once per day. Re-entry never reruns acquisition after
its checkpoint was committed; tender receipts handle per-item retry separately.
"""
from __future__ import annotations

import fcntl
import hashlib
import html
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .engine import run_due
from .config import db_path
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


def _report_parts(text: str, limit: int = 3800) -> list[str]:
    """Plain report text is escaped for the HTML transport and UTF-16 bounded."""
    parts, chunk = [], ""
    for char in text:
        safe = html.escape(char, quote=False)
        if len((chunk + safe).encode("utf-16-le")) // 2 > limit:
            parts.append(chunk)
            chunk = ""
        chunk += safe
    if chunk:
        parts.append(chunk)
    return parts


def _send_report(path: Path, day: str, text: str, token: str, chat: str) -> dict:
    parts = _report_parts(text)
    fingerprint = hashlib.sha256(text.encode()).hexdigest()
    progress_path = path.with_name(path.stem + "-parts.json")
    state = json.loads(progress_path.read_text()) if progress_path.exists() else {
        "fingerprint": fingerprint, "parts": {}}
    if state["fingerprint"] != fingerprint:
        raise ValueError("Daily report changed after a send attempt; reconcile first")
    for i, part in enumerate(parts):
        key = str(i)
        previous = state["parts"].get(key, {})
        if previous.get("status") == "SUCCESS":
            continue
        if previous.get("status") in ("PENDING", "UNKNOWN"):
            raise RuntimeError("Daily report outcome unknown; reconcile before resend")
        state["parts"][key] = {"status": "PENDING"}
        _write_json(progress_path, state)
        try:
            message_id = _send_message(bot_token=token, chat_id=chat, text=part)
        except Exception as exc:
            import re
            state["parts"][key] = {"status": "FAILED" if re.search(r"telegram HTTP 4\d\d", str(exc)) else "UNKNOWN"}
            _write_json(progress_path, state)
            raise
        state["parts"][key] = {"status": "SUCCESS", "message_id": message_id}
        _write_json(progress_path, state)
    ids = [state["parts"][str(i)]["message_id"] for i in range(len(parts))]
    result = {"day": day, "message_id": ids[0], "message_ids": ids}
    _write_json(path, result)
    return result


def _coverage_report(day: str, acquisition: dict[str, object], delivery: dict[str, object], image_ocr: dict[str, object] | None = None, attachment_health: dict[str, object] | None = None, s01_verified: dict[str, object] | None = None, s01_intelligence: dict[str, object] | None = None) -> str:
    results = acquisition.get("results") or []
    if not isinstance(results, list):
        raise ValueError("daily acquisition results must be a list")
    failed = [r for r in results if isinstance(r, dict) and r.get("status") == "FAILED"]
    succeeded = [r for r in results if isinstance(r, dict) and r.get("status") == "SUCCESS"]
    not_due = [r for r in results if isinstance(r, dict) and r.get("status") == "NOT_DUE"]
    unknown = [r for r in results if not isinstance(r, dict) or r.get("status") not in {"FAILED", "SUCCESS", "NOT_DUE"}]
    lines = [
        f"📋 SignalForge 政府/国企招标日报 · {day}（仰光）",
        f"调度覆盖：{len(results)} 源；实际采集成功 {len(succeeded)}；失败 {len(failed)}；未到期 {len(not_due)}；其他 {len(unknown)}。",
        f"有效招标通知：{delivery.get('sent_count', 0)} 条；"
        f"质量过滤：{delivery.get('quality_filtered_count', 0)} 条。",
    ]
    # This report is sent every day even when there are no actionable new tenders.
    blocked = int(delivery.get("quality_filtered_count", 0)) + int(delivery.get("failed_count", 0))
    if int(delivery.get("sent_count", 0)) == 0:
        lines.append("⚠️ 本轮没有成功投递的新增招标通知，有待处理项目；不代表来源没有新增。" if blocked else "✅ 今日无新增招标（本轮无新增有效招标通知）。")
    if delivery.get("failed_count"):
        lines.append(f"⚠️ 本轮投递失败 {delivery.get('failed_count', 0)} 条，未写成功回执；其他符合条件的招标已继续处理。")
    if image_ocr is not None:
        lines.append(f"S01 图片 OCR：尝试 {image_ocr.get('attempted', 0)}，成功 {image_ocr.get('completed', 0)}，失败 {image_ocr.get('failed', 0)}；结果仅供审核。")
    if s01_verified is not None:
        reviewed = int(s01_verified.get("reviewed", 0))
        created = int(s01_verified.get("promoted", 0))
        if s01_verified.get("status") == "CHECK_FAILED":
            lines.append("S01 正式招标复核入库检查失败；本轮有效新增数未知。")
        else:
            lines.append(
                f"S01 官方原图复核：已审核 {reviewed} 件；新入库可信招标 {created}；"
                f"缺投标提交截止日 {int(s01_verified.get('blocked_missing_bid_deadline', 0))}；"
                f"非采购 {int(s01_verified.get('excluded_nonprocurement', 0))}。"
            )
    if s01_intelligence is not None:
        lines.append(f"S01 招标关联资讯审核候选：{s01_intelligence.get('candidates', 0)}；S01 全量新闻由独立日报投递。")
    if attachment_health is not None:
        checked = int(attachment_health.get("checked_count", 0))
        broken = int(attachment_health.get("http_404_count", 0))
        if checked:
            lines.append(
                f"S20 \u5b98\u65b9 PDF \u9644\u4ef6\uff1a\u8fd145\u5929\u62bd\u67e5 {checked} \u4efd\uff1bHTTP 404 {broken} \u4efd\u3002\u7f3a\u5931\u7684\u7269\u9879\u3001\u6570\u91cf\u53ca\u6295\u6807\u622a\u6b62\u65e5\u671f\u4e0d\u5f97\u731c\u6d4b\u3002"
            )
        elif attachment_health.get("status") == "CHECK_FAILED":
            lines.append("S20 PDF 附件健康检查失败，附件可用性未知。")
        recovery = attachment_health.get("recovery")
        if isinstance(recovery, dict):
            lines.append(
                f"S20 历史官方附件核验记录：{int(attachment_health.get('reviewed_attachment_evidence_count', 0))} 份；"
                f"其中有独立截止日证据 {int(attachment_health.get('reviewed_submission_deadline_count', 0))} 份。"
            )
            lines.append(
                f"S20 PDF 原件恢复：存档 {int(recovery.get('downloaded_count', 0))} 份，"
                f"原生文本恢复 {int(recovery.get('native_text_count', 0))} 份，"
                f"需扫描/OCR/复核 {int(recovery.get('scan_or_parse_review_count', 0))} 份；"
                "未复核内容不自动补写投标截止日期。"
            )
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
    image_path = state_root / f"{prefix}-image-ocr.json"
    s01_verified_path = state_root / f"{prefix}-s01-verified.json"
    intelligence_path = state_root / f"{prefix}-s01-intelligence.json"
    attachment_path = state_root / f"{prefix}-moep-attachments.json"
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
                # Daily coverage requires a real attempt for every enabled source;
                # the per-source scheduler's NOT_DUE gate would otherwise skip them.
                acquisition = run_due(force=True)
                if not isinstance(acquisition, dict) or not isinstance(acquisition.get("results"), list):
                    raise ValueError("run_due returned incomplete source results")
            except Exception as exc:
                return {"status": "ACQUISITION_ABORTED", "day": day,
                        "error": f"{type(exc).__name__}: {exc}"[:300]}
            _write_json(acquisition_path, acquisition)
        if image_path.exists():
            image_ocr = json.loads(image_path.read_text(encoding="utf-8"))
        else:
            try:
                from .national_portal_tender import process_pending_s01_image_ocr
                image_ocr = process_pending_s01_image_ocr(db_path(), limit=2)
            except Exception as exc:
                image_ocr = {"attempted": 0, "completed": 0, "failed": 1,
                             "error": f"{type(exc).__name__}: {exc}"[:200]}
            _write_json(image_path, image_ocr)
        if s01_verified_path.exists():
            s01_verified = json.loads(s01_verified_path.read_text(encoding="utf-8"))
        else:
            try:
                from .s01_reviewed_tenders import promote_reviewed_s01_images
                s01_verified = promote_reviewed_s01_images(db_path())
            except Exception as exc:
                s01_verified = {"status": "CHECK_FAILED", "error": f"{type(exc).__name__}: {exc}"[:180]}
            _write_json(s01_verified_path, s01_verified)
        if intelligence_path.exists():
            s01_intelligence = json.loads(intelligence_path.read_text(encoding="utf-8"))
        else:
            try:
                from .s01_government_intelligence import refresh_s01_government_intelligence
                s01_intelligence = refresh_s01_government_intelligence(db_path())
            except Exception as exc:
                s01_intelligence = {"status": "CHECK_FAILED", "error": f"{type(exc).__name__}: {exc}"[:180]}
            _write_json(intelligence_path, s01_intelligence)
        prior_delivery = json.loads(delivery_path.read_text(encoding="utf-8")) if delivery_path.exists() else {}
        if prior_delivery.get("status") == "PASS":
            delivery = prior_delivery
        else:
            try:
                delivery = telegram_deliver()
                if not isinstance(delivery, dict) or delivery.get("status") not in ("PASS", "PARTIAL") or delivery.get("dry_run"):
                    raise ValueError("Telegram delivery did not complete successfully")
            except Exception as exc:
                return {"status": "DELIVERY_FAILED", "day": day,
                        "error": f"{type(exc).__name__}: {exc}"[:300]}
            delivery["sent"] = prior_delivery.get("sent", []) + delivery.get("sent", [])
            delivery["sent_count"] = len(delivery["sent"])
            _write_json(delivery_path, delivery)
        if attachment_path.exists():
            attachment_health = json.loads(attachment_path.read_text(encoding="utf-8"))
        else:
            try:
                from .moep_attachment_health import probe_recent_s20_attachments
                attachment_health = probe_recent_s20_attachments(db_path())
                from .moep_attachment_recovery import recover_accessible_s20_pdfs
                attachment_health["recovery"] = recover_accessible_s20_pdfs(
                    db_path(), attachment_health,
                )
            except Exception as exc:
                attachment_health = {"status": "CHECK_FAILED", "error": f"{type(exc).__name__}: {exc}"[:160]}
            _write_json(attachment_path, attachment_health)
        if not report_path.exists():
            token = os.environ.get("SIGNALFORGE_TELEGRAM_BOT_TOKEN", "")
            chat = os.environ.get("SIGNALFORGE_TELEGRAM_CHAT_ID", "")
            if not token or not chat:
                return {"status": "REPORT_FAILED", "day": day, "error": "Telegram credentials unavailable"}
            try:
                _send_report(report_path, day,
                    _coverage_report(day, acquisition, delivery, image_ocr, attachment_health, s01_verified, s01_intelligence),
                    token, chat)
            except Exception as exc:
                return {"status": "REPORT_FAILED", "day": day,
                        "error": f"{type(exc).__name__}: {exc}"[:300]}
        if delivery.get("failed_count"):
            return {"status":"DELIVERY_PARTIAL","day":day,"sent_count":delivery["sent_count"],
                    "failed_count":delivery["failed_count"]}
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
