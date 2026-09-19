from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .config import db_path, evidence_root

NOISE_SHADOW_VERSION = 0
DEFAULT_MODEL = "jev-latest"
DEFAULT_OPEN_THRESHOLD = 0.50
DEFAULT_SECTOR_THRESHOLD = 0.60
NOISE_SHADOW_AUTHORITY = "HUMAN_REVIEW_REQUIRED"
PRODUCTION_EFFECT = "NONE"
SUPPORTED_STATUSES = {"PENDING", "CONFIRMED_NOISE", "FALSE_NEGATIVE", "INCONCLUSIVE"}

NoiseEvaluator = Callable[[dict[str, object]], dict[str, object]]


class _EvidenceTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def _html_text(path: Path, *, max_chars: int = 18_000) -> str:
    parser = _EvidenceTextParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()[:max_chars]


def noise_review_recommended(
    *,
    open_actionable: float,
    mission_sector: float,
    page_state: str,
    open_threshold: float = DEFAULT_OPEN_THRESHOLD,
    sector_threshold: float = DEFAULT_SECTOR_THRESHOLD,
) -> bool:
    if not 0.0 <= open_threshold <= 1.0:
        raise ValueError("Jev noise-shadow open threshold must be between 0 and 1")
    if not 0.0 <= sector_threshold <= 1.0:
        raise ValueError("Jev noise-shadow sector threshold must be between 0 and 1")
    return (
        open_actionable >= open_threshold
        and mission_sector >= sector_threshold
        and page_state == "contains_open_opportunity"
    )


def _resolve_artifact(
    *,
    source_id: str,
    payload: dict[str, object],
    evidence_directory: Path,
) -> Path | None:
    raw_value = payload.get("artifact_path")
    if not isinstance(raw_value, str) or not raw_value:
        return None

    raw = Path(raw_value)
    if raw.is_file():
        return raw

    candidate = evidence_directory / source_id / raw.name
    if candidate.is_file():
        return candidate

    marker = "/srv/signalforge/evidence/"
    if raw_value.startswith(marker):
        remapped = evidence_directory / raw_value[len(marker) :]
        if remapped.is_file():
            return remapped
    return None


def _sample_state(
    row: sqlite3.Row,
    *,
    evidence_directory: Path,
) -> tuple[dict[str, object] | None, str]:
    try:
        payload = json.loads(str(row["payload_json"] or "{}"))
    except json.JSONDecodeError:
        return None, "INVALID_PAYLOAD_JSON"
    if not isinstance(payload, dict):
        return None, "INVALID_PAYLOAD_JSON"

    state: dict[str, object] = {
        "source_id": str(row["source_id"]),
        "candidate_kind": str(row["candidate_kind"]),
        "evidence_url": row["evidence_url"],
        "processed_at": payload.get("finished_at") or row["sampled_at"],
    }

    kind = str(row["candidate_kind"])
    if kind == "ZERO_ITEM_PROCESSING":
        artifact = _resolve_artifact(
            source_id=str(row["source_id"]),
            payload=payload,
            evidence_directory=evidence_directory,
        )
        if artifact is None:
            return None, "EVIDENCE_NOT_AVAILABLE"
        if artifact.suffix.lower() not in {".html", ".htm"}:
            return None, "UNSUPPORTED_EVIDENCE_TYPE"
        state["artifact_sha256"] = payload.get("artifact_sha256")
        state["evidence_text"] = _html_text(artifact)
        if not state["evidence_text"]:
            return None, "EMPTY_EVIDENCE_TEXT"
        return state, "EVIDENCE_READY"

    if kind == "INDEPENDENT_LISTING_NONSTANDARD":
        title = payload.get("title")
        url = payload.get("url")
        if not isinstance(title, str) or not title.strip():
            return None, "TITLE_NOT_AVAILABLE"
        state["title"] = title.strip()
        if isinstance(url, str) and url:
            state["listing_url"] = url
        return state, "EVIDENCE_READY"

    if kind == "KNOWN_HISTORICAL_SIGNAL_NOISE":
        return None, "SEMANTIC_EVIDENCE_INSUFFICIENT"

    return None, "UNSUPPORTED_CANDIDATE_KIND"


