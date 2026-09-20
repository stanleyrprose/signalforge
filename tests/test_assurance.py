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
    _coverage_from_existing_audit,
    _coverage_from_listing,
    _metric_review,
    _noise_candidates,
    _zero_item_replayability,
    _nonstandard_candidates,
    _source_candidates,
    assurance_status,
    coverage_has_reviewed_external_recovery,
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

    def test_zero_item_replayability_separates_legacy_from_retention_era_debt(self) -> None:
        class FakeConn:
            def execute(self, _sql, _params):  # type: ignore[no-untyped-def]
                rows = [
                    {
                        "source_id": "S22",
                        "finished_at": "2026-09-16T01:16:07Z",
                        "artifact_sha256": "legacy",
                        "artifact_media_type": "text/html",
                    },
                    {
                        "source_id": "S22",
                        "finished_at": "2026-09-16T01:17:50Z",
                        "artifact_sha256": "retained",
                        "artifact_media_type": "text/html",
                    },
                    {
                        "source_id": "S40",
                        "finished_at": "2026-09-16T01:18:00Z",
                        "artifact_sha256": "missing-current",
                        "artifact_media_type": "text/html",
                    },
                ]
                return SimpleNamespace(fetchall=lambda: rows)

        def retained(_source_id: str, digest: str, _media_type: str):  # type: ignore[no-untyped-def]
            return Path("/tmp/retained.html") if digest == "retained" else None

        with patch("signalforge.assurance._retained_evidence_path", side_effect=retained):
            result = _zero_item_replayability(FakeConn(), cutoff="2026-09-01T00:00:00Z")
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["replayable"], 1)
        self.assertEqual(result["legacy_unreplayable"], 1)
        self.assertEqual(result["retention_era_unreplayable"], 1)
        self.assertEqual(result["unreplayable"], 2)

    def test_legacy_unreplayable_evidence_does_not_claim_current_retention_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            with patch(
                "signalforge.assurance._zero_item_replayability",
                return_value={
                    "total": 10,
                    "replayable": 2,
                    "unreplayable": 8,
                    "legacy_unreplayable": 8,
                    "retention_era_unreplayable": 0,
                },
            ):
                result = run_assurance(
                    database=database,
                    network=False,
                    noise_sample_size=0,
                    now=datetime(2026, 9, 19, 8, 0, tzinfo=UTC),
                )
            metrics = result["metric_review"]["metrics"]
            reasons = result["metric_review"]["conclusions"]["review_reasons"]
            self.assertEqual(metrics["filtered_zero_item_legacy_unreplayable_window"], 8)
            self.assertEqual(metrics["filtered_zero_item_retention_era_unreplayable_window"], 0)
            self.assertNotIn("FILTERED_EVIDENCE_NOT_REPLAYABLE_AFTER_RETENTION", reasons)

    def test_retention_era_unreplayable_evidence_remains_a_review_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            with patch(
                "signalforge.assurance._zero_item_replayability",
                return_value={
                    "total": 3,
                    "replayable": 2,
                    "unreplayable": 1,
                    "legacy_unreplayable": 0,
                    "retention_era_unreplayable": 1,
                },
            ):
                result = run_assurance(
                    database=database,
                    network=False,
                    noise_sample_size=0,
                    now=datetime(2026, 9, 19, 8, 0, tzinfo=UTC),
                )
            reasons = result["metric_review"]["conclusions"]["review_reasons"]
            self.assertIn("FILTERED_EVIDENCE_NOT_REPLAYABLE_AFTER_RETENTION", reasons)

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

    def test_existing_audit_preserves_partial_and_unproven_coverage_semantics(self) -> None:
        partial = _coverage_from_existing_audit(
            {
                "checks": {
                    "strategic_coverage": {
                        "S13": {
                            "status": "PARTIAL",
                            "tender_like_pages": 0,
                            "missing": 0,
                            "verified_external_recovery_count": 1,
                            "risk_kind": "ISSUER_DISCOVERY_PARTIAL",
                        }
                    }
                },
                "findings": [],
            },
            "S13",
        )
        self.assertEqual(partial["status"], "PARTIAL")
        self.assertEqual(partial["official"], 0)
        self.assertEqual(partial["covered"], 0)

        unproven = _coverage_from_existing_audit(
            {
                "checks": {
                    "strategic_coverage": {
                        "S13": {"status": "UNPROVEN", "tender_like_pages": 0, "missing": 0}
                    }
                },
                "findings": [],
            },
            "S13",
        )
        self.assertEqual(unproven["status"], "UNPROVEN")

    def test_assurance_status_separates_coverage_risk_from_confirmed_miss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            run_id = "00000000-0000-4000-8000-000000000211"
            with connect(database) as conn, conn:
                conn.execute(
                    "INSERT INTO assurance_runs(assurance_run_id,started_at,status,network_checks,summary_json) VALUES (?,?,?,1,'{}')",
                    (run_id, "2026-09-16T10:00:00Z", "REVIEW"),
                )
                conn.execute(
                    """
                    INSERT INTO coverage_audit_results(
                        coverage_audit_id,assurance_run_id,source_id,audit_method,status,official_candidate_count,
                        canonical_covered_count,missing_count,checked_at,details_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "coverage-risk-s21",
                        run_id,
                        "S21",
                        "independent-listing-links",
                        "CHECK_FAILED",
                        0,
                        0,
                        0,
                        "2026-09-16T10:00:00Z",
                        json.dumps({"error": "FetchError: issuer origin timed out"}),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO canonical_items(
                        canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,
                        deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "railways:test-latest", "S21", "TENDER", "Railway engineering tender", "R-1",
                        "Railway engineering tender", "2026-09-01", "2026-09-14", None,
                        "https://www.railways.gov.mm/test-latest", "h", "e", "{}",
                        "2026-09-01T00:00:00Z", "2026-09-01T00:00:00Z",
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO source_state(
                        source_id,baseline_complete,last_success_at,next_due_at,last_error,consecutive_failures,updated_at
                    ) VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        "S21",
                        1,
                        "2026-09-13T13:00:46Z",
                        "2026-09-16T10:30:00Z",
                        "FetchError: issuer origin timed out",
                        509,
                        "2026-09-16T10:00:00Z",
                    ),
                )

            latest = assurance_status(database=database)
            self.assertEqual(latest["counts"]["open_misses"], 0)
            self.assertEqual(latest["coverage_risk_count"], 1)
            risk = latest["coverage_risks"][0]
            self.assertEqual(risk["source_id"], "S21")
            self.assertEqual(risk["source_name"], "Myanma Railways Tenders")
            self.assertEqual(risk["coverage_status"], "CHECK_FAILED")
            self.assertEqual(risk["last_success_at"], "2026-09-13T13:00:46Z")
            self.assertEqual(risk["retained_tender_count"], 1)
            self.assertEqual(risk["retained_open_tender_count"], 0)
            self.assertEqual(risk["latest_retained_tender_publication_date"], "2026-09-01")
            self.assertEqual(risk["latest_retained_tender_deadline"], "2026-09-14")
            self.assertEqual(risk["retained_tender_context_semantics"], "RETAINED_STATE_ONLY_NOT_CURRENT_COVERAGE_PROOF")
            self.assertFalse(risk["known_miss"])
            self.assertEqual(risk["semantics"], "COVERAGE_RISK_NOT_CONFIRMED_MISS")

            with patch("signalforge.briefing.current_opportunities", return_value={
                "qualification_policy_version": 1,
                "as_of": "2026-09-16T10:00:00Z",
                "count": 0,
                "counts": {"OPEN": 0, "UNKNOWN": 0, "EXPIRED": 0},
                "qualification_counts": {},
                "opportunities": [],
            }):
                briefing = business_briefing(database=database)
            self.assertEqual(briefing["assurance"]["open_misses"], 0)
            self.assertEqual(briefing["assurance"]["coverage_risk_count"], 1)
            self.assertEqual(briefing["assurance"]["coverage_risks"][0]["source_id"], "S21")

    def test_assurance_status_preserves_mpt_issuer_discovery_partial_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            run_id = "00000000-0000-4000-8000-000000000213"
            details = {
                "reason": "VERIFIED_EXTERNAL_OPPORTUNITY_NOT_DISCOVERED_BY_ISSUER_SITEMAP",
                "risk_kind": "ISSUER_DISCOVERY_PARTIAL",
                "verified_external_recovery_count": 1,
                "issuer_page_coverage_debt_retained": True,
            }
            with connect(database) as conn, conn:
                conn.execute(
                    "INSERT INTO assurance_runs(assurance_run_id,started_at,status,network_checks,summary_json) VALUES (?,?,?,1,'{}')",
                    (run_id, "2026-09-19T06:00:00Z", "REVIEW"),
                )
                conn.execute(
                    """
                    INSERT INTO coverage_audit_results(
                        coverage_audit_id,assurance_run_id,source_id,audit_method,status,official_candidate_count,
                        canonical_covered_count,missing_count,checked_at,details_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "coverage-risk-s13",
                        run_id,
                        "S13",
                        "existing-independent-auditor",
                        "PARTIAL",
                        0,
                        0,
                        0,
                        "2026-09-19T06:00:00Z",
                        json.dumps(details),
                    ),
                )
            latest = assurance_status(database=database)
            self.assertEqual(latest["coverage_risk_count"], 1)
            risk = latest["coverage_risks"][0]
            self.assertEqual(risk["source_id"], "S13")
            self.assertEqual(risk["coverage_status"], "PARTIAL")
            self.assertEqual(risk["risk_kind"], "ISSUER_DISCOVERY_PARTIAL")
            self.assertEqual(risk["verified_external_recovery_count"], 1)
            self.assertTrue(risk["issuer_page_coverage_debt_retained"])

    def test_assurance_status_surfaces_s20_business_detail_risk_even_when_event_is_covered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            run_id = "00000000-0000-4000-8000-000000000220"
            payload = {
                "issuer": "DPTSC",
                "publication_date": "2026-09-11",
                "detail_completeness": "HTML_PARTIAL_ATTACHMENT_METADATA",
                "attachment_name": "ACCC_Conductor_Form.pdf",
                "attachment_url": "https://moep.gov.mm/mm/userfile/ACCC_Conductor_Form.pdf",
            }
            with connect(database) as conn, conn:
                conn.execute(
                    "INSERT INTO assurance_runs(assurance_run_id,started_at,status,network_checks,summary_json) VALUES (?,?,?,1,'{}')",
                    (run_id, "2026-09-17T01:56:21Z", "REVIEW"),
                )
                conn.execute(
                    """
                    INSERT INTO coverage_audit_results(
                        coverage_audit_id,assurance_run_id,source_id,audit_method,status,official_candidate_count,
                        canonical_covered_count,missing_count,checked_at,details_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "coverage-pass-s20", run_id, "S20", "independent-listing-links", "PASS", 4,
                        4, 0, "2026-09-17T01:56:21Z", "{}",
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO canonical_items(
                        canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,
                        deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "moep:7157:2026-09-11", "S20", "TENDER", "230kV ACCC conductor replacement", "MOEP-CONTENT-7157",
                        "230kV ACCC conductor replacement", "2026-09-11", None, None,
                        "https://moep.gov.mm/mm/ignite/contentView/7157", "h", "e", json.dumps(payload),
                        "2026-09-11T00:00:00Z", "2026-09-11T00:00:00Z",
                    ),
                )
                conn.execute(
                    "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                    (
                        "00000000-0000-4000-8000-000000000221", "S20", "moep:7157:2026-09-11", "NEW",
                        "2026-09-11T10:10:01Z", "{}",
                    ),
                )

            latest = assurance_status(database=database)
            self.assertEqual(latest["coverage"][0]["status"], "PASS")
            self.assertEqual(latest["coverage_risk_count"], 1)
            risk = latest["coverage_risks"][0]
            self.assertEqual(risk["source_id"], "S20")
            self.assertEqual(risk["risk_kind"], "BUSINESS_DETAIL_GAP")
            self.assertEqual(risk["coverage_status"], "DETAIL_PARTIAL")
            self.assertEqual(risk["affected_current_opportunities"], 1)
            self.assertEqual(risk["attachment_health"], "DEGRADED_HTTP_404")
            self.assertEqual(risk["missing_business_fields"], ["deadline", "participation_details"])
            self.assertEqual(risk["examples"][0]["canonical_key"], "moep:7157:2026-09-11")
            self.assertFalse(risk["known_miss"])

    def test_s20_business_detail_risk_shrinks_after_reviewed_official_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            run_id = "00000000-0000-4000-8000-000000000230"
            records = (
                ("moep:7144:2026-09-04", "MOEP-CONTENT-7144", "2026-09-04", "https://moep.gov.mm/mm/ignite/contentView/7144", "DPTSC-221.pdf"),
                ("moep:7150:2026-09-08", "MOEP-CONTENT-7150", "2026-09-08", "https://moep.gov.mm/mm/ignite/contentView/7150", "YESC-4778.pdf"),
                ("moep:7151:2026-09-08", "MOEP-CONTENT-7151", "2026-09-08", "https://moep.gov.mm/mm/ignite/contentView/7151", "EPGE-1955.pdf"),
                ("moep:7157:2026-09-11", "MOEP-CONTENT-7157", "2026-09-11", "https://moep.gov.mm/mm/ignite/contentView/7157", "ACCC_Conductor_Form.pdf"),
            )
            with connect(database) as conn, conn:
                conn.execute(
                    "INSERT INTO assurance_runs(assurance_run_id,started_at,status,network_checks,summary_json) VALUES (?,?,?,1,'{}')",
                    (run_id, "2026-09-17T16:00:00Z", "REVIEW"),
                )
                conn.execute(
                    """
                    INSERT INTO coverage_audit_results(
                        coverage_audit_id,assurance_run_id,source_id,audit_method,status,official_candidate_count,
                        canonical_covered_count,missing_count,checked_at,details_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    ("coverage-pass-s20-reviewed", run_id, "S20", "independent-listing-links", "PASS", 4, 4, 0, "2026-09-17T16:00:00Z", "{}"),
                )
                for index, (key, ref, publication, url, attachment) in enumerate(records, start=1):
                    payload = {
                        "issuer": "MOEP unit",
                        "reference_no": ref,
                        "publication_date": publication,
                        "url": url,
                        "detail_completeness": "HTML_PARTIAL_ATTACHMENT_METADATA",
                        "attachment_name": attachment,
                        "attachment_url": f"https://moep.gov.mm/mm/userfile/{attachment}",
                    }
                    conn.execute(
                        """
                        INSERT INTO canonical_items(
                            canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,
                            deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            key, "S20", "TENDER", key, ref, key, publication, None, None, url,
                            f"h{index}", f"e{index}", json.dumps(payload), publication + "T00:00:00Z", publication + "T00:00:00Z",
                        ),
                    )
                    conn.execute(
                        "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
                        (f"00000000-0000-4000-8000-00000000023{index}", "S20", key, "NEW", publication + "T10:00:00Z", "{}"),
                    )

            latest = assurance_status(database=database)
            self.assertEqual(latest["coverage_risk_count"], 1)
            risk = latest["coverage_risks"][0]
            self.assertEqual(risk["source_id"], "S20")
            self.assertEqual(risk["affected_current_opportunities"], 1)
            self.assertEqual(risk["reviewed_official_recovery_count"], 3)
            self.assertEqual(risk["examples"][0]["canonical_key"], "moep:7150:2026-09-08")
            self.assertEqual(risk["missing_business_fields"], ["deadline", "participation_details"])

    def test_reviewed_external_recovery_is_not_direct_coverage_pass(self) -> None:
        recovered = {
            "source_id": "S13",
            "status": "PARTIAL",
            "missing": [],
            "details": {
                "issuer_page_coverage_debt_retained": True,
                "verified_external_recovery_count": 1,
                "risk_kind": "ISSUER_DISCOVERY_PARTIAL",
            },
        }
        self.assertTrue(coverage_has_reviewed_external_recovery(recovered))
        self.assertFalse(coverage_has_reviewed_external_recovery({**recovered, "status": "PASS"}))
        self.assertFalse(coverage_has_reviewed_external_recovery({**recovered, "missing": ["x"]}))

    def test_metric_review_separates_recovered_partial_from_check_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            run_id = "metric-coverage-semantics"
            now = datetime(2026, 9, 20, 0, 0, tzinfo=UTC)
            coverage_rows = [
                (
                    {
                        "source_id": source_id,
                        "status": "PARTIAL",
                        "missing": [],
                        "details": {
                            "issuer_page_coverage_debt_retained": True,
                            "verified_external_recovery_count": 1,
                            "risk_kind": "ISSUER_DISCOVERY_PARTIAL",
                        },
                    }
                    if source_id == "S13"
                    else {"source_id": source_id, "status": "CHECK_FAILED", "missing": [], "details": {}}
                    if source_id == "S21"
                    else {"source_id": source_id, "status": "PASS", "missing": [], "details": {}}
                )
                for source_id in MANDATORY_COVERAGE_SOURCES
            ]
            with connect(database) as conn, conn:
                conn.execute(
                    "INSERT INTO assurance_runs(assurance_run_id,started_at,status,network_checks,summary_json) VALUES (?,?,?,?,?)",
                    (run_id, "2026-09-20T00:00:00Z", "RUNNING", 0, "{}"),
                )
                with patch(
                    "signalforge.assurance.source_scorecard",
                    return_value={"summary": {}, "sources": []},
                ):
                    review = _metric_review(
                        conn,
                        assurance_run_id=run_id,
                        coverage_rows=coverage_rows,
                        now=now,
                        registry=Registry(raw={}),
                    )
            metrics = review["metrics"]
            reasons = review["conclusions"]["review_reasons"]
            self.assertEqual(metrics["mandatory_coverage_proven"], 5)
            self.assertEqual(metrics["mandatory_reviewed_external_recovery_sources"], ["S13"])
            self.assertEqual(metrics["mandatory_check_failed_sources"], ["S21"])
            self.assertEqual(metrics["mandatory_business_coverage_accounted"], 6)
            self.assertEqual(metrics["mandatory_business_coverage_accounted_rate"], 0.8571)
            self.assertIn("MANDATORY_COVERAGE_PARTIAL_RECOVERED_EXTERNALLY", reasons)
            self.assertIn("MANDATORY_COVERAGE_CHECK_FAILED", reasons)
            self.assertNotIn("MANDATORY_COVERAGE_NOT_FULLY_PROVEN", reasons)

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
