from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from .config import db_path
from .db import connect, migrate
from .mission_focus import classify_mission_fit

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
PRECURSOR_STAGES = ("POLICY", "BUDGET", "CAPACITY_BUILDING", "PROJECT_ANNOUNCEMENT", "PRE_PROCUREMENT")

MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=MYANMAR_TZ)
    return parsed.astimezone(UTC)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    value = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    return round(value, 2)


def _lead_measurement(
    *,
    first_at: datetime,
    publication_date: object,
    canonical_created_at: str,
) -> tuple[float, str, str, str]:
    """Return lead days plus the procurement reference and its evidence semantics.

    Official publication date is preferred because canonical created_at is an
    ingestion timestamp and can otherwise overstate how early SignalForge found
    the project. Date-only issuer evidence is measured in Myanmar calendar days.
    """

    publication = str(publication_date or "").strip()
    if publication:
        if _DATE_ONLY_RE.fullmatch(publication):
            procurement_date = datetime.strptime(publication, "%Y-%m-%d").date()
            first_date = first_at.astimezone(MYANMAR_TZ).date()
            days = max(0, (procurement_date - first_date).days)
            return float(days), publication, "OFFICIAL_PUBLICATION_DATE", "CALENDAR_DAY"
        try:
            procurement_at = _parse(publication)
        except ValueError:
            pass
        else:
            seconds = max(0, int((procurement_at - first_at).total_seconds()))
            return (
                round(seconds / 86400, 2),
                procurement_at.isoformat().replace("+00:00", "Z"),
                "OFFICIAL_PUBLICATION_DATETIME",
                "EXACT_TIMESTAMP",
            )

    procurement_at = _parse(canonical_created_at)
    seconds = max(0, int((procurement_at - first_at).total_seconds()))
    return (
        round(seconds / 86400, 2),
        procurement_at.isoformat().replace("+00:00", "Z"),
        "CANONICAL_CREATED_AT_FALLBACK",
        "EXACT_TIMESTAMP",
    )


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



def precursor_candidates(*, database: Path | None = None, limit: int = 50) -> dict[str, object]:
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    target = database or db_path()
    migrate(target)
    candidates: list[dict[str, object]] = []
    tracked: dict[str, str] = {}
    with connect(target) as conn:
        for event in conn.execute("SELECT project_key,metadata_json FROM project_lifecycle_events"):
            try:
                metadata = json.loads(str(event["metadata_json"] or "{}"))
            except json.JSONDecodeError:
                continue
            if isinstance(metadata, dict):
                key = str(metadata.get("precursor_canonical_key") or "")
                if key:
                    tracked[key] = str(event["project_key"])
        rows = conn.execute(
            """
            SELECT canonical_key,source_id,title,publication_date,url,created_at,evidence_sha256,payload_json
            FROM canonical_items
            WHERE item_kind='REGULATORY_NOTICE'
            ORDER BY created_at DESC,canonical_key ASC
            """
        ).fetchall()
        for row in rows:
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict) or payload.get("business_stage") != "PROJECT_PRECURSOR_CANDIDATE":
                continue
            if payload.get("precursor_review_required") is not True:
                continue
            key = str(row["canonical_key"])
            project_key = tracked.get(key)
            candidates.append({
                "canonical_key": key,
                "source_id": str(row["source_id"]),
                "title": str(row["title"] or ""),
                "publication_date": row["publication_date"],
                "first_retained_at": str(row["created_at"]),
                "url": row["url"],
                "evidence_sha256": row["evidence_sha256"],
                "precursor_stage_hint": payload.get("precursor_stage_hint"),
                "relevance_categories": payload.get("relevance_categories") or [],
                "review_status": "TRACKED" if project_key else "PENDING_REVIEW",
                "project_key": project_key,
            })
    pending = sum(1 for row in candidates if row["review_status"] == "PENDING_REVIEW")
    return {
        "metric": "PROJECT_PRECURSOR_PIPELINE",
        "summary": {
            "candidates": len(candidates),
            "pending_review": pending,
            "tracked": len(candidates) - pending,
            "returned_candidates": min(limit, len(candidates)),
        },
        "candidates": candidates[:limit],
        "semantics": {
            "candidate_is_not_confirmed_project": True,
            "human_review_required_before_lifecycle_promotion": True,
            "first_retained_at_is_detection_evidence": True,
            "issuer_publication_date_is_not_signalforge_detection_time": True,
            "fuzzy_project_linking_prohibited": True,
        },
    }


