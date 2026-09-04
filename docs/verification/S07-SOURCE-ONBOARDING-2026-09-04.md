# S07 Myanmar Customs Notifications — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / LIVE TRANSPORT PASS

## Decision

S07 is an issuer-original `REGULATORY_NOTICE` source using a new but bounded source shape:

```text
listing HTML itself
-> complete regulatory-event records
-> canonicalization
```

There is no issuer HTML detail page between the listing row and the official PDF attachment. The production primary path therefore must not invent a fake detail URL and must not re-fetch the same listing once per row.

## v1.5.1 Browser-plane compliance

S07 remains Direct-HTTP-only on Bangkok.

The Mac Browser Plane integration amendment is preserved:

```text
VPS Browser/Crawlee R3 = SUPERSEDED_BY_MAC_BROWSER_PLANE
browser_production_approved = false
```

No Chrome, Playwright, Crawlee, Browserless, remote Mac invocation, public CDP, or ad-hoc Browser API is introduced by S07.

If Customs later proves browser execution is actually required, S07 must become capability-blocked while the Mac Browser Provider is production-disabled; it must not trigger Bangkok/Beijing Browser installation.

## Official endpoint / current shape

Primary endpoint:

```text
https://customs.gov.mm/notifications
```

Fresh audit found five current records on page 1. Each table row exposes:

- issuer notification/order number;
- regulatory title;
- official PDF attachment URL.

Current examples:

```text
124/2026 -> HSD (500 ppm) customs-duty reduction extension
123/2026 -> LNG customs-duty reduction extension
103/2026 -> customs-duty reduction period extension
104/2026 -> customs-duty reduction determination
87/2026  -> customs-duty reduction determination
```

Page 2 already contains older 2026/2025 records. The production incremental contract monitors page 1 only; historical backfill is intentionally separate from forward monitoring.

## Canonical identity

Issuer reference is authoritative identity:

```text
customs-notice:<normalized issuer notification/order number>
```

Examples:

```text
customs-notice:124/2026
customs-notice:123/2026
```

Myanmar digits are normalized to ASCII digits and spacing around `/` is removed. The URL is not used as canonical identity.

The listing does not expose a trustworthy publication date, so:

```text
publication_date = unknown / null
```

No date is inferred from PDF filenames or page ordering.

## Item semantics

S07 rows are stored as:

```text
item_kind = REGULATORY_NOTICE
project_name = title      # legacy storage alias only
```

Operational metrics preserve domain separation:

```text
items_parsed   = N
tenders_parsed = 0
details_attempted = 0
details_succeeded = 0
```

S07 is not represented as a tender.

## Listing-complete engine capability

`SourceAdapter` now has an optional `parse_discovery_records` contract.

When present:

```text
1 Direct HTTP discovery acquisition
-> 1 EvidenceEnvelope
-> 1 business ProcessingRecord
-> N canonical items
```

No `discovery_items` backlog rows or synthetic detail candidates are created for this source shape.

Existing S05A/S13/S20/S21/S22 adapters continue using the existing discovery/detail lifecycle unchanged.

## Parse-health semantics

S07 uses:

```text
parse_sample_source = BUSINESS_PROCESSING
```

This measures recent business `processing_records` instead of legacy detail-attempt counters. The first successful listing-business parse therefore provides a valid run-level parse sample without pretending a detail request occurred.

Existing sources default to:

```text
DETAIL_SCHEDULER
```

and retain their previous health semantics.

## HTML / PDF boundary

Official PDFs are currently reachable, including fresh Bangkok checks of the current HSD and LNG attachments.

S07 primary policy remains:

```text
METADATA_ONLY_NON_BLOCKING
fetch_in_primary_pipeline = false
```

The PDF URL and filename are canonical metadata. PDF contents are not fetched or parsed by the primary source pipeline.

## Bangkok transport verification

Using the production SignalForge Direct HTTP fetcher from Bangkok with normal TLS verification:

```text
/notifications read 1 -> PASS / 66099 bytes / ~0.34s
/notifications read 2 -> PASS / 66099 bytes / ~0.30s
/notifications read 3 -> PASS / 66099 bytes / ~0.48s
124/2026 HSD PDF     -> PASS / %PDF-1.7
123/2026 LNG PDF     -> PASS / %PDF-1.3
```

The successful PDF transport check establishes attachment availability only; it does not authorize PDF extraction.

## Frozen-parser current-live verification

The implementation parser against the current issuer page returned:

```text
records=5
124/2026 CUSTOMS_TARIFF
123/2026 CUSTOMS_TARIFF
103/2026 CUSTOMS_TARIFF
104/2026 CUSTOMS_TARIFF
87/2026  CUSTOMS_TARIFF
```

## Live isolated engine verification

Using the current official page with the real S07 engine path and an isolated temporary SQLite database:

```text
status=SUCCESS
baseline=true
listing_complete=true
discovered=5
items=5
tenders=0
details_attempted=0
details_succeeded=0
changed=5
signals_created=0
backlog_remaining=0
```

Persistence:

```text
canonical=5
signals=0
acquisition_requests=1
acquisition_attempts=1
evidence_envelopes=1
processing_records=1
discovery_items=0
SQLite quick_check=ok
```

Fetch calls:

```text
https://customs.gov.mm/notifications
```

Exactly one network acquisition occurred; no PDF URL was requested.

## Test evidence

Targeted source/regression suite:

```text
23 / 23 PASS
```

Full CI-equivalent Python suite after contract-fixture update:

```text
43 / 43 PASS
```

Also passed:

- current-live parser verification;
- current-live isolated engine baseline;
- Python compileall;
- Source Registry JSON validation;
- shell syntax validation;
- `git diff --check`;
- existing S05A/S13/S20/S21/S22 regression coverage;
- same-reference material update -> exactly one `UPDATED` signal;
- baseline zero-signal behavior;
- one listing run -> one acquisition/evidence/processing lifecycle;
- primary pipeline PDF fetch count remains zero.

## Production gate

Production is not complete until all of the following pass:

1. PR CI success and exact merged SHA deployment to Bangkok only;
2. controlled timer pause / frozen pre-deploy business counts;
3. `signalforge-refresh S07` first production baseline;
4. zero customer signals from that baseline;
5. exactly five current `REGULATORY_NOTICE` canonical items unless the issuer page changes before rollout;
6. `items_parsed > 0`, `tenders_parsed = 0`, `details_attempted = 0`;
7. S07 acquisition lifecycle is one request/attempt/evidence/processing record and zero PDF acquisitions;
8. S07 parse health GREEN from `BUSINESS_PROCESSING`;
9. S05A/S13/S20/S21/S22 remain GREEN with unchanged business state except normal due-source activity;
10. one manual refresh remains one Worker SignalForge application Run;
11. Beijing retains strict `/srv/signalforge` absence and denies `signalforge-refresh S07`;
12. Bangkok and Beijing Worker doctors pass;
13. timer is restored to enabled / active / waiting;
14. no Browser-plane invariant from PRD v1.5.1 is violated.
