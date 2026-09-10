# Source Business Yield Scorecard v1 Production Closure — 2026-09-10

## Purpose

Health alone does not answer whether a source creates useful business intelligence. Scorecard v1 makes the complete active-source funnel visible to the operator and AI without modifying source execution.

## Production summary

- Active monitored sources: **27**
- GREEN: **27**
- Canonical from active sources: **207**
- Non-active/manual canonical: **2** (S15A MPA Manual P0)
- Database canonical total: **209**
- Raw signals: **45**
- Known historical noise: **21**
- Effective business signals: **24**
- Current opportunities: **9**
- Current ICT/Telecom opportunities: **2**
- Immediate Telegram alerts delivered: **4**
- Yield states: **4 ACTIONABLE_PROVEN / 3 SIGNAL_PROVEN / 18 BASELINE_ONLY / 1 NOISE_ONLY_HISTORY / 1 EMPTY**

The 21 known-noise rows are accounting exclusions only: twenty audited S25 normalization-only UPDATED rows plus one exact S13 parser-only historical UPDATED signal. They remain in the immutable signal history.

## Two-axis model

`Strategic Tier` and `Observed Yield` are intentionally separate. A source can be strategically essential but temporarily quiet (for example S41 MYTEL), or context-oriented but still produce a real actionable opportunity (for example S26 DOMS). No single opaque score is used.

Observed Yield states:

- `ACTIONABLE_PROVEN`: current opportunity or successful TG contribution exists.
- `SIGNAL_PROVEN`: effective signal exists but no current opportunity/TG contribution.
- `BASELINE_ONLY`: canonical inventory exists but no effective signal yet.
- `NOISE_ONLY_HISTORY`: raw signals exist but all are already-audited historical noise.
- `EMPTY`: no canonical inventory yet.

## Full 27-source live scorecard

| Source | Name | Strategic Tier | Observed Yield | Canonical | Effective Signals | Current Opps | TG Alerts | Obs. Days | Recommendation |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| S38 | Ministry of Industry Procurement Announcements | CORE | ACTIONABLE_PROVEN | 8 | 6 | 6 | 1 | 2.15 | KEEP_PROVEN |
| S26 | DOMS Medical Procurement Opportunities | CONTEXT | ACTIONABLE_PROVEN | 3 | 2 | 1 | 1 | 6.10 | KEEP_PROVEN |
| S39 | Ministry of Energy Collective Tenders | CORE | ACTIONABLE_PROVEN | 4 | 1 | 1 | 1 | 2.06 | KEEP_PROVEN |
| S30 | Ministry of Foreign Affairs Procurement Invitations | CORE | ACTIONABLE_PROVEN | 2 | 1 | 1 | 1 | 3.58 | KEEP_PROVEN |
| S13 | MPT Tender Information | CORE | SIGNAL_PROVEN | 16 | 10 | 0 | 0 | 8.09 | KEEP_STRATEGIC |
| S20 | MOEP Main Tender Hub | CORE | SIGNAL_PROVEN | 8 | 3 | 0 | 0 | 6.67 | KEEP_STRATEGIC |
| S08A | Myanmar Customs Auction Announcements | CONTEXT | SIGNAL_PROVEN | 5 | 1 | 0 | 0 | 6.40 | OBSERVE_TO_30D |
| S41 | MYTEL Procurement Invitations via Viettel Global | STRATEGIC_WATCH | BASELINE_ONLY | 15 | 0 | 0 | 0 | 0.21 | KEEP_STRATEGIC |
| S34 | Posts and Telecommunications Department Open Tenders | STRATEGIC_WATCH | BASELINE_ONLY | 6 | 0 | 0 | 0 | 3.29 | KEEP_STRATEGIC |
| S21 | Myanma Railways Tenders | STRATEGIC_WATCH | BASELINE_ONLY | 45 | 0 | 0 | 0 | 6.97 | KEEP_STRATEGIC |
| S22 | Inland Water Transport Tenders | STRATEGIC_WATCH | BASELINE_ONLY | 4 | 0 | 0 | 0 | 6.69 | KEEP_STRATEGIC |
| S16 | YCDC Engineering Department (Building) Tender Opportunities | STRATEGIC_WATCH | BASELINE_ONLY | 5 | 0 | 0 | 0 | 3.34 | KEEP_STRATEGIC |
| S27 | Ministry of Border Affairs Tender Opportunities | STRATEGIC_WATCH | BASELINE_ONLY | 6 | 0 | 0 | 0 | 2.09 | KEEP_STRATEGIC |
| S35 | Department of Advanced Science and Technology Tenders | STRATEGIC_WATCH | BASELINE_ONLY | 6 | 0 | 0 | 0 | 3.20 | KEEP_STRATEGIC |
| S05A | Ministry of Commerce Trade Notifications | CONTEXT | BASELINE_ONLY | 3 | 0 | 0 | 0 | 6.61 | OBSERVE_TO_30D |
| S07 | Myanmar Customs Notifications | CONTEXT | BASELINE_ONLY | 5 | 0 | 0 | 0 | 6.50 | OBSERVE_TO_30D |
| S12 | IRD Business Tax Announcements | CONTEXT | BASELINE_ONLY | 9 | 0 | 0 | 0 | 6.36 | OBSERVE_TO_30D |
| S10 | DICA Company and Investment Announcements | CONTEXT | BASELINE_ONLY | 12 | 0 | 0 | 0 | 6.34 | OBSERVE_TO_30D |
| S29 | DWIR Waterway and River Works Tenders | OBSERVATION | BASELINE_ONLY | 4 | 0 | 0 | 0 | 5.78 | OBSERVE_TO_30D |
| S37 | Ministry of Information Ministerial Office Procurement Announcements | OBSERVATION | BASELINE_ONLY | 1 | 0 | 0 | 0 | 3.10 | OBSERVE_TO_30D |
| S36 | Department of Agriculture Procurement Announcements | OBSERVATION | BASELINE_ONLY | 6 | 0 | 0 | 0 | 3.15 | OBSERVE_TO_30D |
| S31 | Ministry of Ethnic Affairs Procurement Invitations | OBSERVATION | BASELINE_ONLY | 9 | 0 | 0 | 0 | 3.55 | OBSERVE_TO_30D |
| S32 | Myanma Timber Enterprise Procurement Invitations | OBSERVATION | BASELINE_ONLY | 2 | 0 | 0 | 0 | 3.46 | OBSERVE_TO_30D |
| S33 | Ministry of Cooperatives and Rural Development Tenders | OBSERVATION | BASELINE_ONLY | 5 | 0 | 0 | 0 | 3.44 | OBSERVE_TO_30D |
| S28 | Department of Fisheries Open Tenders | OBSERVATION | BASELINE_ONLY | 8 | 0 | 0 | 0 | 6.04 | OBSERVE_TO_30D |
| S25 | MONPIFER Ministry Tenders | OBSERVATION | NOISE_ONLY_HISTORY | 10 | 0 | 0 | 0 | 6.18 | OBSERVE_TO_30D |
| S40 | Ministry of Labour Procurement Invitations | OBSERVATION | EMPTY | 0 | 0 | 0 | 0 | 2.03 | OBSERVE_TO_30D |

