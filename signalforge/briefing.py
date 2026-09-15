from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .config import Registry
from .opportunities import current_opportunities

BRIEFING_POLICY_VERSION = 1


def _collapse(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _excerpt(value: object, limit: int = 1800) -> str:
    text = _collapse(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _attention_action(item: dict[str, object]) -> str:
    if item.get("priority_band") == "REVIEW":
        return "REVIEW"
    if item.get("urgency") == "URGENT":
        return "ACT_NOW"
    return "PRIORITIZE"


def _why_now(item: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    categories = {str(value) for value in (item.get("relevance_categories") or [])}
    if item.get("urgency") == "URGENT":
        reasons.append("COMMERCIAL_EVENT_WITHIN_72H" if item.get("item_kind") == "AUCTION_NOTICE" else "DEADLINE_WITHIN_72H")
    if {"ICT", "TELECOM"} & categories:
        reasons.append("STRATEGIC_FIT_ICT_TELECOM")
    if item.get("priority_band") == "REVIEW":
        reasons.append("HUMAN_REVIEW_REQUIRED")
    opportunity_status = item.get("opportunity_status") or item.get("deadline_status") or "UNKNOWN"
    if opportunity_status == "UNKNOWN":
        reasons.append("DEADLINE_UNKNOWN")
    elif item.get("item_kind") == "AUCTION_NOTICE" and item.get("action_date"):
        reasons.append("COMMERCIAL_EVENT_DATE_KNOWN")
    if item.get("trust_grade") == "A":
        reasons.append("A_GRADE_BUSINESS_EVIDENCE")
    elif item.get("trust_grade") == "B":
        reasons.append("TRUSTED_EVENT_PARTIAL_ACTIONABILITY")
    return reasons


def _attention_item(item: dict[str, object]) -> dict[str, object]:
    return {
        "canonical_key": item.get("canonical_key"),
        "source_id": item.get("source_id"),
        "item_kind": item.get("item_kind"),
        "commercial_event_type": item.get("commercial_event_type"),
        "commercial_direction": item.get("commercial_direction"),
        "attention_action": _attention_action(item),
        "priority_band": item.get("priority_band"),
        "trust_grade": item.get("trust_grade"),
        "signal_quality_model_version": item.get("signal_quality_model_version"),
        "signal_quality_score": item.get("signal_quality_score"),
        "signal_quality_band": item.get("signal_quality_band"),
        "signal_quality_dimensions": item.get("signal_quality_dimensions"),
        "signal_quality_strengths": item.get("signal_quality_strengths"),
        "signal_quality_gaps": item.get("signal_quality_gaps"),
        "signal_quality_priority_independent": item.get("signal_quality_priority_independent"),
        "primary_relevance": item.get("primary_relevance"),
        "relevance_categories": item.get("relevance_categories"),
        "urgency": item.get("urgency"),
        "issuer": item.get("issuer"),
        "title": item.get("title"),
        "reference_no": item.get("reference_no"),
        "reference_numbers": item.get("reference_numbers"),
        "focus_reference_numbers": item.get("focus_reference_numbers"),
        "focus_reference_count": item.get("focus_reference_count"),
        "focus_relevance": item.get("focus_relevance"),
        "deadline": item.get("deadline"),
        "deadline_time": item.get("deadline_time"),
        "deadline_kind": item.get("deadline_kind"),
        "tender_opening_date": item.get("tender_opening_date"),
        "tender_opening_time": item.get("tender_opening_time"),
        "deadline_at": item.get("deadline_at"),
        "deadline_status": item.get("deadline_status"),
        "action_date": item.get("action_date"),
        "action_time": item.get("action_time"),
        "action_date_kind": item.get("action_date_kind"),
        "action_at": item.get("action_at"),
        "opportunity_status": item.get("opportunity_status"),
        "evidence_level": item.get("evidence_level"),
        "completeness": item.get("completeness"),
        "scope_excerpt": _excerpt(item.get("focus_scope_summary") or item.get("scope_summary")),
        "location": item.get("location"),
        "location_evidence": item.get("location_evidence"),
        "quantity_or_lot_summary": item.get("quantity_or_lot_summary"),
        "quantity_or_lot_evidence": item.get("quantity_or_lot_evidence"),
        "quantity_or_lot_confidence": item.get("quantity_or_lot_confidence"),
        "next_action_summary": item.get("next_action_summary"),
        "next_action_evidence": item.get("next_action_evidence"),
        "reviewed_enrichment_status": item.get("reviewed_enrichment_status"),
        "reviewed_image_url": item.get("reviewed_image_url"),
        "reviewed_image_sha256": item.get("reviewed_image_sha256"),
        "reviewed_rules_url": item.get("reviewed_rules_url"),
        "why_now": _why_now(item),
        "latest_signal_id": item.get("latest_signal_id"),
        "latest_signal_type": item.get("latest_signal_type"),
        "latest_signal_at": item.get("latest_signal_at"),
        "signal_count": item.get("signal_count"),
        "url": item.get("url"),
    }


def business_briefing(
    *,
    database: Path | None = None,
    now: datetime | None = None,
    registry: Registry | None = None,
) -> dict[str, object]:
    opportunities = current_opportunities(database=database, now=now, registry=registry, limit=500)
    rows = opportunities.get("opportunities") or []
    assert isinstance(rows, list)

    attention_rows = [
        item
        for item in rows
        if isinstance(item, dict) and item.get("priority_band") in {"HIGH", "REVIEW"}
    ]
    watch_rows = [
        item
        for item in rows
        if isinstance(item, dict) and item.get("priority_band") == "MEDIUM"
    ]

    attention = [_attention_item(item) for item in attention_rows]
    action_counts = {
        action: sum(1 for item in attention if item.get("attention_action") == action)
        for action in ("ACT_NOW", "PRIORITIZE", "REVIEW")
    }
    watch_relevance: dict[str, int] = {}
    for item in watch_rows:
        category = str(item.get("primary_relevance") or "OTHER")
        watch_relevance[category] = watch_relevance.get(category, 0) + 1

    return {
        "status": "PASS",
        "briefing_policy_version": BRIEFING_POLICY_VERSION,
        "qualification_policy_version": opportunities.get("qualification_policy_version"),
        "as_of": opportunities.get("as_of"),
        "current_opportunities": opportunities.get("count"),
        "current_counts": opportunities.get("counts"),
        "qualification_counts": opportunities.get("qualification_counts"),
        "attention_count": len(attention),
        "attention_action_counts": action_counts,
        "attention": attention,
        "watchlist": {
            "priority_band": "MEDIUM",
            "count": len(watch_rows),
            "primary_relevance_counts": dict(sorted(watch_relevance.items())),
            "canonical_keys": [item.get("canonical_key") for item in watch_rows],
            "items": [_attention_item(item) for item in watch_rows[:5]],
        },
        "delivery_contract": {
            "generator": "external_agent_or_chatgpt",
            "recommended_order": ["ACT_NOW", "PRIORITIZE", "REVIEW"],
            "facts_must_not_be_inferred": True,
        },
    }
