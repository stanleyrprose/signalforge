# S35 DAST Tenders — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / ISOLATED LIVE PASS — PRODUCTION GATE PENDING

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
