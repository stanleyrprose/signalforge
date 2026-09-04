from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from signalforge.config import Registry
from signalforge.dwir import DwirParseError, parse_tender_detail, parse_tender_listing
from signalforge.engine import run_source

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
HOME_URL = "https://www.dwir.gov.mm/"
URL_298 = "https://www.dwir.gov.mm/index.php/news-events/dwir-news/298-tender"
RAW_297 = "https://www.dwir.gov.mm/index.php/news-events/dwir-news/297-အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"
RAW_296 = "https://www.dwir.gov.mm/index.php/news-events/dwir-news/296-တင်ဒါခေါ်ယူခြင်း"
RAW_289 = "https://www.dwir.gov.mm/index.php/news-events/dwir-news/289-အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း-3"


def _encoded(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/%:@-._~()"), "", ""))


URL_297 = _encoded(RAW_297)
URL_296 = _encoded(RAW_296)
URL_289 = _encoded(RAW_289)


class MapFetcher:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url not in self.payloads:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.payloads[url]


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    raw["sources"] = {"S29": raw["sources"]["S29"]}
    return Registry(raw)


class DwirParserTests(unittest.TestCase):
    def test_homepage_selects_tenders_excludes_result_and_uses_visible_discovery_dates(self) -> None:
        entries = parse_tender_listing((FIXTURES / "dwir_home.html").read_bytes())
        self.assertEqual([entry.url for entry in entries], [URL_298, URL_297, URL_296, URL_289])
        self.assertEqual(entries[0].lastmod, "2026-08-06T00:00:00+06:30")
        self.assertEqual(entries[1].lastmod, "2026-05-29T00:00:00+06:30")
        self.assertEqual(entries[3].lastmod, "2025-09-19T00:00:00+06:30")
        self.assertTrue(all("285-" not in entry.url for entry in entries))
        self.assertIn("%E1%80", entries[1].url)

    def test_homepage_structure_drift_fails_closed_but_valid_empty_board_is_allowed(self) -> None:
        with self.assertRaises(DwirParseError):
            parse_tender_listing(b"<html><body><a href='/news'>News</a></body></html>")
        empty = b"<html><body><h3 class='module-title'>Latest News (Bulletin board)</h3><ul class='lnd_latestnews'></ul></body></html>"
        self.assertEqual(parse_tender_listing(empty), [])

    def test_detail_uses_stable_article_id_detail_publication_date_and_html_scope(self) -> None:
        tender = parse_tender_detail((FIXTURES / "dwir_tender_298.html").read_bytes(), URL_298)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "dwir:298")
        self.assertEqual(tender.publication_date, "2026-08-07")
        self.assertEqual(tender.reference_no, "DWIR-POST-298")
        self.assertEqual(tender.reference_no_kind, "joomla_article_id")
        self.assertIsNone(tender.deadline)
        self.assertIn("ကမ်းပြိုကာကွယ်ရေး", tender.scope_summary or "")
        self.assertIn("ရေလမ်းကောင်းမွန်ရေး", tender.project_name)
        self.assertEqual(tender.embedded_image_count, 1)
        self.assertEqual(tender.payload()["embedded_image_policy"], "UNPARSED_NON_BLOCKING")
        self.assertEqual(tender.payload()["deadline_evidence"], "UNKNOWN_NOT_IN_HTML_TEXT")

    def test_detail_extracts_split_reference_and_keeps_missing_scope_fields_unknown(self) -> None:
        tender = parse_tender_detail((FIXTURES / "dwir_tender_297.html").read_bytes(), URL_297)
        self.assertIsNotNone(tender)
        assert tender is not None
        self.assertEqual(tender.canonical_key, "dwir:297")
        self.assertEqual(tender.publication_date, "2026-05-29")
        self.assertEqual(tender.reference_no, "TENDER No.(2)Q/2026-2027")
        self.assertEqual(tender.reference_no_kind, "issuer_tender_reference")
        self.assertIsNone(tender.deadline)

    def test_outcome_detail_is_not_canonicalized(self) -> None:
        html = b"""<html><body><h1 class='article-title'>Tender Result</h1><time itemprop='datePublished'>01 September 2026</time><section itemprop='articleBody'>Tender winner award result</section></body></html>"""
        self.assertIsNone(parse_tender_detail(html, "https://www.dwir.gov.mm/index.php/news-events/dwir-news/300-tender-result"))


