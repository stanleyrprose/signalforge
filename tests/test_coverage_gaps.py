from __future__ import annotations

import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from signalforge.business_digest import render_business_digest
from signalforge.coverage_gaps import reviewed_coverage_gaps, verified_external_opportunities


class CoverageGapTests(unittest.TestCase):
    def test_reviewed_records_do_not_exist_before_their_review_date(self) -> None:
        assert reviewed_coverage_gaps(now=datetime(2026, 9, 14, tzinfo=UTC)) == []
        assert verified_external_opportunities(now=datetime(2026, 9, 14, tzinfo=UTC)) == []

    def test_reviewed_gaps_and_verified_external_are_separate_business_states(self) -> None:
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

    def test_reviewed_records_expire_by_deadline_date(self) -> None:
        after_first = reviewed_coverage_gaps(now=datetime(2026, 9, 17, tzinfo=UTC))
        assert [item["deadline"] for item in after_first] == ["2026-09-23"]
        after_moc = reviewed_coverage_gaps(now=datetime(2026, 9, 24, tzinfo=UTC))
        assert [item["deadline"] for item in after_moc] == ["2026-09-25", "2026-10-09"]
        assert all(item["evidence_basis"] == "REVIEWED_OFFICIAL_TENDER_BOARD_LISTING" for item in after_moc)
        assert [item["deadline"] for item in verified_external_opportunities(now=datetime(2026, 9, 24, tzinfo=UTC))] == ["2026-09-29"]
        assert verified_external_opportunities(now=datetime(2026, 9, 30, tzinfo=UTC)) == []

    def test_reviewed_records_expire_at_exact_local_deadline_time(self) -> None:
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
        assert [item["gap_id"] for item in after_highway_close] == [
            "S23:board:yangon-2026-09-25",
            "S23:board:mandalay-bridge5-2026-10-09",
        ]

        before_mpt_close = verified_external_opportunities(now=datetime(2026, 9, 29, 7, 29, tzinfo=UTC))
        assert len(before_mpt_close) == 1
        after_mpt_close = verified_external_opportunities(now=datetime(2026, 9, 29, 7, 30, tzinfo=UTC))
        assert after_mpt_close == []

    def test_s23_highway_gap_becomes_verified_external_only_after_resolution_review(self) -> None:
        before = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
        assert [item["gap_id"] for item in reviewed_coverage_gaps(now=before)] == [
            "S23:18be5b60-accb-11f1-b41f-3517e3a380a0"
        ]
        assert [item["source_id"] for item in verified_external_opportunities(now=before)] == ["S13"]

        after = datetime(2026, 9, 18, 0, 0, tzinfo=UTC)
        assert reviewed_coverage_gaps(now=after) == []
        verified = verified_external_opportunities(now=after)
        assert [item["source_id"] for item in verified] == ["S23", "S13"]
        highway = verified[0]
        assert highway["target_source_id"] == "S23"
        assert highway["coverage_origin"] == "S23_REVIEW"
        assert highway["deadline"] == "2026-09-23"
        assert highway["deadline_time"] == "16:00"
        assert highway["priority_band"] == "MEDIUM"
        assert highway["mission_sector"] == "CONSTRUCTION"
        assert highway["canonical_truth"] is False
        assert highway["issuer_document_verified"] is True
        assert highway["issuer_identity_verified"] is True
        assert highway["scope_verified"] is True
        assert highway["deadline_verified"] is True
        assert "9/23 16:00" in highway["next_action_summary"]

    def test_s23_board_only_current_gaps_are_tracked_but_not_verified(self) -> None:
        now = datetime(2026, 9, 20, 13, 30, tzinfo=UTC)
        gaps = reviewed_coverage_gaps(now=now)
        assert [item["gap_id"] for item in gaps] == [
            "S23:board:yangon-2026-09-25",
            "S23:board:mandalay-bridge5-2026-10-09",
        ]
        assert all(item["source_id"] == "S23" for item in gaps)
        assert all(item["evidence_basis"] == "REVIEWED_OFFICIAL_TENDER_BOARD_LISTING" for item in gaps)
        assert all(item["canonical_signal_status"] == "OUTSIDE_CANONICAL_SIGNAL_PIPELINE" for item in gaps)

        verified = verified_external_opportunities(now=now)
        assert [item["source_id"] for item in verified] == ["S23", "S13"]
        assert not {item["gap_id"] for item in gaps} & {item["gap_id"] for item in verified}

    def test_s23_board_only_gap_cannot_be_promoted_to_verified_external(self) -> None:
        board_only = {
            "gap_id": "S23:board:test",
            "source_id": "S23",
            "evidence_basis": "REVIEWED_OFFICIAL_TENDER_BOARD_LISTING",
            "resolution_mode": "VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY",
            "resolution_reviewed_at": "2026-09-20",
            "issuer_document_verified": True,
            "issuer_identity_verified": True,
            "scope_verified": True,
            "deadline_verified": True,
            "canonical_truth": False,
            "document_sha256": "0" * 64,
            "coverage_origin": "S23_REVIEW",
            "target_source_id": "S23",
            "verification_basis": "SHOULD_NOT_BE_ACCEPTED",
        }
        with patch("signalforge.coverage_gaps._active_reviewed_records", return_value=[board_only]):
            with self.assertRaisesRegex(ValueError, "tender-board-only"):
                verified_external_opportunities(now=datetime(2026, 9, 20, 13, 30, tzinfo=UTC))

    def test_business_digest_renders_verified_external_separately_from_unresolved_gaps(self) -> None:
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

    def test_business_digest_counts_s23_verified_external_and_links_official_pdf_after_resolution(self) -> None:
        now = datetime(2026, 9, 18, tzinfo=UTC)
        verified = verified_external_opportunities(now=now)
        digest = {
            "digest_date": "2026-09-18",
            "sources": {"monitored": 32, "green": 31, "non_green": 1, "changed_24h": 0},
            "activity_24h": {"scheduler_runs": 0, "records_changed": 0, "evidence_fetched": 0, "items_parsed": 0, "signals": 0, "new_signals": 0, "updated_signals": 0},
            "pipeline_totals": {"telegram_alerts_24h": 0, "telegram_alerts": 0},
            "source_yield": {"yield_states": {}, "active_sources": 32},
            "business": {
                "current_opportunities": 10,
                "canonical_current_opportunities": 8,
                "verified_external_opportunity_count": 2,
                "verified_external_opportunities": verified,
                "tracked_opportunities": 18,
                "priority_counts": {"HIGH": 2, "MEDIUM": 7, "REVIEW": 1},
                "qualification_counts": {},
                "attention": [],
                "watchlist_count": 0,
                "coverage_gap_count": 0,
                "coverage_gaps": [],
            },
            "auditor": {},
        }
        text = render_business_digest(digest)
        assert "✅ 外部官方文件核验：2 条" in text
        assert "Yangon–Mandalay Expressway" in text
        assert "[S23 ← S23_REVIEW]" in text
        assert "https://construction.gov.mm/letter-download/18be5b60-accb-11f1-b41f-3517e3a380a0" in text
        assert "官方PDF" in text
        assert "⚠️ 人工核验机会（尚未形成可计入的官方覆盖）" not in text
        assert "业务概览</b>：目标内 <b>10</b> 个机会（canonical 8 + 外部官方核验 2）" in text


if __name__ == "__main__":
    unittest.main()
