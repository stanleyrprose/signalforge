# Telegram Delivery v1 — Credential Gate — 2026-09-09

## Result

> **IMPLEMENTED / DEPLOYED / SAFE-DISABLED / CREDENTIAL GATE**

SignalForge Telegram Delivery v1 is implemented, CI-verified and deployed to Bangkok, but outbound Telegram delivery remains intentionally disabled until the operator configures the bot token and target chat ID locally on Bangkok.

## Exact production release

SignalForge PR #110 merged as:

`489d05f5b36189dc8292b51032edf49e0e102b4d`

Immediate rollback target:

`a61f9f7e7ef0af9be22bafd778f17bfe5f3a5ebc`

Deployment archive SHA256, identical locally and on Bangkok:

`ccc50cab9cee209512a8cccd7eb1c91ee24a7209893ae9833170bb350d22fceb`

## Delivery semantics

Telegram Delivery consumes only Business Briefing attention rows (`HIGH + REVIEW`). It does not deliver MEDIUM watchlist rows.

Each successful delivery receipt is identified by:

`channel + canonical_key + latest_signal_id + attention_action`

Consequences:

- the same Signal/action is not sent repeatedly every timer cycle;
- a new NEW/UPDATED Signal can be delivered even if the action remains the same;
- the same Signal can be delivered again when its action escalates, e.g. `PRIORITIZE -> ACT_NOW` as the deadline enters the 72-hour window;
- a failed Telegram request does not create a success receipt and can be retried;
- Telegram itself does not provide an exactly-once idempotency key, so the documented transport guarantee is `AT_LEAST_ONCE_WITH_SUCCESS_RECEIPT_DEDUP`.

## Schema v6

Schema v6 adds one generic table:

`delivery_receipts`

It records successful channel delivery provenance only. No canonical item or Signal is modified by delivery.

After production migration:

- schema versions: `1,2,3,4,5,6`
- canonical items: `194`
- signals: `44`
- delivery receipts: `0`
- DB quick check: `ok`

## Runtime

Installed but disabled until credential authorization:

- `signalforge-telegram-deliver.service`
- `signalforge-telegram-deliver.timer`

Timer schedule is five-minute cadence, offset after the main scheduler. The deployment preserves its prior enabled state on later releases, but first installation remains disabled because it did not previously exist.

Secret contract:

`/etc/signalforge/telegram.env`

Expected variables:

- `SIGNALFORGE_TELEGRAM_BOT_TOKEN`
- `SIGNALFORGE_TELEGRAM_CHAT_ID`

The file is not created by deployment and no token/chat ID is stored in Git.

## Tests and external gates

- targeted Telegram / contract / DB / opportunity tests: PASS
- full suite: `234 passed`
- `git diff --check`: PASS
- BKK `systemd-analyze verify` for Telegram service/timer: PASS
- BKK strict-TLS reachability to `https://api.telegram.org/`: PASS (`ssl_verify_result=0`)

Telegram Bot API transport uses `sendMessage`, HTML parse mode and disabled link preview. User-provided text is escaped before transport; messages are bounded to Telegram's 4096-character text limit.

## Production dry-run

Live production `telegram-deliver --dry-run` requires no Telegram credentials and returned exactly four pending attention events:

1. `industry:1022` — `ACT_NOW`
2. `energy:235` — `PRIORITIZE`
3. `mofa:59800` — `PRIORITIZE`
4. `doms:12735` — `REVIEW`

MEDIUM watchlist items are not pending for Telegram delivery.

## Final safe-disabled state

- active SignalForge application: `489d05f5b36189dc8292b51032edf49e0e102b4d`
- main SignalForge timer: enabled / active
- Telegram delivery timer: disabled / inactive
- Telegram secret file: absent
- overall SignalForge: PASS / GREEN
- canonical: `194`
- signals: `44`
- recovery backlog: `0`
- delivery receipts: `0`

No Telegram message has been sent by this rollout.

## Credential gate

The next production step requires explicit operator configuration of a Telegram bot token and target chat ID in the root-managed Bangkok secret file. After that gate, perform one reviewed real delivery, verify four success receipts, rerun to prove zero duplicate delivery, then enable the delivery timer and close production verification.
