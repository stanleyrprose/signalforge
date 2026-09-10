# Business Digest v1 Production Closure — 2026-09-10

## Why this slice existed

SignalForge had become technically observable (`PASS/GREEN`, source health, acquisition evidence, signals, opportunities and Telegram Attention delivery), but the operator still could not answer the simplest business questions from one output: how many sources are being monitored, how much changed, how many useful opportunities exist, what was sent to Telegram, and what was filtered out. The prior delivery channel was intentionally an immediate Attention channel, not a business-output report.

Business Digest v1 adds that missing product layer without relaxing the immediate Alert policy.

## Production business funnel at rollout

- Monitored active sources: **27**
- Canonical items: **209**
- Raw signals: **45**
- Effective business-signal accounting from the prior portfolio audit: **24** (`45 - 20` known S25 normalization-noise UPDATED rows `- 1` known S13 parser-only historical UPDATED)
- Current opportunities: **9** = `8 OPEN + 1 UNKNOWN`
- Priority: **3 HIGH + 5 MEDIUM + 1 REVIEW**
- Immediate Telegram Attention items already delivered: **4**
- MEDIUM watchlist: **5**
- First daily Business Digest: successfully delivered as Telegram provider message **7**

This funnel is the primary business-facing acceptance metric. `raw signals` are audit/event rows; they must not be presented as equivalent to useful customer messages.

## Product contract

Two Telegram surfaces now coexist:

1. **Immediate Attention** — existing `telegram-deliver`; HIGH/REVIEW only, with time-driven MEDIUM -> HIGH/ACT_NOW escalation preserved.
2. **Daily Business Digest** — new `telegram-digest`; one report per Myanmar calendar day, including current Attention and a compact MEDIUM watchlist summary.

The Digest reports:

- source coverage and health;
- rolling 24-hour scheduler/source/change/evidence/parse/signal activity;
- current opportunity and priority counts;
- immediate-Telegram delivery counts;
- the current Attention shortlist;
- MEDIUM Watchlist count and its non-immediate policy;
- Auditor status;
- bounded MPT/MYTEL reconciliation and ATOM surface status;
- cumulative canonical/signal totals.

It does **not** alter source/parser/canonical/qualification semantics or the immediate Alert delivery identity.

## Implementation

- `signalforge/business_digest.py` — structured digest, Telegram rendering and once-per-day delivery.
- CLI: `business-digest`, `telegram-digest [--dry-run] [--no-network]`.
- Schema **v7** adds only `digest_delivery_receipts` with `UNIQUE(channel,digest_date)`.
- Digest receipt identity is independent from per-signal `delivery_receipts`.
- New systemd service/timer use the existing Telegram credential file and run as dedicated `signalforge`.
- Timer: `OnCalendar=*-*-* 02:00:00 UTC`, equivalent to **08:30 Myanmar**, `Persistent=true`, bounded randomized delay.
- Future release deployment preserves the digest timer's previous enabled state and drains the digest service during deployment.

## Tests and CI

- Digest/contract/DB targeted: **11 passed**.
- Full suite: **280 passed**.
- `git diff --check`: PASS.
- PR #146 Actions run **34504021465**: PASS.
- PR #146 squash merge / production runtime: `40ad4f4d4e2f935e9ed77cceb044f9bf8d61240a`.
- Archive SHA256: `b648171f22148e2bf61cff9d211d823a4099d6a46f9000d54f162a2801f834fa`.
- Rollback: `b19a775e8413181206b3c4e0adb68fd03f0be257`.

## First production dry-run

The first real production `telegram-digest --dry-run` returned:

- `27 monitored / 27 GREEN / 0 degraded`;
- `27` sources polled in the rolling 24h window;
- `4` sources changed;
- `35` records changed;
- `1329` scheduler runs;
- `1578` evidence artifacts fetched;
- `2807` items parsed / `2378` tenders parsed;
- `1` signal in the 24h window: `NEW=0 / UPDATED=1`, source S13;
- `9` current opportunities: `HIGH=3 / MEDIUM=5 / REVIEW=1`;
- `4` cumulative immediate Telegram alerts and `0` in that particular rolling 24h window;
- Auditor `PASS / finding_count=0`;
- MPT missing `0`; MYTEL `15/15 / missing0`; ATOM `NO_TRIGGER`;
- cumulative `209 canonical / 45 signals`.

The rendered message explicitly showed the four current Attention items and stated that the five MEDIUM items are valid Watchlist opportunities that do not generate immediate alerts until urgency/strategic policy promotes them.

## One-time deployment bootstrap nuance

The exact runtime was deployed using the **previous active release's deploy script**. That old script could not know about the newly added digest service/timer, so immediately after runtime deployment the digest timer was correctly observed as `not-found`. No Digest had been sent.

The service and timer were then installed directly from the exact deployed release under `/srv/signalforge/active/systemd/`, `systemctl daemon-reload` and `systemd-analyze verify` passed, and the timer remained deliberately `disabled/inactive` until the production dry-run was inspected. This is a one-time bootstrap condition. Future deployments use the new deploy script and preserve the digest timer state.

## First real Telegram delivery

After the production message was reviewed, `signalforge-telegram-digest.service` was started once manually. It returned `Result=success / ExecMainStatus=0`. The durable receipt is:

- `digest_date=2026-09-10`
- `channel=telegram-business-digest`
- `provider_message_id=7`
- `sent_at=2026-09-10T16:48:42.427867Z`

A second same-day `telegram-digest --dry-run --no-network` returned `deduplicated=true / pending_count=0 / sent_count=0`, proving same-day replay suppression.

The timer was then enabled. Its first observed next elapse was **2026-09-11 08:30:24 +0630**. Acquisition, immediate Telegram Alert, and Business Digest timers are all enabled/active.

## Final production gate

- Runtime: `40ad4f4d4e2f935e9ed77cceb044f9bf8d61240a`
- `status=PASS / signalforge_health=GREEN`
- `canonical=209 / signals=45 / recovery_backlog=0`
- `audit=PASS / findings=0`
- immediate Telegram `pending=0`
- schema `7`
- digest receipts `1`
- `PRAGMA quick_check=ok`
- acquisition timer active
- immediate Alert timer active
- daily Digest timer active

## Product interpretation

SignalForge business output must now be reviewed through the funnel, not by source health alone:

`Sources -> Canonical -> Signals -> Current Opportunities -> Attention / Watchlist -> Telegram Alert + Daily Digest`

A source being GREEN proves technical operation, not business yield. A raw signal proves a recorded change, not customer value. The daily Digest is therefore the default operator-visible business-yield surface, while Auditor remains the assurance surface and immediate Telegram remains the interruption/attention surface.
