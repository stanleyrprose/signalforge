from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .config import repo_root

COVERAGE_GAP_SCHEMA_VERSION = 1
VERIFIED_EXTERNAL_RESOLUTION = "VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY"
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


def _active_reviewed_records(
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
            reviewed_at = datetime.strptime(str(value["reviewed_at"]), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("invalid coverage-gap deadline/reviewed_at") from exc
        url = str(value["url"])
        parsed = urlparse(url)
        source_id = str(value["source_id"])
        if source_id == "S23":
            valid_url = url.startswith("https://construction.gov.mm/letter-download/")
        elif source_id == "S13" and str(value["evidence_basis"]).startswith("REVIEWED_NATIONAL_PORTAL_HOSTED_"):
            valid_url = (
                parsed.scheme == "https"
                and parsed.hostname in {"myanmar.gov.mm", "www.myanmar.gov.mm"}
                and parsed.path.startswith("/documents/")
            )
        else:
            valid_url = False
        if not valid_url:
            raise ValueError("coverage-gap URL/evidence source combination is not allowlisted")
        if reviewed_at > today or deadline < today:
            continue
        deadline_time_raw = str(value.get("deadline_time") or "").strip()
        if deadline_time_raw:
            try:
                deadline_local = datetime.strptime(
                    f"{deadline.isoformat()} {deadline_time_raw}", "%Y-%m-%d %H:%M"
                ).replace(tzinfo=_LOCAL_TZ)
            except ValueError as exc:
                raise ValueError("invalid coverage-gap deadline_time") from exc
            if deadline_local <= local_now:
                continue
        item = dict(value)
        item["reviewed_read_only"] = True
        item["canonical_signal_status"] = "OUTSIDE_CANONICAL_SIGNAL_PIPELINE"
        active.append(item)
    active.sort(key=lambda item: (str(item["deadline"]), str(item["gap_id"])))
    return active


def reviewed_coverage_gaps(
    *,
    now: datetime | None = None,
    root: Path | None = None,
) -> list[dict[str, object]]:
    """Reviewed gaps that still lack an accepted business-output resolution."""

    return [
        item
        for item in _active_reviewed_records(now=now, root=root)
        if str(item.get("resolution_mode") or "") != VERIFIED_EXTERNAL_RESOLUTION
    ]


def verified_external_opportunities(
    *,
    now: datetime | None = None,
    root: Path | None = None,
) -> list[dict[str, object]]:
    """Official issuer-document opportunities recovered outside canonical acquisition.

    These records are deliberately not canonical Signals. They are accepted for
    customer-facing business coverage only when issuer identity, business scope
    and deadline are all independently reviewed from an allowlisted official
    document.
    """

    verified: list[dict[str, object]] = []
    for item in _active_reviewed_records(now=now, root=root):
        if str(item.get("resolution_mode") or "") != VERIFIED_EXTERNAL_RESOLUTION:
            continue
        required_true = (
            item.get("issuer_document_verified"),
            item.get("issuer_identity_verified"),
            item.get("scope_verified"),
            item.get("deadline_verified"),
        )
        if not all(value is True for value in required_true):
            raise ValueError("verified external opportunity is missing required review proof")
        if item.get("canonical_truth") is not False:
            raise ValueError("verified external opportunity must remain non-canonical")
        document_sha256 = str(item.get("document_sha256") or "")
        if len(document_sha256) != 64 or any(char not in "0123456789abcdef" for char in document_sha256.lower()):
            raise ValueError("verified external opportunity requires reviewed document sha256")
        if not str(item.get("coverage_origin") or "") or not str(item.get("target_source_id") or ""):
            raise ValueError("verified external opportunity requires coverage origin and target source")
        if not str(item.get("verification_basis") or ""):
            raise ValueError("verified external opportunity requires verification basis")
        copy = dict(item)
        copy["verified_external"] = True
        copy["business_coverage_status"] = VERIFIED_EXTERNAL_RESOLUTION
        verified.append(copy)
    return verified
