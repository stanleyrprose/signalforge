from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.moea import (
    MOEA_LIST_URL,
    MoeaParseError,
    is_procurement_invitation,
    parse_actionable_deadline,
    parse_explicit_deadline,
    parse_tender_records,
    parse_visible_publication_date,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class SinglePageFetcher:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs) -> bytes:
        self.calls.append(url)
        if url != MOEA_LIST_URL:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.payload


def _registry() -> Registry:
    raw = json.loads(json.dumps(Registry.load(ROOT).raw))
    source = raw["sources"]["S31"]
    raw["sources"] = {"S31": source}
    return Registry(raw)


class MoeaParserTests(unittest.TestCase):
    def test_visible_date_and_explicit_myanmar_digit_deadline(self) -> None:
        self.assertEqual(parse_visible_publication_date("27 July 2026"), "2026-07-27")
        self.assertEqual(parse_explicit_deadline("တင်ဒါတင်သွင်းရမည့်နောက်ဆုံးရက် - (၇-၈-၂၀၂၆) ရက်"), "2026-08-07")
        self.assertIsNone(parse_explicit_deadline("တင်ဒါပုံစံရောင်းချမည့်ရက် ၂၉-၅-၂၀၂၆ မှ ၁၀-၆-၂၀၂၆"))

    def test_actionable_deadline_distinguishes_submission_acceptance_from_form_sale(self) -> None:
        final = parse_actionable_deadline("တင်ဒါတင်သွင်းရမည့်နောက်ဆုံးရက် - (၇-၈-၂၀၂၆) ရက်၊ ရုံးချိန်အတွင်း")
        self.assertEqual(final, ("2026-08-07", None, "BID_SUBMISSION_DEADLINE", "EXPLICIT_HTML_COMMENT_FINAL_SUBMISSION_DATE"))
        application_final = parse_actionable_deadline(
            "တင်ဒါလျှောက်လွှာ စတင်ရောင်းချမည့်ရက် - (၁၂-၆-၂၀၂၃) "
            "တင်ဒါလျှောက်လွှာ တင်သွင်းရမည့်နောက်ဆုံးရက် - (၂၇-၆-၂၀၂၃)"
        )
        self.assertEqual(
            application_final,
            ("2023-06-27", None, "BID_SUBMISSION_DEADLINE", "EXPLICIT_HTML_COMMENT_FINAL_SUBMISSION_DATE"),
        )

        acceptance = parse_actionable_deadline(
            "တင်ဒါလျှောက်လွှာလက်ခံမည့်ရက် - ၂၉-၅-၂၀၂၆ ရက်မှ ၁၀-၆-၂၀၂၆ ရက်အထိ "
            "၀၉:၃၀ နာရီ မှ ၁၆:၀၀ နာရီ။ သတ်မှတ်ကာလထက်ကျော်လွန်သော တင်ဒါများကို ထည့်သွင်းစဉ်းစားမည်မဟုတ်ပါ။"
        )
        self.assertEqual(
            acceptance,
            (
                "2026-06-10",
                "16:00",
                "TENDER_APPLICATION_ACCEPTANCE_CLOSE",
                "EXPLICIT_HTML_COMMENT_TENDER_APPLICATION_ACCEPTANCE_WINDOW_END",
            ),
        )

        sale_only = parse_actionable_deadline("တင်ဒါပုံစံရောင်းချမည့်ရက် ၂၉-၅-၂၀၂၆ မှ ၁၀-၆-၂၀၂၆")
        self.assertEqual(sale_only[:3], (None, None, None))
        unrelated_final = parse_actionable_deadline("စာရင်းပေးသွင်းရန် နောက်ဆုံးရက် ၁၀-၆-၂၀၂၆")
        self.assertEqual(unrelated_final[:3], (None, None, None))

    def test_selection_excludes_awards_and_non_procurement_leases(self) -> None:
        self.assertTrue(is_procurement_invitation("အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း"))
        self.assertFalse(is_procurement_invitation("တင်ဒါအောင်မြင်သော ကုမ္ပဏီများစာရင်း"))
        self.assertFalse(is_procurement_invitation("ဆိုင်ခန်း ငှားရမ်းရန် တင်ဒါခေါ်ယူခြင်း"))

    def test_listing_yields_three_procurement_records_without_fetching_attachments(self) -> None:
        rows = parse_tender_records((FIXTURES / "moea_tenders.html").read_bytes())
        self.assertEqual(len(rows), 3)
        self.assertEqual([row.publication_date for row in rows], ["2026-07-27", "2026-05-28", "2026-02-04"])
        self.assertEqual(rows[0].deadline, "2026-08-07")
        self.assertEqual(rows[0].deadline_kind, "BID_SUBMISSION_DEADLINE")
        self.assertEqual(rows[1].deadline, "2026-06-10")
        self.assertEqual(rows[1].deadline_time, "16:00")
        self.assertEqual(rows[1].deadline_kind, "TENDER_APPLICATION_ACCEPTANCE_CLOSE")
        self.assertIsNone(rows[2].deadline)
        self.assertIn("သက်မွေးပညာသင်တန်းစင်တာ", rows[0].scope_summary or "")
        self.assertEqual(rows[0].location, "နေပြည်တော်")
        self.assertEqual(rows[0].attachment_name, "1785147339.pdf")
        self.assertEqual(rows[0].payload()["reference_no_kind"], "issuer_archive_event_fingerprint")
        self.assertEqual(rows[0].payload()["attachment_policy"], "METADATA_ONLY_NON_BLOCKING")
        self.assertEqual(rows[0].payload()["semantic_version"], 3)
        self.assertTrue(rows[0].canonical_key.startswith("moea:2026-07-27:"))

    def test_structural_drift_fails_closed_but_valid_empty_is_allowed(self) -> None:
        with self.assertRaisesRegex(MoeaParseError, "listing structure"):
            parse_tender_records(b"<html><body>changed</body></html>")
        award_only = b'''<div class="tender-content"><h4 class="tender-title">Tender Award Result</h4><ul><li>27 July 2026</li><li>Nay Pyi Taw</li></ul><div class="tender-action"><a href="news_images/pdf/1.pdf">View</a></div></div>'''
        self.assertEqual(parse_tender_records(award_only), [])

    def test_identity_collision_with_different_attachment_fails_closed(self) -> None:
        html = b'''<div class="tender-content"><h4 class="tender-title">Open Tender Invitation</h4><ul><li>27 July 2026</li><li>Nay Pyi Taw</li></ul><div class="tender-action"><a href="news_images/pdf/a.pdf">View</a></div></div><div class="tender-content"><h4 class="tender-title">Open Tender Invitation</h4><ul><li>27 July 2026</li><li>Nay Pyi Taw</li></ul><div class="tender-action"><a href="news_images/pdf/b.pdf">View</a></div></div>'''
        with self.assertRaisesRegex(MoeaParseError, "identity collision"):
            parse_tender_records(html)


