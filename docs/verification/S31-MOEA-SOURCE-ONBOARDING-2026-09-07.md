# S31 MOEA Procurement Invitations — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRODUCTION
Result: PRODUCTION / GREEN — LIVE VERIFIED 2026-09-07

## Source decision

S31 selects the issuer-original Ministry of Ethnic Affairs (MOEA) tender archive:

```text
https://portal.moea.gov.mm/index.php?page=ORwuBwpT
```

The source is intentionally implemented as an `ACTIVE_SELECTIVE`, listing-complete, Direct-HTTP HTML source. The board mixes procurement invitations with tender award/result records and older non-procurement lease-style tenders, so the entire board cannot be treated as current procurement opportunities.

MOEA was selected after S30 because it adds issuer-original procurement coverage without adding Browser, OCR, PDF parsing, remote-provider transport, schema migration or a new Worker capability. MOL/SSB remains lower-value while its current surface is dominated by evaluation/award stages; MCRD remains blocked by weak issuer-stable row identity.

## Bangkok transport audit

Using Bangkok directly against the exact production URL:

```text
attempt 1: HTTP 200 / 90,396 bytes / ~0.407s
attempt 2: HTTP 200 / 90,396 bytes / ~0.280s
attempt 3: HTTP 200 / 90,396 bytes / ~0.412s
```

The whole-response SHA changes between requests even though the business cards are stable. Therefore transport-body hash is evidence provenance only; canonical change semantics are driven by normalized selected business fields.

No TLS bypass, proxy fallback, Browser escalation or alternate endpoint is required.

## Important HTML-comment discovery

MOEA renders each tender as a structured `div.tender-content` card with:

- tender title;
- visible publication date;
- location;
- official PDF View/Download link.

Crucially, the issuer CMS also leaves the full tender narrative inside an HTML comment (`<!-- <p>...</p> -->`). For the 2026-07-27 invitation this comment contains the construction scope, tender-form sale window, submission location and explicit final submission date.

This means the runtime can remain HTML-only. The PDF link is stored as metadata but is never fetched by the S31 primary pipeline.

## Selection semantics

P0 includes invitation/call language such as:

```text
တင်ဒါခေါ်ယူ...
အိတ်ဖွင့်တင်ဒါ...
open tender
invitation to tender
```

P0 excludes stage/result semantics such as:

```text
တင်ဒါအောင်...
အောင်မြင်...
awarded
result
```

It also excludes clearly non-procurement tenancy/auction semantics such as `ငှားရမ်း` / `လေလံ` / lease / auction.

Structural drift fails closed when the tender-card structure disappears. A structurally valid board with zero qualifying procurement invitations is a valid-empty success.

## Deadline epistemic boundary

A deadline is emitted only when the HTML-comment narrative explicitly contains the Burmese final-deadline marker `နောက်ဆုံး` followed by an unambiguous day-month-year date. Myanmar digits are normalized deterministically.

For the current 2026-07-27 event:

```text
publication_date = 2026-07-27
deadline         = 2026-08-07
```

A generic form-sale or application date range is not promoted to a deadline. If the explicit final-date marker is absent or ambiguous, `deadline=null`.

The current 2026-07-27 event is historical as of 2026-09-07 because its deadline has passed. The first production baseline therefore establishes monitoring continuity and must not create a customer signal.

## Identity contract

MOEA exposes no native post/article/row identifier in this archive surface. The P0 canonical identity therefore follows the already-proven archive-event fingerprint pattern:

```text
moea:<publication_date>:<sha256(normalized publication_date + normalized title)[:16]>
```

The attachment URL is deliberately not part of canonical identity because attachment filenames/paths are transport metadata and can be replaced independently of the business event.

Boundary and tradeoff:

- a later issuer title correction can produce a new identity because no stronger issuer-native ID exists;
- this is preferable to using a mutable attachment locator as identity;
- two rows with the same derived identity but different attachment URLs fail closed as an identity collision rather than silently merging.

This is a source-local use of an existing identity pattern, not a generic discovery-schema change.

## Implementation

