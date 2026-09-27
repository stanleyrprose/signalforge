# Project → Procurement Link Review Production Closure — 2026-09-27

## Objective

Close the operational gap between upstream project precursor capture and the final business metric:

> how many days before official procurement did SignalForge first detect the project?

S48, S49 and S50 can retain pre-procurement candidates, but SignalForge still needed a safe operational path to help a human reviewer identify a later procurement that may belong to an already promoted project.

The new path is deliberately **review-only**. It does not create project links and it does not change the lead-time KPI until a human performs the existing explicit reviewed link action.

## Code and CI

PR #259:

`feat: add reviewed project procurement link queue`

Merged release:

`e905cbd93a88bc0a19fa2bda82a15f08e27f9072`

GitHub Actions:

- workflow: `verify`;
- run: `36325428113`;
- result: PASS.

Local verification before merge:

- focused leadtime / Business Digest / business KPI tests: `48 passed`;
- full unittest suite: `531 passed`;
- Python compileall: PASS;
- `git diff --check`: PASS.

## Review queue contract

The read-only function and CLI expose possible later procurement records for already promoted lifecycle projects.

Selection boundaries:

1. project must already exist in `project_lifecycle_events`;
2. projects already linked to procurement are excluded;
3. procurement canonicals already used by another reviewed link are excluded;
4. official procurement publication evidence must not predate the project's first SignalForge detection;
5. if official publication time is unavailable, canonical ingestion time is only a fallback temporal gate;
6. there must be a deterministic project-identity anchor;
7. sector, location and issuer may increase review ranking but are supporting evidence only;
8. generic asset words such as power / plant / substation / road / bridge / network / construction are not sufficient identity anchors;
9. project location and issuer terms are explicitly removed from the authoritative anchor set;
10. fuzzy automatic linking is prohibited.

A dedicated regression proves that a project and tender sharing only `Naypyidaw + ENERGY + same ministry` do **not** produce a suggestion.

Cross-sector suggestions remain possible when the actual project identity is strong. This supports cases such as a power-related precursor inside the Pinpet steel-factory project later leading to an Industry procurement record sharing the named Pinpet / steel-factory identity.

## Authority boundary

Every suggestion returns:

- `authority = REVIEW_ONLY_NO_LINK_WRITE`;
- `required_action = EXPLICIT_PROJECT_LINK_PROCUREMENT_REVIEW`.

The suggestion score is a deterministic ranking aid, not a match probability.

The only authoritative write path remains explicit:

`project-link-procurement --project ... --canonical ... --basis ... --by ...`

No suggestion call invokes that command or writes to `project_procurement_links`.

## Product surfaces

The queue is exposed in three places:

1. CLI: `project-link-suggestions`;
2. `business-kpis` as `project_procurement_link_review`;
3. Business Digest v14.

When suggestions exist, Digest renders a dedicated `项目→采购待复核` section and explicitly states that it will not automatically establish the project→procurement link.

The actual lead-time metric remains separately scoped to explicit reviewed links only.

## Deployment

Previous Bangkok release:

`d28b2184d4930369ec93d5e73b14f3ebe23ef6ab`

New Bangkok release:

`e905cbd93a88bc0a19fa2bda82a15f08e27f9072`

Release archive SHA256, identical on Mac and Bangkok:

`7f26cf7110d2864324b3a89e5072768614a7547f53d6cb8c8bab36670c892383`

The first standard deployment attempt returned:

`SignalForge busy; deploy deferred` with exit code `75`.

This was accepted fail-safe behavior. No lock bypass, force deployment or worker termination was used.

The busy gate was then rechecked against:

- `signalforge-run-due.service`;
- `signalforge-telegram-deliver.service`;
- `signalforge-telegram-digest.service`;
- `signalforge-assurance.service`;
- all active/activating `signalforge-refresh@*.service` units.

After all four named services were inactive/dead with successful prior results and no refresh unit remained active/activating, the exact same already-hashed release was deployed through the standard script.

Final deployment result:

`deployment=success application=signalforge release=e905cbd93a88bc0a19fa2bda82a15f08e27f9072 previous=d28b2184d4930369ec93d5e73b14f3ebe23ef6ab`

## Live production acceptance

Active symlink:

`/srv/signalforge/active -> /srv/signalforge/releases/e905cbd93a88bc0a19fa2bda82a15f08e27f9072`

### Review queue

`project-link-suggestions --limit 20 --per-project 3` returns:

- tracked projects: 0;
- already linked projects: 0;
- unlinked projects: 0;
- projects with suggestions: 0;
- suggestions: 0.

This is correct because production does not yet contain a human-promoted post-activation precursor project. No synthetic project was inserted just to produce a non-empty demo.

### Core KPI

`business-kpis --lead-limit 20` returns:

- business current opportunities: 8;
- canonical current opportunities: 6;
- verified-external current opportunities: 2;
- canonical quality average: 81.2;
- high / very-high canonical rate: 0.8333;
- project precursor candidates: 0;
- tracked projects: 0;
- project procurement review suggestions: 0;
- reviewed project-to-procurement lead-time samples: 0.

Lead-time therefore remains unmeasured, as required.

### Business Digest

`business-digest --no-network` returns:

- status: PASS;
- digest version: 14;
- monitored sources: 34;
- green sources: 34;
- current opportunities: 8;
- explicit `project_precursor_pipeline`;
- explicit `project_procurement_link_review`.

Because the queue is empty, the user-visible review section is correctly omitted rather than rendering noise.

## Read-only proof

Before invoking the new review queue plus KPI and Digest reads:

- project lifecycle events: 0;
- project procurement links: 0;
- canonical items: 251;
- signals: 72;
- digest delivery receipts: 18.

After invoking them:

- project lifecycle events: 0;
- project procurement links: 0;
- canonical items: 251;
- signals: 72;
- digest delivery receipts: 18.

The commands therefore introduced no lifecycle, link, canonical, Signal or delivery-receipt mutation.

SQLite `PRAGMA quick_check` returned `ok`.

## Runtime health

Post-deployment:

- SignalForge status: PASS;
- SignalForge health: GREEN;
- active sources: 34;
- recovery backlog: 0.

All production timers are enabled and active/waiting:

- `signalforge-run-due.timer`;
- `signalforge-telegram-deliver.timer`;
- `signalforge-telegram-digest.timer`;
- `signalforge-assurance.timer`.

## Final-goal implication

The technical loop is now complete:

`official precursor source -> PROJECT_PRECURSOR_CANDIDATE -> human project promotion -> review-only procurement suggestion -> explicit human procurement link -> measured lead-time`

What remains is evidence arrival, not missing plumbing.

The first real lead-time sample must come from a precursor first retained **after** its source activation and later connected to a real official procurement by explicit review. Historical S48/S49/S50 parser fixtures remain prohibited as artificial detection history.
