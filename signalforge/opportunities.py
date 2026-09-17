from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from .config import Registry, db_path
from .db import connect
from .customs_reviewed_enrichment import apply_reviewed_customs_overlay
from .doms_reviewed_enrichment import apply_reviewed_doms_overlay
from .mte_reviewed_enrichment import apply_reviewed_mte_overlay
from .moep_reviewed_enrichment import apply_reviewed_moep_overlay
from .qualification import QUALIFICATION_POLICY_VERSION, qualify_opportunity

MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))
UNKNOWN_OPPORTUNITY_FRESHNESS_DAYS = 45


def _deadline_kind(payload: dict[str, object], source_id: str) -> str | None:
    explicit = payload.get("deadline_kind")
    if isinstance(explicit, str) and explicit:
        return explicit
    evidence = payload.get("deadline_evidence")
    if source_id in {"S30", "S39"} and evidence == "OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME":
        return "BID_SUBMISSION_DEADLINE"
    if source_id == "S38" and evidence == "EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME":
        return "BID_SUBMISSION_DEADLINE"
    return None


_ENERGY_DMP_REFERENCE_RE = re.compile(r"\bDMP/L-\s*(?P<number>\d{3})\s*\((?P<year>\d{2}-\d{2})\)", re.I)


def _reference_bundle(payload: dict[str, object], source_id: str) -> tuple[object, object, object]:
    explicit = payload.get("reference_numbers")
    if isinstance(explicit, list) and explicit:
        return explicit, payload.get("reference_count"), payload.get("reference_numbers_evidence")

    if (
        source_id == "S39"
        and payload.get("detail_completeness") == "HTML_ID_PUBLICATION_PLUS_TEXT_PDF_SCOPE_DEADLINE"
        and isinstance(payload.get("scope_summary"), str)
    ):
        values: list[str] = []
        for match in _ENERGY_DMP_REFERENCE_RE.finditer(str(payload["scope_summary"])):
            value = f"DMP/L-{match.group('number')}({match.group('year')})"
            if value not in values:
                values.append(value)
        if len(values) >= 2:
            return values, len(values), "OFFICIAL_TEXT_NATIVE_PDF_SCOPE_DMP_REFERENCE_PATTERN"

    return payload.get("reference_numbers"), payload.get("reference_count"), payload.get("reference_numbers_evidence")


_ENERGY_DMP_FOCUS_TERMS = (
    "communication and information",
    " iot ",
    "software",
    "scanner",
    "computer",
    "server",
    "network",
    "telecom",
)


def _reference_focus(
    payload: dict[str, object],
    source_id: str,
    reference_numbers: object,
) -> tuple[object, object, object, object]:
    scope = payload.get("scope_summary")
    if (
        source_id != "S39"
        or payload.get("detail_completeness") != "HTML_ID_PUBLICATION_PLUS_TEXT_PDF_SCOPE_DEADLINE"
        or not isinstance(scope, str)
        or not isinstance(reference_numbers, list)
        or len(reference_numbers) < 2
    ):
        return None, None, None, None

    allowed = {str(value) for value in reference_numbers}
    matches = list(_ENERGY_DMP_REFERENCE_RE.finditer(scope))
    if len(matches) < 2:
        return None, None, None, None

    focus_refs: list[str] = []
    focus_segments: list[str] = []
    for index, match in enumerate(matches):
        reference = f"DMP/L-{match.group('number')}({match.group('year')})"
        if reference not in allowed:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(scope)
        segment = scope[match.start() : end].strip(" |")
        segment = re.sub(r"\s*\|\s*\(?\d+\)?\s*$", "", segment).strip()
        padded = f" {segment.lower()} "
        if not any(term in padded for term in _ENERGY_DMP_FOCUS_TERMS):
            continue
        focus_refs.append(reference)
        focus_segments.append(segment)

    if not focus_refs:
        return None, None, None, None
    return (
        focus_refs,
        len(focus_refs),
        "ICT_TELECOM",
        " | ".join(focus_segments),
    )


def _deadline_at(payload: dict[str, object]) -> datetime | None:
    explicit_local = payload.get("deadline_datetime_local")
    if isinstance(explicit_local, str) and explicit_local:
        try:
            parsed = datetime.fromisoformat(explicit_local.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=MYANMAR_TZ)
            return parsed.astimezone(UTC)
        except ValueError:
            pass
    raw = payload.get("deadline")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        if "T" in raw:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=MYANMAR_TZ)
            return parsed.astimezone(UTC)

        deadline_time = payload.get("deadline_time")
        local_time = str(deadline_time) if isinstance(deadline_time, str) and deadline_time else "23:59"
        parsed = datetime.fromisoformat(f"{raw}T{local_time}:00+06:30")
        return parsed.astimezone(UTC)
    except ValueError:
        return None


