# S30 MOFA Participation Detail Enrichment — Production Closure

Date: 2026-09-18

## Goal

Improve the same-day actionability of current MOFA tender `mofa:59800 / MOFA-POST-59800` without rewriting canonical history or creating a new Signal.

Before this change the official MOFA PDF already proved scope and the `2026-09-18 16:30` bid deadline, but the customer read model still had `LOCATION_MISSING` and signal quality `90`.

## Official source-native evidence

Official attachment:

`https://www.mofa.gov.mm/wp-content/uploads/2026/09/Tender-Announcement.pdf`

Live audit SHA256:

`aad5b2c3e51ffc289edb5018254f364896b01d14bee8fa3be7e362e756e130c7`

This exactly matches the canonical `evidence_sha256`.

The PDF explicitly states:

- tender forms available from 2026-09-07 through 2026-09-18 during office hours;
- bid submission deadline `2026-09-18 16:30`;
- form purchase and bid submission at Ministry of Foreign Affairs, Office No.9, Nay Pyi Taw, through the relevant Strategic Studies and Training Department unit;
- contact phone `067-412317`.

## Implementation

PR #214 merged as:

`cf95214e33d0162396957e3ba9c35c68df1f535a`

A source-scoped reviewed MOFA PDF overlay now requires exact match on canonical key, source, item kind, reference, publication date, article URL, attachment URL and canonical evidence SHA.

The overlay adds only location, next action, provenance and stronger detail-completeness metadata in the read layer. Wrong identity or SHA fails closed.

Canonical payload, parser, scheduler and Signal history remain unchanged.

## Validation

- focused tests: `19/19 PASS` on default Python and Python 3.13;
- full suite: `414/414 PASS` on default Python and Python 3.13;
- production DB-copy Telegram preview: quality `100`, gaps `[]`, Office No.9 location and 16:30 next action rendered;
- compileall, registry parse, shell syntax and `git diff --check`: PASS.

GitHub Actions run `35295438246` did not start repository code because of account payment/spending-limit state. Equivalent Python 3.13 workflow checks passed locally.

## Production

Bangkok active release:

`cf95214e33d0162396957e3ba9c35c68df1f535a`

Rollback release:

`5a703fc56142dde38f4156cc93a9da9d5bda35ec`

Live verification:

- DB `quick_check=ok`;
- S30 canonical payload remains `location=None / next_action_summary=None`;
- canonical evidence SHA remains `aad5b2c3...30c7`;
- S30 Signal count remains exactly `1`;
- read-layer quality is now `100`;
- read-layer quality gaps are empty;
- location is `Ministry of Foreign Affairs, Office No.9, Nay Pyi Taw`;
- next action contains the 2026-09-18 16:30 submission deadline and phone `067-412317`;
- all four production timers remain enabled;
- Telegram digest dry-run is `PASS / pending_count=1` and renders the new location/next-action text.

The pending item is the normal 2026-09-18 daily digest, not a new immediate Signal.

## Decision

This closes the current S30 actionability gap. As with S39, exact-hash-bound source-native reviewed enrichment is preferred over canonical rewrites when the official evidence already exists but historical parsing omitted customer-facing fields.
