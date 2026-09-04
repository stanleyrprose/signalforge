# S10 DICA Company and Investment Announcements — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRODUCTION
Result: PASS / PRODUCTION COMPLETE

## Decision

S10 is an `ACTIVE_SELECTIVE` issuer-hosted business/regulatory event source from the Directorate of Investment and Company Administration (DICA).

P0 canonicalizes event-level facts from DICA HTML as `REGULATORY_NOTICE` while preserving official PDF links as metadata only. It does not claim that PDF contents have been extracted into production business facts.

## Official source

```text
https://www.dica.gov.mm/category/announcements-and-information/
```

Bangkok production-path Direct HTTP transport passed 3/3 repeated category reads. Current category HTML is WordPress server-rendered HTML; no Browser capability is required.

Current page 1 exposes 12 announcement records with deterministic post IDs and publication datetimes. Current categories selected by P0 are:

```text
COMPANY_STRIKE_OFF_BATCH=9
COMPANY_COMPLIANCE_NOTICE=1
INVESTMENT_TAX_INCENTIVE=1
INVESTMENT_CAPITAL_CURRENCY=1
```

Unknown/unrecognized DICA announcements fail closed and are acknowledged as processing success with no canonical object.

## Canonical contract

```text
item_kind = REGULATORY_NOTICE
canonical identity = DICA WordPress post id
canonical example = dica-notice:52512
```

If the DICA title exposes an issuer notification/newsletter reference, it is preserved as `issuer_notice_reference`; otherwise the fallback is `DICA-POST-<post_id>` with `reference_no_kind=issuer_record_id`.

DICA is recorded as the publisher/source authority. P0 leaves `legal_issuer` unknown rather than inferring a legal issuer from PDF filename text.

## PDF value gate — triggered, runtime gate deferred

Fresh audit proved that DICA HTML often contains only event metadata while the business-critical detail is in the official PDF:

- strike-off notices contain the affected company names/registration numbers in PDF;
- the Sky Villa company compliance notice contains affected companies/responsible persons in PDF;
- investment incentive and CNY capital notices contain the substantive policy text in PDF.

Representative current PDFs were directly retrievable and text-native during audit, including:

```text
Notification 83/2026 strike-off list
Sky Villa company compliance notice
Notification 1/2026 tax exemption/relief criteria
Investment Newsletter 1/2026 CNY capital policy
```

This is the first source that materially satisfies the frozen PDF supplementary value criterion.

However Bangkok production SignalForge currently has a zero-third-party-dependency packaging model:

```text
pyproject dependencies=[]
BKK pypdf=absent
BKK pdftotext=absent
```

Introducing PDF extraction now would require a separate runtime packaging/dependency change. S10 P0 therefore freezes:

```text
pdf_value_gate = TRIGGERED
runtime_packaging_gate = DEFERRED_ZERO_DEPENDENCY
attachment_policy = METADATA_ONLY_NON_BLOCKING
fetch_in_primary_pipeline = false
```

No PDF/OCR parser is silently added in this source onboarding.

## Current-live isolated engine

Using the real S10 Registry/adapter/engine path with current public DICA HTML and a temporary SQLite database:

```text
status=SUCCESS
baseline=true
discovered=12
candidates=12
fetched=12
detail_errors=0
items=12
tenders=0
details_attempted=4
details_succeeded=4
changed=12
signals_created=0
backlog_remaining=0
```

`details_attempted=4/4` is the bounded parse-health sample over the four representative bootstrap seeds. All 12 current records were fetched and canonicalized.

Canonical distribution:

```text
REGULATORY_NOTICE=12
COMPANY_STRIKE_OFF_BATCH=9
COMPANY_COMPLIANCE_NOTICE=1
INVESTMENT_TAX_INCENTIVE=1
INVESTMENT_CAPITAL_CURRENCY=1
```

Persistence/acquisition:

```text
requests/attempts/evidence/processing=13/13/13/13
PDF requested_url count=0
recovery backlog=0
SQLite quick_check=ok
```

## Bangkok performance check

All 12 current DICA detail pages were fetched through the Bangkok production SignalForge fetcher:

```text
12/12 SUCCESS
total elapsed ~=34.1s
per detail ~=1.3s to 4.4s
```

Current reviewed refresh unit has:

```text
TimeoutStartSec=300s
```

Therefore the 12-detail baseline/delta limit is operationally bounded with substantial timeout headroom.

## Verification

```text
targeted suite: 31/31 PASS
full CI-equivalent unit suite: 56/56 PASS
compileall: PASS
Registry JSON: PASS
shell syntax: PASS
git diff --check: PASS
current-live isolated engine: PASS
Bangkok category Direct HTTP 3/3: PASS
Bangkok current 12-detail transport: 12/12 PASS
```

Existing S05A/S07/S08A/S12/S13/S20/S21/S22 regression behavior remains unchanged.

