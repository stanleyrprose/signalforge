# Source Portfolio Business-Yield Audit — 2026-09-10

## Decision

Do not change source roles, priorities or polling intervals from this audit.

SignalForge now has enough production evidence to distinguish technical health from business yield, but not enough elapsed time to prune or downgrade sources safely. The active-source observation window ranges from less than one day for S41 to roughly eight days for S13; most sources have only three to seven days of production history.

The correct action is therefore a **provisional portfolio tiering** for decision-making and future re-audit, not runtime reconfiguration.

## Current production baseline

Production runtime remains:

`c5c2327c2300e5d7a22fce3222552bf8c6de7cc9`

Current production state after S41 activation:

```text
canonical_items = 209
raw signals     = 45
recovery backlog= 0
customer view   = 8 OPEN + 1 UNKNOWN
```

All currently active sources have `baseline_complete=1` and `consecutive_failures=0` at the audit snapshot.

## Effective-signal accounting

Raw signal count is not a valid source-productivity measure because known historical implementation noise is preserved for audit.

The portfolio therefore uses an **effective business signal** count for this audit only:

```text
45 raw signals
-20 S25 historical attachment/normalization UPDATED noise
- 1 S13 parser-only historical UPDATED noise (mpt:CCO-2026-001)
=24 effective business signals
```

No rows are deleted or rewritten. This is an analytical accounting rule only.

Effective signal contribution currently observed:

| Source | Effective signals | Current known OPEN | Current UNKNOWN opportunities | Latest issuer publication seen |
|---|---:|---:|---:|---|
| S13 MPT | 10 | 0 | 0 | 2026-07-17 |
| S38 Industry | 6 | 6 | 0 | 2026-09-07 |
| S20 MOEP | 3 | 0 | 0 | 2026-09-08 |
| S26 DOMS | 2 | 0 | 3 | 2026-09-08 |
| S08A Customs Auctions | 1 | 0 | 0 | 2026-09-08 |
| S30 MOFA | 1 | 1 | 1 | 2026-09-04 |
| S39 Energy | 1 | 1 | 0 | 2026-09-04 |
| all other active sources | 0 | 0 | varies | varies |

These seven sources account for all 24 effective business signals observed so far.

## Observation-window boundary

First recorded production scheduler runs range from:

- S13: 2026-09-02;
- S21: 2026-09-03;
- many government/regulatory sources: 2026-09-04;
- S16/S30-S37: 2026-09-07;
- S27/S38-S40: 2026-09-08;
- S41: 2026-09-10.

A zero-signal source is therefore mostly **unproven**, not demonstrated low-value. For example S21 Railways has 45 canonical records and an issuer publication as recent as 2026-09-01, but no post-baseline signal yet. That is insufficient evidence to demote a technically healthy source.

## Provisional portfolio tiers

These tiers are analytical overlays only. They do not replace `ACTIVE_PRIMARY`, `ACTIVE_SELECTIVE`, provider/direct-http roles, source priority or polling configuration.

### Tier A — Core / proven decision yield

**S13 MPT, S20 MOEP, S30 MOFA, S38 Industry, S39 Energy**

Rationale:

- each has already produced real post-baseline business signals;
- collectively they account for 21 of 24 effective signals;
- S30/S38/S39 currently contribute all eight known-deadline OPEN opportunities;
- S13 is the highest-value operator-specific telecom source despite the current tender set being expired;
- S20 captures current power-sector procurement and has already produced multiple real signals.

This tier identifies proven decision yield; it does not imply every item is strategically equal.

### Tier B — Strategic Watch / high-value coverage, yield not yet proven

**S16 YCDC Engineering, S21 Myanma Railways, S22 Inland Water Transport, S27 Border Affairs, S34 PTD, S35 DAST, S41 MYTEL**

Rationale:

