# S21 Myanma Railways — Source Onboarding Verification

Date (Asia/Yangon): 2026-09-04
Phase: `PRE_PRODUCTION`
Result: **READY_FOR_PR / NOT YET PRODUCTION-COMPLETE**

## Decision

S21 Myanma Railways is the first source expansion after SignalForge v1.5 production closure.

The source stays inside the frozen v1.5 architecture:

```text
Bangkok SignalForge
-> Source Acquisition Policy
-> AcquisitionRequest / AcquisitionAttempt
-> LOCAL_BANGKOK Direct HTTP
-> EvidenceEnvelope
-> Railways source adapter
-> ProcessingRecord
-> Canonical / Dedup / Signal
```

No Worker ABI, Control Plane verb, remote Provider, Browser/Browserless, Mac production dependency, Beijing acquisition, Redis/Celery, distributed queue or automatic cross-zone failover is introduced.

## Why S21 first

The pre-code engineering source audit classified Myanma Railways as a strong issuer-original engineering tender source and a `GREEN-CANDIDATE / PARSE-STRONG` Type-A structured HTML source. Unlike the conditional YCDC/MCDC/NPTDC paths, S21 does not currently require identity-segmentation, scanned-PDF, or mixed-board classifier gates.

## Current live transport re-audit

### Mac / Myanmar-side development path

Standard Python HTTPS with normal certificate verification against:

```text
https://www.railways.gov.mm/category/tender/
```

returned:

```text
HTTP 200
Content-Type: text/html
body ~= 75 KB
```

The live listing parser found 10 current tender detail pages. The newest parsed publication date was `2026-09-01`.

The newest detail page was fetched with standard TLS and parsed into four independent business tenders:

```text
၃၂၆/မမ/CE
12(T)30/MR (ML/ISN)
15(T)5/MR(E)
၃၂၇/မမ/CMO
```

The shared deadline `(၁၄.၉.၂၀၂၆)` was normalized to `2026-09-14`.

### Bangkok production egress

The Bangkok VPS performed three sequential standard-TLS reads of the category endpoint:

```text
(200, 0.456s)
(200, 0.366s)
(200, 0.271s)
```

The newest detail page also returned:

```text
HTTP 200
Content-Type: text/html
body=75535 bytes
```

and its raw response contained tender reference `၃၂၆/မမ/CE`.

Conclusion: Direct HTTP from the canonical Bangkok production zone is sufficient. No Browser capability gate is triggered.

## Source-shape finding

S21 is not equivalent to MPT's current one-detail-page/one-tender shape.

A single Myanma Railways detail page can contain multiple tender rows. Therefore the implementation does **not** reuse the MPT business parser directly and does not pretend one discovery URL maps to one canonical business item.

The source adapter contract is:

```text
Tender category HTML
-> N detail URLs
-> one detail HTML
-> N RailwayTender business items
-> one EvidenceEnvelope / ProcessingRecord for the fetched page
-> N canonical upserts
```

For multi-item pages, `discovery_items.canonical_key` remains `NULL`; canonical identities remain in `canonical_items` rather than storing a false one-to-one URL mapping.

## Canonical identity

Issuer-original evidence wins over mirrors.

S21 canonical identity uses:

```text
railways:<normalized tender reference>
```

Myanmar digits in the tender reference are normalized to ASCII digits while issuer-specific Burmese/Latin reference components are preserved. Examples:

```text
၃၂၆/မမ/CE      -> railways:326/မမ/CE
12(T)30/MR ... -> railways:12(T)30/MR(ML/ISN)
```

The `railways:` namespace prevents cross-source collisions with existing MPT canonical keys.

## Source policy

```text
source_id=S21
adapter=railways
role=ACTIVE_PRIMARY
network_zone=myanmar-international
engine=direct_http
egress_profile=mm-intl-datacenter
source_policy_version=1
poll_interval_seconds=900
baseline_lookback_days=120
baseline_detail_limit=10
delta_detail_limit=10
first_baseline_customer_signal=false
```

Failure policy preserves v1.5 fail-closed semantics:

```text
TLS_FAILURE -> FAIL
JS_RENDER_REQUIRED -> REVIEW_CAPABILITY
PARSER_DRIFT -> REAUDIT
```

## Implementation

Added:

- `signalforge/railways.py` — listing parser, multi-row detail parser, Myanmar digit/deadline normalization;
- `signalforge/source_adapters.py` — bounded source adapter registry for MPT and Railways;
- S21 active Source Registry policy;
- Railways listing/detail fixtures;
- Railways parser and engine regression tests.

Changed the engine only where required for source-shape reuse:

- adapter-selected discovery content type/parser;
- adapter-selected parser/normalizer/canonicalizer metadata;
- detail parser returns zero-to-N business items;
- one fetched detail page remains one acquisition/evidence/processing lifecycle;
- N canonical items remain SignalForge-internal business state.

MPT continues through the `mpt` adapter with its prior one-item behavior.

## Pre-production verification

Targeted source + regression suite:

```text
15/15 PASS
```

CI-equivalent SignalForge unit suite including the new Railways tests:

```text
25/25 PASS
```

Additional release checks:

```text
python3 -m compileall -q signalforge tests   PASS
python3 -m json.tool registry/Source-Registry-v1.yaml PASS
sh -n bin/signalforge                       PASS
sh -n deploy/deploy-signalforge-release.sh  PASS
git diff --check                            PASS
```

The live parser was also run against the current issuer HTML rather than only fixtures and reproduced the current four-item latest tender page correctly.

## Production acceptance after merge

S21 is **not** production-complete until all of the following pass on the exact merged SHA:

1. pause the production timer through the reviewed Control Plane verb;
2. snapshot S13/canonical/signal/Worker Run baseline;
3. deploy the exact merged SignalForge SHA to Bangkok only;
4. verify Beijing remains strict SignalForge zero-footprint;
5. execute reviewed `signalforge-refresh S21` once to establish the first S21 baseline;
6. prove the first S21 baseline creates **zero customer signals**;
7. prove exactly one Worker application Run correlates to the S21 manual baseline invocation;
8. verify S21 acquisition/evidence/processing rows and Railway canonical rows are durable;
9. verify S13 canonical/signal state is unchanged except normal production activity outside the paused window;
10. verify SQLite `quick_check=ok`;
11. verify Bangkok + Beijing Worker doctors remain PASS;
12. restore `signalforge-run-due.timer` to `enabled/active/waiting`;
13. record the final live onboarding evidence and update `CHECKPOINT.md` / `GOAL.md`.

Until those steps pass, this record remains `PRE_PRODUCTION`.
