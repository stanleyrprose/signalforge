# CHECKPOINT

Date: 2026-09-04 (Asia/Yangon)
Branch: `main` after S05A Ministry of Commerce regulatory-notice production onboarding closure.

## Production releases

- SignalForge current application: `3c833d62dcf16ecd9e4b12dafd9ac557417efddb`
- Immediate SignalForge rollback (S13 + S20 + S21 + S22): `255f18f3dd919b6e77b9d3138839f0439062e3bc`
- Previous SignalForge S13 + S21 + S22 release: `9ec2b133ca1c3339abccf34c5f5c86cecd3e6023`
- Previous SignalForge S13 + S21 release: `52c9ab5b5e5643014e1b55a634cc5fbe26c0ebac`
- Previous SignalForge v1.5 S13-only release: `618afaf4e6ef2ac7fdde64931f2a87dbc053a6f6`
- SignalForge v1.4.5 known-good rollback: `d36f38336bf1b10580cffdb7fa96c7db119c2079`
- Worker runtime/provider on Bangkok + Beijing: `0a53558c9233622c69b083d61bed596cbedc0857`
- Control Plane dispatcher/validator: `64ab3a907bb8a18808839176208023a5de976b55`

## Current production health

- Worker fleet: `FULL 2/2`
- Bangkok Worker Runtime: PASS
- Beijing Worker Runtime: PASS
- Bangkok `nanobot-gateway.service`: active
- Beijing `hermes-gateway.service`: active
- Bangkok SignalForge: ENABLED / GREEN
- S05A source health: GREEN
- S05A parse health at baseline: GREEN (`3/3`, ratio `1.0`)
- S05A canonical domain: `REGULATORY_NOTICE`; baseline `items_parsed=3`, `tenders_parsed=0`
- S13 source health: GREEN
- S20 source health: GREEN
- S20 parse health at baseline: GREEN (`5/5`, ratio `1.0`)
- S20 attachment health: DEGRADED (`0/5` current advertised PDFs retrievable; metadata-only/non-blocking)
- S21 source health: GREEN
- S22 source health: GREEN
- S22 parse health at baseline: GREEN (`4/4`, ratio `1.0`)
- Bangkok `signalforge-run-due.timer`: enabled / active / waiting
- Beijing SignalForge placement: DISABLED with strict `/srv/signalforge` absence
- SQLite `PRAGMA quick_check`: ok

## Current SignalForge business state

Final live state after S05A baseline and timer restoration:

```text
canonical_items=73
signals=10
scheduler_runs=152
failed_runs=0
recovery_backlog=0
acquisition_requests=198
acquisition_attempts=198
evidence_envelopes=198
processing_records=198
Worker SignalForge application Runs=406
```

Per-source canonical/signal state verified during the paused rollout window:

```text
S05A canonical_items=3  / signals=0 / item_kind=REGULATORY_NOTICE
S13 canonical_items=16 / signals=10 / item_kind=TENDER
S20 canonical_items=5  / signals=0 / item_kind=TENDER
S21 canonical_items=45 / signals=0 / item_kind=TENDER
S22 canonical_items=4  / signals=0 / item_kind=TENDER
```

S22 onboarding-owned acquisition lifecycle:

```text
acquisition_requests=5
acquisition_attempts=5
evidence_envelopes=5
processing_records=5
```

The four S22 rows are issuer nodes 1038, 1037, 1036 and 1035. The baseline created no customer signals.

## Production sources

### S05A — Ministry of Commerce Trade Notifications — GREEN / PRODUCTION COMPLETE

Current production release: `3c833d62dcf16ecd9e4b12dafd9ac557417efddb`.

Source/domain shape:

```text
Myanmar Commerce Notifications Drupal view
-> bounded HTML detail fetch
-> ACTIVE_SELECTIVE business classification
-> zero/one REGULATORY_NOTICE canonical item
-> attachment metadata only
```

First baseline: 3 selected regulatory notices, `items_parsed=3`, `tenders_parsed=0`, zero signals.

### S13 — MPT Tender Information — GREEN

Existing production semantics remain unchanged.

### S20 — MOEP Main Tender Hub — GREEN / PRODUCTION COMPLETE

