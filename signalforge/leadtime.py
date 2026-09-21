from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .config import db_path
from .db import connect, migrate

STAGES = (
    "POLICY",
    "BUDGET",
    "CAPACITY_BUILDING",
    "PROJECT_ANNOUNCEMENT",
    "PRE_PROCUREMENT",
    "TENDER",
    "AWARD",
    "COMMISSIONING",
    "O_AND_M",
)


def _iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def record_project_event(
    *,
    project_key: str,
    source_id: str,
    stage: str,
    title: str,
    url: str | None = None,
    evidence_kind: str = "OFFICIAL",
    detected_at: datetime | None = None,
    metadata: dict[str, object] | None = None,
    database: Path | None = None,
) -> dict[str, object]:
    stage = stage.upper()
    if stage not in STAGES:
        raise ValueError(f"invalid lifecycle stage: {stage}")
    if not project_key.strip() or not source_id.strip() or not title.strip():
        raise ValueError("project_key, source_id and title are required")
    target = database or db_path()
    migrate(target)
    detected = _iso(detected_at)
    raw = "|".join((project_key, source_id, stage, url or "", detected))
    event_id = "ple-" + hashlib.sha256(raw.encode()).hexdigest()[:20]
    payload = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
    with connect(target) as conn, conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO project_lifecycle_events(
                event_id,project_key,source_id,stage,detected_at,title,url,evidence_kind,metadata_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (event_id, project_key, source_id, stage, detected, title, url, evidence_kind, payload),
        )
    return {"event_id": event_id, "project_key": project_key, "stage": stage, "detected_at": detected}


def link_procurement(
    *,
    project_key: str,
    canonical_key: str,
    link_basis: str,
    linked_by: str = "operator",
    linked_at: datetime | None = None,
    database: Path | None = None,
) -> dict[str, object]:
    if not link_basis.strip():
        raise ValueError("link_basis is required; fuzzy/implicit links are not accepted")
    target = database or db_path()
    migrate(target)
    linked = _iso(linked_at)
    with connect(target) as conn, conn:
        canonical = conn.execute(
            "SELECT canonical_key,item_kind,created_at,publication_date FROM canonical_items WHERE canonical_key=?",
            (canonical_key,),
        ).fetchone()
        if canonical is None:
            raise ValueError("canonical procurement does not exist")
        if str(canonical["item_kind"]) not in {"TENDER", "AUCTION_NOTICE"}:
            raise ValueError("canonical item is not a procurement opportunity")
        conn.execute(
            """
            INSERT INTO project_procurement_links(project_key,canonical_key,linked_at,linked_by,link_basis)
            VALUES(?,?,?,?,?)
            ON CONFLICT(project_key) DO UPDATE SET
                canonical_key=excluded.canonical_key,
                linked_at=excluded.linked_at,
                linked_by=excluded.linked_by,
                link_basis=excluded.link_basis
            """,
            (project_key, canonical_key, linked, linked_by, link_basis),
        )
    return {"project_key": project_key, "canonical_key": canonical_key, "linked_at": linked}


def leadtime_report(*, database: Path | None = None, limit: int = 100) -> dict[str, object]:
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    target = database or db_path()
    migrate(target)
    rows: list[dict[str, object]] = []
    with connect(target) as conn:
        linked = conn.execute(
            """
            SELECT l.project_key,l.canonical_key,l.link_basis,l.linked_by,
                   c.title,c.publication_date,c.created_at
            FROM project_procurement_links l
            JOIN canonical_items c ON c.canonical_key=l.canonical_key
            ORDER BY c.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        for row in linked:
            first = conn.execute(
                """
                SELECT event_id,stage,detected_at,source_id,title,url
                FROM project_lifecycle_events
                WHERE project_key=?
                ORDER BY detected_at ASC,event_id ASC
                LIMIT 1
                """,
                (row["project_key"],),
            ).fetchone()
            if first is None:
                continue
            procurement_at = _parse(str(row["created_at"]))
            first_at = _parse(str(first["detected_at"]))
            lead_seconds = max(0, int((procurement_at - first_at).total_seconds()))
            rows.append(
                {
                    "project_key": str(row["project_key"]),
                    "canonical_key": str(row["canonical_key"]),
                    "procurement_title": str(row["title"] or ""),
                    "first_detected_at": str(first["detected_at"]),
                    "first_stage": str(first["stage"]),
                    "first_source_id": str(first["source_id"]),
                    "procurement_formed_at": procurement_at.isoformat().replace("+00:00", "Z"),
                    "lead_days": round(lead_seconds / 86400, 2),
                    "link_basis": str(row["link_basis"]),
                }
            )
    lead_days = sorted(float(row["lead_days"]) for row in rows)
    if lead_days:
        n = len(lead_days)
        median = lead_days[n // 2] if n % 2 else (lead_days[n // 2 - 1] + lead_days[n // 2]) / 2
        summary = {
            "linked_projects": n,
            "median_lead_days": round(median, 2),
            "mean_lead_days": round(sum(lead_days) / n, 2),
            "max_lead_days": round(max(lead_days), 2),
        }
    else:
        summary = {"linked_projects": 0, "median_lead_days": None, "mean_lead_days": None, "max_lead_days": None}
    return {"metric": "PROJECT_TO_PROCUREMENT_LEAD_TIME", "summary": summary, "projects": rows}