class MoeaEngineTests(unittest.TestCase):
    def test_baseline_is_one_html_fetch_signal_free_and_pdf_is_not_fetched(self) -> None:
        listing = (FIXTURES / "moea_tenders.html").read_bytes()
        registry = _registry()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            fetcher = SinglePageFetcher(listing)
            result = run_source(
                "S31",
                registry=registry,
                now=datetime(2026, 9, 7, 4, 0, tzinfo=UTC),
                fetcher=fetcher,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "moea-baseline"},
            )
            self.assertTrue(result["baseline"])
            self.assertTrue(result["listing_complete"])
            self.assertEqual(result["items"], 3)
            self.assertEqual(result["tenders"], 3)
            self.assertEqual(result["details_attempted"], 0)
            self.assertEqual(result["changed"], 3)
            self.assertEqual(result["signals_created"], 0)
            self.assertEqual(fetcher.calls, [MOEA_LIST_URL])

            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items WHERE source_id='S31'").fetchone()[0], 3)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S31'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S31'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence_envelopes WHERE source_id='S31' AND lower(requested_url) LIKE '%.pdf%'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT details_attempted,tenders_parsed,items_parsed FROM scheduler_runs WHERE source_id='S31'").fetchone(), (0, 3, 3))

    def test_listing_semantic_v2_to_v3_transition_is_suppressed_once(self) -> None:
        listing = (FIXTURES / "moea_tenders.html").read_bytes()
        registry = _registry()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "signalforge.db"
            evidence = base / "evidence"
            fetcher = SinglePageFetcher(listing)
            baseline = run_source(
                "S31",
                registry=registry,
                now=datetime(2026, 9, 10, 2, 0, tzinfo=UTC),
                fetcher=fetcher,
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "moea-v3-baseline"},
            )
            self.assertEqual(baseline["signals_created"], 0)

            with sqlite3.connect(db) as conn:
                key = conn.execute(
                    "SELECT canonical_key FROM canonical_items WHERE source_id='S31' AND publication_date='2026-05-28'"
                ).fetchone()[0]
                payload = json.loads(conn.execute(
                    "SELECT payload_json FROM canonical_items WHERE canonical_key=?", (key,)
                ).fetchone()[0])
                payload["semantic_version"] = 2
                payload["deadline_time"] = None
                payload["deadline_kind"] = None
                payload["deadline"] = None
                payload["deadline_evidence"] = "UNKNOWN_NO_ACTIONABLE_DEADLINE_IN_HTML_COMMENT"
                conn.execute(
                    "UPDATE canonical_items SET content_hash='moea-v2-before-v3-transition',deadline=NULL,payload_json=? WHERE canonical_key=?",
                    (json.dumps(payload, ensure_ascii=False, sort_keys=True), key),
                )
                conn.commit()

            enrichment = run_source(
                "S31",
                registry=registry,
                now=datetime(2026, 9, 10, 3, 0, tzinfo=UTC),
                fetcher=SinglePageFetcher(listing),
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "moea-v3-transition"},
            )
            self.assertEqual(enrichment["changed"], 1)
            self.assertEqual(enrichment["signals_created"], 0)

            with sqlite3.connect(db) as conn:
                payload = json.loads(conn.execute(
                    "SELECT payload_json FROM canonical_items WHERE canonical_key=?", (key,)
                ).fetchone()[0])
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S31'").fetchone()[0], 0)
                self.assertEqual(payload["semantic_version"], 3)
                self.assertEqual(payload["deadline"], "2026-06-10")
                self.assertEqual(payload["deadline_time"], "16:00")
                self.assertEqual(payload["deadline_kind"], "TENDER_APPLICATION_ACCEPTANCE_CLOSE")

                payload["deadline"] = "2026-06-09"
                conn.execute(
                    "UPDATE canonical_items SET content_hash='wrong-v3-deadline',deadline=?,payload_json=? WHERE canonical_key=?",
                    ("2026-06-09", json.dumps(payload, ensure_ascii=False, sort_keys=True), key),
                )
                conn.commit()

            corrected = run_source(
                "S31",
                registry=registry,
                now=datetime(2026, 9, 10, 4, 0, tzinfo=UTC),
                fetcher=SinglePageFetcher(listing),
                force=True,
                database=db,
                evidence=evidence,
                worker_context={"run_id": "moea-v3-correction"},
            )
            self.assertEqual(corrected["changed"], 1)
            self.assertEqual(corrected["signals_created"], 1)
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S31'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT signal_type FROM signals WHERE source_id='S31'").fetchone()[0], "UPDATED")


if __name__ == "__main__":
    unittest.main()