New adapter:

```text
signalforge/moea.py
adapter = moea_tender
discovery parser = moea-tender-archive-card-v1
normalizer = moea-tender-normalize-v1
canonicalizer = moea-archive-event-fingerprint-v1
```

Registry policy:

```text
source_id = S31
role = ACTIVE_SELECTIVE
engine = direct_http
listing_complete_business_records = true
primary = DIRECT_HTTP / HTML
supplementary = []
attachment = METADATA_ONLY_NON_BLOCKING
first_baseline_customer_signal = false
parse_sample_source = BUSINESS_PROCESSING
```

## Local verification

```text
python -m pytest tests/test_moea.py tests/test_contract.py -q
10 passed
```

The tests cover:

- Burmese-digit explicit-deadline parsing;
- result/award exclusion;
- lease/auction exclusion;
- HTML-comment scope extraction;
- valid-empty vs structural drift;
- derived event identity;
- identity-collision fail-closed behavior;
- one-fetch listing-complete engine path;
- first-baseline signal suppression;
- zero PDF acquisition.

## Bangkok isolated live-engine verification

The uncommitted working-tree implementation was copied to an isolated `/tmp` runtime on Bangkok and run against an isolated SQLite DB/evidence root. It did not touch production SignalForge state.

First live run:

```text
status             = SUCCESS
baseline           = true
items              = 9
tenders            = 9
details_attempted  = 0
changed            = 9
signals_created    = 0
worker_run_id      = s31-live-isolated-1
```

Second real fetch two seconds later:

```text
status             = SUCCESS
baseline           = false
items              = 9
tenders            = 9
details_attempted  = 0
changed            = 0
signals_created    = 0
worker_run_id      = s31-live-isolated-2
```

This second fetch is important because the full page body changes between HTTP requests. Normalized business records remained identical, so no synthetic update was emitted.

Isolated lifecycle totals after the two live runs:

```text
requests    = 2
attempts    = 2
evidence    = 2
processing  = 2
pdf_evidence= 0
signals     = 0
SQLite quick_check = ok
```

Current selected archive includes nine procurement-invitation records. The newest three are:

```text
2026-07-27  MOEA / ethnic-rights department open tender  deadline=2026-08-07
2026-05-28  office equipment/furniture/construction open tender  deadline=null
2026-02-04  tender invitation  deadline=null
```

The 2026-06-26 tender-award equipment record is excluded, as is the historical restaurant tenancy/lease tender.

## Frozen boundaries

S31 does not authorize or require:

- PDF fetching or parsing;
- OCR;
- Browser/Crawlee on Bangkok or Beijing;
- Mac Browser Provider production enablement;
- TLS bypass;
- remote Provider invocation;
- new Worker runtime capability;
- database/schema migration;
- aggregator issuer-resolution/dedup work.

Mac provider invariants remain:

```text
production_enabled=false
remote_invocation=false
browser_production_approved=false
```

## Production gate

S31 may be promoted only after:

1. feature branch commit + push;
2. PR and GitHub Actions `verify` PASS;
3. merge to `main`;
4. exact merged application SHA deployment to Bangkok only;
5. timer paused and no active run/refresh units during rollout;
6. reviewed first `signalforge-refresh S31` baseline succeeds with zero customer signals;
7. production evidence confirms exactly one HTML acquisition and zero PDF acquisition for the baseline;
8. one S31 refresh maps to exactly one Worker application Run;
9. Bangkok/Beijing Worker doctors PASS and Beijing remains SignalForge-free / denies S31 refresh;
10. Mac provider flags remain frozen;
11. timer resumes enabled/active and post-resume reconciliation is clean.

No additional capability is authorized by S31.


## Production closure — 2026-09-07

S31 passed the production gate on exact merged application release:

```text
f751c8f13ae86740a227ba2cd00518d68cde2edc
```

The previous application-code rollback target is:

```text
61d6984bf0efd05dddcac0791bba00cf741f3052
```

### Frozen pre-deploy state

Immediately before deployment the Bangkok timer was paused and there were no active `run-due` or source-refresh units. The frozen application state was:

