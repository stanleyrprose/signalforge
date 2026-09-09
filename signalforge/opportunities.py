from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from .config import db_path
from .db import connect

MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))


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
) -> dict[str, object]:
    if limit < 1 or limit > 500:
        raise ValueError("opportunities limit must be between 1 and 500")
    now = (now or datetime.now(UTC)).astimezone(UTC)
    target = database or db_path()

    query = """
        SELECT
            c.source_id,c.canonical_key,c.title,c.reference_no,c.publication_date,c.location,c.url,c.payload_json,
            ss.signal_count,ss.latest_signal_at,
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

            rows.append(
                {
                    "source_id": str(row["source_id"]),
                    "canonical_key": str(row["canonical_key"]),
                    "title": str(row["title"] or payload.get("title") or payload.get("project_name") or ""),
                    "reference_no": str(row["reference_no"] or payload.get("reference_no") or ""),
                    "publication_date": payload.get("publication_date") or row["publication_date"],
                    "deadline": payload.get("deadline"),
                    "deadline_time": payload.get("deadline_time"),
                    "deadline_at": deadline.astimezone(MYANMAR_TZ).isoformat() if deadline is not None else None,
                    "deadline_status": deadline_status,
                    "remaining_seconds": remaining_seconds,
                    "issuer": payload.get("issuer") or payload.get("business_unit"),
                    "location": payload.get("location") or row["location"],
                    "scope_summary": payload.get("scope_summary"),
                    "detail_completeness": payload.get("detail_completeness"),
                    "url": str(row["url"]),
                    "latest_signal_type": str(row["latest_signal_type"]),
                    "latest_signal_at": str(row["latest_signal_at"]),
                    "latest_signal_reason": latest_signal_payload.get("signal_reason"),
                    "signal_count": int(row["signal_count"]),
                }
            )

    rank = {"OPEN": 0, "UNKNOWN": 1, "EXPIRED": 2}
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
    return {
        "status": "PASS",
        "as_of": now.isoformat().replace("+00:00", "Z"),
        "source_id": source_id,
        "include_expired": include_expired,
        "count": len(returned),
        "total_matching": len(rows),
        "counts": counts,
        "opportunities": returned,
    }
