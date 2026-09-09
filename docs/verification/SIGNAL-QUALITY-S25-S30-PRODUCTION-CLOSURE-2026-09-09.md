# Signal Quality / Business Completeness Production Closure — S25 + S30 — 2026-09-09

## Result

**PASS / PRODUCTION LIVE / SIGNAL QUALITY IMPROVED**

This closure records a deliberate shift from source-count expansion toward business-signal quality. The fresh source audit did not justify adding S41; instead, production evidence exposed two higher-value issues in already-live sources:

1. S25 MONPIFER was emitting repeated `UPDATED` customer signals for a non-business attachment URL normalization change.
2. S30 MOFA had a current, still-actionable ICT tender canonicalized from HTML metadata but without deadline/scope completeness or a customer signal because the business facts lived in a text-native official PDF.

Neither fix changes SignalForge topology. Production remains Bangkok-only. No Beijing check is part of this closure.

## S25 MONPIFER signal-noise fix

Production showed 20 S25 `UPDATED` signals on 2026-09-08. Inspection of repeated signals for the same canonical showed identical business data; the only difference was the issuer serving an equivalent attachment URL in two forms:

- `https://www.monpifer.gov.mm/index.php/sites/default/files/...`
- `https://www.monpifer.gov.mm/sites/default/files/...`

The S25 parser now canonicalizes official tender-PDF URLs to the non-`/index.php` issuer form before canonical payload hashing. This is source-local normalization; global signal semantics were not weakened.

Regression proves:

- equivalent attachment URL form change -> `changed=0 / signals_created=0`;
- real business deadline change -> exactly one `UPDATED` signal.

PR #96 passed CI and squash-merged as `a7e979743cfe092c7af20ed6a460fb5c74c4b75a`.

Full suite after the change: `215 passed`.

Production verification on exact release `a7e979743cfe092c7af20ed6a460fb5c74c4b75a`:

- S25 live page parsed 10 tenders;
- `changed=0`;
- `signals_created=0`;
- total signals stayed `34`;
- historical S25 noisy signals were not deleted;
- DB quick check remained `ok`;
- S25 health remained GREEN.

## S30 MOFA business-completeness gap

Production canonical `mofa:59800`, published 2026-09-04, was correctly classified `OPPORTUNITY`, but its HTML-only record had:

- `deadline=None`;
- attachment `Tender-Announcement.pdf` stored as metadata only;
- S30 customer signals `0`.

The current official PDF is text-native and contains material ICT procurement facts absent from the HTML metadata:

- Data Server (1 set);
- Dell PowerEdge R750-XS;
- 2 x Intel Xeon Silver 4310;
- 4 x 32 GB RDIMM;
- 6 x 2 TB SAS;
- 10 GbE adapters;
- iDRAC 9;
- configuration/installation, O&M and training;
- Windows Server 2025 Standard 24 Core with Microsoft License;
- Microsoft SQL Server 2022 Standard;
- tender form sale window 2026-09-07 through 2026-09-18;
- submission deadline **2026-09-18 16:30**.

## S30 implementation boundary

S30 remains Bangkok Direct HTTP. No Browser or Provider capability was added.

The existing Direct-HTTP supplementary-PDF path was extended to support an explicitly optional contract:

- same-origin PDF only;
- max one PDF per detail;
- `required_primary_attachments=0`;
- successful text-native PDF parse enriches canonical scope/deadline;
- PDF acquisition failure falls back to original HTML metadata without making the source fail;
- S39/S40 required-PDF behavior remains fail-closed and unchanged.

Parser performs no network I/O; acquisition/evidence remains engine-owned.

Regression verifies:

- current MOFA PDF -> `deadline=2026-09-18`, `deadline_time=16:30`;
- scope contains `PowerEdge R750-XS`, `Windows Server 2025 Standard`, and `Microsoft SQL Server 2022 Standard`;
- optional PDF fetch failure -> source SUCCESS, detail SUCCESS, HTML metadata canonical preserved;
- required-PDF sources are unaffected.

Targeted tests: `23 passed`.

Full suite: `217 passed`.

PR #97 passed CI and squash-merged as `38ba382bd132769dd89e784331f06c3ae7e3392a`.

## Production rollout and natural unattended proof

Exact release `38ba382bd132769dd89e784331f06c3ae7e3392a` was deployed to Bangkok with timer frozen. Pre-deploy state for `mofa:59800` was:

- deadline: null;
- S30 signals: 0;
- total signals: 34.

The first immediate post-deploy manual refresh correctly did not force a detail health probe because the two-hour probe interval had not yet elapsed. No DB due-time mutation, clock spoofing or production interval reduction was used.

After timer restoration, the normal production scheduler reached the probe window naturally.

At `2026-09-08T17:50:03.314007Z`:

- S30 discovery processing: SUCCESS;
- S30 detail/PDF processing: SUCCESS;
- `items_found=1`;
- `canonical_items=1`;
- `signals_created=1`;
- parser `mofa-wordpress-html-optional-text-pdf-v2`;
- evidence target kind `PDF`;
- PDF artifact SHA `aad5b2c3e51ffc289edb5018254f364896b01d14bee8fa3be7e362e756e130c7`.

That SHA is now the canonical `mofa:59800` evidence SHA.

The generated customer signal is exactly one `UPDATED` signal containing deadline `2026-09-18 16:30` and enriched ICT scope. Total SignalForge signals changed `34 -> 35`.

Subsequent natural S30 PDF refreshes at later probe windows reused the same official PDF SHA and produced no additional signal. Four S30 PDF acquisitions are present; all four artifact hashes match the canonical evidence SHA, while the signal count for `mofa:59800` remains exactly one.

## Final production snapshot

- active application: `38ba382bd132769dd89e784331f06c3ae7e3392a`;
- Bangkok timer: enabled / active;
- SQLite quick check: `ok`;
- SignalForge overall: `PASS / GREEN`;
- non-GREEN sources: none;
- canonical items: `193`;
- signals: `35`;
- recovery backlog: `0`;
- S30 health: GREEN, parse 10/10;
- `mofa:59800`: `deadline=2026-09-18`, `deadline_time=16:30`, `attachment_policy=OPTIONAL_TEXT_PDF_ENRICHMENT`.

## Product decision

Do not optimize for S41/S42 source count by default. Current source coverage is already producing fresh opportunities such as S20 YESC/EPGE and S26 DMS tenders. The higher-value next slice is continued business-value auditing of existing sources for:

- false-positive update noise;
- missing deadlines/scope hidden in already-accessible official attachments;
- actionable baseline items that lack sufficient business completeness;
- duplicate signals for semantically unchanged facts.

New source onboarding should resume only when a genuine issuer coverage gap has higher expected value than improving precision/completeness of the existing production graph.
