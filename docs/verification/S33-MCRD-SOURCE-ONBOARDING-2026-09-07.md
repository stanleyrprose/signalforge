# S33 Ministry of Cooperatives and Rural Development Tenders — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRODUCTION
Result: PRODUCTION / GREEN — LIVE VERIFIED 2026-09-07

## Source decision

S33 selects the issuer-original Ministry of Cooperatives and Rural Development tender board:

```text
https://www.mcrd.gov.mm/index.php?page=dGluZGEmbW8%3D
```

The board is a structured Direct-HTTP HTML surface. Each tender row exposes:

- title;
- closing date;
- primary tender-information document link;
- department;
- an additional tender-form link that may be only a directory placeholder.

S33 is listing-complete and does not fetch the linked document in P0.

## Candidate audit before S33

### S23 Ministry of Construction

The Ministry of Construction was freshly reconsidered first because its official board currently exposes high-value, actionable 2026 tenders, including a record with closing date `2026-09-16`.

Bangkok strict TLS failed on both `www.construction.gov.mm` and `construction.gov.mm` with:

```text
curl: (60) SSL certificate problem: certificate has expired
```

S23 therefore remains deferred. No `-k`, `verify=False`, Browser fallback or Mac remote invocation was introduced.

### MOL / SSB

The MOL tender surface remains technically strong but its current first page is dominated by evaluation/award-stage records rather than fresh invitations. It remains lower priority than a new issuer-original board whose identity blocker can now be resolved deterministically.

### MCRD identity blocker re-evaluation

MCRD was previously deferred because the board exposes no issuer-native row ID or row detail URL.

Fresh inspection shows that each row provides enough stable event material to define a bounded source-local identity:

```text
normalized_title
+ closing_date
+ department
```

The primary document is deliberately excluded from identity. It is instead used as a collision guard: if the same event identity is observed with a different primary document URL, parsing fails closed for re-audit rather than silently creating or mutating an event.

This resolves the earlier identity blocker without adding schema, Browser, OCR, PDF parsing or a remote provider.

## Bangkok transport audit

Strict HTTPS from Bangkok is GREEN:

```text
HTTP/1.1 200 OK
Server: Apache/2.4.41 (Ubuntu)
Content-Type: text/html; charset=UTF-8
```

No TLS bypass or alternate transport is required.

## Current board facts

The live board currently exposes five tender invitation rows:

```text
2026-05-15  Ministry Office open tender
2025-06-20  Ministry Office open tender
2025-05-23  Ministry Office open tender
2024-05-14  Ministry Office open tender
2023-05-19  Ministry Office open tender
```

The latest record is already closed, so the first baseline must remain customer-signal-free.

The current 2026 row exposes:

```text
title      = Ministry of Cooperatives and Rural Development, Union Minister Office, Open Tender Invitation
deadline   = 2026-05-15
department = Union Minister Office
primary document = Minister.pdf
```

Publication date is not exposed by the board and remains `null`.

## Identity contract

Canonical identity is:

```text
mcrd:<closing_date>:<sha256(normalized_title|closing_date|department)[:16]>
```

The primary document name/path is metadata, not identity.

Collision rule:

```text
same canonical identity + different primary document URL
=> fail closed / parser error / re-audit
```

This prevents an issuer document replacement from being silently interpreted as a new tender event.

## Epistemic boundary

S33 emits:

```text
publication_date = null
publication_date_evidence = UNKNOWN_NOT_EXPOSED_IN_TENDER_BOARD_HTML

deadline = explicit board closing date
deadline_evidence = EXPLICIT_TENDER_BOARD_CLOSING_DATE
```

The linked PDF/JPEG is metadata only and is not fetched in the production pipeline.

## Implementation

New adapter:

```text
signalforge/mcrd.py
adapter = mcrd_tender
discovery parser = mcrd-tender-board-v1
normalizer = mcrd-tender-normalize-v1
canonicalizer = mcrd-board-event-fingerprint-v1
```

Registry:

