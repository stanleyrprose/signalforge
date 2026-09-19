# Jev Noise Shadow v0 — Production Calibration

Date: 2026-09-19

## Purpose

Extend Jev shadow analysis earlier than current_opportunities by evaluating the existing Assurance noise-review corpus.

The feature is read-only:

- authority = HUMAN_REVIEW_REQUIRED
- production_effect = NONE
- writes = NONE
- no automatic noise-review outcome
- no automatic missed_signals write
- no Telegram or scheduler integration

## Existing Assurance corpus

A read-only SQLite backup of Bangkok production contained:

- 30 noise_review_samples
- 24 CONFIRMED_NOISE
- 1 FALSE_NEGATIVE
- 5 INCONCLUSIVE
- 826 successful zero-item processing records

For calibration, Jev was not given review_status or review_note.

Eligible semantic evidence:

- retained HTML for ZERO_ITEM_PROCESSING samples
- title/url for INDEPENDENT_LISTING_NONSTANDARD samples

KNOWN_HISTORICAL_SIGNAL_NOISE and unavailable historical artifacts are skipped instead of guessed.

## Calibration result

14 reviewed samples had sufficient semantic evidence:

- 13 CONFIRMED_NOISE
- 1 FALSE_NEGATIVE

The main-briefing Jev threshold of 0.60 was too strict for miss detection. The known S22 false negative was stable around:

- open_actionable: 0.50–0.51
- mission_sector: 0.72–0.75
- page_state: contains_open_opportunity

All 13 confirmed-noise examples stayed outside the review gate.

The v0 recall-oriented review gate is therefore:

~~~text
open_actionable >= 0.50
AND mission_sector >= 0.60
AND page_state == contains_open_opportunity
~~~

This threshold is for human-review recommendation only; it is not a production action threshold.

Retrospective result:

- TP = 1
- FP = 0
- TN = 13
- FN = 0

A live run of the implemented module over all 30 production review samples returned:

- tracked = 30
- evaluated = 14
- skipped = 16
- REVIEW_RECOMMENDED = 1

The sole recommendation was the already human-confirmed S22 ZERO_ITEM_PROCESSING false negative.

## CLI

~~~bash
TYPESAFE_API_KEY=... signalforge jev-noise-shadow
~~~

Defaults:

- review status: PENDING
- limit: 50
- open threshold: 0.50
- sector threshold: 0.60
- model: jev-latest

For retrospective review:

~~~bash
signalforge jev-noise-shadow --status ALL
~~~

Optional database/evidence-root overrides support offline validation against a production snapshot.

## Validation

- focused Jev/noise/mission tests: 9 / 9 PASS
- full pytest: 450 passed
- unittest discovery: 444 tests / OK
- compileall: PASS
- Source Registry JSON contract: PASS
- shell syntax checks: PASS
- git diff --check: PASS

## Boundary

Jev may recommend that a noise sample deserves human review. Only the existing explicit noise-review workflow may mark a sample FALSE_NEGATIVE, and only that human-reviewed outcome may create a missed_signals record.
