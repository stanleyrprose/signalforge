from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .iwt import parse_tender_detail as parse_iwt_tender_detail
from .iwt import parse_tender_listing as parse_iwt_tender_listing
from .moep import parse_tender_detail as parse_moep_tender_detail
from .moep import parse_tender_listing as parse_moep_tender_listing
from .mpt import SitemapEntry, parse_sitemap, parse_tender_detail as parse_mpt_tender_detail
from .railways import parse_tender_detail as parse_railways_tender_detail
from .railways import parse_tender_listing


class SourceAdapterError(RuntimeError):
    pass


DiscoveryParser = Callable[[bytes], list[SitemapEntry]]
DetailParser = Callable[[bytes, str], list[object]]


@dataclass(frozen=True)
class SourceAdapter:
    name: str
    discovery_content_types: tuple[str, ...]
    discovery_parser_version: str
    detail_parser_version: str
    normalizer_version: str
    canonicalizer_version: str
    parse_discovery: DiscoveryParser
    parse_detail: DetailParser


def _parse_mpt_detail(payload: bytes, url: str) -> list[object]:
    tender = parse_mpt_tender_detail(payload, url)
    return [tender] if tender is not None else []


def _parse_iwt_detail(payload: bytes, url: str) -> list[object]:
    tender = parse_iwt_tender_detail(payload, url)
    return [tender] if tender is not None else []


def _parse_moep_detail(payload: bytes, url: str) -> list[object]:
    tender = parse_moep_tender_detail(payload, url)
    return [tender] if tender is not None else []


ADAPTERS = {
    "mpt": SourceAdapter(
        name="mpt",
        discovery_content_types=("application/xml", "text/xml"),
        discovery_parser_version="mpt-sitemap-v1",
        detail_parser_version="mpt-v3",
        normalizer_version="mpt-normalize-v1",
        canonicalizer_version="tender-canonical-v1",
        parse_discovery=parse_sitemap,
        parse_detail=_parse_mpt_detail,
    ),
    "railways": SourceAdapter(
        name="railways",
        discovery_content_types=("text/html",),
        discovery_parser_version="railways-list-v1",
        detail_parser_version="railways-v1",
        normalizer_version="railways-normalize-v1",
        canonicalizer_version="railways-reference-v1",
        parse_discovery=parse_tender_listing,
        parse_detail=parse_railways_tender_detail,
    ),
    "iwt": SourceAdapter(
        name="iwt",
        discovery_content_types=("text/html",),
        discovery_parser_version="iwt-list-v1",
        detail_parser_version="iwt-v1",
        normalizer_version="iwt-normalize-v1",
        canonicalizer_version="iwt-node-date-v1",
        parse_discovery=parse_iwt_tender_listing,
        parse_detail=_parse_iwt_detail,
    ),
    "moep": SourceAdapter(
        name="moep",
        discovery_content_types=("text/html",),
        discovery_parser_version="moep-category-v1",
        detail_parser_version="moep-html-v1",
        normalizer_version="moep-normalize-v1",
        canonicalizer_version="moep-content-date-v1",
        parse_discovery=parse_moep_tender_listing,
        parse_detail=_parse_moep_detail,
    ),
}


def adapter_for(source_id: str, source: dict) -> SourceAdapter:
    name = source.get("adapter")
    if not isinstance(name, str) or name not in ADAPTERS:
        raise SourceAdapterError(f"unsupported source adapter: {source_id}")
    return ADAPTERS[name]
