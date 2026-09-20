from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signalforge.cli import main
from signalforge.db import connect, migrate
from signalforge.jev_noise_triage import _candidate_pool, jev_noise_triage_report


def _insert_zero_item(
    database: Path,
    evidence_root: Path,
    *,
    processing_id: str,
    source_id: str,
    artifact_sha: str,
    finished_at: str,
    html: str,
    items_found: int = 0,
    url: str | None = None,
    retain_artifact: bool = True,
) -> None:
    artifact = evidence_root / source_id / f"{artifact_sha}.html"
    if retain_artifact:
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(html, encoding="utf-8")
    with connect(database) as conn, conn:
        scheduler_id = f"s-{processing_id}"
        request_id = f"r-{processing_id}"
        attempt_id = f"a-{processing_id}"
        evidence_id = f"e-{processing_id}"
        conn.execute(
            """
            INSERT INTO scheduler_runs(
                app_run_id,trigger_id,trigger_kind,source_id,worker_run_id,started_at,status
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (scheduler_id,"test","MANUAL",source_id,"worker",finished_at,"SUCCESS"),
        )
        conn.execute(
            """
            INSERT INTO acquisition_requests(
                request_id,schema_version,scheduler_run_id,app_job_ref,source_id,source_policy_version,
                mode,reason,egress_profile,requested_at,primary_method,target_kind,timeout_seconds,
                expected_content_types_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                request_id,1,scheduler_id,None,source_id,1,"TEST","TEST","TEST",finished_at,
                "DIRECT","DETAIL",30,'["text/html"]',
            ),
        )
        conn.execute(
            """
            INSERT INTO acquisition_attempts(
                attempt_id,schema_version,request_id,attempt_number,source_id,source_policy_version,
                method,egress_profile,started_at,status
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (attempt_id,1,request_id,1,source_id,1,"DIRECT","TEST",finished_at,"SUCCESS"),
        )
        conn.execute(
            """
            INSERT INTO evidence_envelopes(
                evidence_id,schema_version,request_id,attempt_id,scheduler_run_id,app_job_ref,source_id,
                source_policy_version,execution_scope,provider_id,provider_baseline_version,egress_profile,
                fetch_method,started_at,fetched_at,requested_url,final_url,http_status,media_type,content_length,
                artifact_id,artifact_sha256,artifact_bytes,artifact_media_type,acquisition_failure_class
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                evidence_id,1,f"r-{processing_id}",f"a-{processing_id}",f"s-{processing_id}",None,source_id,
                1,"TEST","fixture",1,"TEST","DIRECT",finished_at,finished_at,
                url or f"https://example.test/{processing_id}",url or f"https://example.test/{processing_id}",200,
                "text/html",len(html),f"artifact-{processing_id}",artifact_sha,len(html),"text/html",None,
            ),
        )
        conn.execute(
            """
            INSERT INTO processing_records(
                processing_id,schema_version,evidence_id,request_id,attempt_id,source_id,parser_version,
                normalizer_version,canonicalizer_version,started_at,finished_at,status,
                processing_failure_class,items_found,canonical_items,signals_created
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                processing_id,1,evidence_id,f"r-{processing_id}",f"a-{processing_id}",source_id,
                "parser-v1","norm-v1","canon-v1",finished_at,finished_at,"SUCCESS",None,items_found,items_found,0,
            ),
        )


class JevNoiseTriageTests(unittest.TestCase):
    def test_candidate_pool_distinguishes_legacy_and_retention_era_missing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            database=root/"signalforge.db"
            evidence=root/"evidence"
            migrate(database)
            _insert_zero_item(
                database,evidence,processing_id="legacy-missing",source_id="S22",artifact_sha="legacy-missing",
                finished_at="2026-09-16T01:16:00Z",html="legacy",retain_artifact=False,
            )
            _insert_zero_item(
                database,evidence,processing_id="retention-missing",source_id="S40",artifact_sha="retention-missing",
                finished_at="2026-09-16T01:18:00Z",html="unexpected",retain_artifact=False,
            )
            _insert_zero_item(
                database,evidence,processing_id="empty",source_id="S47",artifact_sha="empty",
                finished_at="2026-09-16T01:19:00Z",html="",
            )
            pool,counters=_candidate_pool(
                database=database,evidence_directory=evidence,candidate_limit=10,per_source_cap=5
            )
            self.assertEqual(pool,[])
            self.assertEqual(counters["zero_item_missing_evidence"],2)
            self.assertEqual(counters["zero_item_legacy_missing_evidence"],1)
            self.assertEqual(counters["zero_item_retention_era_missing_evidence"],1)
            self.assertEqual(counters["zero_item_empty_evidence_text"],1)
            report=jev_noise_triage_report(
                database=database,evidence_directory=evidence,candidate_limit=10,per_source_cap=5,top=5,
                evaluator=lambda state: self.fail("missing/empty evidence must not reach Jev"),
            )
            self.assertEqual(report["pool"]["evidence_retention_status"],"REVIEW")
            self.assertTrue(report["pool"]["legacy_missing_evidence_is_diagnostic_only"])

    def test_candidate_pool_excludes_reviewed_and_deduplicates_same_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "signalforge.db"
            evidence = root / "evidence"
            migrate(database)
            _insert_zero_item(
                database,evidence,processing_id="old",source_id="S22",artifact_sha="same",
                finished_at="2026-09-18T00:00:00Z",
                html="<html><body>Open tender for marine engineering works</body></html>",
            )
            _insert_zero_item(
                database,evidence,processing_id="new",source_id="S22",artifact_sha="same",
                finished_at="2026-09-19T00:00:00Z",
                html="<html><body>Open tender for marine engineering works</body></html>",
            )
            _insert_zero_item(
                database,evidence,processing_id="reviewed",source_id="S40",artifact_sha="reviewed",
                finished_at="2026-09-19T01:00:00Z",
                html="<html><body>Tender award result</body></html>",
            )
            _insert_zero_item(
                database,evidence,processing_id="same-artifact-new-processing",source_id="S40",artifact_sha="reviewed",
                finished_at="2026-09-19T03:00:00Z",
                html="<html><body>Tender award result</body></html>",
            )
            with connect(database) as conn, conn:
                conn.execute(
                    """
                    INSERT INTO noise_review_samples(
                        noise_sample_id,assurance_run_id,source_id,candidate_kind,candidate_ref,evidence_url,
                        sample_basis,sampled_at,payload_json,review_status
                    ) VALUES ('sample-1',NULL,'S40','ZERO_ITEM_PROCESSING','processing:reviewed',NULL,
                              'TEST','2026-09-19T02:00:00Z','{"artifact_sha256":"reviewed"}','CONFIRMED_NOISE')
                    """
                )

            pool, counters = _candidate_pool(
                database=database,evidence_directory=evidence,candidate_limit=20
            )
            self.assertEqual(len(pool),1)
            self.assertEqual(pool[0]["candidate_ref"],"processing:new")
            self.assertEqual(counters["zero_item_existing_review"],1)
            self.assertEqual(counters["zero_item_existing_review_artifact"],1)
            self.assertEqual(counters["zero_item_duplicate_artifact"],1)

    def test_candidate_pool_suppresses_zero_item_recovered_later_on_same_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            database=root/"signalforge.db"
            evidence=root/"evidence"
            migrate(database)
            shared_url="https://example.test/listing"
            _insert_zero_item(
                database,evidence,processing_id="old-zero",source_id="S22",artifact_sha="old-sha",
                finished_at="2026-09-16T00:00:00Z",html="<html><body>old listing</body></html>",
                items_found=0,url=shared_url,
            )
            _insert_zero_item(
                database,evidence,processing_id="new-success",source_id="S22",artifact_sha="new-sha",
                finished_at="2026-09-19T00:00:00Z",html="<html><body>recovered listing</body></html>",
                items_found=3,url=shared_url,
            )
            pool,counters=_candidate_pool(
                database=database,evidence_directory=evidence,candidate_limit=10,per_source_cap=5
            )
            self.assertEqual(pool,[])
            self.assertEqual(counters["zero_item_recovered_later"],1)

    def test_candidate_pool_applies_per_source_cap_before_total_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            database=root/"signalforge.db"
            evidence=root/"evidence"
            migrate(database)
            for index in range(4):
                _insert_zero_item(
                    database,evidence,processing_id=f"s40-{index}",source_id="S40",artifact_sha=f"sha-{index}",
                    finished_at=f"2026-09-19T0{index}:00:00Z",
                    html=f"<html><body>result page {index}</body></html>",
                )
            _insert_zero_item(
                database,evidence,processing_id="s22",source_id="S22",artifact_sha="sha-s22",
                finished_at="2026-09-18T23:00:00Z",
                html="<html><body>open tender</body></html>",
            )
            pool,counters=_candidate_pool(
                database=database,evidence_directory=evidence,candidate_limit=4,per_source_cap=2
            )
            sources=[str(row["source_id"]) for row in pool]
            self.assertEqual(sources.count("S40"),2)
            self.assertEqual(sources.count("S22"),1)
            self.assertEqual(counters["bounded_source_counts"],{"S40":2,"S22":1})
            self.assertGreaterEqual(int(counters["source_cap_excluded"]),2)

    def test_triage_ranks_suspicious_candidates_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "signalforge.db"
            evidence = root / "evidence"
            migrate(database)
            _insert_zero_item(
                database,evidence,processing_id="open",source_id="S22",artifact_sha="open",
                finished_at="2026-09-19T03:00:00Z",
                html="<html><body>Open tender for vessel engineering works. Deadline 30 Sep 2026.</body></html>",
            )
            _insert_zero_item(
                database,evidence,processing_id="result",source_id="S40",artifact_sha="result",
                finished_at="2026-09-19T04:00:00Z",
                html="<html><body>Tender award result</body></html>",
            )

            def evaluator(state: dict[str, object]) -> dict[str, object]:
                if state["source_id"] == "S22":
                    return {
                        "open_actionable":0.52,"mission_sector":0.82,
                        "page_state":"contains_open_opportunity","page_state_confidence":0.9,
                        "page_state_probabilities":{},"request_id":"open","model":"jev-test","usage":{},
                    }
                return {
                    "open_actionable":0.08,"mission_sector":0.40,
                    "page_state":"post_bid_result","page_state_confidence":0.95,
                    "page_state_probabilities":{},"request_id":"result","model":"jev-test","usage":{},
                }

            report = jev_noise_triage_report(
                database=database,evidence_directory=evidence,
                candidate_limit=10,top=2,evaluator=evaluator,
            )
            self.assertEqual(report["status"],"SHADOW_ONLY")
            self.assertEqual(report["authority"],"HUMAN_REVIEW_REQUIRED")
            self.assertEqual(report["writes"],"NONE")
            self.assertEqual(report["pool"]["evidence_retention_status"],"PASS")
            self.assertEqual(report["counts"]["review_recommended"],1)
            self.assertEqual(report["rows"][0]["source_id"],"S22")
            self.assertTrue(report["rows"][0]["review_recommended"])
            self.assertEqual(report["rows"][0]["rank"],1)
            with connect(database) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM noise_review_samples").fetchone()[0],0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM missed_signals").fetchone()[0],0)

    def test_nonstandard_latest_audit_candidate_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            database=root/"signalforge.db"
            evidence=root/"evidence"
            migrate(database)
            with connect(database) as conn, conn:
                conn.execute(
                    "INSERT INTO assurance_runs(assurance_run_id,started_at,status,network_checks,summary_json) VALUES ('run','2026-09-19T00:00:00Z','PASS',1,'{}')"
                )
                details=json.dumps({"nonstandard_candidates":[{"url":"https://example.test/nonstandard","title":"Open tender for telecom equipment"}]})
                conn.execute(
                    """
                    INSERT INTO coverage_audit_results(
                        coverage_audit_id,assurance_run_id,source_id,audit_method,status,official_candidate_count,
                        canonical_covered_count,missing_count,checked_at,details_json
                    ) VALUES ('audit','run','S38','TEST','PASS',1,1,0,'2026-09-19T01:00:00Z',?)
                    """,
                    (details,),
                )
            pool,_=_candidate_pool(database=database,evidence_directory=evidence,candidate_limit=10)
            self.assertEqual(len(pool),1)
            self.assertEqual(pool[0]["candidate_kind"],"INDEPENDENT_LISTING_NONSTANDARD")

    def test_cli_exposes_read_only_triage(self) -> None:
        report={"status":"SHADOW_ONLY","authority":"HUMAN_REVIEW_REQUIRED","writes":"NONE"}
        with patch("signalforge.cli.jev_noise_triage_report",return_value=report) as mocked:
            self.assertEqual(
                main([
                    "jev-noise-triage","--candidate-limit","20","--per-source-cap","4","--top","5",
                    "--open-threshold","0.50","--sector-threshold","0.60",
                    "--model","jev-test","--database","/tmp/test.db",
                    "--evidence-root","/tmp/evidence",
                ]),
                0,
            )
        mocked.assert_called_once_with(
            database=Path("/tmp/test.db"),
            evidence_directory=Path("/tmp/evidence"),
            candidate_limit=20,
            per_source_cap=4,
            top=5,
            open_threshold=0.50,
            sector_threshold=0.60,
            model="jev-test",
        )


if __name__ == "__main__":
    unittest.main()
