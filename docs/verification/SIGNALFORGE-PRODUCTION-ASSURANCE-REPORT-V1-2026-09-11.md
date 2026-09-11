# SignalForge Production Assurance Report v1 — 2026-09-11

## Status

**PASS WITH EXPLICIT COMPLETENESS LIMITS**

This report is a read-only production assurance snapshot for Bangkok SignalForge. It measures current operational health, business yield, customer delivery integrity, and bounded strategic coverage. It does **not** claim that SignalForge proves the absence of every possible Myanmar tender outside the monitored and independently reconciled surfaces.

- Report date/time zone: 2026-09-11 / Asia/Yangon.
- GitHub report baseline: `stanleyrprose/signalforge main@53eebae92195e3ba03abdc01a1fe58ec92963363`.
- Exact live application release: `bd86efcaa5699f1aa5082459cd57882b8ffe4e73` (`/srv/signalforge/active`).
- Production node: Bangkok only.
- Read paths used: `status`, `business-digest --no-network`, network-backed `audit`, `source-scorecard --window-days 30`, `opportunities`, Telegram dry-runs, systemd status, and read-only SQLite receipt queries.
- No acquisition was forced, no source was refreshed manually, no canonical/signal row was changed, and no Telegram message was sent by this audit.

## 1. Production funnel

| Layer | Live value | Interpretation |
| --- | ---: | --- |
| Active monitored sources | 27 | Production portfolio currently scheduled in Bangkok |
| GREEN sources | 27 / 27 | No current source-level GREEN degradation |
| Active-source canonical items | 207 | Canonical rows attributable to active sources |
| Database canonical items | 209 | Includes 2 non-active / Manual P0 canonical rows |
| Raw signals | 45 | Historical SignalForge signal rows |
| Known historical noise | 21 | 20 S25 normalization-only UPDATED + 1 S13 parser-only historical UPDATED |
| Effective business signals | 24 | Raw signals after the audited historical-noise exclusions |
| Current opportunities | 9 | 8 OPEN + 1 UNKNOWN |
| Current ICT / Telecom opportunities | 2 | Energy + MOFA |
| Immediate Telegram alert receipts | 4 | Current customer-action states already delivered |
| Immediate Telegram pending | 0 | No undelivered HIGH/REVIEW attention item at snapshot time |

The key business conclusion is that source count and source health are no longer sufficient KPIs. Only **7 of 27** active sources have demonstrated effective business-signal yield so far: 4 `ACTIONABLE_PROVEN` and 3 `SIGNAL_PROVEN`. Eighteen are still `BASELINE_ONLY`, one has only historical normalization noise, and one is currently empty. Observation windows are only about 0.6–8.5 days, so this is not evidence for pruning before the existing 30-day gate.

## 2. Last-24-hour acquisition activity

Read-only Business Digest snapshot at `2026-09-11T01:52:39Z` reported:

| Metric | Last 24h |
| --- | ---: |
| Sources polled | 27 / 27 |
| Sources changed | 3 |
| Scheduler source runs | 1,330 |
| Evidence fetched | 1,581 |
| Items parsed | 2,995 |
| Tender items parsed | 2,578 |
| Records changed | 34 |
| NEW signals | 0 |
| UPDATED signals | 0 |
| Total business signals | 0 |
| Immediate Telegram alerts | 0 |

This is not a contradiction: source pages and canonical records can change or be re-observed without producing a new customer-relevant signal. SignalForge deliberately separates acquisition churn from business-signal yield.

Cumulative database counters at the same production baseline were:

- `acquisition_requests=7219`
- `acquisition_attempts=7219`
- `evidence_envelopes=7197`
- `processing_records=7129`
- `scheduler_runs=6012`
- `canonical_items=209`
- `signals=45`
- `recovery_backlog=0`

## 3. Health: current failures vs historical failures

`status` reports `failed_runs=33`, but this is a cumulative historical counter and must not be read as 33 live failures.

The preceding 24 hours contained **one FAILED scheduler row**: S35 DAST at `2026-09-10T23:55:25Z`, caused by an issuer HTTP read timeout. S35 subsequently returned to successful polling and was GREEN at the assurance snapshot, with latest success `2026-09-11T01:40:14Z` and `consecutive_failures=0`.

Current operational state:

