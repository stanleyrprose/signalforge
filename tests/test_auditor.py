from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.auditor import audit
from signalforge.cli import main, verb_manifest
from signalforge.config import Registry
from signalforge.db import connect, migrate


def _registry() -> Registry:
    health = {
        "freshness_yellow_seconds": 3600,
        "freshness_red_seconds": 7200,
        "fetch_yellow_failures": 1,
        "fetch_red_failures": 3,
        "parse_window_runs": 10,
        "parse_min_attempts": 1,
        "parse_yellow_ratio": 0.9,
        "parse_red_ratio": 0.7,
        "parse_probe_interval_seconds": 7200,
        "parse_sample_source": "DETAIL_SCHEDULER",
    }
    return Registry(
        {
            "sources": {
                "S13": {
                    "enabled": True,
                    "engine": "direct_http",
                    "network_zone": "myanmar-international",
                    "discovery_url": "https://mpt.test/page-sitemap.xml",
                    "request_timeout_seconds": 30,
                    "request_max_bytes": 2_000_000,
                    "recovery_slo_seconds": 1800,
                    "health_policy": dict(health),
                },
                "S41": {
                    "enabled": True,
                    "engine": "direct_http",
                    "network_zone": "myanmar-international",
                    "discovery_url": "https://viettel.test/feed",
                    "request_timeout_seconds": 30,
                    "request_max_bytes": 1_000_000,
                    "recovery_slo_seconds": 3600,
                    "health_policy": dict(health),
                },
            }
        }
    )


def _sitemap(url: str, lastmod: str = "2026-09-10T10:00:00+00:00") -> bytes:
    return f'''<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>{url}</loc><lastmod>{lastmod}</lastmod></url>
</urlset>'''.encode()


def _mytel_feed(num: int = 17) -> bytes:
    return json.dumps(
        {
            "data": [
                {
                    "id": 100 + num,
                    "created_at": "2026-09-10T09:00:00+00:00",
                    "name": f"Mytel Announcement on Invitation to Bidding {num}/2026/MYTEL-MW System",
                    "content": f"Telecom International Myanmar Co., Ltd (MYTEL) Reference number of Request for Proposal: {num}/2026/MYTEL-MW System",
                }
            ]
        }
    ).encode()


