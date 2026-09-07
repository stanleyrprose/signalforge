# S33 Ministry of Cooperatives and Rural Development Tenders — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / ISOLATED LIVE PASS — PRODUCTION GATE PENDING

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
