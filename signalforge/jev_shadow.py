from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Registry
from .mission_focus import MISSION_POLICY_VERSION, classify_mission_fit
from .opportunities import current_opportunities

JEV_SHADOW_VERSION = 0
DEFAULT_MODEL = "jev-latest"
DEFAULT_THRESHOLD = 0.60
SHADOW_AUTHORITY = "DETERMINISTIC_ONLY"
PRODUCTION_EFFECT = "NONE"

Evaluator = Callable[[dict[str, object]], dict[str, object]]


def _shadow_state(item: dict[str, object]) -> dict[str, object]:
    keys = (
        "source_id",
        "canonical_key",
        "item_kind",
        "issuer",
        "title",
        "project_name",
        "scope_summary",
        "focus_scope_summary",
        "reference_no",
        "location",
        "deadline",
        "deadline_time",
        "business_stage",
        "action_date",
        "action_time",
        "commercial_event_type",
        "commercial_direction",
        "primary_relevance",
        "relevance_categories",
        "quantity_or_lot_summary",
        "next_action_summary",
    )
    return {key: item.get(key) for key in keys if item.get(key) not in (None, "", [], {})}


def shadow_main_briefing(
    *,
    commercial_opportunity: float,
    sector: float,
    stage: str,
    threshold: float = DEFAULT_THRESHOLD,
) -> bool:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Jev shadow threshold must be between 0 and 1")
    return (
        commercial_opportunity >= threshold
        and sector >= threshold
        and stage == "open_opportunity"
    )


def _decision_label(*, deterministic: bool, shadow: bool) -> str:
    if deterministic and shadow:
        return "AGREE_INCLUDE"
    if deterministic and not shadow:
        return "DETERMINISTIC_ONLY"
    if not deterministic and shadow:
        return "JEV_ONLY"
    return "AGREE_EXCLUDE"


def _questions():
    try:
        from typesafe_sdk import Choice, Noul
    except ImportError as exc:  # pragma: no cover - exercised through explicit CLI runtime only
        raise RuntimeError(
            "Jev shadow mode requires the optional 'typesafe-sdk' package; "
            "core SignalForge does not depend on it"
        ) from exc

    return {
        "commercial_opportunity": Noul(
            instructions=(
                "At the record's publication/event stage, does this evidence describe a specific actionable "
                "commercial opportunity for an external business to participate, bid, supply, perform work, "
                "or buy/lease from the issuer? Include buyer-side procurement and seller-side open tender/"
                "auction/lease opportunities. Ignore whether a historical date has since passed. Exclude "
                "tentative programmes, awards/results, opening/evaluation meetings, jobs, policy, news, "
                "and completed workflow stages."
            )
        ),
        "procurement": Noul(
            instructions=(
                "At publication, does this evidence describe a buyer-side procurement/tender/RFP/RFQ/bid "
                "opportunity where the issuer seeks external goods, works, or services? Ignore whether a "
                "historical date has since passed. Exclude seller-side sales/auctions/leases, programmes, "
                "awards/results, opening/evaluation stages, jobs, policy and news."
            )
        ),
        "sector": Noul(
            instructions=(
                "Is the underlying business subject materially within SignalForge's MAIN mission: engineering "
                "projects/equipment/services; construction/civil/infrastructure works; telecommunications or "
                "ICT infrastructure; or energy/power/oil-and-gas infrastructure? Exclude medical procurement, "
                "books, office furniture/supplies, consumer/commercial goods, ordinary commodities/chemicals, "
                "tax/regulatory notices and unrelated administration. Judge actual scope, not merely issuer "
                "name. Mixed tenders count yes when a material lot is in the target sectors."
            )
        ),
        "stage": Choice(
            instructions=(
                "Classify the record's semantic workflow stage at publication. Ignore whether historical "
                "dates have since passed."
            ),
            criteria={
                "open_opportunity": (
                    "A specific open/actionable procurement or seller-side tender/auction/lease opportunity."
                ),
                "programme_or_preview": (
                    "A tentative programme, calendar, schedule or preview rather than a specific open opportunity."
                ),
                "strategic_intelligence": (
                    "Sector-relevant network/infrastructure/policy intelligence but not a commercial opportunity."
                ),
                "post_bid_workflow": (
                    "Tender opening, scrutiny, evaluation, award, result or other post-submission/completed stage."
                ),
                "regulatory_or_admin": (
                    "Regulatory, tax, company, compliance or administrative business notice; not procurement."
                ),
                "unrelated": "Jobs/recruitment or unrelated non-business content.",
                "noise": "Consumer/training/other low-value noise not fitting the categories above.",
            },
        ),
    }