class AuditorTests(unittest.TestCase):
    def _db(self, root: str) -> Path:
        path = Path(root) / "signalforge.db"
        migrate(path)
        with connect(path) as conn, conn:
            for sid in ("S13", "S41"):
                conn.execute(
                    "INSERT INTO source_state(source_id,baseline_complete,last_success_at,next_due_at,last_error,consecutive_failures,updated_at) VALUES (?,?,?,?,?,?,?)",
                    (sid, 1, "2026-09-10T10:00:00Z", "2026-09-10T11:00:00Z", None, 0, "2026-09-10T10:00:00Z"),
                )
        return path

    def _canonical(self, database: Path, *, key: str, source_id: str, url: str) -> None:
        payload = {
            "reference_no": key,
            "project_name": "Test procurement",
            "deadline": "2026-09-20",
            "deadline_time": "16:00",
            "business_stage": "OPPORTUNITY",
            "url": url,
        }
        with connect(database) as conn, conn:
            conn.execute(
                """INSERT INTO canonical_items(canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,content_hash,evidence_sha256,payload_json,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (key, source_id, "TENDER", "Test procurement", key, "Test procurement", "2026-09-10", "2026-09-20", None, url, f"hash-{key}", f"evidence-{key}", json.dumps(payload), "2026-09-10T10:00:00Z", "2026-09-10T10:00:00Z"),
            )

    def test_pass_when_health_and_strategic_coverage_agree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            mpt_url = "https://mpt.com.mm/en/test-procurement/"
            self._canonical(database, key="mpt:TEST-1", source_id="S13", url=mpt_url)
            self._canonical(database, key="mytel:17-2026", source_id="S41", url="https://viettelglobal.com.vn/en/test")
            def fetch(url: str, **_kwargs) -> bytes:
                if "sitemap" in url:
                    return _sitemap(mpt_url)
                if url == mpt_url:
                    return b"<table><tr><td>Reference No</td><td>TEST-1</td></tr><tr><td>Project Name</td><td>Test procurement</td></tr></table>"
                raise AssertionError(url)

            result = audit(database=database, registry=_registry(), now=datetime(2026,9,10,10,30,tzinfo=UTC), fetcher=fetch, mytel_fetcher=lambda *_a, **_k: _mytel_feed())
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["finding_count"], 0)
            self.assertEqual(result["checks"]["strategic_coverage"]["S41"]["missing"], [])
            self.assertEqual(result["checks"]["strategic_coverage"]["S13"]["missing"], 0)
            self.assertTrue(result["contract"]["read_only"])

    def test_detects_independent_mpt_and_mytel_coverage_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            mpt_url = "https://mpt.com.mm/en/new-tender/"

            def fetch(url: str, **_kwargs) -> bytes:
                if "sitemap" in url:
                    return _sitemap(mpt_url)
                return b"<table><tr><td>Reference No</td><td>NEW-1</td></tr><tr><td>Project Name</td><td>New project</td></tr></table>"

            result = audit(database=database, registry=_registry(), now=datetime(2026,9,10,10,30,tzinfo=UTC), fetcher=fetch, mytel_fetcher=lambda *_a, **_k: _mytel_feed(18))
            gaps = [item for item in result["findings"] if item["type"] == "COVERAGE_GAP"]
            self.assertEqual(result["status"], "ALERT")
            self.assertEqual({item["code"] for item in gaps}, {"MPT_RECENT_TENDER_PAGE_NOT_CANONICAL", "MYTEL_OFFICIAL_RFP_NOT_CANONICAL"})
            mpt = next(item for item in gaps if item["source_id"] == "S13")
            self.assertEqual(mpt["likely_layer"], "DISCOVERY")

    def test_health_alert_detects_stale_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            with connect(database) as conn, conn:
                conn.execute("UPDATE source_state SET last_success_at='2026-09-10T01:00:00Z' WHERE source_id='S13'")
            result = audit(database=database, registry=_registry(), now=datetime(2026,9,10,10,30,tzinfo=UTC), network=False)
            health = [item for item in result["findings"] if item["type"] == "HEALTH_ALERT"]
            self.assertTrue(any(item["source_id"] == "S13" and item["severity"] == "RED" for item in health))

    def test_signal_and_delivery_identity_anomalies_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = self._db(tmp)
            self._canonical(database, key="mpt:TEST-1", source_id="S13", url="https://mpt.com.mm/en/test/")
            with connect(database) as conn, conn:
                conn.execute("INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)", ("sig-bad","S41","mpt:TEST-1","NEW","2026-09-10T10:15:00Z",json.dumps({"canonical_key":"wrong:key","signal_type":"UPDATED"})))
                conn.execute("INSERT INTO delivery_receipts(delivery_key,channel,canonical_key,signal_id,attention_action,priority_band,payload_sha256,provider_message_id,sent_at) VALUES (?,?,?,?,?,?,?,?,?)", ("delivery-bad","telegram","mpt:TEST-1","missing-signal","PRIORITIZE","HIGH","sha","1","2026-09-10T10:20:00Z"))
            result = audit(database=database, registry=_registry(), now=datetime(2026,9,10,10,30,tzinfo=UTC), network=False)
            codes = {item["code"] for item in result["findings"]}
            self.assertIn("SIGNAL_SOURCE_MISMATCH", codes)
            self.assertIn("SIGNAL_PAYLOAD_IDENTITY_MISMATCH", codes)
            self.assertIn("DELIVERY_RECEIPT_ORPHAN_OR_MISMATCH", codes)

    def test_cli_and_manifest_expose_closed_audit_verb(self) -> None:
        self.assertEqual(verb_manifest()["verbs"]["signalforge-audit"], {"helper_command": "audit", "argument": None})
        with patch("signalforge.cli.audit", return_value={"status": "PASS", "auditor_version": 1}) as run:
            code = main(["audit", "--no-network"])
        self.assertEqual(code, 0)
        run.assert_called_once_with(network=False)


if __name__ == "__main__":
    unittest.main()
