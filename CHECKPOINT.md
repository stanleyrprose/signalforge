# CHECKPOINT

Date: 2026-09-04 (Asia/Yangon)
Branch: `main` after S21 Myanma Railways production onboarding closure.

## Production releases

- SignalForge current application: `52c9ab5b5e5643014e1b55a634cc5fbe26c0ebac`
- Immediate SignalForge rollback (v1.5 S13-only): `618afaf4e6ef2ac7fdde64931f2a87dbc053a6f6`
- SignalForge v1.4.5 known-good rollback: `d36f38336bf1b10580cffdb7fa96c7db119c2079`
- Worker runtime/provider on Bangkok + Beijing: `0a53558c9233622c69b083d61bed596cbedc0857`
- Control Plane dispatcher/validator: `64ab3a907bb8a18808839176208023a5de976b55`
- Worker v1.4.5 final contract/docs closure: `c80c4e81a3f60b018c07f82bb72e4541e13cdef5`

## Current production health

- Worker fleet: `FULL 2/2`
- Bangkok Worker Runtime: PASS
- Beijing Worker Runtime: PASS
- Bangkok `nanobot-gateway.service`: active
- Beijing `hermes-gateway.service`: active
- Bangkok SignalForge: ENABLED / GREEN
- S13 source health: GREEN
- S21 source health: GREEN
- S21 parse health: GREEN (`10/10`, ratio `1.0` at baseline)
- Bangkok `signalforge-run-due.timer`: enabled / active / waiting
- Beijing SignalForge placement: DISABLED with strict `/srv/signalforge` absence
- SQLite `PRAGMA quick_check`: ok

## Current SignalForge business state

Final live state after S21 baseline and timer restoration:

```text
canonical_items=61
signals=10
scheduler_runs=85
failed_runs=0
recovery_backlog=0
acquisition_requests=23
acquisition_attempts=23
evidence_envelopes=23
processing_records=23
```

S21-owned state:

```text
canonical_items=45
signals=0
acquisition_requests=11
acquisition_attempts=11
evidence_envelopes=11
processing_records=11
```

The S21 first production baseline parsed 45 tenders from 10 current detail pages and created zero customer signals.

## Production sources

### S13 — MPT Tender Information — GREEN

Existing production semantics remain unchanged.

### S21 — Myanma Railways Tenders — GREEN / PRODUCTION COMPLETE

Production release: `52c9ab5b5e5643014e1b55a634cc5fbe26c0ebac`.

Source shape:

```text
category HTML
-> N detail pages
-> one detail page -> N Railway tender rows
-> N canonical items
```

Canonical identity:

```text
railways:<normalized tender reference>
```

The first baseline used the reviewed `signalforge-refresh S21` path:

```text
baseline=1
status=SUCCESS
details_attempted=10
details_succeeded=10
tenders_parsed=45
changed=45
signals_created=0
```

Worker correlation:

```text
Worker SignalForge Runs: 299 -> 300
S21 worker_run_id=signalforge-20260903T180207Z-0b368d02
Worker latest Run ID=same / SUCCESS
```

Evidence: `docs/verification/S21-SOURCE-ONBOARDING-2026-09-04.md`.

## Completed SignalForge / integration gates

### Gate O — Topology / MPT fixture — PASS

- Bangkok-only SignalForge and Beijing strict absence verified.
- Source Registry remains owned only by SignalForge.
- real MPT Direct HTTP fixture/pipeline verified.
- first baseline produced no customer signal.

Evidence: `docs/verification/GATE-O-2026-09-02.md`.

### Gate S — Bangkok Recovery Reconciliation — PASS

- recovery backlog is durable and bounded;
- no crawl-all storm, duplicate canonical item or duplicate signal.

Evidence: `docs/verification/GATE-S-2026-09-02.md`.

### Gate Z — Single-scheduler Invocation — PASS

- one scheduler/manual wrapper invocation maps to one opaque Worker application Run;
- source/business Jobs and acquisition attempts remain SignalForge-owned;
- Worker DB does not own source/business identity.

S21 reconfirmation: after timer resume, one wrapper changed Worker SignalForge Runs `300 -> 301` while SignalForge `scheduler_runs` stayed `85 -> 85` because no source was due.

Evidence: `docs/verification/GATE-Z-2026-09-03.md` and S21 onboarding record.

### Gate AA — Cross-repo Verb Compatibility — PASS

- `verb_manifest_version=1` remains live;
- active Source Registry membership now exposes S13 + S21;
- Beijing continues to reject all SignalForge verbs.

Worker evidence: `vps-worker-plane/docs/verification/GATE-AA-2026-09-03.md`.

### Gate AB — v1.5 Production Compatibility — PASS

v1.5 remains the frozen acquisition/Worker compatibility baseline.

Evidence: `docs/verification/GATE-AB-2026-09-03.md`.

### S21 Source Onboarding — PASS

- PR #14 CI PASS and merged;
- exact SHA deployed to Bangkok only;
- Bangkok Direct HTTP transport verified;
- first baseline signal suppression verified;
- 45 Railway canonical items durable;
- SQLite quick_check ok;
- Worker cardinality/correlation verified;
- Bangkok + Beijing Worker doctors PASS;
- Beijing remains strict zero-footprint and returns `126 / DENY: SignalForge is Bangkok-only` for `signalforge-refresh S21`;
- timer restored enabled / active / waiting.

Evidence: `docs/verification/S21-SOURCE-ONBOARDING-2026-09-04.md`.

## v1.5 acquisition contract — production

The production lifecycle now supports source-specific adapters while keeping common acquisition ownership:

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

Frozen invariants remain:

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

S21 triggered none of these gates.

## Next

1. operate S13 + S21 and collect real source/acquisition history;
2. continue Myanmar Source Expansion with **S22 Inland Water Transport** as the preferred next candidate, beginning with a fresh endpoint/shape audit;
3. keep S20 MOEP Main as another provisional candidate;
4. preserve the previously identified YCDC/MCDC/NPTDC identity/PDF/classifier conditions rather than bypassing them;
5. use Direct HTTP first and trigger capability expansion only from real fixture evidence;
6. run the next cross-repo consistency review by 2026-12-03 or an earlier contract-change trigger.
