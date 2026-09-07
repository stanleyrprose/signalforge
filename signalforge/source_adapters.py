from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .commerce import parse_notification_detail as parse_commerce_notification_detail
from .commerce import parse_notification_listing as parse_commerce_notification_listing
from .customs import parse_notification_records as parse_customs_notification_records
from .customs_announcements import parse_auction_records as parse_customs_auction_records
from .dast import parse_tender_detail as parse_dast_tender_detail
from .dast import parse_tender_listing as parse_dast_tender_listing
from .dica import parse_announcement_detail as parse_dica_announcement_detail
from .dica import parse_announcement_listing as parse_dica_announcement_listing
from .doms import parse_tender_detail as parse_doms_tender_detail
from .doms import parse_tender_listing as parse_doms_tender_listing
from .dof import parse_tender_records as parse_dof_tender_records
from .dwir import parse_tender_detail as parse_dwir_tender_detail
from .dwir import parse_tender_listing as parse_dwir_tender_listing
from .iwt import parse_tender_detail as parse_iwt_tender_detail
from .ird import parse_announcement_detail as parse_ird_announcement_detail
from .ird import parse_announcement_listing as parse_ird_announcement_listing
from .iwt import parse_tender_listing as parse_iwt_tender_listing
from .monpifer import parse_tender_records as parse_monpifer_tender_records
from .moep import parse_tender_detail as parse_moep_tender_detail
from .moep import parse_tender_listing as parse_moep_tender_listing
from .moea import parse_tender_records as parse_moea_tender_records
from .mofa import parse_tender_detail as parse_mofa_tender_detail
from .mofa import parse_tender_listing as parse_mofa_tender_listing
from .mcrd import parse_tender_records as parse_mcrd_tender_records
from .mte import parse_tender_records as parse_mte_tender_records
from .mpt import SitemapEntry, parse_sitemap, parse_tender_detail as parse_mpt_tender_detail
from .ptd import parse_tender_detail as parse_ptd_tender_detail
from .ptd import parse_tender_listing as parse_ptd_tender_listing
from .railways import parse_tender_detail as parse_railways_tender_detail
from .railways import parse_tender_listing
from .ycdc_building import parse_tender_records as parse_ycdc_building_tender_records


class SourceAdapterError(RuntimeError):
    pass


DiscoveryParser = Callable[[bytes], list[SitemapEntry]]
DiscoveryRecordParser = Callable[[bytes, str], list[object]]
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
    parse_discovery_records: DiscoveryRecordParser | None = None


def _empty_discovery(_payload: bytes) -> list[SitemapEntry]:
    return []


def _parse_mpt_detail(payload: bytes, url: str) -> list[object]:
    tender = parse_mpt_tender_detail(payload, url)
    return [tender] if tender is not None else []


def _parse_dast_detail(payload: bytes, url: str) -> list[object]:
    tender = parse_dast_tender_detail(payload, url)
    return [tender] if tender is not None else []


def _parse_ptd_detail(payload: bytes, url: str) -> list[object]:
    tender = parse_ptd_tender_detail(payload, url)
    return [tender] if tender is not None else []


def _parse_iwt_detail(payload: bytes, url: str) -> list[object]:
    tender = parse_iwt_tender_detail(payload, url)
    return [tender] if tender is not None else []


def _parse_moep_detail(payload: bytes, url: str) -> list[object]:
    tender = parse_moep_tender_detail(payload, url)
    return [tender] if tender is not None else []


def _parse_commerce_detail(payload: bytes, url: str) -> list[object]:
    notice = parse_commerce_notification_detail(payload, url)
    return [notice] if notice is not None else []


def _parse_ird_detail(payload: bytes, url: str) -> list[object]:
    notice = parse_ird_announcement_detail(payload, url)
    return [notice] if notice is not None else []


def _parse_dica_detail(payload: bytes, url: str) -> list[object]:
    notice = parse_dica_announcement_detail(payload, url)
    return [notice] if notice is not None else []


def _parse_doms_detail(payload: bytes, url: str) -> list[object]:
    tender = parse_doms_tender_detail(payload, url)
    return [tender] if tender is not None else []