def promote_precursor_from_canonical(
    *,
    canonical_key: str,
    project_key: str,
    stage: str,
    review_basis: str,
    reviewed_by: str,
    database: Path | None = None,
) -> dict[str, object]:
    stage = stage.upper()
    if stage not in PRECURSOR_STAGES:
        raise ValueError(f"invalid precursor stage: {stage}")
    if not project_key.strip() or not review_basis.strip() or not reviewed_by.strip():
        raise ValueError("project_key, review_basis and reviewed_by are required")
    target = database or db_path()
    migrate(target)
    with connect(target) as conn:
        row = conn.execute(
            """
            SELECT canonical_key,source_id,item_kind,title,publication_date,url,created_at,evidence_sha256,payload_json
            FROM canonical_items WHERE canonical_key=?
            """,
            (canonical_key,),
        ).fetchone()
    if row is None:
        raise ValueError("canonical precursor does not exist")
    if str(row["item_kind"]) != "REGULATORY_NOTICE":
        raise ValueError("canonical item is not a regulatory/project precursor notice")
    try:
        payload = json.loads(str(row["payload_json"] or "{}"))
    except json.JSONDecodeError as exc:
        raise ValueError("canonical precursor payload is invalid") from exc
    if not isinstance(payload, dict) or payload.get("business_stage") != "PROJECT_PRECURSOR_CANDIDATE":
        raise ValueError("canonical item is not a project precursor candidate")
    if payload.get("precursor_review_required") is not True:
        raise ValueError("canonical precursor is missing the review-required contract")
    metadata = {
        "precursor_canonical_key": str(row["canonical_key"]),
        "precursor_publication_date": row["publication_date"],
        "precursor_evidence_sha256": row["evidence_sha256"],
        "precursor_stage_hint": payload.get("precursor_stage_hint"),
        "precursor_selection_basis": payload.get("precursor_selection_basis"),
        "review_basis": review_basis,
        "reviewed_by": reviewed_by,
        "detection_time_semantics": "CANONICAL_FIRST_INGESTION_TIME_NOT_PUBLICATION_DATE",
    }
    result = record_project_event(
        project_key=project_key,
        source_id=str(row["source_id"]),
        stage=stage,
        title=str(row["title"] or ""),
        url=str(row["url"]) if row["url"] else None,
        evidence_kind="RETAINED_CANONICAL_OFFICIAL",
        detected_at=_parse(str(row["created_at"])),
        metadata=metadata,
        database=target,
    )
    return {
        **result,
        "canonical_key": canonical_key,
        "publication_date": row["publication_date"],
        "review_basis": review_basis,
        "reviewed_by": reviewed_by,
        "detection_time_semantics": metadata["detection_time_semantics"],
    }


