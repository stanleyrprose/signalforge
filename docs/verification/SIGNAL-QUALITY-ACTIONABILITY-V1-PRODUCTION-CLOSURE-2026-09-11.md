# Signal Quality / Actionability v1 — Production Closure

Date: 2026-09-11 (Asia/Yangon)
Result: PRODUCTION / GREEN

## Objective

Add an explainable quality/actionability score for SignalForge business opportunities without turning that score into a second priority policy.

- `priority_band` continues to decide interruption/attention behavior.
- `signal_quality_score` describes evidence completeness and business actionability.
- No alert or qualification threshold uses the new score in v1.

## Model

`SIGNAL_QUALITY_MODEL_VERSION = 1`

100 points:

- issuer: 15
- business scope + quantified lot/amount: 20
- time: 20
- location: 10
- next participation/action path: 10
- official evidence: 10
- strategic relevance: 10
- urgency: 5

Bands:

- `VERY_HIGH >= 85`
- `HIGH >= 70`
- `MEDIUM >= 55`
- `REVIEW >= 40`
- `LOW < 40`

The output carries per-dimension evidence, strengths and explicit gaps. Quantity/scope specificity requires a numeric value adjacent to a recognized unit/lot/set token; generic words such as `lot details` do not receive quantity credit.

## Policy boundary

`QUALIFICATION_POLICY_VERSION` remains `1`.

This slice does **not** change:

- HIGH/MEDIUM/REVIEW/LOW priority semantics;
- Telegram delivery identity;
- source acquisition or parser behavior;
- scheduler/timer cadence;
- database schema;
- canonical or Signal state.

## Calibration

A fresh read-only copy of the live production DB was evaluated with the feature code. Current 15 opportunities:

- `VERY_HIGH = 7`
- `HIGH = 6`
- `MEDIUM = 1`
- `REVIEW = 1`
- `LOW = 0`
- average score = `78.3`

Existing priority remained exactly:

- HIGH = 3
- MEDIUM = 10
- REVIEW = 2
- LOW = 0

Representative calibration:

- `industry:1022` = `93 / VERY_HIGH`;
- Industry remaining current tenders = `89-91 / VERY_HIGH`;
- `mofa:59800` = `86 / VERY_HIGH`;
- `energy:235` = `81 / HIGH`;
- S21 Railways = `71-78 / HIGH`;
- S22 IWT = `78 / HIGH`;
- `mte:1605` = `59 / MEDIUM`, while priority stays `REVIEW`;
- `doms:12735` = `40 / REVIEW`.

MTE gaps are explicit: quantity/lot detail, exact time, location and detailed participation instructions are not yet structured. DOMS is lower because the action timeframe and next action are still unknown.

Production-copy DB SHA256 before and after scoring:

`00ab308c2381f130c90527166b3ed366ae3f1eba675650628ed16165d836f168`

## Tests / CI

- targeted cross-layer tests: `41 passed`;
- full suite: `295 passed`;
- PR: `#155`;
- GitHub Actions run: `34564204071`;
- conclusion: `success`.

## Exact deployment

Runtime:

`b9fc1b3feaaa73ad9bbacade2dd5ad967a7cd234`

Archive SHA256:

`8a6e9ab34d2de44d4ada5417ce55f6b5e16c6070377e98be2f659d84f202a5fd`

Rollback:

`cb847afc59e71ef89ba3ee57a1ca1707792ec7e0`

Pre-deploy state was `210 canonical / 51 signals / 5 immediate Telegram receipts`; all three timers were active.

## Live verification

Post-deploy:

- active runtime = exact SHA above;
- opportunities = 15;
- priority = `HIGH 3 / MEDIUM 10 / REVIEW 2`;
- quality = `VERY_HIGH 7 / HIGH 6 / MEDIUM 1 / REVIEW 1`;
- quality average = `78.3`;
- Energy = `81/HIGH`;
- MOFA = `86/VERY_HIGH`;
- MTE = `59/MEDIUM` while priority remains REVIEW;
- DOMS = `40/REVIEW`;
- Business Digest exposes the same distribution;
- future Telegram Attention messages expose `Signal质量: score/100 · band`;
- Telegram dry-run = `pending_count=0`;
- DB = `210 canonical / 51 signals / 5 immediate receipts`;
- status = PASS / GREEN;
- active sources = `27/27 GREEN`;
- recovery backlog = `0`;
- acquisition, immediate Alert and daily Digest timers = active.

No source refresh, schema migration, canonical update, new Signal, or delivery replay was required.

## Next gate

Do not use the score to automatically promote/demote `priority_band` until enough real examples have been reviewed. The next decision gate is calibration quality: collect false-high / false-low examples, especially where location or participation instructions are present only in attachments/images, and only then decide whether Signal Quality should influence ranking or alert thresholds.
