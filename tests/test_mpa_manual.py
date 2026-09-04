from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from signalforge.cli import verb_manifest
from signalforge.config import Registry
from signalforge.db import connect
from signalforge.mpa import MpaPdfFields
from signalforge.mpa_manual import MpaManualCommitError, commit_manual_provider_bundle
from signalforge.provider_bridge import build_provider_request, import_provider_result


ROOT = Path(__file__).resolve().parents[1]
DETAIL_URL = "https://www.mpa.gov.mm/announcements/open-tender-invitation-for-three-tugs-2/"
PDF_URL = "https://www.mpa.gov.mm/wp-content/uploads/2026/06/Three-Tug-Tender-Eng.pdf"
LISTING = f"""
<html><body><table><tbody>
<tr><td class="text-center">02/06/2026</td><td class="ps-4"><a href="{DETAIL_URL}">Open Tender Invitation for three Tugs</a></td></tr>
</tbody></table></body></html>
""".encode("utf-8")
DETAIL = f"""<html><head><link rel='shortlink' href='https://www.mpa.gov.mm/?p=37867' /></head>
<body><iframe data-src='{PDF_URL}'></iframe></body></html>""".encode("utf-8")


def _fields(*, deadline: str = "2026-06-25T13:00:00", scope: str = "auctioned through an open tender system") -> MpaPdfFields:
    return MpaPdfFields(
        final_item_kind="AUCTION_NOTICE",
        classification_status="DETERMINISTIC_PDF",
        classification_basis="AUCTION_EN",
        deadline_local=deadline,
        deadline_timezone="Asia/Yangon",
        deadline_status="FOUND",
        reference_no=None,
        scope_excerpt=scope,
        page_count=2,
        text_chars=1941,
    )


