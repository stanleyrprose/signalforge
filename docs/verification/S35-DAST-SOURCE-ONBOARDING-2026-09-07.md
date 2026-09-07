# S35 DAST Tenders — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRODUCTION
Result: PRODUCTION / GREEN — LIVE VERIFIED 2026-09-07

## Selection rationale

Fresh source audit prioritized issuer-original 2026 sources with business value, Bangkok strict-HTTPS Direct HTTP, stable identity and business-complete HTML.

- YESC was not split into a new source because current YESC tenders are already represented through the existing MOEP tender hub (S20); duplicating them would create unnecessary cross-source canonical overlap.
- LBVD was freshly tested from Bangkok and returned HTTP 403 three times on the issuer home/tender endpoints, so it remains outside production rather than weakening HTTP policy.
- Department of Advanced Science and Technology (DAST), Ministry of Science and Technology, passed transport and business-shape gates.

## Issuer endpoints and legacy-host normalization

Stable issuer archive:

```text
https://www.dast.gov.mm/category/tender/
```

Bangkok audit returned the archive three times as HTTP 200, `text/html`, 114,471 bytes. The current archive contains six 2026 tender posts.

The WordPress/Elementor HTML still emits historical links such as:

```text
https://dast.edu.mm/?p=2631
```

The legacy `.edu.mm` host times out from Bangkok. The same issuer WordPress post IDs are served directly by the current official `.gov.mm` site:

```text
https://www.dast.gov.mm/?p=2631
```

Therefore S35 treats the native WordPress post ID as issuer identity and deterministically canonicalizes the transport locator to `www.dast.gov.mm`. This is an issuer-local mirror rewrite, not a third-party fallback or TLS bypass. Official attachment paths are normalized by the same rule.

## Current business records

The current archive page exposes six 2026 tender posts:

```text
2631  2026-08-06  QA/QC construction services
2625  2026-07-07  construction works
2595  2026-05-08  Reference Book procurement
2578  2026-04-21  construction works (209 works)
2582  2026-04-21  QA/QC services
2571  2026-04-21  teaching/equipment/office/furniture procurement
```

The latest QA/QC tender HTML includes two lots for Polytechnic University (Myitkyina) and Polytechnic University (Kyaing Tong), including water wells/tanks/tower, football field, teacher residence, student dormitory, workshop repair and residence works.

## Deadline epistemic contract

DAST detail HTML contains explicit tender-form sale and submission periods. S35 derives a deadline only from explicit HTML submission language:

1. prefer `နောက်ဆုံးတင်သွင်းရမည့်ရက်` followed by an unambiguous D-M-Y date;
2. otherwise, in section 2, require submission semantics (`တင်သွင်း` plus `ပြန်လည်`/`နောက်ဆုံး`) and use the latest explicitly stated submission date;
3. otherwise deadline remains `null`.

Myanmar numerals are normalized to ASCII. Collection time and attachment filenames never become deadline evidence.

Current parsed deadlines:

```text
dast:2631 -> 2026-08-14
dast:2625 -> 2026-07-21
dast:2595 -> 2026-05-22
dast:2578 -> 2026-05-07
dast:2582 -> 2026-05-07
dast:2571 -> 2026-05-07
```

All are historical as of 2026-09-07, so the first production baseline must emit zero customer signals.

## Identity contract

```text
canonical_key = dast:<wordpress_post_id>
reference_no  = DAST-POST-<wordpress_post_id>
reference_no_kind = wordpress_post_id
```

The issuer-native WordPress post ID is stronger than a derived title/date fingerprint.

## Attachment boundary

Official linked PDFs are metadata-only. Example rewritten current issuer URL:

```text
https://www.dast.gov.mm/wp-content/uploads/2026/07/26-27-Construction-Second-Tender.pdf
```

A strict-HTTPS Bangkok probe returned HTTP 200 / `application/pdf`, but S35 does not fetch attachments in the primary pipeline because scope and deadline are already available in HTML.

## Implementation

```text
source_id             = S35
adapter               = dast_tender
role                  = ACTIVE_SELECTIVE
engine                = direct_http
discovery             = https://www.dast.gov.mm/category/tender/
poll_interval         = 1800s
baseline_lookback     = 180 days
baseline_detail_limit = 10
delta_detail_limit    = 6
canonical_key         = wordpress_post_id
primary               = DIRECT_HTTP / HTML
supplementary         = []
attachment_policy     = METADATA_ONLY_NON_BLOCKING
first baseline signal = false
```

Parser versions:

```text
discovery     = dast-tender-category-v1
detail        = dast-tender-html-v1
normalizer    = dast-tender-normalize-v1
canonicalizer = dast-wordpress-post-id-v1
```

## Local verification

```text
python -m pytest tests/test_dast.py tests/test_contract.py -q
11 passed
```

Coverage includes:

