from __future__ import annotations

from typing import Any

QUALIFICATION_POLICY_VERSION = 1

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "TELECOM": (
        "telecom",
        "telecommunication",
        "mobile network",
        "bts",
        "fiber",
        "fibre",
        "antenna",
        "radio frequency",
        " rf ",
    ),
    "ICT": (
        "data center",
        "data server",
        "server",
        "software",
        "computer",
        "information technology",
        " ict ",
        "windows server",
        "sql server",
        "iot",
        "network equipment",
        "network infrastructure",
        "scanner",
    ),
    "ENERGY": (
        "energy",
        "electricity",
        "electric power",
        "power system",
        "power generation",
        "power transmission",
        "petroleum",
        "line pipe",
        "transmission",
    ),
    "INDUSTRIAL": (
        "industrial",
        "industry",
        "chemical",
        "machinery",
        "mechanical",
        "spare part",
        "steel",
        "refractory",
        "scrap",
        "lubricant",
        "equipment",
    ),
    "MEDICAL": (
        "medical",
        "hospital",
        "health",
        "ct ",
        "mri",
        "fibroscan",
        "surgical",
    ),
    "CONSTRUCTION": (
        "construction",
        "renovation",
        "building",
        "civil work",
        "housing",
    ),
}

_SOURCE_CATEGORY_FALLBACK = {
    "S26": "MEDICAL",
    "S38": "INDUSTRIAL",
    "S39": "ENERGY",
}

_PRIMARY_RELEVANCE_ORDER = ("TELECOM", "ICT", "ENERGY", "INDUSTRIAL", "MEDICAL", "CONSTRUCTION")


def _has_business_scope(item: dict[str, object]) -> bool:
    scope = item.get("scope_summary")
    return isinstance(scope, str) and len(scope.strip()) >= 20


def _evidence_level(item: dict[str, object], source_policy: dict[str, Any] | None) -> str:
    completeness = str(item.get("detail_completeness") or "").upper()
    deadline_evidence = str(item.get("deadline_evidence") or "").upper()
    if "TEXT_PDF" in completeness or deadline_evidence.startswith("OFFICIAL_TEXT_NATIVE_PDF"):
        return "OFFICIAL_HTML_PLUS_TEXT_PDF"
    if str((source_policy or {}).get("engine") or "") == "provider":
        return "OFFICIAL_HTML_VIA_PROVIDER"
    return "OFFICIAL_HTML"


def _relevance_categories(item: dict[str, object], source_policy: dict[str, Any] | None) -> list[str]:
    text = " ".join(
        str(value or "")
        for value in (
            item.get("title"),
            item.get("scope_summary"),
            item.get("issuer"),
            item.get("reference_no"),
            (source_policy or {}).get("name"),
        )
    ).lower()
    padded = f" {text} "
    categories = [category for category, words in _KEYWORDS.items() if any(word in padded for word in words)]
    fallback = _SOURCE_CATEGORY_FALLBACK.get(str(item.get("source_id") or ""))
    if fallback and fallback not in categories:
        categories.append(fallback)
    if not categories:
        categories.append("OTHER")
    return [category for category in _PRIMARY_RELEVANCE_ORDER if category in categories] + [
        category for category in categories if category not in _PRIMARY_RELEVANCE_ORDER
    ]


def qualify_opportunity(item: dict[str, object], source_policy: dict[str, Any] | None = None) -> dict[str, object]:
    deadline_status = str(item.get("deadline_status") or "UNKNOWN")
    opportunity_status = str(item.get("opportunity_status") or deadline_status)
    remaining = item.get("remaining_seconds")
    if opportunity_status == "EXPIRED":
        urgency = "EXPIRED"
    elif not isinstance(remaining, int):
        urgency = "UNKNOWN"
    elif remaining <= 72 * 3600:
        urgency = "URGENT"
    elif remaining <= 7 * 24 * 3600:
        urgency = "SOON"
    else:
        urgency = "NORMAL"

    evidence_level = _evidence_level(item, source_policy)
    scope_present = _has_business_scope(item)
    explicit_deadline = deadline_status != "UNKNOWN"
    explicit_action_date = bool(item.get("action_date")) and bool(item.get("action_date_evidence"))
    deadline_evidence = bool(item.get("deadline_evidence")) or "DEADLINE" in str(item.get("detail_completeness") or "").upper()

    if scope_present and explicit_deadline and deadline_evidence:
        completeness = "FULL"
        trust_grade = "A"
    elif scope_present or item.get("reference_numbers") or item.get("reference_no"):
        completeness = "PARTIAL"
        trust_grade = "B"
    else:
        completeness = "MINIMAL"
        trust_grade = "C"

    relevance_categories = _relevance_categories(item, source_policy)
    primary_relevance = relevance_categories[0]
    strategic = any(category in {"ICT", "TELECOM"} for category in relevance_categories)

    if opportunity_status == "EXPIRED" or trust_grade == "C":
        priority_band = "LOW"
    elif opportunity_status == "OPEN" and trust_grade == "A" and (strategic or urgency == "URGENT"):
        priority_band = "HIGH"
    elif opportunity_status == "OPEN" and trust_grade == "A":
        priority_band = "MEDIUM"
    else:
        priority_band = "REVIEW"

    reasons = ["SIGNAL_BACKED_CANONICAL", evidence_level]
    if str((source_policy or {}).get("engine") or "") == "provider":
        reasons.append("PROVIDER_ACQUISITION")
    reasons.append("BUSINESS_SCOPE_PRESENT" if scope_present else "BUSINESS_SCOPE_PARTIAL")
    if explicit_deadline:
        reasons.append("EXPLICIT_DEADLINE")
    elif explicit_action_date:
        reasons.append("EXPLICIT_ACTION_DATE")
    else:
        reasons.append("DEADLINE_UNKNOWN")
    if int(item.get("reference_count") or 0) > 1:
        reference_evidence = str(item.get("reference_numbers_evidence") or "")
        if reference_evidence == "HTML_TITLE":
            reasons.append("MULTI_REFERENCE_HTML_TITLE")
        elif reference_evidence.startswith("OFFICIAL_TEXT_NATIVE_PDF_SCOPE_"):
            reasons.append("MULTI_REFERENCE_OFFICIAL_PDF_SCOPE")
        else:
            reasons.append("MULTI_REFERENCE_EVIDENCE")

    return {
        "qualification_policy_version": QUALIFICATION_POLICY_VERSION,
        "trust_grade": trust_grade,
        "actionability": opportunity_status,
        "urgency": urgency,
        "evidence_level": evidence_level,
        "completeness": completeness,
        "relevance_categories": relevance_categories,
        "primary_relevance": primary_relevance,
        "priority_band": priority_band,
        "qualification_reasons": reasons,
        "source_engine": str((source_policy or {}).get("engine") or "unknown"),
    }
