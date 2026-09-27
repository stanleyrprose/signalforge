# S48 Project Precursor Production Closure — 2026-09-27

## Scope

Close the only remaining rollout item for PR #247: deploy the current `main` release containing S48 `MOI Official Project Precursor News` to Bangkok production and verify that the new precursor path is live without contaminating the existing Tender opportunity surface.

No application code was changed during this closure. The original local feature worktree remained untouched because it still contains uncommitted precursor-development changes; deployment was built from a separate detached worktree at reviewed `origin/main`.

## Release identity

- deployed application release: `0184ce18d7a34aa01596b6bea7a833264800d348`;
- required S48 code revision contained in that release: `1caeac90bfdc6beebe06f68bf1d60aab3e755225`;
- previous Bangkok active release: `95e9161956df2b737c851cbedc78d1eb23f1621b`;
- release archive SHA256, verified equal on Mac and Bangkok before deployment: `15ad6c8cf27d438ddf4f8ca8dfbee7f1198765988d6596cc37ce3c13def75a00`;
- deployment mechanism: `deploy/deploy-signalforge-release.sh`;
- deployment result: `deployment=success`.

The standard deployment script paused/restored the SignalForge timers, staged the immutable release and venv, ran migration/status validation, atomically moved `/srv/signalforge/active`, and retained the prior release as rollback.

## Live S48 baseline

An initial direct `signalforge refresh-source S48` invocation was correctly rejected with `WorkerContextError: missing systemd INVOCATION_ID`. This confirmed that source refresh cannot bypass the Worker/systemd execution contract.

The first production baseline was then run through the intended unit:

`systemctl start signalforge-refresh@S48.service`

The oneshot completed with `Result=success`, `ExecMainCode=0`, and `ExecMainStatus=0`.

Post-baseline S48 state:

- `baseline_complete=1`;
- `consecutive_failures=0`;
- `last_error=null`;
- `last_success_at=2026-09-27T03:23:35.022108Z`;
- `last_snapshot_at=2026-09-27T03:23:35.022108Z`;
- `next_due_at=2026-09-27T03:53:35.022108Z`;
- `sitemap_hash=f4e1547720a802327b789f674e3ca16f1f012e9dd8afcc2c9123de48bce46d33`;
- fetch health GREEN;
- freshness health GREEN;
- source health GREEN;
- recovery backlog 0.

Parse health is `UNKNOWN / PARSE_SAMPLE_INSUFFICIENT` because this zero-candidate first baseline produced zero BUSINESS_PROCESSING samples. This is not a fetch or source failure.

## Business-contract acceptance

`signalforge project-precursors --limit 50`:

- candidates: 0;
- pending review: 0;
- tracked: 0.

`signalforge business-kpis --lead-limit 20`:

- command PASS;
- current business opportunities: 8;
- canonical current opportunities: 6;
- reviewed verified-external current opportunities: 2;
- project precursor candidates: 0;
- tracked projects: 0;
- linked projects: 0;
- lead-time headline remains unmeasured rather than fabricated.

`signalforge opportunities --source-id S48 --include-expired --limit 50`:

- status PASS;
- opportunity count 0;
- total matching 0.

This verifies the intended boundary: S48 can collect review-required upstream precursor candidates, but a precursor baseline does not create Tender opportunities or silently promote lifecycle evidence.

## Runtime acceptance

Active symlink:

`/srv/signalforge/active -> /srv/signalforge/releases/0184ce18d7a34aa01596b6bea7a833264800d348`

All four production timers are enabled and active/waiting:

- `signalforge-run-due.timer`;
- `signalforge-telegram-deliver.timer`;
- `signalforge-telegram-digest.timer`;
- `signalforge-assurance.timer`.

Bangkok does not have the standalone `sqlite3` CLI installed, so the database integrity check was executed read-only with the production Python runtime and stdlib `sqlite3`. `PRAGMA quick_check` returned exactly `ok`.

Global SignalForge remains DEGRADED/RED with the known S21 Myanma Railways origin timeout still RED. S48 itself is GREEN and adds no recovery backlog.

## Closure

S48 Bangkok production rollout is complete.

State transition:

`code DONE -> CI PASS -> main MERGED -> Bangkok DEPLOYED -> first baseline PASS -> live acceptance PASS`

The project-to-procurement lead-time KPI remains intentionally at a zero reviewed sample until a real retained precursor is human-promoted and later linked to an official procurement by reviewed project identity. No historical backfill or fuzzy link was introduced merely to produce a metric.