```text
source_id = S33
role = ACTIVE_SELECTIVE
engine = direct_http
listing_complete_business_records = true
primary = DIRECT_HTTP / HTML
supplementary = []
attachment mode = METADATA_ONLY_NON_BLOCKING
first_baseline_customer_signal = false
parse_sample_source = BUSINESS_PROCESSING
```

Award/result semantics are excluded if they appear in the board later.

## Local verification

```text
python -m pytest tests/test_mcrd.py tests/test_contract.py -q
9 passed
```

Coverage includes:

- invitation-vs-award filtering;
- explicit closing-date parsing;
- null publication-date boundary;
- source-local event fingerprint;
- primary-document collision fail-closed behavior;
- structural-drift fail-closed behavior;
- one-fetch listing-complete engine path;
- first-baseline signal suppression;
- zero detail/document acquisition.

## Bangkok isolated live-engine verification

The working-tree implementation was copied to a temporary Bangkok runtime and run twice against an isolated SQLite DB/evidence directory. Production state was not touched.

First real fetch:

```text
status             = SUCCESS
baseline           = true
items              = 5
tenders            = 5
details_attempted  = 0
changed            = 5
signals_created    = 0
```

Second real fetch:

```text
status             = SUCCESS
baseline           = false
items              = 5
tenders            = 5
details_attempted  = 0
changed            = 0
signals_created    = 0
```

Current live canonical identities under the final identity contract:

```text
mcrd:2026-05-15:8980d452a32f4599  Minister.pdf
mcrd:2025-06-20:bee5d62c81b1641c  အိတ်ဖွင့်တင်ဒါကြော်ငြာ-တည်.pdf
mcrd:2025-05-23:c97c5f1d56c267a1  အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း-15.pdf
mcrd:2024-05-14:04e465d2c06af2cd  MO's Tender.pdf
mcrd:2023-05-19:1ce78c99645badfa  Web capture_2-5-2023_155024_.jpeg
```

Lifecycle totals after two isolated runs:

```text
requests   = 2
attempts   = 2
evidence   = 2
processing = 2
signals    = 0
SQLite quick_check = ok
```

No linked PDF/JPEG or detail page was acquired by the engine.

## Frozen boundaries

S33 does not authorize or require:

- PDF/JPEG fetching or parsing;
- OCR;
- Browser/Crawlee;
- TLS bypass;
- SignalForge→Mac remote invocation;
- a new Worker runtime capability;
- schema migration;
- a synthetic publication date;
- award/result canonicalization.

Mac production flags remain frozen:

```text
production_enabled=false
remote_invocation=false
browser_production_approved=false
```

## Production gate

S33 may be promoted only after:

1. feature commit/push;
2. PR + GitHub Actions `verify` PASS;
3. merge to `main`;
4. exact merged application SHA deploy to Bangkok only with timer paused;
5. reviewed `signalforge-refresh S33` first baseline succeeds with zero customer signals;
6. production evidence confirms exactly one board HTML acquisition and zero linked-document acquisition;
7. one S33 refresh maps to exactly one Worker Run;
8. Bangkok/Beijing Worker doctors PASS and Beijing remains SignalForge-free / denies S33 refresh;
9. Mac provider flags remain frozen;
10. timer resumes and final all-source health is GREEN.

No additional capability is authorized by S33.


## Production closure — 2026-09-07

S33 passed the production gate on exact merged application release:

```text
a4d55bf4ad8cf1977b5e874fa9b652d880c2b2a7
```

Previous application-code rollback target:

```text
2edaf3259d168344544f5a5cd09ab1d2c37fe563
```

### Frozen pre-deploy state

Immediately before rollout, Bangkok was healthy and idle:

```text
application_release   = 2edaf3259d168344544f5a5cd09ab1d2c37fe563
automated_sources     = 16 / 16 GREEN
canonical_items       = 143
signals               = 11
scheduler_runs        = 1321
acquisition_requests  = 1634
acquisition_attempts  = 1634
evidence_envelopes    = 1630
processing_records    = 1632
failed_runs           = 4
recovery_backlog      = 0
timer                 = enabled / active
run-due               = inactive
active refresh units  = 0
```

