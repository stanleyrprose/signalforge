# Engineering Relevance Taxonomy — Production Closure

Date: 2026-09-19

## Problem

SignalForge's stated mission includes government/SOE opportunities in engineering, construction, telecom and energy, but the relevance taxonomy had no `ENGINEERING` category. A real S22 Inland Water Transport vessel procurement therefore fell through to `OTHER` even after its evidence/actionability gaps had been closed.

## Decision

Add `ENGINEERING` as a first-class relevance category.

Scoring:

- TELECOM = 10
- ICT = 10
- ENERGY = 7
- ENGINEERING = 7
- INDUSTRIAL = 6
- MEDICAL = 5
- CONSTRUCTION = 4
- OTHER = 2

This changes contextual relevance only. It does not change the strategic interrupt rule: only ICT/TELECOM satisfy the existing `strategic=True` condition for automatic HIGH promotion. Engineering opportunities therefore do not become HIGH merely because they are engineering-related.

## Keywords

High-precision English keywords:

- vessel
- token-bounded ship
- railway
- bridge
- dredging
- marine

High-precision Burmese keywords:

- ရေယာဉ်
- သင်္ဘော
- မီးရထား
- တံတား

Port terms were deliberately excluded.

During production A/B, adding `port / ဆိပ်ကမ်း` incorrectly reclassified S38 `industry:1038`, which is a container-truck rental/logistics tender moving pharmaceutical materials from Yangon ports to factories, not a port-engineering opportunity. The keywords were removed before merge and a regression test was added.

Token boundaries are also used for English `ship` so strings such as `partnership` and `scholarship` do not create false ENGINEERING matches.

## S22 production case

Canonical key:

`iwt:1038:2026-08-25`

Real production qualification input is Burmese and contains `ရေယာဉ်` (vessel). The earlier Telegram English label `Coastal Cargo Vessel` is presentation-layer text and was not available to the classifier.

Before:

- primary relevance: `OTHER`
- relevance score: `2/10`
- quality: `88`
- priority: `MEDIUM`

After:

- primary relevance: `ENGINEERING`
- provenance: `ITEM_TEXT_KEYWORD:ရေယာဉ်`
- relevance score: `7/10`
- quality: `93`
- quality band: `VERY_HIGH`
- priority remains `MEDIUM`
- gaps remain `[]`

## Validation

PR #220 merged as:

`f23956f78edd54eed1ea57ced7de599a79559d0a`

Tests:

- focused qualification/signal-quality/opportunities: `31/31 PASS` on default Python;
- focused: `31/31 PASS` on Python 3.13;
- full suite: `427/427 PASS` on default Python;
- full suite: `427/427 PASS` on Python 3.13;
- compileall: PASS;
- `git diff --check`: PASS.

Red-team sensors added:

- real Burmese S22 vessel classification;
- transport/partnership substring does not trigger ENGINEERING;
- port used only as a logistics origin does not trigger ENGINEERING;
- S22 integration locks `quality=93` and `priority=MEDIUM`.

GitHub Actions run `35426014137` did not start repository code because the account payment/spending-limit state blocked the job. Equivalent local Python 3.13 validation passed.

## Pre-deploy production A/B

The undeployed commit was executed against the live Bangkok production DB.

There were 15 current opportunities. After removing the port false-positive, exactly one current opportunity changed:

`iwt:1038:2026-08-25`

All other 14 current opportunities remained unchanged in relevance, score and priority.

## Production

Bangkok active release:

`f23956f78edd54eed1ea57ced7de599a79559d0a`

Previous release:

`6a19a69266d0fff87484debef46176eee2226147`

Live acceptance:

- DB `quick_check=ok`;
- canonical rows: 244;
- Signal rows: 65;
- S22 Signal count remains exactly 1;
- S22 relevance = `ENGINEERING`;
- S22 provenance = `ITEM_TEXT_KEYWORD:ရေယာဉ်`;
- S22 quality = `93 / VERY_HIGH`;
- S22 priority remains `MEDIUM`;
- S22 gaps = `[]`;
- reviewed OCR location and next action remain present;
- four production timers remain enabled;
- Telegram digest dry-run = `PASS / pending_count=0`.

No canonical rewrite, source adapter change, Signal creation, scheduler change or delivery-policy change was introduced.

## Outcome

The fix closes a structural mismatch between SignalForge's mission and its relevance taxonomy. Engineering is now represented explicitly rather than being forced into INDUSTRIAL/CONSTRUCTION/OTHER, while false-positive controls keep the category narrow.
