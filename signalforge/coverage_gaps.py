from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .config import repo_root

COVERAGE_GAP_SCHEMA_VERSION = 1
_DATA_FILE = "Reviewed-Coverage-Gaps-v1.json"
_LOCAL_TZ = ZoneInfo("Asia/Yangon")
_REQUIRED = {
    "gap_id",
    "source_id",
    "issuer",
    "title",
    "location",
    "deadline",
    "url",
    "reason",
    "evidence_basis",
    "reviewed_at",
}


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != COVERAGE_GAP_SCHEMA_VERSION:
        raise ValueError("invalid coverage-gap schema")
    records = raw.get("records")
    if not isinstance(records, list):
        raise ValueError("invalid coverage-gap records")
    return raw


def reviewed_coverage_gaps(
    *,
    now: datetime | None = None,
    root: Path | None = None,
) -> list[dict[str, object]]:
    local_now = (now or datetime.now(_LOCAL_TZ)).astimezone(_LOCAL_TZ)
    today = local_now.date()
    raw = _load(str((root or repo_root()) / "registry" / _DATA_FILE))
    active: list[dict[str, object]] = []
    seen: set[str] = set()
    for value in raw["records"]:
        if not isinstance(value, dict) or not _REQUIRED.issubset(value):
            raise ValueError("invalid coverage-gap record")
        gap_id = str(value["gap_id"])
        if not gap_id or gap_id in seen:
            raise ValueError("duplicate/empty coverage-gap id")
        seen.add(gap_id)
        try:
            deadline = datetime.strptime(str(value["deadline"]), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("invalid coverage-gap deadline") from exc
        if not str(value["url"]).startswith("https://construction.gov.mm/letter-download/"):
            raise ValueError("coverage-gap URL must be official MOC download URL")
        if deadline < today:
            continue
        item = dict(value)
        item["reviewed_read_only"] = True
        item["canonical_signal_status"] = "OUTSIDE_CANONICAL_SIGNAL_PIPELINE"
        active.append(item)
    active.sort(key=lambda item: (str(item["deadline"]), str(item["gap_id"])))
    return active