class MpaManualCommitTests(unittest.TestCase):
    def _import_artifact(
        self,
        *,
        root: Path,
        registry: Registry,
        role: str,
        payload: bytes,
        content_type: str,
        url: str | None = None,
        label: str,
    ) -> str:
        request = build_provider_request(
            "S15A",
            registry=registry,
            requested_at="2026-09-05T00:00:00Z",
            url=url,
            target_role=role,
        )
        provider_request_id = str(request["_provider_request"]["provider_request_id"])
        request_path = root / f"{label}-request.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        suffix = ".pdf" if role == "PDF" else ".html"
        artifact_path = root / f"{label}-response{suffix}"
        artifact_path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        result_path = root / f"{label}-result.json"
        result_path.write_text(
            json.dumps(
                {
                    "job_id": f"browser-{label}",
                    "state": "SUCCEEDED",
                    "started_at": "2026-09-05T00:00:01Z",
                    "finished_at": "2026-09-05T00:00:02Z",
                    "result": {
                        "engine": "c0-fetch",
                        "url": request["url"],
                        "status": 200,
                        "content_type": content_type,
                        "body_bytes": len(payload),
                        "artifact_path": str(artifact_path),
                        "sha256": digest,
                    },
                }
            ),
            encoding="utf-8",
        )
        imported = import_provider_result(
            request_path=request_path,
            result_path=result_path,
            database=root / "state" / "signalforge.db",
            evidence_directory=root / "evidence",
            registry=registry,
        )
        self.assertEqual(imported["status"], "IMPORTED_EVIDENCE_ONLY")
        return provider_request_id

    def _bundle(self, root: Path, registry: Registry, *, pdf_payload: bytes = b"%PDF-manual-one") -> tuple[str, str, str]:
        listing = self._import_artifact(
            root=root,
            registry=registry,
            role="LISTING",
            payload=LISTING,
            content_type="text/html",
            label="listing",
        )
        detail = self._import_artifact(
            root=root,
            registry=registry,
            role="DETAIL",
            payload=DETAIL,
            content_type="text/html",
            url=DETAIL_URL,
            label="detail",
        )
        pdf = self._import_artifact(
            root=root,
            registry=registry,
            role="PDF",
            payload=pdf_payload,
            content_type="application/pdf",
            url=PDF_URL,
            label="pdf-one",
        )
        return listing, detail, pdf

    def test_manual_commit_creates_canonical_without_signal_and_is_idempotent(self) -> None:
        registry = Registry.load(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            listing, detail, pdf = self._bundle(root, registry)
            with patch("signalforge.mpa.parse_pdf_business_fields", return_value=_fields()):
                result = commit_manual_provider_bundle(
                    listing_provider_request_id=listing,
                    detail_provider_request_id=detail,
                    pdf_provider_request_id=pdf,
                    database=root / "state" / "signalforge.db",
                    evidence_directory=root / "evidence",
                    registry=registry,
                    now=datetime(2026, 9, 5, 1, 0, tzinfo=UTC),
                )
                again = commit_manual_provider_bundle(
                    listing_provider_request_id=listing,
                    detail_provider_request_id=detail,
                    pdf_provider_request_id=pdf,
                    database=root / "state" / "signalforge.db",
                    evidence_directory=root / "evidence",
                    registry=registry,
                    now=datetime(2026, 9, 5, 1, 1, tzinfo=UTC),
                )
            self.assertEqual(result["status"], "COMMITTED")
            self.assertEqual(result["action"], "CREATED")
            self.assertEqual(result["canonical_key"], "mpa:37867")
            self.assertEqual(result["item_kind"], "AUCTION_NOTICE")
            self.assertEqual(result["signals_created"], 0)
            self.assertEqual(again["status"], "ALREADY_COMMITTED")
            with connect(root / "state" / "signalforge.db") as conn:
                row = conn.execute(
                    "SELECT source_id,item_kind,deadline,evidence_sha256 FROM canonical_items WHERE canonical_key='mpa:37867'"
                ).fetchone()
                self.assertEqual(row["source_id"], "S15A")
                self.assertEqual(row["item_kind"], "AUCTION_NOTICE")
                self.assertEqual(row["deadline"], "2026-06-25T13:00:00+06:30")
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S15A'").fetchone()[0], 0)
                self.assertEqual(
                    conn.execute(
                        "SELECT COUNT(*) FROM processing_records WHERE source_id='S15A' AND canonicalizer_version='mpa-manual-v1'"
                    ).fetchone()[0],
                    1,
                )

    def test_new_pdf_evidence_can_emit_updated_signal_only_when_explicit(self) -> None:
        registry = Registry.load(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            listing, detail, pdf_one = self._bundle(root, registry)
            with patch("signalforge.mpa.parse_pdf_business_fields", return_value=_fields()):
                commit_manual_provider_bundle(
                    listing_provider_request_id=listing,
                    detail_provider_request_id=detail,
                    pdf_provider_request_id=pdf_one,
                    database=root / "state" / "signalforge.db",
                    evidence_directory=root / "evidence",
                    registry=registry,
                )
            pdf_two = self._import_artifact(
                root=root,
                registry=registry,
                role="PDF",
                payload=b"%PDF-manual-two-changed",
                content_type="application/pdf",
                url=PDF_URL,
                label="pdf-two",
            )
            with patch(
                "signalforge.mpa.parse_pdf_business_fields",
                return_value=_fields(deadline="2026-06-26T13:00:00", scope="auctioned through an updated open tender system"),
            ):
                result = commit_manual_provider_bundle(
                    listing_provider_request_id=listing,
                    detail_provider_request_id=detail,
                    pdf_provider_request_id=pdf_two,
                    emit_signal=True,
                    database=root / "state" / "signalforge.db",
                    evidence_directory=root / "evidence",
                    registry=registry,
                )
            self.assertEqual(result["action"], "UPDATED")
            self.assertEqual(result["signals_created"], 1)
            self.assertEqual(result["signal_type"], "UPDATED")
            with connect(root / "state" / "signalforge.db") as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals WHERE source_id='S15A'").fetchone()[0], 1)

    def test_review_required_bundle_cannot_commit(self) -> None:
        registry = Registry.load(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            listing, detail, pdf = self._bundle(root, registry)
            review = MpaPdfFields(
                final_item_kind=None,
                classification_status="REVIEW_REQUIRED",
                classification_basis=None,
                deadline_local=None,
                deadline_timezone="Asia/Yangon",
                deadline_status="NOT_FOUND",
                reference_no=None,
                scope_excerpt=None,
                page_count=1,
                text_chars=300,
            )
            with patch("signalforge.mpa.parse_pdf_business_fields", return_value=review):
                with self.assertRaisesRegex(MpaManualCommitError, "not READY_FOR_MANUAL_COMMIT"):
                    commit_manual_provider_bundle(
                        listing_provider_request_id=listing,
                        detail_provider_request_id=detail,
                        pdf_provider_request_id=pdf,
                        database=root / "state" / "signalforge.db",
                        evidence_directory=root / "evidence",
                        registry=registry,
                    )
            with connect(root / "state" / "signalforge.db") as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_items").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0], 0)

    def test_manual_commit_command_is_not_worker_verb(self) -> None:
        verbs = verb_manifest()["verbs"]
        self.assertNotIn("mpa-provider-bundle-commit", verbs)
        self.assertNotIn("signalforge-mpa-provider-bundle-commit", verbs)


if __name__ == "__main__":
    unittest.main()
