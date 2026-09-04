from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.dica import classify_business_notice, parse_announcement_detail, parse_announcement_listing
from signalforge.engine import run_source

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://www.dica.gov.mm/category/announcements-and-information/"
U52512 = "https://www.dica.gov.mm/52512/"
U52343 = "https://www.dica.gov.mm/52343/"
U51848 = "https://www.dica.gov.mm/51848/"
U51845 = "https://www.dica.gov.mm/51845/"
U50000 = "https://www.dica.gov.mm/50000/"


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


def _detail(post_id: str, date_iso: str, title: str, *, pdf: str | None = None) -> bytes:
    attachment = ""
    if pdf:
        attachment = f'<div class="wp-block-file"><a href="{pdf}">attachment</a><a href="{pdf}" class="wp-block-file__button">Download</a></div>'
    return f'''<!doctype html><html><body>
    <article id="post-{post_id}" class="post category-announcements-and-information">
      <header><h1 class="page-title">{title}</h1><time class="ct-meta-element-date" datetime="{date_iso}">{date_iso[:10]}</time></header>
      <div class="entry-content">{attachment}</div>
    </article></body></html>'''.encode()


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S10"]
    source["baseline_detail_limit"] = 5
    source["delta_detail_limit"] = 5
    source["request_delay_ms"] = 0
    source["bootstrap_seed_urls"] = [U52512, U52343, U51848, U51845]
    source["health_policy"]["parse_probe_interval_seconds"] = 3600
    raw["sources"] = {"S10": source}
    return Registry(raw)


class DicaParserTests(unittest.TestCase):
    def test_listing_parses_current_wordpress_post_shape(self) -> None:
        entries = parse_announcement_listing((FIXTURES / "dica_announcements.html").read_bytes())
        self.assertEqual([e.url for e in entries], [U52512, U52343, U51848, U51845, U50000])
        self.assertEqual(entries[0].lastmod, "2026-08-17T09:02:09+00:00")

    def test_selection_is_explicit_and_unknown_announcements_fail_closed(self) -> None:
        self.assertEqual(classify_business_notice("Notification No. 83/2026, List of Companies Struck Off from the Company Registration"), "COMPANY_STRIKE_OFF_BATCH")
        self.assertEqual(classify_business_notice("ကုမ္ပဏီများသို့ အသိပေးကြေညာခြင်း"), "COMPANY_COMPLIANCE_NOTICE")
        self.assertEqual(classify_business_notice("Notification No. 1 / 2026, The Minimum Criteria Required to be Eligible for Tax Exemption or Relief"), "INVESTMENT_TAX_INCENTIVE")
        self.assertEqual(classify_business_notice("Investment Newsletter (1/2026), investments accepted in Chinese Yuan (CNY)"), "INVESTMENT_CAPITAL_CURRENCY")
        self.assertIsNone(classify_business_notice("DICA Office Holiday Announcement"))

    def test_detail_preserves_event_and_pdf_metadata_without_claiming_pdf_content(self) -> None:
        item = parse_announcement_detail(
            _detail("52343", "2026-07-30T02:17:03+00:00", "ကုမ္ပဏီများသို့ အသိပေးကြေညာခြင်း", pdf="/wp-content/uploads/2026/07/အသိပေးကြေညာချက်Sky-Villa-1.pdf"),
            U52343,
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.item_kind, "REGULATORY_NOTICE")
        self.assertEqual(item.notice_category, "COMPANY_COMPLIANCE_NOTICE")
        self.assertEqual(item.canonical_key, "dica-notice:52343")
        self.assertEqual(item.reference_no, "DICA-POST-52343")
        self.assertEqual(item.reference_no_kind, "issuer_record_id")
        self.assertEqual(item.attachment_name, "အသိပေးကြေညာချက်Sky-Villa-1.pdf")
        self.assertIn("%E1%80", str(item.attachment_url))
        self.assertEqual(item.payload()["pdf_value_gate"], "TRIGGERED_EXTRACTION_RUNTIME_DEFERRED")
        self.assertIsNone(item.payload()["legal_issuer"])