First onboarding release: `255f18f3dd919b6e77b9d3138839f0439062e3bc`.

Source shape:

```text
/mm/ignite/page/62 HTML
-> latest 5 official tender items
-> one detail page -> one partial HTML tender
-> attachment metadata only
```

First production baseline through reviewed `signalforge-refresh S20`:

```text
baseline=1
status=SUCCESS
details_attempted=5
details_succeeded=5
tenders_parsed=5
changed=5
signals_created=0
worker_run_id=signalforge-20260904T011731Z-2575d704
```

Worker correlation:

```text
Worker SignalForge Runs: 389 -> 390
latest Worker Run=signalforge-20260904T011731Z-2575d704 / SUCCESS
```

S20 persistence:

```text
requests=6
attempts=6
evidence=6
processing=6
canonical=5
signals=0
PDF requested_url count=0
```

Current official attachment reality is degraded: the latest 5 advertised PDFs returned HTTP 404 from Bangkok. This does not reduce S20 HTML source health because attachments are explicitly `METADATA_ONLY_NON_BLOCKING`. Missing deadline/business-detail fields remain unknown rather than inferred.

Evidence: `docs/verification/S20-SOURCE-ONBOARDING-2026-09-04.md`.

### S21 — Myanma Railways Tenders — GREEN

- Direct HTTP / structured multi-item Railway detail pages.
- 45 canonical items remain durable.
- zero S21 customer signals have been created by the baseline.
- onboarding evidence: `docs/verification/S21-SOURCE-ONBOARDING-2026-09-04.md`.

### S22 — Inland Water Transport Tenders — GREEN / PRODUCTION COMPLETE

Production release: `9ec2b133ca1c3339abccf34c5f5c86cecd3e6023`.

Source shape:

```text
/tenders HTML
-> N Drupal tender nodes
-> one tender node -> one business tender
-> attachment metadata only
```

Canonical identity:

```text
iwt:<issuer Drupal node id>:<publication date>
```

Example:

```text
iwt:1038:2026-08-25
```

The required legacy `reference_no` field is explicit issuer-record metadata (`IWT-NODE-1038`, `reference_no_kind=issuer_record_id`) rather than pretending the node id is a business tender number.

First production baseline through reviewed `signalforge-refresh S22`:

```text
baseline=1
status=SUCCESS
details_attempted=4
details_succeeded=4
tenders_parsed=4
changed=4
signals_created=0
worker_run_id=signalforge-20260904T004652Z-d4992f14
```

Worker correlation:

```text
Worker SignalForge Runs: 381 -> 382
latest Worker Run=signalforge-20260904T004652Z-d4992f14 / SUCCESS
S22 scheduler worker_run_id=same
```

S22 acquisition/evidence persistence:

```text
requests=5
attempts=5
evidence=5
processing=5
canonical=4
signals=0
```

Evidence: `docs/verification/S22-SOURCE-ONBOARDING-2026-09-04.md`.

## S22 transport finding

A bare library-default Python urllib request currently receives HTTP 403 from IWT, but the already-frozen SignalForge application fetcher identity succeeds. Bangkok production egress using the actual SignalForge fetcher returned three consecutive successful Direct HTTP reads of the listing and successfully fetched node 1038.

This is an HTTP client-identity policy difference, not a Browser/JS-render requirement. No Browser gate was triggered and no browser-like spoofing was added.

If the production SignalForge fetcher itself later receives HTTP 403, the existing policy remains `HTTP_403 -> REVIEW`.

## S22 detail-change probe

IWT listing timestamps are publication timestamps and may not change when an existing tender's deadline/body changes.

Tender-only sources now use the newest currently discovered tender for the existing bounded low-frequency detail probe before falling back to static bootstrap seeds.

The regression fixture proved:

```text
same canonical iwt:1038:2026-08-25
deadline 2026-11-03 -> 2026-11-10
result=UPDATED, not duplicate NEW
```

This applies to S21/S22 tender-only discovery and does not change MPT behavior.

## Gate Z reconfirmation after S22

Before S22 baseline:

```text
Worker SignalForge Runs=381
scheduler_runs=128
```

