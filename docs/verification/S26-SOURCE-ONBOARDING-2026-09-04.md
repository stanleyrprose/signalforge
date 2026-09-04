# S26 DOMS Medical Procurement Opportunities — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRODUCTION
Result: PASS / PRODUCTION COMPLETE

## Decision

Allocate `S26` to the Department of Medical Services (DOMS), Ministry of Health, as an issuer-original `ACTIVE_SELECTIVE` medical-procurement opportunity source.

Production discovery uses the official WordPress tender category HTML:

```text
https://www.doms.gov.mm/category/tender/
```

The source intentionally remains inside the frozen v1.5 HTML-first acquisition contract:

```text
category HTML
-> stable WordPress post id + title + issuer permalink
-> opportunity-stage classifier
-> selected detail HTML only
-> TENDER canonical
-> official PDF links as metadata only
```

No schema migration, JSON primary target, PDF extraction, OCR, Browser or remote Provider capability is introduced.

## Candidate selection context

Fresh source comparison before S26 included several issuer-original candidates.

- Ministry of Industry: commercially strong HTML procurement notices, but Bangkok production fetcher failed DNS 3/3; fail closed.
- Ministry of Energy: active and commercially strong, but current detail pages carry business content in embedded official PDFs; HTML exposes mainly title/date. Deferred until PDF runtime value justifies expansion.
- Department of Fisheries: Direct HTTP and listing-complete HTML are viable, but lower current business value/update intensity than DOMS.
- DOMS: Direct HTTP is stable, procurement value is high, stable WordPress post IDs are exposed, and selected opportunity detail HTML/attachment labels carry usable medical-procurement scope without reading PDFs.

DOMS therefore offers the best current business-value-to-complexity ratio while preserving the existing engine.

## Bangkok transport audit

Using the actual Bangkok SignalForge production fetcher:

```text
DOMS tender category HTML: 3/3 SUCCESS
bytes ~=205 KB
elapsed ~=0.67s to 3.71s during sampled run

representative DOMS detail HTML: 3/3 SUCCESS
bytes ~=197 KB
elapsed ~=0.07s to 0.12s during earlier sample
```

Direct HTTP is sufficient. Browser gate is not triggered.

## WordPress identity audit

The tender category emits stable issuer-owned article IDs directly in HTML:

```html
<article id="post-12634" class="... category-tender ...">
<article id="post-12491" class="... category-tender ...">
```

Representative detail HTML independently exposes the same WordPress identity, for example:

```text
postid-12491
wp-json post id=12491
article id=post-12491
```

Canonical identity is therefore:

```text
doms:<wordpress_post_id>
```

Publication date is read from the issuer permalink path (`/YYYY/MM/DD/.../`), not invented from local collection time.

## Why the WordPress REST API is not the production primary

Fresh audit proved that DOMS's public WordPress REST API is technically strong:

```text
/wp-json/wp/v2/posts/12491            -> 3/3 PASS
/wp-json/wp/v2/categories?per_page=100 -> category 38 = tender
/wp-json/wp/v2/posts?categories=38...  -> 3/3 PASS
```

However the frozen v1.5 acquisition contract explicitly requires P0 primary target kind `HTML`. Promoting JSON as a new primary target would be a contract expansion unrelated to the source's actual necessity.

Therefore S26 deliberately uses official HTML even though REST exists. This is an engineering-boundary decision, not a discovery gap.

## Current category shape / selection policy

The current first tender-category page exposes ten recent tender-workflow posts and spans roughly 2026-07-03 through 2026-09-03. The page mixes opportunity creation with later procurement stages.

Current examples include:

```text
12725  2026-09-03  7DMS opening/evaluation meeting                 -> DROP
12717  2026-08-31  6DMS tender winner list                         -> DROP
12686  2026-08-20  7DMS Envelope-B scrutiny meeting                -> DROP
12656  2026-08-12  5DMS supplementary winner list                  -> DROP
12634  2026-08-10  Tender No. 7DMS/2026-2027(L)                    -> SELECT
12589  2026-07-29  3DMS/5DMS winner list                           -> DROP
12510  2026-07-10  3DMS winner list                                -> DROP
12498  2026-07-10  4DMS lab reagents winner list                   -> DROP
12491  2026-07-09  Open Tender — CT/MRI Preventive Maintenance     -> SELECT
12518  2026-07-03  3DMS winner list                                -> DROP
```

