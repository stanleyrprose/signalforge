"""Promote only independently reviewed issuer-authored S01 images with complete facts.

OCR triage is evidence for review, never an authorizer of a canonical tender.
The production review manifest is the explicit human-approved fact SOT.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .config import repo_root
from .db import connect
from .engine import _upsert_tender

_SHA = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST = "S01-Reviewed-Issuer-Images-v1.json"


@dataclass(frozen=True)
class S01ReviewedImageTender:
    url: str
    issuer: str
    title: str
    scope_summary: str
    quantity_or_lot_summary: str
    deadline: str
    source_image_sha256: str
    reviewed_at: str

    item_kind = "TENDER"
    reference_no = None
    publication_date = None
    location = None

    @property
    def canonical_key(self) -> str:
        return "national-portal-document:" + hashlib.sha256(self.url.encode()).hexdigest()[:24]

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": "TENDER", "issuer": self.issuer, "title": self.title,
            "project_name": self.project_name, "scope_summary": self.scope_summary,
            "quantity_or_lot_summary": self.quantity_or_lot_summary,
            "quantity_disclosure_status": "HUMAN_VERIFIED_EXPLICIT",
            "deadline": self.deadline, "deadline_kind": "BID_SUBMISSION_DEADLINE",
            "deadline_evidence": "HUMAN_REVIEWED_OFFICIAL_IMAGE_DEADLINE",
            "document_authority": "ISSUER_IMAGE_VIA_NATIONAL_PORTAL_HUMAN_REVIEWED",
            "source_document_sha256": self.source_image_sha256,
            "reviewed_at": self.reviewed_at, "url": self.url,
        }


def _review_manifest(root: Path) -> dict[str, dict[str, object]]:
    raw = json.loads((root / "registry" / _MANIFEST).read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1 or not isinstance(raw.get("records"), dict):
        raise ValueError("invalid S01 reviewed-image manifest schema")
    records = raw["records"]
    for digest, record in records.items():
        if not _SHA.fullmatch(digest) or not isinstance(record, dict):
            raise ValueError("invalid S01 reviewed-image record identity")
        if record.get("review_status") != "HUMAN_APPROVED_SOURCE_IMAGE":
            raise ValueError("S01 official-image promotion requires human approval")
        if not isinstance(record.get("formal_procurement_tender"), bool):
            raise ValueError("S01 reviewed procurement disposition missing")
    return records


def promote_reviewed_s01_images(
    database: Path, *, root: Path | None = None, now: datetime | None = None,
) -> dict[str, int]:
    """Idempotent, manifest-and-live-image-hash-bound canonical promotion.

    A human-reviewed image may be retained without qualifying as an eligible
    formal procurement. The exact submission deadline must be verified, and
    document-sale and tender-opening dates are never substituted for it.
    """
    records = _review_manifest(root or repo_root())
    clock = (now or datetime.now(UTC)).astimezone(UTC)
    yangon_today = clock.astimezone(ZoneInfo("Asia/Yangon")).date()
    outcome = {
        "reviewed": 0, "eligible": 0, "promoted": 0, "signals_created": 0,
        "excluded_nonprocurement": 0, "blocked_missing_bid_deadline": 0,
        "blocked_missing_facts": 0, "blocked_no_evidence_match": 0,
        "blocked_duplicate_image": 0,
    }
    seen_digests: set[str] = set()
    with connect(database) as conn, conn:
        try:
            approved = conn.execute(
                "SELECT url,review_status,ocr_input_sha256 FROM s01_image_review "
                "WHERE review_status='HUMAN_APPROVED' ORDER BY url"
            ).fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc):
                raise
            approved = []
        for item in approved:
            outcome["reviewed"] += 1
            url = str(item["url"])
            parsed = urlparse(url)
            digest = str(item["ocr_input_sha256"] or "")
            if (
                not _SHA.fullmatch(digest)
                or parsed.scheme != "https"
                or parsed.hostname != "myanmar.gov.mm"
                or not parsed.path.startswith("/documents/")
                or not re.search(r"\.jpe?g(?:/|$)", parsed.path, re.I)
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443)
                or parsed.query or parsed.fragment
                or digest not in records
            ):
                outcome["blocked_no_evidence_match"] += 1
                continue
            if digest in seen_digests:
                outcome["blocked_duplicate_image"] += 1
                continue
            seen_digests.add(digest)
            entry = records[digest]
            if entry["formal_procurement_tender"] is False:
                outcome["excluded_nonprocurement"] += 1
                continue
            deadline = entry.get("bid_submission_deadline")
            if not isinstance(deadline, str) or not deadline:
                outcome["blocked_missing_bid_deadline"] += 1
                continue
            try:
                verified_day = date.fromisoformat(deadline)
                review_day = date.fromisoformat(str(entry.get("reviewed_at") or ""))
            except ValueError:
                outcome["blocked_missing_facts"] += 1
                continue
            issuer, scope, quantity = (
                entry.get("issuer"), entry.get("scope_summary"),
                entry.get("quantity_or_lot_summary"),
            )
            if (
                entry.get("bid_submission_deadline_evidence") != "HUMAN_REVIEWED_OFFICIAL_IMAGE_DEADLINE"
                or not all(isinstance(v, str) and v.strip() for v in (issuer, scope, quantity))
            ):
                outcome["blocked_missing_facts"] += 1
                continue
            outcome["eligible"] += 1
            owner = conn.execute(
                "SELECT source_id FROM canonical_items WHERE evidence_sha256=? LIMIT 1",
                (digest,),
            ).fetchone()
            if owner is not None:
                # The exact issuer image was already canonicalized. Do not create
                # a second tender when the portal document URL changes.
                outcome["blocked_duplicate_image"] += 1
                continue
            tender = S01ReviewedImageTender(
                url=url, issuer=str(issuer).strip(),
                title=str(entry.get("title") or scope).strip(),
                scope_summary=str(scope).strip(),
                quantity_or_lot_summary=str(quantity).strip(),
                deadline=deadline, source_image_sha256=digest,
                reviewed_at=review_day.isoformat(),
            )
            existing = conn.execute(
                "SELECT 1 FROM canonical_items WHERE canonical_key=?",
                (tender.canonical_key,),
            ).fetchone()
            # Never produce a NEW signal for an already-expired historical review.
            changed, signals = _upsert_tender(
                conn, source_id="S01", tender=tender,
                observed_at=clock.isoformat(), evidence_digest=digest,
                suppress_signal=(verified_day < yangon_today),
            )
            if changed and existing is None:
                outcome["promoted"] += 1
            outcome["signals_created"] += signals
    return outcome
