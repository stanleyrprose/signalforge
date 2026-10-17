"""Transfer one immutable S01 edition between Mac and Bangkok over existing SSH.

This is a staging utility only; it does not send Telegram or alter schedules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def stage(manifest_path: Path, inbox: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    edition = manifest["edition_id"]
    if not isinstance(edition, str) or len(edition) != 64 or any(c not in "0123456789abcdef" for c in edition):
        raise ValueError("invalid edition id")
    pdf = manifest_path.parent / Path(manifest["pdf"]).name
    if not pdf.is_file() or hashlib.sha256(pdf.read_bytes()).hexdigest() != manifest["pdf_sha256"]:
        raise ValueError("PDF checksum mismatch")
    destination = inbox / edition
    destination.mkdir(parents=True, exist_ok=True)
    for source in (manifest_path, pdf):
        target = destination / source.name
        if target.exists():
            if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(source.read_bytes()).digest():
                raise ValueError("existing edition file differs; manual reconciliation required")
            continue
        temporary = target.with_name(target.name + ".partial")
        if temporary.exists():
            temporary.unlink()
        shutil.copyfile(source, temporary)
        temporary.replace(target)
    return {"status": "STAGED", "edition_id": edition,
            "manifest": str(destination / manifest_path.name),
            "pdf": str(destination / pdf.name)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("inbox", type=Path)
    args = parser.parse_args()
    print(json.dumps(stage(args.manifest, args.inbox), ensure_ascii=False))


if __name__ == "__main__":
    main()
