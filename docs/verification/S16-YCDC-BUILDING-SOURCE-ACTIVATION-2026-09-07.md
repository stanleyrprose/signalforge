# S16 YCDC Engineering Department (Building) — Stable Archive Activation

Date (Asia/Yangon): 2026-09-07
Phase: PRODUCTION
Result: PRODUCTION / GREEN — LIVE VERIFIED 2026-09-07

## Why S16 is being reopened

S16 YCDC was previously deferred because the generic YCDC tender flow exposed randomized Laravel ciphertext locators that changed on every request. That made discovery identity inseparable from a transport-only locator.

Fresh re-audit found an issuer-original stable department archive that bypasses the randomized locator layer entirely:

```text
https://www.ycdc.gov.mm/frontend_engineering_building_detail/1
```

This is a stable numeric department/archive URL. It is Direct-HTTP reachable from Bangkok and contains the business text itself.

## Candidate audit before activation

### Office of the Auditor General of the Union

OAG was freshly audited because it has active 2026 open-tender posts and stable Drupal node IDs. Bangkok strict HTTPS is GREEN, but current tender detail body content is seven JPG scan pages with no business-critical HTML text. Activating OAG would therefore require Burmese image/OCR to recover scope/deadline and is deferred under the existing capability gate.

### YCDC stable Building archive

Bangkok fetched the YCDC Building archive three times with strict HTTPS:

```text
HTTP 200
bytes = 60673 on each fetch
final URL unchanged
```

The page contains eight `တင်ဒါခေါ်ယူခြင်း` blocks plus one `လေလံခေါ်ယူခြင်း` block. Each tender block is inline HTML and can contain scope, tender-form dates, final submission date/time, location and contact details.

The stable archive therefore closes the old S16 discovery-identity vs transport-locator blocker without Browser, OCR, PDF, schema or cross-host transport.

## Business classification boundary

YCDC mixes several transaction directions on the same page. S16 must not treat the word `တင်ဒါ` alone as procurement/business implementation.

S16 selects only PPP/building implementation opportunities whose scope contains strong implementation semantics such as:

```text
ပူးပေါင်းဆောင်ရွက်
အကောင်အထည်ဖော်
ဆောက်လုပ်
PPP / public private partnership / construction
```

S16 excludes scope-level semantics for:

```text
လေလံ                auction
အငှားချထား           lease/concession-only
ရောင်းချ              sale/disposal
ဖြိုဖျက်ရောင်းချ       demolition + sale
```

Important parser rule: exclusion tokens are evaluated only inside the scope paragraph, not the whole tender block. This avoids falsely excluding a valid PPP tender merely because later HTML contains `တင်ဒါပုံစံရောင်းချမည့်ရက်` (tender-form sale date).

## Current live archive result

The current archive yields five selected PPP/building implementation records:

```text
2026-02-27  affordable-housing PPP / Dagon South + Dagon Seikkan
2024-11-27  Hlaing Tharyar West PPP housing implementation
2024-10-24  Hlaing Tharyar West PPP housing implementation
2024-09-18  Hlaing Tharyar West PPP housing implementation
2024-06-21  Hlaing Tharyar West PPP housing implementation
```

The current 2026-08-10 healthcare/sports/restaurant operation notice is excluded because its scope is a lease/concession (`အငှားချထား`). The auction block and demolition-sale blocks are also excluded.

All selected current records are historical as of 2026-09-07, so first baseline must remain customer-signal-free.

## Identity contract

The stable archive exposes no native per-event row ID. S16 therefore uses a source-local event fingerprint:

```text
ycdc-building:<deadline>:<sha256(explicit_deadline|normalized_scope_summary)[:16]>
```

Identity material is intentionally limited to explicit deadline + normalized scope summary. Tender-form sale dates, contacts and other mutable detail fields are not identity.

Within one archive fetch:

```text
same canonical identity + different normalized full block
=> fail closed / parser error / re-audit
```

This protects against same-event ambiguity without making mutable transport/detail fields part of identity.

## Epistemic boundary

S16 emits:

