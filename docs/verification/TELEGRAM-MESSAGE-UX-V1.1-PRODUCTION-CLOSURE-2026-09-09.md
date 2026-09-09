# Telegram Message UX v1.1 — Production Closure — 2026-09-09

## Result

> **COMPLETE / PASS / PRODUCTION**

Telegram Delivery now renders future SignalForge attention notifications as compact business cards while preserving all v1 delivery eligibility and dedup semantics.

## Exact implementation

PR #113 merged as:

`ff9df1af9ebf7e144b33b94aec7f6d32782a1992`

Immediate rollback target:

`489d05f5b36189dc8292b51032edf49e0e102b4d`

Deployment archive SHA256:

`7dddcc93ae218a43d2b8addfff88d0191a5da9c020ee220dfc0842d7dd1f09e6`

Tests:

- targeted Telegram tests: `8 passed`
- full suite: `235 passed`
- `git diff --check`: PASS

## Presentation changes

The renderer now uses deterministic Chinese static labels without translating or inferring issuer facts:

- `ACT_NOW -> 立即行动`
- `PRIORITIZE -> 优先关注`
- `REVIEW -> 人工复核`
- buyer, deadline, reference, why-now, scope, evidence and official-source labels are optimized for quick mobile scanning
- evidence labels are compact and explain provenance, including Provider HTML and official text PDF
- scope is collapsed and bounded to 240 characters at transport rendering time
- latest Signal type is surfaced

Official titles and business facts remain in their source language. No LLM or translation API was added.

## Production proof

Exact deployed renderer against the live production DB produced:

- `industry:1022` — 643 chars — `立即行动 / HIGH / A / INDUSTRIAL`
- `energy:235` — 581 chars — `优先关注 / HIGH / A / ICT`
- `mofa:59800` — 746 chars — `优先关注 / HIGH / A / ICT`
- `doms:12735` — 754 chars — `人工复核 / REVIEW / B / MEDICAL`

Long official URLs render as one `官方来源` link in Telegram.

## No-repeat rollout proof

The pre-existing four successful Telegram receipts remained authoritative after the renderer change. A post-deployment real delivery invocation returned:

- `status=PASS`
- `pending_count=0`
- `sent_count=0`
- Telegram receipt count remained `4`

Therefore renderer changes do not resend previously delivered business events because delivery identity remains independent of message text.

## Final production state

- active SignalForge release: `ff9df1af9ebf7e144b33b94aec7f6d32782a1992`
- acquisition timer: enabled / active
- Telegram timer: enabled / active
- overall health: `PASS / GREEN`
- DB quick check: `ok`
- canonical items: `194`
- signals: `44`
- recovery backlog: `0`
- Telegram receipts: `4`

No canonical item, Signal, qualification rule, delivery eligibility, receipt identity, timer cadence, schema, acquisition, Browser or Provider behavior changed.
