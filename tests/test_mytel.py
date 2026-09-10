from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.http import FetchError, fetch_bytes_cloudrity_d1n
from signalforge.mytel import MYTEL_FEED_URL, MytelParseError, parse_tender_records

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FEED = (FIXTURES / "mytel-feed.json").read_bytes()


class MytelParserTests(unittest.TestCase):
    def test_feed_filters_mytel_and_merges_extension_by_rfp_reference(self) -> None:
        rows = parse_tender_records(FEED)
        self.assertEqual(len(rows), 2)
        by_ref = {row.reference_no: row for row in rows}

        mw = by_ref["17/2026/MYTEL-MW SYSTEM"]
        self.assertEqual(mw.canonical_key, "mytel:17-2026")
        self.assertEqual(mw.publication_date, "2026-03-16")
        self.assertEqual(mw.deadline, "2026-03-20")
        self.assertEqual(mw.deadline_time, "14:00")
        self.assertEqual(mw.deadline_kind, "TENDER_FORM_SALE_CLOSE")
        self.assertEqual(mw.source_version_kind, "EXTENSION")
        self.assertEqual(mw.source_post_id, 2507)
        self.assertEqual(mw.payload()["business_stage"], "OPPORTUNITY")

        tower = by_ref["30/2026/MYTEL-TOWER (SST & RTT)"]
        self.assertEqual(tower.deadline, "2026-04-06")
        self.assertEqual(tower.deadline_time, "14:00")
        self.assertEqual(tower.deadline_kind, "BID_SUBMISSION_DEADLINE")
        self.assertEqual(tower.deadline_evidence, "OFFICIAL_FEED_EXPLICIT_PROPOSAL_SUBMISSION_DEADLINE")
        self.assertEqual(tower.source_version_kind, "INVITATION")
        self.assertEqual(tower.tender_opening_date, "2026-04-06")
        self.assertEqual(tower.tender_opening_time, "14:00")

    def test_rfp_serial_year_identity_absorbs_extension_suffix_drift(self) -> None:
        raw = json.loads(FEED)
        invitation = dict(raw["data"][0])
        invitation["id"] = 3001
        invitation["created_at"] = "2026-02-23T10:00:00Z"
        invitation["name"] = "Mytel Announcement 03/2026/MYTEL-ANTENNA & TWINBEAM"
        invitation["content"] = (
            "<p>Request Party: TELECOM INTERNATIONAL MYANMAR CO., LTD (MYTEL).<br>"
            "Reference number of Request for Proposal: No. 03/2026/MYTEL-ANTENNA & TWINBEAM – “Purchase Antenna for Mytel”<br>"
            "Deadline for submitting the Proposal Document: before [14h00, March 11th, 2026].</p>"
        )
        invitation["slugable"] = {"key": "mytel-03-invitation"}

        extension = dict(raw["data"][1])
        extension["id"] = 3002
        extension["created_at"] = "2026-03-01T10:00:00Z"
        extension["name"] = "Mytel Announcement on Extension to Bidding No. 03/2026/MYTEL-ANTENNA"
        extension["content"] = (
            "<p>ANNOUNCEMENT ON EXTENSION TO BIDDING<br>"
            "Name of Bidder: TELECOM INTERNATIONAL MYANMAR CO., LTD (MYTEL)<br>"
            "Bidding package name: No. 03/2026/MYTEL-ANTENNA “Purchasing Antenna for Mytel”.<br>"
            "Time to collect bid documents: 14h00 March 15th, 2026 (GMT +6:30 YGN)</p>"
        )
        extension["slugable"] = {"key": "mytel-03-extension"}

        rows = parse_tender_records(json.dumps({"data": [invitation, extension]}).encode())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].canonical_key, "mytel:3-2026")
        self.assertEqual(rows[0].reference_no, "3/2026/MYTEL-ANTENNA")
        self.assertEqual(rows[0].source_version_kind, "EXTENSION")
        self.assertEqual(rows[0].deadline, "2026-03-15")

    def test_created_at_wins_over_incorrect_published_at_for_extension(self) -> None:
        mw = next(row for row in parse_tender_records(FEED) if row.reference_no == "17/2026/MYTEL-MW SYSTEM")
        self.assertEqual(mw.publication_date, "2026-03-16")

    def test_malformed_or_non_list_feed_fails_closed(self) -> None:
        with self.assertRaises(MytelParseError):
            parse_tender_records(b"not-json")
        with self.assertRaises(MytelParseError):
            parse_tender_records(b'{"data": {}}')


