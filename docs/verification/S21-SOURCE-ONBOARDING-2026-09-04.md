# S21 Myanma Railways — Source Onboarding Verification

Date (Asia/Yangon): 2026-09-04
Phase: `PRODUCTION`
Result: **PASS / PRODUCTION COMPLETE**

## Decision

S21 Myanma Railways is the first production source expansion after SignalForge v1.5 closure.

It stays inside the frozen v1.5 architecture:

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

No Worker ABI, Control Plane verb, remote Provider, Browser/Browserless, Mac production dependency, Beijing acquisition, Redis/Celery, distributed queue or automatic cross-zone failover was introduced.

## Release

- SignalForge production release: `52c9ab5b5e5643014e1b55a634cc5fbe26c0ebac`
- Implementation PR: `#14 feat: onboard Myanma Railways S21`
- PR CI `verify`: PASS
- Immediate rollback release: `618afaf4e6ef2ac7fdde64931f2a87dbc053a6f6`
- Worker Bangkok + Beijing: `0a53558c9233622c69b083d61bed596cbedc0857`
- Control Plane: `64ab3a907bb8a18808839176208023a5de976b55`

The live Bangkok `/srv/signalforge/active` symlink was verified to resolve to the exact merged SHA above.

## Why S21 first

The pre-code engineering audit classified Myanma Railways as issuer-original, engineering-value rich, `GREEN-CANDIDATE / PARSE-STRONG`, and a Type-A structured HTML source. It did not require the identity-segmentation, scanned-PDF, mixed-board classifier or Browser gates that remain relevant to some other candidates.

## Current transport / shape verification

### Local / Myanmar-side re-audit

Standard HTTPS with normal certificate verification against:

```text
https://www.railways.gov.mm/category/tender/
```

returned HTTP 200 / `text/html`. The live listing parser found 10 current detail pages; the newest publication date was `2026-09-01`.

The newest detail page parsed into four independent tender rows:

```text
၃၂၆/မမ/CE
12(T)30/MR (ML/ISN)
15(T)5/MR(E)
၃၂၇/မမ/CMO
```

The shared Burmese deadline `(၁၄.၉.၂၀၂၆)` normalized to `2026-09-14`.

### Bangkok production egress

Before deployment, Bangkok performed three sequential standard-TLS reads of the category endpoint:

```text
HTTP 200 in 0.456s
HTTP 200 in 0.366s
HTTP 200 in 0.271s
```

The current newest detail page returned `HTTP 200`, `text/html`, 75535 bytes, and the raw response contained `၃၂၆/မမ/CE`.

Direct HTTP is sufficient; no Browser capability gate is triggered.

## Source-shape contract

S21 differs from MPT's current one-detail-page/one-business-item shape. One Railway detail page can contain multiple tender rows.

The implemented adapter contract is:

```text
Tender category HTML
-> N detail URLs
-> one detail HTML
-> N RailwayTender business items
-> one acquisition / evidence / processing lifecycle for that fetched page
-> N canonical upserts
```

For multi-item detail pages, `discovery_items.canonical_key` remains `NULL`; the system does not invent a false one-URL-to-one-canonical relationship.

## Canonical identity

S21 canonical identity is:

```text
railways:<normalized tender reference>
```

Myanmar digits in the tender reference are normalized to ASCII digits while issuer-specific Burmese / Latin reference components are preserved.

Examples:

```text
၃၂၆/မမ/CE      -> railways:326/မမ/CE
12(T)30/MR ... -> railways:12(T)30/MR(ML/ISN)
```

The `railways:` namespace prevents cross-source collisions with MPT canonical keys.

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

Fail-closed capability policy remains:

```text
TLS_FAILURE -> FAIL
JS_RENDER_REQUIRED -> REVIEW_CAPABILITY
PARSER_DRIFT -> REAUDIT
```

## Pre-production verification

Targeted S21 + MPT regression suite:

```text
15/15 PASS
```

CI-equivalent SignalForge unit suite including Railways:

```text
25/25 PASS
```

Release checks:

```text
python3 -m compileall -q signalforge tests        PASS
python3 -m json.tool registry/Source-Registry-v1.yaml PASS
sh -n bin/signalforge                            PASS
sh -n deploy/deploy-signalforge-release.sh       PASS
git diff --check                                 PASS
```

The Railways parser was also run against current live issuer HTML and reproduced the four-item latest detail correctly.

## Controlled production rollout

The production timer was paused through the reviewed `signalforge-pause` Control Plane verb before deployment.

Frozen pre-deploy state:

