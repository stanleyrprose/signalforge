"""Shared, opt-in cleanup of task-owned transient artifacts.

Business jobs must call this only after their own durable success gate. This
module never discovers files by age or deletes evidence, ledgers or receipts.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path


class CleanupSafetyError(ValueError):
    pass


def cleanup_completed_temp(root: Path, paths: list[Path], *,
                           delivery_confirmed: bool,
                           durable_receipts_confirmed: bool) -> dict:
    """Remove explicit transient children of a dedicated task temp root.

    Safety is fail-closed: caller proves delivery completion and persisted
    receipts, files must be direct children of the allowlisted task root,
    and symlinks are never followed. No recursive search or wildcard deletion.
    """
    if not delivery_confirmed or not durable_receipts_confirmed:
        raise CleanupSafetyError("task delivery and durable receipts not both confirmed")
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise CleanupSafetyError("invalid task temp root")
    candidates = [Path(path) for path in paths]
    if not candidates:
        return {"status": "NOTHING_TO_REMOVE", "removed": 0}
    if len(set(map(str, candidates))) != len(candidates):
        raise CleanupSafetyError("duplicate cleanup path")
    for path in candidates:
        if path.is_symlink() or not path.exists() or path.resolve().parent != root:
            raise CleanupSafetyError("path outside task-owned temp root or missing")
        if path.name.startswith(".") or path.name in {
            "state", "evidence-retained", "receipts", "logs", "db",
        }:
            raise CleanupSafetyError("protected operational path")
    removed = 0
    for path in candidates:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()
        else:
            raise CleanupSafetyError("unsupported file type")
        removed += 1
    return {"status": "TEMP_ARTIFACTS_REMOVED", "removed": removed}
