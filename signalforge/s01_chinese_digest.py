"""Evidence-bound AI review reconciliation and Chinese digest rendering.

No model is called here: only complete, validated model outputs may be ingested.
"""
from __future__ import annotations

import json
from pathlib import Path

from .db import connect
from .s01_ai_review import build_review_request, validate_review_result


def pending_review_batches(database: Path, *, model: str, batch_size: int = 10) -> list[dict]:
    if not 1 <= batch_size <= 20:
        raise ValueError("batch_size must be 1-20")
    with connect(database) as conn:
        rows = conn.execute("""SELECT n.url,n.title_hint,d.body_text,d.detail_sha256
            FROM s01_news_review n JOIN s01_news_detail_review d ON d.url=n.url
            WHERE d.body_chars >= 100 ORDER BY n.url""").fetchall()
    items = [{"url": url, "title_hint": title, "body_text": body[:12000],
              "detail_sha256": sha, "evidence_status": "DETAIL_EXTRACTED_UNVERIFIED"}
             for url, title, body, sha in rows]
    return [build_review_request(items[i:i + batch_size], model=model)
            for i in range(0, len(items), batch_size)]


def reconcile_ai_digest(database: Path, results: list[dict], *, min_importance: int = 60,
                        output: Path | None = None, include_all: bool = True) -> dict:
    if not 0 <= min_importance <= 100:
        raise ValueError("invalid threshold")
    with connect(database) as conn:
        rows = conn.execute("""SELECT n.url,n.title_hint,n.listing_sha256,
            d.detail_sha256,d.body_chars,d.review_status,d.body_text
            FROM s01_news_review n LEFT JOIN s01_news_detail_review d ON d.url=n.url
            ORDER BY n.url""").fetchall()
    source = [{"url": r[0]} for r in rows]
    reviewed = {}
    for result in results:
        for item in validate_review_result(result, source):
            if item["source_url"] in reviewed:
                raise ValueError("duplicate AI result across batches")
            reviewed[item["source_url"]] = item
    items = []
    from .s01_daily_ledger import content_fingerprint
    for url, title, listing_sha, detail_sha, chars, status, body in rows:
        ai = reviewed.get(url)
        if not detail_sha or (chars or 0) < 100:
            disposition, reason = "DETAIL_REQUIRED", "Missing sufficient article body evidence"
        elif ai is None:
            disposition, reason = "AI_REVIEW_PENDING", "No validated Chinese AI review"
        elif include_all or ai["importance"] >= min_importance:
            disposition, reason = "INCLUDED", None
        else:
            disposition, reason = "EXCLUDED_LOW_PRIORITY", ai["rationale"]
        items.append({"url": url, "title_hint": title, "listing_sha256": listing_sha,
                      "detail_sha256": detail_sha, "detail_status": status,
                      "content_sha256": content_fingerprint(body) if body else None,
                      "disposition": disposition, "exclusion_reason": reason,
                      "ai_review": ai})
    included = sorted((i for i in items if i["disposition"] == "INCLUDED"),
                      key=lambda i: -i["ai_review"]["importance"])
    unresolved = sum(i["disposition"] in {"DETAIL_REQUIRED", "AI_REVIEW_PENDING"} for i in items)
    report = {"total_discovered": len(items), "included": len(included),
              "excluded": sum(i["disposition"] == "EXCLUDED_LOW_PRIORITY" for i in items),
              "unresolved": unresolved,
              "digest_publish_gate": "REVIEW_REQUIRED" if not unresolved else ("PARTIAL_READY_FOR_REVIEW" if included else "BLOCKED_NO_ARTICLES"),
              "items": items}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def render_chinese_digest(report: dict) -> str:
    lines = ["S01 缅甸政府门户新闻｜中文审核稿",
             "来源网页TLS证书未验证；AI摘要不等于官方事实核验。",
             f"发现 {report['total_discovered']}｜收录 {report['included']}｜排除 {report['excluded']}｜待处理 {report['unresolved']}"]
    included = sorted((i for i in report["items"] if i["disposition"] == "INCLUDED"),
                      key=lambda i: -i["ai_review"]["importance"])
    for index, item in enumerate(included, 1):
        ai = item["ai_review"]
        lines.extend([f"{index}. {ai['chinese_title']}（{ai['importance']}分｜{ai['category']}）",
                      ai["chinese_summary"], f"重要性：{ai['rationale']}",
                      f"证据局限：{ai['evidence_limitations']}", f"原文：{item['url']}"])
    lines.append("未收录及待处理对账：")
    for item in report["items"]:
        if item["disposition"] != "INCLUDED":
            lines.append(f"{item['disposition']}｜{item['title_hint']}｜{item['exclusion_reason']}｜{item['url']}")
    return "\n".join(lines)
