# S05A Ministry of Commerce Trade Notifications — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRODUCTION
Result: PASS / PRODUCTION COMPLETE

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

## Production rollout — PASS

Implementation PR `#21` passed CI and was squash-merged. Exact production SHA:

```text
3c833d62dcf16ecd9e4b12dafd9ac557417efddb
```

Immediate rollback target:

```text
255f18f3dd919b6e77b9d3138839f0439062e3bc
```

The timer was paused through the reviewed Control Plane verb before deployment. Frozen pre-deploy state:

```text
canonical_items=70
signals=10
scheduler_runs=151
acquisition_requests=182
acquisition_attempts=182
evidence_envelopes=182
processing_records=182
failed_runs=0
recovery_backlog=0
Worker SignalForge Runs=404
S13/S20/S21/S22=GREEN
timer=disabled/inactive
```

The exact merged SHA was deployed to Bangkok only. Deployment reported:

```text
deployment=success
release=3c833d62dcf16ecd9e4b12dafd9ac557417efddb
previous=255f18f3dd919b6e77b9d3138839f0439062e3bc
timer_preexisting=0
```

Post-migration verification before the S05A baseline:

```text
schema_versions=[1,2,3,4,5]
SQLite quick_check=ok
canonical_items=70
signals=10
scheduler_runs=151
item_kinds=TENDER:70
missing_titles=0
Worker SignalForge Runs=404
```

Thus schema v5 migration changed no business fact and created no Worker application Run.

## First S05A production baseline — PASS

Reviewed invocation:

```text
signalforge-refresh S05A
```

Live result:

```text
trigger_kind=MANUAL
baseline=1
status=SUCCESS
details_attempted=3
details_succeeded=3
items_parsed=3
tenders_parsed=0
changed=3
signals_created=0
worker_run_id=signalforge-20260904T023116Z-d16ef9d0
```

Business state:

```text
canonical_items: 70 -> 73
signals:         10 -> 10
scheduler_runs: 151 -> 152
```

S05A durable canonical state:

```text
canonical=3
item_kind=REGULATORY_NOTICE:3
signals=0
```

The three baseline items were issuer nodes `32972`, `33011` and `33037` covering import/export operator administration, market supply and product-control notices.

## Acquisition / PDF isolation — PASS

S05A persisted:

```text
acquisition_requests=16
acquisition_attempts=16
evidence_envelopes=16
processing_records=16
PDF requested_url count=0
```

This is one discovery acquisition plus fifteen bounded HTML detail acquisitions. The three selected business notices became canonical items; non-selected notices were acknowledged without becoming parser failures or canonical business objects.

## Worker correlation / topology — PASS

Worker cardinality around the manual S05A baseline:

```text
Worker SignalForge Runs: 404 -> 405
latest Worker Run=signalforge-20260904T023116Z-d16ef9d0 / SUCCESS
```

The Worker Run ID exactly matches the S05A scheduler row. One manual refresh therefore remains one Worker operational Run while the sixteen acquisition attempts remain internal SignalForge state.

Additional topology checks:

```text
Bangkok Worker doctor=PASS
Beijing Worker doctor=PASS
Beijing /srv/signalforge=ABSENT
Beijing signalforge-refresh S05A=126 / DENY: SignalForge is Bangkok-only
SQLite quick_check=ok
```

## Timer restoration — PASS

`signalforge-resume` restored:

```text
enabled / active / waiting
```

Resume immediately created one persistent Worker wrapper, so Worker SignalForge Runs changed `405 -> 406`. SignalForge `scheduler_runs` remained `152` and all business/acquisition counts remained unchanged, proving again that a Worker wrapper is not a business scheduler run.

## Final production state

```text
SignalForge release=3c833d62dcf16ecd9e4b12dafd9ac557417efddb
active sources=S05A,S13,S20,S21,S22
SignalForge health=GREEN
S05A health=GREEN
S05A parse=3/3
canonical_items=73
signals=10
scheduler_runs=152
acquisition_requests=198
acquisition_attempts=198
evidence_envelopes=198
processing_records=198
failed_runs=0
recovery_backlog=0
Worker SignalForge Runs=406
timer=enabled/active/waiting
```

S13/S20/S21/S22 remained GREEN through migration and rollout. No Browser, remote Provider, Mac production, PDF extraction or distributed coordination capability was triggered.
