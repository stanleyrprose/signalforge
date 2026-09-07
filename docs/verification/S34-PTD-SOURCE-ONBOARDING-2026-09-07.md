# S34 PTD Telecom Tenders — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / ISOLATED LIVE PASS — PRODUCTION GATE PENDING

## Selection rationale

Fresh source audit prioritized issuer-original Myanmar sources with 2026 activity, Bangkok strict-TLS Direct HTTP, stable discovery, HTML business scope, and no new Browser/OCR/PDF capability.

Office of the Auditor General was re-audited and remains deferred: current tender detail is scan/JPG-only for business-critical scope/deadline and would require a separately approved Burmese image/OCR capability.

Posts and Telecommunications Department (PTD) is a materially stronger fit for SignalForge because its current official tender category contains telecom/ICT procurement with business scope directly in HTML. Current examples include:

- earthquake recovery equipment for radio-frequency monitoring systems;
- RF monitoring system spare parts including CPU modules, TCI RF synthesizer, POE, antenna controller and cable;
- equipment for a Bago radio-frequency monitoring station;
- measurement equipment for an RF monitoring vehicle;
- construction works in Nay Pyi Taw and Pathein;
- continuous operation and maintenance of the All DNS System including `.mm Root DNS System` and second-level DNS.

## Issuer-original endpoints

```text
landing  = https://www.ptd.gov.mm/CatAnnouncements.aspx
discovery= https://www.ptd.gov.mm/Announcement.aspx?id=jOhwNsVnnrHGITOdpDNvsw%3D%3D
detail   = https://www.ptd.gov.mm/AnnouncementDetail.aspx?id=<issuer opaque locator>
```

Bangkok strict-HTTPS audit returned the tender category three times as HTTP 200, `text/html`, 85,873 bytes, with the same final URL. Current detail pages are also Direct-HTTP reachable. No TLS bypass, proxy or Browser is required.

## Selective stage classifier

The PTD tender category mixes opportunity and outcome stages. S34 selects open-tender invitations and excludes tender-winner/award/result announcements. The word `တင်ဒါ` alone is not sufficient for canonicalization.

## Business and epistemic boundary

Each selected detail HTML exposes publication date and procurement scope. Linked official PDFs contain additional tender rules/deadline information but are metadata-only in P0.

```text
publication_date = explicit HTML Posted-on date
deadline         = null
deadline_evidence= UNKNOWN_IN_PDF_ATTACHMENT_NOT_PARSED
attachment       = official PTD PDF metadata only
```

S34 does not fetch or parse PDFs and does not infer a deadline from filenames, collection time or other indirect metadata.

PTD listing dates use abbreviated English month names (`Jul`, `Aug`) while detail pages use full month names (`July`, `August`); the parser explicitly supports both issuer forms.

## Identity contract

The issuer detail URL contains an opaque encoded locator. It is stable enough for transport/discovery, but S34 deliberately does not make that opaque transport locator canonical business identity.

Canonical identity is:

```text
ptd:<publication_date>:<sha256(publication_date|normalized_scope_summary)[:16]>
```

This separates two same-day generic `Open Tender` records by their actual business scope. A significant issuer correction to scope can create a new event identity because PTD exposes no stronger native tender ID in HTML; the opaque detail locator is retained only as metadata/hash for audit.

## Implementation

```text
source_id            = S34
adapter              = ptd_tender
role                 = ACTIVE_SELECTIVE
engine               = direct_http
poll_interval        = 900s
baseline_lookback    = 150 days
baseline_detail_limit= 20
delta_detail_limit   = 10
primary              = DIRECT_HTTP / HTML
supplementary        = []
attachment_policy    = METADATA_ONLY_NON_BLOCKING
first baseline signal= false
```

Parser versions:

```text
discovery    = ptd-tender-category-v1
detail       = ptd-tender-html-v1
normalizer   = ptd-tender-normalize-v1
canonicalizer= ptd-business-event-fingerprint-v1
```

## Local verification

```text
python -m pytest tests/test_ptd.py tests/test_contract.py -q
10 passed
```

Coverage includes:

- open-tender selection and award-stage exclusion;
- abbreviated/full English issuer date formats;
- same-day generic-title identity separation;
- high-value `.mm Root DNS` scope preservation;
- official PDF metadata without PDF acquisition;
- fail-closed category-shape drift;
- first-baseline signal suppression.

## Bangkok isolated live-engine verification

The working tree was copied to a temporary Bangkok runtime with isolated SQLite/evidence roots. Production was not touched.

First real run:

```text
status            = SUCCESS
baseline          = true
items             = 6
tenders           = 6
details_attempted = 6
details_succeeded = 6
changed           = 6
signals_created   = 0
```

Second real run:

```text
status            = SUCCESS
baseline          = false
items             = 0
tenders           = 0
details_attempted = 0
details_succeeded = 0
changed           = 0
signals_created   = 0
```

The second run fetched only the category because no discovery item was pending; it did not redundantly re-fetch six detail pages.

Current isolated canonical rows:

```text
ptd:2026-07-31:a683b1bfdd91b4c7  earthquake RF-monitoring recovery equipment
ptd:2026-07-30:2cc7b9918c60651f  RF-monitoring spare parts
ptd:2026-07-30:5fa9f5303e79d570  Bago RF-monitoring station equipment
ptd:2026-06-23:d3580760420bf8bc  RF-monitoring vehicle measurement equipment
ptd:2026-05-26:739549b4ad40ffc5  Nay Pyi Taw / Pathein construction works
ptd:2026-05-19:da5f996299cbbc95  All DNS / .mm Root DNS operations and maintenance
```

Two-run lifecycle totals:

```text
requests   = 8
attempts   = 8
evidence   = 8
processing = 8
canonical  = 6
signals    = 0
pdf_evidence = 0
SQLite quick_check = ok
```

## Frozen boundaries

S34 introduces no:

- PDF fetching/parsing;
- OCR or image processing;
- Browser/Crawlee;
- TLS bypass;
- SignalForge→Mac remote invocation;
- schema migration;
- new Worker runtime capability;
- synthetic deadline.

Mac production flags remain frozen:

```text
production_enabled=false
remote_invocation=false
browser_production_approved=false
```

## Production gate

S34 may be promoted only after:

1. feature commit and push;
2. PR + GitHub Actions `verify` PASS;
3. merge to main;
4. exact merged application SHA deploy to Bangkok with timer paused;
5. reviewed `signalforge-refresh S34` baseline succeeds with zero customer signals;
6. production evidence confirms one category HTML plus selected detail HTML and zero PDF evidence;
7. one S34 refresh maps to exactly one Worker Run;
8. Bangkok/Beijing Worker doctors PASS and Beijing remains SignalForge-free / rejects S34;
9. Mac provider production flags remain frozen;
10. timer resumes and all-source health is GREEN.
