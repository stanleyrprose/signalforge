# MTE Reviewed Image Enrichment v1 — Production Closure — 2026-09-11

## Scope

This closure records production acceptance of the source-scoped reviewed enrichment for the exact Myanma Timber Enterprise S32 commercial event `mte:1605`:

`Local Marketing and Milling Department, Open Tender No (6/2026-2027)(15.9.2026)`.

The change is intentionally a **read-model enrichment only**. It does not rewrite canonical evidence, manufacture historical Signal rows, change source acquisition, add a schema migration, change qualification/priority policy, or expand the SignalForge Provider contract to invoke OCR.

## Why this change was required

The official MTE HTML page exposed the event identity and event date, while important business fields were carried by the official image. A prior manual review had two factual errors:

- event time was stored as `09:30`, but the official image states `08:30`;
- quantity was interpreted as `6 categories/types`, but the official image states approximately `6,243 tons` of logs/sawn timber.

The corrected reading was cross-checked with local Burmese + English OCR against the **same official image SHA-256**. OCR is supporting evidence only; it is not treated as an automatic canonical source of truth.

## Accepted reviewed facts

Exact reviewed identity:

```text
source_id        = S32
canonical_key    = mte:1605
item_kind        = AUCTION_NOTICE
reference_no     = MTE-LOCAL-6/2026-2027
action_date      = 2026-09-15
article_url      = https://mte.gov.mm/index.php/en/annoucements/17-tenders/local-milling-marketing-dept-tender/1605-392026
image_url        = https://mte.gov.mm/images/2022/ll%20sep.jpg
image_sha256     = 6a6c2452cf8ae18bf4985c3bd77f63bbd77ec710ad5b37ae3db51409854348e1
```

Reviewed fields accepted for the read model:

```text
action_time             = 08:30
location                = Myanma Timber Enterprise, Gyogon Forest Compound, Insein Township, Yangon
quantity_or_lot_summary = Approximately 6,243 tons of teak/hardwood logs and sawn timber
quantity confidence     = HIGH
next action             = follow the MTE Local Marketing & Milling Department tender/auction application process and pre-submit required Earnest Money by Payment Order
```

No bid-submission deadline is inferred from the event date. The event remains an `AUCTION_NOTICE / SELLER_OPEN_TENDER_SALE / BUY_FROM_ISSUER` commercial opportunity.

## Implementation boundary

The enrichment registry is `registry/MTE-Reviewed-Image-Enrichments-v1.json`.

The overlay is fail-closed and applies only when the following reviewed identity fields match:

- source id;
- canonical key;
- item kind;
- reference number;
- action date;
- article URL when supplied.

Application semantics:

- canonical/HTML fields win;
- reviewed values only fill missing read-model fields;
- reviewed provenance is surfaced in the opportunity/briefing payload;
- `current_opportunities` is enriched without mutating stored canonical payloads;
- Auditor independently re-fetches the reviewed official image and verifies its SHA-256;
- an image SHA mismatch is a RED audit finding;
- Signal Quality may consume reviewed quantity/time/location/next-action evidence, but remains independent from `priority_band`.

## Verification before merge

Feature PR: **#157 — `feat: enrich reviewed MTE commercial event`**.

Feature head:

`f90fc4f56d66776d89d2b6311ffb8ad2926dca67`

Verification:

```text
targeted enrichment/opportunity/Telegram tests = 27 passed
full suite                                      = 299 passed
GitHub Actions verify run                       = 34620976113 PASS
```

PR #157 squash-merged to `main` as:

`6a1e8ea4a6b7df5f628ea428d959de50e0dc3f5c`

## Exact production deployment

Pre-deploy Bangkok runtime / rollback target:

`b9fc1b3feaaa73ad9bbacade2dd5ad967a7cd234`

Exact merged Git archive SHA-256:

`c010edab2413fc57da4941bc0eecb778236fd166627c2e9e7204a6e44b4dc6b9`

The archive SHA matched locally and on Bangkok before deployment.

The standard atomic SignalForge release script deployed:

`6a1e8ea4a6b7df5f628ea428d959de50e0dc3f5c`

and reported:

```text
deployment=success
previous=b9fc1b3feaaa73ad9bbacade2dd5ad967a7cd234
timer_preexisting=1
```

The acquisition, immediate Telegram delivery, and daily digest timers were restored by the existing deployment mechanism.

## Live production acceptance

Immediately after deployment, the S32 opportunity read model returned exactly one current MTE opportunity with the corrected reviewed fields:

```text
canonical_key                  = mte:1605
action_at                      = 2026-09-15T08:30:00+06:30
action_time                    = 08:30
quantity_or_lot_summary        = Approximately 6,243 tons of teak/hardwood logs and sawn timber
quantity_or_lot_confidence     = HIGH
location                       = Myanma Timber Enterprise, Gyogon Forest Compound, Insein Township, Yangon
priority_band                  = REVIEW
trust_grade                    = B
signal_quality_score           = 86
signal_quality_band            = VERY_HIGH
reviewed_enrichment_read_only  = true
reviewed_image_sha256          = 6a6c2452cf8ae18bf4985c3bd77f63bbd77ec710ad5b37ae3db51409854348e1
opportunity_status             = OPEN
```

The important distinction is preserved: **Signal Quality improved because the evidence is more complete, but priority remains `REVIEW`**. The enrichment does not silently upgrade interrupt policy or fabricate a deadline.

## Auditor acceptance

A live Bangkok network Auditor run after deployment returned:

```text
status                                  = PASS
finding_count                           = 0
source_health.checked_sources           = 27
source_health.non_green_sources         = 0
reviewed_mte_image_evidence.status      = PASS
reviewed_mte_image_evidence.records     = 1
reviewed_mte_image_evidence.images_checked = 1
reviewed_mte_image_evidence.sha_matches = 1
```

The global completeness boundary remains unchanged: external completeness is still `NOT_PROVEN`; the Auditor only proves its explicitly bounded checks.

## Delivery / state safety

The production change does not alter delivery identity or create a new Signal. Post-deploy Telegram dry-run returned:

```text
status        = PASS
pending_count = 0
```

Therefore the reviewed enrichment did **not** replay or duplicate the already-delivered MTE alert.

At the pre-deploy health snapshot, production was `PASS/GREEN`, backlog `0`, with `212 canonical / 53 signals`; these counts are live operational state and may naturally increase as scheduled acquisition continues. Deployment itself was not used to mutate those business records.

## Relationship to Mac Browser Plane OCR P0

Mac Browser Plane OCR P0 was independently merged and production-accepted before this SignalForge closure. It uses local Tesseract 5.5.3 with runtime-local `tessdata_best` `mya+eng` and no network access.

For the same MTE image SHA it recovered the Burmese-script values corresponding to:

- `6243`;
- `15-9-2026`;
- `08:30`.

That OCR result was used as a **cross-check for human-reviewed evidence**, not as an automatic SignalForge production dependency.

The SignalForge Provider Invocation Contract still does **not** authorize `artifact_ocr`; automatic remote OCR routing is explicitly outside this closure.

## Final state

**PASS / PRODUCTION ACCEPTED.**

The system now exposes the corrected MTE commercial event as a substantially more actionable, evidence-rich Signal without violating the existing separation between acquisition, canonical truth, reviewed evidence, Signal Quality, priority policy, and delivery identity.

Rollback target remains:

`b9fc1b3feaaa73ad9bbacade2dd5ad967a7cd234`
