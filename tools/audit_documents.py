#!/usr/bin/env python3
"""Static Markdown path/heading audit. Not semantic or production acceptance."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {".git", ".ai-bridge", ".pytest_cache", ".ruff_cache", "__pycache__", ".venv", "venv", "node_modules"}

def rendered_text(raw):
    return re.sub(r"(?ms)^(```|~~~).*?^\1[^\n]*$", "", raw)

def anchors(raw):
    text = rendered_text(raw)
    result = set(re.findall(r'<(?:a|[hH][1-6])\b[^>]*(?:id|name)=["\']([^"\']+)["\']', text))
    counts = {}
    headings = re.findall(r"(?m)^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", text)
    headings += re.findall(r"(?m)^([^\n]+)\n {0,3}(?:=+|-+)\s*$", text)
    for heading in headings:
        heading = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", heading)
        heading = html.unescape(re.sub(r"<[^>]+>", "", heading)).lower().strip()
        slug = "".join(c for c in heading if c in "-_ " or unicodedata.category(c)[0] in "LN")
        slug = slug.replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(slug + (f"-{count}" if count else ""))
    return result

def audit():
    files = sorted(p for p in ROOT.rglob("*.md") if not any(x in EXCLUDE for x in p.relative_to(ROOT).parts))
    broken, records = [], []
    for path in files:
        raw = path.read_text(encoding="utf-8")
        text = rendered_text(raw)
        targets = re.findall(r"!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", text)
        targets += re.findall(r"(?m)^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)", text)
        local = 0
        for target in targets:
            target = target.strip("<>")
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            local += 1
            dest = path.parent / unquote(url.path) if url.path else path
            reason = None
            if not dest.exists():
                reason = "MISSING_PATH"
            elif url.fragment and dest.suffix.lower() == ".md" and unquote(url.fragment) not in anchors(dest.read_text(encoding="utf-8")):
                reason = "MISSING_HEADING"
            if reason:
                broken.append({"file":str(path.relative_to(ROOT)), "target":target, "reason":reason})
        records.append({"file":str(path.relative_to(ROOT)), "sha256":hashlib.sha256(raw.encode()).hexdigest(), "local_links":local})
    preservation = []
    baseline = ROOT / "docs/verification/historical-body-sha256-20261024.json"
    if baseline.exists():
        for name, expected in json.loads(baseline.read_text())["files"].items():
            body = (ROOT / name).read_text(encoding="utf-8")
            body = re.sub(r"\n\n> Historical evidence scope — added 2026-10-24: [^\n]*\n", "\n", body, count=1)
            preservation.append({"file":name, "unchanged":hashlib.sha256(body.encode()).hexdigest() == expected})
    return {"historical_body_checks":preservation, "kind":"STATIC_PATH_HEADING_AUDIT_NOT_SEMANTIC_OR_PRODUCTION_ACCEPTANCE", "files":len(files), "broken_links":broken, "records":records}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    result = audit()
    failures = sum(not row["unchanged"] for row in result["historical_body_checks"])
    if args.summary:
        result = {key:value for key,value in result.items() if key not in {"records", "historical_body_checks"}} | {"historical_bodies":len(result["historical_body_checks"]), "changed_historical_bodies":failures}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result["broken_links"] or failures else 0)