_GENERIC_IDENTITY_TERMS = {
    "project", "projects", "tender", "procurement", "construction", "works", "work",
    "planned", "plan", "planning", "new", "build", "building", "built", "upgrade",
    "expand", "expansion", "implementation", "implement", "approval", "approved",
    "budget", "fund", "funding", "purchase", "supply", "equipment", "installation",
    "ministry", "department", "government", "myanmar", "city", "road", "bridge",
    "power", "plant", "station", "substation", "grid", "transmission", "distribution",
    "line", "network", "telecom", "energy", "engineering", "electricity", "ict", "digital", "infrastructure",
    "စီမံကိန်း", "လုပ်ငန်း", "အတွက်", "အတွင်း", "အသစ်", "တည်ဆောက်", "တည်ဆောက်ရန်",
    "တည်ဆောက်မည်", "တည်ဆောက်မည့်", "တည်ဆောက်မည့်", "ဆောက်လုပ်", "တိုးချဲ့",
    "ဆောင်ရွက်", "အကောင်အထည်ဖော်", "ဝယ်ယူ", "အိတ်ဖွင့်တင်ဒါ", "အိတ်ဖွင့်တင်ဒါ",
    "တင်ဒါ", "ဖိတ်ခေါ်", "ခေါ်ယူ", "ဝန်ကြီးဌာန", "ဦးစီးဌာန", "အခြေအနေ",
    "ဓာတ်အားပေးစက်ရုံ", "ဓာတ်အားခွဲရုံ", "ဓာတ်အားလိုင်း",
}
_IDENTITY_SUFFIXES = ("စီမံကိန်း", "လုပ်ငန်း", "အတွင်း", "အတွက်")
_IDENTITY_SPLIT_RE = re.compile(r"[\s,.;:!?()\[\]{}<>/\\|+&'\"“”‘’၊။\-–—]+")
_GENERIC_LOCATIONS = {"myanmar", "မြန်မာ", "မြန်မာနိုင်ငံ"}


def _identity_terms(*values: object) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split()).lower()
        for raw in _IDENTITY_SPLIT_RE.split(text):
            term = raw.strip()
            if not term:
                continue
            for suffix in _IDENTITY_SUFFIXES:
                if term.endswith(suffix) and len(term) >= len(suffix) + 4:
                    term = term[: -len(suffix)]
                    break
            if (
                not term
                or term in _GENERIC_IDENTITY_TERMS
                or len(term) < 4
                or any(ch.isdigit() for ch in term)
                or not any(ch.isalpha() for ch in term)
                or term in seen
            ):
                continue
            seen.add(term)
            terms.append(term)
    return terms


def _compact_identity_text(*values: object) -> str:
    combined = " ".join(str(value or "") for value in values).lower()
    return "".join(_IDENTITY_SPLIT_RE.split(combined))


def _safe_payload(value: object) -> dict[str, object]:
    try:
        parsed = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _procurement_temporal_evidence(
    *,
    publication_date: object,
    created_at: str,
    first_detected_at: datetime,
) -> tuple[str, str] | None:
    publication = str(publication_date or "").strip()
    if publication:
        if _DATE_ONLY_RE.fullmatch(publication):
            procurement_date = datetime.strptime(publication, "%Y-%m-%d").date()
            if procurement_date < first_detected_at.astimezone(MYANMAR_TZ).date():
                return None
            return publication, "OFFICIAL_PUBLICATION_DATE"
        try:
            procurement_at = _parse(publication)
        except ValueError:
            pass
        else:
            if procurement_at < first_detected_at:
                return None
            return procurement_at.isoformat().replace("+00:00", "Z"), "OFFICIAL_PUBLICATION_DATETIME"

    created = _parse(created_at)
    if created < first_detected_at:
        return None
    return created.isoformat().replace("+00:00", "Z"), "CANONICAL_CREATED_AT_FALLBACK"


