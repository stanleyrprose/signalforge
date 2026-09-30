# Tender Radar Pilot Validation Production Closure — 2026-09-30

## Purpose

Close the first sellable SignalForge Tender Radar pilot slice:

```text
official Myanmar government/SOE tender
→ canonical TENDER Signal
→ Simplified-Chinese presentation
→ deterministic Business Profile match
→ per-pilot Telegram delivery
→ official-source evidence
→ explicit customer outcome feedback
→ pilot conversion report
```

This closure does **not** create a public SaaS, automatic billing, public signup, automatic bid/no-bid decisions, or automatic tender submission.

## Product boundary

The owner/operator Telegram feed remains unchanged and continues to use the legacy owner delivery receipt path.

Paying-pilot delivery is isolated by `profile_id`:

- one official Tender Signal may be delivered once to pilot A and once to pilot B;
- rerunning the same `profile_id + canonical_key + signal_id` is idempotent;
- one pilot customer's successful receipt cannot suppress another pilot customer's delivery;
- pilot delivery is canonical Tender-only;
- manual promotions remain owner/operator-only;
- pilot metrics count only pilot-attributed deliveries, never historical owner-feed receipts.

Business Profile matching remains deterministic before LLM presentation. LLM/translation may improve the Chinese rendering but cannot create, mutate or suppress canonical tender facts.

## Code lineage

### Productization baseline

PR #261 established the pilot product surface and was already live before this tranche:

- Business Profile;
- Chinese Tender Telegram message;
- official evidence link;
- pilot MVP documentation.

Baseline production release before this closure:

`e88421475785bbf33fdaf36df264883e09527649`

### PR #262 — pilot outcome tracking

PR #262 `feat: track Tender Radar pilot outcomes`:

- merged to `main` at `db87b23730251a343ccb23040598535e57e80782`;
- GitHub Actions verify run `36673455283`: PASS;
- added schema v10 attribution fields and `pilot_feedback_events`;
- added `pilot-feedback` and `pilot-report`;
- added outcome types:
  - `ACKNOWLEDGED`;
  - `WORTH_REVIEWING`;
  - `ACTION_TAKEN`;
  - `BID_OR_QUOTE_INITIATED`;
  - `DISMISSED`.

### First production deployment attempt — safe failure

The exact `db87b23730251a343ccb23040598535e57e80782` archive matched Mac and Bangkok at:

`97473a92c248dfe577160244bef3e6f159a2b32c7df5d79ab8ce2cfd8b5a6e91`

The standard production deployment exposed a real old-schema migration defect:

`OperationalError: no such column: profile_id`

Root cause: the v10 migration attempted to create the new `delivery_receipts(profile_id,...)` index before upgrading an existing v9 `delivery_receipts` table with the new columns.

The standard deploy rollback path behaved correctly:

- active release returned to `e88421475785bbf33fdaf36df264883e09527649`;
- schema remained v9;
- SQLite `quick_check=ok`;
- all four production timers returned enabled + active;
- no lock bypass, timer bypass, forced worker termination or DB hand-edit was used.

### PR #263 — production-shaped migration repair

PR #263 `fix: migrate pilot delivery attribution safely`:

- GitHub Actions verify run `36681899606`: PASS;
- merged to `main` at `9466ba391a7b5c10fc9a3ccb5760a9342134bf36`;
- moved the profile index creation after additive column migration;
- added a production-shaped v9 → current migration regression test preserving a legacy delivery row.

Local validation before merge:

- targeted migration/pilot/Telegram suite: 24/24 PASS;
- full suite: 548/548 PASS;
- compileall / registry JSON / shell syntax / `git diff --check`: PASS.

Exact release archive SHA256, identical on Mac and Bangkok:

`3ded171b734275ed5dac7e348502246bb299d06f016e11e21b87c22505585cde`

Deployment succeeded. Schema v10, `quick_check=ok`, SignalForge PASS/GREEN and all four timers enabled + active.

## Live product audit after v10

The first live `pilot-report` correctly revealed a second, product-level problem:

- historical owner feed contained 41 delivery receipts / 37 unique tenders;
- those owner receipts appeared in the pilot denominator even though no real pilot customer had been onboarded;
- the legacy Telegram dedupe identity was global per channel/canonical/signal, so using the same table for multiple pilots would allow pilot A's successful delivery to suppress pilot B's copy of the same Tender Signal.

This was not accepted as a paying-pilot implementation.

No synthetic pilot customer, fake receipt, or fake feedback event was inserted to make the report non-zero.

### PR #264 — multi-pilot isolation