```text
SignalForge release=618afaf4e6ef2ac7fdde64931f2a87dbc053a6f6
canonical_items=16
signals=10
scheduler_runs=84
acquisition_requests=12
acquisition_attempts=12
failed_runs=0
recovery_backlog=0
Worker SignalForge application Runs=299
S13 health=GREEN
timer=disabled/inactive (controlled pause)
```

The exact merge SHA `52c9ab5b5e5643014e1b55a634cc5fbe26c0ebac` was transferred as a Git archive and deployed to Bangkok only. The deploy script reported:

```text
deployment=success
previous=618afaf4e6ef2ac7fdde64931f2a87dbc053a6f6
timer_preexisting=0
```

The post-deploy manifest exposed exactly:

```text
active_source_ids=[S13,S21]
verb_manifest_version=1
```

## First S21 production baseline — PASS

The reviewed Control Plane path executed:

```text
signalforge-refresh S21
```

Live result:

```text
trigger_kind=MANUAL
baseline=1
status=SUCCESS
details_attempted=10
details_succeeded=10
tenders_parsed=45
changed=45
signals_created=0
recovery_backlog=0
```

Business-state change:

```text
canonical_items: 16 -> 61
signals:         10 -> 10
scheduler_runs:  84 -> 85
```

Therefore the first Railway baseline created 45 durable Railway canonical items and **zero customer signals**, as required.

## Acquisition / evidence persistence — PASS

The baseline fetched one discovery page plus ten bounded detail pages:

```text
S21 acquisition_requests=11
S21 acquisition_attempts=11
S21 evidence_envelopes=11
S21 processing_records=11
S21 canonical_items=45
S21 signals=0
PRAGMA quick_check=ok
```

S21 health after baseline:

```text
fetch_health=GREEN
parse_health=GREEN
parse_attempts=10
parse_successes=10
parse_success_ratio=1.0
recovery_backlog_health=GREEN
source_health=GREEN
```

## Worker cardinality / correlation — PASS

Before the S21 baseline:

```text
Worker SignalForge application Runs=299
```

After the S21 baseline:

```text
Worker SignalForge application Runs=300
latest Worker Run=signalforge-20260903T180207Z-0b368d02 / SUCCESS
```

The S21 scheduler row stores the same Worker Run ID:

```text
worker_run_id=signalforge-20260903T180207Z-0b368d02
```

Thus one reviewed manual source refresh created exactly one Worker application Run while the eleven acquisition attempts and 45 business items remained internal SignalForge state.

## Topology / Worker verification — PASS

Bangkok `workerctl doctor`:

```text
PASS
repo-contract=PASS
job-contracts=PASS
state-db=PASS
state-lock-wait=PASS
notification-backlog=PASS
```

Beijing `workerctl doctor` returned the same PASS set.

Beijing remained strict zero-footprint:

```text
/srv/signalforge absent
```

and `signalforge-refresh S21` on Beijing returned:

```text
126 / DENY: SignalForge is Bangkok-only
```

## Timer restoration / Gate Z observation — PASS

The reviewed `signalforge-resume` verb restored the production timer.

Final systemd state:

```text
signalforge-run-due.service=inactive/dead, Result=success, ExecMainStatus=0
signalforge-run-due.timer=enabled/active/waiting
```

The resume produced one immediate persistent-timer wrapper invocation:

```text
Worker SignalForge application Runs: 300 -> 301
SignalForge scheduler_runs:           85 -> 85
```

No source was due, so the wrapper created one Worker operational Run and zero business scheduler rows. This is the expected Gate Z cardinality and confirms that adding S21 did not turn acquisition attempts or source jobs into Worker Runs.

## Final production state

```text
SignalForge release=52c9ab5b5e5643014e1b55a634cc5fbe26c0ebac
active sources=S13,S21
SignalForge health=GREEN
S13 health=GREEN
S21 health=GREEN
canonical_items=61
signals=10
scheduler_runs=85
acquisition_requests=23
acquisition_attempts=23
evidence_envelopes=23
processing_records=23
failed_runs=0
recovery_backlog=0
SQLite quick_check=ok
Bangkok Worker doctor=PASS
Beijing Worker doctor=PASS
Beijing SignalForge footprint=ABSENT
timer=enabled/active/waiting
```

## Conclusion

S21 Myanma Railways source onboarding is **PASS / PRODUCTION COMPLETE**.

It is the first proof that the v1.5 local acquisition contract can support a second source with a materially different HTML shape — including one detail page producing multiple business items — without changing Worker ABI, scheduler cardinality, topology, source-health ownership or customer-signal baseline semantics.
