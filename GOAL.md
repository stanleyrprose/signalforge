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
- Browser, remote Provider, Mac production, Browserless, PDF extraction and distributed coordination remain evidence-triggered capabilities rather than default infrastructure.

## Current production sources

### S13 — MPT Tender Information

- production-enabled;
- Direct HTTP / issuer sitemap + structured detail parser;
- source health GREEN.

### S20 — MOEP Main Tender Hub

- production-enabled on `255f18f3dd919b6e77b9d3138839f0439062e3bc`;
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

> **S13 + S20 + S21 + S22 = PRODUCTION / GREEN**

SignalForge has now proven four source shapes under the same v1.5 acquisition lifecycle:

```text
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

The next source should be selected by business value and current audit evidence, not simply by source ID order. Strong candidates from the existing audit pool include S01 National Portal, S04 Trade Portal legal documents, S05A Commerce Notifications, S07/S08A Customs and S12 IRD. YCDC/MCDC/NPTDC retain their identity/PDF/classifier conditions and must not be force-onboarded merely to increase source count.