```text
publication_date = null
publication_date_evidence = UNKNOWN_NOT_EXPOSED_IN_STABLE_ARCHIVE_HTML

deadline = explicit final submission date from HTML
deadline_evidence = EXPLICIT_HTML_FINAL_SUBMISSION_DATE
```

No date is inferred from collection time or URL structure.

## Implementation

New adapter:

```text
signalforge/ycdc_building.py
adapter = ycdc_building_tender
discovery parser = ycdc-building-stable-archive-v1
normalizer = ycdc-building-normalize-v1
canonicalizer = ycdc-building-event-fingerprint-v1
```

Registry activation:

```text
source_id = S16
role = ACTIVE_SELECTIVE
engine = direct_http
listing_complete_business_records = true
primary = DIRECT_HTTP / HTML
supplementary = []
attachment mode = HTML_ONLY_NO_ATTACHMENT_REQUIRED
first_baseline_customer_signal = false
parse_sample_source = BUSINESS_PROCESSING
```

The previous deferred S16 entry is removed because its exact blocker is resolved by the stable archive path. The generic randomized `frontend_tender/<ciphertext>` transport remains unused.

## Local verification

```text
python -m pytest tests/test_ycdc_building.py tests/test_contract.py -q
10 passed
```

Coverage includes:

- PPP/building include semantics;
- lease/sale/auction exclusion;
- Myanmar-digit deadline parsing;
- scope-only exclusion to avoid tender-form-sale false negatives;
- event fingerprint identity;
- same-identity/different-block fail-closed behavior;
- structural-drift fail-closed behavior;
- one-fetch listing-complete engine path;
- first-baseline signal suppression;
- zero detail/attachment acquisition.

## Bangkok isolated live-engine verification

The working tree was copied to a temporary Bangkok runtime with isolated SQLite/evidence directories; production state was not touched.

First live fetch:

```text
status             = SUCCESS
baseline           = true
items              = 5
tenders            = 5
details_attempted  = 0
changed            = 5
signals_created    = 0
```

Second live fetch:

```text
status             = SUCCESS
baseline           = false
items              = 5
tenders            = 5
details_attempted  = 0
changed            = 0
signals_created    = 0
```

Current canonical keys:

