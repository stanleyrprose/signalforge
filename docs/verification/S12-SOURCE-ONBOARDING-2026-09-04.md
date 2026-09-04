# S12 IRD Business Tax Announcements — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / LIVE TRANSPORT PASS

## Decision

S12 is an `ACTIVE_SELECTIVE` issuer-original tax/regulatory source from Myanmar Internal Revenue Department (IRD).

P0 canonicalizes only business-relevant tax announcements as `REGULATORY_NOTICE`. IRD tenders, anti-corruption campaigns, training/meeting/news-style institutional content and generic announcements without a tax signal are acknowledged but do not create canonical business items.

## Official source

```text
https://www.ird.gov.mm/announcement-lists
```

Bangkok production-path Direct HTTP transport passed 3/3 repeated reads. No Browser capability is required.

## S04 comparison / deferral

Myanmar National Trade Portal `/en/legals` is healthy and structured, but it is a multi-agency official aggregator. Current records include Commerce and Customs material already covered by issuer-original S05A/S07 and prospective S12 records. S04 canonical onboarding is therefore deferred until an explicit cross-source issuer-resolution/equivalence/dedup contract exists.

This avoids introducing duplicate legal/regulatory signals simply because an aggregator republishes issuer material.

## Current IRD source shape

Current first page exposes 16 announcement records with deterministic detail URLs and visible publication dates.

Fresh audit of records 104 through 89 showed a stable split between:

```text
selected business tax notices:
- taxpayer/company registration notices
- taxpayer registration/TIN reminders
- income/commercial tax filing reminders
- vehicle-transfer tax / Digital Payment workflow
- IMEI tax payment workflow
- fertilizer import advance-income-tax exemption
- diesel import customs/special-goods/commercial/advance-income-tax exemption

excluded from S12 P0:
- IRD procurement/tender notices
- anti-corruption / 1111 campaign
- institutional/training/meeting/news content
- generic announcement without a deterministic tax business signal
```

## Canonical contract

```text
item_kind = REGULATORY_NOTICE
canonical identity = IRD issuer record id + publication date
canonical example = ird-notice:94:2026-04-02
reference_no = IRD-ANNOUNCEMENT-<record_id>
reference_no_kind = issuer_record_id
```

Selection categories currently include:

```text
TAX_REGISTRATION
TAX_FILING
TAX_PAYMENT
TAX_EXEMPTION
TAX_NOTICE
```

Title semantics take precedence for exclusion/category assignment. Detail body is supplementary classification evidence. This prevents a valid taxpayer-registration notice from being rejected merely because its body mentions tender participation as one use of a TIN.

## Attachment boundary

Official PDFs are stored only as attachment metadata. Myanmar characters and spaces in official IRD paths are percent-encoded safely.

```text
attachment_policy = METADATA_ONLY_NON_BLOCKING
fetch_in_primary_pipeline = false
```

No PDF parser, OCR, Browser runtime or Mac remote invocation is introduced.

## Current-live isolated engine

Using the real S12 Registry/adapter/engine path with current public IRD HTML and a temporary SQLite database:

```text
status=SUCCESS
baseline=true
discovered=16
candidates=14
fetched=14
detail_errors=0
items=9
tenders=0
details_attempted=9
details_succeeded=9
changed=9
signals_created=0
backlog_remaining=0
```

Canonical distribution:

```text
REGULATORY_NOTICE=9
TAX_REGISTRATION=3
TAX_PAYMENT=2
TAX_FILING=2
TAX_EXEMPTION=2
```

Persistence/acquisition:

```text
requests/attempts/evidence/processing=15/15/15/15
PDF requested_url count=0
recovery backlog=0
SQLite quick_check=ok
```

The 15 network acquisitions are one listing page plus fourteen in-lookback detail pages. Five non-selected 2026 details are still acknowledged as successful processing rather than parser failures.

## Language/equivalence boundary

IRD may publish closely related Myanmar/English records separately (for example same-day filing notices). S12 P0 preserves issuer record identity and does not guess that two legal notices are equivalent translations. Cross-record semantic equivalence/dedup is a future explicit contract, not an adapter heuristic.

## Verification

```text
targeted suite: 27/27 PASS
full CI-equivalent unit suite: 52/52 PASS
compileall: PASS
Registry JSON: PASS
shell syntax: PASS
git diff --check: PASS
current-live isolated engine: PASS
Bangkok Direct HTTP: PASS
```

Existing S05A/S07/S08A/S13/S20/S21/S22 regression behavior remains unchanged.

## Production gate

Production is not complete until:

1. PR CI passes and exact merged SHA is deployed to Bangkok only;
2. timer is paused and current seven-source state is frozen;
3. deployment itself leaves business counts unchanged;
4. reviewed `signalforge-refresh S12` succeeds;
5. baseline creates zero customer signals;
6. current baseline creates the audited IRD `REGULATORY_NOTICE` set with `tenders_parsed=0`;
7. PDF requested URL count remains zero;
8. excluded tender/propaganda/institutional records do not remain pending;
9. S12 parse health is GREEN;
10. existing seven sources remain or recover to GREEN after timer restoration;
11. one manual source refresh correlates to one Worker SignalForge Run;
12. Beijing remains SignalForge-free and rejects S12 refresh;
13. both Worker doctors pass;
14. timer returns to enabled/active/waiting;
15. PRD v1.5.1 Browser-plane invariants remain intact.
