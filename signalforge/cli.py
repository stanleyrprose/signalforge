from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from . import VERB_MANIFEST_VERSION
from .assurance import (
    assurance_status,
    list_manual_promotions,
    list_missed_signals,
    list_noise_samples,
    record_manual_promotion,
    record_missed_signal,
    resolve_manual_promotion,
    resolve_missed_signal,
    review_noise_sample,
    run_assurance,
)
from .auditor import audit
from .briefing import business_briefing
from .browser_escalation import browser_escalation_candidates
from .business_digest import business_digest, telegram_digest
from .config import Registry, SOURCE_ID_PATTERN, db_path
from .db import connect, migrate
from .engine import run_due, run_source
from .harness import default_checkpoint_path, evaluate_harness, persist_checkpoint
from .jev_shadow import DEFAULT_MODEL as JEV_DEFAULT_MODEL, DEFAULT_THRESHOLD as JEV_DEFAULT_THRESHOLD, jev_shadow_report
from .mpa import build_manual_bundle_preview, parse_listing_records, parse_pdf_business_fields, preview_summary
from .mpa_manual import commit_manual_provider_bundle
from .opportunities import current_opportunities
from .provider_bridge import build_provider_request, import_provider_result, load_imported_provider_artifact, write_provider_request
from .provider_r3 import prepare_r3_gate, r3_gate_status
from .source_scorecard import source_scorecard
from .telegram_delivery import telegram_deliver
from .translation import translation_status


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def verb_manifest() -> dict[str, object]:
    registry = Registry.load()
    return {
        "verb_manifest_version": VERB_MANIFEST_VERSION,
        "provider": "signalforge",
        "verbs": {
            "signalforge-status": {"helper_command": "status", "argument": None},
            "signalforge-opportunities": {"helper_command": "opportunities", "argument": None},
            "signalforge-briefing": {"helper_command": "briefing", "argument": None},
            "signalforge-audit": {"helper_command": "audit", "argument": None},
            "signalforge-source-scorecard": {"helper_command": "source-scorecard", "argument": None},
            "signalforge-assurance-run": {"helper_command": "assurance-run", "argument": None},
            "signalforge-assurance-status": {"helper_command": "assurance-status", "argument": None},
            "signalforge-harness-verify": {"helper_command": "harness-verify", "argument": None},
            "signalforge-misses": {"helper_command": "misses", "argument": None},
            "signalforge-manual-promotions": {"helper_command": "manual-promotions", "argument": None},
            "signalforge-run-due": {"helper_command": "run-due", "argument": None},
            "signalforge-refresh": {"helper_command": "refresh-source", "argument": "source_id"},
            "signalforge-pause": {"helper_command": None, "argument": None},
            "signalforge-resume": {"helper_command": None, "argument": None},
        },
        "grammar": {"source_id": SOURCE_ID_PATTERN.pattern},
        "active_source_ids": [source_id for source_id, _source in registry.enabled_sources()],
    }


def _health_rank(value: str) -> int:
    return {"GREEN": 0, "UNKNOWN": 0, "YELLOW": 1, "RED": 2}.get(value, 2)


