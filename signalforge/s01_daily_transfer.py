"""Explicit Mac-to-Bangkok S01 transfer, sender invocation and receipt return.

Not wired into the production scheduler. SSH host aliases are configured externally.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import re
import subprocess
from pathlib import Path

from .s01_daily_handoff import stage
from .s01_daily_receipt import import_receipt


def _run(argv: list[str]) -> None:
    subprocess.run(argv, check=True, timeout=180)


@contextlib.contextmanager
def _edition_lock(outbox: Path, edition: str):
    """One Mac-side transfer per edition; released even after a crash."""
    outbox.mkdir(parents=True, exist_ok=True)
    lock_path = outbox / (".s01-transfer-" + edition + ".lock")
    with lock_path.open("a+b") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("S01 edition transfer already running") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def transfer(manifest: Path, mac_ledger: Path, outbox: Path, *,
             host: str, remote_inbox: str, remote_ledger: str,
             python: str = "python3") -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", host) or host.startswith("-"):
        raise ValueError("SSH host must be a preconfigured safe alias")
    for value in (remote_inbox, remote_ledger):
        if not value.startswith("/") or not re.fullmatch(r"[/A-Za-z0-9_.-]+", value):
            raise ValueError("remote paths must be safe absolute paths")
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", python) or python.startswith("-"):
        raise ValueError("invalid remote Python executable")
    from .s01_daily_ledger import edition_identity
    source = json.loads(manifest.read_text(encoding="utf-8"))
    edition_key = edition_identity(
        source["date"],
        [(item["identity"], item["detail_sha"]) for item in source["articles"]])
    with _edition_lock(outbox, edition_key):
        return _transfer_locked(manifest, mac_ledger, outbox, host=host,
                                remote_inbox=remote_inbox,
                                remote_ledger=remote_ledger, python=python)


def _transfer_locked(manifest: Path, mac_ledger: Path, outbox: Path, *,
                     host: str, remote_inbox: str, remote_ledger: str,
                     python: str) -> dict:
    staged = stage(manifest, outbox)
    directory = Path(staged["directory"])
    edition = staged["edition_id"] if "edition_id" in staged else directory.name
    # Minimum date/edition binding survives content cleanup and guards its scope.
    from datetime import date
    day = date.fromisoformat(json.loads(manifest.read_text(encoding="utf-8"))["date"]).isoformat()
    index = mac_ledger.parent / "edition-index" / (edition + ".json")
    if index.resolve() != mac_ledger.parent.resolve() / "edition-index" / (edition + ".json"):
        raise ValueError("Unsafe S01 edition index")
    binding = {"date": day, "edition_id": edition}
    if index.exists() and json.loads(index.read_text(encoding="utf-8")) != binding:
        raise ValueError("S01 edition index mismatch")
    index.parent.mkdir(parents=True, exist_ok=True)
    temporary = index.with_suffix(".tmp")
    temporary.write_text(json.dumps(binding) + "\n", encoding="utf-8")
    temporary.replace(index)
    remote_dir = remote_inbox.rstrip("/") + "/" + edition
    # Create the inbox root explicitly; a fresh isolated deployment may not have it.
    _run(["ssh", "-o", "BatchMode=yes", host, "mkdir", "-p", remote_inbox])
    # Never overwrite an existing remote edition: it may already contain
    # a successful receipt or an unresolved in-flight Telegram attempt.
    probe = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host, "test", "-e", remote_dir],
        check=False, timeout=180)
    if probe.returncode == 1:
        _run(["ssh", "-o", "BatchMode=yes", host, "mkdir", remote_dir])
    elif probe.returncode != 0:
        raise RuntimeError("remote edition probe failed; refuse overwrite")
    # A missing READY marks an interrupted upload. Re-copying immutable
    # artifacts is safe only before publishing READY; a complete edition is
    # never overwritten, including when its Telegram receipt is missing.
    ready_probe = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host, "test", "-f", remote_dir + "/READY"],
        check=False, timeout=180)
    if ready_probe.returncode == 1:
        files = sorted(p for p in directory.iterdir() if p.name != "READY")
        _run(["scp", "-B", *map(str, files), f"{host}:{remote_dir}/"])
        _run(["scp", "-B", str(directory / "READY"), f"{host}:{remote_dir}/READY"])
    elif ready_probe.returncode != 0:
        raise RuntimeError("remote READY probe failed; refuse overwrite")
    _run(["ssh", "-o", "BatchMode=yes", host, python, "-m",
          "signalforge.s01_daily_handoff", "accept", remote_dir])
    receipt = manifest.with_suffix(".receipt.json")
    # Recover an already-sent edition before invoking the sender again.
    # A missing receipt is not proof of non-delivery: Bangkok's persistent
    # ledger remains the authority and its sender blocks UNKNOWN attempts.
    remote_receipt = remote_dir + "/manifest.receipt.json"
    found = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host, "test", "-f", remote_receipt],
        check=False, timeout=180)
    if found.returncode == 1:
        _run(["ssh", "-o", "BatchMode=yes", host, "env", "PYTHONPATH=/srv/signalforge/active", python, "-m",
              "signalforge.s01_daily_sender", remote_ledger, remote_dir + "/manifest.json"])
    elif found.returncode != 0:
        raise RuntimeError("remote receipt probe failed; delivery status unknown")
    _run(["scp", "-B", f"{host}:{remote_receipt}", str(receipt)])
    result = import_receipt(mac_ledger, manifest, receipt)
    # Cleanup only after Mac has durably imported both Telegram receipts.
    _run(["ssh", "-o", "BatchMode=yes", host, python, "-m",
          "signalforge.s01_daily_cleanup", remote_inbox, edition, "--ledger", remote_ledger])
    # Resolve the original generated PDF before removing the staging directory.
    source_pdf = manifest.parent / Path(
        json.loads(manifest.read_text(encoding="utf-8"))["pdf"]).name
    import shutil
    shutil.copyfile(receipt, directory / "manifest.receipt.json")
    from .s01_daily_cleanup import cleanup
    cleanup(outbox, edition, ledger=mac_ledger)
    # Remove generated artifacts only when they live inside the designated
    # outbox; never unlink an arbitrary source file or evidence directory.
    generated_root = outbox.resolve()
    for artifact in (source_pdf, manifest, receipt):
        if artifact.is_symlink() or artifact.resolve().parent != generated_root:
            continue
        artifact.unlink(missing_ok=True)
    return {**result, "cleanup": "BOTH_HOSTS_STAGING_REMOVED"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("mac_ledger", type=Path)
    parser.add_argument("outbox", type=Path)
    parser.add_argument("--host", required=True)
    parser.add_argument("--remote-inbox", required=True)
    parser.add_argument("--remote-ledger", required=True)
    parser.add_argument("--python", default="python3")
    args = parser.parse_args()
    result = transfer(args.manifest, args.mac_ledger, args.outbox,
                      host=args.host, remote_inbox=args.remote_inbox,
                      remote_ledger=args.remote_ledger, python=args.python)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
