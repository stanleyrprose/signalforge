# S23 Verified-External Promotion + Scorecard Consistency — Production Closure

Date: 2026-09-18

## Goal

Close the gap between evidence quality and customer-facing opportunity quality without weakening canonical truth or the S23 strict-TLS activation gate.

The Ministry of Construction S23 acquisition source remains disabled because its normal strict-TLS activation gate is still blocked. However, the current Yangon–Mandalay Expressway tender had already been captured as a reviewed coverage gap. The remaining question was whether the official issuer document was strong enough to count as a non-canonical verified business opportunity.

## Official-document revalidation

Audit-only retrieval of the exact official issuer URL:

`https://construction.gov.mm/letter-download/18be5b60-accb-11f1-b41f-3517e3a380a0`

returned HTTP 200 `application/pdf`.

The live PDF SHA256 exactly matched the previously reviewed registry fingerprint:

`161e6400cb19ef0b6bf116d73745f4b2efdb8a0c7b45e9468632e388481277c0`

The official one-page text PDF explicitly proves:

- issuer/business unit: Ministry of Construction / Roads Department / Yangon–Mandalay Expressway maintenance, repair and supervision group;
- scope: 2026–2027 Yangon–Mandalay Expressway road-construction materials procurement;
- tender-form sale start: 2026-09-10 10:00;
- bid submission deadline: 2026-09-23 16:00;
- participation location: the expressway maintenance/repair/supervision group office in Nay Pyi Taw;
- official contact information is present in the PDF.

This satisfies issuer identity, scope, deadline/actionability and immutable reviewed-document hash requirements.

## PR #209 — verified external business promotion

Merge SHA:

`f5fccd2037b78f558358bea62017755d2ba81460`

The S23 record was promoted to `VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY` in the reviewed read layer only.

Important invariants remained unchanged:

- `canonical_truth=false`;
- no canonical item was created;
- no Signal was created;
- S23 acquisition remained `enabled=false`;
- S23 role remained `DEFERRED_READY`;
- activation gate remained `STRICT_TLS_HTTPS / BLOCKED_ISSUER_CERT_EXPIRED`;
- no TLS bypass was introduced into production acquisition.

A `resolution_reviewed_at=2026-09-18` gate preserves historical semantics: 2026-09-16 and 2026-09-17 historical queries still see the item as a reviewed coverage gap; only 2026-09-18 onward sees the verified-external business resolution.

The Business Digest verified-external renderer was extended to allow the official `construction.gov.mm` document link.

## Test-sensor correction

During validation, `tests/test_coverage_gaps.py` was found to contain pytest-style top-level test functions while the repository CI executes `python -m unittest discover -s tests`. The file therefore existed but was not part of the primary CI sensor.

It was converted to `unittest.TestCase`, raising the primary discovered suite from 398 tests to 405 tests.

Validation for PR #209:

- coverage/digest/scorecard focused regression: PASS;
- pytest coverage-gap file: 7/7 PASS;
- default Python full unittest suite: 405/405 PASS;
- Python 3.13 full unittest suite: 405/405 PASS;
- compileall, registry parsing, shell syntax and `git diff --check`: PASS.

The production DB-copy preview changed business output exactly as intended:

- current target opportunities: 9 -> 10;
- canonical current opportunities: 8 unchanged;
- verified external opportunities: 1 -> 2;
- unresolved reviewed coverage gaps: 1 -> 0;
- MEDIUM: 6 -> 7;
- REVIEW: 1 unchanged;
- Attention: 3 unchanged.

## Production result after PR #209

Bangkok active release became:

`f5fccd2037b78f558358bea62017755d2ba81460`

Live DB remained:

- canonical items: 243;
- Signals: 64;
- S23 canonical items: 0;
- S23 Signals: 0;
- `PRAGMA quick_check=ok`.

All four timers remained enabled.

The live Business Digest correctly rendered the S23 tender in the verified-official section with the official PDF, 2026-09-23 16:00 deadline and next action.

## Scorecard inconsistency found during live verification

Post-deploy validation exposed one remaining metric inconsistency:

- Business Digest business layer: `10 current / 8 canonical / 2 verified external`;
- source-scorecard summary: `9 current / 8 canonical / 1 verified external`.

Root cause: verified external opportunities were grouped by target source, but the source-scorecard row loop only iterated `registry.enabled_sources()`. Because S23 is intentionally disabled, the valid S23 external opportunity was dropped when the summary was computed.

The fix must not create a fake active S23 source row merely to make the totals match.

## PR #210 — scorecard summary consistency

Merge SHA:

`3f66cf073c7e297f18e3b412eff06010286d872c`

Source-scorecard semantics are now:

- `sources[]` continues to describe active sources only;
- `canonical_current_opportunities` is the active canonical-current total;
- `verified_external_opportunities` counts all mission-qualified verified-external business opportunities, including those whose target source is disabled/deferred;
- `current_opportunities = canonical_current_opportunities + verified_external_opportunities`;
- new metric `verified_external_non_active_source_opportunities` makes the disabled/deferred-source contribution explicit.

A regression test proves that an S23-style external opportunity:

- increases the scorecard business summary;
- does not create an S23 active source row.

Validation for PR #210:

- focused source-scorecard tests: 10/10 PASS on default Python and Python 3.13;
- production DB-copy consistency preview:
  - business: `10 / 8 / 2 / gap0`;
  - scorecard: `10 / 8 / 2`;
  - verified external from non-active source: `1`;
- default Python full unittest suite: 406/406 PASS;
- Python 3.13 full unittest suite: 406/406 PASS;
- compileall, registry parsing, shell syntax and `git diff --check`: PASS.

GitHub Actions for PR #209 and PR #210 did not execute repository code because GitHub rejected the jobs before startup due to account payment/spending-limit state. Equivalent Python 3.13 workflow checks were executed locally and passed.

## Final production state

Bangkok active release:

`3f66cf073c7e297f18e3b412eff06010286d872c`

Rollback release:

`f5fccd2037b78f558358bea62017755d2ba81460`

Live verification:

- DB `quick_check=ok`;
- canonical items: 243;
- Signals: 64;
- S23 canonical items: 0;
- S23 Signals: 0;
- Business Digest: `10 current / 8 canonical / 2 verified external / gap0 / Attention3`;
- source-scorecard: `10 current / 8 canonical / 2 verified external / non-active external1`;
- run-due, Telegram deliver, Telegram digest and assurance timers: all enabled;
- S23 remains disabled and strict-TLS blocked;
- the 2026-09-18 Telegram digest dry-run uses the new verified-official S23 text; its pending item is the normal daily digest, not an immediate Signal replay.

## Decision

This closes the S23 business-output issue.

The system now distinguishes three concepts correctly:

1. canonical acquisition truth;
2. independently reviewed official business coverage;
3. active-source health/yield.

A high-quality official tender can contribute to customer business coverage without being represented as canonical or forcing a disabled source to appear healthy.
