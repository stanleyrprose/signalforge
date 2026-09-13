from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from .mpt import normalize_text

API_URL = "https://www.atom.com.mm/api/v1/medias?locale=en&search=5G&page=1"
ISSUER = "ATOM Myanmar"
SELECTION_POLICY_VERSION = 1
_NETWORK_TOKENS = (
    "5g", "4g", "4.5g", "lte", "network", "fiber", "fibre", "ftth", "core network",
    "transport network", "radio network", "cloud-based infrastructure", "cloud infrastructure",
    "infrastructure", "coverage", "network site", "base station", "spectrum", "backhaul",
    "network readiness", "connectivity expansion", "network expansion", "network upgrade",
)


class AtomNetworkParseError(ValueError):
    pass


def _is_network_notice(value: str) -> bool:
    lower = normalize_text(value).lower()
    return any(token in lower for token in _NETWORK_TOKENS)


def _url(kind: int, slug: str) -> str:
    route = {1: "article", 2: "press-release", 3: "statement"}.get(kind, "article")
    return f"https://www.atom.com.mm/en/{route}/{slug}"


@dataclass(frozen=True)
class AtomNetworkNotice:
    record_id: str
    title: str
    publication_date: str
    scope_summary: str
    url: str

    item_kind = "REGULATORY_NOTICE"
    deadline = None
    location = "Myanmar"

    @property
    def reference_no(self) -> str:
        return f"ATOM-MEDIA-{self.record_id}"

    @property
    def project_name(self) -> str:
        return self.title

    @property
    def canonical_key(self) -> str:
        return f"atom-network:{self.record_id}"

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": ISSUER,
            "title": self.title,
            "reference_no": self.reference_no,
            "reference_no_kind": "official_media_id",
            "source_record_id": self.record_id,
            "publication_date": self.publication_date,
            "deadline": None,
            "location": self.location,
            "scope_summary": self.scope_summary,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "STRATEGIC_INTELLIGENCE",
            "relevance_categories": ["TELECOM"],
            "telecom_signal_kind": "NETWORK_TECHNOLOGY",
            "detail_completeness": "OFFICIAL_JSON_MEDIA_METADATA",
            "url": self.url,
        }


def parse_network_records(payload: bytes, page_url: str = API_URL) -> list[AtomNetworkNotice]:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AtomNetworkParseError("ATOM media API is not valid JSON") from exc
    media = raw.get("media") if isinstance(raw, dict) else None
    data = media.get("data") if isinstance(media, dict) else None
    if not isinstance(data, list):
        raise AtomNetworkParseError("ATOM media API data structure not found")
    selected: list[AtomNetworkNotice] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        record_id = str(row.get("id") or "")
        slug = str(row.get("slug") or "")
        title = normalize_text(str(row.get("title") or ""))
        description = normalize_text(str(row.get("description") or ""))
        keywords = normalize_text(str(row.get("keywords") or ""))
        if not record_id or not slug or not title or not _is_network_notice(" ".join((title, description, keywords))):
            continue
        publish_time = str(row.get("publish_time") or "")
        publication = ""
        if publish_time:
            try:
                publication = datetime.fromisoformat(publish_time).date().isoformat()
            except ValueError:
                publication = ""
        if not publication:
            try:
                publication = datetime.strptime(str(row.get("date") or ""), "%d %b, %Y").date().isoformat()
            except ValueError:
                continue
        type_raw = row.get("type")
        kind = int(type_raw.get("key") or 1) if isinstance(type_raw, dict) else 1
        scope = description or keywords or title
        selected.append(AtomNetworkNotice(record_id, title, publication, scope[:3000], _url(kind, slug)))
    return selected
