from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signalforge.config import Registry
from signalforge.engine import run_source
from signalforge.leadtime import precursor_candidates, promote_precursor_from_canonical
from signalforge.moi_project_precursor import (
    MOI_PROJECT_LIST_URL,
    MoiProjectPrecursorParseError,
    parse_project_detail,
    parse_project_listing,
)

ROOT = Path(__file__).resolve().parents[1]
DETAIL_URL = "https://www.moi.gov.mm/news/83043"


def _card(*, node: str, title: str, date: str = "September 25, 2026") -> str:
    return f"""
    <div class="card shadow mb-3">
      <div class="card-title news-title"><a href="/news/{node}">{title}</a></div>
      <p class="my-3">Published: {date}</p>
    </div>
    """


def _listing(*cards: str) -> bytes:
    return ("<html><body>" + "".join(cards) + "</body></html>").encode()


def _detail(
    *,
    node: str = "83043",
    title: str = "Yadanabon Cyber City project coordination meeting",
    body: str = "The digital infrastructure project master plan implementation will continue with network and construction works.",
    date: str = "05/22/2026",
) -> bytes:
    return f"""
    <html><body>
      <article class="node node--type-news" data-history-node-id="{node}">
        <h1 class="post-title">{title}</h1>
        <span class="post-created">{date}</span>
        <div class="field field--name-body">{body}</div>
      </article>
    </body></html>
    """.encode()


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
    raw["sources"] = {"S48": raw["sources"]["S48"]}
    return Registry(raw)


class MoiProjectPrecursorParserTests(unittest.TestCase):
    def test_listing_routes_only_project_plus_target_sector_candidates(self) -> None:
        html = _listing(
            _card(node="83043", title="Yadanabon Cyber City project coordination meeting"),
            _card(node="90001", title="Education project coordination meeting"),
            _card(node="90002", title="5G network technology update"),
        )
        entries = parse_project_listing(html)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].url, DETAIL_URL)
        self.assertEqual(entries[0].lastmod, "2026-09-25T00:00:00+06:30")

    def test_listing_structural_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(MoiProjectPrecursorParseError, "card structure"):
            parse_project_listing(b"<html><body>changed</body></html>")

    def test_detail_requires_forward_action_and_excludes_open_tender(self) -> None:
        item = parse_project_detail(_detail(), DETAIL_URL)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.canonical_key, "moi-project:83043")
        self.assertEqual(item.publication_date, "2026-05-22")
        self.assertEqual(item.precursor_stage_hint, "PROJECT_ANNOUNCEMENT")
        self.assertEqual(list(item.relevance_categories), ["CONSTRUCTION", "TELECOM"])
        payload = item.payload()
        self.assertEqual(payload["business_stage"], "PROJECT_PRECURSOR_CANDIDATE")
        self.assertTrue(payload["precursor_review_required"])
        completed = _detail(body="The digital infrastructure project was completed and opened last year.")
        self.assertIsNone(parse_project_detail(completed, DETAIL_URL))
        tender = _detail(body="The digital infrastructure project invites Open Tender bids for network construction.")
        self.assertIsNone(parse_project_detail(tender, DETAIL_URL))


class MoiProjectPrecursorLifecycleTests(unittest.TestCase):
    def test_new_candidate_is_retained_but_lifecycle_requires_reviewed_promotion(self) -> None:
        registry = _registry()
        baseline_listing = _listing(_card(node="90001", title="Education project coordination meeting"))
        delta_listing = _listing(
            _card(node="90001", title="Education project coordination meeting"),
            _card(node="83043", title="Yadanabon Cyber City project coordination meeting"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            database = base / "signalforge.db"
            evidence = base / "evidence"
            first = run_source(
                "S48", registry=registry, now=datetime(2026, 9, 25, 2, 0, tzinfo=UTC),
                fetcher=MapFetcher({MOI_PROJECT_LIST_URL: baseline_listing}),
                sleeper=lambda _s: None, force=True, database=database, evidence=evidence,
                worker_context={"run_id": "s48-baseline"},
            )
            self.assertTrue(first["baseline"])
            self.assertEqual(first["changed"], 0)
            second = run_source(
                "S48", registry=registry, now=datetime(2026, 9, 25, 3, 0, tzinfo=UTC),
                fetcher=MapFetcher({MOI_PROJECT_LIST_URL: delta_listing, DETAIL_URL: _detail()}),
                sleeper=lambda _s: None, force=True, database=database, evidence=evidence,
                worker_context={"run_id": "s48-delta"},
            )
            self.assertFalse(second["baseline"])
            self.assertEqual(second["changed"], 1)
            with sqlite3.connect(database) as conn:
                canonical = conn.execute(
                    "SELECT created_at,publication_date FROM canonical_items WHERE canonical_key='moi-project:83043'"
                ).fetchone()
                lifecycle_before = conn.execute("SELECT COUNT(*) FROM project_lifecycle_events").fetchone()[0]
            self.assertIsNotNone(canonical)
            assert canonical is not None
            self.assertEqual(canonical[1], "2026-05-22")
            self.assertEqual(lifecycle_before, 0)
            queue = precursor_candidates(database=database)
            self.assertEqual(queue["summary"]["pending_review"], 1)
            self.assertEqual(queue["candidates"][0]["first_retained_at"], canonical[0])
            promoted = promote_precursor_from_canonical(
                canonical_key="moi-project:83043", project_key="yadanabon-cyber-city",
                stage="PROJECT_ANNOUNCEMENT", review_basis="reviewed exact project identity",
                reviewed_by="operator", database=database,
            )
            self.assertEqual(promoted["detected_at"], canonical[0])
            with sqlite3.connect(database) as conn:
                lifecycle_after = conn.execute(
                    "SELECT COUNT(*) FROM project_lifecycle_events WHERE project_key='yadanabon-cyber-city'"
                ).fetchone()[0]
            self.assertEqual(lifecycle_after, 1)


if __name__ == "__main__":
    unittest.main()
