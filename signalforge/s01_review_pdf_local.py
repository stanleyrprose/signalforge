from pathlib import Path
import json
import fitz

root=Path("/tmp/s01-full-review-20261016")
report=json.loads((root/"coverage-audit.json").read_text())
fontfile="/System/Library/Fonts/Hiragino Sans GB.ttc"
font=fitz.Font(fontfile=fontfile)
doc=fitz.open()
page=None
y=0
def newpage():
    global page,y
    page=doc.new_page(width=595,height=842)
    page.insert_font(fontname="cjk",fontfile=fontfile)
    y=48
def line(text,size=10,indent=0):
    global y
    if page is None or y>795:
        newpage()
    available=510-indent
    chunks=[]
    chunk=""
    for char in str(text):
        if font.text_length(chunk+char,fontsize=size)>available and chunk:
            chunks.append(chunk);chunk=char
        else: chunk+=char
    if chunk:chunks.append(chunk)
    for segment in chunks or [""]:
        if y>795:newpage()
        page.insert_text((42+indent,y),segment,fontname="cjk",fontsize=size,color=(0.12,0.15,0.2))
        y+=size*1.55
    y+=3
line("S01 缅甸政府门户｜中文新闻人工审核稿",16)
line("2026-10-16  |  未经独立事实核实  |  禁止自动发布",10)
line("发现84条；全部收录84条；重要性过滤0条；待处理0条。来源TLS证书未验证。",10)
line("一、重点新闻（AI评分，待人工确认）",13)
included=sorted([x for x in report["items"] if x["disposition"]=="INCLUDED"],key=lambda x:-x["ai_review"]["importance"])
for i,item in enumerate(included,1):
    ai=item["ai_review"]
    line(f'{i}. [{ai["importance"]}分] {ai["chinese_title"]}',12)
    line(ai["chinese_summary"],10,10)
    line("分类："+ai["category"]+"；理由："+ai["rationale"],9,10)
    line("证据限制："+ai["evidence_limitations"],9,10)
    line("原文："+item["url"],7,10)
line("二、低优先级新闻及排除理由（17条）",13)
for i,item in enumerate([x for x in report["items"] if x["disposition"]!="INCLUDED"],1):
    ai=item["ai_review"] or {}
    line(f'{i}. [{ai.get("importance","?")}分] {ai.get("chinese_title",item["title_hint"])}',10)
    line("排除理由："+str(item["exclusion_reason"]),9,10)
line("审核说明：所有新闻均来自S01页面及AI提取，不代表独立确认；请审核事实表述、优先级、遗漏和误收录。",9)
out=root/"S01-Chinese-News-Review-20261016.pdf"
doc.save(out,garbage=4,deflate=True)
print("PDF",out,"pages",len(doc),"bytes",out.stat().st_size)
