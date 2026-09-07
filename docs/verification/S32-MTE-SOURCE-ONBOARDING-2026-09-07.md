# S32 Myanma Timber Enterprise Procurement Invitations — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRODUCTION
Result: PRODUCTION / GREEN — LIVE VERIFIED 2026-09-07

## Source decision

S32 selects the issuer-original Myanma Timber Enterprise announcement archive:

```text
https://mte.gov.mm/index.php/en/annoucements
```

This is intentionally an `ACTIVE_SELECTIVE`, listing-complete Direct-HTTP HTML source. MTE publishes several different commercial event types under “Open Tender”, including timber sales. Therefore `Open Tender` alone is not sufficient procurement evidence.

P0 selects only records whose issuer HTML itself proves buyer-side procurement, such as:

```text
ဝန်ဆောင်မှုရယူရန် ... တင်ဒါခေါ်ယူခြင်း
ဝယ်ယူလို ... ပေးသွင်းရန်ဖိတ်ခေါ်
purchase / procure / supply invitation + tender
```

It rejects sale/auction semantics such as:

```text
ရောင်းချ
လေလံ
sale / sales / auction
```

Ambiguous title-only “open tender” records are left unclassified rather than promoted to procurement.

## Candidate comparison

Before selecting S32, S27 Ministry of Border Affairs was freshly re-audited because the official site now exposes a current 2026-08-24 open tender with closing date 2026-09-08. Bangkok strict TLS still failed 3/3 with `CERTIFICATE_VERIFY_FAILED / unable to get local issuer certificate` on both listing and detail URLs. S27 therefore remains deferred; no certificate bypass, Browser escalation or remote Mac invocation was introduced.

MTE was selected because:

- Bangkok Direct HTTP succeeds;
- the issuer archive exposes stable Joomla article IDs;
- current article `1600` exposes a visible tender number and buyer-side service-procurement scope entirely in HTML;
- the source can be useful at event level without fetching the image supplements;
- no new schema/runtime/browser/OCR/PDF capability is required.

## Bangkok transport audit

Representative strict Direct-HTTP checks passed against:

```text
https://mte.gov.mm/
https://mte.gov.mm/index.php/en/annoucements
https://mte.gov.mm/index.php/en/annoucements/1600-26626
https://mte.gov.mm/index.php/mm/tenders/other-departments-tenders
```

Observed archive response during audit:

```text
HTTP 200
~46 KB
sub-second fetch
text/html
```

No TLS bypass, proxy fallback or Browser is required.

## Current issuer HTML facts

Current procurement record `1600` exposes directly in archive HTML:

```text
issuer/committee:
Myanma Timber Enterprise, Sagaing Region (West) tender committee

tender number:
(၁/၂၆-၂၇)

scope:
procure transportation service for teak/hardwood logs by hired vessel
```

The detail article contains three images with supplementary tender detail. Those images are deliberately not fetched or parsed in S32 P0.

A historical article `1415` independently proves the same buyer-procurement selection shape for High Speed Diesel / Premium Diesel supply.

## Epistemic boundary

The archive does not expose a trustworthy publication date or closing deadline for the selected current record in HTML.

Therefore S32 emits:

```text
publication_date = null
publication_date_evidence = UNKNOWN_NOT_EXPOSED_IN_ARCHIVE_HTML

deadline = null
deadline_evidence = UNKNOWN_IN_IMAGE_SUPPLEMENT_NOT_PARSED
```

Collection time is never substituted for issuer publication time. The article slug is not decoded into a date because its semantics are not contractually established.

This means S32 is an event-detection source, not a deadline-complete source. A future OCR slice would be a separate capability/value decision.

## Identity contract

Issuer-native Joomla numeric article ID is the canonical identity:

```text
mte:<article_id>
```

Current examples:

```text
mte:1600
mte:1415
```

The visible issuer tender number is stored when available. If absent, `MTE-ARTICLE-<id>` is only a reference fallback; it does not replace canonical identity.