def _parse_dwir_detail(payload: bytes, url: str) -> list[object]:
    tender = parse_dwir_tender_detail(payload, url)
    return [tender] if tender is not None else []


def _parse_mofa_detail(payload: bytes, url: str) -> list[object]:
    tender = parse_mofa_tender_detail(payload, url)
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
    "dast_tender": SourceAdapter(
        name="dast_tender",
        discovery_content_types=("text/html",),
        discovery_parser_version="dast-tender-category-v1",
        detail_parser_version="dast-tender-html-v1",
        normalizer_version="dast-tender-normalize-v1",
        canonicalizer_version="dast-wordpress-post-id-v1",
        parse_discovery=parse_dast_tender_listing,
        parse_detail=_parse_dast_detail,
    ),
    "ptd_tender": SourceAdapter(
        name="ptd_tender",
        discovery_content_types=("text/html",),
        discovery_parser_version="ptd-tender-category-v1",
        detail_parser_version="ptd-tender-html-v1",
        normalizer_version="ptd-tender-normalize-v1",
        canonicalizer_version="ptd-business-event-fingerprint-v1",
        parse_discovery=parse_ptd_tender_listing,
        parse_detail=_parse_ptd_detail,
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
    "commerce_notice": SourceAdapter(
        name="commerce_notice",
        discovery_content_types=("text/html",),
        discovery_parser_version="commerce-notification-block-v1",
        detail_parser_version="commerce-notice-html-v1",
        normalizer_version="commerce-notice-normalize-v1",
        canonicalizer_version="commerce-notice-node-date-v1",
        parse_discovery=parse_commerce_notification_listing,
        parse_detail=_parse_commerce_detail,
    ),
    "ird_notice": SourceAdapter(
        name="ird_notice",
        discovery_content_types=("text/html",),
        discovery_parser_version="ird-announcement-list-v1",
        detail_parser_version="ird-announcement-detail-v1",
        normalizer_version="ird-notice-normalize-v1",
        canonicalizer_version="ird-notice-record-date-v1",
        parse_discovery=parse_ird_announcement_listing,
        parse_detail=_parse_ird_detail,
    ),
    "dica_notice": SourceAdapter(
        name="dica_notice",
        discovery_content_types=("text/html",),
        discovery_parser_version="dica-announcement-category-v1",
        detail_parser_version="dica-announcement-detail-v1",
        normalizer_version="dica-notice-normalize-v1",
        canonicalizer_version="dica-notice-post-date-v1",
        parse_discovery=parse_dica_announcement_listing,
        parse_detail=_parse_dica_detail,
    ),
    "customs_notice": SourceAdapter(
        name="customs_notice",
        discovery_content_types=("text/html",),
        discovery_parser_version="customs-notification-table-v1",
        detail_parser_version="not-applicable",
        normalizer_version="customs-notice-normalize-v1",
        canonicalizer_version="customs-notice-reference-v1",
        parse_discovery=_empty_discovery,
        parse_detail=lambda _payload, _url: [],
        parse_discovery_records=parse_customs_notification_records,
    ),
    "customs_auction": SourceAdapter(
        name="customs_auction",
        discovery_content_types=("text/html",),
        discovery_parser_version="customs-announcements-auction-v1",
        detail_parser_version="not-applicable",
        normalizer_version="customs-auction-normalize-v1",
        canonicalizer_version="customs-auction-fingerprint-v1",
        parse_discovery=_empty_discovery,
        parse_detail=lambda _payload, _url: [],
        parse_discovery_records=parse_customs_auction_records,
    ),
    "monpifer_tender": SourceAdapter(
        name="monpifer_tender",
        discovery_content_types=("text/html",),
        discovery_parser_version="monpifer-tender-table-v1",
        detail_parser_version="not-applicable",
        normalizer_version="monpifer-tender-normalize-v1",
        canonicalizer_version="monpifer-article-alias-v1",
        parse_discovery=_empty_discovery,
        parse_detail=lambda _payload, _url: [],
        parse_discovery_records=parse_monpifer_tender_records,
    ),
    "doms_tender": SourceAdapter(
        name="doms_tender",
        discovery_content_types=("text/html",),
        discovery_parser_version="doms-tender-category-v1",
        detail_parser_version="doms-tender-html-v1",
        normalizer_version="doms-tender-normalize-v1",
        canonicalizer_version="doms-wordpress-post-id-v1",
        parse_discovery=parse_doms_tender_listing,
        parse_detail=_parse_doms_detail,
    ),
    "dof_tender": SourceAdapter(
        name="dof_tender",
        discovery_content_types=("text/html",),
        discovery_parser_version="dof-tender-card-v1",
        detail_parser_version="not-applicable",
        normalizer_version="dof-tender-normalize-v1",
        canonicalizer_version="dof-issuer-alias-v1",
        parse_discovery=_empty_discovery,
        parse_detail=lambda _payload, _url: [],
        parse_discovery_records=parse_dof_tender_records,
    ),
    "moea_tender": SourceAdapter(
        name="moea_tender",
        discovery_content_types=("text/html",),
        discovery_parser_version="moea-tender-archive-card-v1",
        detail_parser_version="not-applicable",
        normalizer_version="moea-tender-normalize-v1",
        canonicalizer_version="moea-archive-event-fingerprint-v1",
        parse_discovery=_empty_discovery,
        parse_detail=lambda _payload, _url: [],
        parse_discovery_records=parse_moea_tender_records,
    ),
    "ycdc_building_tender": SourceAdapter(
        name="ycdc_building_tender",
        discovery_content_types=("text/html",),
        discovery_parser_version="ycdc-building-stable-archive-v1",
        detail_parser_version="not-applicable",
        normalizer_version="ycdc-building-normalize-v1",
        canonicalizer_version="ycdc-building-event-fingerprint-v1",
        parse_discovery=_empty_discovery,
        parse_detail=lambda _payload, _url: [],
        parse_discovery_records=parse_ycdc_building_tender_records,
    ),
    "mcrd_tender": SourceAdapter(
        name="mcrd_tender",
        discovery_content_types=("text/html",),
        discovery_parser_version="mcrd-tender-board-v1",
        detail_parser_version="not-applicable",
        normalizer_version="mcrd-tender-normalize-v1",
        canonicalizer_version="mcrd-board-event-fingerprint-v1",
        parse_discovery=_empty_discovery,
        parse_detail=lambda _payload, _url: [],
        parse_discovery_records=parse_mcrd_tender_records,
    ),
    "mte_tender": SourceAdapter(
        name="mte_tender",
        discovery_content_types=("text/html",),
        discovery_parser_version="mte-announcement-archive-v1",
        detail_parser_version="not-applicable",
        normalizer_version="mte-procurement-normalize-v1",
        canonicalizer_version="mte-joomla-article-id-v1",
        parse_discovery=_empty_discovery,
        parse_detail=lambda _payload, _url: [],
        parse_discovery_records=parse_mte_tender_records,
    ),
    "mofa_tender": SourceAdapter(
        name="mofa_tender",
        discovery_content_types=("text/html",),
        discovery_parser_version="mofa-announcement-category-v1",
        detail_parser_version="mofa-wordpress-html-v1",
        normalizer_version="mofa-tender-normalize-v1",
        canonicalizer_version="mofa-wordpress-post-id-v1",
        parse_discovery=parse_mofa_tender_listing,
        parse_detail=_parse_mofa_detail,
    ),
    "dwir_tender": SourceAdapter(
        name="dwir_tender",
        discovery_content_types=("text/html",),
        discovery_parser_version="dwir-home-latest-news-v1",
        detail_parser_version="dwir-joomla-html-v1",
        normalizer_version="dwir-tender-normalize-v1",
        canonicalizer_version="dwir-joomla-article-id-v1",
        parse_discovery=parse_dwir_tender_listing,
        parse_detail=_parse_dwir_detail,
    ),
}


def adapter_for(source_id: str, source: dict) -> SourceAdapter:
    name = source.get("adapter")
    if not isinstance(name, str) or name not in ADAPTERS:
        raise SourceAdapterError(f"unsupported source adapter: {source_id}")
    return ADAPTERS[name]
