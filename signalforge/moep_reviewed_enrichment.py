from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import repo_root

MOEP_REVIEWED_ENRICHMENT_VERSION = 1
_DATA_FILE = "MOEP-Reviewed-Official-Newspaper-Enrichments-v1.json"
_ALLOWED_FIELDS = {
    "deadline",
    "deadline_time",
    "deadline_kind",
    "deadline_evidence",
    "location",
    "location_evidence",
    "next_action_summary",
    "next_action_evidence",
    "reference_numbers",
    "reference_count",
    "reference_numbers_evidence",
    "detail_completeness",
}


def _sha256_hex(parts: object) -> str:
    if not isinstance(parts, list) or len(parts) != 8:
        raise ValueError("invalid MOEP reviewed document sha256 parts")
    values: list[int] = []
    for part in parts:
        if not isinstance(part, int) or part < 0 or part > 0xFFFFFFFF:
            raise ValueError("invalid MOEP reviewed document sha256 part")
        values.append(part)
    return "".join(f"{part:08x}" for part in values)


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != MOEP_REVIEWED_ENRICHMENT_VERSION:
        raise ValueError("invalid MOEP reviewed enrichment schema")
    records = raw.get("records")
    if not isinstance(records, dict):
        raise ValueError("invalid MOEP reviewed enrichment records")
    for canonical_key, value in records.items():
        if not isinstance(value, dict):
            raise ValueError("invalid MOEP reviewed enrichment record")
        newspaper_url = str(value.get("newspaper_url") or "")
        parsed = urlparse(newspaper_url)
        if parsed.scheme != "https" or parsed.hostname not in {"moi.gov.mm", "www.moi.gov.mm"}:
            raise ValueError("MOEP reviewed evidence must be hosted by MOI")
        _sha256_hex(value.get("document_sha256_u32be"))
        fields = value.get("fields")
        if not isinstance(fields, dict) or any(key not in _ALLOWED_FIELDS for key in fields):
            raise ValueError(f"invalid MOEP reviewed enrichment fields for {canonical_key}")
    return raw


def reviewed_moep_records(root: Path | None = None) -> dict[str, dict[str, object]]:
    raw = _load(str((root or repo_root()) / "registry" / _DATA_FILE))
    records = raw.get("records")
    assert isinstance(records, dict)
    result: dict[str, dict[str, object]] = {}
    for key, value in records.items():
        if not isinstance(value, dict):
            continue
        item = dict(value)
        item["document_sha256"] = _sha256_hex(item.get("document_sha256_u32be"))
        result[str(key)] = item
    return result


def reviewed_moep_overlay(
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    publication_date: object,
    article_url: object,
    attachment_name: object,
    root: Path | None = None,
) -> dict[str, object]:
    if source_id != "S20" or item_kind != "TENDER":
        return {}
    record = reviewed_moep_records(root).get(canonical_key)
    if not isinstance(record, dict):
        return {}
    if record.get("source_id") != source_id or record.get("item_kind") != item_kind:
        return {}
    if str(record.get("reference_no") or "") != str(reference_no or ""):
        return {}
    if str(record.get("publication_date") or "") != str(publication_date or ""):
        return {}
    if str(record.get("article_url") or "") != str(article_url or ""):
        return {}
    if str(record.get("attachment_name") or "") != str(attachment_name or ""):
        return {}
    fields = record.get("fields")
    assert isinstance(fields, dict)
    result = {key: value for key, value in fields.items() if key in _ALLOWED_FIELDS}
    result.update(
        {
            "reviewed_enrichment_version": MOEP_REVIEWED_ENRICHMENT_VERSION,
            "reviewed_enrichment_status": record.get("review_status"),
            "reviewed_enrichment_at": record.get("reviewed_at"),
            "reviewed_document_url": record.get("newspaper_url"),
            "reviewed_document_sha256": record.get("document_sha256"),
            "reviewed_document_page": record.get("newspaper_page"),
            "reviewed_document_date": record.get("newspaper_date"),
            "reviewed_enrichment_read_only": True,
        }
    )
    return result


def apply_reviewed_moep_overlay(
    payload: dict[str, object],
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    root: Path | None = None,
) -> dict[str, object]:
    overlay = reviewed_moep_overlay(
        canonical_key=canonical_key,
        source_id=source_id,
        item_kind=item_kind,
        reference_no=reference_no,
        publication_date=payload.get("publication_date"),
        article_url=payload.get("url"),
        attachment_name=payload.get("attachment_name"),
        root=root,
    )
    if not overlay:
        return payload
    enriched = dict(payload)
    for key, value in overlay.items():
        if key == "detail_completeness" or key.startswith("reviewed_") or not enriched.get(key):
            enriched[key] = value
    return enriched
