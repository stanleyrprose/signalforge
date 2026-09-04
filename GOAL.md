# GOAL — SignalForge Myanmar Source Expansion

## Goal

Expand SignalForge across high-value Myanmar issuer-original sources while preserving the proven v1.5 local acquisition contract and the existing Worker / Control / Fleet boundaries.

## Frozen production boundary

- SignalForge production remains Bangkok-only.
- Beijing remains Generic Worker only and SignalForge-free.
- Direct HTTP remains the default production acquisition method.
- One SignalForge scheduler/service invocation creates one Worker operational Run; source/business jobs and acquisition attempts remain internal SignalForge state.
- `AcquisitionRequest` and `AcquisitionAttempt` are not Worker Runs.
- Worker DB has no SignalForge source/canonical/acquisition business semantics.
- Source adapters follow real issuer shape; there is no universal tender parser requirement.
- TLS/HTTP failures stay fail-closed and do not silently become certificate bypass or Browser escalation.
- Browser execution belongs only to the Mac Browser Plane; VPS Browser/Crawlee R3 is superseded. SignalForge→Mac unattended production invocation remains disabled until a separate Provider Invocation Contract is approved; Browserless/PDF/distributed coordination remain evidence-triggered future capabilities.

## Current production sources

### S13 — MPT Tender Information

- production-enabled;
- Direct HTTP / issuer sitemap + structured detail parser;
- source health GREEN.

### S07 — Myanmar Customs Notifications

- production-enabled; first Customs Notifications onboarding release was `edf3e342ad127b4beac93a285bfb0096a1815aaa`;
- issuer-original `REGULATORY_NOTICE` source;
- listing-complete Direct HTTP shape: one `/notifications` HTML acquisition directly yields current business records;
- canonical identity is normalized issuer notification/order number (`customs-notice:<ref>`);
- first baseline created 5 regulatory canonical items and zero customer signals;
- baseline metrics: `items_parsed=5`, `tenders_parsed=0`, `details_attempted=0`;
- official PDF links remain metadata-only and are not fetched by the primary pipeline;
- parse health uses `BUSINESS_PROCESSING`; first production sample `1/1 = GREEN`;
- source health GREEN;
- evidence: `docs/verification/S07-SOURCE-ONBOARDING-2026-09-04.md`.

### S08A — Myanmar Customs Auction Announcements

- production-enabled on current application release `cb5291fdfcc13a678f63b53072e39089f8c27258`;
- `ACTIVE_SELECTIVE` auction-opportunity slice from the mixed Customs Announcements page;
- canonical domain is `AUCTION_NOTICE`; tender-award/result records remain explicitly excluded from this slice;
- visible issuer publication text is authoritative because the current HTML `datetime` attribute is stale (`2025-05-13`);
- first baseline created 4 auction canonical items and zero customer signals;
- baseline metrics: `items_parsed=4`, `tenders_parsed=0`, `details_attempted=0`;
- official PDF paths are safely percent-encoded as metadata only; current PDFs are mixed text-native/scan and are not fetched by the primary pipeline;
- no OCR/PDF parser/Browser capability was introduced;
- parse health uses `BUSINESS_PROCESSING`; source health GREEN;
- evidence: `docs/verification/S08A-SOURCE-ONBOARDING-2026-09-04.md`.

### S05A — Ministry of Commerce Trade Notifications

- production-enabled; first regulation-domain onboarding release was `3c833d62dcf16ecd9e4b12dafd9ac557417efddb`;
- first production `REGULATORY_NOTICE` domain slice, explicitly not represented as a tender;
- `ACTIVE_SELECTIVE` Myanmar-language Drupal Notifications discovery;
- current baseline created 3 regulatory canonical items and zero customer signals;
- baseline metrics: `items_parsed=3`, `tenders_parsed=0`, parse `3/3 = 1.0`;
- official PDF links are preserved as metadata only and are not fetched in the primary pipeline;
- source health GREEN;
- evidence: `docs/verification/S05A-SOURCE-ONBOARDING-2026-09-04.md`.

