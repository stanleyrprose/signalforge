from __future__ import annotations

from typing import Any
import re

SIGNAL_QUALITY_MODEL_VERSION = 1

_BANDS = (
    (85, "VERY_HIGH"),
    (70, "HIGH"),
    (55, "MEDIUM"),
    (40, "REVIEW"),
    (0, "LOW"),
)

_QUANTITY_PATTERN = re.compile(
    r"[\(\[]?\s*[0-9၀-၉][0-9၀-၉,./-]*\s*[\)\]]?\s*"
    r"(?:lots?|sets?|nos?|items?|groups?|tons?|meters?|metres?|kva|kw|sft|မျိုး|စီး|လုံး|ခု|စုံ|တန်|ပေ)",
    flags=re.I,
)

_LOCATION_TOKENS = (
    "တင်ဒါတင်သွင်းရမည့်နေရာ", "တင်ဒါသွင်းရမည့်နေရာ", "နေပြည်တော်", "ရန်ကုန်", "မန္တလေး",
    "nay pyi taw", "naypyitaw", "yangon", "mandalay", "submission place", "submission address",
)

_ACTION_TOKENS = (
    "တင်ဒါတင်သွင်း", "တင်ဒါသွင်း", "တင်သွင်းရန်", "ဈေးနှုန်းလွှာ", "ဝယ်ယူနိုင်", "ဖိတ်ခေါ်",
    "submit", "submission", "quotation", "tender form", "contact", "apply", "application",
)

_RELEVANCE_SCORES = {
    "TELECOM": 10,
    "ICT": 10,
    "ENERGY": 7,
    "INDUSTRIAL": 6,
    "MEDICAL": 5,
    "CONSTRUCTION": 4,
    "OTHER": 2,
}

_URGENCY_SCORES = {"URGENT": 5, "SOON": 3, "NORMAL": 1, "UNKNOWN": 0, "EXPIRED": 0}


def _text(item: dict[str, object]) -> str:
    return " ".join(str(item.get(key) or "") for key in ("title", "scope_summary", "focus_scope_summary")).lower()