## Implementation

New adapter:

```text
signalforge/mte.py
adapter = mte_tender
discovery parser = mte-announcement-archive-v1
normalizer = mte-procurement-normalize-v1
canonicalizer = mte-joomla-article-id-v1
```

Registry:

```text
source_id = S32
role = ACTIVE_SELECTIVE
engine = direct_http
listing_complete_business_records = true
primary = DIRECT_HTTP / HTML
supplementary = []
attachment/image mode = EMBEDDED_IMAGE_UNPARSED_NON_BLOCKING
first_baseline_customer_signal = false
parse_sample_source = BUSINESS_PROCESSING
```

## Local verification

```text
python -m pytest tests/test_mte.py tests/test_contract.py -q
8 passed
```

Coverage includes:

- procurement-vs-sale selection;
- strong procurement evidence requirement;
- stable Joomla identity;
- visible tender-number extraction;
- null publication/deadline epistemic boundary;
- structural-drift fail-closed behavior;
- valid-empty archive behavior;
- one-fetch listing-complete engine path;
- first-baseline signal suppression;
- zero detail/image acquisition.

## Bangkok isolated live-engine verification

The working-tree implementation was copied to a temporary Bangkok runtime and run against an isolated SQLite DB/evidence directory. Production state was not touched.

First real fetch:

```text
status             = SUCCESS
baseline           = true
items              = 2
tenders            = 2
details_attempted  = 0
changed            = 2
signals_created    = 0
worker_run_id      = s32-live-isolated-1
```

Second real fetch:

```text
status             = SUCCESS
baseline           = false
items              = 2
tenders            = 2
details_attempted  = 0
changed            = 0
signals_created    = 0
worker_run_id      = s32-live-isolated-2
```

Selected canonical records:

```text
mte:1600  reference=၁/၂၆-၂၇
  transportation service for teak/hardwood logs
  publication_date=null
  deadline=null

mte:1415  reference=MTE-ARTICLE-1415
  High Speed Diesel / Premium Diesel procurement
  publication_date=null
  deadline=null
```

Lifecycle totals after two runs:

```text
requests   = 2
attempts   = 2
evidence   = 2
processing = 2
signals    = 0
SQLite quick_check = ok
```

No detail page or image was acquired by the engine.

## Frozen boundaries

S32 does not authorize or require:

- image fetching or OCR;
- PDF extraction;
- Browser/Crawlee;
- TLS bypass;
- SignalForge→Mac remote invocation;
- new Worker runtime capability;
- schema migration;
- guessing dates from URL slugs or local collection time;
- treating all MTE “Open Tender” sales as procurement opportunities.

Mac production flags remain frozen:

```text
production_enabled=false
remote_invocation=false
browser_production_approved=false
```

## Production gate

S32 may be promoted only after:

1. feature commit/push;
2. PR + GitHub Actions `verify` PASS;
3. merge to `main`;
4. exact merged application SHA deploy to Bangkok only with timer paused;
5. reviewed `signalforge-refresh S32` first baseline succeeds with zero customer signals;
6. production evidence confirms exactly one archive HTML acquisition and zero detail/image acquisition;
7. one S32 refresh maps to exactly one Worker Run;
8. Bangkok/Beijing Worker doctors PASS and Beijing remains SignalForge-free / denies S32 refresh;
9. Mac provider flags remain frozen;
10. timer resumes and post-resume reconciliation remains clean.

No additional capability is authorized by S32.


## Production closure — 2026-09-07

S32 passed the production gate on exact merged application release:

```text
2edaf3259d168344544f5a5cd09ab1d2c37fe563
```

Previous application-code rollback target:

```text
f751c8f13ae86740a227ba2cd00518d68cde2edc
```

### Frozen pre-deploy state

Before rollout the Bangkok timer was disabled and no `run-due` or source-refresh unit was active. The frozen production state was:

