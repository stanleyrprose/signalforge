# Source Yield / Signal Funnel Audit v2 — 2026-09-12

## Decision

SignalForge production is technically healthy and the S16/YCDC incident is closed without code or routing changes. The value audit now has enough evidence to promote **S21 Myanma Railways from `STRATEGIC_WATCH` to analytical `CORE`**. No other source tier or runtime setting is changed.

This audit remains read-only with respect to acquisition and delivery semantics. It changes only the scorecard's analytical portfolio tier map.

## S16 / YCDC incident closure

S16 uses the stable YCDC Engineering Department (Building) archive:

`https://www.ycdc.gov.mm/frontend_engineering_building_detail/1`

On 2026-09-12 the source experienced an intermittent availability episode:

- `07:40 UTC` — SUCCESS, 5 items parsed;
- `08:10–08:55 UTC` — 8 consecutive `urlopen error timed out` failures;
- `09:05 UTC` — SUCCESS, 5 items parsed;
- `09:35 UTC` — SUCCESS, 5 items parsed.

A direct Bangkok probe after recovery resolved `www.ycdc.gov.mm` to `203.81.69.212` and returned HTTP 200 in approximately `0.3–0.7s` with both the SignalForge user-agent and a browser-like user-agent. This rules against a persistent block, parser drift, mandatory JavaScript rendering, or a stable need for Browser Plane fallback.

At the closure snapshot S16 reported:

```text
consecutive_failures = 0
fetch_health         = GREEN
freshness_health     = GREEN
parse_health         = GREEN
source_health        = GREEN
success_runs         = 216 / 224 ≈ 96.4%
canonical_count      = 5
effective_signals    = 0
current_opportunities= 0
recovery_backlog     = 0
```

Global SignalForge state had also automatically returned to `PASS / GREEN`.

### S16 decision

**No engineering change is authorized.** In particular:

- do not add Mac Browser Plane fallback;
- do not increase timeout merely to hide source health;
- do not change retry cadence;
- do not change parser or stable numeric archive URL.

The existing availability/recovery policy detected the outage, surfaced RED health, retried, and returned to GREEN without losing a newly observed business change. Adding another execution path for a transient 45-minute external outage would increase complexity without demonstrated business benefit.

S16 remains `STRATEGIC_WATCH`: technically healthy, strategically plausible, but currently baseline-only.

## Live production funnel

Snapshot: `2026-09-12T09:56:08Z`.

```text
27 active sources
        ↓  all 27 GREEN
210 active-source canonical items
        ↓
53 raw signals
        ↓  remove 21 audited historical-noise signals
32 effective business signals
        ↓
15 current opportunities
        ↓
11 Telegram alerts sent historically
```

The database totals are `212 canonical / 53 signals`; two canonical rows are non-active-source history and there are no non-active signals. Recovery backlog is `0`.

### Funnel ratios

| Stage | Count | Ratio / interpretation |
|---|---:|---|
| Active sources | 27 | 100% technically GREEN |
| Active canonical items | 210 | source evidence inventory |
| Raw signals | 53 | 25.2% of canonical count |
| Known historical noise | 21 | 39.6% of raw signals |
| Effective business signals | 32 | 60.4% of raw signals; 15.2% of canonical count |
| Current opportunities | 15 | 46.9% of effective-signal count currently actionable/open-or-unknown |
| Telegram alerts | 11 | 34.4% of effective-signal count; delivery policy is intentionally selective |

The opportunity set is `14 OPEN + 1 UNKNOWN`, with priority:

```text
HIGH   = 8
MEDIUM = 5
REVIEW = 2
LOW    = 0
```

There are currently **2 ICT/Telecom-relevant opportunities**, both HIGH:

1. **S39 Ministry of Energy** — tender 27/2026-2027, including Communication & Information accessories, Siemens IOT modules, ICDD PDF-2 software, computers/UPS; deadline 2026-09-18 13:00.
2. **S30 Ministry of Foreign Affairs** — Data Server + Windows Server / SQL Server procurement; deadline 2026-09-18 16:30.

## Source contribution concentration

### Current opportunity contribution