After reviewed S22 baseline:

```text
Worker SignalForge Runs=382
scheduler_runs=129
```

Exactly one Worker operational Run correlated to the S22 manual baseline while five acquisition attempts and four business items remained internal SignalForge state.

After `signalforge-resume`, the persistent timer created one wrapper:

```text
Worker SignalForge Runs: 382 -> 383
```

S13 and S21 had become due during the controlled pause, so that single wrapper processed two business source jobs:

```text
S13 POLL = SUCCESS, details 1/1, signals 0
S21 POLL = SUCCESS, no pending detail, signals 0
scheduler_runs: 129 -> 131
```

This is the intended Gate Z relationship:

> one Worker wrapper Run may own N due SignalForge business source jobs; business jobs do not become separate Worker Runs.

S22 was not run again because its `next_due_at` had not arrived.

## Topology / integrity verification — PASS

- `PRAGMA quick_check=ok`.
- Bangkok Worker doctor: PASS.
- Beijing Worker doctor: PASS.
- Beijing `/srv/signalforge`: absent.
- Beijing `signalforge-refresh S22`: `126 / DENY: SignalForge is Bangkok-only`.
- `signalforge-run-due.timer`: enabled / active / waiting.
- final SignalForge health: GREEN.
- S13/S21/S22 final source health: GREEN.
- final `failed_runs=0`.
- final `recovery_backlog=0`.

## Completed SignalForge / integration gates

### Gate O — Topology / MPT fixture — PASS

Bangkok-only SignalForge and the original MPT pipeline remain proven.

Evidence: `docs/verification/GATE-O-2026-09-02.md`.

### Gate S — Bangkok Recovery Reconciliation — PASS

Recovery backlog remains durable and bounded without crawl-all storms or duplicate signals.

Evidence: `docs/verification/GATE-S-2026-09-02.md`.

### Gate Z — Single-scheduler Invocation — PASS

S22 onboarding reconfirmed both forms:

- one manual source baseline -> one Worker Run;
- one timer wrapper -> multiple due business source rows while remaining one Worker Run.

Evidence: `docs/verification/GATE-Z-2026-09-03.md`, S21 onboarding and S22 onboarding records.

### Gate AA — Cross-repo Verb Compatibility — PASS

- `verb_manifest_version=1` remains live;
- active Source Registry membership now exposes `S13`, `S20`, `S21`, `S22`;
- Beijing continues to reject SignalForge control verbs.

### Gate AB — v1.5 Production Compatibility — PASS

v1.5 remains the frozen acquisition/Worker compatibility baseline.

Evidence: `docs/verification/GATE-AB-2026-09-03.md`.

### S21 Source Onboarding — PASS

Evidence: `docs/verification/S21-SOURCE-ONBOARDING-2026-09-04.md`.

### S22 Source Onboarding — PASS

- PR #16 CI PASS and merged;
- exact SHA deployed to Bangkok only;
- Direct HTTP transport verified using the real SignalForge fetcher identity;
- first baseline signal suppression verified;
- four IWT canonical items durable;
- full closing-time and attachment metadata preserved from HTML;
- no PDF parser or Browser capability added;
- SQLite quick_check ok;
- Worker cardinality/correlation verified;
- Bangkok + Beijing Worker doctors PASS;
- Beijing remains strict zero-footprint and rejects `signalforge-refresh S22`;
- timer restored enabled / active / waiting;
- resumed wrapper processed due S13/S21 correctly with no signals or canonical changes.

Evidence: `docs/verification/S22-SOURCE-ONBOARDING-2026-09-04.md`.

### S20 Source Onboarding — PASS

- PR #18 CI PASS and merged;
- exact SHA `255f18f3dd919b6e77b9d3138839f0439062e3bc` deployed to Bangkok only;
- first baseline parsed 5/5 current MOEP detail pages;
- first baseline created zero customer signals;
- 5 S20 canonical items durable;
- one category + five detail acquisitions persisted; zero PDF requested URLs;
- SQLite quick_check ok;
- Worker cardinality/correlation verified (`389 -> 390`);
- Bangkok + Beijing Worker doctors PASS;
- Beijing remains strict zero-footprint and rejects `signalforge-refresh S20`;
- timer restored enabled / active / waiting with no immediate extra wrapper;
- S13/S21/S22 canonical/signal state remained unchanged.