### S20 — MOEP Main Tender Hub

- production-enabled; first onboarding release was `255f18f3dd919b6e77b9d3138839f0439062e3bc`;
- `ACTIVE_SELECTIVE` HTML-first source;
- official discovery: `https://moep.gov.mm/mm/ignite/page/62`;
- current first page exposes five latest tenders with issuer/date/summary/detail URL;
- first production baseline parsed 5/5 detail pages and created zero customer signals;
- source health GREEN / parse `5/5 = 1.0`;
- current advertised PDF attachments are degraded (`0/5` retrievable, HTTP 404) but are metadata-only and non-blocking;
- no PDF parser or Browser capability is in the primary pipeline;
- evidence: `docs/verification/S20-SOURCE-ONBOARDING-2026-09-04.md`.

### S21 — Myanma Railways Tenders

- production-enabled;
- Direct HTTP / category-list discovery + multi-item detail parser;
- first production baseline parsed 45 business tenders from 10 detail pages;
- first baseline created zero customer signals;
- source health GREEN;
- evidence: `docs/verification/S21-SOURCE-ONBOARDING-2026-09-04.md`.

### S22 — Inland Water Transport Tenders

- production-enabled;
- Direct HTTP / Drupal tender-list discovery + one-detail/one-business-item parser;
- current HTML exposes title, scope, publication time, closing time and attachment metadata;
- first production baseline parsed four audited 2026 tender nodes;
- first baseline created zero customer signals;
- source health GREEN;
- evidence: `docs/verification/S22-SOURCE-ONBOARDING-2026-09-04.md`.

## Current result

> **S05A + S07 + S08A + S13 + S20 + S21 + S22 = PRODUCTION / GREEN**

SignalForge has now proven seven source/domain shapes under the same v1.5 acquisition lifecycle:

```text
Commerce: one Drupal notice -> zero/one selected REGULATORY_NOTICE + attachment metadata
Customs Notifications: one listing HTML -> N REGULATORY_NOTICE records, no synthetic detail stage
Customs Auctions:      one mixed announcements HTML -> selected AUCTION_NOTICE records, award/result excluded
MPT:      one detail page -> zero/one tender
MOEP:     one category item -> one partial HTML tender + attachment metadata
Railways: one detail page -> N tender rows
IWT:      one Drupal tender node -> one tender + attachment metadata
```

All remain inside one Bangkok SignalForge application boundary and the existing Worker operational envelope.

## Important S20 epistemic boundary

MOEP currently provides strong discovery but incomplete business qualification in HTML. The latest advertised PDFs return HTTP 404 from Bangkok and must not be treated as usable evidence.

Therefore:

```text
HTML tender event = production evidence
PDF URL           = attachment metadata only
PDF content       = unavailable / not claimed
missing deadline  = unknown, not inferred
```

If MOEP attachments become reliably retrievable, a supplementary PDF gate may be evaluated independently. It must not weaken HTML source health or become a silent hard dependency.

## Next authorized direction

Continue source expansion one source at a time through:

```text
business-value audit
-> fresh network / endpoint / shape re-audit
-> Direct HTTP fixture
-> source adapter / parser
-> baseline suppression
-> health
-> exact-SHA production deploy
-> live verification
-> checkpoint closure
```

The next source should be selected by business value and current audit evidence, not simply by source ID order. S01 National Portal remains deferred as a canonical source because aggregator metadata conflicts with issuer-original evidence; keep it only for a future discovery-lead contract. S05A, S07 and S08A are now production-complete and prove regulation plus auction-opportunity source shapes without tender semantic leakage. The preferred next issuer-original audit pool is S04 Trade Portal legal documents and S12 IRD. S08A tender-award/result content remains a separate future `PROCUREMENT_RESULT` decision rather than part of the auction slice. YCDC/MCDC/NPTDC retain their identity/PDF/classifier conditions and must not be force-onboarded merely to increase source count.