class DwirEngineTests(unittest.TestCase):
    def test_baseline_is_signal_free_and_health_probe_updates_same_article_without_image_fetch(self) -> None:
        registry = _registry()
        home = (FIXTURES / "dwir_home.html").read_bytes()
        detail_298 = (FIXTURES / "dwir_tender_298.html").read_bytes()
        detail_297 = (FIXTURES / "dwir_tender_297.html").read_bytes()
        detail_296 = (FIXTURES / "dwir_tender_296.html").read_bytes()
        detail_289 = (FIXTURES / "dwir_tender_289.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            first_fetcher = MapFetcher({
                HOME_URL: home,
                URL_298: detail_298,
                URL_297: detail_297,
                URL_296: detail_296,
                URL_289: detail_289,
            })
            first = run_source(
                "S29", registry=registry, now=datetime(2026, 9, 5, 0, 0, tzinfo=UTC),
                fetcher=first_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "dwir-baseline"},
            )
            self.assertTrue(first["baseline"])
            self.assertEqual(first["details_attempted"], 4)
            self.assertEqual(first["details_succeeded"], 4)
            self.assertEqual(first["tenders"], 4)
            self.assertEqual(first["signals_created"], 0)
            self.assertEqual(first_fetcher.calls, [HOME_URL, URL_298, URL_297, URL_296, URL_289])

            changed_298 = detail_298.replace("ရေလမ်းကောင်းမွန်ရေးလုပ်ငန်းများ".encode(), "ရေလမ်းကောင်းမွန်ရေးနှင့် သောင်တူးလုပ်ငန်းများ".encode(), 1)
            second_fetcher = MapFetcher({HOME_URL: home, URL_298: changed_298})
            second = run_source(
                "S29", registry=registry, now=datetime(2026, 9, 5, 2, 1, tzinfo=UTC),
                fetcher=second_fetcher, sleeper=lambda _s: None, force=True,
                database=db, evidence=base / "evidence", worker_context={"run_id": "dwir-probe"},
            )
            self.assertFalse(second["baseline"])
            self.assertTrue(second["health_probe"])
            self.assertEqual(second["details_attempted"], 1)
            self.assertEqual(second["details_succeeded"], 1)
            self.assertEqual(second["changed"], 1)
            self.assertEqual(second["signals_created"], 1)
            self.assertEqual(second_fetcher.calls, [HOME_URL, URL_298])

            with sqlite3.connect(db) as conn:
                canonical = conn.execute("SELECT count(*) FROM canonical_items WHERE source_id='S29'").fetchone()[0]
                signal = conn.execute("SELECT signal_type,canonical_key FROM signals WHERE source_id='S29'").fetchone()
                lifecycle = tuple(conn.execute(q).fetchone()[0] for q in [
                    "SELECT count(*) FROM acquisition_requests WHERE source_id='S29'",
                    "SELECT count(*) FROM acquisition_attempts WHERE source_id='S29'",
                    "SELECT count(*) FROM evidence_envelopes WHERE source_id='S29'",
                    "SELECT count(*) FROM processing_records WHERE source_id='S29'",
                ])
                media_requests = conn.execute(
                    "SELECT count(*) FROM evidence_envelopes WHERE source_id='S29' AND (lower(requested_url) LIKE '%.pdf%' OR lower(requested_url) LIKE '%.jpg%' OR lower(requested_url) LIKE 'data:image%')"
                ).fetchone()[0]
            self.assertEqual(canonical, 4)
            self.assertEqual(signal, ("UPDATED", "dwir:298"))
            self.assertEqual(lifecycle, (7, 7, 7, 7))
            self.assertEqual(media_requests, 0)


if __name__ == "__main__":
    unittest.main()
