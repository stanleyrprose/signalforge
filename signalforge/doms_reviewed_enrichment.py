from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import repo_root

DOMS_REVIEWED_ENRICHMENT_VERSION = 1
_DATA_FILE = "DOMS-Reviewed-OCR-Enrichments-v1.json"
_ALLOWED_FIELDS = {
    "scope_summary",
    "quantity_or_lot_summary",
    "quantity_or_lot_evidence",
    "quantity_or_lot_confidence",
    "detail_completeness",
    "image_review_notes",
}
_REFERENCE_ONLY_RE = re.compile(r"DMS.*_[0-9a-f]{8}-[0-9a-f-]{20,}", re.I)


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != DOMS_REVIEWED_ENRICHMENT_VERSION:
        raise ValueError("invalid DOMS reviewed enrichment schema")
    records = raw.get("records")
    if not isinstance(records, dict):
        raise ValueError("invalid DOMS reviewed enrichment records")
    return raw


def _data(root: Path | None = None) -> dict[str, Any]:
    return _load(str((root or repo_root()) / "registry" / _DATA_FILE))


def reviewed_doms_overlay(
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    url: object = None,
    root: Path | None = None,
) -> dict[str, object]:
    if source_id != "S26" or item_kind != "TENDER":
        return {}
    records = _data(root).get("records")
    assert isinstance(records, dict)
    record = records.get(canonical_key)
    if not isinstance(record, dict):
        return {}
    if record.get("source_id") != source_id or record.get("item_kind") != item_kind:
        return {}
    if str(record.get("reference_no") or "") != str(reference_no or ""):
        return {}
    if url is not None and str(record.get("article_url") or "") != str(url or ""):
        return {}
    fields = record.get("fields")
    if not isinstance(fields, dict) or any(key not in _ALLOWED_FIELDS for key in fields):
        raise ValueError("invalid DOMS reviewed enrichment fields")
    result = {key: value for key, value in fields.items() if key in _ALLOWED_FIELDS}
    result.update({
        "reviewed_enrichment_version": DOMS_REVIEWED_ENRICHMENT_VERSION,
        "reviewed_enrichment_status": record.get("review_status"),
        "reviewed_enrichment_at": record.get("reviewed_at"),
        "reviewed_enrichment_read_only": True,
    })
    return result


def apply_reviewed_doms_overlay(
    payload: dict[str, object],
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    root: Path | None = None,
) -> dict[str, object]:
    overlay = reviewed_doms_overlay(
        canonical_key=canonical_key,
        source_id=source_id,
        item_kind=item_kind,
        reference_no=reference_no,
        url=payload.get("url"),
        root=root,
    )
    if not overlay:
        return payload
    enriched = dict(payload)
    for key, value in overlay.items():
        if key == "scope_summary":
            current = str(enriched.get(key) or "")
            if not current or _REFERENCE_ONLY_RE.search(current):
                enriched[key] = value
        elif key == "detail_completeness":
            enriched[key] = value
        elif key.startswith("reviewed_") or not enriched.get(key):
            enriched[key] = value
    return enriched
