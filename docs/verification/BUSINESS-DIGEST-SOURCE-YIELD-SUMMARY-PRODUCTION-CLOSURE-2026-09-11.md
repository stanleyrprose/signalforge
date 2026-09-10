# Business Digest Source Yield Summary — Production Closure — 2026-09-11

## Result

> **PASS / PRODUCTION**

SignalForge daily Telegram Business Digest now exposes the Source Business Yield Scorecard summary directly in the scheduled user-facing message.

## Product reason

The system previously exposed source yield only through `signalforge source-scorecard`, while the daily Telegram Digest still showed total sources and raw signal totals. That made it too easy to confuse engineering activity with business value. This slice makes the two business-facing distinctions visible every day:

1. how many monitored sources have actually proven useful output; and
2. how many signal rows are effective business signals versus known raw/historical noise.

## User-visible output

The production render after rollout included:

`🧭 Source产出：7/27 proven · actionable 4 · signal-only 3 · baseline 18 · noise-only 1 · empty 1`

and:

`🗃 累计：209 canonical · 24 effective / 45 raw signals`

The rest of the existing Digest remained intact: 24-hour acquisition activity, current opportunities, immediate Telegram alert counts, top attention items, Watchlist, Auditor status, and telecom coverage.

## Implementation boundary

The implementation only changes the Business Digest aggregation/render layer and its tests. It reuses the production `source_scorecard(..., window_days=30)` result. It does **not** introduce another scoring implementation.

No change was made to:

- source registry role, priority or polling
- acquisition/parser/canonical/signal semantics
- qualification or attention policy
- immediate Telegram delivery identity or policy
- Digest receipt key or once-per-Myanmar-day dedup
- Digest timer cadence
- DB schema
- Browser/Provider/Worker/Control Plane topology
- Beijing role

## Verification

- Targeted Digest + Source Scorecard tests: **10 passed**.
- Full suite: **285 passed**.
- `git diff --check`: PASS before PR.
- PR #150 Actions run `34510340590`: PASS.
- Exact production runtime: `bd86efcaa5699f1aa5082459cd57882b8ffe4e73`.
- Archive SHA256: `13cb4a9592c31ac427c17d81040373c4c223c6587c14c43e5745b235ca752d05`.
- Rollback: `bb8ed3146c69b7727d8143f06f3467c49f16ec33`.

## Production gate

After deployment, live `business-digest --no-network` returned Source Yield summary:

- active sources: **27**
- yield states: `ACTIONABLE_PROVEN=4 / SIGNAL_PROVEN=3 / BASELINE_ONLY=18 / NOISE_ONLY_HISTORY=1 / EMPTY=1`
- effective business signals: **24**
- raw signals: **45**

A live `telegram-digest --dry-run --no-network` produced the intended next Digest message without sending it. The 2026-09-11 Digest was correctly `pending=1` because the scheduled 08:30 run had not yet happened. `digest_delivery_receipts` remained **1**, so previewing did not write a new receipt.

Final operational checks:

- immediate Telegram pending: **0**
- DB quick_check: **ok**
- acquisition timer: **active**
- immediate Telegram timer: **active**
- Business Digest timer: **active**
- next Digest observed: **2026-09-11 08:30:04 +0630**

The no-network preview intentionally skipped external MPT/MYTEL/ATOM reconciliation fields. Normal scheduled Digest execution still uses its default network-backed Auditor path.

## Closure

Daily Telegram output now answers not only **"did SignalForge run?"** but also **"how many monitored sources have actually proven useful, and how much of the signal history represents effective business information?"** without increasing notification noise or changing business qualification.
