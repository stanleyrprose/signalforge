# S08A Myanmar Customs Auction Announcements — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRODUCTION
Result: PASS / PRODUCTION COMPLETE

## Decision

S08A is an `ACTIVE_SELECTIVE` Customs announcement source. The current page mixes business object types, so the first production slice canonicalizes only active auction-sale announcements as `AUCTION_NOTICE`.

The current tender-award/result announcement is explicitly excluded from this slice. It is not represented as a tender or regulatory notice; a future `PROCUREMENT_RESULT` slice requires its own business-value/extraction decision.

## Official source shape

Endpoint:

```text
https://customs.gov.mm/Announcements
```

Current first page contains five announcement articles:

- one tender-award/result announcement;
- four auction-sale announcements.

The site currently reuses stale article metadata: visible publication text is 2026-08-31/21/15/08 while the HTML `datetime` attribute remains `2025-05-13`. S08A therefore treats visible issuer text as publication evidence and ignores the stale machine attribute.

## Canonical contract

Selected items use:

```text
item_kind = AUCTION_NOTICE
canonical identity = publication_date + normalized title + attachment filename fingerprint
reference_no_kind = issuer_archive_record_fingerprint
```

The PDF URL alone is not canonical identity. Spaces and Myanmar path characters are percent-encoded for durable attachment metadata.

## PDF audit / boundary

All five current official PDFs are retrievable after safe URL percent-encoding.

Fresh text audit:

```text
tender-award PDF             -> text-native
Nyaung Khar Shay auction PDF -> text-native
auction-date PDF             -> text-native
Announcement_2.pdf           -> scan / extract_text=0
BGO Announcement.pdf         -> scan / extract_text=0
```

One text-native auction document exposes actionable details such as auction date `2026-08-27`, time `10:00`, and location in its PDF text. However two current auction PDFs are scans, so making full PDF extraction mandatory would immediately require Burmese OCR.

That capability is not introduced in S08A P0.

Production attachment policy remains:

```text
METADATA_ONLY_NON_BLOCKING
fetch_in_primary_pipeline = false
```

The operator/reviewer can follow the official attachment, but SignalForge does not claim full PDF-rule extraction.

## Browser-plane compliance

Direct HTTP is sufficient. No Browser requirement exists.

Per PRD v1.5.1:

```text
VPS Browser/Crawlee R3 = SUPERSEDED_BY_MAC_BROWSER_PLANE
browser_production_approved = false
```

No Chrome/Playwright/Crawlee, Mac remote invocation, public CDP, Browserless, OCR, or PDF production parser is added.

## Current-live parser

Frozen parser against the current issuer page selected four auctions:

```text
2026-08-21 Nyaung Khar Shay permanent inspection-station auction notice
2026-08-21 auction-sale date announcement
2026-08-15 auction-sale announcement
2026-08-08 Bago Township Customs auction announcement
```

The 2026-08-31 tender-award/result announcement is intentionally not selected.

## Current-live isolated engine

Using the real S08A engine path and a temporary SQLite database:

```text
status=SUCCESS
baseline=true
listing_complete=true
discovered=4
items=4
tenders=0
details_attempted=0
changed=4
signals_created=0
backlog_remaining=0
```

Persistence:

```text
item_kind=AUCTION_NOTICE:4
signals=0
requests/attempts/evidence/processing=1/1/1/1
discovery_items=0
PDF requested_url count=0
SQLite quick_check=ok
```

Fetch calls contained only:

```text
https://customs.gov.mm/Announcements
```

## Test evidence

Targeted source/regression suite:

```text
28 / 28 PASS
```

Full CI-equivalent suite:

```text
48 / 48 PASS
```

Also passed:

- current-live parser;
- current-live isolated engine baseline;
- Source Registry JSON validation;
- Python compileall;
- old S05A/S07/S13/S20/S21/S22 regressions;
- visible publication date contract;
- tender-award exclusion;
- encoded official attachment URLs;
- zero PDF fetch in primary path.

## Production rollout — PASS

PR #26 passed CI and was squash-merged. Exact application SHA deployed to Bangkok:

```text
cb5291fdfcc13a678f63b53072e39089f8c27258
```

Immediate rollback target:

