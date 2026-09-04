from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.cli import status
from signalforge.commerce import classify_business_notice, parse_notification_detail, parse_notification_listing
from signalforge.config import Registry
from signalforge.engine import run_source


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://commerce.gov.mm/my/node/32071"
NODE_33037 = "https://commerce.gov.mm/my/article/asipekennyaakhkmaa/33037"
NODE_33011 = "https://commerce.gov.mm/my/article/asipekennyaakhkmaa-neaakchunr-sttng/33011"
NODE_32972 = "https://commerce.gov.mm/my/article/asipekennyaakhkmaa/32972"
NODE_32990 = "https://commerce.gov.mm/my/article/asipekennyaakhkmaa/32990"

class MapFetcher:
    def __init__(self, mapping: dict[str, bytes]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        try:
            return self.mapping[url]
        except KeyError as exc:
            raise AssertionError(f"unexpected fetch: {url}") from exc


def _detail(node_id: str, title: str, publication: str, *, pdf: str | None = None, label: str | None = None) -> bytes:
    attachment = ""
    if pdf:
        attachment = f'''<div class="field field-node--field-attachment-files field-name-field-attachment-files">
          <a href="{pdf}" type="application/pdf">{label or Path(pdf).name}</a>
        </div>'''
    return f'''<!doctype html><html lang="my"><body>
    <article data-history-node-id="{node_id}" class="node node--id-{node_id} node--type-article node--view-mode-full" role="article">
      <header class="node__header--has-meta node__header">
        <h1 class="node__title"><span class="field field-name-title">{title}</span></h1>
        <span class="node__pubdate"><span class="field field-name-created"><time datetime="{publication}">{publication}</time></span></span>
      </header>
      <div class="node__content">{attachment}</div>
    </article>
    </body></html>'''.encode()


def _commerce_registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S05A"]
    source["baseline_detail_limit"] = 4
    source["delta_detail_limit"] = 4
    source["request_delay_ms"] = 0
    source["poll_interval_seconds"] = 3600
    source["health_policy"]["parse_probe_interval_seconds"] = 3600
    raw["sources"] = {"S05A": source}
    return Registry(raw)


class CommerceParserTests(unittest.TestCase):
    def test_listing_is_scoped_to_notification_block_not_other_quicktabs(self) -> None:
        entries = parse_notification_listing((FIXTURES / "commerce_notifications.html").read_bytes())
        self.assertEqual(
            [entry.url for entry in entries],
            [NODE_33037, NODE_33011, NODE_32972, NODE_32990],
        )
        self.assertEqual(entries[0].lastmod, "2026-07-28T11:51:05+00:00")
        self.assertFalse(any("19965" in entry.url for entry in entries))

    def test_business_selection_is_explicit_and_rejects_training_noise(self) -> None:
        self.assertEqual(classify_business_notice("သွင်းကုန်ရည်ညွှန်းစျေးနှုန်းများ သတ်မှတ်ထုတ်ပြန်ခြင်း"), "IMPORT")
        self.assertEqual(classify_business_notice("ပို့ကုန်သွင်းကုန်လုပ်ငန်းရှင်စိစစ်ရေးကတ် အပ်နှံရန်ကိစ္စ"), "IMPORT_EXPORT")
        self.assertEqual(classify_business_notice("အဆိပ်ရှိပစ္စည်းဖြစ်သော ပိုးသတ်ဆေး ၂ မျိုး"), "PRODUCT_CONTROL")
        self.assertIsNone(classify_business_notice("ကုန်သွယ်ရေးဦးစီးဌာန အမှုထမ်းရာထူး စာမေးပွဲအောင်မြင်သူစာရင်း"))
        self.assertIsNone(classify_business_notice("ကုန်အမှတ်တံဆိပ် သင်တန်းသား စာမေးပွဲအောင်စာရင်း"))

    def test_detail_returns_regulatory_notice_and_preserves_pdf_as_metadata_only(self) -> None:
        payload = _detail(
            "32913",
            "သွင်းကုန်ရည်ညွှန်းစျေးနှုန်းများ သတ်မှတ်ထုတ်ပြန်ခြင်း",
            "2026-05-05T10:26:58+00:00",
            pdf="/sites/default/files/documents/2026/05/Announcement%20for%20Reference%20Rate%20%281-2026%29.pdf",
            label="အသိပေးကြေညာချက် (၁/၂၀၂၆)",
        )
        url = "https://commerce.gov.mm/my/article/asipekennyaakhkmaa/32913"
        notice = parse_notification_detail(payload, url)
        self.assertIsNotNone(notice)
        assert notice is not None
        self.assertEqual(notice.item_kind, "REGULATORY_NOTICE")
        self.assertEqual(notice.canonical_key, "commerce-notice:32913:2026-05-05")
        self.assertEqual(notice.reference_no, "၁/၂၀၂၆")
        self.assertEqual(notice.payload()["reference_no_kind"], "issuer_notice_reference")
        self.assertEqual(notice.notice_category, "IMPORT")
        self.assertEqual(notice.deadline, None)
        self.assertEqual(notice.project_name, notice.title)
        self.assertEqual(notice.attachment_name, "Announcement for Reference Rate (1-2026).pdf")
        self.assertTrue(str(notice.attachment_url).endswith("Announcement%20for%20Reference%20Rate%20%281-2026%29.pdf"))

    def test_irrelevant_detail_is_processing_success_with_no_canonical_object(self) -> None:
        payload = _detail(
            "32990",
            "ကုန်အမှတ်တံဆိပ်မှတ်ပုံတင်ခြင်းဆိုင်ရာ ကိုယ်စားလှယ်သင်တန်း စာမေးပွဲအောင်စာရင်း",
            "2026-06-30T08:44:39+00:00",
        )
        self.assertIsNone(parse_notification_detail(payload, NODE_32990))


class CommerceEngineTests(unittest.TestCase):
    def test_selective_baseline_is_signal_free_pdf_is_not_fetched_and_update_signals_once(self) -> None:
        registry = _commerce_registry()
        listing = (FIXTURES / "commerce_notifications.html").read_bytes()
        detail_33037 = _detail(
            "33037",
            "အဆိပ်ရှိပစ္စည်းဖြစ်သော ပိုးသတ်ဆေး ၂ မျိုးနှင့်စပ်လျဉ်း၍ အသိပေး ကြေညာခြင်း",
            "2026-07-28T11:51:05+00:00",
            pdf="/sites/default/files/documents/2026/07/pesticide.pdf",
            label="အသိပေးကြေညာချက်",
        )
        detail_33011 = _detail(
            "33011",
            "အများပြည်သူသို့ စားအုန်းဆီဖြန့်ဖြူးပေးနေမှု အသိပေးကြေညာချက်",
            "2026-07-11T16:01:33+00:00",
            pdf="/sites/default/files/documents/2026/07/palm-oil.pdf",
        )
        detail_32972 = _detail(
            "32972",
            "ပို့ကုန်သွင်းကုန်လုပ်ငန်းရှင်စိစစ်ရေးကတ် အပ်နှံရန်ကိစ္စ",
            "2026-06-19T06:37:27+00:00",
            pdf="/sites/default/files/documents/2026/06/Pa%20Ta%20Ka%20Check%20Certificate%20Option%201_0.pdf",
        )
        detail_32990 = _detail(
            "32990",
            "ကုန်အမှတ်တံဆိပ်မှတ်ပုံတင်ခြင်းဆိုင်ရာ ကိုယ်စားလှယ်သင်တန်း စာမေးပွဲအောင်စာရင်း",
            "2026-06-30T08:44:39+00:00",
        )

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            baseline_fetcher = MapFetcher(
                {
                    LIST_URL: listing,
                    NODE_33037: detail_33037,
                    NODE_33011: detail_33011,
                    NODE_32972: detail_32972,
                    NODE_32990: detail_32990,
                }
            )
            baseline = run_source(
                "S05A",
                registry=registry,
                now=datetime(2026, 9, 4, 1, 0, tzinfo=UTC),
                fetcher=baseline_fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "commerce-baseline"},
            )
            self.assertTrue(baseline["baseline"])
            self.assertEqual(baseline["fetched"], 4)
            self.assertEqual(baseline["details_attempted"], 3)
            self.assertEqual(baseline["details_succeeded"], 3)
            self.assertEqual(baseline["items"], 3)
            self.assertEqual(baseline["tenders"], 0)
            self.assertEqual(baseline["changed"], 3)
            self.assertEqual(baseline["signals_created"], 0)
            self.assertFalse(any(url.lower().endswith(".pdf") for url in baseline_fetcher.calls))

            with sqlite3.connect(db) as conn:
                rows = conn.execute(
                    "SELECT canonical_key,item_kind,title,project_name FROM canonical_items WHERE source_id='S05A' ORDER BY canonical_key"
                ).fetchall()
                baseline_run = conn.execute(
                    "SELECT details_attempted,details_succeeded,tenders_parsed,items_parsed FROM scheduler_runs WHERE source_id='S05A'"
                ).fetchone()
                irrelevant = conn.execute(
                    "SELECT canonical_key,pending_since_at FROM discovery_items WHERE source_id='S05A' AND url=?",
                    (NODE_32990,),
                ).fetchone()
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(row[1] == "REGULATORY_NOTICE" for row in rows))
            self.assertTrue(all(row[2] == row[3] for row in rows))
            self.assertEqual(baseline_run, (3, 3, 0, 3))
            self.assertEqual(irrelevant, (None, None))

            changed_listing = listing.replace(
                b'2026-06-19T06:37:27+00:00', b'2026-09-04T02:00:00+00:00'
            )
            changed_detail = _detail(
                "32972",
                "ပို့ကုန်သွင်းကုန်လုပ်ငန်းရှင်စိစစ်ရေးကတ် အပ်နှံရန်ကိစ္စ - ပြင်ဆင်အသိပေးချက်",
                "2026-06-19T06:37:27+00:00",
                pdf="/sites/default/files/documents/2026/06/Pa%20Ta%20Ka%20Check%20Certificate%20Option%201_0.pdf",
            )
            update_fetcher = MapFetcher({LIST_URL: changed_listing, NODE_32972: changed_detail})
            update = run_source(
                "S05A",
                registry=registry,
                now=datetime(2026, 9, 4, 2, 1, tzinfo=UTC),
                fetcher=update_fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "commerce-update"},
            )
            self.assertFalse(update["baseline"])
            self.assertEqual(update["candidates"], 1)
            self.assertEqual(update["changed"], 1)
            self.assertEqual(update["signals_created"], 1)
            self.assertEqual(update_fetcher.calls, [LIST_URL, NODE_32972])

            with sqlite3.connect(db) as conn:
                signal = conn.execute(
                    "SELECT source_id,signal_type,canonical_key,payload_json FROM signals"
                ).fetchone()
                canonical = conn.execute(
                    "SELECT item_kind,title FROM canonical_items WHERE canonical_key='commerce-notice:32972:2026-06-19'"
                ).fetchone()
            self.assertEqual(signal[:3], ("S05A", "UPDATED", "commerce-notice:32972:2026-06-19"))
            self.assertIn('"item_kind":"REGULATORY_NOTICE"', signal[3])
            self.assertEqual(canonical[0], "REGULATORY_NOTICE")
            self.assertIn("ပြင်ဆင်အသိပေးချက်", canonical[1])

            with patch.dict(os.environ, {"SIGNALFORGE_DB": str(db), "SIGNALFORGE_REPO_ROOT": str(ROOT)}, clear=False):
                health = status(now=datetime(2026, 9, 4, 2, 2, tzinfo=UTC), registry=registry)
            source_health = health["sources"][0]["health"]
            self.assertEqual(source_health["parse_attempts"], 4)
            self.assertEqual(source_health["parse_successes"], 4)
            self.assertEqual(source_health["parse_health"], "GREEN")


if __name__ == "__main__":
    unittest.main()
