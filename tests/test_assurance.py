from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from signalforge.assurance import (
    MANDATORY_COVERAGE_SOURCES,
    _coverage_from_listing,
    _noise_candidates,
    _nonstandard_candidates,
    _source_candidates,
    assurance_status,
    list_missed_signals,
    list_noise_samples,
    record_manual_promotion,
    record_missed_signal,
    resolve_manual_promotion,
    resolve_missed_signal,
    review_noise_sample,
    run_assurance,
)
from signalforge.briefing import business_briefing
from signalforge.business_digest import business_digest, render_business_digest
from signalforge.config import Registry
from signalforge.db import SCHEMA_VERSION, connect, migrate
from signalforge.telegram_delivery import telegram_deliver

FIXTURES = Path(__file__).parent / "fixtures"
KNOWN_NOISE_SIGNAL_ID = "67f9c7a2-b930-439c-84cc-d05cdecbe695"


class AssuranceTests(unittest.TestCase):
    def _db(self, root: str) -> Path:
        database = Path(root) / "signalforge.db"
        migrate(database)
        return database

    def _insert_known_noise(self, database: Path) -> None:
        with connect(database) as conn, conn:
            conn.execute(
                """
                INSERT INTO canonical_items(
                    canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,
                    deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "mpt:NOISE", "S13", "TENDER", "Historical parser-only noise", "NOISE", "Noise",
                    "2026-09-01", None, None, "https://mpt.com.mm/en/noise/", "h", "e", "{}",
                    "2026-09-01T00:00:00Z", "2026-09-01T00:00:00Z",
                ),
            )
            conn.execute(
                "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                (KNOWN_NOISE_SIGNAL_ID, "S13", "mpt:NOISE", "UPDATED", "2026-09-01T00:00:00Z", "{}"),
            )

    def test_schema_v8_contains_assurance_ledger_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            with connect(database) as conn:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                version = conn.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0]
        self.assertEqual(SCHEMA_VERSION, 8)
        self.assertEqual(version, 8)
        self.assertTrue(
            {
                "assurance_runs", "coverage_audit_results", "noise_review_samples", "missed_signals",
                "manual_promotions", "manual_delivery_receipts", "metric_reviews",
            }
            <= tables
        )

    def test_independent_candidate_extractors_cover_high_value_fixtures(self) -> None:
        cases = [
            ("S20", "moep_tender_list.html", "https://moep.gov.mm/mm/ignite/page/62", 2),
            ("S21", "railways_tender_list.html", "https://www.railways.gov.mm/category/tender/", 2),
            ("S30", "mofa_announcement_list.html", "https://www.mofa.gov.mm/category/announcement/", 2),
            ("S38", "industry-listing.html", "https://www.industrymsme.gov.mm/announcements", 16),
            ("S39", "energy-tenders.html", "https://energy.gov.mm/tenders", 4),
        ]
        for source_id, fixture, base, minimum in cases:
            with self.subTest(source_id=source_id):
                rows = _source_candidates(source_id, (FIXTURES / fixture).read_bytes(), base)
                self.assertGreaterEqual(len(rows), minimum)
                self.assertTrue(all(str(row["url"]).startswith("https://") for row in rows))
        mofa_payload = (FIXTURES / "mofa_announcement_list.html").read_bytes()
        mofa_nonstandard = _nonstandard_candidates("S30", mofa_payload, "https://www.mofa.gov.mm/category/announcement/")
        self.assertEqual(len(mofa_nonstandard), 1)
        self.assertIn("တင်ဒါအောင်မြင်ကြောင်း", mofa_nonstandard[0]["title"])
        industry_payload = (FIXTURES / "industry-listing.html").read_bytes()
        nonstandard = _nonstandard_candidates("S38", industry_payload, "https://www.industrymsme.gov.mm/announcements")
        self.assertEqual(len(nonstandard), 4)

    def test_s38_nonstandard_candidates_enter_noise_review_pool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            run_id = "00000000-0000-4000-8000-000000000099"
            details = {
                "nonstandard_candidates": [
                    {
                        "url": "https://www.industrymsme.gov.mm/announcements/1031",
                        "title": "Machinery import permission application",
                    }
                ]
            }
            with connect(database) as conn, conn:
                conn.execute(
                    "INSERT INTO assurance_runs(assurance_run_id,started_at,status,network_checks,summary_json) VALUES (?,?,?,1,'{}')",
                    (run_id, "2026-09-15T00:00:00Z", "REVIEW"),
                )
                conn.execute(
                    """
                    INSERT INTO coverage_audit_results(
                        coverage_audit_id,assurance_run_id,source_id,audit_method,status,official_candidate_count,
                        canonical_covered_count,missing_count,checked_at,details_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "coverage-1", run_id, "S38", "independent-provider-raw-fetch-links", "PASS", 16,
                        16, 0, "2026-09-15T00:00:00Z", json.dumps(details),
                    ),
                )
                rows = _noise_candidates(conn)
            matching = [row for row in rows if row["candidate_kind"] == "INDEPENDENT_LISTING_NONSTANDARD"]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["source_id"], "S38")
            self.assertIn("1031", str(matching[0]["candidate_ref"]))

    def test_s38_coverage_uses_provider_raw_fetch_and_independent_extractor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            payload = (FIXTURES / "industry-listing.html").read_bytes()
            candidates = _source_candidates("S38", payload, "https://www.industrymsme.gov.mm/announcements")
            with connect(database) as conn, conn:
                for index, item in enumerate(candidates):
                    conn.execute(
                        """
                        INSERT INTO canonical_items(
                            canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,
                            deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            f"industry:{index}", "S38", "TENDER", item["title"], f"IND-{index}", item["title"],
                            "2026-09-15", None, None, item["url"], f"h{index}", f"e{index}", "{}",
                            "2026-09-15T00:00:00Z", "2026-09-15T00:00:00Z",
                        ),
                    )
            policy = Registry.load(Path(__file__).resolve().parents[1]).source("S38")
            capture = SimpleNamespace(
                payload=payload,
                provider_request_id="provider-assurance",
                sha256="abc123",
                final_url="https://www.industrymsme.gov.mm/announcements",
                http_status=200,
            )
            with patch("signalforge.assurance.acquire_provider_diagnostic_bytes", return_value=capture) as provider:
                with connect(database) as conn:
                    result = _coverage_from_listing(
                        conn,
                        database=database,
                        assurance_run_id="00000000-0000-4000-8000-000000000001",
                        source_id="S38",
                        policy=policy,
                        network=True,
                        now=datetime(2026, 9, 15, tzinfo=UTC),
                    )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["official"], len(candidates))
            self.assertEqual(result["covered"], len(candidates))
            self.assertEqual(result["method"], "independent-provider-raw-fetch-links")
            kwargs = provider.call_args.kwargs
            self.assertEqual(kwargs["assurance_run_id"], "00000000-0000-4000-8000-000000000001")
            self.assertEqual(kwargs["target_role"], "LISTING")
            self.assertEqual(kwargs["capability"], "C0_FETCH")

    def test_miss_ledger_deduplicates_and_supports_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            first = record_missed_signal(
                source_id="S39", title="Missing tender 999", reason="coverage gap", url="https://energy.gov.mm/tenders/999",
                database=database, now=datetime(2026, 9, 15, tzinfo=UTC),
            )
            second = record_missed_signal(
                source_id="S39", title="Missing tender 999", reason="coverage gap", url="https://energy.gov.mm/tenders/999",
                database=database, now=datetime(2026, 9, 15, 1, tzinfo=UTC),
            )
            self.assertFalse(first["deduplicated"])
            self.assertTrue(second["deduplicated"])
            self.assertEqual(list_missed_signals(database=database)["count"], 1)
            resolved = resolve_missed_signal(str(first["miss_id"]), note="canonicalized", database=database)
            self.assertEqual(resolved["miss"]["status"], "RESOLVED")

    def test_noise_review_false_negative_opens_miss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            self._insert_known_noise(database)
            result = run_assurance(
                database=database,
                network=False,
                noise_sample_size=1,
                now=datetime(2026, 9, 15, 2, 0, tzinfo=UTC),
            )
            self.assertEqual(len(result["coverage"]), len(MANDATORY_COVERAGE_SOURCES))
            samples = list_noise_samples(database=database, status="PENDING")["samples"]
            self.assertEqual(len(samples), 1)
            reviewed = review_noise_sample(
                str(samples[0]["noise_sample_id"]),
                outcome="FALSE_NEGATIVE",
                note="Actually contained a live tender",
                database=database,
                now=datetime(2026, 9, 15, 3, 0, tzinfo=UTC),
            )
            self.assertIsNotNone(reviewed["miss"])
            misses = list_missed_signals(database=database)["misses"]
            self.assertEqual(len(misses), 1)
            self.assertEqual(misses[0]["detected_by"], "NOISE_REVIEW")

    def test_manual_promotion_is_visible_and_uses_separate_delivery_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            promoted = record_manual_promotion(
                source_id="SXX",
                title="重要但非标准采购线索",
                summary="客户正在准备未正式发布的传输设备采购。",
                reason="高商业价值但缺少标准 tender identity",
                priority_band="HIGH",
                url="https://example.com/source",
                deadline="2026-09-20",
                database=database,
            )
            briefing = business_briefing(database=database)
            self.assertEqual(briefing["manual_promotions"]["count"], 1)
            digest = business_digest(database=database, audit_network=False)
            text = render_business_digest(digest)
            self.assertIn("🧑 人工升级", text)
            self.assertIn("重要但非标准采购线索", text)
            dry = telegram_deliver(database=database, dry_run=True)
            self.assertEqual(dry["manual_pending_count"], 1)
            self.assertIn("不是 canonical Signal", dry["pending"][0]["message"])
            with patch("signalforge.telegram_delivery._send_message", return_value="9001"):
                sent = telegram_deliver(database=database, bot_token="secret", chat_id="42")
            self.assertEqual(sent["manual_sent_count"], 1)
            with connect(database) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM manual_delivery_receipts").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM delivery_receipts").fetchone()[0], 0)
            resolved = resolve_manual_promotion(str(promoted["promotion"]["promotion_id"]), note="closed", database=database)
            self.assertEqual(resolved["promotion"]["status"], "RESOLVED")

    def test_inconclusive_noise_review_does_not_dilute_false_negative_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            self._insert_known_noise(database)
            sampled = run_assurance(
                database=database,
                network=False,
                noise_sample_size=1,
                now=datetime(2026, 9, 15, 2, 0, tzinfo=UTC),
            )
            sample_id = str(sampled["noise_samples_created"][0]["noise_sample_id"])
            review_noise_sample(
                sample_id,
                outcome="INCONCLUSIVE",
                note="historical raw evidence was not retained",
                database=database,
                now=datetime(2026, 9, 15, 3, 0, tzinfo=UTC),
            )
            reviewed = run_assurance(
                database=database,
                network=False,
                noise_sample_size=0,
                now=datetime(2026, 9, 15, 4, 0, tzinfo=UTC),
            )
            metrics = reviewed["metric_review"]["metrics"]
            reasons = reviewed["metric_review"]["conclusions"]["review_reasons"]
            self.assertEqual(metrics["noise_samples_reviewed_window"], 1)
            self.assertEqual(metrics["noise_samples_conclusive_window"], 0)
            self.assertEqual(metrics["noise_samples_inconclusive_window"], 1)
            self.assertIsNone(metrics["noise_false_negative_rate"])
            self.assertIn("NO_CONCLUSIVE_NOISE_SAMPLE_IN_WINDOW", reasons)

    def test_metric_validity_is_review_when_coverage_unproven_and_fail_with_red_miss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            review = run_assurance(database=database, network=False, noise_sample_size=0)
            self.assertEqual(review["status"], "REVIEW")
            self.assertIn("MANDATORY_COVERAGE_NOT_FULLY_PROVEN", review["metric_review"]["conclusions"]["review_reasons"])
            self.assertIn("raw_signals", review["metric_review"]["conclusions"]["diagnostic_only_not_business_value_proof"])
            record_missed_signal(source_id="S13", title="Known miss", reason="manual validation", database=database)
            failed = run_assurance(database=database, network=False, noise_sample_size=0)
            self.assertEqual(failed["status"], "FAIL")
            self.assertIn("OPEN_RED_MISS_EXISTS", failed["metric_review"]["conclusions"]["fail_reasons"])
            latest = assurance_status(database=database)
            self.assertEqual(latest["counts"]["open_red_misses"], 1)


if __name__ == "__main__":
    unittest.main()