class DicaEngineTests(unittest.TestCase):
    def test_baseline_is_signal_free_unknown_is_acknowledged_and_pdf_is_not_fetched(self) -> None:
        registry = _registry()
        listing = (FIXTURES / "dica_announcements.html").read_bytes()
        mapping = {
            LIST_URL: listing,
            U52512: _detail("52512", "2026-08-17T09:02:09+00:00", "Notification No. 83/2026, List of Companies Struck Off from the Company Registration", pdf="/wp-content/uploads/2026/08/Struck-Off-207-1.pdf"),
            U52343: _detail("52343", "2026-07-30T02:17:03+00:00", "ကုမ္ပဏီများသို့ အသိပေးကြေညာခြင်း", pdf="/wp-content/uploads/2026/07/အသိပေးကြေညာချက်Sky-Villa-1.pdf"),
            U51848: _detail("51848", "2026-04-03T08:14:42+00:00", "Notification No. 1 / 2026, The Minimum Criteria Required to be Eligible for Tax Exemption or ReliefNotification No. 1 / 2026,", pdf="/wp-content/uploads/2026/04/Tax-Relief.pdf"),
            U51845: _detail("51845", "2026-04-03T08:11:46+00:00", "Investment Newsletter (1/2026), announcement that investments are being accepted in Chinese Yuan (CNY) in addition to US Dollars (USD)", pdf="/wp-content/uploads/2026/04/CNY-Notification.pdf"),
            U50000: _detail("50000", "2026-01-01T00:00:00+00:00", "DICA Office Holiday Announcement"),
        }
        fetcher = MapFetcher(mapping)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            result = run_source(
                "S10", registry=registry, now=datetime(2026, 9, 4, 9, 0, tzinfo=UTC),
                fetcher=fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "dica-baseline"},
            )
            self.assertTrue(result["baseline"])
            self.assertEqual(result["fetched"], 5)
            self.assertEqual(result["details_attempted"], 4)
            self.assertEqual(result["details_succeeded"], 4)
            self.assertEqual(result["items"], 4)
            self.assertEqual(result["tenders"], 0)
            self.assertEqual(result["changed"], 4)
            self.assertEqual(result["signals_created"], 0)
            self.assertFalse(any(".pdf" in url.lower() for url in fetcher.calls))

            with sqlite3.connect(db) as conn:
                kinds = conn.execute("SELECT item_kind,count(*) FROM canonical_items WHERE source_id='S10' GROUP BY item_kind").fetchall()
                categories = sorted(json.loads(row[0])["notice_category"] for row in conn.execute("SELECT payload_json FROM canonical_items WHERE source_id='S10'"))
                excluded = conn.execute("SELECT canonical_key,pending_since_at FROM discovery_items WHERE source_id='S10' AND url=?", (U50000,)).fetchone()
                pdf_requests = conn.execute("SELECT count(*) FROM evidence_envelopes WHERE source_id='S10' AND lower(requested_url) LIKE '%.pdf%'").fetchone()[0]
                run = conn.execute("SELECT details_attempted,details_succeeded,tenders_parsed,items_parsed FROM scheduler_runs WHERE source_id='S10'").fetchone()
            self.assertEqual(kinds, [("REGULATORY_NOTICE", 4)])
            self.assertEqual(categories, ["COMPANY_COMPLIANCE_NOTICE", "COMPANY_STRIKE_OFF_BATCH", "INVESTMENT_CAPITAL_CURRENCY", "INVESTMENT_TAX_INCENTIVE"])
            self.assertEqual(excluded, (None, None))
            self.assertEqual(pdf_requests, 0)
            self.assertEqual(run, (4, 4, 0, 4))

            changed_listing = listing.replace(b"2026-08-17T09:02:09+00:00", b"2026-09-04T09:30:00+00:00")
            changed_detail = _detail(
                "52512", "2026-08-17T09:02:09+00:00",
                "Notification No. 83/2026, List of Companies Struck Off from the Company Registration - Updated",
                pdf="/wp-content/uploads/2026/08/Struck-Off-207-1.pdf",
            )
            update_fetcher = MapFetcher({LIST_URL: changed_listing, U52512: changed_detail})
            update = run_source(
                "S10", registry=registry, now=datetime(2026, 9, 4, 9, 31, tzinfo=UTC),
                fetcher=update_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "dica-update"},
            )
            self.assertFalse(update["baseline"])
            self.assertEqual(update["candidates"], 1)
            self.assertEqual(update["changed"], 1)
            self.assertEqual(update["signals_created"], 1)
            with sqlite3.connect(db) as conn:
                keys = conn.execute("SELECT canonical_key FROM canonical_items WHERE source_id='S10' AND canonical_key='dica-notice:52512'").fetchall()
                signal = conn.execute("SELECT signal_type,canonical_key FROM signals WHERE source_id='S10'").fetchone()
            self.assertEqual(keys, [("dica-notice:52512",)])
            self.assertEqual(signal, ("UPDATED", "dica-notice:52512"))


if __name__ == "__main__":
    unittest.main()
