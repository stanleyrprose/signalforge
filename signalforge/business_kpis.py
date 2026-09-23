from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .assurance import assurance_status
from .config import Registry, db_path
from .coverage_gaps import verified_external_opportunities
from .db import connect
from .leadtime import leadtime_report
from .mission_focus import classify_mission_fit
from .opportunities import current_opportunities

QUALITY_BANDS = ("VERY_HIGH", "HIGH", "MEDIUM", "REVIEW", "LOW")


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _median(values: list[int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    value = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    return round(float(value), 1)


def _dimension_score(item: dict[str, object], name: str) -> int:
    dimensions = item.get("signal_quality_dimensions")
    if not isinstance(dimensions, dict):
        return 0
    dimension = dimensions.get(name)
    if not isinstance(dimension, dict):
        return 0
    try:
        return int(dimension.get("score") or 0)
    except (TypeError, ValueError):
        return 0


def _verified_external_proof_complete(item: dict[str, object]) -> bool:
    sha = str(item.get("document_sha256") or "")
    return (
        item.get("issuer_document_verified") is True
        and item.get("issuer_identity_verified") is True
        and item.get("scope_verified") is True
        and item.get("deadline_verified") is True
        and item.get("canonical_truth") is False
        and len(sha) == 64
        and all(char in "0123456789abcdef" for char in sha.lower())
    )


def summarize_opportunity_quality(
    *,
    canonical_rows: list[dict[str, object]],
    verified_external_rows: list[dict[str, object]],
    assurance: dict[str, object],
) -> dict[str, object]:
    scores = [
        int(item["signal_quality_score"])
        for item in canonical_rows
        if isinstance(item.get("signal_quality_score"), (int, float))
    ]
    band_counts = {
        band: sum(1 for item in canonical_rows if str(item.get("signal_quality_band") or "") == band)
        for band in QUALITY_BANDS
    }
    trust_counts = {
        grade: sum(1 for item in canonical_rows if str(item.get("trust_grade") or "") == grade)
        for grade in ("A", "B", "C")
    }
    scored = len(scores)
    high_quality = band_counts["VERY_HIGH"] + band_counts["HIGH"]
    review_or_low = band_counts["REVIEW"] + band_counts["LOW"]
    timeframe_known = sum(1 for item in canonical_rows if _dimension_score(item, "time") > 0)
    next_action_known = sum(1 for item in canonical_rows if _dimension_score(item, "next_action") >= 10)
    official_evidence = sum(1 for item in canonical_rows if _dimension_score(item, "official_evidence") >= 10)

    verified_complete = sum(1 for item in verified_external_rows if _verified_external_proof_complete(item))

    latest_review = assurance.get("latest_metric_review")
    latest_review = latest_review if isinstance(latest_review, dict) else {}
    review_metrics = latest_review.get("metrics")
    review_metrics = review_metrics if isinstance(review_metrics, dict) else {}
    counts = assurance.get("counts")
    counts = counts if isinstance(counts, dict) else {}

    return {
        "business_current_opportunities": len(canonical_rows) + len(verified_external_rows),
        "canonical_current_opportunities": len(canonical_rows),
        "verified_external_current_opportunities": len(verified_external_rows),
        "canonical_signal_quality": {
            "scored_opportunities": scored,
            "unscored_opportunities": len(canonical_rows) - scored,
            "score_average": round(sum(scores) / scored, 1) if scored else None,
            "score_median": _median(scores),
            "band_counts": band_counts,
            "high_or_very_high_count": high_quality,
            "high_or_very_high_rate": _rate(high_quality, scored),
            "review_or_low_count": review_or_low,
            "review_or_low_rate": _rate(review_or_low, scored),
            "trust_grade_counts": trust_counts,
            "trust_a_rate": _rate(trust_counts["A"], len(canonical_rows)),
            "timeframe_known_count": timeframe_known,
            "timeframe_known_rate": _rate(timeframe_known, len(canonical_rows)),
            "explicit_next_action_count": next_action_known,
            "explicit_next_action_rate": _rate(next_action_known, len(canonical_rows)),
            "official_evidence_count": official_evidence,
            "official_evidence_rate": _rate(official_evidence, len(canonical_rows)),
        },
        "verified_external_quality": {
            "proof_complete_count": verified_complete,
            "proof_complete_rate": _rate(verified_complete, len(verified_external_rows)),
            "signal_quality_score_assigned": False,
            "policy": "STRICT_REVIEWED_OFFICIAL_EVIDENCE_WITHOUT_CANONICAL_SIGNAL_STATUS",
        },
        "assurance": {
            "metric_validity": latest_review.get("status") or "NOT_RUN",
            "metric_reviewed_at": latest_review.get("observed_at"),
            "mandatory_coverage_proof_rate": review_metrics.get("mandatory_coverage_proof_rate"),
            "mandatory_business_coverage_accounted_rate": review_metrics.get(
                "mandatory_business_coverage_accounted_rate"
            ),
            "open_misses": counts.get("open_misses", review_metrics.get("open_misses")),
            "open_red_misses": counts.get("open_red_misses", review_metrics.get("open_red_misses")),
            "coverage_risk_count": assurance.get("coverage_risk_count"),
            "noise_samples_conclusive_window": review_metrics.get("noise_samples_conclusive_window"),
            "noise_false_negatives_window": review_metrics.get("noise_false_negatives_window"),
            "noise_false_negative_rate": review_metrics.get("noise_false_negative_rate"),
        },
        "semantics": {
            "no_opaque_composite_score": True,
            "signal_quality_measures": "EVIDENCE_COMPLETENESS_AND_BUSINESS_ACTIONABILITY",
            "signal_quality_is_not_false_positive_precision": True,
            "noise_false_negative_rate_scope": "CONCLUSIVE_REVIEWED_NOISE_SAMPLES_ONLY",
            "verified_external_kept_separate_from_canonical_signal_scoring": True,
        },
    }


def business_kpi_report(
    *,
    database: Path | None = None,
    now: datetime | None = None,
    registry: Registry | None = None,
    lead_limit: int = 100,
) -> dict[str, object]:
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    target = database or db_path()
    registry = registry or Registry.load()

    current = current_opportunities(
        database=target,
        now=observed,
        registry=registry,
        limit=500,
    )
    raw_rows = current.get("opportunities") or []
    canonical_rows: list[dict[str, object]] = []
    with connect(target) as conn:
        canonical_urls = {
            str(row[0]).rstrip("/")
            for row in conn.execute("SELECT url FROM canonical_items WHERE url IS NOT NULL")
            if row[0]
        }
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        mission = classify_mission_fit(raw)
        if mission["mission_fit"]:
            canonical_rows.append({**raw, **mission})

    external_rows: list[dict[str, object]] = []
    for raw in verified_external_opportunities(now=observed):
        url = str(raw.get("url") or "").rstrip("/")
        if url and url in canonical_urls:
            continue
        mission = classify_mission_fit(
            {
                **raw,
                "source_id": str(raw.get("target_source_id") or raw.get("source_id") or ""),
                "item_kind": str(raw.get("item_kind") or "TENDER"),
                "scope_summary": raw.get("business_summary"),
            }
        )
        if mission["mission_fit"]:
            external_rows.append({**raw, **mission})

    assurance = assurance_status(database=target, registry=registry)
    return {
        "metric": "SIGNALFORGE_CORE_BUSINESS_KPIS",
        "as_of": observed.isoformat().replace("+00:00", "Z"),
        "opportunity_output_quality": summarize_opportunity_quality(
            canonical_rows=canonical_rows,
            verified_external_rows=external_rows,
            assurance=assurance,
        ),
        "project_to_procurement_lead_time": leadtime_report(database=target, limit=lead_limit),
    }
