from __future__ import annotations

from collections.abc import Iterable

MISSION_POLICY_VERSION = 1
MISSION_STATEMENT = (
    "Myanmar government/SOE tenders in engineering, construction, telecommunications/ICT infrastructure, and energy"
)

_DIRECT_TARGET_CATEGORIES = {"ENERGY", "TELECOM", "CONSTRUCTION"}
_ICT_INFRA_TERMS = (
    "server",
    "data center",
    "data centre",
    "network infrastructure",
    "network equipment",
    "router",
    "switch",
    "firewall",
    "vmware",
    "red hat",
    "netapp",
    "veritas",
    "windows server",
    "sql server",
    "scada",
    "ems system",
    "database",
    "iot module",
    "communication and information technology",
    "telecommunication",
    "telecom",
    "fiber",
    "fibre",
    "antenna",
    "gmdss",
)
_ENGINEERING_TERMS = (
    "electrical spare",
    "mechanical spare",
    "electrical material",
    "mechanical material",
    "electrical equipment",
    "mechanical equipment",
    "electrical",
    "mechanical",
    "transformer",
    "substation",
    "conductor",
    "transmission line",
    "line pipe",
    "pump house",
    "pump",
    "generator",
    "turbine",
    "compressor",
    "switchgear",
    "vessel",
    "ship",
    "ရေယာဉ်",
    "bridge",
    "road",
    "highway",
    "building repair",
    "building construction",
    "civil work",
    "earthquake repair",
    "environmental control system",
    "enviromental control system",
    "တည်ဆောက်ခြင်း",
)
_OFF_MISSION_TERMS = (
    "medical",
    "hospital",
    "x-ray",
    "mammography",
    "bronchoscope",
    "laparoscope",
    "dental",
    "colored yarn",
    "colour yarn",
    "chemical reagent",
    "sample gas",
    "refractory",
    "castable mortar",
    "scrap cutting",
    "container truck",
    "transportation service",
    "raw material",
)
_SOURCE_TARGET_FALLBACK = {
    "S13": "TELECOM",
    "S20": "ENERGY",
    "S34": "TELECOM",
    "S39": "ENERGY",
    "S41": "TELECOM",
    "S43": "CONSTRUCTION",
}
_PRIVATE_ISSUER_TERMS = (
    "atom myanmar",
    "atom telecom",
    "ooredoo myanmar",
)


def _text(item: dict[str, object]) -> str:
    values: Iterable[object] = (
        item.get("issuer"),
        item.get("title"),
        item.get("scope_summary"),
        item.get("focus_scope_summary"),
        item.get("project_name"),
        item.get("reference_no"),
        item.get("quantity_or_lot_summary"),
        item.get("next_action_summary"),
    )
    return " ".join(str(value or "") for value in values).lower()


def classify_mission_fit(item: dict[str, object]) -> dict[str, object]:
    """Return a conservative output-only mission classification.

    This does not mutate canonical state or Signal semantics. It is intentionally
    conservative: ambiguous items stay in storage but do not occupy the primary
    government/SOE tender briefing until their business scope proves mission fit.
    """

    text = _text(item)
    issuer = str(item.get("issuer") or "").lower()
    item_kind = str(item.get("item_kind") or "TENDER")
    categories = {str(value) for value in (item.get("relevance_categories") or [])}
    primary = str(item.get("primary_relevance") or "")

    if item_kind != "TENDER":
        return {
            "mission_fit": False,
            "mission_sector": "OUT_OF_SCOPE",
            "mission_reason": f"NON_TENDER:{item_kind or 'UNKNOWN'}",
        }
    if any(term in issuer for term in _PRIVATE_ISSUER_TERMS):
        return {
            "mission_fit": False,
            "mission_sector": "OUT_OF_SCOPE",
            "mission_reason": "PRIVATE_ISSUER",
        }

    direct = _DIRECT_TARGET_CATEGORIES & categories
    if "ENERGY" in direct:
        return {"mission_fit": True, "mission_sector": "ENERGY", "mission_reason": "TARGET_CATEGORY:ENERGY"}
    if "TELECOM" in direct:
        return {"mission_fit": True, "mission_sector": "TELECOM", "mission_reason": "TARGET_CATEGORY:TELECOM"}
    if "CONSTRUCTION" in direct:
        return {
            "mission_fit": True,
            "mission_sector": "CONSTRUCTION",
            "mission_reason": "TARGET_CATEGORY:CONSTRUCTION",
        }

    source_id = str(item.get("source_id") or "")
    source_sector = _SOURCE_TARGET_FALLBACK.get(source_id)
    if source_sector:
        return {
            "mission_fit": True,
            "mission_sector": source_sector,
            "mission_reason": f"TARGET_SOURCE:{source_id}",
        }

    ict_term = next((term for term in _ICT_INFRA_TERMS if term in text), None)
    if ict_term:
        return {
            "mission_fit": True,
            "mission_sector": "TELECOM_ICT_INFRA",
            "mission_reason": f"ICT_INFRA:{ict_term}",
        }
    if "ICT" in categories or primary == "ICT":
        return {
            "mission_fit": False,
            "mission_sector": "OUT_OF_SCOPE",
            "mission_reason": "ICT_NON_INFRA_OR_UNPROVEN",
        }

    # Medical and commodity procurement may contain generic equipment words;
    # fail closed before the engineering-text fallback.
    if "MEDICAL" in categories or primary == "MEDICAL":
        return {"mission_fit": False, "mission_sector": "OUT_OF_SCOPE", "mission_reason": "MEDICAL"}
    off_term = next((term for term in _OFF_MISSION_TERMS if term in text), None)
    if off_term:
        return {
            "mission_fit": False,
            "mission_sector": "OUT_OF_SCOPE",
            "mission_reason": f"OFF_MISSION:{off_term}",
        }

    engineering_term = next((term for term in _ENGINEERING_TERMS if term in text), None)
    if engineering_term:
        return {
            "mission_fit": True,
            "mission_sector": "ENGINEERING",
            "mission_reason": f"ENGINEERING_SCOPE:{engineering_term}",
        }

    return {
        "mission_fit": False,
        "mission_sector": "OUT_OF_SCOPE",
        "mission_reason": "NO_TARGET_SECTOR_EVIDENCE",
    }


def mission_fit(item: dict[str, object]) -> bool:
    return bool(classify_mission_fit(item)["mission_fit"])
