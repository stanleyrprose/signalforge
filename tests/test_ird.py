from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.ird import classify_business_notice, parse_announcement_detail, parse_announcement_listing

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_URL = "https://www.ird.gov.mm/announcement-lists"
U104 = f"{LIST_URL}/104"
U102 = f"{LIST_URL}/102"
U97 = f"{LIST_URL}/97"
U94 = f"{LIST_URL}/94"
U99 = f"{LIST_URL}/99"


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


def _detail(record_id: str, date_text: str, title: str, body: str = "", *, pdf: str | None = None) -> bytes:
    attachment = ""
    if pdf:
        attachment = f'<p class="mb-1">Attachments</p><ul><li><a href="{pdf}" target="__blank" class="btn btn-primary">{Path(pdf).name}</a></li></ul>'
    return f'''<!doctype html><html><body>
    <div class="postbox__wrapper postbox__details"><div class="postbox__item"><div class="postbox__content">
      <div class="postbox__meta"><span><i class="far fa-calendar-check"></i> {date_text} </span><span><a href="#">IRD Admin</a></span></div>
      <h3 class="postbox__title">{title}</h3>
      <div class="postbox__text mb-40"><p>{body}</p></div>
      {attachment}
    </div></div></div></body></html>'''.encode()


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S12"]
    source["baseline_detail_limit"] = 5
    source["delta_detail_limit"] = 5
    source["request_delay_ms"] = 0
    source["bootstrap_seed_urls"] = [U104, U97, U94]
    source["health_policy"]["parse_probe_interval_seconds"] = 3600
    raw["sources"] = {"S12": source}
    return Registry(raw)


class IrdParserTests(unittest.TestCase):
    def test_listing_parses_visible_dates_and_record_urls(self) -> None:
        entries = parse_announcement_listing((FIXTURES / "ird_announcements.html").read_bytes())
        self.assertEqual([e.url for e in entries], [U104, U102, U97, U94, U99])
        self.assertEqual(entries[0].lastmod, "2026-09-03T00:00:00+00:00")
        self.assertEqual(entries[2].lastmod, "2026-05-14T00:00:00+00:00")

    def test_classifier_uses_title_for_exclusion_and_body_for_tax_context(self) -> None:
        self.assertEqual(
            classify_business_notice(
                "သတ်မှတ်ရက်အတွင်း အခွန်ထမ်းမှတ်ပုံတင်လက်မှတ်လျှောက်ထားရန် အသိပေးနှိုးဆော်ချက်",
                "TIN အသုံးပြု၍ တင်ဒါဝင်ရောက်ယှဉ်ပြိုင်နိုင်သည်",
            ),
            "TAX_REGISTRATION",
        )
        self.assertEqual(classify_business_notice("ဓာတ်မြေသြဇာတင်သွင်းမှုအပေါ် ကြိုတင်ဝင်ငွေခွန် ကင်းလွတ်ခွင့်ပြုခြင်း"), "TAX_EXEMPTION")
        self.assertIsNone(classify_business_notice("ပြည်တွင်းအခွန်များဦးစီးဌာန ကန့်သတ်မှုမရှိသောတင်ဒါခေါ်ယူခြင်း", "အခွန်ဦးစီးဌာန"))
        self.assertIsNone(classify_business_notice('အဂတိလိုက်စားမှု ကင်းရှင်းစေရေး "1111" ကို ဖြေကြားပေးရန်'))

    def test_detail_returns_regulatory_notice_and_encodes_pdf_metadata_only(self) -> None:
        payload = _detail(
            "94",
            "Apr 02, 2026",
            "ဓာတ်မြေသြဇာတင်သွင်းမှုအပေါ် ကြိုတင်ဝင်ငွေခွန် ကင်းလွတ်ခွင့်ပြုခြင်း",
            pdf="/storage/announcements/69cdedc3f219b-သတင်း (ဓာတ်မြေဩဇာ).pdf",
        )
        notice = parse_announcement_detail(payload, U94)
        self.assertIsNotNone(notice)
        assert notice is not None
        self.assertEqual(notice.item_kind, "REGULATORY_NOTICE")
        self.assertEqual(notice.notice_category, "TAX_EXEMPTION")
        self.assertEqual(notice.canonical_key, "ird-notice:94:2026-04-02")
        self.assertEqual(notice.payload()["reference_no_kind"], "issuer_record_id")
        self.assertIsNone(notice.deadline)
        self.assertIn("%E1%80", str(notice.attachment_url))
        self.assertIn("%20", str(notice.attachment_url))


