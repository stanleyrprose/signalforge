# GOAL — SignalForge Myanmar Source Expansion

## Goal

Expand SignalForge across high-value Myanmar issuer-original sources while preserving the proven v1.5 local acquisition contract and the existing Worker / Control / Fleet boundaries.

## Frozen production boundary

- SignalForge production remains Bangkok-only.
- Beijing remains Generic Worker only and SignalForge-free.
- Direct HTTP is the default production acquisition method.
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

### S21 — Myanma Railways Tenders

- production-enabled;
- Direct HTTP / category-list discovery + multi-item detail parser;
- first production baseline parsed 45 business tenders from 10 detail pages;
- first baseline created zero customer signals;
- source health GREEN;
- evidence: `docs/verification/S21-SOURCE-ONBOARDING-2026-09-04.md`.

### S22 — Inland Water Transport Tenders

- production-enabled on `9ec2b133ca1c3339abccf34c5f5c86cecd3e6023`;
- Direct HTTP / Drupal tender-list discovery + one-detail/one-business-item parser;
- current HTML directly exposes title, scope, publication time, closing time and attachment metadata;
- first production baseline parsed four audited 2026 tender nodes;
- first baseline created zero customer signals;
- source health GREEN and parse ratio `4/4 = 1.0` at baseline;
- PDF remains metadata-only; no PDF parser was required or activated;
- evidence: `docs/verification/S22-SOURCE-ONBOARDING-2026-09-04.md`.

## Current result

> **S13 + S21 + S22 = PRODUCTION / GREEN**

SignalForge has now proven three useful source shapes under the same v1.5 acquisition lifecycle:

```text
MPT:      one detail page -> zero/one tender
Railways: one detail page -> N tender rows
IWT:      one Drupal tender node -> one tender + attachment metadata
```

All remain inside one Bangkok SignalForge application boundary. A single scheduler wrapper can process multiple due source jobs while remaining one Worker operational Run.

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

The next preferred engineering candidate is **S20 MOEP Main Tender Hub**, but it must first receive a fresh business/endpoint/shape audit. Its prior classification was `GREEN-CANDIDATE HTML / YELLOW-PDF-PENDING`: HTML may be sufficient for discovery/identity while detailed equipment lots can live in PDF. Do not automatically add a PDF pipeline; first prove which business fields are actually missing from HTML and whether that gap matters to the R0 commercial wedge.

YCDC/MCDC/NPTDC retain their previously identified identity/PDF/classifier conditions. Do not bypass those gates merely to increase source count.
