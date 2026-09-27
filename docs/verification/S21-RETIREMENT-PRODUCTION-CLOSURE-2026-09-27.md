# S21 Myanma Railways Retirement Production Closure — 2026-09-27

## Decision

S21 Myanma Railways is retired from active SignalForge production rather than physically deleted.

The reason is persistent issuer-origin connect timeout with no current reliable official replacement acquisition surface. The retirement removes an operationally dead source from active health, scheduling and mandatory coverage accounting while preserving historical provenance and the adapter/parser recovery path.

## Code and CI

- PR: #251 `feat: retire unavailable S21 railway source`;
- merged main SHA: `032798f2723dc3dc97946164b56993a6a0df3b58`;
- GitHub Actions `verify`: PASS;
- targeted contract / source-scorecard / Assurance tests: `35 passed`;
- full unittest suite: `504 passed`;
- Python compileall: PASS;
- `git diff --check`: PASS.

Production contract:

- registry `enabled=false`;
- role `RETIRED_UNAVAILABLE`;
- `acquisition_policy.enabled=false`;
- removed from active source manifest;
- removed from source-scorecard CORE accounting;
- removed from `MANDATORY_COVERAGE_SOURCES`;
- historical adapter and parser tests retained through an explicit isolated active test fixture;
- reactivation gate: `OFFICIAL_ORIGIN_RECOVERY_OR_REVIEWED_REPLACEMENT_SURFACE`.

## Pre-deploy production state

Active Bangkok release:

`0184ce18d7a34aa01596b6bea7a833264800d348`

Live status immediately before retirement deployment:

- active sources: `33`;
- SignalForge status: `DEGRADED`;
- SignalForge health: `RED`;
- S21 consecutive failures: `986`;
- S21 last success: `2026-09-13T13:00:46.633907Z`;
- S21 last error: issuer-origin fetch timeout;
- S21 source health: RED.

This established that S21 was actively degrading the production health surface rather than merely carrying historical failure metadata.

## Deployment

New Bangkok release:

`032798f2723dc3dc97946164b56993a6a0df3b58`

Release archive SHA256, verified equal on Mac and Bangkok:

`2a663ee46df177e189c467dd3c50a17385f6b094a92b6634fb1f120bd9490161`

Deployment used the standard `deploy/deploy-signalforge-release.sh` path and returned `deployment=success`. The previous release remains available as rollback.

## Post-deploy active-source acceptance

Live manifest:

- active source count: `32`;
- S21 active: false.

Live `signalforge status`:

- status: `PASS`;
- health: `GREEN`;
- active sources: `32`;
- S21 present: false;
- recovery backlog: `0`.

Live source-scorecard:

- active sources: `32`;
- health GREEN: `32`;
- S21 present: false;
- portfolio CORE sources: `5`;
- current business opportunities: `8`;
- current canonical opportunities: `6`;
- verified-external opportunities: `2`.

The retirement therefore removes the known dead source from operational health without removing current business opportunities.

## Assurance acceptance

A fresh production `signalforge-assurance.service` run completed with `Result=success / ExecMainStatus=0`.

Mandatory coverage after retirement:

- mandatory coverage total: `6`;
- direct PASS: `5`;
- S13 PARTIAL with reviewed-external recovery: `1`;
- mandatory check-failed sources: `[]`;
- mandatory business coverage accounted: `6`;
- mandatory business coverage accounted rate: `1.0`;
- mandatory coverage proof rate: `0.8333`.

Assurance overall status remains `REVIEW`, correctly, because remaining non-S21 discovery/detail risks are still reported. S21 is no longer represented as a current mandatory coverage failure.

## Scheduler and historical-data acceptance

A production `signalforge-run-due.service` execution completed successfully after deployment.

SQLite verification:

- `PRAGMA quick_check = ok`;
- S21 canonical items retained: `45`;
- S21 Signals retained: `4`;
- S21 source_state retained;
- retained consecutive failure count: `986`;
- retained last success: `2026-09-13T13:00:46.633907Z`;
- latest S21 scheduler run: `2026-09-27T08:10:20.385173Z / FAILED / POLL`.

That latest S21 run predates the retirement deployment. No new S21 scheduler run was created by the post-deploy run-due execution, confirming that retired S21 is no longer polled.

All four production timers remain enabled and active/waiting:

- `signalforge-run-due.timer`;
- `signalforge-telegram-deliver.timer`;
- `signalforge-telegram-digest.timer`;
- `signalforge-assurance.timer`.

## Boundary

Retirement means the current Railways official origin is not a reliable production acquisition surface. It does **not** mean that Myanma Railways has no current procurement opportunities.

Historical S21 data and code remain available for audit and future recovery. Reactivation requires either:

1. reliable recovery of the official Railways origin; or
2. a separately reviewed reliable official replacement surface.

No insecure TLS bypass, unofficial mirror, fuzzy reconstruction, historical deletion, or fabricated coverage claim was introduced.

## Closure

State transition:

`S21 ACTIVE / RED -> RETIRED / DISABLED`

Operational result:

`SignalForge DEGRADED / RED -> PASS / GREEN`

with S21 historical evidence retained and active business opportunity output unchanged.
