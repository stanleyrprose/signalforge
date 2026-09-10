# Telegram Time-Based Urgency Escalation Audit — 2026-09-10

## Result

**PASS — no runtime change required.**

SignalForge already supports customer notifications when an existing opportunity becomes urgent solely because time advances, even if the issuer publishes no new page and no new SignalForge signal is created.

## Mechanism

Qualification v1 recalculates urgency at read time from the current clock and the canonical deadline. An OPEN/A opportunity becomes `URGENT` when remaining time is `<=72h`; an otherwise non-strategic A-grade opportunity therefore moves from `MEDIUM` to `HIGH` at that boundary.

`business_briefing()` converts `URGENT` attention items to `ACT_NOW`.

Telegram deduplication includes `attention_action` in the delivery key:

```text
channel | canonical_key | latest_signal_id | attention_action
```

Therefore an unchanged signal can legitimately produce a new delivery when its customer action changes. The new `ACT_NOW` delivery is then deduplicated after a successful receipt.

## Existing unit behavior

The existing `test_action_upgrade_with_same_signal_is_delivered_once` already proves that the same signal can be delivered again when `PRIORITIZE` changes to `ACT_NOW`, then deduplicates on repetition.

## New end-to-end regression

This audit adds `test_deadline_crossing_72h_escalates_same_signal_without_source_update`.

The test creates a real signal-backed S38 opportunity with deadline `2026-09-14 16:00 Myanmar` and a fixed signal id. It runs the real qualification -> opportunities -> briefing -> Telegram path at two times:

- `2026-09-11 15:59 Myanmar`: more than 72h remains, so the opportunity is MEDIUM and no Telegram message is sent;
- `2026-09-11 16:01 Myanmar`: less than 72h remains, the same signal becomes HIGH/URGENT/ACT_NOW and is sent once;
- a repeated call at the same later time is deduplicated.

Telegram targeted suite after the addition: `11 passed`.

Full repository suite: `264 passed`.

## Production live future-time dry-run

Production runtime during the audit:

`3700e675327cd599797fc0eaef8ddb8d0e289005`

Current production opportunity `industry:1034` closes at `2026-09-14 16:00 Myanmar` and is currently MEDIUM before the 72h threshold.

A read-only future-time dry-run at `2026-09-11 16:01 Myanmar` returned:

```text
pending_count = 1
industry:1034 ACT_NOW HIGH URGENT
a0edb802-d525-42cf-96e3-a9e5930e3d02
```

The `latest_signal_id` remained unchanged. Delivery receipts were `4` before and `4` after the dry-run, proving no write occurred.

## Timer cadence

Bangkok production timer:

```text
signalforge-telegram-deliver.timer
OnCalendar=*-*-* *:0/5:45 UTC
RandomizedDelaySec=10s
AccuracySec=1s
```

Telegram delivery is therefore evaluated every five minutes, with at most the configured small randomized delay, independently of whether a source publishes a new event.

## Decision

No feature change is necessary.

Do not add a second deadline scheduler, synthetic urgency signals, periodic canonical rewrites or reminder rows. The existing read-time qualification + action-sensitive delivery key + five-minute Telegram timer is sufficient and simpler.

No BKK deployment is required for this audit because only regression coverage and documentation are added.