```text
edf3e342ad127b4beac93a285bfb0096a1815aaa
```

The reviewed pause froze the pre-rollout state at:

```text
canonical_items=79
signals=11
scheduler_runs=198
acquisition_requests=262
acquisition_attempts=262
evidence_envelopes=262
processing_records=262
failed_runs=0
recovery_backlog=0
Worker SignalForge Runs=443
active sources=S05A,S07,S13,S20,S21,S22
all six existing sources=GREEN
timer=disabled/inactive
```

Deployment reported `timer_preexisting=0`; schema remained v5 (`1,2,3,4,5`) and all business counts were unchanged before the S08A baseline.

### First production baseline

Reviewed `signalforge-refresh S08A` returned:

```text
trigger_kind=MANUAL
baseline=1
status=SUCCESS
changed=4
items_parsed=4
tenders_parsed=0
details_attempted=0
details_succeeded=0
signals_created=0
worker_run_id=signalforge-20260904T074418Z-3e0d0021
```

State transition:

```text
canonical_items: 79 -> 83
signals:         11 -> 11
scheduler_runs:  198 -> 199
acquisition/evidence/processing: 262 -> 263
```

S08A persistence:

```text
canonical=4
item_kind=AUCTION_NOTICE:4
signals=0
requests/attempts/evidence/processing=1/1/1/1
discovery_items=0
PDF requested_url count=0
requested URL=https://customs.gov.mm/Announcements
SQLite quick_check=ok
```

Worker cardinality:

```text
Worker SignalForge Runs: 443 -> 444
latest Worker Run=signalforge-20260904T074418Z-3e0d0021 / SUCCESS
```

The Worker Run ID exactly matches the S08A scheduler row.

### Pause-window freshness aging and reconciliation

Because the rollout window remained intentionally paused long enough for existing sources to cross their freshness thresholds, the aggregate status temporarily became RED with reason `SOURCE_FRESHNESS_LAG` for the six pre-existing sources. Fetch health, parse health, failure counters, SQLite integrity and S08A health remained healthy; this was pause-window aging rather than a source/runtime failure.

After `signalforge-resume`, one persistent Worker wrapper (`444 -> 445`) executed bounded `RECONCILIATION` runs for S05A/S07/S13/S20/S21/S22. All six returned `SUCCESS`, `changed=0` and `signals_created=0`, clearing freshness lag back to GREEN. S08A was not due and was not repeated.

### Topology / timer restoration

```text
Bangkok Worker doctor=PASS
Beijing Worker doctor=PASS
Beijing /srv/signalforge=ABSENT
Beijing signalforge-refresh S08A=126 / DENY: SignalForge is Bangkok-only
```

Final state:

```text
release=cb5291fdfcc13a678f63b53072e39089f8c27258
active sources=S05A,S07,S08A,S13,S20,S21,S22
canonical_items=83
signals=11
scheduler_runs=205
acquisition_requests=274
acquisition_attempts=274
evidence_envelopes=274
processing_records=274
failed_runs=0
recovery_backlog=0
Worker SignalForge Runs=445
timer=enabled/active/waiting
all seven sources=GREEN
browser_production_approved=false
```

No Browser-plane invariant from PRD v1.5.1 was violated. No PDF/OCR production capability was introduced.

## Production gate — closed

All of the following passed:

1. PR CI passes and exact merged SHA is deployed to Bangkok only;
2. timer is paused and pre-deploy counts are frozen;
3. `signalforge-refresh S08A` baseline succeeds;
4. baseline creates zero customer signals;
5. current selected items persist as `AUCTION_NOTICE` only;
6. `items_parsed > 0`, `tenders_parsed=0`, `details_attempted=0`;
7. one HTML acquisition yields one request/attempt/evidence/processing lifecycle and zero PDF acquisitions;
8. S08A parse health is GREEN from `BUSINESS_PROCESSING`;
9. existing six sources remain GREEN;
10. one manual refresh remains one Worker SignalForge application Run;
11. Beijing remains SignalForge-free and rejects S08A refresh;
12. both Worker doctors pass;
13. timer returns to enabled/active/waiting;
14. PRD v1.5.1 Browser-plane invariants remain intact.
