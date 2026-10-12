"""Read-only canonical tender field-quality audit; never equate unknown with undisclosed."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .config import Registry, db_path
from .db import connect
from .moep_reviewed_enrichment import apply_reviewed_moep_overlay

_QUANTITY_FIELDS = ("required_quantity", "quantity", "quantities", "lots", "quantity_or_lot_summary")
_ITEM_FIELDS = ("scope_summary", "project_name", "required_items", "items")
_UNKNOWN = ("not disclosed", "not specified", "not available", "unknown", "未披露", "未说明", "未提供", "详见官方原文")
_UNDISCLOSED = ("not disclosed", "not specified", "未披露", "未说明")
_EVIDENCE_FIELDS = ("source_document_sha256", "reviewed_attachment_status", "attachment_url", "document_url", "pdf_url")


def _text(value: object) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value or "").strip()


def _has_fact(value: object) -> bool:
    text = _text(value).strip()
    return bool(text) and not any(marker in text.lower() for marker in _UNKNOWN)


def _missing_reason(payload: dict[str, object], field: str, values: list[object]) -> str:
    if any(any(marker in _text(value).lower() for marker in _UNDISCLOSED) for value in values):
        return "SOURCE_NOT_DISCLOSED_CLAIM"
    if field == "quantity" and payload.get("reviewed_attachment_status"):
        return "REVIEWED_ATTACHMENT_NOT_NORMALIZED"
    if any(payload.get(key) for key in _EVIDENCE_FIELDS):
        return "DOCUMENT_REVIEW_REQUIRED"
    return "NOT_EXTRACTED_OR_UNAVAILABLE"


def tender_quality(*, database: Path | None = None, registry: Registry | None = None) -> dict[str, object]:
    """Audit extracted facts, not whether the original tender actually contained them.

    Missing fields are diagnostic and do not suppress formal tender delivery.
    A 'source not disclosed' statement remains an unverified claim until source review.
    """
    registry = registry or Registry.load()
    sources = registry.raw["sources"]
    results = {
        sid: {
            "source_id": sid, "status": "NO_OBSERVED_TENDERS", "observed": 0,
            "complete": 0, "reviewed_overlay_complete": 0, "examples": [],
            "missing": {"item": 0, "quantity": 0, "deadline": 0},
            "missing_reasons": {"item": {}, "quantity": {}, "deadline": {}},
        }
        for sid, cfg in sources.items()
        if cfg.get("enabled") is True and cfg.get("item_kind") == "TENDER"
    }
    with connect(database or db_path()) as conn:
        for row in conn.execute(
            "SELECT source_id,canonical_key,url,payload_json,deadline FROM canonical_items WHERE item_kind='TENDER'"
        ):
            sid = str(row["source_id"])
            if sid not in results:
                continue
            result = results[sid]
            result["observed"] += 1
            try:
                payload = json.loads(row["payload_json"] or "{}")
                if not isinstance(payload, dict):
                    payload = {}
            except (ValueError, TypeError):
                payload = {}
            reviewed_overlay_applied = False
            if sid == "S20":
                original = payload
                payload = apply_reviewed_moep_overlay(
                    payload,
                    canonical_key=str(row["canonical_key"]),
                    source_id=sid,
                    item_kind="TENDER",
                    reference_no=str(payload.get("reference_no") or ""),
                )
                reviewed_overlay_applied = payload is not original and bool(
                    payload.get("reviewed_attachment_status") or payload.get("reviewed_enrichment_status")
                )
            values = {
                "item": [payload.get(k) for k in _ITEM_FIELDS],
                "quantity": [payload.get(k) for k in _QUANTITY_FIELDS],
                "deadline": [row["deadline"], payload.get("deadline")],
            }
            missing = [field for field, candidates in values.items() if not any(_has_fact(v) for v in candidates)]
            reasons = {}
            for field in missing:
                result["missing"][field] += 1
                reason = _missing_reason(payload, field, values[field])
                bucket = result["missing_reasons"][field]
                bucket[reason] = bucket.get(reason, 0) + 1
                reasons[field] = reason
            if not missing:
                result["complete"] += 1
                if reviewed_overlay_applied:
                    result["reviewed_overlay_complete"] += 1
            if len(result["examples"]) < 3:
                result["examples"].append({
                    "canonical_key": row["canonical_key"], "url": row["url"],
                    "missing": missing, "missing_reasons": reasons,
                })
    for result in results.values():
        if result["observed"]:
            result["status"] = "COMPLETE_OBSERVED" if result["complete"] == result["observed"] else "INCOMPLETE_OBSERVED"
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "definition": "same canonical tender: item + actual quantity/lot + deadline, including identity-matched reviewed S20 evidence",
        "source_count": len(results), "sources": list(results.values()),
        "limitation": "Canonical database with existing identity-matched S20 reviewed overlays; reviewed_overlay_complete counts complete tenders with reviewed overlays applied, not proof that the overlay supplied each field. Other source PDFs and unreviewed source-not-disclosed claims remain unverified.",
    }
