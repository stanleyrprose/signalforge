# Opportunity Lifecycle Audit — 2026-09-13

## Scope

Read-only P0 audit of the 15-opportunity production snapshot after S46 PTD policy production closure. No Business Fit, source acquisition, qualification policy, Telegram delivery policy, canonical state, Signal generation, schema, timer, Browser/Provider, or runtime change is introduced.

Audited production funnel:

```text
31 active / 31 GREEN
227 DB canonical
53 raw Signals / 32 effective
15 current opportunities = 14 OPEN + 1 UNKNOWN
priority = 8 HIGH / 5 MEDIUM / 2 REVIEW
11 cumulative automatic Telegram alerts
immediate Telegram pending = 0
```

GitHub main later advanced to `29c5280ca4e28f9fd502b60845f5f0f7b0a1d624` for Signal Quality evidence/relevance provenance. Current main retains the same opportunity-lifecycle rules audited here.

## Verified lifecycle semantics

- `deadline/action_at <= now` => `EXPIRED`.
- Default current-opportunity view excludes EXPIRED rows.
- Date-only deadlines use `23:59 Asia/Yangon` as the conservative read-layer boundary.
- `remaining <= 72h` => `URGENT`; `<=7d` => `SOON`.
- A-grade non-strategic OPEN opportunities become HIGH when URGENT.
- A-grade ICT/TELECOM opportunities remain HIGH before the 72h boundary.
- Briefing maps `URGENT -> ACT_NOW`, non-urgent strategic HIGH -> `PRIORITIZE`, REVIEW priority -> `REVIEW`.
- Telegram delivery identity includes `canonical_key + latest_signal_id + attention_action`.
- Therefore a time-only action change can produce exactly one new Telegram delivery without a new issuer Signal, then deduplicates repeats.
- A genuine issuer update creates a new Signal id and can be delivered once again even when the action label stays the same.

Existing regressions explicitly cover time-based `PRIORITIZE/MEDIUM -> ACT_NOW` behavior and re-delivery for a new Signal id. The lifecycle-focused local selection passed `35/35`; branch CI is the final latest-main gate for this docs-only audit.

## Current 15-opportunity lifecycle map

All times are Myanmar time (UTC+06:30).

| Opportunity | Current state | Business time | Automatic lifecycle |
| --- | --- | --- | --- |
| S38 `INDUSTRY-ANN-1034` | HIGH / ACT_NOW | 2026-09-14 16:00 | already inside 72h; disappears after deadline |
| S21 `12(T)30/MR (ML/ISN)` | HIGH / ACT_NOW | date-only 2026-09-14 | read layer uses 23:59; disappears afterwards |
| S21 `15(T)5/MR(E)` | HIGH / ACT_NOW | date-only 2026-09-14 | same |
| S21 `326/.../CE` | HIGH / ACT_NOW | date-only 2026-09-14 | same |
| S21 `327/.../CMO` | HIGH / ACT_NOW | date-only 2026-09-14 | same |
| S32 `MTE-LOCAL-6/2026-2027` | REVIEW | event 2026-09-15 08:30 | action date, not fake bid deadline; disappears after event time |
| S38 `INDUSTRY-ANN-1041` | HIGH / ACT_NOW | 2026-09-15 16:00 | already inside 72h; disappears after deadline |
| S39 `ENERGY-27-2026-2027` | HIGH / PRIORITIZE | 2026-09-18 13:00 | ACT_NOW at 2026-09-15 13:00; disappears after deadline |
| S30 `MOFA-POST-59800` | HIGH / PRIORITIZE | 2026-09-18 16:30 | ACT_NOW at 2026-09-15 16:30; disappears after deadline |
| S38 `INDUSTRY-ANN-1037` | MEDIUM | 2026-09-22 16:00 | SOON on 09-15 16:00 but stays MEDIUM; HIGH/ACT_NOW on 09-19 16:00 |
| S38 `INDUSTRY-ANN-1036` | MEDIUM | 2026-09-24 16:00 | HIGH/ACT_NOW on 09-21 16:00 |
| S38 `INDUSTRY-ANN-1039` | MEDIUM | 2026-09-25 16:00 | HIGH/ACT_NOW on 09-22 16:00 |
| S38 `INDUSTRY-ANN-1035` | MEDIUM | 2026-10-02 16:00 | HIGH/ACT_NOW on 09-29 16:00 |
| S22 `IWT-NODE-1038` | MEDIUM | 2026-11-03 10:00 | HIGH/ACT_NOW on 10-31 10:00 |
| S26 `8DMS/2026-2027(L)` | REVIEW | deadline UNKNOWN | remains current until issuer evidence changes; no safe automatic expiry |

## Telegram accounting

The 11 automatic Telegram receipts are consistent with the lifecycle:

```text
initial Attention deliveries                     4
  historical S38 urgent opportunity              1
  S39 Energy PRIORITIZE                          1
  S30 MOFA PRIORITIZE                            1
  S26 DOMS REVIEW                                1
MTE REVIEW                                       1
four S21 rows entering 72h                       4
S38 1034 entering 72h                            1
S38 1041 entering 72h                            1
--------------------------------------------------
total                                            11
```

The historical S38 opportunity in the initial four has since expired. The other ten receipts correspond to the ten current Attention rows, explaining the verified production `pending=0` state.

If no issuer update happens first, the next expected time-only re-alerts are:

```text
2026-09-15 13:00 MMT  S39 Energy  PRIORITIZE -> ACT_NOW
2026-09-15 16:30 MMT  S30 MOFA    PRIORITIZE -> ACT_NOW
```

Later first-time watchlist escalations are S38 1037 on 09-19 16:00, S38 1036 on 09-21 16:00, S38 1039 on 09-22 16:00, S38 1035 on 09-29 16:00, and S22 on 10-31 10:00.

## Issuer extension/update behavior

No new mechanism is required for deadline extensions. A genuine issuer-side business change emits `UPDATED` under existing source semantics. Because Telegram identity includes `latest_signal_id`, the new evidence state can be delivered once even if the attention action does not change. Parser-only semantic migration remains governed by existing source-specific suppression guards and must not masquerade as issuer change.

## Finding: UNKNOWN-deadline lifecycle remains conservative

S26 DOMS is the only current opportunity with neither a trustworthy deadline nor an action date. It therefore cannot safely auto-expire:

```text
trusted event + missing deadline
-> REVIEW
-> stays in current opportunities
-> one delivery for current Signal/action state
-> no time-only repeat because REVIEW action does not change
```

This is not classified as a P0 bug. An arbitrary 7/14/30-day TTL could hide a still-open procurement event. If real operation later proves UNKNOWN rows become stale clutter, review a separate `STALE_REVIEW`/periodic re-audit policy rather than converting age into a business deadline.

## Decision

**P0 lifecycle audit = PASS / NO RUNTIME CHANGE.**

The current system already provides urgency escalation, one-time Telegram re-alert on action change, re-alert on genuine new Signal, and automatic removal after known deadline/action time. No duplicate scheduler, expiry Signal, Business Fit layer, or new alert channel is justified.

The next highest-value task is a **7-day Miss Audit**: compare real Myanmar tender / construction / telecom events against SignalForge coverage to measure what the 31-source portfolio failed to discover instead of increasing source count.