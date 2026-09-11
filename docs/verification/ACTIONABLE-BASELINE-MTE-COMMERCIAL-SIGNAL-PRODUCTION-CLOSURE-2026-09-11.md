# Actionable Baseline + MTE Commercial Signal — Production Closure

Date: 2026-09-11 (Asia/Yangon)
Result: PRODUCTION / GREEN

## Why this slice existed

A user-supplied ground-truth candidate exposed a product-definition miss:

`Myanma Timber Enterprise — Local Marketing and Milling Department, Open Tender No (6/2026-2027)(15.9.2026)`

The official MTE announcement surface showed the event, but S32 production selected only buyer-side procurement and intentionally rejected sale/auction semantics. The audit also found five still-actionable S21/S22 tenders already stored in canonical state but invisible to the signal-backed customer opportunity view because they had entered on suppressed first baseline.

The acceptance criterion was therefore not merely “parser sees the page”; it was end-to-end:

`official evidence -> canonical -> Signal -> qualification -> customer view -> Telegram policy`

## Product decision

SignalForge now treats a **trustworthy fact that can change a business action** as the core Signal concept. Procurement remains one important subtype, not the whole definition.

For MTE the semantic split is explicit:

- buyer-side procurement -> `TENDER`;
- narrow Local Marketing seller-side open tender -> `AUCTION_NOTICE`;
- `commercial_event_type=SELLER_OPEN_TENDER_SALE`;
- `commercial_direction=BUY_FROM_ISSUER`.

The title date `15.9.2026` is represented as:

- `action_date=2026-09-15`;
- `action_date_kind=TENDER_EVENT_DATE`;
- `action_date_evidence=EXPLICIT_OFFICIAL_TITLE_DATE`;
- `deadline=null`.

No bid-submission deadline is invented from an event date. Image-carried quantity/location/lot detail remains unparsed and therefore keeps the event at partial completeness / human review.

## Baseline reconciliation decision

S21 Myanma Railways and S22 IWT now explicitly opt into `actionable_baseline_signal_policy`. This repairs the case where a tender is real, future and actionable but first appeared during suppressed baseline.

Date-only issuer deadlines are eligible using the start of the Myanmar calendar date only as a conservative reconciliation lower bound. That lower bound is never written back as an invented issuer time.

Legacy S21/S22 TENDER canonical rows without `business_stage` are visible as opportunities only because these sources explicitly opt into actionable-baseline reconciliation. Read-layer scope/evidence uses already-stored issuer data; no historical canonical rewrite/backfill was performed.

## Noise controls

- S21 four recovered baseline tenders: `A / MEDIUM / SOON` -> Watchlist only.
- S22 one recovered baseline tender: `A / MEDIUM / NORMAL` -> Watchlist only.
- MTE `mte:1605`: `B / REVIEW / SOON` -> immediate Attention.
- Existing MTE buyer-procurement canonical payloads remain v1-equivalent, so parser-v2 rollout generated no false historical UPDATED signals.
- MTE Export tender sales / generic tentative programmes were not broadly admitted; the production extractor is limited to the Local Marketing tender category and explicit title pattern.

## Verification before merge

Full suite:

`291 passed`

PR #153 GitHub Actions:

- run: `34558692274`
- job: `verify`
- conclusion: `success`

Feature production-copy gate used a fresh read-only backup of the live database plus live Bangkok network. It returned:

- S21: `changed=0 / signals_created=4`;
- S22: `changed=0 / signals_created=1`;
- S32: `changed=1 / signals_created=1`;
- canonical: `209 -> 210`;
- raw signals: `45 -> 51`;
- current opportunities: `9 -> 15`;
- counts: `14 OPEN + 1 UNKNOWN`;
- priority: `HIGH=3 / MEDIUM=10 / REVIEW=2 / LOW=0`.

## Exact production deployment

Squash merge SHA:

`cb847afc59e71ef89ba3ee57a1ca1707792ec7e0`

Exact Git archive SHA256, matching locally and on Bangkok:

`8e643dbd73fbad74021003fd3153aa13a8cd64d1f337d658da4233171600190f`

Previous runtime / rollback:

`bd86efcaa5699f1aa5082459cd57882b8ffe4e73`

The previous runtime is an ancestor of the deployed SHA. Pre-deploy production was `PASS/GREEN`, 27 sources GREEN, backlog 0, `209 canonical / 45 signals / 4 immediate Telegram receipts`. Deployment itself changed no business counts.

## Reviewed production refresh

Formal systemd Worker boundary executions:

- S21 Worker `signalforge-20260911T033353Z-11839904`: `MANUAL / SUCCESS / changed=0 / signals_created=4`;
- S22 Worker `signalforge-20260911T033403Z-a5c9f167`: `MANUAL / SUCCESS / changed=0 / signals_created=1`;
- S32 Worker `signalforge-20260911T033404Z-d5c82807`: `MANUAL / SUCCESS / changed=1 / signals_created=1 / items=3 / tenders=2`.

Final source signal rows:

- S21: four `NEW / ACTIONABLE_BASELINE_RECONCILIATION / deadline=2026-09-14`;
- S22: one `NEW / ACTIONABLE_BASELINE_RECONCILIATION / deadline=2026-11-03`;
- S32: one `NEW / mte:1605 / AUCTION_NOTICE / action_date=2026-09-15`.

No extra S32 parser-only UPDATED signals were created.

## Customer / Telegram verification

Final opportunity view:

- `15 total`;
- `14 OPEN + 1 UNKNOWN`;
- `HIGH=3 / MEDIUM=10 / REVIEW=2 / LOW=0`;
- S21 x4 = `A / MEDIUM / SOON`;
- S22 x1 = `A / MEDIUM / NORMAL`;
- `mte:1605` = `B / REVIEW / SOON`.

Telegram dry-run before delivery returned exactly one pending item: `mte:1605`. S21/S22 MEDIUM items did not become immediate alert spam.

A direct interactive CLI send correctly failed because Telegram credentials are not exposed to the SSH shell. Delivery through the reviewed systemd service succeeded without exposing secrets:

- delivery receipt count: `4 -> 5`;
- canonical: `mte:1605`;
- action: `REVIEW`;
- provider message id: `9`;
- repeat dry-run: `pending_count=0`.

## Final production state

- runtime: `cb847afc59e71ef89ba3ee57a1ca1707792ec7e0`;
- rollback: `bd86efcaa5699f1aa5082459cd57882b8ffe4e73`;
- status: `PASS`;
- SignalForge health: `GREEN`;
- active source health: `27/27 GREEN`;
- canonical: `210`;
- raw signals: `51`;
- effective signals: `30`;
- current opportunities: `15`;
- recovery backlog: `0`;
- immediate Telegram receipts: `5`;
- source yield: `ACTIONABLE_PROVEN=7 / SIGNAL_PROVEN=3 / BASELINE_ONLY=15 / NOISE_ONLY_HISTORY=1 / EMPTY=1`;
- proven sources: `10/27`;
- acquisition timer: active;
- immediate Telegram timer: active;
- daily Digest timer: active.

This closure authorizes the business semantic rule above. It does **not** authorize generic auction ingestion, inferred deadlines, OCR/image extraction, or broad seller-side event promotion without source-specific evidence and selection rules.