```text
application_release   = 61d6984bf0efd05dddcac0791bba00cf741f3052
automated_sources     = 14 / 14 GREEN
canonical_items       = 132
signals               = 11
scheduler_runs        = 1225
acquisition_requests  = 1522
acquisition_attempts  = 1522
evidence_envelopes    = 1520
processing_records    = 1522
failed_runs           = 2
recovery_backlog      = 0
```

Deploying `f751c8f...` itself changed none of those business/acquisition counters. Before the first baseline, S31 correctly appeared as `baseline=0 / SOURCE_FRESHNESS_LAG / RED`, while all fourteen pre-existing sources retained their prior state.

### Reviewed first production baseline

The baseline ran through the reviewed `signalforge-refresh S31` control-plane path and returned:

```text
source_id             = S31
trigger_kind          = MANUAL
baseline              = 1
status                = SUCCESS
items_parsed          = 9
tenders_parsed        = 9
details_attempted     = 0
details_succeeded     = 0
changed               = 9
signals_created       = 0
backlog_remaining     = 0
worker_run_id         = signalforge-20260907T040008Z-4db411d6
```

The baseline added nine historical procurement-invitation canonical records. The newest three are:

```text
moea:2026-07-27:1889354373bf58c2  deadline=2026-08-07
moea:2026-05-28:7f7cccfe3451afe2  deadline=null
moea:2026-02-04:d334df7a8c845d54  deadline=null
```

The current 2026-07-27 invitation was already closed at baseline time, so first-baseline suppression correctly produced no customer signal.

### Production evidence boundary

The S31 baseline persisted exactly one acquisition lifecycle:

```text
requested_url = https://portal.moea.gov.mm/index.php?page=ORwuBwpT
http_status   = 200
media_type    = text/html
artifact_bytes= 90396
```

Production persistence after baseline:

```text
S31 canonical_items = 9
S31 signals         = 0
requests/attempts/evidence/processing = 1/1/1/1
PDF evidence        = 0
SignalForge SQLite quick_check = ok
```

No attachment URL was fetched. The HTML-comment narrative remains the business-field source; official PDF URLs remain metadata only.

### Worker and host-boundary verification

Worker DB contains exactly one row for the baseline Worker Run:

```text
run_id       = signalforge-20260907T040008Z-4db411d6
application  = signalforge
process_user = signalforge
status       = SUCCESS
exit_code    = 0
```

Additional boundaries:

```text
Bangkok workerctl doctor       = PASS
Beijing workerctl doctor       = PASS
Beijing /srv/signalforge       = ABSENT
Beijing signalforge-refresh S31= 126 / DENY: SignalForge is Bangkok-only
Worker DB quick_check          = ok
Mac production_enabled         = false
Mac remote_invocation          = false
browser_production_approved    = false
Mac invocation_mode            = manual_or_future_contract
canonical_node                 = bangkok
```

S31 therefore introduced no Browser/OCR/PDF/runtime/cross-host dependency.

### Timer resume and reconciliation

Resuming the reviewed timer triggered one due-run Worker wrapper:

```text
signalforge-20260907T040055Z-db7c468a
```

It reconciled nine due sources:

```text
S05A S07 S08A S10 S12 S25 S26 S28 S29
```

All nine returned `SUCCESS / changed=0 / signals=0`.

Final observed production state:

```text
application_release   = f751c8f13ae86740a227ba2cd00518d68cde2edc
automated_sources     = 15 / 15 GREEN
signalforge_health    = GREEN
canonical_items       = 141
signals               = 11
scheduler_runs        = 1235
acquisition_requests  = 1532
acquisition_attempts  = 1532
evidence_envelopes    = 1530
processing_records    = 1532
failed_runs           = 2
recovery_backlog      = 0
timer                 = enabled / active
run-due               = inactive
```

The two cumulative failed runs remain the already-recovered S10 and S28 read timeouts; S31 added no failure or recovery backlog.

**Gate result: S31 is PRODUCTION / GREEN.**
