from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from .config import db_path
from .db import connect, migrate

EVENT_TYPES = (
    "ACKNOWLEDGED",
    "WORTH_REVIEWING",
    "ACTION_TAKEN",
    "BID_OR_QUOTE_INITIATED",
    "DISMISSED",
    "RELEVANT",
    "NOT_RELEVANT",
    "CLICKED",
    "IGNORED",
    "WOULD_PAY",
    "WOULD_NOT_PAY",
)

FEEDBACK_DIMENSIONS = {
    "RELEVANT": ("RELEVANT", "NOT_RELEVANT"),
    "NOT_RELEVANT": ("RELEVANT", "NOT_RELEVANT"),
    "CLICKED": ("CLICKED", "IGNORED"),
    "IGNORED": ("CLICKED", "IGNORED"),
    "WOULD_PAY": ("WOULD_PAY", "WOULD_NOT_PAY"),
    "WOULD_NOT_PAY": ("WOULD_PAY", "WOULD_NOT_PAY"),
}


class PilotFeedbackError(RuntimeError):
    pass


def _event_id(*, profile_id: str, canonical_key: str, signal_id: str | None, event_type: str) -> str:
    raw = "|".join((profile_id, canonical_key, signal_id or "", event_type))
    return "pilot-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def record_pilot_feedback(
    *,
    profile_id: str,
    canonical_key: str,
    event_type: str,
    signal_id: str | None = None,
    note: str | None = None,
    recorded_by: str = "operator",
    database: Path | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    profile_id = profile_id.strip()
    canonical_key = canonical_key.strip()
    event_type = event_type.strip().upper()
    signal_id = signal_id.strip() if signal_id else None
    recorded_by = recorded_by.strip() or "operator"
    if not profile_id:
        raise PilotFeedbackError("profile_id is required")
    if not canonical_key:
        raise PilotFeedbackError("canonical_key is required")
    if event_type not in EVENT_TYPES:
        raise PilotFeedbackError(f"event_type must be one of: {', '.join(EVENT_TYPES)}")

    target = database or db_path()
    migrate(target)
    recorded_at = (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")
    event_id = _event_id(
        profile_id=profile_id,
        canonical_key=canonical_key,
        signal_id=signal_id,
        event_type=event_type,
    )

    with connect(target) as conn, conn:
        canonical = conn.execute(
            "SELECT canonical_key FROM canonical_items WHERE canonical_key=?",
            (canonical_key,),
        ).fetchone()
        if canonical is None:
            raise PilotFeedbackError("canonical_key does not exist")

        if signal_id:
            signal = conn.execute(
                "SELECT signal_id FROM signals WHERE signal_id=? AND canonical_key=?",
                (signal_id, canonical_key),
            ).fetchone()
            if signal is None:
                raise PilotFeedbackError("signal_id does not belong to canonical_key")

        delivered = conn.execute(
            """
            SELECT 1 FROM pilot_delivery_receipts
            WHERE canonical_key=? AND profile_id=?
            LIMIT 1
            """,
            (canonical_key, profile_id),
        ).fetchone()
        if delivered is None:
            raise PilotFeedbackError("no attributed delivery exists for profile_id and canonical_key")

        dimension = FEEDBACK_DIMENSIONS.get(event_type)
        if dimension is not None:
            placeholders = ",".join("?" for _ in dimension)
            conn.execute(
                f"""
                DELETE FROM pilot_feedback_events
                WHERE profile_id=? AND canonical_key=?
                  AND COALESCE(signal_id,'')=COALESCE(?, '')
                  AND event_type IN ({placeholders})
                """,
                (profile_id, canonical_key, signal_id, *dimension),
            )

        conn.execute(
            """
            INSERT OR IGNORE INTO pilot_feedback_events(
                event_id,profile_id,canonical_key,signal_id,event_type,note,recorded_by,recorded_at
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                event_id,
                profile_id,
                canonical_key,
                signal_id,
                event_type,
                note,
                recorded_by,
                recorded_at,
            ),
        )

    return {
        "status": "PASS",
        "event_id": event_id,
        "profile_id": profile_id,
        "canonical_key": canonical_key,
        "signal_id": signal_id,
        "event_type": event_type,
        "note": note,
        "recorded_by": recorded_by,
        "recorded_at": recorded_at,
    }


def pilot_validation_report(
    *,
    profile_id: str | None = None,
    database: Path | None = None,
) -> dict[str, object]:
    target = database or db_path()
    migrate(target)
    where = ""
    params: tuple[object, ...] = ()
    if profile_id:
        where = "WHERE profile_id=?"
        params = (profile_id,)

    with connect(target) as conn:
        delivered = conn.execute(
            f"""
            SELECT COUNT(*) AS delivery_count,
                   COUNT(DISTINCT canonical_key) AS unique_tenders,
                   COUNT(DISTINCT profile_id) AS profiles
            FROM pilot_delivery_receipts
            {where}
            """,
            params,
        ).fetchone()
        feedback_rows = conn.execute(
            f"""
            SELECT event_type,COUNT(*) AS event_count,COUNT(DISTINCT canonical_key) AS tender_count
            FROM pilot_feedback_events
            {where}
            GROUP BY event_type
            ORDER BY event_type
            """,
            params,
        ).fetchall()
        recent = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT event_id,profile_id,canonical_key,signal_id,event_type,note,recorded_by,recorded_at
                FROM pilot_feedback_events
                {where}
                ORDER BY recorded_at DESC
                LIMIT 50
                """,
                params,
            )
        ]

    by_type = {
        str(row["event_type"]): {
            "events": int(row["event_count"]),
            "unique_tenders": int(row["tender_count"]),
        }
        for row in feedback_rows
    }
    delivered_unique = int(delivered["unique_tenders"])
    action_unique = int((by_type.get("ACTION_TAKEN") or {}).get("unique_tenders", 0))
    bid_unique = int((by_type.get("BID_OR_QUOTE_INITIATED") or {}).get("unique_tenders", 0))
    review_unique = int((by_type.get("WORTH_REVIEWING") or {}).get("unique_tenders", 0))
    relevant_unique = int((by_type.get("RELEVANT") or {}).get("unique_tenders", 0))
    not_relevant_unique = int((by_type.get("NOT_RELEVANT") or {}).get("unique_tenders", 0))
    clicked_unique = int((by_type.get("CLICKED") or {}).get("unique_tenders", 0))
    ignored_unique = int((by_type.get("IGNORED") or {}).get("unique_tenders", 0))
    would_pay_unique = int((by_type.get("WOULD_PAY") or {}).get("unique_tenders", 0))
    would_not_pay_unique = int((by_type.get("WOULD_NOT_PAY") or {}).get("unique_tenders", 0))
    relevance_responses = relevant_unique + not_relevant_unique
    engagement_responses = clicked_unique + ignored_unique
    pay_responses = would_pay_unique + would_not_pay_unique

    return {
        "status": "PASS",
        "profile_id": profile_id,
        "delivery_count": int(delivered["delivery_count"]),
        "unique_tenders_delivered": delivered_unique,
        "profiles_with_attributed_delivery": int(delivered["profiles"]),
        "feedback_by_type": by_type,
        "worth_reviewing_rate": round(review_unique / delivered_unique, 4) if delivered_unique else None,
        "action_rate": round(action_unique / delivered_unique, 4) if delivered_unique else None,
        "bid_or_quote_rate": round(bid_unique / delivered_unique, 4) if delivered_unique else None,
        "relevance_response_rate": round(relevance_responses / delivered_unique, 4) if delivered_unique else None,
        "relevant_rate": round(relevant_unique / relevance_responses, 4) if relevance_responses else None,
        "engagement_response_rate": round(engagement_responses / delivered_unique, 4) if delivered_unique else None,
        "clicked_rate": round(clicked_unique / engagement_responses, 4) if engagement_responses else None,
        "pay_intent_response_rate": round(pay_responses / delivered_unique, 4) if delivered_unique else None,
        "would_pay_rate": round(would_pay_unique / pay_responses, 4) if pay_responses else None,
        "recent_feedback": recent,
        "north_star": "CUSTOMER_ACTION_FROM_RELEVANT_TENDER_INTELLIGENCE",
    }
