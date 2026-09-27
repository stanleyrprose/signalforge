# S48 Pre-Procurement Precursor v2 Production Closure — 2026-09-27

## Goal

Improve SignalForge's ability to discover target engineering / construction / telecom / energy projects before formal procurement while keeping the project-to-procurement lead-time metric evidence-based.

The change intentionally does **not** backfill historical projects merely to create a non-zero lead-time result.

## Problem proven in production

S48 was operationally healthy and polled the MOI news page successfully, but v1 repeatedly produced zero candidates.

Read-only inspection of the retained live MOI discovery artifact showed the first page contained 20 current news cards. Several titles were target-sector engineering/construction related, but v1 discarded them before detail fetch because the title-level gate required an explicit project marker.

Inspection also showed why simply widening the gate would be wrong. Current examples included:

- large staff-housing reconstruction already under construction;
- a new museum building at foundation-stone ceremony;
- flood-control/embankment repair work already being executed;
- recovery works already in progress.

Those are useful project context but are not honest evidence of detection before procurement.

## v2 selection contract

Selection policy version: `2`.

Listing recall requires:

- target-sector relevance; and
- either an explicit project marker or concrete future capital intent; and
- not an already-open procurement; and
- not obvious started/completed activity.

Detail acceptance then requires:

- target-sector relevance;
- project marker or capital intent;
- explicit pre-procurement forward evidence such as approval, plan, feasibility/design, budget/funding, procurement preparation, or future construction/upgrade/expansion intent;
- no underway / construction-started evidence;
- no groundbreaking/foundation-stone evidence;
- no opened/completed/commissioned evidence;
- no open Tender/procurement evidence.

A retained row remains `PROJECT_PRECURSOR_CANDIDATE` and `precursor_review_required=true`. It is not a lifecycle event and does not count as a procurement opportunity until human review explicitly promotes exact project identity.

## Review visibility

Business Digest version advanced to `13`.

The digest data model now includes `business.project_precursor_pipeline`. When pending candidates exist, rendering surfaces up to three under a dedicated `采购前项目线索` review section with:

- source;
- translated title;
- stage hint;
- target categories;
- first retained detection date;
- issuer publication date;
- official MOI link.

The renderer explicitly states that these are review candidates and are not current procurement opportunities.

## Test evidence

Before merge:

- final-goal targeted tests: `51 passed`;
- full unittest suite: `509 passed`;
- Python compileall: PASS;
- `git diff --check`: PASS.

Regression coverage includes:

- future capital intent without the literal word “project” can route to detail;
- generic sector news is rejected;
- construction underway is rejected;
- foundation-stone / groundbreaking is rejected;
- open Tender is rejected;
- current MOI Burmese late-stage construction title patterns are rejected;
- a valid pre-procurement capital-intent detail is retained as a candidate;
- Business Digest surfaces a pending precursor but does not increase current procurement opportunity count.

## Code and deployment identity

PR #253:

`feat: improve pre-procurement precursor capture`

Merged application release:

`386edb2aa94b41a92cf9d5e25c9a1ad8d72c07fa`

Previous Bangkok application release:

`032798f2723dc3dc97946164b56993a6a0df3b58`

Release archive SHA256, verified equal on Mac and Bangkok:

`bf3f91015deb6f9bbad2a2b0cce4d10c473e731e8b1cf74b1ca8afdaf953fe62`

Deployment used the standard `deploy/deploy-signalforge-release.sh` path and returned `deployment=success`.

## Live S48 acceptance

Production refresh was executed through the required systemd Worker boundary:

`systemctl start signalforge-refresh@S48.service`

Result:

- `Result=success`;
- `ExecMainStatus=0`.

Latest S48 scheduler run:

- status: SUCCESS;
- `changed=0`;
- `signals_created=0`;
- `details_attempted=0`;
- `details_succeeded=0`;
- `items_parsed=0`;
- error: null.

Latest processing record:

- parser: `moi-news-project-precursor-list-v2`;
- status: SUCCESS;
- `items_found=0`;
- `canonical_items=0`;
- `signals_created=0`.

This zero result is accepted. The live page at verification time did not contain a record that passed the new pre-procurement gate. The observed engineering/construction examples were already late-stage and were deliberately not admitted.

## KPI and business-surface acceptance

`signalforge project-precursors --limit 50`:

- candidates: 0;
- pending review: 0;
- tracked: 0.

`signalforge business-kpis --lead-limit 20`:

- current business opportunities: 8;
- canonical opportunities: 6;
- verified-external opportunities: 2;
- project precursor candidates: 0;
- tracked projects: 0;
- linked projects: 0;
- lead-time headline remains unmeasured.

This is the correct state until a real future precursor is retained, reviewed and later linked to actual procurement.

`signalforge business-digest --no-network`:

- status: PASS;
- digest version: 13;
- monitored sources: 32;
- green sources: 32;
- current business opportunities: 8;
- precursor pipeline present with explicit zero sample.

`signalforge opportunities --source-id S48 --include-expired --limit 50`:

- status: PASS;
- count: 0;
- total matching: 0.

The precursor path therefore remains isolated from the Tender opportunity surface.

## Runtime acceptance

- SignalForge status: PASS;
- SignalForge health: GREEN;
- active sources: 32;
- S48 fetch health: GREEN;
- S48 freshness health: GREEN;
- S48 source health: GREEN;
- S48 consecutive failures: 0;
- recovery backlog: 0;
- `PRAGMA quick_check = ok`.

All four timers remain enabled and active/waiting:

- `signalforge-run-due.timer`;
- `signalforge-telegram-deliver.timer`;
- `signalforge-telegram-digest.timer`;
- `signalforge-assurance.timer`.

## Next final-goal bottleneck

S48 v2 fixes an avoidable recall blind spot, but a single general MOI news feed is unlikely to yield enough high-quality pre-procurement evidence by itself.

The next expansion should therefore target upstream official evidence surfaces with a higher causal relationship to later procurement:

1. project approval / authorization;
2. budget and funding allocation;
3. master plan / feasibility / detailed design;
4. loan or development-finance approval;
5. planned capital works / upgrade / expansion announcements.

The priority is evidence quality and measurable early discovery, not increasing raw source count.
