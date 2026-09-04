# S05A Ministry of Commerce Trade Notifications — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / LIVE TRANSPORT PASS

## Decision

S05A is the first authorized `REGULATORY_NOTICE` source slice. It must not be represented as a tender.

The source remains Bangkok-only and Direct-HTTP-first. Browser, remote Provider, Mac production, PDF extraction and distributed runtime are not triggered.

## Official source shape

Primary discovery endpoint:

```text
https://commerce.gov.mm/my/node/32071
```

The stable Myanmar-language Notifications quicktab is a Drupal view identified by:

```text
view-display-id-block_3
```

The page also exposes yearly notification archive links. The Myanmar-language source is the completeness truth: fresh audit found 43 notices in the 2026 Myanmar archive versus 28 in the English archive.

The permanent Notifications page is used for incremental discovery so the production contract does not encode a calendar year.

## Business selection

The source is `ACTIVE_SELECTIVE`, not an all-content feed.

Current selection policy admits trade/business regulatory events such as:

- import/export operating notices;
- import reference/pricing notices;
- product-control notices;
- market-supply notices.

Training, recruitment, exam-result and similar administrative noise is rejected before canonicalization. A successfully fetched but non-selected detail is a successful processing result with zero canonical items, not a parser failure.

## Canonical domain contract

Schema version advances from v4 to v5 additively.

`canonical_items` adds:

```text
item_kind
title
```

Existing rows are migrated as:

```text
item_kind = TENDER
title = project_name
```

S05A canonical items use:

```text
item_kind = REGULATORY_NOTICE
canonical_key = commerce-notice:<issuer-node-id>:<publication-date>
```

Legacy tender payload hashes are unchanged because the new storage discriminator is not injected into existing tender payloads. This prevents a schema-only migration from generating false `UPDATED` signals for S13/S20/S21/S22.

## Scheduler metric separation

Schema v5 also adds generic:

```text
items_parsed
```

Historical v4 rows are backfilled from `tenders_parsed`.

New semantics:

```text
Tender source:
items_parsed   = N
tenders_parsed = N

S05A regulation source:
items_parsed   = N
tenders_parsed = 0
```

Thus regulatory notices are not counted as tenders in operational evidence.

## HTML / PDF boundary

Commerce detail HTML reliably exposes event metadata including:

- issuer-original article URL / node id;
- title;
- publication timestamp;
- notice/reference label when present;
- official attachment link when present.

Official PDFs are currently retrievable for audited examples, but the production primary pipeline does not fetch or parse them.

S05A attachment policy is:

```text
METADATA_ONLY_NON_BLOCKING
fetch_in_primary_pipeline = false
```

Therefore this slice detects and canonicalizes the regulatory event but does not claim to have extracted the full rule text from the attachment.

## Fresh current-live parser verification

Frozen implementation against the current official page returned:

```text
discovered = 15
latest publication = 2026-09-01T05:45:43+00:00
latest node = 33089
```

Audited current business item node `32972` parsed as:

```text
item_kind = REGULATORY_NOTICE
notice_category = IMPORT_EXPORT
publication_date = 2026-06-19
official attachment metadata = present
```

## Bangkok production-network verification

Using the existing production SignalForge Direct HTTP fetcher from Bangkok with normal TLS verification:

```text
Notifications page -> HTTP fetch PASS / HTML
node 32972 detail   -> HTTP fetch PASS / HTML
```

Fresh response sizes during the pre-production check were approximately 187 KB and 115 KB respectively.

No Browser or TLS-bypass evidence exists.

## Test evidence

Targeted affected suite:

```text
30 / 30 PASS
```

Full CI-equivalent Python suite:

```text
39 / 39 PASS
```

Also passed:

- Python compileall;
- Source Registry JSON validation;
- shell syntax validation;
- `git diff --check`;
- v4 -> v5 scheduler-history backfill regression;
- S13/S20/S21/S22 regression coverage;
- baseline zero-signal behavior;
- one material regulatory update -> exactly one `UPDATED` signal;
- PDF never fetched by the primary S05A engine path;
- non-selected notification -> processing success with zero canonical item.

## Pre-production gate

Implementation is ready for PR/CI and controlled rollout.

Production is not complete until all of the following pass on Bangkok:

1. exact merged SHA deployment;
2. schema v5 migration with SQLite quick check;
3. controlled `signalforge-refresh S05A` first baseline;
4. zero customer signals from the first baseline;
5. `item_kind=REGULATORY_NOTICE` rows only for S05A;
6. `items_parsed > 0` while `tenders_parsed = 0` for the S05A baseline;
7. S13/S20/S21/S22 remain healthy with no migration-generated false signals;
8. one manual refresh remains one Worker application Run;
9. Beijing retains strict SignalForge absence;
10. Bangkok and Beijing worker doctors pass;
11. scheduler timer is restored to enabled/active/waiting.