## Interpretation

The currently proven actionable sources are S38 Industry, S26 DOMS, S39 Energy and S30 MOFA. S13 MPT, S20 MOEP and S08A Customs Auction have proven effective signal production but currently contribute no open opportunity or Telegram alert. S41 MYTEL is strategically important but was only ~0.21 days into production at this snapshot; zero yield is therefore not negative evidence. S40 Labour is EMPTY but had only ~2 days of observation.

The portfolio is too young for pruning: observation windows range from roughly **0.2 to 8.1 days**, well below the default 30-day gate. `KEEP_PROVEN`, `KEEP_STRATEGIC`, and `OBSERVE_TO_30D` are recommendations only; no runtime role/priority/polling changes were made.

## Implementation and verification

- CLI: `signalforge source-scorecard --window-days 30`
- Closed provider manifest advertises `signalforge-source-scorecard -> source-scorecard`.
- Scorecard is read-only and calls network-disabled Auditor health checks.
- Targeted scorecard+contract tests: **9 passed**.
- Full suite: **285 passed**.
- Pre-merge production-copy gate exactly reproduced the production summary.
- PR #148 Actions run **34506868912**: PASS.
- Exact runtime: `bb8ed3146c69b7727d8143f06f3467c49f16ec33`.
- Archive SHA256: `ada3348483a78baa09b7f25196bc4e5ba88da303f04c9516288f89e4ecd72c1e`.
- Rollback: `40ad4f4d4e2f935e9ed77cceb044f9bf8d61240a`.

## Final production gate

Live `source-scorecard` returned the exact summary above. The manifest contains the new read verb. SignalForge remains `PASS/GREEN / 209 canonical / 45 signals / backlog0`; immediate Telegram dry-run pending is 0; same-day Business Digest is deduplicated; DB quick_check is ok. Acquisition, immediate Alert and daily Digest timers are all active, with the next Digest observed at `2026-09-11 08:30:01 +0630`.

No source refresh, parser/canonical migration, qualification change, Telegram policy change, DB schema change, Browser/Provider/Worker topology change, Beijing role, or automated pruning was introduced.
