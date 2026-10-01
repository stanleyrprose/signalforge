# Tender Radar Pilot Feedback Production Closure — 2026-10-01

## Scope

Close the Telegram feedback loop for the Tender Radar pilot on Bangkok production and record the live failure discovered during real user feedback.

The production goal is:

`Official Tender -> Business Profile -> Chinese Telegram card -> customer feedback -> pilot_feedback_events -> pilot-report`

No dashboard, billing, public API, autonomous bidding, or multi-step CRM workflow is part of this closure.

## Release identity

### Feature rollout

- PR #276: `feat: add Telegram feedback loop for tender pilots`
- reviewed head: `3e27c6c298a423cb90f98b38f22a95c6f10f1fa1`
- merged release: `fc1ea97dbfa3cf576f1b81dbb44a8e8b4f57dd24`
- release archive SHA256: `4b61143827ad8613ee2590b2c5edb5b162a6761925e479b819c9975ba7999cfc`
- previous Bangkok release: `abd5eb30d83c15724e8b812a79f5eaa3072455a5`
- schema after rollout: v12

### Live hotfix

A real Telegram callback exposed an acknowledgement/offset ordering bug:

1. customer feedback was durably written to `pilot_feedback_events`;
2. the callback had been sitting long enough that Telegram rejected `answerCallbackQuery` with HTTP 400;
3. the exception aborted the collector before `telegram_update_state` persisted the update offset;
4. the same update could therefore be replayed indefinitely.

Hotfix:

- PR #277: `fix: make Telegram feedback polling durable and responsive`
- reviewed head: `a8928aed042d7206ffd9013d898e651c030253f3`
- merged production release: `8d972e18dc0d07330e5728acd4f204909c25fe97`
- release archive SHA256: `72690456a4dc2c5a52df14b84e5a864a984872858a712efcd98c912e2555d07f`
- previous rollback release: `fc1ea97dbfa3cf576f1b81dbb44a8e8b4f57dd24`

Both release archives were SHA256-verified equal on Mac and Bangkok before deployment.

## Implementation

Profile-attributed Telegram deliveries expose:

- 👍 Relevant -> `RELEVANT`
- 👎 Not Relevant -> `NOT_RELEVANT`
- 🚀 Took Action -> `ACTION_TAKEN`

Feedback is written into the existing `pilot_feedback_events` ledger. No parallel feedback database or duplicate KPI model was introduced.

The callback collector:

- fails closed when a Telegram webhook is configured;
- validates the callback against a real `pilot_delivery_receipts` row;
- validates the Telegram message ID against the delivery receipt;
- writes feedback using the existing `record_pilot_feedback()` contract;
- persists Telegram update offsets in `telegram_update_state`;
- treats `answerCallbackQuery` as UX acknowledgement only;
- reports an acknowledgement failure as degraded UX, but does not roll back durable feedback or prevent offset persistence.

## Runtime

Bangkok active release:

`/srv/signalforge/active -> /srv/signalforge/releases/8d972e18dc0d07330e5728acd4f204909c25fe97`

Database:

- `PRAGMA quick_check = ok`
- schema version = 12
- `telegram_update_state` exists
- existing pilot attribution preserved

Telegram:

- Bot API reachable
- active webhook = none
- existing owner delivery timer remains unchanged
- feedback collector is enabled and active

Collector runtime was changed from a one-minute fixed poll to:

- bounded Telegram `getUpdates` long-poll timeout: 20 seconds
- `OnUnitInactiveSec=2s`
- oneshot service model retained
- no permanent daemon introduced

Observed post-hotfix cycles repeatedly returned:

- `Result=success`
- `ExecMainStatus=0`
- `failed_count=0`
- `ack_failed_count=0`
- `status=PASS`

## Live user acceptance

The existing self-pilot is:

`pilot-self-telecom-ict-power`

Attributed Tender deliveries:

- `moep:7157:2026-09-11`
- `moep:7197:2026-09-30`

Both historical Telegram messages were updated in place to carry the new inline feedback buttons; no fake Tender or duplicate customer message was created.

Real Telegram feedback was received for both Tender deliveries:

- both currently resolve to `RELEVANT`;
- `recorded_by` is a real Telegram callback actor rather than the previous manual `self-pilot` seed;
- the two prior `CLICKED` and `WOULD_PAY` pilot-learning events remain preserved.

Current pilot report:

- unique tenders delivered: 2
- relevance response rate: 100%
- relevant rate: 100%
- engagement response rate: 100%
- clicked rate: 100%
- pay-intent response rate: 100%
- would-pay rate: 100%
- action rate: 0%

No `ACTION_TAKEN` callback has been received. The system must not infer or fabricate customer action.

## Verification

Before PR #277 merge:

- focused feedback/contract tests: 11/11 PASS
- full test suite: 607/607 PASS
- `python -m compileall -q signalforge tests`: PASS
- `sh -n deploy/deploy-signalforge-release.sh`: PASS
- `git diff --check`: PASS

After deployment:

- active SHA exact-match: PASS
- DB quick-check: PASS
- schema v12: PASS
- feedback timer enabled/active: PASS
- repeated long-poll cycles: PASS
- no callback replay observed after Telegram queue drained
- no additional Tender delivery was fabricated for testing

## Product meaning

The engineering loop is now sufficient for a paid pilot:

`Tender -> match -> Telegram -> relevance feedback -> action feedback -> pilot-report`

The next constraint is no longer callback plumbing. It is commercial evidence from external design partners.

The next validation target is 5–10 manually onboarded companies. The operational North Star remains customer action caused by relevant Tender intelligence, not source count or raw Signal count.

## Boundary

This closure does not prove:

- that an external customer will pay;
- that one relevant Tender will lead to a bid;
- that a bid will convert into revenue;
- that the system needs a public SaaS dashboard;
- that the current profile schema is final.

Those are pilot-stage commercial questions, not engineering facts.
