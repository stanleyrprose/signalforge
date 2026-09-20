from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .assurance import _normalize_url
from .config import db_path, evidence_root
from .jev_noise_shadow import (
    DEFAULT_MODEL,
    DEFAULT_OPEN_THRESHOLD,
    DEFAULT_SECTOR_THRESHOLD,
    NoiseEvaluator,
    _html_text,
    _typesafe_noise_evaluator,
    noise_review_recommended,
)

TRIAGE_VERSION = 0
AUTHORITY = "HUMAN_REVIEW_REQUIRED"
PRODUCTION_EFFECT = "NONE"
WRITES = "NONE"


def _artifact_path(
    *,
    evidence_directory: Path,
    source_id: str,
    artifact_sha256: str,
    artifact_media_type: str,
) -> Path | None:
    if not artifact_sha256:
        return None
    suffix = ".pdf" if "pdf" in artifact_media_type.lower() else ".html"
    path = evidence_directory / source_id / f"{artifact_sha256}{suffix}"
    return path if path.is_file() else None


def _existing_review_keys(conn: sqlite3.Connection) -> set[tuple[str, str, str]]:
    return {
        (str(row["source_id"]), str(row["candidate_kind"]), str(row["candidate_ref"]))
        for row in conn.execute(
            "SELECT source_id,candidate_kind,candidate_ref FROM noise_review_samples"
        )
    }


