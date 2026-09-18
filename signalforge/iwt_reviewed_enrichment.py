from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import repo_root

IWT_REVIEWED_ENRICHMENT_VERSION = 1
_DATA_FILE = "IWT-Reviewed-OCR-Enrichments-v1.json"
_ALLOWED_FIELDS = {
    "location",
    "location_evidence",
    "next_action_summary",
    "next_action_evidence",
    "detail_completeness",
}


def _valid_sha256(value: object, *, label: str) -> str:
    text = str(value or "").lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"invalid IWT reviewed {label} sha256")
    return text


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != IWT_REVIEWED_ENRICHMENT_VERSION:
        raise ValueError("invalid IWT reviewed enrichment schema")
    records = raw.get("records")
    if not isinstance(records, dict):
        raise ValueError("invalid IWT reviewed enrichment records")
    for canonical_key, value in records.items():
        if not isinstance(value, dict):
            raise ValueError("invalid IWT reviewed enrichment record")
        article = urlparse(str(value.get("article_url") or ""))
        attachment = urlparse(str(value.get("attachment_url") or ""))
        if article.scheme != "https" or article.hostname not in {"iwt.gov.mm", "www.iwt.gov.mm"}:
            raise ValueError("IWT reviewed article must be hosted by iwt.gov.mm")
        if attachment.scheme != "https" or attachment.hostname not in {"iwt.gov.mm", "www.iwt.gov.mm"}:
            raise ValueError("IWT reviewed evidence must be hosted by iwt.gov.mm")
        if value.get("article_html_identity_policy") != "NOT_HASH_GATED_CLOUDFLARE_DYNAMIC_PARAMS":
            raise ValueError("invalid IWT reviewed article HTML identity policy")
        _valid_sha256(value.get("document_sha256"), label="document")
        _valid_sha256(value.get("rendered_image_sha256"), label="rendered image")
        fields = value.get("fields")
        if not isinstance(fields, dict) or any(key not in _ALLOWED_FIELDS for key in fields):
            raise ValueError(f"invalid IWT reviewed enrichment fields for {canonical_key}")
    return raw


def reviewed_iwt_overlay(
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    publication_date: object,
    article_url: object,
    attachment_url: object,
    root: Path | None = None,
) -> dict[str, object]:
    if source_id != "S22" or item_kind != "TENDER":
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
    if str(record.get("attachment_url") or "") != str(attachment_url or ""):
        return {}

    fields = record.get("fields")
    assert isinstance(fields, dict)
    result = {key: value for key, value in fields.items() if key in _ALLOWED_FIELDS}
    result.update(
        {
            "reviewed_enrichment_version": IWT_REVIEWED_ENRICHMENT_VERSION,
            "reviewed_enrichment_status": record.get("review_status"),
            "reviewed_enrichment_at": record.get("reviewed_at"),
            "reviewed_document_url": record.get("attachment_url"),
            "reviewed_document_sha256": record.get("document_sha256"),
            "reviewed_rendered_image_sha256": record.get("rendered_image_sha256"),
            "reviewed_ocr": record.get("ocr"),
            "reviewed_enrichment_read_only": True,
        }
    )
    return result


def apply_reviewed_iwt_overlay(
    payload: dict[str, object],
    *,
    canonical_key: str,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    root: Path | None = None,
) -> dict[str, object]:
    overlay = reviewed_iwt_overlay(
        canonical_key=canonical_key,
        source_id=source_id,
        item_kind=item_kind,
        reference_no=reference_no,
        publication_date=payload.get("publication_date"),
        article_url=payload.get("url"),
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