S26 P0 classifier fails closed on procurement-stage markers such as winner/result, scrutiny/evaluation, meeting/opening and Envelope-stage notices. It selects only opportunity-origin records with explicit open-tender wording or a clean DMS tender reference not carrying those exclusion stages.

The current first page therefore yields exactly two selected opportunities.

## Discovery-window decision

P0 monitors only the official first category page.

The current ten-post window already spans about two months of issuer activity, while S26 polls every 30 minutes. There is no production evidence that ten newer workflow posts could displace an unseen new opportunity within one poll/recovery window.

Pagination is therefore not added speculatively. It becomes an evidence-triggered follow-up only if real history shows displacement risk.

## Current selected business records

### WordPress post 12634

```text
reference = 7DMS/2026-2027(L)
publication_date = 2026-08-10
canonical = doms:12634
```

The HTML detail carries official attachment labels that directly expose procurement scope, including:

```text
Oncology Medicine
Nuclear Medicine (Reagent)
Antibiotics
Uro Surgery
Radiation Therapy
Renal Medical
Ortho
Neuro Surgery
Maxillo Facial Surgery
Neuro Medicine
Haematology
GI
EYE
ENT
Dental
Cardiac Surgery
Cardiac Medicine (Paed)
Cardiac Medicine (Adult)
```

The parser deduplicates repeated `Download` anchors by official attachment URL and prefers the meaningful issuer label.

### WordPress post 12491

```text
reference = DOMS-POST-12491
reference_no_kind = wordpress_post_id
publication_date = 2026-07-09
canonical = doms:12491
```

HTML body itself states FY2026-2027 and the business scope: preventive maintenance for CT (Computed Tomography) and MRI (Magnetic Resonance Imaging) equipment used across DOMS hospitals.

A synthetic tender number is not invented when the issuer does not publish one in HTML.

## Deadline boundary

The current selected detail HTML does not provide a reliable tender closing deadline.

Therefore:

```text
deadline = unknown / null
deadline_evidence = UNKNOWN_NOT_IN_HTML_TEXT
```

S26 does not infer a deadline from images, PDF content, chronology or later procurement-stage notices.

## Attachment boundary

Selected 7DMS/5DMS records expose official attachments under:

```text
https://www.doms.gov.mm/wp-content/uploads/...
```

S26 preserves these as metadata only.

```text
attachment_policy = METADATA_ONLY_NON_BLOCKING
fetch_in_primary_pipeline = false
```

External/non-DOMS PDF links are rejected by the parser. PDFs are never requested by S26 P0.

## Same-post update semantics

A WordPress post may be edited while keeping the same permalink date and post ID. S26 therefore marks its parser output as tender-only discovery and uses the existing bounded parse-health probe to revisit the newest confirmed opportunity at the configured interval.

Fixture regression proves:

```text
same post_id=12634
same canonical=doms:12634
changed HTML scope/attachment label
-> one UPDATED signal after baseline
-> no duplicate NEW item
```

No engine change was required.

## Current-live isolated engine

Running the real S26 Registry/adapter/engine path against current public DOMS HTML with a temporary SQLite database produced:

```text
status=SUCCESS
baseline=true
discovered=2
candidates=2
fetched=2
items=2
tenders=2
details_attempted=2
details_succeeded=2
changed=2
signals_created=0
backlog_remaining=0
```

Persistence/acquisition:

```text
canonical TENDER=2
requests/attempts/evidence/processing=3/3/3/3
PDF requested_url count=0
SQLite quick_check=ok
```

Requested URLs were exactly:

```text
https://www.doms.gov.mm/category/tender/
https://www.doms.gov.mm/2026/08/10/<7DMS issuer slug>/
https://www.doms.gov.mm/2026/07/09/<open-tender issuer slug>/
```

## Verification

```text
targeted suite: 14/14 PASS
full CI-equivalent suite: 64/64 PASS
compileall: PASS
Registry JSON: PASS
shell syntax: PASS
current-live parser: PASS
current-live isolated engine: PASS
Bangkok Direct HTTP: PASS
```

