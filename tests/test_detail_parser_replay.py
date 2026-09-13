from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source

ROOT = Path(__file__).resolve().parents[1]
LIST_URL = "https://www.industrymsme.gov.mm/announcements"
FUTURE_URL = "https://www.industrymsme.gov.mm/announcements/1042"
EXPIRED_URL = "https://www.industrymsme.gov.mm/announcements/1032"


def _listing() -> bytes:
    return f"""<html><body><ul>
      <li><h3><a href="{FUTURE_URL}">Open Tender future</a></h3><span class="date">11-Sep-2026</span></li>
      <li><h3><a href="{EXPIRED_URL}">Open Tender expired</a></h3><span class="date">28-Aug-2026</span></li>
    </ul></body></html>""".encode()


def _detail(url: str, *, parseable: bool) -> bytes:
    if not parseable:
        body = "Tender form sale date - 11-9-2026 (09:30)"
    elif url == FUTURE_URL:
        body = "တင်ဒါပိတ်မည့်ရက်နှင့်အချိန် - ၁၈-၉-၂၀၂၆ (၁၆း၃၀)နာရီ"
    else:
        body = "တင်ဒါပိတ်သိမ်းမည့် ရက်နှင့်အချိန် - ၁၀-၉-၂၀၂၆ (၁၆း၀၀)နာရီ"
    record = url.rsplit("/", 1)[-1]
    return f"""<html><body>
      <h3 class="title-bg">Open Tender {record}</h3>
      <span class="date">Fri 11-09-2026</span>
      <span class="author">Official business unit</span>
      <div class="member-desc"><p>{body}</p><p>Official procurement scope with enough business detail for action.</p></div>
    </body></html>""".encode("utf-8")


class Fetcher:
    def __init__(self, *, parseable: bool) -> None:
        self.parseable = parseable
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url == LIST_URL:
            return _listing()
        if url in {FUTURE_URL, EXPIRED_URL}:
            return _detail(url, parseable=self.parseable)
        raise AssertionError(f"unexpected fetch {url}")


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S38"]
    source["engine"] = "direct_http"
    source["network_zone"] = "myanmar-international"
    source["egress_profile"] = "mm-intl-datacenter"
    source["request_delay_ms"] = 0
    source["acquisition_policy"]["primary"] = {"method": "DIRECT_HTTP", "target_kind": "HTML"}
    raw["sources"] = {"S38": source}
    return Registry(raw)


class DetailParserReplayTests(unittest.TestCase):
    def test_zero_item_v1_rows_replay_once_under_v2_and_only_actionable_item_signals(self) -> None:
        registry = _registry()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            database = base / "signalforge.db"
            evidence = base / "evidence"

            baseline = run_source(
                "S38",
                registry=registry,
                now=datetime(2026, 9, 11, 3, 0, tzinfo=UTC),
                fetcher=Fetcher(parseable=False),
                sleeper=lambda _seconds: None,
                force=True,
                database=database,
                evidence=evidence,
                worker_context={"run_id": "industry-old-parser"},
            )
            self.assertTrue(baseline["baseline"])
            self.assertEqual(baseline["changed"], 0)
            self.assertEqual(baseline["signals_created"], 0)

            # Model the real historical state: these successful zero-item records were
            # produced by v1 before the v2 parser migration existed.
            with sqlite3.connect(database) as conn:
                conn.execute(
                    "UPDATE processing_records SET parser_version='industry-announcement-detail-v1' "
                    "WHERE source_id='S38' AND items_found=0"
                )
                conn.commit()

            replay_fetcher = Fetcher(parseable=True)
            replay = run_source(
                "S38",
                registry=registry,
                now=datetime(2026, 9, 13, 10, 0, tzinfo=UTC),
                fetcher=replay_fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=database,
                evidence=evidence,
                worker_context={"run_id": "industry-parser-replay"},
            )
            self.assertFalse(replay["baseline"])
            self.assertEqual(replay["candidates"], 2)
            self.assertEqual(replay["changed"], 2)
            self.assertEqual(replay["signals_created"], 1)
            self.assertEqual(replay_fetcher.calls, [LIST_URL, FUTURE_URL, EXPIRED_URL])

            with sqlite3.connect(database) as conn:
                canonicals = conn.execute(
                    "SELECT canonical_key,deadline FROM canonical_items WHERE source_id='S38' ORDER BY canonical_key"
                ).fetchall()
                signals = conn.execute(
                    "SELECT canonical_key,payload_json FROM signals WHERE source_id='S38'"
                ).fetchall()
                replay_records = conn.execute(
                    "SELECT COUNT(*) FROM processing_records WHERE source_id='S38' "
                    "AND parser_version='industry-announcement-detail-v2' AND status='SUCCESS'"
                ).fetchone()[0]
            self.assertEqual(canonicals, [("industry:1032", "2026-09-10"), ("industry:1042", "2026-09-18")])
            self.assertEqual(len(signals), 1)
            self.assertEqual(signals[0][0], "industry:1042")
            self.assertEqual(json.loads(signals[0][1])["signal_reason"], "ACTIONABLE_BASELINE_RECONCILIATION")
            self.assertEqual(replay_records, 2)

            steady_fetcher = Fetcher(parseable=True)
            steady = run_source(
                "S38",
                registry=registry,
                now=datetime(2026, 9, 13, 10, 10, tzinfo=UTC),
                fetcher=steady_fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=database,
                evidence=evidence,
                worker_context={"run_id": "industry-parser-steady"},
            )
            self.assertEqual(steady["candidates"], 0)
            self.assertEqual(steady["signals_created"], 0)
            self.assertEqual(steady_fetcher.calls, [LIST_URL])


if __name__ == "__main__":
    unittest.main()