def _source_health(conn, source_id: str, source: dict[str, object], policy: dict[str, object], now: datetime) -> dict[str, object]:
    health_policy = policy["health_policy"]
    assert isinstance(health_policy, dict)

    last_success = _parse_iso(source.get("last_success_at") if isinstance(source.get("last_success_at"), str) else None)
    freshness_age = max(0, int((now - last_success).total_seconds())) if last_success else None
    freshness_yellow = int(health_policy["freshness_yellow_seconds"])
    freshness_red = int(health_policy["freshness_red_seconds"])
    if freshness_age is None or freshness_age > freshness_red:
        freshness_health = "RED"
    elif freshness_age > freshness_yellow:
        freshness_health = "YELLOW"
    else:
        freshness_health = "GREEN"

    failures = int(source.get("consecutive_failures") or 0)
    fetch_yellow = int(health_policy["fetch_yellow_failures"])
    fetch_red = int(health_policy["fetch_red_failures"])
    if failures >= fetch_red:
        fetch_health = "RED"
    elif failures >= fetch_yellow or source.get("last_error"):
        fetch_health = "YELLOW"
    else:
        fetch_health = "GREEN"

    pending = conn.execute(
        "SELECT COUNT(*) AS count,MIN(pending_since_at) AS oldest FROM discovery_items WHERE source_id=? AND pending_since_at IS NOT NULL",
        (source_id,),
    ).fetchone()
    backlog = int(pending["count"])
    oldest = pending["oldest"]
    oldest_dt = _parse_iso(oldest)
    oldest_age = max(0, int((now - oldest_dt).total_seconds())) if oldest_dt else 0
    recovery_slo = int(policy.get("recovery_slo_seconds", 1800))
    if backlog == 0:
        recovery_health = "GREEN"
    elif oldest_age <= recovery_slo:
        recovery_health = "YELLOW"
    else:
        recovery_health = "RED"

    parse_window = int(health_policy["parse_window_runs"])
    parse_sample_source = str(health_policy.get("parse_sample_source", "DETAIL_SCHEDULER"))
    if parse_sample_source == "BUSINESS_PROCESSING":
        parse_rows = conn.execute(
            "SELECT status FROM processing_records "
            "WHERE source_id=? AND canonicalizer_version!='none' ORDER BY finished_at DESC LIMIT ?",
            (source_id, parse_window),
        ).fetchall()
        parse_attempts = len(parse_rows)
        parse_successes = sum(1 for row in parse_rows if str(row["status"]) == "SUCCESS")
    else:
        parse_rows = conn.execute(
            "SELECT details_attempted,details_succeeded FROM scheduler_runs "
            "WHERE source_id=? AND details_attempted>0 ORDER BY started_at DESC LIMIT ?",
            (source_id, parse_window),
        ).fetchall()
        parse_attempts = sum(int(row["details_attempted"] or 0) for row in parse_rows)
        parse_successes = sum(int(row["details_succeeded"] or 0) for row in parse_rows)
    parse_min_attempts = int(health_policy["parse_min_attempts"])
    parse_ratio = (parse_successes / parse_attempts) if parse_attempts else None
    if parse_attempts < parse_min_attempts:
        parse_health = "UNKNOWN"
    elif parse_ratio is not None and parse_ratio < float(health_policy["parse_red_ratio"]):
        parse_health = "RED"
    elif parse_ratio is not None and parse_ratio < float(health_policy["parse_yellow_ratio"]):
        parse_health = "YELLOW"
    else:
        parse_health = "GREEN"

    component_states = [fetch_health, freshness_health, parse_health, recovery_health]
    source_health = max(component_states, key=_health_rank)
    if source_health == "UNKNOWN":
        source_health = "GREEN"
    reason_code = "OK"
    for state, code in (
        (fetch_health, "SOURCE_FETCH_FAILURES"),
        (freshness_health, "SOURCE_FRESHNESS_LAG"),
        (parse_health, "SOURCE_PARSE_RATE_LOW"),
        (recovery_health, "SOURCE_RECOVERY_BACKLOG"),
    ):
        if state == source_health and state in {"YELLOW", "RED"}:
            reason_code = code
            break
    if reason_code == "OK" and parse_health == "UNKNOWN":
        reason_code = "PARSE_SAMPLE_INSUFFICIENT"
    return {
        "source_health": source_health,
        "reason_code": reason_code,
        "fetch_health": fetch_health,
        "freshness_health": freshness_health,
        "freshness_age_seconds": freshness_age,
        "freshness_yellow_seconds": freshness_yellow,
        "freshness_red_seconds": freshness_red,
        "parse_health": parse_health,
        "parse_window_runs": parse_window,
        "parse_sample_source": parse_sample_source,
        "parse_attempts": parse_attempts,
        "parse_successes": parse_successes,
        "parse_success_ratio": round(parse_ratio, 4) if parse_ratio is not None else None,
        "parse_min_attempts": parse_min_attempts,
        "parse_yellow_ratio": float(health_policy["parse_yellow_ratio"]),
        "parse_red_ratio": float(health_policy["parse_red_ratio"]),
        "recovery_backlog_health": recovery_health,
        "recovery_backlog": backlog,
        "recovery_oldest_pending_at": oldest,
        "recovery_oldest_age_seconds": oldest_age,
        "recovery_slo_seconds": recovery_slo,
        "availability_class": (policy.get("availability_policy") or {}).get("class") if isinstance(policy.get("availability_policy"), dict) else None,
    }


