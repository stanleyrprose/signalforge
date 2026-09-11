from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import repo_root

MTE_REVIEWED_ENRICHMENT_VERSION = 1
_DATA_FILE = "MTE-Reviewed-Image-Enrichments-v1.json"
_ALLOWED_FIELDS = {
    "action_time",
    "action_time_evidence",
    "location",
    "location_evidence",
    "quantity_or_lot_summary",
    "quantity_or_lot_evidence",
    "quantity_or_lot_confidence",
    "next_action_summary",
    "next_action_evidence",
    "image_review_notes",
}


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, dict) or raw.get("schema_version") != MTE_REVIEWED_ENRICHMENT_VERSION:
        raise ValueError("invalid MTE reviewed enrichment schema")
    records = raw.get("records")
    if not isinstance(records, dict):
        raise ValueError("invalid MTE reviewed enrichment records")
    return raw


def _data(root: Path | None = None) -> dict[str, Any]:
    return _load(str((root or repo_root()) / "registry" / _DATA_FILE))


def reviewed_mte_records(root: Path | None = None) -> dict[str, dict[str, object]]:
    records = _data(root).get("records")
    assert isinstance(records, dict)
    return {str(key): dict(value) for key, value in records.items() if isinstance(value, dict)}


def reviewed_mte_overlay(
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    action_date: object,
    url: object = None,
    root: Path | None = None,
) -> dict[str, object]:
    if source_id != "S32" or item_kind != "AUCTION_NOTICE":
        return {}
    records = reviewed_mte_records(root)
    record = records.get(canonical_key)
    if not isinstance(record, dict):
        return {}
    if record.get("source_id") != source_id or record.get("item_kind") != item_kind:
        return {}
    if str(record.get("reference_no") or "") != str(reference_no or ""):
        return {}
    if str(record.get("expected_action_date") or "") != str(action_date or ""):
        return {}
    if url is not None and str(record.get("article_url") or "") != str(url or ""):
        return {}
    fields = record.get("fields")
    if not isinstance(fields, dict) or any(key not in _ALLOWED_FIELDS for key in fields):
        raise ValueError("invalid MTE reviewed enrichment fields")
    result = {key: value for key, value in fields.items() if key in _ALLOWED_FIELDS}
    result.update({
        "reviewed_enrichment_version": MTE_REVIEWED_ENRICHMENT_VERSION,
        "reviewed_enrichment_status": record.get("review_status"),
        "reviewed_enrichment_at": record.get("reviewed_at"),
        "reviewed_image_url": record.get("image_url"),
        "reviewed_image_sha256": record.get("image_sha256"),
        "reviewed_rules_url": record.get("rules_url"),
        "reviewed_enrichment_read_only": True,
    })
    return result


def apply_reviewed_mte_overlay(
    payload: dict[str, object],
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    root: Path | None = None,
) -> dict[str, object]:
    overlay = reviewed_mte_overlay(
        canonical_key=canonical_key,
        source_id=source_id,
        item_kind=item_kind,
        reference_no=reference_no,
        action_date=payload.get("action_date"),
        url=payload.get("url"),
        root=root,
    )
    if not overlay:
        return payload
    enriched = dict(payload)
    # HTML/canonical facts always win. Reviewed fields only fill gaps.
    for key, value in overlay.items():
        if key.startswith("reviewed_") or not enriched.get(key):
            enriched[key] = value
    return enriched
