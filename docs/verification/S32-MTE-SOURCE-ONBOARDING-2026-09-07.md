# S32 Myanma Timber Enterprise Procurement Invitations — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / ISOLATED LIVE PASS — PRODUCTION GATE PENDING

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
