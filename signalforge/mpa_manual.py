from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .acquisition_contract import ACQUISITION_SCHEMA_VERSION
from .config import Registry, db_path, evidence_root
from .db import connect, migrate
from .engine import _upsert_tender
from .mpa import build_manual_bundle_preview
from .provider_bridge import load_imported_provider_artifact


PARSER_VERSION = "mpa-pdf-v1"
NORMALIZER_VERSION = "mpa-manual-v1"
CANONICALIZER_VERSION = "mpa-manual-v1"


class MpaManualCommitError(RuntimeError):
    pass


@dataclass(frozen=True)
class MpaManualCanonicalItem:
    canonical_key: str
    item_kind: str
    title: str
    reference_no: str
    project_name: str
    publication_date: str | None
    deadline: str | None
    location: str | None
    url: str
    pdf_url: str
    source_record_id: str
    scope_excerpt: str | None
    classification_status: str
    classification_basis: str | None
    deadline_status: str
    listing_provisional_item_kind: str

    def payload(self) -> dict[str, object]:
        return {
            "issuer": "Myanma Port Authority",
            "item_kind": self.item_kind,
            "reference_no": self.reference_no,
            "project_name": self.project_name,
            "publication_date": self.publication_date,
            "deadline": self.deadline,
            "location": self.location,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "source_record_id": self.source_record_id,
            "scope_excerpt": self.scope_excerpt,
            "classification_status": self.classification_status,
            "classification_basis": self.classification_basis,
            "deadline_status": self.deadline_status,
            "listing_provisional_item_kind": self.listing_provisional_item_kind,
        }


def _observed_at(value: datetime | None) -> str:
    current = value or datetime.now(UTC)
    return current.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _item_from_candidate(candidate: dict[str, object]) -> MpaManualCanonicalItem:
    required = (
        "canonical_key",
        "item_kind",
        "title",
        "reference_no",
        "project_name",
        "url",
        "pdf_url",
        "source_record_id",
        "classification_status",
        "deadline_status",
        "listing_provisional_item_kind",
    )
    for key in required:
        if not isinstance(candidate.get(key), str) or not str(candidate[key]).strip():
            raise MpaManualCommitError(f"MPA manual candidate missing required field: {key}")
    item_kind = str(candidate["item_kind"])
    if item_kind not in {"TENDER", "AUCTION_NOTICE"}:
        raise MpaManualCommitError(f"MPA manual candidate has unsupported item_kind: {item_kind}")
    return MpaManualCanonicalItem(
        canonical_key=str(candidate["canonical_key"]),
        item_kind=item_kind,
        title=str(candidate["title"]),
        reference_no=str(candidate["reference_no"]),
        project_name=str(candidate["project_name"]),
        publication_date=str(candidate["publication_date"]) if candidate.get("publication_date") is not None else None,
        deadline=str(candidate["deadline"]) if candidate.get("deadline") is not None else None,
        location=str(candidate["location"]) if candidate.get("location") is not None else None,
        url=str(candidate["url"]),
        pdf_url=str(candidate["pdf_url"]),
        source_record_id=str(candidate["source_record_id"]),
        scope_excerpt=str(candidate["scope_excerpt"]) if candidate.get("scope_excerpt") is not None else None,
        classification_status=str(candidate["classification_status"]),
        classification_basis=str(candidate["classification_basis"]) if candidate.get("classification_basis") is not None else None,
        deadline_status=str(candidate["deadline_status"]),
        listing_provisional_item_kind=str(candidate["listing_provisional_item_kind"]),
    )


