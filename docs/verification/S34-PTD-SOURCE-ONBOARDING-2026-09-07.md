# S34 PTD Telecom Tenders — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRODUCTION
Result: PRODUCTION / GREEN — LIVE VERIFIED 2026-09-07

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


## Production closure — 2026-09-07

S34 passed the production gate on exact merged application release:

```text
0f8237916b39daa1c2f85d8309e93ff3ced56238
```

Previous application-code rollback target:

```text
794e0190d1d878d92e9a0580a28b93b6c82dada0
```

### Frozen pre-deploy state

```text
automated_sources     = 18 / 18 GREEN
canonical_items       = 153
signals               = 11
scheduler_runs        = 1456
acquisition_requests  = 1792
acquisition_attempts  = 1792
evidence_envelopes    = 1787
processing_records    = 1789
failed_runs           = 5
recovery_backlog      = 0
timer                 = enabled / active
run-due               = inactive
active refresh units  = 0
```

The timer was disabled before deployment. Deploying `0f823791...` changed none of those counters; all eighteen pre-existing sources stayed GREEN and only new S34 appeared as expected with `baseline=0 / SOURCE_FRESHNESS_LAG / RED`.

### Reviewed production baseline

```text
source_id             = S34
trigger_kind          = MANUAL
baseline              = 1
status                = SUCCESS
items_parsed          = 6
tenders_parsed        = 6
details_attempted     = 6
details_succeeded     = 6
changed               = 6
signals_created       = 0
backlog_remaining     = 0
worker_run_id         = signalforge-20260907T102115Z-c639cb75
```

Production canonical keys:

```text
ptd:2026-07-31:a683b1bfdd91b4c7
ptd:2026-07-30:2cc7b9918c60651f
ptd:2026-07-30:5fa9f5303e79d570
ptd:2026-06-23:d3580760420bf8bc
ptd:2026-05-26:739549b4ad40ffc5
ptd:2026-05-19:da5f996299cbbc95
```

All deadlines remain `null`; first-baseline signal suppression correctly produced zero customer signals.

### Production evidence boundary

The baseline added exactly seven acquisition lifecycles: one tender-category HTML plus six selected detail HTML pages. Production evidence was:

```text
category HTML = 85,873 bytes
detail HTML   = 72,366 / 72,456 / 61,496 / 66,211 / 73,298 / 72,176 bytes
HTTP status   = 200 for all seven
media type    = text/html for all seven
PDF evidence  = 0
```

The linked official tender PDFs remain metadata only. SignalForge DB `quick_check=ok`.

### Worker / fleet / provider verification

Worker DB contains exactly one matching operational run:

```text
run_id       = signalforge-20260907T102115Z-c639cb75
application  = signalforge
process_user = signalforge
status       = SUCCESS
exit_code    = 0
```

Additional boundaries:

```text
Bangkok workerctl doctor        = PASS
Beijing workerctl doctor        = PASS
Beijing /srv/signalforge        = ABSENT
Beijing signalforge-refresh S34 = 126 / DENY: SignalForge is Bangkok-only
Worker DB quick_check           = ok
Mac production_enabled          = false
Mac remote_invocation           = false
browser_production_approved     = false
Mac invocation_mode             = manual_or_future_contract
canonical_node                  = bangkok
```

No PDF parser, OCR, Browser, TLS bypass, schema migration, cross-host provider transport or new Worker capability was introduced.

### Failed-run history

Cumulative `failed_runs` remained `5` before and after S34 rollout. They are the already-recovered S10, S28, two S29 and S25 transport failures; S34 added no failure and recovery backlog remains zero.

### Timer resume and final state

`signalforge-resume` restored the scheduler. No source was due at that exact instant, so no additional scheduler run was created. Final observed state:

```text
application_release   = 0f8237916b39daa1c2f85d8309e93ff3ced56238
automated_sources     = 19 / 19 GREEN
signalforge_health    = GREEN
canonical_items       = 159
signals               = 11
scheduler_runs        = 1457
acquisition_requests  = 1799
acquisition_attempts  = 1799
evidence_envelopes    = 1794
processing_records    = 1796
failed_runs           = 5 (historical / recovered)
recovery_backlog      = 0
timer                 = enabled / active
run-due               = inactive
```

**Gate result: S34 is PRODUCTION / GREEN.**
