# S49 Construction Ministry Precursor Production Closure — 2026-09-27

## Objective

Add an official upstream evidence surface that can detect named construction / infrastructure / telecom / engineering projects before formal procurement, without manufacturing historical lead-time samples.

## Production identity

- PR: #255 `feat: add Construction Ministry precursor source`
- Active release: `fde7f078e23146dddb11208e914aed725f2b7dd3`
- Previous release: `386edb2aa94b41a92cf9d5e25c9a1ad8d72c07fa`
- Release archive SHA256: `11540fbe9dc1147b43bc5962eb9c9ebba76270c15ec9c033de9244fa32a4eb20`
- Standard deployment path: `deploy/deploy-signalforge-release.sh`

## Source contract

S49 monitors the Ministry of Construction planned-capital-work news surface using the strict-TLS-valid non-`www` host.

The parser is fail-closed:

- requires target-sector relevance;
- requires an exact project marker or concrete future capital intent;
- requires forward pre-procurement evidence;
- rejects started/underway, foundation-stone, opened/completed/commissioned and open-procurement records;
- classifies the primary project using the article title plus the first relevant primary paragraph;
- does not use unrelated later project-inspection paragraphs to determine the main project's stage;
- requires human review before lifecycle promotion and explicit reviewed project-to-procurement linking.

Generic bilateral or sector-framework discussion without exact project identity is not a lead-time candidate.

## Historical-boundary rule

`baseline_lookback_days=0`.

Historical current-page records may validate selector/parser behavior, but they must not become production detection evidence. SignalForge detection time for S49 starts only from a record retained after source activation.

## Test evidence

Before merge:

- focused S49 / contract / scorecard tests: 21 PASS;
- full unit suite: 516 PASS;
- compileall: PASS;
- `git diff --check`: PASS;
- GitHub `verify`: PASS.

## Live acceptance

First production run executed via:

`systemctl start signalforge-refresh@S49.service`

Result:

- `Result=success`;
- `ExecMainStatus=0`.

Latest scheduler run:

- status SUCCESS;
- changed 0;
- signals created 0;
- details attempted 0;
- details succeeded 0;
- items parsed 0;
- error null.

Discovery processing:

- parser `construction-news-project-precursor-list-v1`;
- status SUCCESS;
- selector-matching listing items found: 1;
- canonical items: 0;
- signals created: 0.

This is the intended baseline behavior. A historical listing can match the selector, while zero-lookback prevents it from being fetched/retained as a newly detected precursor.

## Business/KPI boundary

After activation:

- S49 procurement opportunities: 0;
- project precursor candidates: 0;
- pending review: 0;
- tracked projects: 0;
- linked projects: 0;
- lead-time headline: unmeasured.

Current opportunity output remains:

- 8 current business opportunities;
- 6 canonical opportunities;
- 2 verified external opportunities.

No precursor record is counted as a Tender opportunity.

## Runtime health

Post-refresh:

- SignalForge: PASS / GREEN;
- active sources: 33;
- green sources: 33;
- S49 fetch health: GREEN;
- S49 freshness health: GREEN;
- S49 source health: GREEN;
- S49 parse health: UNKNOWN only because no detail BUSINESS_PROCESSING sample exists yet;
- consecutive failures: 0;
- recovery backlog: 0;
- SQLite `PRAGMA quick_check = ok`.

All four production timers are enabled and active/waiting.

## Next bottleneck

The final goal now depends more on upstream evidence diversity than on Tender-source count. The next source tranche should prioritize official electricity/energy evidence with a plausible causal lead into later procurement:

- project approval / authorization;
- financing or loan approval;
- budget/funding allocation;
- master plan / feasibility / detailed design;
- named planned grid, substation, generation, transmission or distribution works.

Historical backfill remains prohibited for detection-time metrics.