## Production rollout — PASS

PR #30 passed CI and was squash-merged. Exact application SHA deployed to Bangkok:

```text
3f31b937cc8dbe2941e85b1f810f2bd8a9b811fb
```

Immediate rollback target:

```text
d5222d00e81692ae4f4b8ee3d0a3d7ad70618237
```

Pre-deploy frozen state:

```text
canonical_items=92
signals=11
scheduler_runs=228
acquisition_requests=315
acquisition_attempts=315
evidence_envelopes=315
processing_records=315
failed_runs=0
recovery_backlog=0
Worker SignalForge Runs=462
existing eight sources=GREEN
timer=disabled/inactive
```

Deployment reported `timer_preexisting=0`. Active manifest became `S05A,S07,S08A,S10,S12,S13,S20,S21,S22`. Deployment itself left all business counts unchanged, S10 remained `0/0`, and SQLite `quick_check=ok`.

### First production baseline

Reviewed `signalforge-refresh S10` returned:

```text
trigger_kind=MANUAL
baseline=1
status=SUCCESS
items_parsed=12
tenders_parsed=0
details_attempted=4
details_succeeded=4
changed=12
signals_created=0
worker_run_id=signalforge-20260904T091008Z-10e990be
```

State transition:

```text
canonical_items: 92 -> 104
signals:         11 -> 11
scheduler_runs:  228 -> 229
acquisition/evidence/processing: 315 -> 328
```

S10 persistence:

```text
REGULATORY_NOTICE=12
COMPANY_STRIKE_OFF_BATCH=9
COMPANY_COMPLIANCE_NOTICE=1
INVESTMENT_TAX_INCENTIVE=1
INVESTMENT_CAPITAL_CURRENCY=1
signals=0
requests/attempts/evidence/processing=13/13/13/13
pending discovery items=0
PDF requested_url count=0
SQLite quick_check=ok
```

Canonical identity is post-ID only:

```text
dica-notice:51344
...
dica-notice:52512
```

No publication date is embedded in the canonical key.

The manual production refresh completed successfully within the reviewed `TimeoutStartSec=300s` envelope. End-to-end remote invocation observed during rollout was approximately 99 seconds, still with substantial timeout headroom.

Worker cardinality/correlation:

```text
Worker SignalForge Runs: 462 -> 463
latest Worker Run=signalforge-20260904T091008Z-10e990be / SUCCESS
```

Worker Run ID exactly matched the S10 scheduler row.

### Topology / timer restoration

```text
Bangkok Worker doctor=PASS
Beijing Worker doctor=PASS
Beijing /srv/signalforge=ABSENT
Beijing signalforge-refresh S10=126 / DENY: SignalForge is Bangkok-only
```

After `signalforge-resume`, one persistent wrapper (`463 -> 464`) processed only due S12. It returned `SUCCESS`, `changed=0`, `signals_created=0`; S10 was not repeated.

Final state:

```text
release=3f31b937cc8dbe2941e85b1f810f2bd8a9b811fb
active sources=S05A,S07,S08A,S10,S12,S13,S20,S21,S22
canonical_items=104
signals=11
scheduler_runs=230
acquisition_requests=329
acquisition_attempts=329
evidence_envelopes=329
processing_records=329
failed_runs=0
recovery_backlog=0
Worker SignalForge Runs=464
timer=enabled/active/waiting
all nine sources=GREEN
browser_production_approved=false
```

The PDF value gate remains explicitly **TRIGGERED**, but production extraction/runtime packaging remains **DEFERRED_ZERO_DEPENDENCY**. No `pypdf`, `pdftotext`, OCR, Browser runtime, Mac remote invocation, schema migration, Worker change or Control Plane change was introduced by S10 P0.

## Production gate — closed

All of the following passed:

1. PR CI passes and exact merged SHA is deployed to Bangkok only;
2. timer is paused and current eight-source state is frozen;
3. deployment itself leaves business counts unchanged;
4. reviewed `signalforge-refresh S10` succeeds;
5. first baseline creates zero customer signals;
6. current baseline creates 12 audited event-level `REGULATORY_NOTICE` items with `tenders_parsed=0`;
7. current category distribution matches the audited business categories or any live delta is explicitly explained;
8. PDF requested URL count remains zero;
9. no unrecognized announcement remains pending merely because the selective classifier returned no item;
10. S10 parse health is GREEN;
11. one manual source refresh correlates to one Worker SignalForge Run;
12. Beijing remains SignalForge-free and rejects S10 refresh;
13. both Worker doctors pass;
14. timer returns to enabled/active/waiting and all sources are GREEN;
15. `browser_production_approved=false` and PRD v1.5.1 Browser-plane invariants remain intact;
16. no PDF/OCR runtime packaging change is smuggled into S10 P0.