- issuer WordPress ID discovery;
- live Elementor `elementor-post-date` date shape;
- `.edu.mm` -> official `.gov.mm` deterministic locator rewrite;
- explicit HTML deadline parsing;
- range-based submission deadline parsing;
- scope-table preservation;
- legacy HTTP/HTTPS attachment metadata rewrite;
- post-ID mismatch fail-closed;
- archive-shape fail-closed;
- baseline signal suppression;
- unchanged second poll does not repeat detail fetches;
- no PDF acquisition.

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

Two-run totals:

```text
requests     = 8
attempts     = 8
evidence     = 8
processing   = 8
canonical    = 6
signals      = 0
pdf_evidence = 0
SQLite quick_check = ok
```

The second run fetched only the tender archive; no unchanged detail page was re-fetched.

## Frozen boundaries

S35 introduces no:

- PDF fetching/parsing;
- OCR/image processing;
- Browser/Crawlee;
- TLS bypass;
- SignalForge→Mac remote invocation;
- schema migration;
- new Worker capability;
- duplicate YESC/MOEP source.

## Production gate

Promote only after feature PR + CI PASS, exact merged-SHA Bangkok deployment with timer paused, reviewed zero-signal S35 baseline, production evidence/Worker correlation, Bangkok/Beijing doctor and Bangkok-only checks, frozen Mac-provider verification, timer resume and all-source GREEN closure.


## Production closure — 2026-09-07

Exact production application release:

```text
5ad60eabc2a86235db413c37c49e4bbe91378f95
```

Previous application-code rollback target:

```text
0f8237916b39daa1c2f85d8309e93ff3ced56238
```

### Pre-deploy freeze

A natural `signalforge-run-due` invocation was already activating when rollout began. It was allowed to finish normally before the timer was disabled. The reviewed frozen state was:

```text
automated_sources     = 19 / 19 GREEN
canonical_items       = 159
signals               = 11
scheduler_runs        = 1547
acquisition_requests  = 1901
acquisition_attempts  = 1901
evidence_envelopes    = 1896
processing_records    = 1898
failed_runs           = 5
recovery_backlog      = 0
timer                 = disabled / inactive
run-due               = inactive
active refresh units  = 0
```

Deploying `5ad60ea...` changed none of these counters. All nineteen pre-existing sources remained GREEN; only new S35 appeared with `baseline=0 / SOURCE_FRESHNESS_LAG / RED`, as expected.

### Reviewed production baseline

```text
source_id             = S35
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
worker_run_id         = signalforge-20260907T122630Z-ce3da99b
```

Production canonical rows and deadlines:

```text
dast:2631  publication=2026-08-06  deadline=2026-08-14
dast:2625  publication=2026-07-07  deadline=2026-07-21
dast:2595  publication=2026-05-08  deadline=2026-05-22
dast:2578  publication=2026-04-21  deadline=2026-05-07
dast:2582  publication=2026-04-21  deadline=2026-05-07
dast:2571  publication=2026-04-21  deadline=2026-05-07
```

All deadlines were already expired on 2026-09-07, so the zero-signal baseline is correct.

### Production evidence boundary

The baseline added exactly seven HTML acquisition lifecycles: one archive plus six detail pages.

```text
archive /category/tender/ = 114,471 bytes
post 2571                  = 96,836 bytes
post 2582                  = 95,331 bytes
post 2578                  = 96,203 bytes
post 2595                  = 96,258 bytes
post 2625                  = 95,988 bytes
post 2631                  = 99,264 bytes
HTTP status                = 200 for all seven
media type                 = text/html for all seven
PDF evidence               = 0
```

SignalForge DB `quick_check=ok`. Linked issuer PDFs remain metadata-only.

### Worker / fleet / provider verification

Worker DB contains exactly one matching operational run:

```text
run_id       = signalforge-20260907T122630Z-ce3da99b
application  = signalforge
process_user = signalforge
status       = SUCCESS
exit_code    = 0
```

Additional boundaries:

```text
Worker DB quick_check           = ok
Bangkok workerctl doctor        = PASS
Beijing workerctl doctor        = PASS
Beijing /srv/signalforge        = ABSENT
Beijing signalforge-refresh S35 = 126 / DENY: SignalForge is Bangkok-only
Mac production_enabled          = false
Mac remote_invocation           = false
browser_production_approved     = false
Mac invocation_mode             = manual_or_future_contract
canonical_node                  = bangkok
```

Cumulative `failed_runs` remained `5`; S35 introduced no failure and recovery backlog stayed zero.

### Timer resume and final state

`signalforge-resume` restored the timer. Nothing was due at that instant, so no additional scheduler run was created. Final observed state:

```text
application_release   = 5ad60eabc2a86235db413c37c49e4bbe91378f95
automated_sources     = 20 / 20 GREEN
signalforge_health    = GREEN
canonical_items       = 165
signals               = 11
scheduler_runs        = 1548
acquisition_requests  = 1908
acquisition_attempts  = 1908
evidence_envelopes    = 1903
processing_records    = 1905
failed_runs           = 5 (historical / recovered)
recovery_backlog      = 0
timer                 = enabled / active
run-due               = inactive
```

**Gate result: S35 is PRODUCTION / GREEN.**