- these cover infrastructure, telecom/ICT, municipal engineering, science/technology or government capital spending with plausible high-value opportunity impact;
- S34 is strategically important telecom-sector procurement and already has validated HTML+PDF semantics, but all safely parsed current historical schedules are expired;
- S41 provides direct MYTEL procurement coverage and has only just entered production, so zero signal is expected rather than evidence of low value;
- S21 has substantial canonical activity and a recent issuer publication but too little post-onboarding time to judge yield.

These sources should stay operational without promotion/demotion until more production history exists.

### Tier C — Context / regulatory and selective opportunity intelligence

**S05A Commerce, S07 Customs Notifications, S08A Customs Auctions, S10 DICA, S12 IRD, S26 DOMS**

Rationale:

- these sources contribute regulatory, tax, company/investment, customs or sector-specific opportunity context rather than primarily Telecom/ICT tenders;
- zero tender signal is not a failure for regulatory sources whose value may be policy change rather than procurement frequency;
- S08A and S26 have already produced real events, validating collection value even though they are not core telecom sources;
- S26 remains selective because current medical tenders are deadline-UNKNOWN/scan-heavy and do not justify OCR expansion by themselves.

### Tier D — Observation / low-yield candidates, not yet prune candidates

**S25 MONPIFER, S28 Fisheries, S29 DWIR, S31 MOEA, S32 MTE, S33 MCRD, S36 DOA, S37 MOI, S40 Labour**

Rationale:

- no effective customer signal has yet been demonstrated in the short production window;
- S25 raw signal count is specifically excluded because its twenty historical `UPDATED` rows are known normalization noise;
- several sources currently carry historical deadline-UNKNOWN records, but prior audits already showed that further completion would require image/OCR or otherwise unjustified capability expansion;
- S40's current public surface is result/award-heavy, so zero canonical opportunity output is not currently a parser failure.

Tier D means **observe before investing**, not disable.

## Why no runtime changes now

The portfolio has three different reasons for zero signal that must not be conflated:

1. **quiet since baseline** — e.g. a healthy source published no new event after onboarding;
2. **context source** — regulatory intelligence is valuable even without tender signals;
3. **historical evidence limitation** — old opportunities may lack machine-readable deadlines but are already expired or not actionable.

Changing source role, priority or polling from a few days of history would optimize for onboarding timing rather than actual issuer behavior.

Therefore this audit authorizes **no source role downgrade, polling reduction, disablement or deletion**.

## Re-audit gate

Re-evaluate portfolio roles only after a materially longer production window. The default next portfolio decision gate is **30 days of production observation per source**, unless earlier evidence justifies action.

Earlier re-audit triggers are:

- repeated parser/acquisition failures or persistent non-GREEN health;
- recurring false/duplicate signals;
- a current high-value opportunity that the source cannot represent correctly;
- a source producing repeated high-value signals that justifies promotion;
- evidence that the issuer surface has become result-only, abandoned or structurally irrelevant;
- a newly discovered strategic source with a clearly superior official acquisition surface.

The 30-day gate is a governance threshold for pruning/promoting decisions, not a scheduler setting.

## Source-expansion policy after S41/S42 audits

S41 MYTEL passed the source-quality gate because an official, structured and repeatable procurement feed exists.

ATOM failed the same gate because the bounded audit found no qualifying public procurement surface. S42 therefore remains deferred.

The next source should not be added until it demonstrates both:

1. meaningful strategic/business coverage value; and
2. a trustworthy maintainable acquisition surface.

Until then, engineering effort should favor signal correctness and customer decision quality over source-count growth.

## Production impact

This audit is documentation/governance only.

No changes are made to:

- Source Registry runtime roles or priorities;
- poll/retry intervals;
- database schema or canonical rows;
- signal history;
- Telegram delivery policy;
- Direct HTTP / Provider / Browser Plane topology;
- Worker/Control Plane;
- Beijing role.

Production remains on runtime `c5c2327c2300e5d7a22fce3222552bf8c6de7cc9`.