def _existing_reviewed_artifacts(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    reviewed: set[tuple[str, str]] = set()
    for row in conn.execute(
        "SELECT source_id,payload_json FROM noise_review_samples WHERE candidate_kind='ZERO_ITEM_PROCESSING'"
    ):
        try:
            payload = json.loads(str(row["payload_json"] or "{}"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        artifact_sha = str(payload.get("artifact_sha256") or "")
        if artifact_sha:
            reviewed.add((str(row["source_id"]), artifact_sha))
    return reviewed


def _parse_time(value: object) -> datetime:
    text = str(value or "")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)


def _candidate_pool(
    *,
    database: Path,
    evidence_directory: Path,
    candidate_limit: int,
    per_source_cap: int = 5,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    if candidate_limit < 1 or candidate_limit > 200:
        raise ValueError("Jev noise-triage candidate limit must be between 1 and 200")
    if per_source_cap < 1 or per_source_cap > 50:
        raise ValueError("Jev noise-triage per-source cap must be between 1 and 50")

    uri = f"file:{database}?mode=ro"
    candidates: list[dict[str, object]] = []
    counters = {
        "zero_item_rows_scanned": 0,
        "zero_item_existing_review": 0,
        "zero_item_existing_review_artifact": 0,
        "zero_item_recovered_later": 0,
        "zero_item_duplicate_artifact": 0,
        "zero_item_missing_evidence": 0,
        "zero_item_unsupported_evidence": 0,
        "nonstandard_rows_scanned": 0,
        "nonstandard_existing_review": 0,
    }

    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        existing = _existing_review_keys(conn)
        reviewed_artifacts = _existing_reviewed_artifacts(conn)

        seen_artifacts: set[tuple[str, str]] = set()
        zero_rows = conn.execute(
            """
            SELECT
                p.processing_id,p.source_id,p.parser_version,p.finished_at,
                e.requested_url,e.final_url,e.artifact_sha256,e.artifact_media_type,
                EXISTS(
                    SELECT 1
                    FROM processing_records p2
                    JOIN evidence_envelopes e2 ON e2.evidence_id=p2.evidence_id
                    WHERE p2.source_id=p.source_id
                      AND p2.status='SUCCESS'
                      AND p2.items_found>0
                      AND p2.finished_at>p.finished_at
                      AND COALESCE(e2.final_url,e2.requested_url)=COALESCE(e.final_url,e.requested_url)
                ) AS recovered_later
            FROM processing_records p
            JOIN evidence_envelopes e ON e.evidence_id=p.evidence_id
            WHERE p.status='SUCCESS' AND p.items_found=0
            ORDER BY p.finished_at DESC
            """
        ).fetchall()
        for row in zero_rows:
            counters["zero_item_rows_scanned"] += 1
            source_id = str(row["source_id"])
            ref = f"processing:{row['processing_id']}"
            key = (source_id, "ZERO_ITEM_PROCESSING", ref)
            if key in existing:
                counters["zero_item_existing_review"] += 1
                continue
            if bool(row["recovered_later"]):
                counters["zero_item_recovered_later"] += 1
                continue

            artifact_sha = str(row["artifact_sha256"] or "")
            artifact_key = (source_id, artifact_sha)
            if artifact_key in reviewed_artifacts:
                counters["zero_item_existing_review_artifact"] += 1
                continue
            if artifact_key in seen_artifacts:
                counters["zero_item_duplicate_artifact"] += 1
                continue
            seen_artifacts.add(artifact_key)

            media_type = str(row["artifact_media_type"] or "")
            artifact = _artifact_path(
                evidence_directory=evidence_directory,
                source_id=source_id,
                artifact_sha256=artifact_sha,
                artifact_media_type=media_type,
            )
            if artifact is None:
                counters["zero_item_missing_evidence"] += 1
                continue
            if artifact.suffix.lower() not in {".html", ".htm"}:
                counters["zero_item_unsupported_evidence"] += 1
                continue

            evidence_text = _html_text(artifact)
            if not evidence_text:
                counters["zero_item_missing_evidence"] += 1
                continue

            processed_at = str(row["finished_at"] or "")
            candidates.append(
                {
                    "source_id": source_id,
                    "candidate_kind": "ZERO_ITEM_PROCESSING",
                    "candidate_ref": ref,
                    "evidence_url": str(row["final_url"] or row["requested_url"] or "") or None,
                    "observed_at": processed_at,
                    "artifact_sha256": artifact_sha,
                    "state": {
                        "source_id": source_id,
                        "candidate_kind": "ZERO_ITEM_PROCESSING",
                        "evidence_url": str(row["final_url"] or row["requested_url"] or "") or None,
                        "processed_at": processed_at,
                        "artifact_sha256": artifact_sha,
                        "evidence_text": evidence_text,
                    },
                }
            )

        seen_nonstandard_sources: set[str] = set()
        audit_rows = conn.execute(
            """
            SELECT source_id,checked_at,details_json
            FROM coverage_audit_results
            ORDER BY checked_at DESC
            """
        ).fetchall()
        for audit in audit_rows:
            source_id = str(audit["source_id"])
            if source_id in seen_nonstandard_sources:
                continue
            seen_nonstandard_sources.add(source_id)
            try:
                details = json.loads(str(audit["details_json"] or "{}"))
            except json.JSONDecodeError:
                continue
            rows = details.get("nonstandard_candidates") if isinstance(details, dict) else None
            if not isinstance(rows, list):
                continue
            for item in rows:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url") or "")
                title = str(item.get("title") or "").strip()
                if not url or not title:
                    continue
                counters["nonstandard_rows_scanned"] += 1
                ref = f"url:{_normalize_url(url)}"
                key = (source_id, "INDEPENDENT_LISTING_NONSTANDARD", ref)
                if key in existing:
                    counters["nonstandard_existing_review"] += 1
                    continue
                observed_at = str(audit["checked_at"] or "")
                candidates.append(
                    {
                        "source_id": source_id,
                        "candidate_kind": "INDEPENDENT_LISTING_NONSTANDARD",
                        "candidate_ref": ref,
                        "evidence_url": url,
                        "observed_at": observed_at,
                        "artifact_sha256": None,
                        "state": {
                            "source_id": source_id,
                            "candidate_kind": "INDEPENDENT_LISTING_NONSTANDARD",
                            "evidence_url": url,
                            "processed_at": observed_at,
                            "title": title,
                            "listing_url": url,
                        },
                    }
                )

    candidates.sort(
        key=lambda row: (
            _parse_time(row.get("observed_at")),
            str(row.get("source_id") or ""),
            str(row.get("candidate_ref") or ""),
        ),
        reverse=True,
    )
    bounded: list[dict[str, object]] = []
    source_counts: dict[str, int] = {}
    source_cap_excluded = 0
    for row in candidates:
        source_id = str(row.get("source_id") or "")
        if source_counts.get(source_id, 0) >= per_source_cap:
            source_cap_excluded += 1
            continue
        bounded.append(row)
        source_counts[source_id] = source_counts.get(source_id, 0) + 1
        if len(bounded) >= candidate_limit:
            break
    counters["source_cap_excluded"] = source_cap_excluded
    counters["bounded_source_counts"] = source_counts
    return bounded, counters


def _rank_key(row: dict[str, object]) -> tuple[float, float, float, float, str]:
    jev = row["jev"]
    assert isinstance(jev, dict)
    open_actionable = float(jev["open_actionable"])
    mission_sector = float(jev["mission_sector"])
    page_state = str(jev["page_state"])
    return (
        1.0 if bool(row["review_recommended"]) else 0.0,
        1.0 if page_state == "contains_open_opportunity" else 0.0,
        min(open_actionable, mission_sector),
        max(open_actionable, mission_sector),
        str(row.get("observed_at") or ""),
    )


def jev_noise_triage_report(
    *,
    database: Path | None = None,
    evidence_directory: Path | None = None,
    candidate_limit: int = 30,
    per_source_cap: int = 5,
    top: int = 10,
    open_threshold: float = DEFAULT_OPEN_THRESHOLD,
    sector_threshold: float = DEFAULT_SECTOR_THRESHOLD,
    model: str = DEFAULT_MODEL,
    evaluator: NoiseEvaluator | None = None,
    api_key: str | None = None,
) -> dict[str, object]:
    if top < 1 or top > candidate_limit:
        raise ValueError("Jev noise-triage top must be between 1 and candidate_limit")
    if not 0.0 <= open_threshold <= 1.0:
        raise ValueError("Jev noise-triage open threshold must be between 0 and 1")
    if not 0.0 <= sector_threshold <= 1.0:
        raise ValueError("Jev noise-triage sector threshold must be between 0 and 1")

    target = database or db_path()
    evidence_dir = evidence_directory or evidence_root()
    candidates, pool_counters = _candidate_pool(
        database=target,
        evidence_directory=evidence_dir,
        candidate_limit=candidate_limit,
        per_source_cap=per_source_cap,
    )

    client = None
    if evaluator is None:
        resolved_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "Jev noise-triage mode requires TYPESAFE_API_KEY; "
                "no production credential fallback is allowed"
            )
        evaluator, client = _typesafe_noise_evaluator(model=model, api_key=resolved_key)

    rows: list[dict[str, object]] = []
    try:
        for candidate in candidates:
            state = candidate["state"]
            assert isinstance(state, dict)
            jev = evaluator(state)
            open_actionable = float(jev["open_actionable"])
            mission_sector = float(jev["mission_sector"])
            page_state = str(jev["page_state"])
            recommended = noise_review_recommended(
                open_actionable=open_actionable,
                mission_sector=mission_sector,
                page_state=page_state,
                open_threshold=open_threshold,
                sector_threshold=sector_threshold,
            )
            risk_floor = (
                min(open_actionable, mission_sector)
                if page_state == "contains_open_opportunity"
                else 0.0
            )
            rows.append(
                {
                    "source_id": candidate["source_id"],
                    "candidate_kind": candidate["candidate_kind"],
                    "candidate_ref": candidate["candidate_ref"],
                    "evidence_url": candidate["evidence_url"],
                    "observed_at": candidate["observed_at"],
                    "artifact_sha256": candidate["artifact_sha256"],
                    "review_recommended": recommended,
                    "recommendation": (
                        "REVIEW_RECOMMENDED" if recommended else "LOWER_PRIORITY"
                    ),
                    "risk_floor": round(risk_floor, 4),
                    "jev": {
                        **jev,
                        "open_threshold": open_threshold,
                        "sector_threshold": sector_threshold,
                    },
                }
            )
    finally:
        if client is not None:
            client.close()

    ranked = sorted(rows, key=_rank_key, reverse=True)
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index

    recommended_count = sum(1 for row in ranked if row["review_recommended"])
    return {
        "status": "SHADOW_ONLY",
        "triage_version": TRIAGE_VERSION,
        "authority": AUTHORITY,
        "production_effect": PRODUCTION_EFFECT,
        "writes": WRITES,
        "model_requested": model,
        "thresholds": {
            "open_actionable": open_threshold,
            "mission_sector": sector_threshold,
            "required_page_state": "contains_open_opportunity",
        },
        "scope": {
            "surface": "UNSAMPLED_ASSURANCE_NOISE_CANDIDATE_POOL",
            "candidate_limit": candidate_limit,
            "per_source_cap": per_source_cap,
            "top": top,
            "zero_item_dedupe": "SOURCE_PLUS_ARTIFACT_SHA256_KEEP_LATEST",
            "recovered_zero_item_suppression": "LATER_SUCCESS_NONZERO_ON_SAME_SOURCE_AND_URL",
            "source_diversity": "RECENCY_ORDER_THEN_PER_SOURCE_CAP",
            "automatic_noise_sample_write": False,
            "automatic_false_negative_write": False,
            "automatic_missed_signal_write": False,
            "scheduled_assurance_integration": False,
        },
        "pool": {
            **pool_counters,
            "bounded_candidates": len(candidates),
        },
        "counts": {
            "evaluated": len(ranked),
            "review_recommended": recommended_count,
            "returned": min(top, len(ranked)),
        },
        "rows": ranked[:top],
    }