def _noise_questions():
    try:
        from typesafe_sdk import Choice, Noul
    except ImportError as exc:  # pragma: no cover - explicit runtime-only dependency
        raise RuntimeError(
            "Jev noise-shadow mode requires the optional 'typesafe-sdk' package; "
            "core SignalForge does not depend on it"
        ) from exc

    return {
        "open_actionable": Noul(
            instructions=(
                "At processed_at, did this official evidence contain at least one specific commercial opportunity "
                "that an external business could still act on at that time? Use deadline/date evidence relative "
                "to processed_at. Include open procurement/tenders and explicit open tender/auction/lease events. "
                "Do not count tender awards/results, evaluation/opening notices, jobs, general news, tentative "
                "programmes, or opportunities already expired/closed before processed_at."
            )
        ),
        "mission_sector": Noul(
            instructions=(
                "Does the actionable opportunity itself materially fit SignalForge's main mission: engineering "
                "projects/equipment/services, construction/civil/infrastructure, telecommunications or ICT "
                "infrastructure, or energy/power/oil-and-gas infrastructure? Exclude medical, office/consumer "
                "goods, ordinary commodities/raw materials, unrelated administration, and non-opportunity pages."
            )
        ),
        "page_state": Choice(
            instructions=(
                "Classify the evidence relative to processed_at. If a listing contains multiple records, choose "
                "contains_open_opportunity when at least one specific relevant commercial opportunity is still "
                "open/actionable."
            ),
            criteria={
                "contains_open_opportunity": (
                    "At least one specific opportunity is still open/actionable at processed_at."
                ),
                "expired_or_closed": (
                    "Opportunity evidence exists but relevant opportunities are already expired/closed."
                ),
                "post_bid_result": (
                    "The evidence is primarily award/result/evaluation/opening-stage material."
                ),
                "non_opportunity": "No concrete commercial opportunity is present.",
                "unclear": "Evidence is insufficient or internally ambiguous.",
            },
        ),
    }


def _typesafe_noise_evaluator(*, model: str, api_key: str) -> tuple[NoiseEvaluator, Any]:
    try:
        from typesafe_sdk import TypeSafeClient
    except ImportError as exc:  # pragma: no cover - explicit runtime-only dependency
        raise RuntimeError(
            "Jev noise-shadow mode requires the optional 'typesafe-sdk' package; "
            "core SignalForge does not depend on it"
        ) from exc

    client = TypeSafeClient(api_key=api_key, model=model)
    questions = _noise_questions()

    def evaluate(state: dict[str, object]) -> dict[str, object]:
        result = client.system_one(state=state, questions=questions)
        return {
            "open_actionable": float(result.nouls["open_actionable"].noul),
            "mission_sector": float(result.nouls["mission_sector"].noul),
            "page_state": str(result.choices["page_state"].choice),
            "page_state_confidence": float(result.choices["page_state"].confidence),
            "page_state_probabilities": dict(result.choices["page_state"].probabilities),
            "request_id": result.request_id,
            "model": result.model,
            "usage": result.usage.model_dump(),
        }

    return evaluate, client


