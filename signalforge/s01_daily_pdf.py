"""Generate the complete S01 Chinese edition from a reconciled coverage audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def render_pdf(report: dict, output: Path, *, edition_date: str, fontfile: Path) -> dict:
    import fitz

    included = [item for item in report["items"] if item["disposition"] == "INCLUDED"]
    if len(included) != report["included"] or report["unresolved"] or report.get("excluded", 0):
        raise ValueError("PDF blocked: coverage audit incomplete or articles excluded")
    included.sort(key=lambda item: -item["ai_review"]["importance"])
    if not fontfile.is_file():
        raise FileNotFoundError(fontfile)
    font = fitz.Font(fontfile=str(fontfile))
    doc = fitz.open()
    page = None
    y = 0

    def new_page():
        nonlocal page, y
        page = doc.new_page(width=595, height=842)
        page.insert_font(fontname="s01cjk", fontfile=str(fontfile))
        y = 46

    def write(text: str, size: int = 10, indent: int = 0):
        nonlocal y
        import re
        # Preserve the original spelling in the source audit/URL; never paint
        # unreadable missing-glyph boxes or invent a Chinese proper name.
        text = re.sub(r"[\u1000-\u109f\uaa60-\uaa7f\ua9e0-\ua9ff]+",
                      "〔缅文专名见原文〕", str(text))
        available = 510 - indent
        for raw in str(text).splitlines() or [""]:
            segments = []
            chunk = ""
            for char in raw:
                if chunk and font.text_length(chunk + char, fontsize=size) > available:
                    segments.append(chunk)
                    chunk = char
                else:
                    chunk += char
            segments.append(chunk)
            for segment in segments:
                if page is None or y > 795:
                    new_page()
                page.insert_text((42 + indent, y), segment, fontname="s01cjk",
                                 fontsize=size, color=(0.12, 0.15, 0.2))
                y += size * 1.55
            y += 3

    write("S01 缅甸政府门户｜全量中文新闻", 16)
    write(f"{edition_date} | 来源证书未验证 | AI翻译非独立事实核验", 10)
    write(f"发现 {report['total_discovered']} | 收录 {len(included)} | "
          f"未完成 {report['unresolved']} | 重要性不用于过滤", 10)
    for index, item in enumerate(included, 1):
        ai = item["ai_review"]
        write(f"{index}. [{ai['importance']}分] {ai['chinese_title']}", 12)
        write(ai["chinese_summary"], 10, 10)
        write("分类：" + ai["category"] + "；重要性：" + ai["rationale"], 9, 10)
        write("证据限制：" + ai["evidence_limitations"], 9, 10)
        write("原文：" + item["url"], 7, 10)
    write("审核说明：文章内容来自 S01 页面；所有事实仍以原始来源为准。", 9)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output), garbage=4, deflate=True)
    result = {"pdf": str(output), "pages": len(doc), "articles": len(included),
              "bytes": output.stat().st_size}
    doc.close()
    return result


def render_digest(report: dict, *, edition_date: str, top_n: int = 10) -> str:
    included = sorted((item for item in report["items"] if item["disposition"] == "INCLUDED"),
                      key=lambda item: -item["ai_review"]["importance"])
    lines = [f"【S01 缅甸政府门户｜{edition_date}】",
             f"本期中文新闻 {len(included)} 条；完整内容、原文链接见 PDF。",
             "重要性只影响以下 Digest 排序，不影响 PDF 收录。"]
    for index, item in enumerate(included[:top_n], 1):
        ai = item["ai_review"]
        title = ai["chinese_title"][:75]
        summary = ai["chinese_summary"][:135]
        reason = ai["rationale"][:65]
        lines.append(f"{index}. {title}（{ai['category'][:30]}）\n{summary}"
                     f"\n关注：{reason}\n来源：随附PDF第{index}条；官方单一来源，未经独立核验。")
    if report["unresolved"]:
        lines.append(f"注意：{report['unresolved']} 条待补处理，未计入已完成新闻。")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audit", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--date", required=True)
    parser.add_argument("--font", type=Path, default=Path("/System/Library/Fonts/Hiragino Sans GB.ttc"))
    args = parser.parse_args()
    report = json.loads(args.audit.read_text(encoding="utf-8"))
    result = render_pdf(report, args.output, edition_date=args.date, fontfile=args.font)
    args.output.with_suffix(".digest.txt").write_text(render_digest(report, edition_date=args.date),
                                                       encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