def procurement_link_suggestions(
    *,
    database: Path | None = None,
    limit: int = 50,
    per_project: int = 3,
) -> dict[str, object]:
    """Return review-only candidate procurement links for promoted projects."""

    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    if per_project < 1 or per_project > 20:
        raise ValueError("per_project must be between 1 and 20")
    target = database or db_path()
    migrate(target)

    with connect(target) as conn:
        event_rows = conn.execute(
            """
            SELECT event_id,project_key,source_id,stage,detected_at,title,url,metadata_json
            FROM project_lifecycle_events
            ORDER BY detected_at ASC,event_id ASC
            """
        ).fetchall()
        linked_rows = conn.execute(
            "SELECT project_key,canonical_key FROM project_procurement_links"
        ).fetchall()
        procurement_rows = conn.execute(
            """
            SELECT canonical_key,source_id,item_kind,title,project_name,reference_no,
                   publication_date,location,url,created_at,payload_json
            FROM canonical_items
            WHERE item_kind IN ('TENDER','AUCTION_NOTICE')
            ORDER BY created_at DESC,canonical_key ASC
            """
        ).fetchall()

        linked_projects = {str(row["project_key"]) for row in linked_rows}
        linked_canonicals = {str(row["canonical_key"]) for row in linked_rows}
        first_events: dict[str, object] = {}
        for row in event_rows:
            first_events.setdefault(str(row["project_key"]), row)

        suggestions: list[dict[str, object]] = []
        projects_with_suggestions: set[str] = set()
        for project_key, event in first_events.items():
            if project_key in linked_projects:
                continue
            first_detected = _parse(str(event["detected_at"]))
            event_metadata = _safe_payload(event["metadata_json"])
            precursor_key = str(event_metadata.get("precursor_canonical_key") or "")
            precursor = None
            precursor_payload: dict[str, object] = {}
            if precursor_key:
                precursor = conn.execute(
                    """
                    SELECT title,project_name,location,payload_json
                    FROM canonical_items WHERE canonical_key=?
                    """,
                    (precursor_key,),
                ).fetchone()
                if precursor is not None:
                    precursor_payload = _safe_payload(precursor["payload_json"])

            project_values: list[object] = [project_key, event["title"]]
            project_location = ""
            project_issuer = ""
            project_sectors: set[str] = set()
            if precursor is not None:
                project_values.extend(
                    (
                        precursor["title"],
                        precursor["project_name"],
                        precursor_payload.get("scope_summary"),
                    )
                )
                project_location = str(
                    precursor_payload.get("project_location_hint")
                    or precursor_payload.get("location")
                    or precursor["location"]
                    or ""
                )
                project_issuer = str(precursor_payload.get("issuer") or "")
                raw_categories = precursor_payload.get("relevance_categories") or []
                if isinstance(raw_categories, list):
                    project_sectors = {str(value) for value in raw_categories if str(value)}

            support_only_terms = set(_identity_terms(project_location, project_issuer))
            project_terms = [
                term
                for term in _identity_terms(*project_values)
                if term not in support_only_terms
            ]
            if not project_terms:
                continue

            per_project_rows: list[dict[str, object]] = []
            for row in procurement_rows:
                canonical_key = str(row["canonical_key"])
                if canonical_key in linked_canonicals:
                    continue
                temporal = _procurement_temporal_evidence(
                    publication_date=row["publication_date"],
                    created_at=str(row["created_at"]),
                    first_detected_at=first_detected,
                )
                if temporal is None:
                    continue
                formed_at, temporal_basis = temporal
                payload = _safe_payload(row["payload_json"])
                procurement_values = (
                    row["title"],
                    row["project_name"],
                    payload.get("scope_summary"),
                    row["reference_no"],
                )
                procurement_compact = _compact_identity_text(*procurement_values)
                shared = sorted(
                    {
                        term
                        for term in project_terms
                        if term and _compact_identity_text(term) in procurement_compact
                    },
                    key=lambda value: (-len(value), value),
                )
                if not shared:
                    continue

                max_anchor_len = max(len(term) for term in shared)
                identity_score = min(75, max_anchor_len * 4 + max(0, len(shared) - 1) * 15)
                if not (max_anchor_len >= 8 or len(shared) >= 2):
                    continue

                mission = classify_mission_fit(
                    {
                        "source_id": str(row["source_id"]),
                        "item_kind": str(row["item_kind"]),
                        "title": str(row["title"] or ""),
                        "project_name": str(row["project_name"] or ""),
                        "scope_summary": payload.get("scope_summary"),
                        "relevance_categories": payload.get("relevance_categories") or [],
                        "issuer": payload.get("issuer"),
                        "location": row["location"],
                    }
                )
                procurement_sector = (
                    str(mission.get("mission_sector") or "")
                    if bool(mission.get("mission_fit"))
                    else ""
                )
                sector_match = bool(procurement_sector and procurement_sector in project_sectors)

                procurement_location = str(
                    payload.get("project_location_hint")
                    or payload.get("location")
                    or row["location"]
                    or ""
                )
                project_location_key = _compact_identity_text(project_location)
                procurement_location_key = _compact_identity_text(procurement_location)
                location_match = bool(
                    project_location_key
                    and procurement_location_key
                    and project_location_key not in _GENERIC_LOCATIONS
                    and procurement_location_key not in _GENERIC_LOCATIONS
                    and project_location_key == procurement_location_key
                )
                procurement_issuer = str(payload.get("issuer") or "")
                issuer_match = bool(
                    project_issuer
                    and procurement_issuer
                    and _compact_identity_text(project_issuer)
                    == _compact_identity_text(procurement_issuer)
                )

                score = min(
                    100,
                    identity_score
                    + (10 if sector_match else 0)
                    + (10 if location_match else 0)
                    + (5 if issuer_match else 0),
                )
                if not (identity_score >= 50 or (identity_score >= 35 and score >= 55)):
                    continue

                per_project_rows.append(
                    {
                        "project_key": project_key,
                        "project_first_detected_at": str(event["detected_at"]),
                        "project_first_stage": str(event["stage"]),
                        "project_title": str(event["title"] or ""),
                        "precursor_canonical_key": precursor_key or None,
                        "procurement_canonical_key": canonical_key,
                        "procurement_source_id": str(row["source_id"]),
                        "procurement_title": str(row["title"] or ""),
                        "procurement_project_name": str(row["project_name"] or ""),
                        "procurement_reference_no": row["reference_no"],
                        "procurement_publication_date": row["publication_date"],
                        "procurement_created_at": str(row["created_at"]),
                        "procurement_url": row["url"],
                        "suggestion_score": score,
                        "evidence": {
                            "shared_identity_terms": shared[:8],
                            "identity_anchor_score": identity_score,
                            "project_sectors": sorted(project_sectors),
                            "procurement_sector": procurement_sector or None,
                            "sector_match": sector_match,
                            "project_location": project_location or None,
                            "procurement_location": procurement_location or None,
                            "location_match": location_match,
                            "project_issuer": project_issuer or None,
                            "procurement_issuer": procurement_issuer or None,
                            "issuer_match": issuer_match,
                            "procurement_formed_at": formed_at,
                            "temporal_basis": temporal_basis,
                        },
                        "authority": "REVIEW_ONLY_NO_LINK_WRITE",
                        "required_action": "EXPLICIT_PROJECT_LINK_PROCUREMENT_REVIEW",
                    }
                )

            per_project_rows.sort(
                key=lambda item: (
                    -int(item["suggestion_score"]),
                    str(item["procurement_publication_date"] or item["procurement_created_at"]),
                    str(item["procurement_canonical_key"]),
                )
            )
            selected = per_project_rows[:per_project]
            if selected:
                projects_with_suggestions.add(project_key)
                suggestions.extend(selected)

    suggestions.sort(
        key=lambda item: (
            -int(item["suggestion_score"]),
            str(item["project_first_detected_at"]),
            str(item["project_key"]),
            str(item["procurement_canonical_key"]),
        )
    )
    tracked_projects = len(first_events)
    linked_project_count = len(linked_projects)
    return {
        "metric": "PROJECT_PROCUREMENT_LINK_REVIEW_QUEUE",
        "summary": {
            "tracked_projects": tracked_projects,
            "already_linked_projects": linked_project_count,
            "unlinked_projects": max(0, tracked_projects - linked_project_count),
            "projects_with_suggestions": len(projects_with_suggestions),
            "suggestions": len(suggestions),
            "returned_suggestions": min(limit, len(suggestions)),
        },
        "suggestions": suggestions[:limit],
        "semantics": {
            "review_only": True,
            "suggestion_score_is_ranking_not_probability": True,
            "no_link_write": True,
            "human_review_required": True,
            "explicit_link_command_remains_authoritative": True,
            "procurement_must_not_predate_first_detection": True,
            "sector_location_issuer_are_supporting_not_authoritative": True,
            "fuzzy_automatic_linking_prohibited": True,
        },
    }