def _typesafe_evaluator(*, model: str, api_key: str) -> tuple[Evaluator, Any]:
    try:
        from typesafe_sdk import TypeSafeClient
    except ImportError as exc:  # pragma: no cover - explicit runtime-only dependency
        raise RuntimeError(
            "Jev shadow mode requires the optional 'typesafe-sdk' package; "
            "core SignalForge does not depend on it"
        ) from exc

    client = TypeSafeClient(api_key=api_key, model=model)
    questions = _questions()

    def evaluate(state: dict[str, object]) -> dict[str, object]:
        result = client.system_one(state=state, questions=questions)
        return {
            "commercial_opportunity": float(result.nouls["commercial_opportunity"].noul),
            "procurement": float(result.nouls["procurement"].noul),
            "sector": float(result.nouls["sector"].noul),
            "stage": str(result.choices["stage"].choice),
            "stage_confidence": float(result.choices["stage"].confidence),
            "stage_probabilities": dict(result.choices["stage"].probabilities),
            "request_id": result.request_id,
            "model": result.model,
            "usage": result.usage.model_dump(),
        }

    return evaluate, client


def jev_shadow_report(
    *,
    database: Path | None = None,
    now: datetime | None = None,
    registry: Registry | None = None,
    include_expired: bool = False,
    limit: int = 50,
    threshold: float = DEFAULT_THRESHOLD,
    model: str = DEFAULT_MODEL,
    evaluator: Evaluator | None = None,
    api_key: str | None = None,
) -> dict[str, object]:
    if limit < 1 or limit > 500:
        raise ValueError("Jev shadow limit must be between 1 and 500")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Jev shadow threshold must be between 0 and 1")

    registry = registry or Registry.load()
    opportunities = current_opportunities(
        database=database,
        now=now,
        include_expired=include_expired,
        limit=limit,
        registry=registry,
    )
    tracked = opportunities.get("opportunities") or []
    if not isinstance(tracked, list):
        raise ValueError("current_opportunities returned an invalid opportunities payload")

    client = None
    if evaluator is None:
        resolved_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "Jev shadow mode requires TYPESAFE_API_KEY; no production credential fallback is allowed"
            )
        evaluator, client = _typesafe_evaluator(model=model, api_key=resolved_key)

    rows: list[dict[str, object]] = []
    try:
        for raw in tracked:
            if not isinstance(raw, dict):
                continue
            deterministic = classify_mission_fit(raw)
            jev = evaluator(_shadow_state(raw))
            commercial = float(jev["commercial_opportunity"])
            sector = float(jev["sector"])
            stage = str(jev["stage"])
            shadow = shadow_main_briefing(
                commercial_opportunity=commercial,
                sector=sector,
                stage=stage,
                threshold=threshold,
            )
            deterministic_include = bool(deterministic["mission_fit"])
            decision = _decision_label(deterministic=deterministic_include, shadow=shadow)
            rows.append(
                {
                    "source_id": raw.get("source_id"),
                    "canonical_key": raw.get("canonical_key"),
                    "title": raw.get("title") or raw.get("project_name"),
                    "deterministic": {
                        "main_briefing": deterministic_include,
                        "mission_sector": deterministic.get("mission_sector"),
                        "mission_reason": deterministic.get("mission_reason"),
                        "mission_policy_version": MISSION_POLICY_VERSION,
                    },
                    "jev": {
                        **jev,
                        "threshold": threshold,
                        "main_briefing": shadow,
                    },
                    "decision": decision,
                    "disagreement": decision in {"JEV_ONLY", "DETERMINISTIC_ONLY"},
                }
            )
    finally:
        if client is not None:
            client.close()

    disagreements = [row for row in rows if row["disagreement"]]
    return {
        "status": "SHADOW_ONLY",
        "shadow_version": JEV_SHADOW_VERSION,
        "authority": SHADOW_AUTHORITY,
        "production_effect": PRODUCTION_EFFECT,
        "model_requested": model,
        "threshold": threshold,
        "scope": {
            "surface": "CURRENT_OPPORTUNITY_MISSION_FILTER",
            "include_expired": include_expired,
            "limit": limit,
            "false_negative_coverage_outside_current_opportunities": "NOT_PROVEN",
        },
        "counts": {
            "tracked": len(tracked),
            "evaluated": len(rows),
            "deterministic_include": sum(1 for row in rows if row["deterministic"]["main_briefing"]),
            "jev_include": sum(1 for row in rows if row["jev"]["main_briefing"]),
            "agreements": len(rows) - len(disagreements),
            "disagreements": len(disagreements),
            "jev_only": sum(1 for row in rows if row["decision"] == "JEV_ONLY"),
            "deterministic_only": sum(1 for row in rows if row["decision"] == "DETERMINISTIC_ONLY"),
        },
        "rows": rows,
    }