def status(*, now: datetime | None = None, registry: Registry | None = None) -> dict[str, object]:
    database = db_path()
    migrate(database)
    registry = registry or Registry.load()
    now = (now or datetime.now(UTC)).astimezone(UTC)
    with connect(database) as conn:
        sources: list[dict[str, object]] = []
        for source_id, policy in registry.enabled_sources():
            row = conn.execute("SELECT * FROM source_state WHERE source_id=?", (source_id,)).fetchone()
            source: dict[str, object] = dict(row) if row is not None else {
                "source_id": source_id,
                "baseline_complete": 0,
                "last_success_at": None,
                "last_error": "NOT_INITIALIZED",
                "consecutive_failures": 0,
            }
            source["health"] = _source_health(conn, source_id, source, policy, now)
            sources.append(source)

        counts = {
            "canonical_items": int(conn.execute("SELECT COUNT(*) FROM canonical_items").fetchone()[0]),
            "signals": int(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]),
            "scheduler_runs": int(conn.execute("SELECT COUNT(*) FROM scheduler_runs").fetchone()[0]),
            "failed_runs": int(conn.execute("SELECT COUNT(*) FROM scheduler_runs WHERE status='FAILED'").fetchone()[0]),
            "recovery_backlog": int(conn.execute("SELECT COUNT(*) FROM discovery_items WHERE pending_since_at IS NOT NULL").fetchone()[0]),
            "acquisition_requests": int(conn.execute("SELECT COUNT(*) FROM acquisition_requests").fetchone()[0]),
            "acquisition_attempts": int(conn.execute("SELECT COUNT(*) FROM acquisition_attempts").fetchone()[0]),
            "evidence_envelopes": int(conn.execute("SELECT COUNT(*) FROM evidence_envelopes").fetchone()[0]),
            "processing_records": int(conn.execute("SELECT COUNT(*) FROM processing_records").fetchone()[0]),
        }
        recent = [
            dict(row)
            for row in conn.execute(
                "SELECT app_run_id,source_id,worker_run_id,started_at,finished_at,status,changed,signals_created,baseline,"
                "trigger_kind,recovery,outage_window_start,outage_window_end,backlog_remaining,details_attempted,"
                "details_succeeded,tenders_parsed,items_parsed,error FROM scheduler_runs ORDER BY started_at DESC LIMIT 10"
            )
        ]
    source_states = [str((source.get("health") or {}).get("source_health") or "RED") for source in sources]
    signalforge_health = max(source_states, key=_health_rank) if source_states else "RED"
    degraded = signalforge_health in {"YELLOW", "RED"}
    assurance = assurance_status(database=database)
    return {
        "status": "DEGRADED" if degraded else "PASS",
        "signalforge_health": signalforge_health,
        "canonical_node": registry.raw["production_policy"]["canonical_node"],
        "browser_production_approved": registry.raw["production_policy"]["browser_production_approved"],
        "telegram_translation": translation_status(database=database),
        "assurance": {
            "status": assurance.get("status"),
            "counts": assurance.get("counts"),
            "metric_validity": (assurance.get("latest_metric_review") or {}).get("status") if isinstance(assurance.get("latest_metric_review"), dict) else "NOT_RUN",
        },
        "sources": sources,
        "counts": counts,
        "recent_runs": recent,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="signalforge")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest")
    sub.add_parser("migrate")
    sub.add_parser("run-due")
    run_source_parser = sub.add_parser("run-source")
    run_source_parser.add_argument("source_id")
    run_source_parser.add_argument("--force", action="store_true")
    refresh_source_parser = sub.add_parser("refresh-source")
    refresh_source_parser.add_argument("source_id")
    provider_request_parser = sub.add_parser("provider-request")
    provider_request_parser.add_argument("source_id")
    provider_request_parser.add_argument("--output")
    provider_request_parser.add_argument("--url")
    provider_request_parser.add_argument("--target-role", choices=("LISTING", "DETAIL", "PDF"), default="LISTING")
    provider_import_parser = sub.add_parser("provider-import")
    provider_import_parser.add_argument("--request", required=True)
    provider_import_parser.add_argument("--result", required=True)
    provider_import_parser.add_argument("--artifact")
    provider_import_parser.add_argument("--database")
    provider_import_parser.add_argument("--evidence-root")
    provider_r3_prepare_parser = sub.add_parser("provider-r3-prepare")
    provider_r3_prepare_parser.add_argument("--database")
    provider_r3_prepare_parser.add_argument("--contract")
    provider_r3_status_parser = sub.add_parser("provider-r3-status")
    provider_r3_status_parser.add_argument("gate_id")
    provider_r3_status_parser.add_argument("--database")
    mpa_preview_parser = sub.add_parser("mpa-preview")
    mpa_preview_parser.add_argument("--html", required=True)
    mpa_preview_parser.add_argument("--limit", type=int, default=30)
    mpa_pdf_preview_parser = sub.add_parser("mpa-pdf-preview")
    mpa_pdf_preview_parser.add_argument("--pdf", required=True)
    mpa_bundle_preview_parser = sub.add_parser("mpa-provider-bundle-preview")
    mpa_bundle_preview_parser.add_argument("--listing-provider-request-id", required=True)
    mpa_bundle_preview_parser.add_argument("--detail-provider-request-id", required=True)
    mpa_bundle_preview_parser.add_argument("--pdf-provider-request-id", required=True)
    mpa_bundle_preview_parser.add_argument("--database")
    mpa_bundle_preview_parser.add_argument("--evidence-root")
    mpa_bundle_commit_parser = sub.add_parser("mpa-provider-bundle-commit")
    mpa_bundle_commit_parser.add_argument("--listing-provider-request-id", required=True)
    mpa_bundle_commit_parser.add_argument("--detail-provider-request-id", required=True)
    mpa_bundle_commit_parser.add_argument("--pdf-provider-request-id", required=True)
    mpa_bundle_commit_parser.add_argument("--emit-signal", action="store_true")
    mpa_bundle_commit_parser.add_argument("--database")
    mpa_bundle_commit_parser.add_argument("--evidence-root")
    opportunities_parser = sub.add_parser("opportunities")
    opportunities_parser.add_argument("--source-id")
    opportunities_parser.add_argument("--include-expired", action="store_true")
    opportunities_parser.add_argument("--limit", type=int, default=50)
    sub.add_parser("briefing")
    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("--no-network", action="store_true")
    digest_parser = sub.add_parser("business-digest")
    digest_parser.add_argument("--no-network", action="store_true")
    scorecard_parser = sub.add_parser("source-scorecard")
    scorecard_parser.add_argument("--window-days", type=int, default=30)
    jev_shadow_parser = sub.add_parser("jev-shadow")
    jev_shadow_parser.add_argument("--threshold", type=float, default=JEV_DEFAULT_THRESHOLD)
    jev_shadow_parser.add_argument("--model", default=JEV_DEFAULT_MODEL)
    jev_shadow_parser.add_argument("--limit", type=int, default=50)
    jev_shadow_parser.add_argument("--include-expired", action="store_true")
    browser_escalation_parser = sub.add_parser("browser-escalation-candidates")
    browser_escalation_parser.add_argument("--window-days", type=int, default=7)
    browser_escalation_parser.add_argument("--limit", type=int, default=20)
    assurance_run_parser = sub.add_parser("assurance-run")
    assurance_run_parser.add_argument("--no-network", action="store_true")
    assurance_run_parser.add_argument("--noise-sample-size", type=int, default=5)
    sub.add_parser("assurance-status")
    harness_parser = sub.add_parser("harness-verify")
    harness_parser.add_argument("--checkpoint")
    harness_parser.add_argument("--max-retries", type=int, default=3)
    harness_parser.add_argument("--no-advance-retry", action="store_true")
    misses_parser = sub.add_parser("misses")
    misses_parser.add_argument("--status", choices=("OPEN", "RESOLVED", "FALSE_POSITIVE", "ALL"), default="OPEN")
    misses_parser.add_argument("--limit", type=int, default=100)
    record_miss_parser = sub.add_parser("record-miss")
    record_miss_parser.add_argument("--source-id", required=True)
    record_miss_parser.add_argument("--title", required=True)
    record_miss_parser.add_argument("--reason", required=True)
    record_miss_parser.add_argument("--severity", choices=("RED", "YELLOW"), default="RED")
    record_miss_parser.add_argument("--url")
    record_miss_parser.add_argument("--canonical-key")
    record_miss_parser.add_argument("--detected-by", default="MANUAL")
    resolve_miss_parser = sub.add_parser("resolve-miss")
    resolve_miss_parser.add_argument("miss_id")
    resolve_miss_parser.add_argument("--outcome", choices=("RESOLVED", "FALSE_POSITIVE"), default="RESOLVED")
    resolve_miss_parser.add_argument("--note", required=True)
    resolve_miss_parser.add_argument("--by", default="operator")
    noise_samples_parser = sub.add_parser("noise-samples")
    noise_samples_parser.add_argument("--status", choices=("PENDING", "CONFIRMED_NOISE", "FALSE_NEGATIVE", "INCONCLUSIVE", "ALL"), default="PENDING")
    noise_samples_parser.add_argument("--limit", type=int, default=100)
    noise_review_parser = sub.add_parser("noise-review")
    noise_review_parser.add_argument("noise_sample_id")
    noise_review_parser.add_argument("--outcome", choices=("CONFIRMED_NOISE", "FALSE_NEGATIVE", "INCONCLUSIVE"), required=True)
    noise_review_parser.add_argument("--note", required=True)
    noise_review_parser.add_argument("--by", default="operator")
    noise_review_parser.add_argument("--miss-title")
    manual_promote_parser = sub.add_parser("manual-promote")
    manual_promote_parser.add_argument("--source-id", required=True)
    manual_promote_parser.add_argument("--title", required=True)
    manual_promote_parser.add_argument("--summary", required=True)
    manual_promote_parser.add_argument("--reason", required=True)
    manual_promote_parser.add_argument("--priority", choices=("HIGH", "REVIEW"), default="HIGH")
    manual_promote_parser.add_argument("--url")
    manual_promote_parser.add_argument("--deadline")
    manual_promote_parser.add_argument("--location")
    manual_promote_parser.add_argument("--by", default="operator")
    manual_list_parser = sub.add_parser("manual-promotions")
    manual_list_parser.add_argument("--status", choices=("ACTIVE", "RESOLVED"), default="ACTIVE")
    manual_list_parser.add_argument("--limit", type=int, default=100)
    manual_resolve_parser = sub.add_parser("manual-resolve")
    manual_resolve_parser.add_argument("promotion_id")
    manual_resolve_parser.add_argument("--note", required=True)
    manual_resolve_parser.add_argument("--by", default="operator")
    telegram_parser = sub.add_parser("telegram-deliver")
    telegram_parser.add_argument("--dry-run", action="store_true")
    telegram_digest_parser = sub.add_parser("telegram-digest")
    telegram_digest_parser.add_argument("--dry-run", action="store_true")
    telegram_digest_parser.add_argument("--no-network", action="store_true")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "manifest":
            result: object = verb_manifest()
        elif args.cmd == "migrate":
            migrate()
            result = {"status": "PASS"}
        elif args.cmd == "run-due":
            result = run_due()
        elif args.cmd == "run-source":
            result = run_source(args.source_id, force=args.force)
        elif args.cmd == "refresh-source":
            result = run_source(args.source_id, force=True, trigger_kind_override="MANUAL")
        elif args.cmd == "provider-request":
            if args.output:
                result = write_provider_request(
                    args.source_id,
                    Path(args.output).expanduser(),
                    url=args.url,
                    target_role=args.target_role,
                )
            else:
                result = build_provider_request(args.source_id, url=args.url, target_role=args.target_role)
        elif args.cmd == "provider-import":
            result = import_provider_result(
                request_path=Path(args.request).expanduser(),
                result_path=Path(args.result).expanduser(),
                artifact_path=Path(args.artifact).expanduser() if args.artifact else None,
                database=Path(args.database).expanduser() if args.database else None,
                evidence_directory=Path(args.evidence_root).expanduser() if args.evidence_root else None,
            )
        elif args.cmd == "provider-r3-prepare":
            result = prepare_r3_gate(
                database=Path(args.database).expanduser() if args.database else None,
                contract_path=Path(args.contract).expanduser() if args.contract else None,
            )
        elif args.cmd == "provider-r3-status":
            result = r3_gate_status(
                args.gate_id,
                database=Path(args.database).expanduser() if args.database else None,
            )
        elif args.cmd == "mpa-preview":
            if args.limit < 0:
                raise ValueError("mpa-preview --limit must be >= 0")
            html_path = Path(args.html).expanduser()
            result = preview_summary(parse_listing_records(html_path.read_bytes()))
            records = result["records"]
            assert isinstance(records, list)
            result["records_returned"] = min(args.limit, len(records))
            result["records_truncated"] = len(records) > args.limit
            result["records"] = records[: args.limit]
        elif args.cmd == "mpa-pdf-preview":
            pdf_path = Path(args.pdf).expanduser()
            result = {
                "status": "PREVIEW_ONLY",
                "source_id": "S15A",
                **parse_pdf_business_fields(pdf_path.read_bytes()).payload(),
            }
        elif args.cmd == "mpa-provider-bundle-preview":
            database = Path(args.database).expanduser() if args.database else None
            evidence_directory = Path(args.evidence_root).expanduser() if args.evidence_root else None
            listing = load_imported_provider_artifact(
                args.listing_provider_request_id, database=database, evidence_directory=evidence_directory
            )
            detail = load_imported_provider_artifact(
                args.detail_provider_request_id, database=database, evidence_directory=evidence_directory
            )
            pdf = load_imported_provider_artifact(
                args.pdf_provider_request_id, database=database, evidence_directory=evidence_directory
            )
            if (listing.source_id, detail.source_id, pdf.source_id) != ("S15A", "S15A", "S15A"):
                raise ValueError("MPA provider bundle must contain S15A evidence only")
            if (listing.target_role, detail.target_role, pdf.target_role) != ("LISTING", "DETAIL", "PDF"):
                raise ValueError("MPA provider bundle roles must be LISTING / DETAIL / PDF")
            result = build_manual_bundle_preview(
                listing.payload,
                detail.payload,
                pdf.payload,
                detail_url=detail.requested_url,
                pdf_url=pdf.requested_url,
            )
            result["provider_evidence"] = {
                "listing": {"provider_request_id": listing.provider_request_id, "evidence_id": listing.evidence_id, "sha256": listing.sha256},
                "detail": {"provider_request_id": detail.provider_request_id, "evidence_id": detail.evidence_id, "sha256": detail.sha256},
                "pdf": {"provider_request_id": pdf.provider_request_id, "evidence_id": pdf.evidence_id, "sha256": pdf.sha256},
            }
        elif args.cmd == "mpa-provider-bundle-commit":
            result = commit_manual_provider_bundle(
                listing_provider_request_id=args.listing_provider_request_id,
                detail_provider_request_id=args.detail_provider_request_id,
                pdf_provider_request_id=args.pdf_provider_request_id,
                emit_signal=bool(args.emit_signal),
                database=Path(args.database).expanduser() if args.database else None,
                evidence_directory=Path(args.evidence_root).expanduser() if args.evidence_root else None,
            )
        elif args.cmd == "opportunities":
            if args.source_id is not None and not SOURCE_ID_PATTERN.fullmatch(args.source_id):
                raise ValueError("invalid source id")
            result = current_opportunities(
                source_id=args.source_id,
                include_expired=bool(args.include_expired),
                limit=int(args.limit),
            )
        elif args.cmd == "briefing":
            result = business_briefing()
        elif args.cmd == "audit":
            result = audit(network=not bool(args.no_network))
        elif args.cmd == "business-digest":
            result = business_digest(audit_network=not bool(args.no_network))
        elif args.cmd == "source-scorecard":
            result = source_scorecard(window_days=int(args.window_days))
        elif args.cmd == "jev-shadow":
            result = jev_shadow_report(
                threshold=float(args.threshold),
                model=str(args.model),
                limit=int(args.limit),
                include_expired=bool(args.include_expired),
            )
        elif args.cmd == "browser-escalation-candidates":
            result = browser_escalation_candidates(window_days=int(args.window_days), limit=int(args.limit))
        elif args.cmd == "assurance-run":
            result = run_assurance(network=not bool(args.no_network), noise_sample_size=int(args.noise_sample_size))
        elif args.cmd == "assurance-status":
            result = assurance_status()
        elif args.cmd == "harness-verify":
            database = db_path()
            registry = Registry.load()
            migrate(database)
            with connect(database) as conn:
                db_quick_check = str(conn.execute("PRAGMA quick_check").fetchone()[0])
            report = evaluate_harness(
                status_snapshot=status(registry=registry),
                assurance=assurance_status(database=database, registry=registry),
                briefing=business_briefing(database=database, registry=registry),
                telegram_dry_run=telegram_deliver(database=database, dry_run=True),
                db_quick_check=db_quick_check,
            )
            checkpoint = Path(args.checkpoint).expanduser() if args.checkpoint else default_checkpoint_path(database)
            result = persist_checkpoint(
                report,
                path=checkpoint,
                max_retries=int(args.max_retries),
                advance_retry=not bool(args.no_advance_retry),
            )
        elif args.cmd == "misses":
            result = list_missed_signals(status=None if args.status == "ALL" else args.status, limit=int(args.limit))
        elif args.cmd == "record-miss":
            result = record_missed_signal(
                source_id=args.source_id,
                title=args.title,
                reason=args.reason,
                severity=args.severity,
                detected_by=args.detected_by,
                url=args.url,
                canonical_key=args.canonical_key,
            )
        elif args.cmd == "resolve-miss":
            result = resolve_missed_signal(args.miss_id, outcome=args.outcome, note=args.note, resolved_by=args.by)
        elif args.cmd == "noise-samples":
            result = list_noise_samples(status=None if args.status == "ALL" else args.status, limit=int(args.limit))
        elif args.cmd == "noise-review":
            result = review_noise_sample(
                args.noise_sample_id,
                outcome=args.outcome,
                note=args.note,
                reviewed_by=args.by,
                miss_title=args.miss_title,
            )
        elif args.cmd == "manual-promote":
            result = record_manual_promotion(
                source_id=args.source_id,
                title=args.title,
                summary=args.summary,
                reason=args.reason,
                priority_band=args.priority,
                url=args.url,
                deadline=args.deadline,
                location=args.location,
                created_by=args.by,
            )
        elif args.cmd == "manual-promotions":
            result = list_manual_promotions(status=args.status, limit=int(args.limit))
        elif args.cmd == "manual-resolve":
            result = resolve_manual_promotion(args.promotion_id, note=args.note, resolved_by=args.by)
        elif args.cmd == "telegram-deliver":
            result = telegram_deliver(dry_run=bool(args.dry_run))
        elif args.cmd == "telegram-digest":
            result = telegram_digest(dry_run=bool(args.dry_run), audit_network=not bool(args.no_network))
        else:
            result = status()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if args.cmd == "harness-verify" and isinstance(result, dict) and result.get("phase") != "DONE":
            return 2
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
