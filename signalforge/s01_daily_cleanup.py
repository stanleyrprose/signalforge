"""Remove only a verified S01 edition's temporary transfer directory.

Never removes ledgers, source evidence, code or directories outside the configured inbox.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from .s01_daily_handoff import accept
from .s01_attachment import attachment_part, attachment_path


def cleanup(root: Path, edition: str, *, ledger: Path | None = None) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", edition):
        raise ValueError("invalid edition identifier")
    root = root.resolve(strict=True)
    directory = root / edition
    if directory.is_symlink() or not directory.is_dir() or directory.resolve().parent != root:
        raise ValueError("unsafe edition directory")
    verified = accept(directory)
    if verified["edition_id"] != edition:
        raise ValueError("edition marker mismatch")
    receipt = directory / "manifest.receipt.json"
    if not receipt.is_file():
        raise ValueError("no Telegram receipt; refuse cleanup")
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    import hashlib
    manifest_bytes = (directory / "manifest.json").read_bytes()
    if payload.get("edition_id") != edition or (
        payload.get("manifest_sha256") != hashlib.sha256(manifest_bytes).hexdigest()
    ) or payload.get("articles") != json.loads(manifest_bytes)["articles"] or not all(
        type(payload.get("telegram", {}).get(k)) is int and payload["telegram"][k] > 0
        for k in ("digest", attachment_part(json.loads(manifest_bytes)))
    ):
        raise ValueError("incomplete or mismatched delivery receipt")
    allowed = {"READY", "manifest.json", "manifest.receipt.json",
               attachment_path(json.loads(manifest_bytes), directory).name}
    if {p.name for p in directory.iterdir()} != allowed or any(
        p.is_symlink() or not p.is_file() for p in directory.iterdir()
    ):
        raise ValueError("unexpected files in cleanup directory")
    if ledger is not None:
        from .s01_daily_ledger import S01Ledger
        retained = S01Ledger(ledger)
        try:
            retained.purge_delivered_review_content(edition)
        finally:
            retained.close()
    shutil.rmtree(directory)
    return {"status": "TEMP_ARTIFACTS_REMOVED", "edition_id": edition}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("edition")
    parser.add_argument("--ledger", type=Path)
    args = parser.parse_args()
    print(json.dumps(cleanup(args.root, args.edition, ledger=args.ledger)))


if __name__ == "__main__":
    main()