## Production rollout closure

PR #34 passed GitHub `verify` and was squash-merged. The exact production application SHA is:

```text
ae894d092f97843280c92228d6b43eda3bf0336f
```

Immediate rollback is the previous ten-source application release:

```text
930c94641b0699072350dcea9344aa55e930e169
```

The timer was disabled before deployment and no refresh service was active. The frozen pre-deploy production state was:

```text
canonical_items=114
signals=11
scheduler_runs=358
acquisition_requests=480
acquisition_attempts=480
evidence_envelopes=479
processing_records=479
failed_runs=1
recovery_backlog=0
Worker SignalForge Runs=530
```

The one pre-existing failed run was S10 at `2026-09-04T14:05:13Z`: a Direct-HTTP `CONNECT_TIMEOUT` against the DICA category page. S10 automatically recovered at `14:15Z`; before the S26 rollout its `last_error` was null, `consecutive_failures=0`, and source health was GREEN. This historical fail-closed record was preserved rather than rewritten.

Exact-SHA deployment succeeded with:

```text
deployment=success
release=ae894d092f97843280c92228d6b43eda3bf0336f
previous=930c94641b0699072350dcea9344aa55e930e169
timer_preexisting=0
```

Deployment itself changed no business/acquisition counts. The new manifest exposed eleven active sources while S26 remained uninitialized with canonical/signals `0/0`, as expected before its first baseline.

The first reviewed S26 baseline ran through `signalforge-refresh@S26.service` and produced:

```text
worker_run_id=signalforge-20260904T144640Z-e5ee0dce
trigger_type=MANUAL
status=SUCCESS
baseline=true
discovered=2
candidates=2
fetched=2
items=2
tenders=2
details_attempted=2
details_succeeded=2
changed=2
signals_created=0
backlog_remaining=0
```

Persistence after the baseline:

```text
canonical_items: 114 -> 116
signals: 11 -> 11
scheduler_runs: 358 -> 359
S26 requests/attempts/evidence/processing=3/3/3/3
S26 PDF requested_url count=0
S26 canonical_items=2
S26 signals=0
SQLite quick_check=ok
```

The production canonical keys are exactly:

```text
doms:12634 -> 7DMS/2026-2027(L), publication_date=2026-08-10, deadline=null
doms:12491 -> DOMS-POST-12491, publication_date=2026-07-09, deadline=null
```

Worker cardinality/correlation passed:

```text
Worker SignalForge Runs: 530 -> 531
latest run_id=signalforge-20260904T144640Z-e5ee0dce / SUCCESS
S26 scheduler worker_run_id matches exactly
```

Topology/runtime gates also passed:

```text
Bangkok workerctl doctor = PASS
Beijing workerctl doctor = PASS
Beijing /srv/signalforge = ABSENT
Beijing signalforge-refresh S26 = 126 / DENY: SignalForge is Bangkok-only
browser_production_approved=false
```

After timer resume, Persistent reconciliation created one normal Worker wrapper:

```text
signalforge-20260904T145148Z-f0f1b9e9
```

That single wrapper processed eight due source jobs:

```text
S08A / S10 / S12 / S13 / S20 / S21 / S22 / S25
```

All eight were `SUCCESS`, `changed=0`, `signals=0`. S26 was not due and was not fetched again. This again preserves Gate Z: one Worker operational Run can contain N SignalForge business jobs.

Final steady state after reconciliation:

```text
11/11 sources GREEN
overall=PASS / GREEN
canonical_items=116
signals=11
scheduler_runs=367
acquisition_requests=495
acquisition_attempts=495
evidence_envelopes=494
processing_records=494
failed_runs=1   # pre-existing recovered S10 timeout
recovery_backlog=0
Worker SignalForge Runs=532
timer=enabled / active
run-due service=inactive
browser_production_approved=false
```

No JSON-primary contract, schema migration, PDF extraction, OCR, Browser, remote Provider, Worker-runtime or Control-Plane capability was added for S26. The production application remains pinned to `ae894d092f97843280c92228d6b43eda3bf0336f`; any later documentation-only closure SHA must not be redeployed merely to update facts.