def _present(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _band(score: int) -> str:
    for threshold, name in _BANDS:
        if score >= threshold:
            return name
    return "LOW"


def _dimension(score: int, maximum: int, evidence: str) -> dict[str, object]:
    return {"score": score, "max": maximum, "evidence": evidence}


def score_signal_quality(item: dict[str, object], source_policy: dict[str, Any] | None = None) -> dict[str, object]:
    """Deterministic read-model score for business-action quality.

    This score is intentionally independent from priority_band. It describes how
    complete/actionable the evidence is, not whether the user should be interrupted.
    """
    dimensions: dict[str, dict[str, object]] = {}
    strengths: list[str] = []
    gaps: list[str] = []

    issuer = item.get("issuer")
    issuer_score = 15 if _present(issuer) else 0
    dimensions["issuer"] = _dimension(issuer_score, 15, "EXPLICIT_ISSUER" if issuer_score else "MISSING_ISSUER")
    (strengths if issuer_score else gaps).append("ISSUER_KNOWN" if issuer_score else "ISSUER_MISSING")

    text = _text(item)
    scope_present = _present(item.get("scope_summary")) or _present(item.get("focus_scope_summary"))
    quantity_specific = scope_present and _QUANTITY_PATTERN.search(text) is not None
    scope_score = (10 if scope_present else 0) + (10 if quantity_specific else 0)
    scope_evidence = "SCOPE_AND_QUANTITY" if quantity_specific else ("SCOPE_ONLY" if scope_present else "MISSING_SCOPE")
    dimensions["scope_quantity"] = _dimension(scope_score, 20, scope_evidence)
    if quantity_specific:
        strengths.append("QUANTIFIED_SCOPE")
    elif scope_present:
        strengths.append("BUSINESS_SCOPE_KNOWN")
        gaps.append("QUANTITY_OR_LOT_DETAIL_MISSING")
    else:
        gaps.append("BUSINESS_SCOPE_MISSING")

    deadline_known = str(item.get("deadline_status") or "UNKNOWN") != "UNKNOWN"
    deadline_time_known = _present(item.get("deadline_time")) or "DATETIME" in str(item.get("deadline_evidence") or "").upper()
    action_date_known = _present(item.get("action_date"))
    action_time_known = _present(item.get("action_time"))
    if deadline_known and deadline_time_known:
        time_score, time_evidence = 20, "DEADLINE_DATE_TIME"
    elif deadline_known:
        time_score, time_evidence = 16, "DEADLINE_DATE_ONLY"
    elif action_date_known and action_time_known:
        time_score, time_evidence = 16, "ACTION_DATE_TIME"
    elif action_date_known:
        time_score, time_evidence = 14, "ACTION_DATE_ONLY"
    else:
        time_score, time_evidence = 0, "TIME_UNKNOWN"
    dimensions["time"] = _dimension(time_score, 20, time_evidence)
    if time_score:
        strengths.append("ACTION_TIMEFRAME_KNOWN")
        if time_score < 20:
            gaps.append("EXACT_DEADLINE_TIME_MISSING")
    else:
        gaps.append("ACTION_TIMEFRAME_UNKNOWN")

    explicit_location = _present(item.get("location"))
    scope_location = any(token in text for token in _LOCATION_TOKENS)
    if explicit_location:
        location_score, location_evidence = 10, "STRUCTURED_LOCATION"
    elif scope_location:
        location_score, location_evidence = 7, "LOCATION_IN_SCOPE"
    else:
        location_score, location_evidence = 0, "LOCATION_UNKNOWN"
    dimensions["location"] = _dimension(location_score, 10, location_evidence)
    if location_score:
        strengths.append("LOCATION_KNOWN")
    else:
        gaps.append("LOCATION_MISSING")

    explicit_action = any(token in text for token in _ACTION_TOKENS)
    has_action_clock = deadline_known or action_date_known
    if explicit_action:
        next_action_score, next_action_evidence = 10, "PARTICIPATION_INSTRUCTION_PRESENT"
    elif has_action_clock:
        next_action_score, next_action_evidence = 5, "TIME_BOUND_EVENT_ONLY"
    else:
        next_action_score, next_action_evidence = 0, "NEXT_ACTION_UNKNOWN"
    dimensions["next_action"] = _dimension(next_action_score, 10, next_action_evidence)
    if next_action_score == 10:
        strengths.append("PARTICIPATION_PATH_KNOWN")
    elif next_action_score:
        gaps.append("PARTICIPATION_INSTRUCTION_MISSING")
    else:
        gaps.append("NEXT_ACTION_MISSING")

    evidence_level = str(item.get("evidence_level") or "")
    official = evidence_level.startswith("OFFICIAL_")
    evidence_score = 10 if official else 5 if evidence_level else 0
    dimensions["official_evidence"] = _dimension(evidence_score, 10, evidence_level or "EVIDENCE_UNKNOWN")
    if official:
        strengths.append("OFFICIAL_EVIDENCE")
    else:
        gaps.append("OFFICIAL_EVIDENCE_MISSING")

    categories = [str(v) for v in (item.get("relevance_categories") or [])]
    relevance_score = max((_RELEVANCE_SCORES.get(v, 0) for v in categories), default=0)
    dimensions["strategic_relevance"] = _dimension(relevance_score, 10, ",".join(categories) or "UNCLASSIFIED")
    if relevance_score >= 10:
        strengths.append("ICT_TELECOM_STRATEGIC_FIT")
    elif relevance_score == 0:
        gaps.append("STRATEGIC_RELEVANCE_UNCLASSIFIED")

    urgency = str(item.get("urgency") or "UNKNOWN")
    urgency_score = _URGENCY_SCORES.get(urgency, 0)
    dimensions["urgency"] = _dimension(urgency_score, 5, urgency)
    if urgency in {"URGENT", "SOON"}:
        strengths.append(f"{urgency}_WINDOW")

    score = sum(int(value["score"]) for value in dimensions.values())
    return {
        "signal_quality_model_version": SIGNAL_QUALITY_MODEL_VERSION,
        "signal_quality_score": score,
        "signal_quality_band": _band(score),
        "signal_quality_dimensions": dimensions,
        "signal_quality_strengths": strengths,
        "signal_quality_gaps": gaps,
        "signal_quality_priority_independent": True,
    }
