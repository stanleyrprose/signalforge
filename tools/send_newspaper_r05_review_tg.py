#!/usr/bin/env python3
"""Bangkok SignalForge Bot: R05 full-issue MAL news coverage acceptance only.

The files are staged locally on Bangkok from the Mac developer machine.
Never writes tender canonical records; no automatic reply-to-chat ingestion.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from send_newspaper_acceptance_tg import _credentials
from send_newspaper_news_review_tg import _send_document, _send_text

ROOT = Path("/srv/signalforge/tmp/manual-newspaper-r05-20261016")
RECEIPTS = Path("/srv/signalforge/state/manual-newspaper-r05-20261016-receipts.json")
DELIVERIES = (
    ("R05.official", "R05-official-32pages.pdf",
     "R05《缅甸之光》2026-10-16 官方原报（32页），仅供核对原文"),
    ("R05.highlights", "R05-Chinese-Key-News-Review.pdf",
     "R05 中文重点新闻与重要信息【人工审核稿】——32页已OCR，精选20个重点候选"),
    ("R05.coverage", "R05-Coverage-Audit.pdf",
     "R05 整期32页逐页覆盖表＋重要主题漏报检查（2页）"),
)


def _save(receipts: dict[str, int]) -> None:
    tmp = RECEIPTS.with_suffix(".tmp")
    tmp.write_text(json.dumps(receipts, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    os.replace(tmp, RECEIPTS)


def main() -> None:
    token, chat = _credentials()
    state = json.loads(RECEIPTS.read_text(encoding="utf-8")) if RECEIPTS.exists() else {}
    for key, name, caption in DELIVERIES:
        path = ROOT / name
        if not path.is_file():
            raise RuntimeError(f"Missing preapproved review PDF: {name}")
        if key not in state:
            state[key] = _send_document(token, chat, path, caption)
            _save(state)
    if "R05.instructions" not in state:
        message = (
            "🧪 SignalForge 人工验收 R05 — 《缅甸之光》重要信息漏报修复\n"
            "日期：2026-10-16；整期32/32页已做OCR和第二轮候选筛查。\n\n"
            "你此前的 R04 FAIL 已确认：只处理2/32页，且误删LOW置信度重要新闻。"
            "本次附官方32页PDF、8页中文重点候选（20项）以及2页覆盖审计。\n"
            "已补回 NCA 11周年讲话及会见、世界粮食日、燃油/汇率/黄金市场表、"
            "政府命令、中小企业立法、文化比赛与官方招标（桥梁监测、天然气管道、纺织设备等）。\n"
            "注意：83个候选仍有低置信度或专名需复核；"
            "数值和期限待核的地方均按【待核】处理，不能当作最终核准公告。\n"
            "已排除商业广告和法律分类广告等无关信息，保留有价值政府采购与公告。"
            "这是修复后的人工审核稿，不是最终中文发行版或正式 Tender Signal。\n\n"
            "请在当前 ChatGPT 会话回复 R05 PASS / R05 REVISE（指出遗漏信息、错误数据或不应保留的内容）。"
            "Telegram 回复尚未自动回传此会话。"
        )
        state["R05.instructions"] = _send_text(token, chat, message)
        _save(state)
    print(json.dumps({"status": "SENT", "target": "Bangkok SignalForge TG",
                      "review_receipts": state}, ensure_ascii=False))


if __name__ == "__main__":
    main()