def commit_manual_provider_bundle(
    *,
    listing_provider_request_id: str,
    detail_provider_request_id: str,
    pdf_provider_request_id: str,
    emit_signal: bool = False,
    database: Path | None = None,
    evidence_directory: Path | None = None,
    registry: Registry | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    registry = registry or Registry.load()
    target_database = database or db_path()
    target_evidence_root = evidence_directory or evidence_root()

    listing = load_imported_provider_artifact(
        listing_provider_request_id,
        database=target_database,
        evidence_directory=target_evidence_root,
        registry=registry,
    )
    detail = load_imported_provider_artifact(
        detail_provider_request_id,
        database=target_database,
        evidence_directory=target_evidence_root,
        registry=registry,
    )
    pdf = load_imported_provider_artifact(
        pdf_provider_request_id,
        database=target_database,
        evidence_directory=target_evidence_root,
        registry=registry,
    )
    if (listing.source_id, detail.source_id, pdf.source_id) != ("S15A", "S15A", "S15A"):
        raise MpaManualCommitError("MPA manual commit requires S15A provider evidence only")
    if (listing.target_role, detail.target_role, pdf.target_role) != ("LISTING", "DETAIL", "PDF"):
        raise MpaManualCommitError("MPA manual commit roles must be LISTING / DETAIL / PDF")

    preview = build_manual_bundle_preview(
        listing.payload,
        detail.payload,
        pdf.payload,
        detail_url=detail.requested_url,
        pdf_url=pdf.requested_url,
    )
    if preview.get("status") != "READY_FOR_MANUAL_COMMIT":
        raise MpaManualCommitError("MPA provider bundle is not READY_FOR_MANUAL_COMMIT")
    candidate = preview.get("candidate")
    if not isinstance(candidate, dict):
        raise MpaManualCommitError("MPA provider bundle candidate missing")
    item = _item_from_candidate(candidate)

    migrate(target_database)
    observed_at = _observed_at(now)
    processing_id = str(uuid.uuid4())
    with connect(target_database) as conn, conn:
        prior_processing = conn.execute(
            """
            SELECT processing_id FROM processing_records
            WHERE evidence_id=? AND canonicalizer_version=? AND status='SUCCESS'
            ORDER BY rowid DESC LIMIT 1
            """,
            (pdf.evidence_id, CANONICALIZER_VERSION),
        ).fetchone()
        if prior_processing is not None:
            return {
                "status": "ALREADY_COMMITTED",
                "source_id": "S15A",
                "canonical_key": item.canonical_key,
                "processing_id": str(prior_processing["processing_id"]),
                "pdf_provider_request_id": pdf.provider_request_id,
                "emit_signal": False,
            }

        evidence_row = conn.execute(
            "SELECT request_id,attempt_id,artifact_sha256 FROM evidence_envelopes WHERE evidence_id=? AND source_id='S15A'",
            (pdf.evidence_id,),
        ).fetchone()
        if evidence_row is None:
            raise MpaManualCommitError("MPA PDF evidence correlation missing")
        if str(evidence_row["request_id"]) != pdf.acquisition_request_id:
            raise MpaManualCommitError("MPA PDF acquisition request correlation mismatch")
        if str(evidence_row["artifact_sha256"]) != pdf.sha256:
            raise MpaManualCommitError("MPA PDF evidence digest mismatch")

        prior = conn.execute(
            "SELECT content_hash FROM canonical_items WHERE canonical_key=?",
            (item.canonical_key,),
        ).fetchone()
        changed, signal_count = _upsert_tender(
            conn,
            source_id="S15A",
            tender=item,
            observed_at=observed_at,
            suppress_signal=not emit_signal,
            evidence_digest=pdf.sha256,
        )
        action = "CREATED" if prior is None else ("UPDATED" if changed else "UNCHANGED")
        signal_type = None
        if signal_count:
            signal_type = "NEW" if prior is None else "UPDATED"

        conn.execute(
            """
            INSERT INTO processing_records(
                processing_id,schema_version,evidence_id,request_id,attempt_id,source_id,parser_version,normalizer_version,
                canonicalizer_version,started_at,finished_at,status,processing_failure_class,items_found,canonical_items,signals_created
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                processing_id,
                ACQUISITION_SCHEMA_VERSION,
                pdf.evidence_id,
                str(evidence_row["request_id"]),
                str(evidence_row["attempt_id"]),
                "S15A",
                PARSER_VERSION,
                NORMALIZER_VERSION,
                CANONICALIZER_VERSION,
                observed_at,
                observed_at,
                "SUCCESS",
                None,
                1,
                1,
                signal_count,
            ),
        )

    return {
        "status": "COMMITTED",
        "source_id": "S15A",
        "canonical_key": item.canonical_key,
        "item_kind": item.item_kind,
        "action": action,
        "changed": changed,
        "emit_signal": emit_signal,
        "signals_created": signal_count,
        "signal_type": signal_type,
        "processing_id": processing_id,
        "listing_provider_request_id": listing.provider_request_id,
        "detail_provider_request_id": detail.provider_request_id,
        "pdf_provider_request_id": pdf.provider_request_id,
        "evidence_sha256": pdf.sha256,
    }
