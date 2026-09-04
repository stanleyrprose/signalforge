# S08A Myanmar Customs Auction Announcements — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / LIVE TRANSPORT PASS

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

## Production gate

Production is not complete until:

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