```text
application_release   = f751c8f13ae86740a227ba2cd00518d68cde2edc
automated_sources     = 15 / 15 GREEN
canonical_items       = 141
signals               = 11
scheduler_runs        = 1300
acquisition_requests  = 1608
acquisition_attempts  = 1608
evidence_envelopes    = 1604
processing_records    = 1606
failed_runs           = 4
recovery_backlog      = 0
```

Deploying `2edaf325...` changed none of those counters. Immediately after deployment S32 correctly appeared as `baseline=0 / SOURCE_FRESHNESS_LAG / RED`; all fifteen pre-existing automated sources remained GREEN.

### Reviewed first production baseline

The reviewed control path executed:

```text
signalforge-refresh S32
```

and returned:

```text
source_id             = S32
trigger_kind          = MANUAL
baseline              = 1
status                = SUCCESS
items_parsed          = 2
tenders_parsed        = 2
details_attempted     = 0
details_succeeded     = 0
changed               = 2
signals_created       = 0
backlog_remaining     = 0
worker_run_id         = signalforge-20260907T060955Z-b9a81d4d
```

Production canonical records are:

```text
mte:1600
reference_no = ၁/၂၆-၂၇
publication_date = null
deadline = null
scope = transportation service for teak/hardwood logs by hired vessel

mte:1415
reference_no = MTE-ARTICLE-1415
publication_date = null
deadline = null
scope = High Speed Diesel / Premium Diesel procurement
```

The baseline remained signal-free by policy.

### Production evidence boundary

The baseline added exactly one acquisition lifecycle. The sole S32 EvidenceEnvelope is:

```text
requested_url = https://mte.gov.mm/index.php/en/annoucements
http_status   = 200
media_type    = text/html
artifact_bytes= 46158
```

Production persistence immediately after baseline:

```text
S32 canonical_items = 2
S32 signals         = 0
requests/attempts/evidence/processing increment = 1/1/1/1
detail acquisitions = 0
image acquisitions  = 0
SignalForge SQLite quick_check = ok
```

The supplementary images visible in MTE detail content were not fetched. `publication_date` and `deadline` remain unknown rather than inferred.

### Worker and host-boundary verification

Worker DB contains exactly one matching operational Run:

```text
run_id       = signalforge-20260907T060955Z-b9a81d4d
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
Beijing signalforge-refresh S32 = 126 / DENY: SignalForge is Bangkok-only
Worker DB quick_check           = ok
Mac production_enabled          = false
Mac remote_invocation           = false
browser_production_approved     = false
Mac invocation_mode             = manual_or_future_contract
canonical_node                  = bangkok
```

No Browser, OCR, image-processing, PDF, TLS-bypass or cross-host production capability was introduced.

### Historical failed-run audit

The cumulative `failed_runs` count was already `4` before S32 deployment. The two newer entries are both S29 DWIR transport failures, not S32 regressions:

```text
2026-09-07T05:10Z  S29  HTTP 522
2026-09-07T05:20Z  S29  read timeout
```

S29 subsequently succeeded at:

```text
2026-09-07T05:30Z  SUCCESS / changed=0 / signals=0
2026-09-07T06:05Z  SUCCESS / changed=0 / signals=0
```

The earlier two cumulative failures remain the already-recovered S10 and S28 read timeouts. Current recovery backlog is zero and S29 health is GREEN.

### Timer resume and final state

`signalforge-resume` restored the scheduler. No source was due at that exact instant, so no new scheduler run was created merely by resume. Final state after restoration:

```text
application_release   = 2edaf3259d168344544f5a5cd09ab1d2c37fe563
automated_sources     = 16 / 16 GREEN
signalforge_health    = GREEN
canonical_items       = 143
signals               = 11
scheduler_runs        = 1301
acquisition_requests  = 1609
acquisition_attempts  = 1609
evidence_envelopes    = 1605
processing_records    = 1607
failed_runs           = 4 (all historical/recovered)
recovery_backlog      = 0
timer                 = enabled / active
run-due               = inactive
```

**Gate result: S32 is PRODUCTION / GREEN.**