- SignalForge health: `GREEN`.
- Current non-GREEN sources: `0`.
- Recovery backlog: `0`.
- All 27 sources have recent successful reconciliation.
- S40 Labour is an important nuance: overall source health is GREEN, but parse health is `UNKNOWN / PARSE_SAMPLE_INSUFFICIENT` because the current issuer page yields zero qualifying business rows. This is treated as an empty observation source, not as a parser failure.

## 4. Business-yield scorecard

### Proven actionable sources

| Source | Effective signals | Current opportunities | TG alerts | Current state |
| --- | ---: | ---: | ---: | --- |
| S38 Ministry of Industry | 6 | 6 | 1 | `ACTIONABLE_PROVEN` |
| S26 DOMS | 2 | 1 | 1 | `ACTIONABLE_PROVEN` |
| S39 Ministry of Energy | 1 | 1 | 1 | `ACTIONABLE_PROVEN` |
| S30 MOFA | 1 | 1 | 1 | `ACTIONABLE_PROVEN` |

### Proven signal sources without a current opportunity

| Source | Effective signals | Current opportunities | TG alerts | Interpretation |
| --- | ---: | ---: | ---: | --- |
| S13 MPT | 10 | 0 | 0 | Highest effective-signal contribution; no currently open qualified opportunity |
| S20 MOEP | 3 | 0 | 0 | Signal-producing but no current qualified opportunity |
| S08A Customs Auction | 1 | 0 | 0 | Proven selective contribution |

### Important zero-yield observations

- **S41 MYTEL:** 15 canonical RFP identities, 0 effective signals, 0 current opportunities, 0 TG alerts. It had only about 0.57 day of observation at this snapshot; this is a strategic watch source, not evidence of poor value.
- **S25 MONPIFER:** 20 raw signals are all audited historical normalization noise; effective yield is 0 (`NOISE_ONLY_HISTORY`).
- **S40 Labour:** 0 canonical, 0 signals (`EMPTY`) after about 2.4 days; keep observing to the 30-day gate unless concrete evidence changes the decision.
- The remaining zero-yield sources are `BASELINE_ONLY`; they are not automatically candidates for deletion because most have less than one week of production history.

## 5. Current opportunity book

| Priority | Canonical key | Issuer / scope | Deadline | Assurance |
| --- | --- | --- | --- | --- |
| HIGH / ACT_NOW | `industry:1022` | Ministry of Industry — Chemical (8 types) | **2026-09-11 16:00** | A-grade, explicit official HTML deadline |
| HIGH / PRIORITIZE | `energy:235` | Ministry of Energy — 11 packages; 4 ICT/Telecom focus refs | **2026-09-18 13:00** | A-grade, official HTML + text-native PDF |
| HIGH / PRIORITIZE | `mofa:59800` | MOFA — Data Server + Windows Server Software | **2026-09-18 16:30** | A-grade, official HTML + text-native PDF |
| MEDIUM | `industry:1034` | Heavy Machinery & Equipment renovation, 10 jobs | 2026-09-14 16:00 | A-grade; expected to enter <=72h urgency window later on 2026-09-11 |
| MEDIUM | `industry:1037` | Environmental-control laboratory apparatus | 2026-09-22 16:00 | A-grade |
| MEDIUM | `industry:1036` | Chemical Reagent + Sample Gas | 2026-09-24 16:00 | A-grade |
| MEDIUM | `industry:1039` | Lubricants + electrical/mechanical spare parts | 2026-09-25 16:00 | A-grade |
| MEDIUM | `industry:1035` | Refractory / Castable / Consumables / Scrap | 2026-10-02 16:00 | A-grade |
| REVIEW | `doms:12735` | DOMS — 8DMS/9DMS/10DMS procurement bundle | UNKNOWN | B-grade / partial; deadline not trustworthy from current HTML/PDF evidence |

Customer-action priority at the snapshot is therefore clear: the Industry chemical tender closes **today at 16:00 Yangon**; Energy and MOFA are the two current ICT-relevant high-priority opportunities; DOMS remains a deliberate human-review item rather than receiving a guessed deadline.

## 6. MPT / MYTEL / ATOM strategic coverage

Network-backed Auditor v1 returned `PASS / findings=0`.

### MPT — S13

- Seven-day bounded sitemap reconciliation: PASS.
- Recent sitemap pages checked: 1.
- Tender-like pages missing from canonical: 0.
- Page fetch errors: 0.
- Business history: 16 canonical rows, 11 raw signals, 1 known parser-only historical noise row, **10 effective signals**.
- Current qualified opportunities: 0.