The timer was then disabled and no active run/refresh unit remained. Deploying `a4d55bf...` changed none of those business/acquisition counters. S33 appeared exactly as expected with `baseline=0 / SOURCE_FRESHNESS_LAG / RED`, while every pre-existing source remained GREEN.

### Reviewed first production baseline

The reviewed control path executed:

```text
signalforge-refresh S33
```

and returned:

```text
source_id             = S33
trigger_kind          = MANUAL
baseline              = 1
status                = SUCCESS
items_parsed          = 5
tenders_parsed        = 5
details_attempted     = 0
details_succeeded     = 0
changed               = 5
signals_created       = 0
backlog_remaining     = 0
worker_run_id         = signalforge-20260907T064353Z-74f21b24
```

The five production canonical rows are:

```text
mcrd:2026-05-15:8980d452a32f4599  deadline=2026-05-15
mcrd:2025-06-20:bee5d62c81b1641c  deadline=2025-06-20
mcrd:2025-05-23:c97c5f1d56c267a1  deadline=2025-05-23
mcrd:2024-05-14:04e465d2c06af2cd  deadline=2024-05-14
mcrd:2023-05-19:1ce78c99645badfa  deadline=2023-05-19
```

All `publication_date` values remain `null`. The newest board event was already closed at baseline time, and first-baseline suppression correctly produced zero customer signals.

### Production evidence boundary

The baseline added exactly one acquisition lifecycle. The sole S33 EvidenceEnvelope is:

```text
requested_url = https://www.mcrd.gov.mm/index.php?page=dGluZGEmbW8%3D
http_status   = 200
media_type    = text/html
artifact_bytes= 52527
```

Production persistence after baseline:

```text
S33 canonical_items = 5
S33 signals         = 0
requests/attempts/evidence/processing increment = 1/1/1/1
linked PDF/JPEG acquisitions = 0
SignalForge SQLite quick_check = ok
```

The primary tender-information links remain metadata only. No linked document or synthetic detail request was introduced.

### Worker and host-boundary verification

Worker DB contains exactly one row for the baseline Worker Run:

```text
run_id       = signalforge-20260907T064353Z-74f21b24
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
Beijing signalforge-refresh S33 = 126 / DENY: SignalForge is Bangkok-only
Worker DB quick_check           = ok
Mac production_enabled          = false
Mac remote_invocation           = false
browser_production_approved     = false
Mac invocation_mode             = manual_or_future_contract
canonical_node                  = bangkok
```

S33 therefore introduced no PDF/JPEG acquisition, OCR, Browser, TLS bypass, remote-provider transport, schema migration or new Worker runtime capability.

### Failed-run history

Cumulative `failed_runs` remained `4` before and after S33 rollout. They are the already-reviewed historical/recovered failures:

```text
S10  DICA  read timeout
S28  DOF   read timeout
S29  DWIR  HTTP 522
S29  DWIR  read timeout
```

No S33 failure was added and recovery backlog remains zero.

### Timer resume and final state

`signalforge-resume` restored the scheduler. No source was due at that exact instant, so resume created no artificial scheduler run. The timer returned to `enabled / active / waiting`, with `run-due` inactive.

Final observed state:

```text
application_release   = a4d55bf4ad8cf1977b5e874fa9b652d880c2b2a7
automated_sources     = 17 / 17 GREEN
signalforge_health    = GREEN
canonical_items       = 148
signals               = 11
scheduler_runs        = 1322
acquisition_requests  = 1635
acquisition_attempts  = 1635
evidence_envelopes    = 1631
processing_records    = 1633
failed_runs           = 4 (historical / recovered)
recovery_backlog      = 0
timer                 = enabled / active / waiting
run-due               = inactive
```

**Gate result: S33 is PRODUCTION / GREEN.**
