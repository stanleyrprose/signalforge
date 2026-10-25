#!/usr/bin/env python3
"""Static Markdown inventory and local-link audit; does not run application code."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {".git", ".ai-bridge", ".pytest_cache", ".ruff_cache", "__pycache__", ".venv", "venv", "node_modules"}
def audit():
    files = sorted(p for p in ROOT.rglob("*.md") if not any(x in EXCLUDE for x in p.relative_to(ROOT).parts))
    broken, records = [], []
    for path in files:
        raw = path.read_text(encoding="utf-8")
        # Fenced code is example text, not a rendered Markdown link.
        text = re.sub(r"(?ms)^(```|~~~).*?^\1[^\n]*$", "", raw)
        targets = re.findall(r"!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", text)
        targets += re.findall(r"(?m)^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)", text)
        local = 0
        for target in targets:
            target = target.strip("<>")
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            local += 1
            dest = path.parent / unquote(url.path)
            if not dest.exists():
                broken.append({"file":str(path.relative_to(ROOT)), "target":target})
        records.append({"file":str(path.relative_to(ROOT)), "sha256":hashlib.sha256(raw.encode()).hexdigest(), "local_links":local})
    preservation = []
    baseline = ROOT / "docs/verification/historical-body-sha256-20261024.json"
    if baseline.exists():
        for name, expected in json.loads(baseline.read_text())["files"].items():
            body = (ROOT / name).read_text(encoding="utf-8")
            body = re.sub(r"\n\n> Historical evidence scope — added 2026-10-24: [^\n]*\n", "\n", body, count=1)
            preservation.append({"file":name, "unchanged":hashlib.sha256(body.encode()).hexdigest() == expected})
    return {"historical_body_checks":preservation, "kind":"STATIC_LINK_AUDIT_NOT_SEMANTIC_OR_PRODUCTION_ACCEPTANCE", "files":len(files), "broken_links":broken, "records":records}
if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
