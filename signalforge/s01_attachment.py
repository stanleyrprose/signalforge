"""S01 Markdown attachment contract, retaining read support for older PDF manifests."""
from pathlib import Path
import hashlib


def attachment_part(manifest: dict) -> str:
    return "markdown" if "markdown" in manifest else "pdf"


def attachment_path(manifest: dict, directory: Path) -> Path:
    return directory / Path(manifest[attachment_part(manifest)]).name


def verify_attachment(manifest: dict, directory: Path) -> Path:
    part = attachment_part(manifest)
    path = attachment_path(manifest, directory)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != manifest[part + "_sha256"]:
        raise ValueError("Attachment missing or checksum mismatch")
    return path


def paired_receipts(receipts: dict) -> bool:
    return (type(receipts.get("digest")) is int and receipts["digest"] > 0
            and any(type(receipts.get(part)) is int and receipts[part] > 0
                    for part in ("markdown", "pdf")))


def render_markdown(report: dict, *, edition_date: str) -> str:
    items = [x for x in report["items"] if x["disposition"] == "INCLUDED"]
    lines = [f"# S01 缅甸政府门户｜全量中文新闻｜{edition_date}", "",
             f"本期 {len(items)} 条。AI 翻译；官方单一来源，未经独立事实核验。", ""]
    for index, item in enumerate(items, 1):
        ai = item["ai_review"]
        lines += [f"## {index}. {ai['chinese_title']}", "",
                  ai["chinese_summary"], "",
                  f"分类：{ai['category']}｜重要性：{ai['importance']}",
                  f"关注理由：{ai['rationale']}", "",
                  f"证据限制：{ai['evidence_limitations']}", "",
                  f"原文：{item['url']}", ""]
    for item in report.get("pending_articles", []):
        lines += [f"未完成标记：{item['url']}；原因：{item.get('reason') or '无法读取，跳过'}", ""]
    return "\n".join(lines) + "\n"
