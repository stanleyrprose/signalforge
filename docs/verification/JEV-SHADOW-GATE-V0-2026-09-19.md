# Jev Shadow Gate v0 — Calibration and Read-Only Integration

Date: 2026-09-19

## Decision

Jev is admitted only as an explicit, read-only shadow semantic judge for the current-opportunity mission filter.

It is not authoritative for Signal creation, canonical state, qualification, priority, Signal Quality, Telegram delivery, source acquisition, parser behavior, or mission-filter output.

Runtime contract:

- authority = DETERMINISTIC_ONLY
- production_effect = NONE
- no scheduler/timer integration
- no database writes or schema migration
- no delivery receipt changes
- no automatic Jev fallback
- no mandatory typesafe-sdk project dependency

Explicit CLI surface:

~~~bash
TYPESAFE_API_KEY=... signalforge jev-shadow
~~~

Default model: jev-latest.

Default shadow threshold: 0.60.

## Why the decision is atomic rather than one score

SignalForge has two materially different concepts:

1. commercial opportunity — a concrete business event that can change action;
2. procurement — a buyer-side tender/RFP/RFQ/bid where the issuer seeks goods, works or services.

They are not equivalent. The reviewed MTE seller-side event mte:1605 is a real commercial opportunity but not buyer-side procurement.

The shadow gate therefore uses three independent semantics:

~~~text
commercial_opportunity >= threshold
AND mission_sector >= threshold
AND workflow_stage == open_opportunity
~~~

procurement remains an explanatory dimension, not the overall Signal gate.

A single overall suitability Score was evaluated earlier and was less stable across regulatory and strategic-intelligence cases, so v0 does not use it.

## Calibration set

The expanded calibration used 54 reviewed examples derived from existing SignalForge tests, fixtures and GOAL semantics. It included energy, construction, railway, telecom/ICT and engineering tenders; mixed-scope tenders; medical/books/office-goods/chemical off-mission procurement; seller-side auction/open-tender/lease opportunities; telecom/network strategic intelligence; regulatory notices; tentative programmes; opening/scrutiny stages; awards/results; jobs; and low-value noise.

No production database state was mutated by calibration.

## Jev results

Model requested: jev-latest.

Effective model returned during calibration: jev-1.13.0.

| Dimension | Result |
| --- | ---: |
| commercial opportunity @ 0.5 | 54 / 54 |
| procurement @ 0.5 | 54 / 54 |
| mission sector @ 0.5 | 49 / 50 |
| workflow stage | 52 / 54 |

The one mission-sector error was Smart ID Card Printing, scored 0.58, while the reviewed SignalForge mission treats it as outside the four primary target sectors.

The two stage mismatches were taxonomy-level disagreements that did not change opportunity gating: a Commerce training/exam item was regulatory_or_admin vs reviewed noise; PTD Spectrum Roadmap was programme_or_preview vs reviewed strategic_intelligence. Both remained non-opportunities.

## Main-briefing threshold calibration

The evaluated shadow rule was:

~~~text
commercial_opportunity >= t
AND sector >= t
AND stage == open_opportunity
~~~

| Threshold | TP | FP | FN |
| ---: | ---: | ---: | ---: |
| 0.50 | 23 | 1 | 0 |
| 0.55 | 23 | 1 | 0 |
| 0.60 | 23 | 0 | 0 |
| 0.65 | 23 | 0 | 0 |
| 0.70 | 23 | 0 | 0 |
| 0.75 | 23 | 0 | 0 |
| 0.80 | 21 | 0 | 2 |
| 0.90 | 19 | 0 | 4 |

0.60 is the lowest reviewed threshold that removed the observed false positive without sacrificing reviewed true positives. It is suitable for shadow comparison, not yet for production authority.

## Real API smoke

A live TypeSafe API smoke against two synthetic in-memory current-opportunity rows returned:

- PTD RF-monitoring tender: AGREE_INCLUDE, commercial 0.93, sector 0.97;
- DOMS CT/MRI medical tender: AGREE_EXCLUDE, commercial 0.93, sector 0.25.

The report retained status SHADOW_ONLY, authority DETERMINISTIC_ONLY, and production_effect NONE.

No SignalForge database was used or mutated by this smoke.

## Integration validation

The repository's exact verify.yml command sequence was replayed locally in a fresh Python 3.13 virtual environment after converting the new tests to unittest discovery semantics:

- editable runtime install: PASS
- Source Registry JSON contract: PASS
- compileall over signalforge and tests: PASS
- unittest discovery: 437 tests / OK
- bin/signalforge shell syntax: PASS
- deploy/deploy-signalforge-release.sh shell syntax: PASS
- git diff --check: PASS

## Scope limit

v0 compares Jev only against rows already exposed by current_opportunities().

It does not prove false-negative coverage for records that never entered the current-opportunity surface. That limit is reported explicitly as:

~~~text
false_negative_coverage_outside_current_opportunities = NOT_PROVEN
~~~

A later expansion to parser/noise/missed-signal auditing requires separate evidence; it must not be inferred from this v0 result.
