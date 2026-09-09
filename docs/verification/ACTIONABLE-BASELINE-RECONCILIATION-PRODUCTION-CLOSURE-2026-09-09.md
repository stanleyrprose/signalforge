# Actionable Baseline Reconciliation — Production Closure — 2026-09-09

## Result

**PASS / PRODUCTION LIVE / BOUNDED BASELINE OPPORTUNITY RECOVERY**

SignalForge historically used `first_baseline_customer_signal=false` to prevent source onboarding from flooding customers with historical records. Production business-value audit showed a real side effect: a baseline canonical that remained actionable but never changed afterward could remain permanently silent.

The first production audit found seven such tenders with explicit future deadlines and zero signals:

- S38 `industry:1022` — deadline `2026-09-11 16:00`
- S38 `industry:1034` — deadline `2026-09-14 16:00`
- S39 `energy:235` — deadline `2026-09-18 13:00`
- S38 `industry:1037` — deadline `2026-09-22 16:00`
- S38 `industry:1036` — deadline `2026-09-24 16:00`
- S38 `industry:1039` — deadline `2026-09-25 16:00`
- S38 `industry:1035` — deadline `2026-10-02 16:00`

Deadline evidence was already strong and canonicalized: S38 uses `EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME`; S39 uses `OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME`.

## Production rule

PR #99 introduced a per-source opt-in `actionable_baseline_signal_policy`, enabled only for S38 and S39 in the initial rollout:

```json
{
  "enabled": true,
  "min_remaining_seconds": 43200,
  "max_signals_per_run": 3
}
```

The reconciliation rule is intentionally narrow:

- first baseline itself remains signal-free;
- only canonical `TENDER` items are eligible;
- payload `business_stage` must equal `OPPORTUNITY`;
- explicit deadline + deadline time must parse successfully;
- at least 12 hours must remain before deadline;
- canonical must have no existing customer signal of any type;
- candidates are ordered by nearest deadline first;
- at most three signals are inserted per source run;
- inserted signal type is `NEW`;
- payload includes `signal_reason=ACTIONABLE_BASELINE_RECONCILIATION`;
- insert is guarded atomically by `WHERE NOT EXISTS`, making repeated or closely spaced scheduler invocations idempotent.

There is no new DB schema, daemon, browser capability, provider capability or external side effect. The rule runs only after a successful non-baseline source execution.

## Test gate

Regression proves the original safety boundary and the new recovery behavior together:

- S39 baseline still creates zero signals;
- next non-baseline run with unchanged canonical data creates one reconciliation signal for `energy:235`;
- signal reason is explicit;
- a subsequent run creates zero additional signals;
- provider / engine / source contract targeted suite: `31 passed`;
- full SignalForge suite: `217 passed`;
- `git diff --check`: PASS.

PR #99 passed CI and squash-merged as:

`6f10d0f5a7cf37ca11d8461c03a54b3ff9f648c7`

## Production rollout

Pre-rollout:

- active application: `38ba382bd132769dd89e784331f06c3ae7e3392a`;
- signals: `35`;
- S38 signals: `0`;
- S39 signals: `0`;
- DB quick check: `ok`;
- timer frozen before deployment;
- run-due inactive;
- refresh services inactive.

Exact release `6f10d0f5a7cf37ca11d8461c03a54b3ff9f648c7` deployed successfully with the timer still disabled.

## S39 live gate

Manual source execution while the scheduler timer remained frozen:

- Worker: `signalforge-20260909T022719Z-ef18977b`
- app run: `855a944b-4f37-4174-8f3b-3fcdefc5f05a`
- baseline: false
- changed: 0
- signals_created: 1
- details_attempted: 0
- status: SUCCESS

Exactly one signal was inserted:

`NEW / energy:235 / ACTIONABLE_BASELINE_RECONCILIATION / 2026-09-18 13:00`

Global signals changed `35 -> 36`.

## S38 bounded live gates

First S38 execution:

- app run `22df739b-37a7-4cfc-ae02-5fb396bdf7ec`
- status SUCCESS
- baseline false
- changed 0
- details_attempted 0
- signals_created **3**

Promoted opportunities:

- `industry:1022` — `2026-09-11 16:00`
- `industry:1034` — `2026-09-14 16:00`
- `industry:1037` — `2026-09-22 16:00`

Global signals changed `36 -> 39`.

Second S38 execution:

- app run `0044b9f4-747a-4da6-b7c6-fde0e1c29975`
- status SUCCESS
- changed 0
- details_attempted 0
- signals_created **3**

Remaining eligible opportunities were promoted:

- `industry:1036` — `2026-09-24 16:00`
- `industry:1039` — `2026-09-25 16:00`
- `industry:1035` — `2026-10-02 16:00`

Global signals changed `39 -> 42`.

The DB rows in each batch share the same run timestamp, so row display order inside a timestamp is not used as proof of insertion order; eligibility ordering is locked by regression and the observed batch membership is correct.

## Idempotency / expiry gate

A third S38 execution and a second S39 execution both completed SUCCESS with:

- changed: 0
- signals_created: 0
- details_attempted: 0.

Final live checks:

- S38 signal count: `6`;
- S39 signal count: `1`;
- global signals: `42`;
- expired S38 canonicals `industry:1025` and `industry:1033`: `0` signals;
- future-deadline S38/S39 canonicals without a signal: `0`;
- SQLite quick check: `ok`.

This proves both bounded promotion and duplicate suppression without deleting or mutating historical canonicals.

## Timer restoration / scheduler gate

Bangkok timer was restored enabled/active.

At restoration, two closely spaced normal `run-due` invocations occurred (the persistent timer trigger and an explicit scheduler start). Both completed `SUCCESS`; all sources were `NOT_DUE`, including S38 and S39, and the total signal count remained `42`.

This is also an additional idempotency proof: closely spaced scheduler invocations do not duplicate actionable-baseline signals.

Final production snapshot:

- active application: `6f10d0f5a7cf37ca11d8461c03a54b3ff9f648c7`;
- timer: enabled / active;
- run-due: inactive after successful completion;
- SignalForge: `PASS / GREEN`;
- non-GREEN sources: none;
- canonical items: `193`;
- signals: `42`;
- recovery backlog: `0`;
- DB quick check: `ok`.

## Product boundary

This rule is not a generic historical backfill mechanism. It exists to repair one specific conflict between two desirable semantics:

1. first source baseline must not flood customers with history;
2. a high-confidence tender that is still open must not remain permanently silent merely because it first appeared during baseline.

Initial production authorization remains limited to S38 and S39. Other sources must not opt in merely because they have zero-signal baseline records; they need explicit future deadline evidence of comparable quality first.

Beijing is outside SignalForge production topology and was not part of this rollout.