def _reviewed_confusion(rows: list[dict[str, object]]) -> dict[str, int]:
    tp = fp = tn = fn = 0
    for row in rows:
        if row.get("evidence_status") != "EVIDENCE_READY":
            continue
        status = str(row.get("review_status") or "")
        if status not in {"CONFIRMED_NOISE", "FALSE_NEGATIVE"}:
            continue
        predicted = bool(row.get("review_recommended"))
        expected = status == "FALSE_NEGATIVE"
        if predicted and expected:
            tp += 1
        elif predicted:
            fp += 1
        elif expected:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def jev_noise_shadow_report(
    *,
    database: Path | None = None,
    evidence_directory: Path | None = None,
    status: str | None = "PENDING",
    limit: int = 50,
    open_threshold: float = DEFAULT_OPEN_THRESHOLD,
    sector_threshold: float = DEFAULT_SECTOR_THRESHOLD,
    model: str = DEFAULT_MODEL,
    evaluator: NoiseEvaluator | None = None,
    api_key: str | None = None,
) -> dict[str, object]:
    if status is not None and status not in SUPPORTED_STATUSES:
        raise ValueError("invalid noise review status")
    if limit < 1 or limit > 500:
        raise ValueError("Jev noise-shadow limit must be between 1 and 500")
    if not 0.0 <= open_threshold <= 1.0:
        raise ValueError("Jev noise-shadow open threshold must be between 0 and 1")
    if not 0.0 <= sector_threshold <= 1.0:
        raise ValueError("Jev noise-shadow sector threshold must be between 0 and 1")

    target = database or db_path()
    evidence_dir = evidence_directory or evidence_root()
    uri = f"file:{target}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        if status is None:
            samples = conn.execute(
                "SELECT * FROM noise_review_samples ORDER BY sampled_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            samples = conn.execute(
                "SELECT * FROM noise_review_samples WHERE review_status=? ORDER BY sampled_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()

    client = None
    if evaluator is None:
        resolved_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "Jev noise-shadow mode requires TYPESAFE_API_KEY; "
                "no production credential fallback is allowed"
            )
        evaluator, client = _typesafe_noise_evaluator(model=model, api_key=resolved_key)

    rows: list[dict[str, object]] = []
    try:
        for sample in samples:
            state, evidence_status = _sample_state(
                sample,
                evidence_directory=evidence_dir,
            )
            base: dict[str, object] = {
                "noise_sample_id": str(sample["noise_sample_id"]),
                "source_id": str(sample["source_id"]),
                "candidate_kind": str(sample["candidate_kind"]),
                "candidate_ref": str(sample["candidate_ref"]),
                "review_status": str(sample["review_status"]),
                "sampled_at": str(sample["sampled_at"]),
                "evidence_status": evidence_status,
            }
            if state is None:
                rows.append(
                    {
                        **base,
                        "review_recommended": False,
                        "recommendation": "SKIPPED_INSUFFICIENT_EVIDENCE",
                        "jev": None,
                    }
                )
                continue

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
            rows.append(
                {
                    **base,
                    "review_recommended": recommended,
                    "recommendation": "REVIEW_RECOMMENDED" if recommended else "NO_JEV_ESCALATION",
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

    evaluated = [row for row in rows if row["evidence_status"] == "EVIDENCE_READY"]
    skipped = [row for row in rows if row["evidence_status"] != "EVIDENCE_READY"]
    recommended = [row for row in evaluated if row["review_recommended"]]

    return {
        "status": "SHADOW_ONLY",
        "shadow_version": NOISE_SHADOW_VERSION,
        "authority": NOISE_SHADOW_AUTHORITY,
        "production_effect": PRODUCTION_EFFECT,
        "writes": "NONE",
        "model_requested": model,
        "thresholds": {
            "open_actionable": open_threshold,
            "mission_sector": sector_threshold,
            "required_page_state": "contains_open_opportunity",
        },
        "scope": {
            "surface": "ASSURANCE_NOISE_REVIEW_SAMPLES",
            "review_status_filter": status or "ALL",
            "limit": limit,
            "automatic_false_negative_write": False,
            "automatic_missed_signal_write": False,
        },
        "counts": {
            "tracked": len(samples),
            "evaluated": len(evaluated),
            "skipped": len(skipped),
            "review_recommended": len(recommended),
        },
        "reviewed_confusion": _reviewed_confusion(rows),
        "rows": rows,
    }
