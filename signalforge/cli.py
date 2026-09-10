from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from . import VERB_MANIFEST_VERSION
from .auditor import audit
from .briefing import business_briefing
from .config import Registry, SOURCE_ID_PATTERN, db_path
from .db import connect, migrate
from .engine import run_due, run_source
from .mpa import build_manual_bundle_preview, parse_listing_records, parse_pdf_business_fields, preview_summary
from .mpa_manual import commit_manual_provider_bundle
from .opportunities import current_opportunities
from .provider_bridge import build_provider_request, import_provider_result, load_imported_provider_artifact, write_provider_request
from .provider_r3 import prepare_r3_gate, r3_gate_status
from .telegram_delivery import telegram_deliver


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
    return {
        "status": "DEGRADED" if degraded else "PASS",
        "signalforge_health": signalforge_health,
        "canonical_node": registry.raw["production_policy"]["canonical_node"],
        "browser_production_approved": registry.raw["production_policy"]["browser_production_approved"],
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
    telegram_parser = sub.add_parser("telegram-deliver")
    telegram_parser.add_argument("--dry-run", action="store_true")
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
        elif args.cmd == "telegram-deliver":
            result = telegram_deliver(dry_run=bool(args.dry_run))
        else:
            result = status()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
