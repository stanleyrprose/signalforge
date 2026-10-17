"""S01 Mac/Bangkok file handoff with atomic inbox publishing.

This module only stages and validates artifacts. It never invokes Telegram or SSH.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from .s01_daily_ledger import article_identity, edition_identity


def _manifest(path: Path) -> tuple[dict, Path]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data["articles"]
    pairs = [(e["identity"], e["detail_sha"]) for e in entries]
    if not pairs or len({p[0] for p in pairs}) != len(pairs):
        raise ValueError("empty or duplicate article identities")
    if edition_identity(data["date"], pairs) != data["edition_id"]:
        raise ValueError("edition mismatch")
    if any(article_identity(e["url"]) != e["identity"] for e in entries):
        raise ValueError("article identity mismatch")
    pdf = path.parent / Path(data["pdf"]).name
    if not pdf.is_file() or hashlib.sha256(pdf.read_bytes()).hexdigest() != data["pdf_sha256"]:
        raise ValueError("PDF missing or checksum mismatch")
    return data, pdf


def stage(manifest_path: Path, outbox: Path) -> dict:
    manifest, pdf = _manifest(manifest_path)
    edition = manifest["edition_id"]
    outbox.mkdir(parents=True, exist_ok=True)
    target = outbox / edition
    if target.exists():
        existing = target / "manifest.json"
        if existing.is_file() and existing.read_bytes() == manifest_path.read_bytes():
            _manifest(existing)
            return {"status": "ALREADY_STAGED", "directory": str(target)}
        raise ValueError("edition outbox collision")
    tmp = Path(tempfile.mkdtemp(prefix=".s01-stage-", dir=outbox))
    try:
        shutil.copyfile(manifest_path, tmp / "manifest.json")
        shutil.copyfile(pdf, tmp / pdf.name)
        (tmp / "READY").write_text(edition + "\n", encoding="ascii")
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)
    return {"status": "STAGED", "directory": str(target), "edition_id": edition}


def accept(inbox_dir: Path) -> dict:
    ready = inbox_dir / "READY"
    manifest_path = inbox_dir / "manifest.json"
    if not ready.is_file() or not manifest_path.is_file():
        raise ValueError("incomplete handoff")
    manifest, pdf = _manifest(manifest_path)
    if ready.read_text(encoding="ascii").strip() != manifest["edition_id"]:
        raise ValueError("handoff marker mismatch")
    return {"status": "VERIFIED", "manifest": str(manifest_path),
            "pdf": str(pdf), "edition_id": manifest["edition_id"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("stage", "accept"))
    parser.add_argument("path", type=Path)
    parser.add_argument("outbox", nargs="?", type=Path)
    args = parser.parse_args()
    if args.mode == "stage":
        if args.outbox is None:
            parser.error("stage requires outbox")
        result = stage(args.path, args.outbox)
    else:
        result = accept(args.path)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