class MytelHttpProfileTests(unittest.TestCase):
    def test_d1n_profile_retries_once_with_host_bound_cookie(self) -> None:
        challenge = b'<html><body><script>document.cookie="D1N=abcdef0123456789"+"; expires=x; path=/";window.location.reload(true);</script></body></html>'
        final = b'{"data": []}'
        with patch("signalforge.http._fetch_bytes_with_headers", side_effect=[challenge, final]) as mocked:
            result = fetch_bytes_cloudrity_d1n(MYTEL_FEED_URL, timeout=7, max_bytes=1000)
        self.assertEqual(result, final)
        self.assertEqual(mocked.call_count, 2)
        second_headers = mocked.call_args_list[1].kwargs["headers"]
        self.assertEqual(second_headers["Cookie"], "D1N=abcdef0123456789")

    def test_d1n_profile_rejects_other_hosts_and_persistent_challenge(self) -> None:
        with self.assertRaises(FetchError):
            fetch_bytes_cloudrity_d1n("https://example.com/feed")

        challenge = b'<script>document.cookie="D1N=abcdef0123456789"+"; path=/";window.location.reload(true);</script>'
        with patch("signalforge.http._fetch_bytes_with_headers", side_effect=[challenge, challenge]):
            with self.assertRaises(FetchError):
                fetch_bytes_cloudrity_d1n(MYTEL_FEED_URL, max_bytes=1000)


class MytelEngineTests(unittest.TestCase):
    def test_listing_complete_baseline_is_silent_and_future_new_rfp_signals(self) -> None:
        registry = Registry.load()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"

            baseline = run_source(
                "S41",
                registry=registry,
                now=datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
                fetcher=lambda _url, **_kwargs: FEED,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "mytel-baseline"},
                force=True,
            )
            self.assertEqual(baseline["status"], "SUCCESS")
            self.assertTrue(baseline["listing_complete"])
            self.assertEqual(baseline["items"], 2)
            self.assertEqual(baseline["signals_created"], 0)

            raw = json.loads(FEED)
            raw["data"].append(
                {
                    "id": 9999,
                    "name": "Mytel Announcement on Invitation to Bidding 200/2026/MYTEL-ROUTER – Purchase Router for Mytel",
                    "created_at": "2026-09-10T06:30:00.000000Z",
                    "published_at": "2026-09-10 13:00:00",
                    "content": (
                        "<p>Announcement on Invitation to Bidding<br>"
                        "Request Party: TELECOM INTERNATIONAL MYANMAR CO., LTD (MYTEL).<br>"
                        "Reference number of Request for Proposal: No. 200/2026/MYTEL-ROUTER – “Purchase Router for Mytel”<br>"
                        "Deadline for submitting the Proposal Document: before [14h00, September 18th, 2026. GMT+(6:30)].<br>"
                        "The Proposal Document shall be opened in public on [14h00, September 18th, 2026. GMT+(6:30)].</p>"
                    ),
                    "slugable": {"key": "mytel-announcement-router-200-2026"},
                }
            )
            updated_feed = json.dumps(raw, ensure_ascii=False).encode()
            follow = run_source(
                "S41",
                registry=registry,
                now=datetime(2026, 9, 10, 7, 0, tzinfo=UTC),
                fetcher=lambda _url, **_kwargs: updated_feed,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "mytel-follow"},
                force=True,
            )
            self.assertEqual(follow["changed"], 1)
            self.assertEqual(follow["signals_created"], 1)

            conn = sqlite3.connect(db)
            row = conn.execute(
                "SELECT signal_type,canonical_key FROM signals WHERE source_id='S41' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            self.assertEqual(row, ("NEW", "mytel:200-2026"))
            payload = json.loads(
                conn.execute("SELECT payload_json FROM canonical_items WHERE canonical_key='mytel:200-2026'").fetchone()[0]
            )
            self.assertEqual(payload["deadline_kind"], "BID_SUBMISSION_DEADLINE")
            self.assertEqual(payload["deadline"], "2026-09-18")
            conn.close()


class MytelRegistryTests(unittest.TestCase):
    def test_s41_is_direct_listing_complete_and_bounded(self) -> None:
        source = Registry.load().source("S41")
        self.assertEqual(source["engine"], "direct_http")
        self.assertEqual(source["network_zone"], "myanmar-international")
        self.assertTrue(source["listing_complete_business_records"])
        self.assertFalse(source["discovery_is_tender_only"])
        self.assertEqual(source["http_fetch_profile"], "cloudrity_d1n_v1")
        self.assertIn("limit=100", source["discovery_url"])
        self.assertEqual(source["request_max_bytes"], 1_000_000)
        self.assertEqual(source["canonical_key"], "mytel_rfp_serial_year")
        self.assertFalse(source["first_baseline_customer_signal"])


if __name__ == "__main__":
    unittest.main()
