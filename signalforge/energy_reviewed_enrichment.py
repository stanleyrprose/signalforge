from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import repo_root

ENERGY_REVIEWED_ENRICHMENT_VERSION = 1
_DATA_FILE = "Energy-Reviewed-PDF-Enrichments-v1.json"
_ALLOWED_FIELDS = {
    "location",
    "location_evidence",
    "next_action_summary",
    "next_action_evidence",
    "detail_completeness",
}


def _valid_sha256(value: object) -> str:
    text = str(value or "").lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ValueError("invalid Energy reviewed document sha256")
    return text


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != ENERGY_REVIEWED_ENRICHMENT_VERSION:
        raise ValueError("invalid Energy reviewed enrichment schema")
    records = raw.get("records")
    if not isinstance(records, dict):
        raise ValueError("invalid Energy reviewed enrichment records")
    for canonical_key, value in records.items():
        if not isinstance(value, dict):
            raise ValueError("invalid Energy reviewed enrichment record")
        article = urlparse(str(value.get("article_url") or ""))
        attachment = urlparse(str(value.get("attachment_url") or ""))
        if article.scheme != "https" or article.hostname != "energy.gov.mm":
            raise ValueError("Energy reviewed article must be hosted by energy.gov.mm")
        if attachment.scheme != "https" or attachment.hostname != "energy.gov.mm":
            raise ValueError("Energy reviewed evidence must be hosted by energy.gov.mm")
        _valid_sha256(value.get("document_sha256"))
        fields = value.get("fields")
        if not isinstance(fields, dict) or any(key not in _ALLOWED_FIELDS for key in fields):
            raise ValueError(f"invalid Energy reviewed enrichment fields for {canonical_key}")
    return raw


def reviewed_energy_overlay(
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    publication_date: object,
    article_url: object,
    attachment_urls: object,
    evidence_sha256: object,
    root: Path | None = None,
) -> dict[str, object]:
    if source_id != "S39" or item_kind != "TENDER":
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
    if str(record.get("article_url") or "") != str(article_url or ""):
        return {}
    attachments = attachment_urls if isinstance(attachment_urls, list) else []
    if attachments != [record.get("attachment_url")]:
        return {}
    if _valid_sha256(record.get("document_sha256")) != str(evidence_sha256 or "").lower():
        return {}
    fields = record.get("fields")
    assert isinstance(fields, dict)
    result = {key: value for key, value in fields.items() if key in _ALLOWED_FIELDS}
    result.update(
        {
            "reviewed_enrichment_version": ENERGY_REVIEWED_ENRICHMENT_VERSION,
            "reviewed_enrichment_status": record.get("review_status"),
            "reviewed_enrichment_at": record.get("reviewed_at"),
            "reviewed_document_url": record.get("attachment_url"),
            "reviewed_document_sha256": record.get("document_sha256"),
            "reviewed_enrichment_read_only": True,
        }
    )
    return result


def apply_reviewed_energy_overlay(
    payload: dict[str, object],
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    evidence_sha256: object,
    root: Path | None = None,
) -> dict[str, object]:
    overlay = reviewed_energy_overlay(
        canonical_key=canonical_key,
        source_id=source_id,
        item_kind=item_kind,
        reference_no=reference_no,
        publication_date=payload.get("publication_date"),
        article_url=payload.get("url"),
        attachment_urls=payload.get("attachment_urls"),
        evidence_sha256=evidence_sha256,
        root=root,
    )
    if not overlay:
        return payload
    enriched = dict(payload)
    for key, value in overlay.items():
        if key == "detail_completeness" or key.startswith("reviewed_") or not enriched.get(key):
            enriched[key] = value
    return enriched