This means the bounded recent MPT public tender surface is internally reconciled; it does **not** prove that MPT has no private, invitation-only, unpublished, or otherwise unobserved procurement.

### MYTEL — S41

- Official identities found: 15.
- Canonical identities: 15.
- Missing: 0.
- Bounded reconciliation: PASS.
- Current signals/opportunities: 0 / 0.

S41 is therefore coverage-complete against the currently defined bounded Viettel Global MYTEL feed, but it has not yet demonstrated production yield in its very short observation window.

### ATOM — S42 trigger

- Official sitemap trigger result: `NO_TRIGGER`.
- Candidate procurement URLs: 0.

This does **not** mean ATOM has no procurement activity. It means there is still no qualifying anonymous public procurement surface that justifies creating S42. Credentialed/private supplier systems remain outside this audit unless separately authorized.

## 7. Integrity assurance matrix

| Failure class | Current assurance | Result / boundary |
| --- | --- | --- |
| Persistent non-GREEN source | Internal health checked | 27 checked, 0 non-GREEN |
| Missed new MPT/MYTEL item | Bounded independent reconciliation | S13 PASS; S41 15/15 PASS |
| New ATOM public procurement surface | Official sitemap trigger | `NO_TRIGGER`, 0 candidate URLs |
| Wrong deadline accepted | Evidence anomaly checks | 174 tenders checked; 134 have deadlines; 0 declared conflicts / 0 suspects; official deadlines are **not independently revalidated for every row** |
| False signal emitted | Recent internal trace | 24h signal count is 0; historical false-signal proof is incomplete |
| Duplicate Telegram push | Receipt integrity | 4 receipts checked, 0 anomalies; provider-side duplicate delivery is not externally observable |
| Missed high-value tender globally | Not provable from internal system alone | `NOT_PROVEN_GLOBALLY` |

The Auditor contract correctly reports `external_completeness=NOT_PROVEN` and `coverage_semantic_independence=PARTIAL`. MPT still uses the same `Reference No + Project Name` tender predicate family as production; MYTEL independently re-extracts official reference identity but does not independently prove all procurement semantics.

## 8. Telegram delivery state

Immediate Alert delivery uses success-receipt dedup. The four current delivery receipts are:

1. `industry:1022` — ACT_NOW / HIGH — Telegram provider message `3`.
2. `energy:235` — PRIORITIZE / HIGH — provider message `4`.
3. `mofa:59800` — PRIORITIZE / HIGH — provider message `5`.
4. `doms:12735` — REVIEW — provider message `6`.

A live `telegram-deliver --dry-run` returned `pending_count=0`, so there was no currently undelivered immediate attention state.

Daily Business Digest uses a separate once-per-Myanmar-calendar-day receipt. Before the scheduled 2026-09-11 run, the read-only database contained one digest receipt only: `2026-09-10 / telegram-business-digest / provider message 7 / sent_at 2026-09-10T16:48:42.427867Z`. A 2026-09-11 pre-schedule dry-run correctly returned `pending_count=1`.

### 2026-09-11 08:30 scheduled Digest gate

**Pending final live verification in this report branch.** The production timer was enabled/active and scheduled for `2026-09-11 08:30:04 +0630`. Final report closure must confirm service success and the 2026-09-11 success receipt without manually sending the Digest.

## 9. Decision

Production assurance is **PASS WITH EXPLICIT COMPLETENESS LIMITS**.

What can be asserted now:

- SignalForge is running on the expected Bangkok release and its three production timers are active.
- All 27 monitored production sources are currently GREEN with no recovery backlog.
- The system's business funnel is observable and separates raw acquisition churn from business yield.
- Seven sources have demonstrated effective business yield; four currently produce actionable opportunities.
- MPT and MYTEL pass their bounded reconciliation checks; ATOM has no current public-surface trigger.
- Current immediate Telegram attention has no pending delivery; receipt integrity shows no internal duplicate anomaly.

What must **not** be asserted:

- that SignalForge globally covers every Myanmar procurement surface;
- that zero Auditor findings proves zero missed tender;
- that every parsed deadline has been independently revalidated from a second semantic method;
- that Telegram's provider never duplicated delivery outside SignalForge's receipt visibility;
- that low-yield sources should be pruned before their observation gate.

The next optimization should therefore be driven by **decision value and real miss/noise evidence**, not by increasing source count or adding more infrastructure.
