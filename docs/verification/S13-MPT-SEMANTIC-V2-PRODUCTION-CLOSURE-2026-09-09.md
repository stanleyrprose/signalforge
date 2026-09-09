# S13 MPT Semantic v2 — Production Closure — 2026-09-09

## Result

> **COMPLETE / PASS / PRODUCTION**

S13 MPT now has a production semantic parser capable of turning future genuine MPT tender pages into SignalForge business opportunities without changing the existing Direct HTTP acquisition path, canonical identity, global qualification policy, Browser/Provider architecture, or historical database records.

## Exact implementation

SignalForge PR #115 merged as:

`21c162e0333c328e06f9a83ad7bee7b1bdf2abdf`

Immediate rollback target:

`ff9df1af9ebf7e144b33b94aec7f6d32782a1992`

Deployment archive SHA256, identical locally and on Bangkok:

`2698747d39ea4275b192c103d67caa4319a6e188cb30238e613c9aef6496f948`

Runtime parser versions:

- detail parser: `mpt-v4`
- normalizer: `mpt-normalize-v2`
- canonicalizer remains unchanged
- acquisition remains `direct_http`

## Semantic v2 contract

For a valid MPT tender page the parser now preserves existing fields and adds deterministic business semantics:

- `business_stage`
- `scope_summary`
- `detail_completeness`
- `deadline_evidence`
- `deadline_candidates`
- evidence-backed `procurement_stage`

Official MPT tender pages commonly expose reference number, project name, publication date, location, company qualification/turnover, required quantity/scope, remarks, and deadline text. No Browser, PDF, OCR or external enrichment is required.

## Deadline rules

The parser now recognizes full and abbreviated English month names, including MPT forms such as `10 th Apr 2025`.

Deadline selection is deliberately fail-closed:

1. collect official deadline-date candidates from deadline text;
2. when publication date exists, keep only candidates on or after publication date;
3. accept only one unique reasonable candidate;
4. if official candidates exist but none or multiple reasonable dates remain, set `deadline=None` with `OFFICIAL_HTML_DEADLINE_CONFLICT`;
5. do not calculate a deadline from MPT template wording such as `within 15 days`.

This prevents copied/stale official template dates from becoming invented facts.

## Real-page audit

All 16 currently stored S13 MPT official pages were fetched read-only from Bangkok and parsed with v2 before production rollout.

Result:

- `15` -> `OPPORTUNITY` with explicit accepted official deadline
- `1` -> `TENDER_NOTICE` with `OFFICIAL_HTML_DEADLINE_CONFLICT`
- minimum derived business scope length: `41`
- `16/16` currently contain evidence for `PRE_QUALIFICATION`

The only fail-closed deadline case is `mpt:202604-CTO-029` / `BTS Battery Purchasing Project FY26`:

- publication date: `2026-04-08`
- official deadline candidates include `2026-03-06` and `2025-03-06`
- both precede publication
- production v2 therefore refuses to accept either date

Historical MPT pages containing a reasonable current-year deadline plus a stale copied prior-year date correctly keep only the reasonable candidate.

## End-to-end regression

A synthetic future MPT telecom tender was parsed and inserted through the normal canonical/signal read model in tests. `current_opportunities` classified it as:

- `OPEN`
- Trust `A`
- Priority `HIGH`
- Primary relevance `TELECOM`
- source engine `direct_http`
- evidence `OFFICIAL_HTML`

This proves future eligible MPT tenders can flow through:

`MPT HTML -> parser v4 -> canonical/signal -> current_opportunities -> Qualification -> Briefing -> Telegram`

No special MPT ranking path was added.

## Verification

- targeted MPT/opportunity/acquisition/briefing/Telegram tests: `27 passed`
- full suite: `239 passed`
- `git diff --check`: PASS
- real 16-page read-only parser preview: PASS
- exact production runtime reports `mpt-v4 / mpt-normalize-v2`
- active runtime read-only parse of `mpt:CCO-2026-001`: `OPPORTUNITY`, explicit official deadline evidence, 420-char business scope, `PRE_QUALIFICATION`

## Historical-noise protection

No historical MPT canonical migration or business-enrichment backfill was performed.

Before deployment:

- S13 canonical: `16`
- S13 signals: `10`
- global canonical: `194`
- global signals: `44`
- Telegram receipts: `4`

Immediately after deployment:

- S13 canonical: `16`
- S13 signals: `10`
- global canonical: `194`
- global signals: `44`
- Telegram receipts: `4`

A post-deploy Telegram delivery invocation returned `pending_count=0 / sent_count=0`.

The canonical change detector remains based on official page content hash rather than parser version, so parser deployment alone does not create historical UPDATED signals.

Production `signalforge opportunities --source-id S13` intentionally remains empty immediately after rollout because the 16 historical canonical payloads were not rewritten. This is expected and is evidence that no hidden backfill occurred.

## Final production state

- active application: `21c162e0333c328e06f9a83ad7bee7b1bdf2abdf`
- immediate rollback: `ff9df1af9ebf7e144b33b94aec7f6d32782a1992`
- SignalForge: `PASS / GREEN`
- DB quick check: `ok`
- canonical: `194`
- signals: `44`
- S13 canonical/signals: `16 / 10`
- recovery backlog: `0`
- Telegram receipts: `4`
- acquisition timer: enabled / active
- Telegram timer: enabled / active

No forced S13 refresh was used for rollout verification. The next genuine new or officially changed MPT tender will naturally exercise semantic v2 through the normal scheduler.
