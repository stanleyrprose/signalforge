# Jev Noise Triage v0 — Production Validation

Date: 2026-09-20

## Purpose

Prioritize the existing Assurance false-negative review workload before random sampling.

The feature is explicit and read-only:

- authority = HUMAN_REVIEW_REQUIRED
- production_effect = NONE
- writes = NONE
- no change to assurance-run
- no scheduler integration
- no Telegram integration
- no automatic noise sample creation
- no automatic FALSE_NEGATIVE outcome
- no automatic missed_signals write

## Candidate pool

The v0 pool contains only:

- unsampled ZERO_ITEM_PROCESSING records with retained HTML evidence;
- latest INDEPENDENT_LISTING_NONSTANDARD candidates.

Deterministic gates are applied before Jev:

1. exclude exact candidates already present in noise_review_samples;
2. exclude an artifact SHA already represented by a reviewed zero-item sample;
3. suppress a zero-item when the same source and acquisition URL later produced a successful nonzero parse;
4. collapse repeated zero-item rows by source + artifact SHA;
5. sort by recency;
6. cap each source at five candidates by default;
7. bound the total Jev candidate count to 30 by default.

This prevents high-frequency changing pages from consuming the entire review budget.

## Ranking

Jev reuses the calibrated miss-review semantics:

~~~text
REVIEW_RECOMMENDED when:

open_actionable >= 0.50
AND mission_sector >= 0.60
AND page_state == contains_open_opportunity
~~~

The ranking is transparent:

1. REVIEW_RECOMMENDED first;
2. contains_open_opportunity before other page states;
3. higher min(open_actionable, mission_sector);
4. higher max(open_actionable, mission_sector);
5. newer evidence.

No opaque composite model score is used.

## Production observations

Initial Bangkok candidate statistics before source balancing:

- zero-item rows scanned: 845
- unique replayable HTML before recovery suppression: 177
- source concentration: S40=166, S37=6, S47=4, S22=1
- naive latest-30 selection: S40 occupied 29 of 30

This proved artifact dedupe alone was insufficient and motivated the per-source cap.

## Recovery suppression finding

The first live triage pass surfaced one S22/IWT zero-item candidate:

- open_actionable about 0.53
- mission_sector about 0.76
- page_state = contains_open_opportunity

Replay with the current IWT parser parsed 20 records from the historical artifact, and the production canonical state already contained the recovered IWT tenders.

This was therefore historical evidence of a previously fixed parser miss, not a currently unresolved miss.

The deterministic candidate gate was extended to suppress a historical zero-item when the same source + acquisition URL has a later successful processing record with items_found > 0.

## Final production pool

With the final gates:

- zero-item rows scanned: 845
- later-success recovery suppressions: 237
- exact reviewed candidates excluded: 17
- duplicate artifacts collapsed: 60
- retained evidence unavailable: 361
- eligible zero-item candidates before per-source cap: 170
- final zero-item bounded pool: S40=5, S47=4
- latest nonstandard candidates added: S38=3
- total Jev-evaluated bounded candidates: 12

Final Jev result:

- REVIEW_RECOMMENDED: 0
- LOWER_PRIORITY: 12

No current unresolved false-negative candidate was identified in this bounded review.

The 361 missing-evidence records were subsequently confirmed to be entirely pre-retention legacy audit debt, with zero retention-era missing evidence. See `EVIDENCE-RETENTION-AUDIT-DEBT-CLOSURE-2026-09-20.md`. Jev still does not guess over unavailable evidence.

## CLI

~~~bash
TYPESAFE_API_KEY=... signalforge jev-noise-triage
~~~

Defaults:

- candidate-limit = 30
- per-source-cap = 5
- top = 10
- open-threshold = 0.50
- sector-threshold = 0.60
- model = jev-latest

Offline snapshot validation can use:

~~~bash
signalforge jev-noise-triage \
  --database /path/to/signalforge.db \
  --evidence-root /path/to/evidence
~~~

## Validation

- focused Jev noise triage + noise shadow: 10 / 10 PASS
- full pytest: 459 passed
- unittest discovery: 453 tests / OK
- compileall: PASS
- Source Registry JSON contract: PASS
- shell syntax checks: PASS
- git diff --check: PASS

## Boundary

Jev only prioritizes evidence for review.

The existing human review process remains the authority for declaring a false negative and for any later missed_signals record.
