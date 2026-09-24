# Core Business KPI Production Closure — 2026-09-24

## Result

**PASS / LIVE KPI SURFACE / LEAD-TIME SAMPLE NOT YET MATURE**

SignalForge now exposes and runs the two core business-success metric families in Bangkok production:

1. current mission opportunity output quality;
2. reviewed project-to-procurement lead time.

The implementation intentionally does not collapse them into one opaque score.

## Production release

- active application: `95e9161956df2b737c851cbedc78d1eb23f1621b`;
- previous active application: `675c40e21427dfb13cd32978b156887eeecabef0`;
- release archive SHA256 verified local == Bangkok before deployment:
  `e3dad476831370501cfbe70008d93f587df6014ccb95c2b5d046eff06d216210`;
- deployment completed through the standard SignalForge release script with automatic timer pause/restore and rollback semantics;
- post-deploy SQLite `PRAGMA quick_check=ok`;
- all four SignalForge timers are enabled and active.

The release contains the already-reviewed lifecycle foundation from PR #243, the separately reviewed optional OCR runtime-projection evidence change from PR #244, and the core KPI read model from PR #245. No new source, delivery policy, public API, scheduler topology, or automatic project/procurement fuzzy linker was introduced by the KPI work.

## KPI definition

### Opportunity output quality

The quality surface reports separate observables:

- mission opportunity count;
- canonical Signal Quality score distribution;
- Trust distribution;
- official-evidence, timeframe and explicit-next-action completeness;
- verified-external proof completeness;
- Assurance coverage/miss/false-negative state.

`signal_quality_score` measures evidence completeness and business actionability. It is **not** a false-positive precision estimate.

Reviewed verified-external opportunities remain `canonical_truth=false` and are kept outside canonical Signal Quality scoring.

### Project-to-procurement lead time

For explicitly reviewed links only:

`first retained project precursor detection -> official procurement publication`

The procurement reference prefers issuer publication date/time. `canonical_items.created_at` is only a fallback because ingestion delay would otherwise inflate claimed early-warning performance.

Date-only publication evidence is measured by Myanmar calendar day.

The linked project sample is not a precursor-to-procurement conversion rate.

## Live production snapshot

Snapshot time:

- UTC: `2026-09-24T16:21:39.069538Z`;
- Asia/Yangon: `2026-09-24 22:51`.

### Current business opportunities

- total mission opportunities: **9**;
- canonical: **7**;
- reviewed verified-external: **2**;
- status: **8 OPEN + 1 UNKNOWN**.

Canonical Signal Quality:

- average: **82.3**;
- median: **85**;
- bands: **4 VERY_HIGH + 2 HIGH + 1 REVIEW**;
- High/Very High rate: **6/7 = 85.71%**;
- Trust A: **6/7 = 85.71%**;
- official-evidence dimension: **7/7 = 100%**;
- known timeframe: **6/7 = 85.71%**;
- explicit next action: **6/7 = 85.71%**.

Verified-external:

- proof-complete: **2/2 = 100%**;
- canonical Signal Quality score assigned: **false**.

### Assurance / miss risk

- Metric Validity: **REVIEW**;
- mandatory coverage proof rate: **0.7143**;
- mandatory business coverage accounted rate: **0.8571**;
- open misses: **0**;
- open RED misses: **0**;
- conclusive reviewed noise samples: **25**;
- reviewed noise false negatives: **1**;
- reviewed noise false-negative rate: **0.04**;
- coverage-risk count: **3**.

Known coverage risks:

1. S13 MPT issuer discovery remains PARTIAL because reviewed external official evidence proved an opportunity not found by the issuer sitemap;
2. S21 Myanma Railways remains RED from persistent direct-fetch timeout; this predates the KPI release;
3. S20/YESC retains a DETAIL_PARTIAL opportunity because the official attachment channel is HTTP 404 and deadline/participation details are not proven.

The quality KPI therefore must be read together with Assurance. A high average quality score does not prove complete market coverage.

## Lead-time baseline

Live production result:

- tracked projects: **0**;
- explicitly linked procurements: **0**;
- official-publication-basis projects: **0**;
- ingestion-fallback projects: **0**;
- median / mean / min / max lead days: **null**.

Therefore the business answer today is:

> SignalForge cannot yet truthfully state “we discover procurement projects X days early.” The current production value is **UNKNOWN / NOT YET MEASURABLE**, because there is no reviewed project→procurement outcome sample.

This must not be represented as zero days.

## Historical backfill decision

The production database contains regulatory/network records, but the inspected historical records do not provide enough same-project identity evidence to create trustworthy project→procurement pairs.

For example, existing MPT network records describe network expansion or completed fiber migration. Treating those as procurement precursors merely to populate the KPI would create false lead-time performance.

Decision:

- do **not** fuzzy-link historical policy/news/regulatory items to tenders;
- do **not** use issuer publication date as historical SignalForge first-detection time;
- if a historical precursor is ever backfilled, `detected_at` must reflect actual retained SignalForge detection evidence;
- procurement linking remains explicit/reviewed.

## What must happen next for the metric to mature

The bottleneck is now data, not the lead-time formula.

For future high-confidence official project precursors in the target sectors, record a reviewed lifecycle event at actual SignalForge detection time with a stable project key. When an official procurement later appears, link it only after exact project identity is reviewed.

Recommended maturity gates before treating lead time as a management KPI:

- first result: at least one reviewed pair, reported only as a case study;
- directional metric: several independent reviewed pairs with visible sample size and stage breakdown;
- management KPI: a sufficiently broad, time-matured cohort across issuers/sectors, with measurement coverage reported beside median lead time.

No automatic fuzzy matching should be added merely to accelerate sample accumulation.

## Verification

Pre-merge / pre-deploy:

- affected-path tests: `87 passed`;
- full local suite: `504 passed`;
- compileall: PASS;
- PR #245 GitHub Actions `verify`: PASS.

Post-deploy:

- active release resolves to `/srv/signalforge/releases/95e9161956df2b737c851cbedc78d1eb23f1621b`;
- `signalforge business-kpis --lead-limit 20`: PASS;
- four timers: enabled + active;
- SQLite quick check: `ok`;
- scheduler continued natural successful runs after deployment;
- existing overall degraded health is attributable to the pre-existing S21 Railways fetch failure, not to this release.

## Closure

The core business KPI instrumentation is now live and honest:

- **Opportunity quality is measurable now** and currently strong on retained mission opportunities, with explicit coverage-risk caveats.
- **Early-discovery lead time is instrumented but not yet statistically observed**. Production starts from a clean zero-sample baseline rather than a fabricated historical number.

The next optimization target is trustworthy precursor capture and outcome linking, not further KPI formula complexity.
