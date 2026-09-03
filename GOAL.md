# GOAL — SignalForge Myanmar Source Expansion

## Goal

Expand SignalForge from the proven S13 MPT production baseline to additional high-value Myanmar issuer-original sources while preserving the v1.5 local acquisition contract and the existing Worker / Control / Fleet boundaries.

## Frozen production boundary

- SignalForge production remains Bangkok-only.
- Beijing remains Generic Worker only and SignalForge-free.
- Direct HTTP is the default production acquisition method.
- One SignalForge scheduler/service invocation creates one Worker operational Run; source/business jobs and acquisition attempts remain internal SignalForge state.
- `AcquisitionRequest` and `AcquisitionAttempt` are not Worker Runs.
- Worker DB has no SignalForge source/canonical/acquisition business semantics.
- Source adapters may differ by real source shape; there is no universal tender parser requirement.
- TLS failure stays fail-closed and never becomes certificate bypass or automatic Browser escalation.
- Browser, remote Provider, Mac production, Browserless and distributed coordination remain evidence-triggered capabilities, not default infrastructure.

## Current production sources

### S13 — MPT Tender Information

- production-enabled;
- Direct HTTP / issuer sitemap + structured detail parser;
- source health GREEN.

### S21 — Myanma Railways Tenders

- production-enabled on `52c9ab5b5e5643014e1b55a634cc5fbe26c0ebac`;
- Direct HTTP / category-list discovery + multi-item detail parser;
- first production baseline parsed 45 business tenders from 10 detail pages;
- first baseline created zero customer signals;
- source health GREEN;
- production onboarding evidence: `docs/verification/S21-SOURCE-ONBOARDING-2026-09-04.md`.

## Current result

> **S13 + S21 = PRODUCTION / GREEN**

SignalForge has now proven two source shapes under the same v1.5 acquisition lifecycle:

```text
MPT:      one detail page -> zero/one tender
Railways: one detail page -> N tenders
```

Both remain inside one Bangkok SignalForge application boundary and one Worker operational envelope per scheduler/manual invocation.

## Next authorized direction

Continue source expansion one source at a time through:

```text
business-value audit
-> current network / endpoint re-audit
-> Direct HTTP fixture
-> source adapter / parser
-> baseline suppression
-> health
-> exact-SHA production deploy
-> live verification
-> checkpoint closure
```

The next preferred candidate from the completed engineering source audit is **S22 Inland Water Transport**, subject to a fresh endpoint/shape re-audit before implementation. S20 MOEP Main remains another provisional candidate; YCDC/MCDC/NPTDC retain their previously identified identity/PDF/classifier conditions.

Do not trigger Browser, remote Provider, Mac production or distributed runtime merely because another source is being added.
