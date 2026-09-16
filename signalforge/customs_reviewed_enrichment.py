from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import repo_root

CUSTOMS_REVIEWED_ENRICHMENT_VERSION = 1
_DATA_FILE = "Customs-Reviewed-PDF-Enrichments-v1.json"
_ALLOWED_FIELDS = {
    "business_stage",
    "scope_summary",
    "action_date",
    "action_time",
    "action_date_kind",
    "action_date_evidence",
    "commercial_event_type",
    "commercial_direction",
    "location",
    "location_evidence",
    "next_action_summary",
    "next_action_evidence",
    "detail_completeness",
}


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != CUSTOMS_REVIEWED_ENRICHMENT_VERSION:
        raise ValueError("invalid Customs reviewed enrichment schema")
    records = raw.get("records")
    if not isinstance(records, dict):
        raise ValueError("invalid Customs reviewed enrichment records")
    return raw


def reviewed_customs_overlay(
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    publication_date: object,
    attachment_url: object,
    root: Path | None = None,
) -> dict[str, object]:
    if source_id != "S08A" or item_kind != "AUCTION_NOTICE":
        return {}
    raw = _load(str((root or repo_root()) / "registry" / _DATA_FILE))
    records = raw.get("records")
    assert isinstance(records, dict)
    record = records.get(canonical_key)
    if not isinstance(record, dict):
        return {}
    if record.get("source_id") != source_id or record.get("item_kind") != item_kind:
        return {}
    if str(record.get("reference_no") or "") != str(reference_no or ""):
        return {}
    if str(record.get("publication_date") or "") != str(publication_date or ""):
        return {}
    if str(record.get("attachment_url") or "") != str(attachment_url or ""):
        return {}
    fields = record.get("fields")
    if not isinstance(fields, dict) or any(key not in _ALLOWED_FIELDS for key in fields):
        raise ValueError("invalid Customs reviewed enrichment fields")
    result = {key: value for key, value in fields.items() if key in _ALLOWED_FIELDS}
    result.update({
        "reviewed_enrichment_version": CUSTOMS_REVIEWED_ENRICHMENT_VERSION,
        "reviewed_enrichment_status": record.get("review_status"),
        "reviewed_enrichment_at": record.get("reviewed_at"),
        "reviewed_enrichment_read_only": True,
    })
    return result


def apply_reviewed_customs_overlay(
    payload: dict[str, object],
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    root: Path | None = None,
) -> dict[str, object]:
    overlay = reviewed_customs_overlay(
        canonical_key=canonical_key,
        source_id=source_id,
        item_kind=item_kind,
        reference_no=reference_no,
        publication_date=payload.get("publication_date"),
        attachment_url=payload.get("attachment_url"),
        root=root,
    )
    if not overlay:
        return payload
    enriched = dict(payload)
    for key, value in overlay.items():
        if key == "detail_completeness" or key.startswith("reviewed_") or not enriched.get(key):
            enriched[key] = value
    return enriched
