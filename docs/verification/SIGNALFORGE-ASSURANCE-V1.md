# SignalForge Assurance v1

## Purpose

SignalForge Assurance v1 adds a counter-evidence loop around the production signal pipeline. Its job is not to produce more Signals. Its job is to prove where SignalForge may be blind, preserve false negatives, make filtering auditable, give humans a controlled override, and periodically test whether operational metrics still correlate with commercial value.

The assurance layer never changes a canonical item or Signal merely to make a metric look better.

## Five controls

### 1. Independent high-value coverage audit

Mandatory coverage sources are the CORE portfolio sources `S13`, `S20`, `S21`, `S30`, `S38`, `S39`, plus strategic procurement source `S41` (MYTEL).

Coverage is persisted in `coverage_audit_results` with explicit statuses:

- `PASS`: the independent official-surface candidate set is represented in canonical state.
- `GAP`: at least one independently observed official candidate is missing. A deduplicated RED miss is opened automatically.
- `PARTIAL`: only partial assurance is possible.
- `UNPROVEN`: the system lacks enough independent evidence. This is never promoted to PASS by assumption.
- `CHECK_FAILED`: the independent check itself failed.

S13/MPT and S41/MYTEL reuse the already independent auditor reconciliations. S20/S21/S30/S39 use assurance-only official listing link extraction and do not call the production source parser. S38 is provider-backed in production; Assurance does not add a hidden direct-HTTP bypass. It performs a bounded `DIAGNOSTIC` C0 raw fetch through the same approved Mac Provider, then applies an assurance-only link extractor rather than the production parser. S38 announcements that are official but do not satisfy the standard tender markers are kept as `INDEPENDENT_LISTING_NONSTANDARD` noise-review candidates rather than being misreported as tender coverage gaps. Provider acquisition failure is reported as `CHECK_FAILED`, never as PASS.

### 2. Random review of filtered/noise records

`noise_review_samples` provides a review queue. The candidate pool is limited to evidence SignalForge can actually prove it filtered or excludes:

- exact audited historical Signal noise already excluded by Source Scorecard accounting;
- `processing_records` where processing succeeded but produced zero items and the original raw evidence is still retained and replayable, joined to the original evidence envelope.

Selection is deterministic-random per calendar date and bounded. Previously sampled candidates are not repeatedly sampled while alternatives remain. Acquisition evidence is persisted before parsing so future zero-item and parser-failure outcomes remain replayable. Historical zero-item rows whose raw artifact was not retained are measured as an auditability gap rather than silently treated as reviewable noise.

Human outcomes are:

- `CONFIRMED_NOISE`
- `FALSE_NEGATIVE`
- `INCONCLUSIVE`

A `FALSE_NEGATIVE` automatically opens a RED `missed_signals` record.

### 3. Miss Ledger

`missed_signals` records what SignalForge failed to capture or classify. It is deliberately separate from successful Telegram delivery receipts.

A miss can be detected by `COVERAGE_AUDIT`, `NOISE_REVIEW`, or a human/operator. Stable dedupe keys prevent repeated weekly assurance runs from producing duplicate open misses.

Open RED misses make Metric Validity `FAIL` until resolved or explicitly marked false positive.

### 4. Human promotion of nonstandard but important signals

`manual_promotions` lets an operator promote an important item even when it cannot safely satisfy canonical identity/schema requirements.

A promotion is explicitly labelled `非标准化人工升级` and is never inserted into `canonical_items` or `signals`.

Active promotions appear in Business Briefing and the daily Business Digest under `🧑 人工升级`. `telegram-deliver` also sends undelivered active promotions immediately, but writes a separate `manual_delivery_receipts` record so canonical Signal delivery integrity remains intact.

### 5. Metric Validity Review

Each Assurance run persists a `metric_reviews` record. There is no opaque composite score. The review retains separate observables including:

- active and GREEN sources;
- mandatory coverage proof rate and status distribution;
- open misses and open RED misses;
- reviewed, conclusive, and inconclusive noise samples; false negatives; false-negative rate over conclusive reviews only;
- replayable vs unreplayable zero-item filtered evidence;
- current opportunities;
- effective vs raw Signals and known historical noise;
- Telegram alerts;
- active manual promotions;
- high-value sources with recent business yield.

Transparent rules:

- `FAIL` if any open RED miss exists or a mandatory coverage source has a confirmed `GAP`.
- `REVIEW` if mandatory coverage is `UNPROVEN`, `PARTIAL`, or `CHECK_FAILED`; if there is no conclusive noise sample in the current review window; if recent filtered zero-item evidence is not replayable; if a recent noise review found a false negative; or if technical health is healthy while no business outcome is being observed.
- `PASS` only when neither FAIL nor REVIEW conditions apply.

`active_sources`, `green_sources`, and `raw_signals` are diagnostic metrics only. They are never sufficient proof of commercial value.

## Operator CLI

All commands return JSON.

```bash
signalforge assurance-run
signalforge assurance-run --no-network --noise-sample-size 5
signalforge assurance-status

TYPESAFE_API_KEY=... signalforge jev-noise-triage
signalforge noise-samples --status PENDING
TYPESAFE_API_KEY=... signalforge jev-noise-shadow --status PENDING
signalforge noise-review <sample_id> --outcome CONFIRMED_NOISE --note "checked official evidence"
signalforge noise-review <sample_id> --outcome FALSE_NEGATIVE --note "live tender was filtered"

signalforge misses --status OPEN
signalforge record-miss --source-id S39 --title "Missing tender" --reason "found manually" --url https://...
signalforge resolve-miss <miss_id> --outcome RESOLVED --note "backfilled and verified"

signalforge manual-promote --source-id MANUAL --title "..." --summary "..." --reason "..." --priority HIGH --url https://...
signalforge manual-promotions --status ACTIVE
signalforge manual-resolve <promotion_id> --note "opportunity closed"
```

## Scheduling

`signalforge-assurance.timer` runs weekly on Sunday at 14:40 UTC, which is Sunday 21:10 in Myanmar (UTC+06:30), with up to five minutes randomized delay.

The service executes `signalforge assurance-run`. It persists evidence and findings but never sends Telegram by itself. Telegram delivery of manual promotions remains the responsibility of the existing `signalforge-telegram-deliver` path.

`jev-noise-triage` is an optional manual read-only pre-sampling aid. It ranks a bounded, source-balanced pool of unsampled replayable zero-item and nonstandard candidates, suppresses later-recovered zero-item history, and never creates review rows or changes Assurance scheduling.

`jev-noise-shadow` is an optional manual read-only review aid for samples already in `noise_review_samples`. It may recommend a PENDING sample for human review, but it never changes `noise_review_samples`, creates `missed_signals`, or alters Assurance scheduling.

## Boundaries

- Assurance does not modify canonical source records or Signals.
- It does not bypass provider/network policy to make coverage look complete.
- An unsupported or unavailable independent check is `UNPROVEN`, not PASS.
- Coverage audit is not a substitute for source health; source health is not a substitute for coverage.
- Noise sampling is not claimed to be exhaustive. It is a bounded mechanism for estimating false-negative risk and discovering filter drift.
- Manual promotion is not normalization. It is a controlled business override with explicit provenance.