| Source | Current opportunities | Priority mix | TG alerts | Assessment |
|---|---:|---|---:|---|
| S38 Industry | 6 | 2 HIGH / 4 MEDIUM | 3 | strongest current opportunity producer |
| S21 Railways | 4 | 4 HIGH | 4 | repeated high-value actionable yield |
| S26 DOMS | 1 | 1 REVIEW | 1 | useful but incomplete deadline/action data |
| S39 Energy | 1 | 1 HIGH | 1 | strategically strong ICT/energy opportunity |
| S30 MOFA | 1 | 1 HIGH | 1 | strategically strong ICT opportunity |
| S32 MTE | 1 | 1 REVIEW | 1 | first proven seller-side commercial event |
| S22 IWT | 1 | 1 MEDIUM | 0 | legitimate opportunity; immediate TG policy does not require MEDIUM alert |

S38 + S21 alone account for **10/15 current opportunities (66.7%)** and **7/11 Telegram alerts (63.6%)**.

### Effective-signal contribution

| Source | Effective signals | Current opps | TG alerts | Portfolio interpretation |
|---|---:|---:|---:|---|
| S13 MPT | 10 | 0 | 0 | strategically critical, signal-rich, no current live opportunity |
| S38 Industry | 7 | 6 | 3 | high conversion to current action |
| S21 Railways | 4 | 4 | 4 | every observed effective signal is currently actionable/HIGH |
| S20 MOEP | 4 | 0 | 0 | signal proven; current set not live |
| S26 DOMS | 2 | 1 | 1 | useful selective context |
| S39 Energy | 1 | 1 | 1 | high-value ICT/energy |
| S30 MOFA | 1 | 1 | 1 | high-value ICT |
| S32 MTE | 1 | 1 | 1 | newly actionable seller-side event |
| S22 IWT | 1 | 1 | 0 | newly actionable MEDIUM event |
| S08A Customs Auction | 1 | 0 | 0 | signal proven, no current opportunity |

The top four sources by effective signals — S13, S38, S21 and S20 — contribute **25/32 = 78.1%** of all effective business signals.

## Noise accounting

The 21 known noise signals are already explicitly accounted for and are not deleted:

- S25 MONPIFER: 20 normalization-only historical UPDATED rows;
- S13 MPT: 1 audited parser-only historical UPDATED row.

S25 therefore remains `NOISE_ONLY_HISTORY` rather than appearing as a productive 20-signal source. This is essential; raw signal counts would otherwise materially mis-rank the portfolio.

## Yield-state distribution

```text
ACTIONABLE_PROVEN  = 7 sources
SIGNAL_PROVEN      = 3 sources
BASELINE_ONLY      = 15 sources
NOISE_ONLY_HISTORY = 1 source
EMPTY              = 1 source
```

Interpretation:

- **7 actionable-proven** sources have already produced a live opportunity or Telegram alert.
- **3 signal-proven** sources have produced valid business changes but currently no live opportunity.
- **15 baseline-only** sources should not yet be called low-value; most have <10 days observation.
- **S25** requires 30-day re-audit because historical raw signals were noise.
- **S40 Labour** is currently empty after ~3.7 observation days; too early to prune.

## Portfolio tier v2 decision

The 2026-09-10 audit explicitly allowed early re-audit when a source produces repeated high-value signals that justify promotion. S21 now satisfies that gate:

```text
S21 observation_days ≈ 8.7
canonical            = 45
effective signals    = 4
current opportunities= 4
HIGH opportunities   = 4
Telegram alerts      = 4
health               = GREEN
```

Therefore scorecard v2 changes only:

```text
S21: STRATEGIC_WATCH → CORE
```

S22 remains `STRATEGIC_WATCH`: one MEDIUM opportunity is promising but not repeated high-value evidence.

S32 remains `OBSERVATION`: its MTE commercial-event success is important, but one reviewed event is not yet enough to promote the whole source portfolio tier.

All other analytical tiers remain unchanged.

## Runtime actions authorized

**None.** This audit does not change:

- Source Registry role;
- source priority;
- poll/retry interval;
- source URL or acquisition engine;
- parser/canonical/signal qualification;
- Browser Plane routing;
- Telegram delivery policy;
- database rows;
- Beijing/Bangkok topology.

The only implementation change is the read-only source-scorecard analytical tier map and scorecard version `1 → 2`.

## Next decision gate

Do not prune low-yield sources yet. Re-audit at 30 days per source unless an earlier hard trigger occurs.

At that gate, focus on:

1. whether S25 produces any real post-fix effective signal;
2. whether S40 remains empty;
3. whether S16 remains technically stable and starts producing new YCDC business changes;
4. whether S21 continues to justify CORE status;
5. whether S22 or S32 produce repeated actionable events sufficient for promotion;
6. whether the current high concentration in S38/S21 persists or diversifies.
