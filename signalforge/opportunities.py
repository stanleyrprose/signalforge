from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from .config import Registry, db_path
from .db import connect
from .qualification import QUALIFICATION_POLICY_VERSION, qualify_opportunity

MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))


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


def _deadline_at(payload: dict[str, object]) -> datetime | None:
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
            c.source_id,c.canonical_key,c.title,c.reference_no,c.publication_date,c.location,c.url,c.payload_json,
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
        WHERE c.item_kind='TENDER'
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
            if not isinstance(payload, dict) or str(payload.get("business_stage") or "").upper() != "OPPORTUNITY":
                continue

            deadline = _deadline_at(payload)
            if deadline is None:
                deadline_status = "UNKNOWN"
                remaining_seconds = None
            elif deadline <= now:
                deadline_status = "EXPIRED"
                remaining_seconds = int((deadline - now).total_seconds())
            else:
                deadline_status = "OPEN"
                remaining_seconds = int((deadline - now).total_seconds())

            if deadline_status == "EXPIRED" and not include_expired:
                continue

            latest_signal_payload: dict[str, object] = {}
            try:
                decoded = json.loads(str(row["latest_signal_payload"]))
                if isinstance(decoded, dict):
                    latest_signal_payload = decoded
            except json.JSONDecodeError:
                pass

            source_id_value = str(row["source_id"])
            reference_numbers, reference_count, reference_numbers_evidence = _reference_bundle(payload, source_id_value)
            item = {
                "source_id": source_id_value,
                "canonical_key": str(row["canonical_key"]),
                "title": str(row["title"] or payload.get("title") or payload.get("project_name") or ""),
                "reference_no": str(row["reference_no"] or payload.get("reference_no") or ""),
                "reference_numbers": reference_numbers,
                "reference_count": reference_count,
                "reference_numbers_evidence": reference_numbers_evidence,
                "publication_date": payload.get("publication_date") or row["publication_date"],
                "deadline": payload.get("deadline"),
                "deadline_time": payload.get("deadline_time"),
                "deadline_kind": _deadline_kind(payload, source_id_value),
                "tender_opening_date": payload.get("tender_opening_date"),
                "tender_opening_time": payload.get("tender_opening_time"),
                "deadline_at": deadline.astimezone(MYANMAR_TZ).isoformat() if deadline is not None else None,
                "deadline_status": deadline_status,
                "remaining_seconds": remaining_seconds,
                "issuer": payload.get("issuer") or payload.get("business_unit"),
                "location": payload.get("location") or row["location"],
                "scope_summary": payload.get("scope_summary"),
                "detail_completeness": payload.get("detail_completeness"),
                "deadline_evidence": payload.get("deadline_evidence"),
                "url": str(row["url"]),
                "latest_signal_id": str(row["latest_signal_id"]),
                "latest_signal_type": str(row["latest_signal_type"]),
                "latest_signal_at": str(row["latest_signal_at"]),
                "latest_signal_reason": latest_signal_payload.get("signal_reason"),
                "signal_count": int(row["signal_count"]),
            }
            source_policy = source_policies.get(source_id_value) if isinstance(source_policies, dict) else None
            item.update(qualify_opportunity(item, source_policy if isinstance(source_policy, dict) else None))
            rows.append(item)

    rank = {"OPEN": 0, "UNKNOWN": 1, "EXPIRED": 2}
    priority_rank = {"HIGH": 0, "MEDIUM": 1, "REVIEW": 2, "LOW": 3}
    max_dt = datetime.max.replace(tzinfo=UTC)

    def sort_key(item: dict[str, object]) -> tuple[object, ...]:
        deadline_at = item.get("deadline_at")
        parsed = _deadline_at({"deadline": deadline_at}) if isinstance(deadline_at, str) else None
        if item["deadline_status"] == "EXPIRED":
            parsed = datetime.min.replace(tzinfo=UTC) if parsed is None else parsed
            deadline_sort: datetime = datetime.max.replace(tzinfo=UTC) - (parsed - datetime.min.replace(tzinfo=UTC))
        else:
            deadline_sort = parsed or max_dt
        return (
            rank[str(item["deadline_status"])],
            priority_rank.get(str(item.get("priority_band") or "LOW"), 3),
            deadline_sort,
            str(item["latest_signal_at"]),
            str(item["source_id"]),
            str(item["canonical_key"]),
        )

    rows.sort(key=sort_key)
    returned = rows[:limit]
    counts = {
        "OPEN": sum(1 for item in rows if item["deadline_status"] == "OPEN"),
        "UNKNOWN": sum(1 for item in rows if item["deadline_status"] == "UNKNOWN"),
        "EXPIRED": sum(1 for item in rows if item["deadline_status"] == "EXPIRED"),
    }
    trust_counts = {grade: sum(1 for item in rows if item.get("trust_grade") == grade) for grade in ("A", "B", "C")}
    priority_counts = {
        band: sum(1 for item in rows if item.get("priority_band") == band)
        for band in ("HIGH", "MEDIUM", "REVIEW", "LOW")
    }
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
            "relevance": dict(sorted(relevance_counts.items())),
        },
        "opportunities": returned,
    }
