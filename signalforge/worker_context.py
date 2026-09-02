from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class WorkerContextError(RuntimeError):
    pass


def load_worker_context() -> dict[str, Any]:
    invocation_id = os.environ.get("INVOCATION_ID") or os.environ.get("SIGNALFORGE_INVOCATION_ID")
    if not invocation_id:
        if os.environ.get("SIGNALFORGE_TEST_MODE") == "1":
            return {"invocation_id": "test-invocation", "run_id": "test-worker-run", "application": "signalforge", "worker": "bangkok"}
        raise WorkerContextError("missing systemd INVOCATION_ID")
    root = Path(os.environ.get("WORKER_APPLICATION_INVOCATION_ROOT", "/run/worker/apps"))
    path = root / "signalforge" / f"{invocation_id}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkerContextError(f"worker application correlation unavailable: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkerContextError("worker application correlation is not an object")
    if value.get("invocation_id") != invocation_id or value.get("application") != "signalforge":
        raise WorkerContextError("worker application correlation mismatch")
    if value.get("worker") != "bangkok" or not value.get("run_id"):
        raise WorkerContextError("SignalForge must correlate to a Bangkok Worker Run")
    return value
