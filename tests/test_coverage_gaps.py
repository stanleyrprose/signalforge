from __future__ import annotations

from datetime import UTC, datetime

from signalforge.business_digest import render_business_digest
from signalforge.coverage_gaps import reviewed_coverage_gaps, verified_external_opportunities


def test_reviewed_records_do_not_exist_before_their_review_date() -> None:
    assert reviewed_coverage_gaps(now=datetime(2026, 9, 14, tzinfo=UTC)) == []
    assert verified_external_opportunities(now=datetime(2026, 9, 14, tzinfo=UTC)) == []


def test_reviewed_gaps_and_verified_external_are_separate_business_states() -> None:
    now = datetime(2026, 9, 16, tzinfo=UTC)
    gaps = reviewed_coverage_gaps(now=now)
    verified = verified_external_opportunities(now=now)
    assert [item["deadline"] for item in gaps] == ["2026-09-16", "2026-09-23"]
    assert [item["source_id"] for item in gaps] == ["S23", "S23"]
    assert len(verified) == 1
    assert verified[0]["source_id"] == "S13"
    assert verified[0]["deadline"] == "2026-09-29"
    assert verified[0]["coverage_origin"] == "S01"
    assert verified[0]["target_source_id"] == "S13"
    assert verified[0]["mission_sector"] == "CONSTRUCTION"
    assert verified[0]["verified_external"] is True
    assert verified[0]["canonical_truth"] is False
    assert verified[0]["issuer_document_verified"] is True
    assert verified[0]["issuer_identity_verified"] is True
    assert verified[0]["scope_verified"] is True
    assert verified[0]["deadline_verified"] is True
    assert all(item["reviewed_read_only"] is True for item in gaps + verified)
    assert all(item["canonical_signal_status"] == "OUTSIDE_CANONICAL_SIGNAL_PIPELINE" for item in gaps + verified)


def test_reviewed_records_expire_by_deadline_date() -> None:
    after_first = reviewed_coverage_gaps(now=datetime(2026, 9, 17, tzinfo=UTC))
    assert [item["deadline"] for item in after_first] == ["2026-09-23"]
    after_moc = reviewed_coverage_gaps(now=datetime(2026, 9, 24, tzinfo=UTC))
    assert after_moc == []
    assert [item["deadline"] for item in verified_external_opportunities(now=datetime(2026, 9, 24, tzinfo=UTC))] == ["2026-09-29"]
    assert verified_external_opportunities(now=datetime(2026, 9, 30, tzinfo=UTC)) == []



def test_reviewed_records_expire_at_exact_local_deadline_time() -> None:
    # Myanmar is UTC+06:30. At 09:29 UTC it is 15:59 local, so the 16:00 bridge tender is still active.
    before_bridge_close = reviewed_coverage_gaps(now=datetime(2026, 9, 16, 9, 29, tzinfo=UTC))
    assert [item["gap_id"] for item in before_bridge_close] == [
        "S23:0f39a580-a813-11f1-97b9-bbf17f490ccf",
        "S23:18be5b60-accb-11f1-b41f-3517e3a380a0",
    ]
    after_bridge_close = reviewed_coverage_gaps(now=datetime(2026, 9, 16, 9, 30, tzinfo=UTC))
    assert [item["gap_id"] for item in after_bridge_close] == [
        "S23:18be5b60-accb-11f1-b41f-3517e3a380a0"
    ]
    after_highway_close = reviewed_coverage_gaps(now=datetime(2026, 9, 23, 9, 30, tzinfo=UTC))
    assert after_highway_close == []

    before_mpt_close = verified_external_opportunities(now=datetime(2026, 9, 29, 7, 29, tzinfo=UTC))
    assert len(before_mpt_close) == 1
    after_mpt_close = verified_external_opportunities(now=datetime(2026, 9, 29, 7, 30, tzinfo=UTC))
    assert after_mpt_close == []

def test_business_digest_renders_verified_external_separately_from_unresolved_gaps() -> None:
    now = datetime(2026, 9, 16, tzinfo=UTC)
    gaps = reviewed_coverage_gaps(now=now)
    verified = verified_external_opportunities(now=now)
    digest = {
        "digest_date": "2026-09-16",
        "sources": {"monitored": 31, "green": 29, "non_green": 2, "changed_24h": 0},
        "activity_24h": {"scheduler_runs": 0, "records_changed": 0, "evidence_fetched": 0, "items_parsed": 0, "signals": 0, "new_signals": 0, "updated_signals": 0},
        "pipeline_totals": {"telegram_alerts_24h": 0, "telegram_alerts": 0},
        "source_yield": {"yield_states": {}, "active_sources": 31},
        "business": {
            "current_opportunities": 9,
            "canonical_current_opportunities": 8,
            "verified_external_opportunity_count": 1,
            "verified_external_opportunities": verified,
            "tracked_opportunities": 17,
            "priority_counts": {"HIGH": 2, "MEDIUM": 3, "REVIEW": 4},
            "qualification_counts": {},
            "attention": [],
            "watchlist_count": 0,
            "coverage_gap_count": len(gaps),
            "coverage_gaps": gaps,
        },
        "auditor": {},
    }
    text = render_business_digest(digest)
    assert "✅ 外部官方文件核验：1 条" in text
    assert "Pobbathiri Exchange Office" in text
    assert "[S13 ← S01]" in text
    assert "已计入目标机会" in text
    assert "⚠️ 人工核验机会（尚未形成可计入的官方覆盖）" in text
    assert "Ayeyarwady 桥梁工程" in text
    assert "Yangon–Mandalay Expressway" in text
    assert "仍属 coverage gap，不计入目标机会数" in text
    assert "业务概览</b>：目标内 <b>9</b> 个机会（canonical 8 + 外部官方核验 1）" in text