class IrdEngineTests(unittest.TestCase):
    def test_selective_baseline_is_signal_free_and_never_fetches_pdf(self) -> None:
        registry = _registry()
        listing = (FIXTURES / "ird_announcements.html").read_bytes()
        details = {
            U104: _detail("104", "Sep 03, 2026", "ပြည်ထောင်စုနယ်မြေလိပ်စာဖြင့် ဖွဲ့စည်းတည်ထောင်ထားသည့် အခွန်ထမ်းကုမ္ပဏီများအတွက် အသိပေးကြေညာချက်", "အခွန်ထမ်းကုမ္ပဏီ TIN မှတ်ပုံတင်ခြင်း"),
            U102: _detail("102", "Aug 15, 2026", "ပြည်တွင်းအခွန်များဦးစီးဌာန ကန့်သတ်မှုမရှိသောတင်ဒါခေါ်ယူခြင်း", "အခွန်ဦးစီးဌာန ဝယ်ယူရေး"),
            U97: _detail("97", "May 14, 2026", "သတ်မှတ်ရက်အတွင်း အခွန်ထမ်းမှတ်ပုံတင်လက်မှတ်လျှောက်ထားရန် အသိပေးနှိုးဆော်ချက်", "TIN ဖြင့် တင်ဒါဝင်ရောက်ယှဉ်ပြိုင်ရာတွင် အသုံးပြုရမည်", pdf="/storage/announcements/နှိုးဆော်စာ update.pdf"),
            U94: _detail("94", "Apr 02, 2026", "ဓာတ်မြေသြဇာတင်သွင်းမှုအပေါ် ကြိုတင်ဝင်ငွေခွန် ကင်းလွတ်ခွင့်ပြုခြင်း", pdf="/storage/announcements/သတင်း (ဓာတ်မြေဩဇာ).pdf"),
            U99: _detail("99", "Jun 09, 2026", 'အဂတိလိုက်စားမှု ကင်းရှင်းစေရေး "1111" ကို ဖြေကြားပေးရန်', "အခွန်ဦးစီးဌာန"),
        }
        fetcher = MapFetcher({LIST_URL: listing, **details})
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            result = run_source(
                "S12",
                registry=registry,
                now=datetime(2026, 9, 4, 8, 0, tzinfo=UTC),
                fetcher=fetcher,
                sleeper=lambda _seconds: None,
                force=True,
                database=db,
                evidence=base / "evidence",
                worker_context={"run_id": "ird-baseline"},
            )
            self.assertTrue(result["baseline"])
            self.assertEqual(result["fetched"], 5)
            self.assertEqual(result["details_attempted"], 3)
            self.assertEqual(result["details_succeeded"], 3)
            self.assertEqual(result["items"], 3)
            self.assertEqual(result["tenders"], 0)
            self.assertEqual(result["changed"], 3)
            self.assertEqual(result["signals_created"], 0)
            self.assertFalse(any(".pdf" in url.lower() for url in fetcher.calls))

            with sqlite3.connect(db) as conn:
                kinds = conn.execute("SELECT item_kind,count(*) FROM canonical_items WHERE source_id='S12' GROUP BY item_kind").fetchall()
                run = conn.execute("SELECT details_attempted,details_succeeded,tenders_parsed,items_parsed FROM scheduler_runs WHERE source_id='S12'").fetchone()
                excluded = conn.execute("SELECT url,canonical_key,pending_since_at FROM discovery_items WHERE source_id='S12' AND url IN (?,?) ORDER BY url", (U99,U102)).fetchall()
                pdf_requests = conn.execute("SELECT count(*) FROM evidence_envelopes WHERE source_id='S12' AND lower(requested_url) LIKE '%.pdf%'").fetchone()[0]
            self.assertEqual(kinds, [("REGULATORY_NOTICE", 3)])
            self.assertEqual(run, (3, 3, 0, 3))
            self.assertTrue(all(row[1:] == (None, None) for row in excluded))
            self.assertEqual(pdf_requests, 0)


if __name__ == "__main__":
    unittest.main()