```text
ycdc-building:2026-02-27:350a78fc50e80f42
ycdc-building:2024-11-27:41b637c17955c917
ycdc-building:2024-10-24:79210266b25cf7b7
ycdc-building:2024-09-18:2b48abda67d39612
ycdc-building:2024-06-21:47833d4849dd7cb1
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

No detail page, attachment, Browser or OCR acquisition occurred.

## Frozen boundaries

S16 activation does not authorize or require:

- randomized YCDC ciphertext locators;
- PDF/image fetching or parsing;
- OCR;
- Browser/Crawlee;
- TLS bypass;
- SignalForge→Mac remote invocation;
- a new Worker runtime capability;
- schema migration;
- synthetic publication dates;
- lease/sale/auction canonicalization.

Mac production flags remain frozen:

```text
production_enabled=false
remote_invocation=false
browser_production_approved=false
```

## Production gate

S16 may be promoted only after:

1. feature commit/push;
2. PR + GitHub Actions `verify` PASS;
3. merge to `main`;
4. exact merged application SHA deploy to Bangkok only with timer paused;
5. reviewed `signalforge-refresh S16` baseline succeeds with zero customer signals;
6. production evidence confirms exactly one archive HTML acquisition and zero detail/attachment acquisition;
7. one S16 refresh maps to exactly one Worker Run;
8. Bangkok/Beijing Worker doctors PASS and Beijing remains SignalForge-free / denies S16 refresh;
9. Mac provider flags remain frozen;
10. timer resumes and final all-source health is GREEN.


## Production closure — 2026-09-07

S16 passed the production gate on exact merged application release:

```text
794e0190d1d878d92e9a0580a28b93b6c82dada0
```

Previous application-code rollback target:

```text
a4d55bf4ad8cf1977b5e874fa9b652d880c2b2a7
```

### Frozen pre-deploy state

Immediately before rollout, Bangkok was healthy and idle:

```text
application_release   = a4d55bf4ad8cf1977b5e874fa9b652d880c2b2a7
automated_sources     = 17 / 17 GREEN
canonical_items       = 148
signals               = 11
scheduler_runs        = 1414
acquisition_requests  = 1746
acquisition_attempts  = 1746
evidence_envelopes    = 1741
processing_records    = 1743
failed_runs           = 5
recovery_backlog      = 0
timer                 = enabled / active
run-due               = inactive
active refresh units  = 0
```

The timer was disabled and no active `run-due` or refresh unit remained. Deploying `794e019...` changed none of those counters. Immediately after deployment, S16 correctly appeared as `baseline=0 / SOURCE_FRESHNESS_LAG / RED`; all seventeen pre-existing automated sources remained GREEN.

### Reviewed first production baseline

The reviewed control path executed:

```text
signalforge-refresh S16
```

and returned:

```text
source_id             = S16
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
worker_run_id         = signalforge-20260907T091305Z-669065f6
```

Production canonical rows are:

```text
ycdc-building:2026-02-27:350a78fc50e80f42
ycdc-building:2024-11-27:41b637c17955c917
ycdc-building:2024-10-24:79210266b25cf7b7
ycdc-building:2024-09-18:2b48abda67d39612
ycdc-building:2024-06-21:47833d4849dd7cb1
```

All `publication_date` values remain `null`. The newest selected PPP/building implementation record was already closed on `2026-02-27`, so first-baseline suppression correctly produced zero customer signals. The newer `2026-08-10` YCDC notice remains excluded because it is a lease/concession opportunity rather than a PPP/building implementation event.

### Production evidence boundary

The baseline added exactly one acquisition lifecycle. The sole S16 EvidenceEnvelope is:

```text
requested_url = https://www.ycdc.gov.mm/frontend_engineering_building_detail/1
http_status   = 200
media_type    = text/html
artifact_bytes= 60673
```

Production persistence immediately after baseline:

```text
S16 canonical_items = 5
S16 signals         = 0
requests/attempts/evidence/processing increment = 1/1/1/1
detail acquisitions = 0
attachment acquisitions = 0
SignalForge SQLite quick_check = ok
```

No randomized ciphertext tender locator, detail page, PDF/JPG, Browser or OCR acquisition was used.

### Worker and host-boundary verification

Worker DB contains exactly one matching operational Run:

```text
run_id       = signalforge-20260907T091305Z-669065f6
application  = signalforge
process_user = signalforge
status       = SUCCESS
exit_code    = 0
```

Additional verification:

```text
Bangkok workerctl doctor        = PASS
Beijing workerctl doctor        = PASS
Beijing /srv/signalforge        = ABSENT
Beijing signalforge-refresh S16 = 126 / DENY: SignalForge is Bangkok-only
Worker DB quick_check           = ok
Mac production_enabled          = false
Mac remote_invocation           = false
browser_production_approved     = false
Mac invocation_mode             = manual_or_future_contract
canonical_node                  = bangkok
```

No Browser, OCR, PDF/image pipeline, TLS bypass, schema migration, cross-host transport or new Worker capability was introduced.

### Failed-run audit

The cumulative `failed_runs` count was already `5` before S16 deployment. The fifth entry is a recovered S25 MONPIFER transport failure, not an S16 regression:

```text
2026-09-07T08:30Z  S25  HTTP 522
2026-09-07T08:40Z  S25  SUCCESS / changed=0 / signals=0
```

The prior four historical/recovered failures remain S10, S28 and two S29 events. Recovery backlog is zero and S25 health is GREEN.

### Timer resume and final state

`signalforge-resume` restored the scheduler. No source was due at that exact instant, so no artificial scheduler run was created. Final state after restoration:

```text
application_release   = 794e0190d1d878d92e9a0580a28b93b6c82dada0
automated_sources     = 18 / 18 GREEN
signalforge_health    = GREEN
canonical_items       = 153
signals               = 11
scheduler_runs        = 1415
acquisition_requests  = 1747
acquisition_attempts  = 1747
evidence_envelopes    = 1742
processing_records    = 1744
failed_runs           = 5 (all historical/recovered)
recovery_backlog      = 0
timer                 = enabled / active
run-due               = inactive
```

**Gate result: S16 is PRODUCTION / GREEN.**
