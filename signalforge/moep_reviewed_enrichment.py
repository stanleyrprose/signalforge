from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import repo_root

MOEP_REVIEWED_ENRICHMENT_VERSION = 1
_DATA_FILE = "MOEP-Reviewed-Official-Newspaper-Enrichments-v1.json"
_ATTACHMENT_DATA_FILE = "MOEP-Reviewed-Official-Attachment-Enrichments-v1.json"
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
    "scope_summary",
    "quantity_or_lot_summary",
    "quantity_or_lot_evidence",
    "quantity_or_lot_confidence",
}
_REVIEWED_BUSINESS_OVERRIDE_FIELDS = {
    "scope_summary",
    "quantity_or_lot_summary",
    "quantity_or_lot_evidence",
    "quantity_or_lot_confidence",
    "reference_numbers",
    "reference_count",
    "reference_numbers_evidence",
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


def _validate_fields(canonical_key: str, value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(key not in _ALLOWED_FIELDS for key in value):
        raise ValueError(f"invalid MOEP reviewed enrichment fields for {canonical_key}")
    return value


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
        _validate_fields(str(canonical_key), value.get("fields"))
    return raw


@lru_cache(maxsize=4)
def _load_attachment(path: str) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != MOEP_REVIEWED_ENRICHMENT_VERSION:
        raise ValueError("invalid MOEP reviewed attachment enrichment schema")
    records = raw.get("records")
    if not isinstance(records, dict):
        raise ValueError("invalid MOEP reviewed attachment enrichment records")
    for canonical_key, value in records.items():
        if not isinstance(value, dict):
            raise ValueError("invalid MOEP reviewed attachment enrichment record")
        attachment_url = str(value.get("attachment_url") or "")
        parsed = urlparse(attachment_url)
        if parsed.scheme != "https" or parsed.hostname not in {"moep.gov.mm", "www.moep.gov.mm"}:
            raise ValueError("MOEP reviewed attachment evidence must be hosted by MOEP")
        digest = str(value.get("document_sha256") or "")
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("invalid MOEP reviewed attachment sha256")
        _validate_fields(str(canonical_key), value.get("fields"))
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


def reviewed_moep_attachment_records(root: Path | None = None) -> dict[str, dict[str, object]]:
    raw = _load_attachment(str((root or repo_root()) / "registry" / _ATTACHMENT_DATA_FILE))
    records = raw.get("records")
    assert isinstance(records, dict)
    return {str(key): dict(value) for key, value in records.items() if isinstance(value, dict)}


def _identity_matches(
    record: dict[str, object],
    *,
    source_id: str,
    item_kind: str,
    reference_no: str | None,
    publication_date: object,
    article_url: object,
    attachment_name: object,
) -> bool:
    return (
        record.get("source_id") == source_id
        and record.get("item_kind") == item_kind
        and str(record.get("reference_no") or "") == str(reference_no or "")
        and str(record.get("publication_date") or "") == str(publication_date or "")
        and str(record.get("article_url") or "") == str(article_url or "")
        and str(record.get("attachment_name") or "") == str(attachment_name or "")
    )


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

    result: dict[str, object] = {}
    newspaper = reviewed_moep_records(root).get(canonical_key)
    if isinstance(newspaper, dict) and _identity_matches(
        newspaper,
        source_id=source_id,
        item_kind=item_kind,
        reference_no=reference_no,
        publication_date=publication_date,
        article_url=article_url,
        attachment_name=attachment_name,
    ):
        fields = newspaper.get("fields")
        assert isinstance(fields, dict)
        result.update({key: value for key, value in fields.items() if key in _ALLOWED_FIELDS})
        result.update(
            {
                "reviewed_enrichment_version": MOEP_REVIEWED_ENRICHMENT_VERSION,
                "reviewed_enrichment_status": newspaper.get("review_status"),
                "reviewed_enrichment_at": newspaper.get("reviewed_at"),
                "reviewed_document_url": newspaper.get("newspaper_url"),
                "reviewed_document_sha256": newspaper.get("document_sha256"),
                "reviewed_document_page": newspaper.get("newspaper_page"),
                "reviewed_document_date": newspaper.get("newspaper_date"),
                "reviewed_enrichment_read_only": True,
            }
        )

    attachment = reviewed_moep_attachment_records(root).get(canonical_key)
    if isinstance(attachment, dict) and _identity_matches(
        attachment,
        source_id=source_id,
        item_kind=item_kind,
        reference_no=reference_no,
        publication_date=publication_date,
        article_url=article_url,
        attachment_name=attachment_name,
    ):
        fields = attachment.get("fields")
        assert isinstance(fields, dict)
        for key, value in fields.items():
            if key in _ALLOWED_FIELDS and (key in _REVIEWED_BUSINESS_OVERRIDE_FIELDS or not result.get(key)):
                result[key] = value
        result.update(
            {
                "reviewed_attachment_status": attachment.get("review_status"),
                "reviewed_attachment_at": attachment.get("reviewed_at"),
                "reviewed_attachment_url": attachment.get("attachment_url"),
                "reviewed_attachment_sha256": attachment.get("document_sha256"),
                "reviewed_attachment_read_only": True,
            }
        )
        if not result.get("reviewed_enrichment_status"):
            result["reviewed_enrichment_version"] = MOEP_REVIEWED_ENRICHMENT_VERSION
            result["reviewed_enrichment_status"] = attachment.get("review_status")
            result["reviewed_enrichment_at"] = attachment.get("reviewed_at")
            result["reviewed_enrichment_read_only"] = True

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
        if (
            key == "detail_completeness"
            or key.startswith("reviewed_")
            or key in _REVIEWED_BUSINESS_OVERRIDE_FIELDS
            or not enriched.get(key)
        ):
            enriched[key] = value
    return enriched
