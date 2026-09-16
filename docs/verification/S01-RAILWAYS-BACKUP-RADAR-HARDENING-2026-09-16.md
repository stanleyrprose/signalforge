# S01 Myanma Railways Backup Radar Hardening

Date: 2026-09-16

## Reason

S21 Myanma Railways is a high-value engineering source but its issuer-origin endpoint remains a coverage risk because direct acquisition has timed out since 2026-09-13.

A third-party tender index surfaced a possible later Myanma Railways tender after the last issuer-origin success. The lead is **not** promoted because no issuer-original or National Portal official evidence has yet corroborated it.

The investigation exposed a deterministic radar gap: a National Portal card whose title is only `Myanma Railways Open Tender Call` may contain no bridge/road/transformer keywords, so S01 Mission Radar could ignore it even though the issuer itself is mission-critical.

## Change

S01 Mission Radar now recognizes English `railway`, `railways`, `Myanma Railways`, and Burmese `မြန်မာ့မီးရထား` as ENGINEERING discovery-title evidence.

Source resolution also maps those English title forms to target source `S21`.

Existing safeguards remain unchanged:

- S01 is Assurance-only;
- `canonical_truth=false`;
- National Portal closing date remains hint-only;
- off-mission title veto runs first, so a Railways card explicitly describing hospital/medical procurement is rejected;
- no National Portal lead becomes canonical or customer-visible without existing review/resolution rules.

## Verification

- targeted National Portal tests: 8 passed;
- full suite: 398 passed;
- Ruff PASS;
- diff check PASS.

Live National Portal pages 1-6 on 2026-09-16 remained unchanged:

- page 1: S13/MPT lead;
- page 2: S38 engineering lead;
- page 3: S22/IWT engineering lead;
- pages 4-6: no mission leads;
- current S21/Railways leads: 0.

Therefore this hardening adds future backup coverage without manufacturing a present gap.
