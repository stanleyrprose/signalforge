from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


class BusinessProfileError(RuntimeError):
    pass


def _strings(value: object, *, upper: bool = False) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise BusinessProfileError("profile list fields must be JSON arrays")
    result: list[str] = []
    for raw in value:
        text = str(raw).strip()
        if not text:
            continue
        normalized = text.upper() if upper else text.lower()
        if normalized not in result:
            result.append(normalized)
    return tuple(result)


@dataclass(frozen=True)
class BusinessProfile:
    profile_id: str
    name: str
    delivery_mode: str
    relevance_categories: tuple[str, ...]
    keywords: tuple[str, ...]
    buyer_keywords: tuple[str, ...]
    exclude_keywords: tuple[str, ...]
    minimum_score: int

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "BusinessProfile":
        profile_id = str(value.get("profile_id") or "").strip()
        name = str(value.get("name") or profile_id).strip()
        if not profile_id:
            raise BusinessProfileError("profile_id is required")
        if not name:
            raise BusinessProfileError("profile name is required")

        delivery_mode = str(value.get("delivery_mode") or "ALL_TENDERS").upper()
        if delivery_mode not in {"ALL_TENDERS", "MATCHED_ONLY"}:
            raise BusinessProfileError("delivery_mode must be ALL_TENDERS or MATCHED_ONLY")

        score = value.get("minimum_score", 45)
        if not isinstance(score, int) or not 1 <= score <= 100:
            raise BusinessProfileError("minimum_score must be an integer between 1 and 100")

        profile = cls(
            profile_id=profile_id,
            name=name,
            delivery_mode=delivery_mode,
            relevance_categories=_strings(value.get("relevance_categories"), upper=True),
            keywords=_strings(value.get("keywords")),
            buyer_keywords=_strings(value.get("buyer_keywords")),
            exclude_keywords=_strings(value.get("exclude_keywords")),
            minimum_score=score,
        )
        if (
            profile.delivery_mode == "MATCHED_ONLY"
            and not profile.relevance_categories
            and not profile.keywords
            and not profile.buyer_keywords
        ):
            raise BusinessProfileError("MATCHED_ONLY profile requires at least one positive matching rule")
        return profile


def load_business_profile(path: Path | None = None) -> BusinessProfile | None:
    configured = str(path) if path is not None else os.environ.get("SIGNALFORGE_BUSINESS_PROFILE", "")
    if not configured:
        return None
    target = Path(configured).expanduser()
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BusinessProfileError(f"cannot load business profile: {exc}") from exc
    if not isinstance(value, dict):
        raise BusinessProfileError("business profile root must be a JSON object")
    return BusinessProfile.from_dict(value)


def match_tender(item: dict[str, object], profile: BusinessProfile) -> dict[str, object]:
    categories = tuple(
        str(value).upper()
        for value in (item.get("relevance_categories") or [])
        if str(value).strip()
    )
    category_hits = [value for value in profile.relevance_categories if value in categories]

    searchable = " ".join(
        str(item.get(field) or "")
        for field in (
            "title",
            "scope_excerpt",
            "quantity_or_lot_summary",
            "price_or_budget_summary",
            "location",
            "reference_no",
        )
    ).lower()
    issuer = str(item.get("issuer") or "").lower()

    keyword_hits = [value for value in profile.keywords if value in searchable]
    buyer_hits = [value for value in profile.buyer_keywords if value in issuer]
    excluded_hits = [value for value in profile.exclude_keywords if value in searchable or value in issuer]

    score = 0
    if category_hits:
        score += 45
    if keyword_hits:
        score += min(45, 30 + 5 * (len(keyword_hits) - 1))
    if buyer_hits:
        score += 20
    score = min(score, 100)

    if excluded_hits:
        eligible = False
    elif profile.delivery_mode == "ALL_TENDERS":
        eligible = True
    else:
        eligible = score >= profile.minimum_score

    summary_parts: list[str] = []
    if category_hits:
        summary_parts.append("/".join(category_hits))
    if keyword_hits:
        summary_parts.append("产品命中 " + ", ".join(keyword_hits[:5]))
    if buyer_hits:
        summary_parts.append("目标买方命中 " + ", ".join(buyer_hits[:3]))
    if excluded_hits:
        summary_parts.append("排除词命中 " + ", ".join(excluded_hits[:3]))

    return {
        "profile_id": profile.profile_id,
        "profile_name": profile.name,
        "delivery_mode": profile.delivery_mode,
        "score": score,
        "minimum_score": profile.minimum_score,
        "eligible": eligible,
        "category_hits": category_hits,
        "keyword_hits": keyword_hits,
        "buyer_hits": buyer_hits,
        "excluded_hits": excluded_hits,
        "summary": "；".join(summary_parts),
    }
