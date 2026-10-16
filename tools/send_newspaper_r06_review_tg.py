#!/usr/bin/env python3
"""Dispatch user-requested R06 all-news reading edition QA via Bangkok SignalForge TG.

Two documents + one explanation, no production tender publishing.
Idempotent receipt file is separate from SignalForge business delivery.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from send_newspaper_acceptance_tg import _credentials
from send_newspaper_news_review_tg import _send_document, _send_text

ROOT = Path("/srv/signalforge/tmp/manual-newspaper-r06-20261016")
RECEIPTS = Path("/srv/signalforge/state/manual-newspaper-r06-20261016-receipts.json")
DOCS = (
    ("R06.edition", "R06-Complete-Chinese-News-Review.pdf",
     "R06《缅甸之光》全量中文新闻编辑版【待人工验收】— 32页原报，115条独立报道，关联续文保留"),
    ("R06.ledger", "R06-Disposition-Ledger.pdf",
     "R06 每条候选最终去向审计 — 121条逐条对应中文ID、合并或待核原因"),
)


def _save(state: dict[str, int]) -> None:
    draft = RECEIPTS.with_suffix(".tmp")
    draft.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    draft.chmod(0o600)
    os.replace(draft, RECEIPTS)


def main() -> None:
    token, chat = _credentials()
    state = json.loads(RECEIPTS.read_text(encoding="utf-8")) if RECEIPTS.exists() else {}
    for identifier, filename, caption in DOCS:
        path = ROOT / filename
        if not path.is_file():
            raise RuntimeError("Missing approved R06 review attachment: " + filename)
        if identifier not in state:
            state[identifier] = _send_document(token, chat, path, caption)
            _save(state)
    if "R06.instructions" not in state:
        message = (
            "🧪 R06《缅甸之光》重新验收（SignalForge Bot／非正式招标Signal）\n"
            "R05 FAIL 已复盘：R05 Coverage Audit 的121条原始新闻候选只手工选20条进入Key News PDF，属于生成规则错误。\n"
            "现在交付：\n"
            "① R06完整中文新闻审核PDF：32页官方原报已扫描，115条独立新闻和重要事项，按类别重新排版，含全部可保留内容而非Top20。\n"
            "② R06候选审计PDF：121个候选ID逐条对应收录文章、合并对象或审核理由。\n"
            "核算：115条独立收录，5条同事件续文合并且保留原文摘要，1条残缺短讯单独待核。\n"
            "重要：82条仍有OCR/专有名词等问题需要人工核验；另有一条源证据校验失败。"
            "这仍是机器初译，不是最终审核完成的正式中文版。"
            "燃油汇率数字、招标截止、职务人名以官方原版为准。\n\n"
            "请先检查：Coverage中提到的缅印合作、供水扩建、食品安全、农牧生产、救灾、招聘等内容"
            "是否已在新版中文新闻PDF；再回复本ChatGPT会话 R06 PASS 或 R06 REVISE。"
            "Telegram的回复目前不会自动同步到此会话。"
        )
        state["R06.instructions"] = _send_text(token, chat, message)
        _save(state)
    print(json.dumps({"status":"SENT","provider":"Bangkok SignalForge TG",
                      "receipts":state},ensure_ascii=False))


if __name__ == "__main__":
    main()