PR #264 `fix: isolate multi-profile pilot deliveries`:

- GitHub Actions verify run `36682869883`: PASS;
- merged to `main` at `2500d6f044c1f3dad985f15fc2e2f207d39199bf`;
- schema bumped to v11;
- added additive `pilot_delivery_receipts`;
- pilot dedupe identity is `channel + profile_id + canonical_key + signal_id`;
- legacy owner feed keeps using `delivery_receipts`;
- `pilot-report` reads only `pilot_delivery_receipts`;
- `pilot-feedback` requires a real pilot-attributed receipt;
- pilot delivery excludes manual promotions;
- documented manual operator delivery per customer chat/profile.

Validation before merge:

- targeted DB/pilot/Telegram/Assurance suite: 46/46 PASS;
- full suite: 550/550 PASS;
- compileall / registry JSON / deploy shell syntax / `git diff --check`: PASS.

A dedicated regression test proves:

- pilot A receives a Tender Signal once;
- pilot B independently receives the same Tender Signal once;
- rerunning pilot A does not redeliver it;
- owner delivery receipts remain untouched.

## Final production deployment

Final production release:

`2500d6f044c1f3dad985f15fc2e2f207d39199bf`

Previous release:

`9466ba391a7b5c10fc9a3ccb5760a9342134bf36`

Final archive SHA256, identical on Mac and Bangkok:

`44738ec629289295d9c800153feec461db39457261571eadb98ac259a63c1eb4`

Standard deployment result:

`deployment=success application=signalforge release=2500d6f044c1f3dad985f15fc2e2f207d39199bf previous=9466ba391a7b5c10fc9a3ccb5760a9342134bf36 timer_preexisting=1`

Live acceptance:

- active symlink resolves to the exact final release;
- schema = 11;
- `pilot_delivery_receipts` exists;
- `pilot_feedback_events` exists;
- legacy `delivery_receipts` exists;
- owner receipts before deployment = 41;
- owner receipts after deployment = 41;
- pilot receipts = 0;
- pilot feedback events = 0;
- SQLite `PRAGMA quick_check = ok`;
- SignalForge = PASS / GREEN;
- recovery backlog = 0;
- current Signals = 79;
- run-due timer = enabled + active;
- Telegram immediate-delivery timer = enabled + active;
- Telegram digest timer = enabled + active;
- Assurance timer = enabled + active.

Final live `pilot-report`:

```text
delivery_count=0
unique_tenders_delivered=0
profiles_with_attributed_delivery=0
feedback_by_type={}
worth_reviewing_rate=null
action_rate=null
bid_or_quote_rate=null
```

This zero state is the correct production result: the capability is live, but no real paying pilot has yet been onboarded. Historical owner-feed activity is no longer misrepresented as customer validation.

## Manual pilot operating procedure

For each real pilot company:

1. create one customer-specific Business Profile JSON with a unique `profile_id`;
2. use that customer's Telegram chat ID for delivery;
3. run:

```sh
SIGNALFORGE_TELEGRAM_CHAT_ID=<customer-chat-id> \
  signalforge telegram-deliver --profile profiles/<customer>.json
```

4. record real observed outcomes only:

```sh
signalforge pilot-feedback \
  --profile-id <profile-id> \
  --canonical-key <canonical-key> \
  --signal-id <signal-id> \
  --event WORTH_REVIEWING

signalforge pilot-feedback \
  --profile-id <profile-id> \
  --canonical-key <canonical-key> \
  --signal-id <signal-id> \
  --event ACTION_TAKEN

signalforge pilot-feedback \
  --profile-id <profile-id> \
  --canonical-key <canonical-key> \
  --signal-id <signal-id> \
  --event BID_OR_QUOTE_INITIATED
```

5. inspect:

`signalforge pilot-report --profile-id <profile-id>`

Customer chat IDs and Telegram credentials remain operator-side secrets and are not committed to Git.

## Next business gate

Engineering is **not** the current bottleneck.

Do not build public signup, billing, dashboard, automatic fan-out or Cloudflare self-service merely because the runtime can support them.

Next gate:

- manually onboard the first 3–5 real pilot companies;
- use their real profile + Telegram chat;
- collect real `WORTH_REVIEWING`, `ACTION_TAKEN`, `BID_OR_QUOTE_INITIATED` outcomes;
- validate willingness to pay in the RMB 200–500/month range;
- only after real customer evidence should SignalForge decide whether to build a self-service Cloudflare Worker/D1 control plane.

North Star remains:

> customer action caused by relevant tender intelligence.
