# Telegram Delivery v1 — Production Closure — 2026-09-09

## Result

> **COMPLETE / PASS / PRODUCTION**

SignalForge Telegram Delivery v1 is now live on Bangkok. The delivery path consumes only Business Briefing attention rows and uses successful-delivery receipts to suppress repeat notifications.

## Exact implementation

SignalForge implementation PR #110 merged as:

`489d05f5b36189dc8292b51032edf49e0e102b4d`

Immediate application rollback target:

`a61f9f7e7ef0af9be22bafd778f17bfe5f3a5ebc`

Deployment archive SHA256:

`ccc50cab9cee209512a8cccd7eb1c91ee24a7209893ae9833170bb350d22fceb`

Full test suite before rollout: `234 passed`.

## Credential handling

Telegram credentials are stored only on Bangkok in the root-managed secret file:

`/etc/signalforge/telegram.env`

The file is `0640 root:signalforge`. The production closure does not record or expose the bot token or target chat identifier.

## First real delivery

The first real `signalforge-telegram-deliver.service` invocation completed successfully and delivered exactly four attention items:

1. `industry:1022` — `ACT_NOW`
2. `energy:235` — `PRIORITIZE`
3. `mofa:59800` — `PRIORITIZE`
4. `doms:12735` — `REVIEW`

Telegram returned message IDs `3`, `4`, `5`, and `6` respectively.

The corresponding successful receipt count became `4`.

## Idempotency proof

The delivery service was immediately executed a second time with the same business state.

Result:

- `status=PASS`
- `pending_count=0`
- `sent_count=0`
- successful Telegram receipt count remained `4`

This proves same-signal / same-attention-action repeat suppression.

Delivery identity remains:

`channel + canonical_key + latest_signal_id + attention_action`

Therefore a new Signal can notify again, and an unchanged Signal can notify again when its attention action escalates, such as `PRIORITIZE -> ACT_NOW`.

Transport semantics remain:

`AT_LEAST_ONCE_WITH_SUCCESS_RECEIPT_DEDUP`

Telegram does not expose an exactly-once idempotency key, so a narrow ambiguous transport-failure window can theoretically duplicate a message if Telegram accepted it but the success response was lost before SignalForge recorded the receipt.

## Timer activation

The production delivery timer is now enabled:

`signalforge-telegram-deliver.timer = enabled / active`

The main acquisition scheduler remains:

`signalforge-run-due.timer = enabled / active`

Telegram delivery runs on the five-minute delivery cadence after the acquisition scheduler and only sends attention events that do not already have a successful matching receipt.

## Final production state

At closure:

- active SignalForge application: `489d05f5b36189dc8292b51032edf49e0e102b4d`
- overall SignalForge: `PASS / GREEN`
- DB quick check: `ok`
- canonical items: `194`
- signals: `44`
- recovery backlog: `0`
- Telegram successful receipts: `4`
- acquisition timer: enabled / active
- Telegram delivery timer: enabled / active

The real delivery rollout changed no canonical item and created no business Signal.

## Boundary

Telegram Delivery v1 does not introduce:

- public API or public listener
- Telegram webhook
- inbound bot command processing
- arbitrary remote execution
- LLM generation inside SignalForge
- Browser or Provider changes
- Beijing dependency
- delivery of MEDIUM watchlist items

Current behavior is outbound-only, Bangkok-only, attention-only delivery.
