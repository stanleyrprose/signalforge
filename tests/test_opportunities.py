from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.cli import main
from signalforge.db import connect, migrate
from signalforge.opportunities import current_opportunities


def _insert_canonical(conn, *, key: str, source_id: str, payload: dict[str, object]) -> None:  # type: ignore[no-untyped-def]
    conn.execute(
        """
        INSERT INTO canonical_items(
            canonical_key,source_id,item_kind,title,reference_no,project_name,publication_date,deadline,location,url,
            content_hash,evidence_sha256,payload_json,created_at,updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            key,
            source_id,
            "TENDER",
            str(payload.get("title") or key),
            str(payload.get("reference_no") or key),
            str(payload.get("project_name") or payload.get("title") or key),
            payload.get("publication_date"),
            payload.get("deadline"),
            payload.get("location"),
            str(payload.get("url") or f"https://example.test/{key}"),
            f"hash-{key}",
            f"evidence-{key}",
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
            "2026-09-01T00:00:00Z",
            "2026-09-09T00:00:00Z",
        ),
    )


def _insert_signal(conn, *, signal_id: str, source_id: str, key: str, created_at: str, signal_type: str = "NEW", reason: str | None = None) -> None:  # type: ignore[no-untyped-def]
    payload: dict[str, object] = {"signal_type": signal_type, "canonical_key": key}
    if reason is not None:
        payload["signal_reason"] = reason
    conn.execute(
        "INSERT INTO signals(signal_id,source_id,canonical_key,signal_type,created_at,payload_json) VALUES (?,?,?,?,?,?)",
        (signal_id, source_id, key, signal_type, created_at, json.dumps(payload, sort_keys=True)),
    )


class OpportunityViewTests(unittest.TestCase):
    def test_default_view_is_signal_backed_deduped_and_active_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                _insert_canonical(
                    conn,
                    key="open:1",
                    source_id="S38",
                    payload={
                        "item_kind": "TENDER",
                        "business_stage": "OPPORTUNITY",
                        "title": "Open tender",
                        "reference_no": "OPEN-1",
                        "publication_date": "2026-09-08",
                        "deadline": "2026-09-18",
                        "deadline_time": "16:30",
                        "scope_summary": "Data Server",
                        "url": "https://example.test/open/1",
                    },
                )
                _insert_signal(conn, signal_id="sig-1", source_id="S38", key="open:1", created_at="2026-09-08T10:00:00Z")
                _insert_signal(
                    conn,
                    signal_id="sig-2",
                    source_id="S38",
                    key="open:1",
                    created_at="2026-09-09T01:00:00Z",
                    signal_type="UPDATED",
                    reason="BUSINESS_ENRICHMENT",
                )
                _insert_canonical(
                    conn,
                    key="unknown:1",
                    source_id="S26",
                    payload={
                        "item_kind": "TENDER",
                        "business_stage": "OPPORTUNITY",
                        "title": "Unknown deadline tender",
                        "reference_no": "8DMS/2026-2027(L)",
                        "reference_numbers": ["8DMS/2026-2027(L)", "9DMS/2026-2027(L)", "10DMS/2026-2027(F)"],
                        "reference_count": 3,
                        "reference_numbers_evidence": "HTML_TITLE",
                        "deadline": None,
                        "url": "https://example.test/unknown/1",
                    },
                )
                _insert_signal(conn, signal_id="sig-3", source_id="S26", key="unknown:1", created_at="2026-09-09T02:00:00Z")
                _insert_canonical(
                    conn,
                    key="expired:1",
                    source_id="S25",
                    payload={
                        "item_kind": "TENDER",
                        "business_stage": "OPPORTUNITY",
                        "title": "Expired tender",
                        "reference_no": "EXPIRED-1",
                        "deadline": "2026-09-01",
                        "deadline_time": "16:00",
                        "url": "https://example.test/expired/1",
                    },
                )
                _insert_signal(conn, signal_id="sig-4", source_id="S25", key="expired:1", created_at="2026-09-01T01:00:00Z")
                _insert_canonical(
                    conn,
                    key="silent:1",
                    source_id="S39",
                    payload={
                        "item_kind": "TENDER",
                        "business_stage": "OPPORTUNITY",
                        "title": "Never signaled",
                        "reference_no": "SILENT-1",
                        "deadline": "2026-10-01",
                        "deadline_time": "13:00",
                        "url": "https://example.test/silent/1",
                    },
                )

            result = current_opportunities(database=database, now=datetime(2026, 9, 9, 4, 0, tzinfo=UTC))
            self.assertEqual(result["count"], 2)
            self.assertEqual(result["counts"], {"OPEN": 1, "UNKNOWN": 1, "EXPIRED": 0})
            rows = result["opportunities"]
            assert isinstance(rows, list)
            self.assertEqual([row["canonical_key"] for row in rows], ["open:1", "unknown:1"])
            self.assertEqual(rows[0]["deadline_status"], "OPEN")
            self.assertEqual(rows[0]["deadline_at"], "2026-09-18T16:30:00+06:30")
            self.assertEqual(rows[0]["signal_count"], 2)
            self.assertEqual(rows[0]["latest_signal_type"], "UPDATED")
            self.assertEqual(rows[0]["latest_signal_reason"], "BUSINESS_ENRICHMENT")
            self.assertEqual(rows[1]["deadline_status"], "UNKNOWN")
            self.assertEqual(
                rows[1]["reference_numbers"],
                ["8DMS/2026-2027(L)", "9DMS/2026-2027(L)", "10DMS/2026-2027(F)"],
            )
            self.assertEqual(rows[1]["reference_count"], 3)
            self.assertEqual(rows[1]["reference_numbers_evidence"], "HTML_TITLE")

    def test_include_expired_source_filter_and_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                for index, deadline in enumerate(("2026-09-10", "2026-09-11", "2026-09-01"), start=1):
                    key = f"item:{index}"
                    _insert_canonical(
                        conn,
                        key=key,
                        source_id="S38",
                        payload={
                            "item_kind": "TENDER",
                            "business_stage": "OPPORTUNITY",
                            "title": key,
                            "reference_no": key,
                            "deadline": deadline,
                            "deadline_time": "16:00",
                            "url": f"https://example.test/{key}",
                        },
                    )
                    _insert_signal(conn, signal_id=f"sig-{index}", source_id="S38", key=key, created_at=f"2026-09-0{index}T00:00:00Z")

            result = current_opportunities(
                database=database,
                now=datetime(2026, 9, 9, 4, 0, tzinfo=UTC),
                source_id="S38",
                include_expired=True,
                limit=2,
            )
            self.assertEqual(result["count"], 2)
            self.assertEqual(result["total_matching"], 3)
            self.assertEqual(result["counts"], {"OPEN": 2, "UNKNOWN": 0, "EXPIRED": 1})
            rows = result["opportunities"]
            assert isinstance(rows, list)
            self.assertEqual([row["canonical_key"] for row in rows], ["item:1", "item:2"])

    def test_cli_command_is_read_only_surface_not_worker_verb(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signalforge.db"
            migrate(database)
            with connect(database) as conn, conn:
                _insert_canonical(
                    conn,
                    key="cli:1",
                    source_id="S39",
                    payload={
                        "item_kind": "TENDER",
                        "business_stage": "OPPORTUNITY",
                        "title": "CLI tender",
                        "reference_no": "CLI-1",
                        "deadline": "2026-09-18",
                        "deadline_time": "13:00",
                        "url": "https://example.test/cli/1",
                    },
                )
                _insert_signal(conn, signal_id="cli-sig", source_id="S39", key="cli:1", created_at="2026-09-09T01:00:00Z")

            output = io.StringIO()
            with patch.dict(os.environ, {"SIGNALFORGE_DB": str(database)}), redirect_stdout(output):
                code = main(["opportunities", "--source-id", "S39", "--limit", "5"])
            self.assertEqual(code, 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["opportunities"][0]["canonical_key"], "cli:1")


if __name__ == "__main__":
    unittest.main()
