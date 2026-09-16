from __future__ import annotations

from signalforge.mission_focus import MISSION_POLICY_VERSION, classify_mission_fit


def _item(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "source_id": "SXX",
        "item_kind": "TENDER",
        "issuer": "Myanmar Government Department",
        "title": "Tender",
        "scope_summary": "",
        "primary_relevance": "OTHER",
        "relevance_categories": ["OTHER"],
    }
    base.update(kwargs)
    return base


def test_mission_policy_targets_government_soe_engineering_construction_telecom_energy() -> None:
    assert MISSION_POLICY_VERSION == 1
    cases = [
        (_item(source_id="S20", issuer="MOEP", scope_summary="generic official tender"), True, "ENERGY"),
        (_item(primary_relevance="ICT", relevance_categories=["ICT"], scope_summary="Data Server with Windows Server and SQL Server"), True, "TELECOM_ICT_INFRA"),
        (_item(primary_relevance="INDUSTRIAL", relevance_categories=["INDUSTRIAL"], scope_summary="Electrical spare parts and Mechanical spare parts"), True, "ENGINEERING"),
        (_item(primary_relevance="OTHER", relevance_categories=["OTHER"], scope_summary="ရေယာဉ် ၁ စီး purchase"), True, "ENGINEERING"),
        (_item(primary_relevance="CONSTRUCTION", relevance_categories=["CONSTRUCTION"], scope_summary="Bridge construction works"), True, "CONSTRUCTION"),
    ]
    for item, expected, sector in cases:
        result = classify_mission_fit(item)
        assert result["mission_fit"] is expected
        assert result["mission_sector"] == sector


def test_off_mission_tenders_stay_stored_but_are_excluded_from_primary_output() -> None:
    cases = [
        _item(item_kind="AUCTION_NOTICE", title="Customs auction"),
        _item(primary_relevance="MEDICAL", relevance_categories=["MEDICAL", "ICT"], scope_summary="X-Ray Mammography Scanner"),
        _item(primary_relevance="INDUSTRIAL", relevance_categories=["INDUSTRIAL"], scope_summary="Chemical Reagent 22 items and Sample Gas 5 items"),
        _item(primary_relevance="INDUSTRIAL", relevance_categories=["INDUSTRIAL"], scope_summary="1/7 PC colored yarn 49,460 lb"),
        _item(primary_relevance="INDUSTRIAL", relevance_categories=["INDUSTRIAL"], scope_summary="Refractory and Castable Mortar raw material"),
        _item(issuer="ATOM Myanmar", primary_relevance="TELECOM", relevance_categories=["TELECOM"], scope_summary="5G telecom tender"),
    ]
    for item in cases:
        result = classify_mission_fit(item)
        assert result["mission_fit"] is False
        assert result["mission_sector"] == "OUT_OF_SCOPE"