Evidence: `docs/verification/S20-SOURCE-ONBOARDING-2026-09-04.md`.

### S05A Commerce Regulatory Notice Onboarding — PASS

- PR #21 CI PASS and squash-merged;
- exact SHA `3c833d62dcf16ecd9e4b12dafd9ac557417efddb` deployed to Bangkok only;
- additive schema v5 migrated 70 existing canonical rows to `item_kind=TENDER` with no business/signal changes;
- first baseline created 3 `REGULATORY_NOTICE` canonical items and zero customer signals;
- baseline operational metrics: `items_parsed=3`, `tenders_parsed=0`, parse `3/3`;
- one discovery + fifteen HTML detail acquisitions persisted; PDF requested URLs remained zero;
- Worker cardinality/correlation verified (`404 -> 405`) for the manual refresh;
- timer resume produced one Worker wrapper (`405 -> 406`) while SignalForge scheduler/business counts remained unchanged;
- SQLite quick_check ok;
- Bangkok + Beijing Worker doctors PASS;
- Beijing remains strict zero-footprint and rejects `signalforge-refresh S05A`;
- S13/S20/S21/S22 remained GREEN.

Evidence: `docs/verification/S05A-SOURCE-ONBOARDING-2026-09-04.md`.

## Frozen acquisition invariants

```text
Source Acquisition Policy
-> AcquisitionRequest
-> AcquisitionAttempt
-> Local Direct HTTP adapter
-> EvidenceEnvelope
-> source-specific parser/normalizer/canonicalizer
-> ProcessingRecord
-> Canonical / Dedup / Signal
```

Still frozen:

- `AcquisitionRequest != Worker Run`;
- `AcquisitionAttempt != Worker Run`;
- Worker DB has no SignalForge business/acquisition semantics;
- Direct HTTP remains default;
- no silent Browser escalation;
- TLS failure never becomes certificate bypass or automatic Browser success;
- no remote Provider transport, Redis/Celery, central scheduler or automatic cross-zone failover;
- Mac remains non-production;
- Beijing remains Generic Worker only.

## Conditional future gates — NOT TRIGGERED

- Browser/Crawlee Gates O2/P/Q: only after a real source proves Direct HTTP insufficient specifically because JS rendering is required.
- Webhook Gate T: only after a real webhook use case and ingress/auth/dedup contract exist.
- Dedicated identity Gate V: before the first real dedicated Generic Job retirement.
- Remote Provider ADR: only after a real source proves Bangkok local acquisition insufficient.
- Mac production Provider ADR: only after a source-specific repeated residential-path need is proven.
- Browserless ADR: only after multiple real browser consumers create shared lifecycle/queue/session pain.
- PDF supplementary adapter: only when issuer HTML lacks business-critical fields whose extraction materially improves the commercial signal.

S20, S22 and S05A triggered none of these gates. S20 did surface a real PDF-attachment degradation, while S05A proved retrievable official PDFs can still remain metadata-only when HTML is sufficient for event detection; neither condition was promoted into a new runtime capability.

## Next

1. operate S05A + S13 + S20 + S21 + S22 and collect real acquisition/source history;
2. choose the next source by business value plus current endpoint quality, not source-ID order;
3. S01 National Portal fresh audit: defer canonical onboarding; preserve only as a future discovery-aggregator/issuer-resolution capability because its labelled closing date can conflict with issuer-original evidence;
4. preferred next issuer-original audit pool: S04 Trade Portal legal documents, S07/S08A Customs, and S12 IRD; S05A is now production-complete;
5. periodically recheck whether MOEP advertised PDFs become retrievable; only then consider a supplementary PDF parser gate;
6. preserve YCDC/MCDC/NPTDC identity/PDF/classifier gates rather than bypassing them;
7. keep Direct HTTP first and trigger Browser/remote/Mac/PDF capability expansion only from real source evidence;
8. run the next cross-repo consistency review by 2026-12-03 or an earlier contract-change trigger.