def leadtime_report(*, database: Path | None = None, limit: int = 100) -> dict[str, object]:
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    target = database or db_path()
    migrate(target)
    rows: list[dict[str, object]] = []
    with connect(target) as conn:
        tracked_projects = int(
            conn.execute("SELECT COUNT(DISTINCT project_key) FROM project_lifecycle_events").fetchone()[0]
        )
        linked = conn.execute(
            """
            SELECT l.project_key,l.canonical_key,l.link_basis,l.linked_by,
                   c.title,c.publication_date,c.created_at
            FROM project_procurement_links l
            JOIN canonical_items c ON c.canonical_key=l.canonical_key
            ORDER BY c.created_at DESC
            """
        ).fetchall()
        linked_projects_total = len(linked)
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
            first_at = _parse(str(first["detected_at"]))
            lead_days, procurement_reference, basis, precision = _lead_measurement(
                first_at=first_at,
                publication_date=row["publication_date"],
                canonical_created_at=str(row["created_at"]),
            )
            rows.append(
                {
                    "project_key": str(row["project_key"]),
                    "canonical_key": str(row["canonical_key"]),
                    "procurement_title": str(row["title"] or ""),
                    "first_detected_at": str(first["detected_at"]),
                    "first_stage": str(first["stage"]),
                    "first_source_id": str(first["source_id"]),
                    "procurement_formed_at": procurement_reference,
                    "procurement_publication_date": row["publication_date"],
                    "canonical_ingested_at": str(row["created_at"]),
                    "leadtime_basis": basis,
                    "leadtime_precision": precision,
                    "lead_days": lead_days,
                    "link_basis": str(row["link_basis"]),
                }
            )

    lead_days = [float(row["lead_days"]) for row in rows]
    stage_breakdown: dict[str, dict[str, object]] = {}
    for stage in STAGES:
        stage_values = [float(row["lead_days"]) for row in rows if row["first_stage"] == stage]
        if not stage_values:
            continue
        stage_breakdown[stage] = {
            "projects": len(stage_values),
            "median_lead_days": _median(stage_values),
            "mean_lead_days": round(sum(stage_values) / len(stage_values), 2),
        }

    official_basis = sum(1 for row in rows if str(row["leadtime_basis"]).startswith("OFFICIAL_PUBLICATION_"))
    fallback_basis = sum(1 for row in rows if row["leadtime_basis"] == "CANONICAL_CREATED_AT_FALLBACK")
    measured = len(rows)
    summary = {
        "tracked_projects": tracked_projects,
        "linked_projects_total": linked_projects_total,
        "linked_projects": measured,
        "measurement_coverage_rate": round(measured / tracked_projects, 4) if tracked_projects else None,
        "official_publication_basis_projects": official_basis,
        "ingestion_fallback_projects": fallback_basis,
        "median_lead_days": _median(lead_days),
        "mean_lead_days": round(sum(lead_days) / measured, 2) if measured else None,
        "min_lead_days": round(min(lead_days), 2) if measured else None,
        "max_lead_days": round(max(lead_days), 2) if measured else None,
        "first_stage_breakdown": stage_breakdown,
        "returned_projects": min(limit, measured),
    }
    return {
        "metric": "PROJECT_TO_PROCUREMENT_LEAD_TIME",
        "summary": summary,
        "projects": rows[:limit],
        "semantics": {
            "headline_basis": "FIRST_RECORDED_PRECURSOR_TO_OFFICIAL_PROCUREMENT_PUBLICATION",
            "publication_date_preferred_over_ingestion_time": True,
            "date_only_publication_precision": "MYANMAR_CALENDAR_DAY",
            "fallback": "CANONICAL_CREATED_AT_ONLY_WHEN_OFFICIAL_PUBLICATION_DATE_IS_UNAVAILABLE_OR_INVALID",
            "sample_scope": "EXPLICITLY_REVIEWED_PROJECT_PROCUREMENT_LINKS_ONLY",
            "measurement_coverage_is_not_conversion_rate": True,
        },
    }
