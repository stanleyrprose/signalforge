from __future__ import annotations

from signalforge.yangon_ycdc_mission import YCDC_TOKEN, parse_tender_detail, parse_tender_listing


def _detail(*, post_id: str = "3755", title: str, scope: str, published: str = "2026-09-15T17:47:34+06:30") -> bytes:
    return f"""
    <html><head><meta property="article:published_time" content="{published}"></head>
    <body class="postid-{post_id}">
      <h1 class="entry-title">{title}</h1>
      <div class="entry-content">{scope}</div>
    </body></html>
    """.encode()


def test_current_ycdc_construction_tender_uses_final_submission_not_sale_date() -> None:
    scope = (
        f"{YCDC_TOKEN} 2026-2027 Open Tender. "
        "Construction materials: HDPE pipe and fittings 1 Lot; cement; HRB-400 rebar; Chipping; Crushed Dust. "
        "Tender forms on sale 17-9-2026. Final submission 29-9-2026 (12:00)."
    )
    tender = parse_tender_detail(
        _detail(title=f"{YCDC_TOKEN} Open Tender", scope=scope),
        "https://www.yangon.gov.mm/ycdc-current/",
    )
    assert tender is not None
    assert tender.canonical_key == "yangon-ycdc-mission:3755"
    assert tender.publication_date == "2026-09-15"
    assert tender.deadline == "2026-09-29"
    assert tender.deadline_time == "12:00"
    assert tender.mission_sector == "CONSTRUCTION"
    assert "HDPE pipe & fittings 1 Lot" in tender.focus_scope_summary
    assert "sand / aggregate / chipping / crushed dust" in tender.focus_scope_summary
    payload = tender.payload()
    assert payload["business_stage"] == "OPPORTUNITY"
    assert payload["deadline_kind"] == "BID_SUBMISSION_DEADLINE"
    assert payload["focus_scope_summary"] == tender.focus_scope_summary
    assert payload["relevance_categories"] == ["CONSTRUCTION"]


def test_ycdc_non_mission_procurement_fails_closed() -> None:
    tender = parse_tender_detail(
        _detail(
            title=f"{YCDC_TOKEN} Open Tender",
            scope=f"{YCDC_TOKEN}: diesel fuel, office chairs and filing cabinets. Final submission 29-9-2026 (12:00).",
        ),
        "https://www.yangon.gov.mm/ycdc-office/",
    )
    assert tender is None


def test_non_ycdc_mission_tender_fails_closed() -> None:
    tender = parse_tender_detail(
        _detail(
            title="Ministry of Construction Open Tender",
            scope="Bridge construction and road works. Final submission 29-9-2026 (12:00).",
        ),
        "https://www.yangon.gov.mm/moc-tender/",
    )
    assert tender is None


def test_generic_yangon_tender_listing_is_reused_for_discovery() -> None:
    html = b'''<html><body><article><h2 class="entry-title"><a href="https://www.yangon.gov.mm/ycdc-current/">Open Tender</a></h2><span class="updated">2026-09-15T17:47:34+06:30</span></article></body></html>'''
    entries = parse_tender_listing(html)
    assert len(entries) == 1
    assert entries[0].url == "https://www.yangon.gov.mm/ycdc-current/"
