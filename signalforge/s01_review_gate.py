"""Deterministic S01 OCR disposition. OCR is never sufficient for tender promotion."""
from __future__ import annotations

from typing import Any


def decide_s01_review(triage: dict[str, Any], *, official_image_verified: bool = False) -> dict[str, Any]:
    """Route obvious non-procurement away from owner review, fail closed otherwise.

    official_image_verified requires independent evidence verification, not an OCR
    confidence score. This gate does not authorize canonical tender creation.
    """
    classification = triage.get("classification")
    formal = triage.get("formal_procurement_tender")
    if classification == "GOVERNMENT_ASSET_LEASING" and formal is False:
        return {
            "disposition": "EXCLUDED_NON_PROCUREMENT",
            "requires_human_review": False,
            "canonical_promotion_allowed": False,
            "reason": "asset leasing is not procurement",
        }
    if classification == "GOVERNMENT_FUEL_PROCUREMENT" and formal is True:
        return {
            "disposition": "READY_FOR_OFFICIAL_EVIDENCE_CHECK" if official_image_verified else "OCR_REVIEW_REQUIRED",
            "requires_human_review": not official_image_verified,
            "canonical_promotion_allowed": False,
            "reason": "OCR fields require independent official evidence validation",
        }
    return {
        "disposition": "OCR_REVIEW_REQUIRED",
        "requires_human_review": True,
        "canonical_promotion_allowed": False,
        "reason": "procurement nature uncertain",
    }
