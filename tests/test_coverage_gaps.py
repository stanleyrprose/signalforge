from __future__ import annotations

from datetime import UTC, datetime

from signalforge.business_digest import render_business_digest
from signalforge.coverage_gaps import reviewed_coverage_gaps


def test_reviewed_moc_coverage_gaps_are_read_only_and_bounded() -> None:
    gaps = reviewed_coverage_gaps(now=datetime(2026, 9, 14, tzinfo=UTC))
    assert [item["deadline"] for item in gaps] == ["2026-09-16", "2026-09-23"]
    assert all(item["source_id"] == "S23" for item in gaps)
    assert all(item["reviewed_read_only"] is True for item in gaps)
    assert all(item["canonical_signal_status"] == "OUTSIDE_CANONICAL_SIGNAL_PIPELINE" for item in gaps)


def test_reviewed_moc_coverage_gaps_expire_by_deadline_date() -> None:
    after_first = reviewed_coverage_gaps(now=datetime(2026, 9, 17, tzinfo=UTC))
    assert [item["deadline"] for item in after_first] == ["2026-09-23"]
    after_all = reviewed_coverage_gaps(now=datetime(2026, 9, 24, tzinfo=UTC))
    assert after_all == []


def test_business_digest_renders_coverage_gap_separately_from_opportunities() -> None:
    gaps = reviewed_coverage_gaps(now=datetime(2026, 9, 14, tzinfo=UTC))
    digest = {
        "digest_date": "2026-09-14",
        "sources": {"monitored": 31, "green": 29, "non_green": 2, "changed_24h": 0},
        "activity_24h": {"scheduler_runs": 0, "records_changed": 0, "evidence_fetched": 0, "items_parsed": 0, "signals": 0, "new_signals": 0, "updated_signals": 0},
        "pipeline_totals": {"telegram_alerts_24h": 0, "telegram_alerts": 0},
        "source_yield": {"yield_states": {}, "active_sources": 31},
        "business": {
            "current_opportunities": 21,
            "priority_counts": {},
            "qualification_counts": {},
            "attention": [],
            "watchlist_count": 0,
            "coverage_gap_count": 2,
            "coverage_gaps": gaps,
        },
        "auditor": {},
    }
    text = render_business_digest(digest)
    assert "⚠️ 人工核验机会（尚未进入正式 Signal）" in text
    assert "2026-09-16" in text
    assert "2026-09-23" in text
    assert "业务概览</b>：当前 <b>21</b> 个机会" in text
    assert "暂不计入正式机会数" in text
