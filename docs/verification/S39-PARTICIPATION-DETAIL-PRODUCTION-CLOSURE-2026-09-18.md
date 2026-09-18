# S39 Energy Participation Detail Enrichment — Production Closure

Date: 2026-09-18

## Goal

Improve the actionability of the current Ministry of Energy tender 27/2026-2027 without rewriting canonical facts or creating a new Signal.

Before this change, S39 already had strong source-native evidence for scope and the 2026-09-18 13:00 bid deadline, but the customer read model still exposed:

- `LOCATION_MISSING`;
- `PARTICIPATION_INSTRUCTION_MISSING`;
- signal quality score `85`.

## Source-native official evidence

The existing canonical S39 attachment is:

`https://energy.gov.mm/storage/tenders/ZN0mM90uR0Ik1KJNCSY8GbcyK1YAgs8BMmbMxUvG.pdf`

Live audit retrieval on 2026-09-18 returned the exact canonical evidence SHA256:

`4d2ef1694aa6a7221b1a2d46799eadba7f8edb9ef46a2045c573e07c1760c94b`

The PDF text explicitly states:

- tender-form purchase is available from 2026-09-04 at MOGE, Office No.44, Finance Department, Nay Pyi Taw;
- bid submission closes on 2026-09-18 at 13:00;
- bids must be submitted in person to Ministry of Energy, Office No.6, Yadana Hall, Nay Pyi Taw;
- contact phone: 067-3411206.

No MOI/Kyemon fallback is needed because the issuer's own PDF already contains the missing business details.

## Implementation

PR #212 merged as:

`5a703fc56142dde38f4156cc93a9da9d5bda35ec`

The change adds a source-scoped reviewed Energy PDF overlay.

The overlay is applied only when all of the following match exactly:

- canonical key;
- source ID `S39`;
- item kind `TENDER`;
- reference number;
- publication date;
- official article URL;
- exact attachment URL;
- canonical `evidence_sha256`.

If any identity or SHA condition differs, the overlay fails closed.

The read layer adds only:

- `location`;
- `location_evidence`;
- `next_action_summary`;
- `next_action_evidence`;
- reviewed-enrichment provenance;
- stronger detail-completeness metadata.

Canonical payload, canonical identity, parser behavior, scheduler behavior and Signal history are unchanged.

## Validation

Focused tests:

- default Python: `18/18 PASS`;
- Python 3.13: `18/18 PASS`.

Full suite:

- default Python: `410/410 PASS`;
- Python 3.13: `410/410 PASS`.

Other checks:

- compileall: PASS;
- registry JSON parse: PASS;
- shell syntax: PASS;
- `git diff --check`: PASS.

GitHub Actions run `35294974340` did not start repository code because of the account payment/spending-limit state. Equivalent Python 3.13 workflow checks passed locally.

## Production deployment

Bangkok active release:

`5a703fc56142dde38f4156cc93a9da9d5bda35ec`

Previous/rollback release:

`3f66cf073c7e297f18e3b412eff06010286d872c`

Live production verification:

- DB `quick_check=ok`;
- S39 canonical payload still has `location=None`;
- S39 canonical payload still has `next_action_summary=None`;
- canonical evidence SHA remains `4d2ef169...1760c94b`;
- S39 Signal count remains exactly `1`;
- read-layer S39 signal quality is now `100`;
- S39 quality gaps are now empty;
- read-layer location is `Ministry of Energy, Office No.6, Yadana Hall, Nay Pyi Taw`;
- read-layer next action includes in-person submission by 2026-09-18 13:00, form-purchase location and phone;
- run-due, Telegram deliver, Telegram digest and assurance timers remain enabled.

The 2026-09-18 Telegram digest dry-run returns `PASS / pending_count=1` and now renders S39 with deadline, location, next action and official link. The pending item is the normal daily digest, not a new immediate Signal.

## Decision

This closes the current S39 actionability gap.

The preferred pattern remains: when canonical evidence is already strong but customer-facing business fields were not parsed historically, use a narrowly reviewed, exact-hash-bound read-layer overlay rather than rewriting canonical history merely to improve presentation.