def _deadline_evidence(payload: dict[str, object], source_id: str) -> object:
    explicit = payload.get("deadline_evidence")
    if explicit:
        return explicit
    if source_id == "S21" and payload.get("deadline"):
        return "EXPLICIT_HTML_TENDER_CLOSE_DATE"
    if source_id == "S22" and payload.get("deadline_datetime_local"):
        return "EXPLICIT_HTML_DEADLINE_DATETIME"
    return explicit


def _action_at(payload: dict[str, object]) -> datetime | None:
    deadline = _deadline_at(payload)
    if deadline is not None:
        return deadline
    raw = payload.get("action_date")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        if "T" in raw:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=MYANMAR_TZ)
            return parsed.astimezone(UTC)
        action_time = payload.get("action_time")
        local_time = str(action_time) if isinstance(action_time, str) and action_time else "23:59"
        return datetime.fromisoformat(f"{raw}T{local_time}:00+06:30").astimezone(UTC)
    except ValueError:
        return None


def current_opportunities(
    *,
    database: Path | None = None,
    now: datetime | None = None,
    source_id: str | None = None,
    include_expired: bool = False,
    limit: int = 50,
    registry: Registry | None = None,
) -> dict[str, object]:
    if limit < 1 or limit > 500:
        raise ValueError("opportunities limit must be between 1 and 500")
    now = (now or datetime.now(UTC)).astimezone(UTC)
    target = database or db_path()
    registry = registry or Registry.load()
    source_policies = registry.raw.get("sources") or {}

    query = """
        SELECT
            c.source_id,c.canonical_key,c.item_kind,c.title,c.reference_no,c.publication_date,c.location,c.url,c.payload_json,
            ss.signal_count,ss.latest_signal_at,
            (
                SELECT s.signal_id FROM signals s
                WHERE s.source_id=c.source_id AND s.canonical_key=c.canonical_key
                ORDER BY s.created_at DESC,s.signal_id DESC LIMIT 1
            ) AS latest_signal_id,
            (
                SELECT s.signal_type FROM signals s
                WHERE s.source_id=c.source_id AND s.canonical_key=c.canonical_key
                ORDER BY s.created_at DESC,s.signal_id DESC LIMIT 1
            ) AS latest_signal_type,
            (
                SELECT s.payload_json FROM signals s
                WHERE s.source_id=c.source_id AND s.canonical_key=c.canonical_key
                ORDER BY s.created_at DESC,s.signal_id DESC LIMIT 1
            ) AS latest_signal_payload
        FROM canonical_items c
        JOIN (
            SELECT source_id,canonical_key,COUNT(*) AS signal_count,MAX(created_at) AS latest_signal_at
            FROM signals
            GROUP BY source_id,canonical_key
        ) ss ON ss.source_id=c.source_id AND ss.canonical_key=c.canonical_key
        WHERE c.item_kind IN ('TENDER','AUCTION_NOTICE')
    """
    params: list[object] = []
    if source_id is not None:
        query += " AND c.source_id=?"
        params.append(source_id)

    rows: list[dict[str, object]] = []
    with connect(target) as conn:
        for row in conn.execute(query, params):
            try:
                payload = json.loads(str(row["payload_json"]))
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            source_id_value = str(row["source_id"])
            source_policy = source_policies.get(source_id_value) if isinstance(source_policies, dict) else None
            canonical_key_value = str(row["canonical_key"])
            reference_no_value = str(row["reference_no"] or payload.get("reference_no") or "")
            payload = apply_reviewed_customs_overlay(
                payload,
                canonical_key=canonical_key_value,
                source_id=source_id_value,
                item_kind=str(row["item_kind"]),
                reference_no=reference_no_value,
            )
            # S20 is an issuer tender-only surface. Older canonical rows predate the
            # business-stage field even when they already have a real Signal. Keep
            # this as a read-model compatibility rule instead of rewriting history.
            if source_id_value == "S20" and str(row["item_kind"]) == "TENDER":
                payload = dict(payload)
                payload.setdefault("business_stage", "OPPORTUNITY")
                if not payload.get("scope_summary"):
                    payload["scope_summary"] = payload.get("project_name") or row["project_name"]
                payload = apply_reviewed_moep_overlay(
                    payload,
                    canonical_key=canonical_key_value,
                    source_id=source_id_value,
                    item_kind=str(row["item_kind"]),
                    reference_no=reference_no_value,
                )
            stage = str(payload.get("business_stage") or "").upper()
            legacy_actionable_tender = (
                stage == ""
                and str(row["item_kind"]) == "TENDER"
                and isinstance(source_policy, dict)
                and isinstance(source_policy.get("actionable_baseline_signal_policy"), dict)
                and source_policy["actionable_baseline_signal_policy"].get("enabled") is True
            )
            if stage != "OPPORTUNITY" and not legacy_actionable_tender:
                continue

            payload = apply_reviewed_mte_overlay(
                payload,
                canonical_key=canonical_key_value,
                source_id=source_id_value,
                item_kind=str(row["item_kind"]),
                reference_no=reference_no_value,
            )
            payload = apply_reviewed_doms_overlay(
                payload,
                canonical_key=canonical_key_value,
                source_id=source_id_value,
                item_kind=str(row["item_kind"]),
                reference_no=reference_no_value,
            )

            deadline = _deadline_at(payload)
            if deadline is None:
                deadline_status = "UNKNOWN"
            elif deadline <= now:
                deadline_status = "EXPIRED"
            else:
                deadline_status = "OPEN"

            action_at = _action_at(payload)
            if action_at is None:
                opportunity_status = deadline_status
                remaining_seconds = None
            elif action_at <= now:
                opportunity_status = "EXPIRED"
                remaining_seconds = int((action_at - now).total_seconds())
            else:
                opportunity_status = "OPEN"
                remaining_seconds = int((action_at - now).total_seconds())

            # Unknown-deadline tenders are useful for a bounded review window, but
            # must not remain in the "current" view forever.
            if opportunity_status == "UNKNOWN":
                publication_raw = payload.get("publication_date") or row["publication_date"]
                try:
                    publication_date = datetime.fromisoformat(str(publication_raw)).date()
                except (TypeError, ValueError):
                    publication_date = None
                if publication_date is not None and publication_date < (now.astimezone(MYANMAR_TZ).date() - timedelta(days=UNKNOWN_OPPORTUNITY_FRESHNESS_DAYS)):
                    opportunity_status = "EXPIRED"

            if opportunity_status == "EXPIRED" and not include_expired:
                continue

            latest_signal_payload: dict[str, object] = {}
            try:
                decoded = json.loads(str(row["latest_signal_payload"]))
                if isinstance(decoded, dict):
                    latest_signal_payload = decoded
            except json.JSONDecodeError:
                pass

            reference_numbers, reference_count, reference_numbers_evidence = _reference_bundle(payload, source_id_value)
            focus_reference_numbers, focus_reference_count, focus_relevance, focus_scope_summary = _reference_focus(
                payload, source_id_value, reference_numbers
            )
            if focus_scope_summary is None and payload.get("focus_scope_summary"):
                focus_scope_summary = payload.get("focus_scope_summary")
            if focus_relevance is None and payload.get("mission_sector_hint"):
                focus_relevance = payload.get("mission_sector_hint")
            item = {
                "source_id": source_id_value,
                "canonical_key": str(row["canonical_key"]),
                "item_kind": str(row["item_kind"]),
                "title": str(row["title"] or payload.get("title") or payload.get("project_name") or ""),
                "reference_no": str(row["reference_no"] or payload.get("reference_no") or ""),
                "reference_numbers": reference_numbers,
                "reference_count": reference_count,
                "reference_numbers_evidence": reference_numbers_evidence,
                "focus_reference_numbers": focus_reference_numbers,
                "focus_reference_count": focus_reference_count,
                "focus_relevance": focus_relevance,
                "focus_scope_summary": focus_scope_summary,
                "publication_date": payload.get("publication_date") or row["publication_date"],
                "deadline": payload.get("deadline"),
                "deadline_time": payload.get("deadline_time"),
                "deadline_kind": _deadline_kind(payload, source_id_value),
                "tender_opening_date": payload.get("tender_opening_date"),
                "tender_opening_time": payload.get("tender_opening_time"),
                "deadline_at": deadline.astimezone(MYANMAR_TZ).isoformat() if deadline is not None else None,
                "deadline_status": deadline_status,
                "action_date": payload.get("action_date"),
                "action_time": payload.get("action_time"),
                "action_date_kind": payload.get("action_date_kind"),
                "action_date_evidence": payload.get("action_date_evidence"),
                "action_at": action_at.astimezone(MYANMAR_TZ).isoformat() if action_at is not None else None,
                "opportunity_status": opportunity_status,
                "commercial_event_type": payload.get("commercial_event_type"),
                "commercial_direction": payload.get("commercial_direction"),
                "remaining_seconds": remaining_seconds,
                "issuer": payload.get("issuer") or payload.get("business_unit"),
                "location": payload.get("location") or row["location"],
                "location_evidence": payload.get("location_evidence"),
                "scope_summary": payload.get("scope_summary") or payload.get("project_name"),
                "relevance_categories": payload.get("relevance_categories"),
                "mission_sector_hint": payload.get("mission_sector_hint"),
                "quantity_or_lot_summary": payload.get("quantity_or_lot_summary"),
                "quantity_or_lot_evidence": payload.get("quantity_or_lot_evidence"),
                "quantity_or_lot_confidence": payload.get("quantity_or_lot_confidence"),
                "next_action_summary": payload.get("next_action_summary"),
                "next_action_evidence": payload.get("next_action_evidence"),
                "action_time_evidence": payload.get("action_time_evidence"),
                "reviewed_enrichment_version": payload.get("reviewed_enrichment_version"),
                "reviewed_enrichment_status": payload.get("reviewed_enrichment_status"),
                "reviewed_enrichment_at": payload.get("reviewed_enrichment_at"),
                "reviewed_image_url": payload.get("reviewed_image_url"),
                "reviewed_image_sha256": payload.get("reviewed_image_sha256"),
                "reviewed_rules_url": payload.get("reviewed_rules_url"),
                "reviewed_document_url": payload.get("reviewed_document_url"),
                "reviewed_document_sha256": payload.get("reviewed_document_sha256"),
                "reviewed_document_page": payload.get("reviewed_document_page"),
                "reviewed_document_date": payload.get("reviewed_document_date"),
                "reviewed_enrichment_read_only": payload.get("reviewed_enrichment_read_only"),
                "image_review_notes": payload.get("image_review_notes"),
                "detail_completeness": payload.get("detail_completeness"),
                "deadline_evidence": _deadline_evidence(payload, source_id_value),
                "url": str(row["url"]),
                "latest_signal_id": str(row["latest_signal_id"]),
                "latest_signal_type": str(row["latest_signal_type"]),
                "latest_signal_at": str(row["latest_signal_at"]),
                "latest_signal_reason": latest_signal_payload.get("signal_reason"),
                "signal_count": int(row["signal_count"]),
            }
            item.update(qualify_opportunity(item, source_policy if isinstance(source_policy, dict) else None))
            rows.append(item)

    rank = {"OPEN": 0, "UNKNOWN": 1, "EXPIRED": 2}
    priority_rank = {"HIGH": 0, "MEDIUM": 1, "REVIEW": 2, "LOW": 3}
    max_dt = datetime.max.replace(tzinfo=UTC)

    def sort_key(item: dict[str, object]) -> tuple[object, ...]:
        action_at_value = item.get("action_at")
        parsed = _deadline_at({"deadline": action_at_value}) if isinstance(action_at_value, str) else None
        if item["opportunity_status"] == "EXPIRED":
            parsed = datetime.min.replace(tzinfo=UTC) if parsed is None else parsed
            action_sort: datetime = datetime.max.replace(tzinfo=UTC) - (parsed - datetime.min.replace(tzinfo=UTC))
        else:
            action_sort = parsed or max_dt
        return (
            rank[str(item["opportunity_status"])],
            priority_rank.get(str(item.get("priority_band") or "LOW"), 3),
            action_sort,
            str(item["latest_signal_at"]),
            str(item["source_id"]),
            str(item["canonical_key"]),
        )

    rows.sort(key=sort_key)
    returned = rows[:limit]
    counts = {
        "OPEN": sum(1 for item in rows if item["opportunity_status"] == "OPEN"),
        "UNKNOWN": sum(1 for item in rows if item["opportunity_status"] == "UNKNOWN"),
        "EXPIRED": sum(1 for item in rows if item["opportunity_status"] == "EXPIRED"),
    }
    trust_counts = {grade: sum(1 for item in rows if item.get("trust_grade") == grade) for grade in ("A", "B", "C")}
    priority_counts = {
        band: sum(1 for item in rows if item.get("priority_band") == band)
        for band in ("HIGH", "MEDIUM", "REVIEW", "LOW")
    }
    quality_counts = {
        band: sum(1 for item in rows if item.get("signal_quality_band") == band)
        for band in ("VERY_HIGH", "HIGH", "MEDIUM", "REVIEW", "LOW")
    }
    quality_scores = [int(item.get("signal_quality_score") or 0) for item in rows]
    relevance_counts: dict[str, int] = {}
    for item in rows:
        for category in item.get("relevance_categories") or []:
            relevance_counts[str(category)] = relevance_counts.get(str(category), 0) + 1

    return {
        "status": "PASS",
        "qualification_policy_version": QUALIFICATION_POLICY_VERSION,
        "as_of": now.isoformat().replace("+00:00", "Z"),
        "source_id": source_id,
        "include_expired": include_expired,
        "count": len(returned),
        "total_matching": len(rows),
        "counts": counts,
        "qualification_counts": {
            "trust_grade": trust_counts,
            "priority_band": priority_counts,
            "signal_quality_band": quality_counts,
            "signal_quality_score_avg": round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 0.0,
            "relevance": dict(sorted(relevance_counts.items())),
        },
        "opportunities": returned,
    }
