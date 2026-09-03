# CHECKPOINT

Date: 2026-09-03 (Asia/Yangon)
Branch: `main` after v1.5 Gate AB closure merge.

## Production releases

- SignalForge v1.5 application: `618afaf4e6ef2ac7fdde64931f2a87dbc053a6f6`
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
- S13 fetch health: GREEN
- S13 parse health: GREEN
- S13 recovery backlog health: GREEN
- Bangkok `signalforge-run-due.timer`: enabled / active / waiting
- Beijing SignalForge placement: DISABLED with strict `/srv/signalforge` absence
- SQLite `PRAGMA quick_check`: ok

## Current SignalForge business state after v1.5 Gate AB

```text
canonical_items=16
signals=10
failed_runs=0
recovery_backlog=0
scheduler_runs=83 at the final business-state check
acquisition_requests=7
acquisition_attempts=7
evidence_envelopes=7
processing_records=7
```

A subsequent persistent-timer wrapper invocation increased the Worker SignalForge application Run count without creating a business scheduler row because S13 was not due. This is expected Gate Z behavior.

## Completed SignalForge / integration gates

### Gate O — Topology / MPT fixture — PASS

- Bangkok-only SignalForge and Beijing strict absence verified.
- Source Registry remains owned only by the SignalForge repository.
- real MPT Direct HTTP fixture/pipeline verified.
- first baseline produced no customer signal.
- parser/canonical and Worker Run correlation verified.

Evidence: `docs/verification/GATE-O-2026-09-02.md`.

### Gate S — Bangkok Recovery Reconciliation — PASS

- schema v2 introduced durable observed-vs-processed discovery state.
- recovery backlog survives snapshots/process boundaries.
- bounded fixture recovery drained five changes as `2 + 2 + 1` with backlog `3 -> 1 -> 0`.
- no crawl-all storm, duplicate canonical item, or duplicate signal.
- recovery health/RTO evidence passed and production state was not polluted by the fixture.

Evidence: `docs/verification/GATE-S-2026-09-02.md`.

### Gate Z — SignalForge Single-scheduler Invocation — PASS

- scheduler uses dedicated `signalforge` UID / `worker-signalforge.slice` and not Generic `worker@.service`.
- one scheduler invocation maps to one opaque Worker application Run.
- business Jobs remain in SignalForge DB; Worker DB does not own source/business identity.
- SignalForge cannot write `worker.db`.
- Beijing remains strict zero-footprint.

Evidence: `docs/verification/GATE-Z-2026-09-03.md`.

### Gate AA — Cross-repo Verb Compatibility — PASS

- `verb_manifest_version=1` compatibility handshake is live.
- unknown/newer manifest versions fail closed.
- dispatcher/provider grammar is independently validated.
- provider-first rolling upgrade was exercised live.
- GitHub cannot invoke unregistered helper verbs.

Worker evidence: `vps-worker-plane/docs/verification/GATE-AA-2026-09-03.md`.

### Gate AB — v1.5 Production Compatibility — PASS

- exact SignalForge v1.5 merge SHA is live on Bangkok.
- v1.4.5 remains the known-good rollback target.
- one reviewed scheduler-wrapper invocation changed Worker SignalForge Runs `291 -> 292` while SignalForge `scheduler_runs` stayed `82 -> 82` because S13 was not due.
- inactive source `S99` was denied with exit 126 and created no Worker Run.
- active `S13` manual refresh changed Worker SignalForge Runs `292 -> 293` and SignalForge `scheduler_runs` `82 -> 83` with `trigger_kind=MANUAL`.
- v1.5 lifecycle rows advanced one-for-one (`6 -> 7`) while canonical items stayed 16 and signals stayed 10.
- SQLite quick_check remained `ok`.
- Bangkok and Beijing Worker doctors both PASS.
- Beijing remains strict SignalForge zero-footprint and rejects SignalForge control verbs.
- production timer was restored to enabled / active / waiting.

Evidence: `docs/verification/GATE-AB-2026-09-03.md`.

## Source Health contract — production

SignalForge owns business/source health semantics. Current S13 policy includes:

- freshness thresholds relative to 900s polling interval;
- rolling tender parser success with minimum sample count;
- bounded low-frequency parser health probe;
- fetch failure health;
- recovery backlog health;
- application-owned `signalforge_health=GREEN|YELLOW|RED` plus bounded `reason_code`.

Production schema is v4. Historical rows migrated additively without changing canonical/signal state. Worker Fleet only consumes the bounded summary and does not recompute business health.

## v1.5 acquisition contract — production

The Bangkok local Direct HTTP path now explicitly records SignalForge-owned:

```text
Source Acquisition Policy
-> AcquisitionRequest
-> AcquisitionAttempt
-> EvidenceEnvelope
-> ProcessingRecord
-> Canonical / Dedup / Signal
```

Frozen v1.5 invariants:

- `AcquisitionRequest != Worker Run`.
- `AcquisitionAttempt != Worker Run`.
- Worker DB has no SignalForge business/acquisition semantics.
- Direct HTTP remains default.
- no silent Browser escalation.
- TLS failure never becomes certificate bypass or automatic Browser success.
- no remote Provider transport, Redis/Celery, central scheduler or automatic cross-zone failover.
- Mac remains non-production.
- Beijing remains Generic Worker only.

## Closed manual source refresh — production

Final reviewed path:

```text
signalforge-refresh <source_id>
-> Control Plane grammar + manifest + active-source membership
-> Bangkok-only placement check
-> signalforge-refresh@<source_id>.service
-> Worker PREPARE
-> SignalForge refresh-source <source_id>
-> trigger_kind=MANUAL
-> Worker FINALIZE
```

Properties:

- arbitrary URL input is impossible;
- same `signalforge` UID/slice/resource/sandbox as scheduler;
- inactive source is rejected with 126 before systemd business execution and creates no Worker Run;
- active S13 succeeds and creates exactly one Worker application Run;
- Beijing returns `126 / DENY: SignalForge is Bangkok-only`.

## Worker / host safeguards relied on by SignalForge

- root-owned Worker operational DBs; SignalForge write denied;
- `ProtectProc=invisible` + `ProcSubset=pid` cross-UID isolation verified live;
- Bangkok child slices benchmarked under real SignalForge + Generic concurrent load;
- Bangkok Generic slice: 128M High / 192M Max / 50% CPU;
- Bangkok SignalForge slice: 384M High / 512M Max / 100% CPU;
- aggregate Worker slice: 600M High / 800M Max / 150% CPU;
- health history writes only sanitized samples to `diagnostics.db`, 14-day retention;
- Host Baseline v2 journald budget is live on both VPS hosts;
- local break-glass uses root-only `worker-admin`, real TTY, human reason and audit.

## v1.4.5 closure / rollback baseline

The v1.4.5 authorized production scope — R0–R2 Shared Worker Runtime + Bangkok-only R5 SignalForge — remains implementation/deployment/live-verification/cross-repo-contract **PASS** and is now the known-good rollback baseline for v1.5.

Worker closure records:

- `vps-worker-plane/docs/verification/V1.4.5-MANDATORY-CLOSURE-2026-09-03.md`
- `vps-worker-plane/docs/verification/contract-review/2026-09-03.md`

Next calendar cross-repo review is due no later than **2026-12-03**, or earlier after a major/minor production release, security-boundary change, Job Runtime ABI change, incompatible Trigger/Webhook schema change, or identity-model change.

## v1.5 closure

SignalForge v1.5 — Acquisition Policy & Local Contract Foundation — P0 is now:

> **IMPLEMENTED / CI PASS / DEPLOYED / GATE AB PASS / PRODUCTION COMPLETE**

The release changes SignalForge internal acquisition lifecycle state only. It does not reopen or replace the proven Worker/Control topology.

## Conditional future gates — NOT TRIGGERED

Do not implement these merely to complete a checklist:

- Browser/Crawlee Gates O2/P/Q: only after a real source fixture proves Direct HTTP insufficient specifically because JS rendering is required.
- Webhook Gate T: only after a real webhook provider/use case and ingress/auth/dedup contract exist.
- Dedicated identity Gate V: before the first real dedicated Generic Job retirement; no production retirement exists yet.
- Remote Provider ADR: only after a real source proves Bangkok local acquisition insufficient.
- Mac production Provider ADR: only after a source-specific repeated residential-path need is proven.
- Browserless ADR: only after multiple real browser consumers create shared lifecycle/queue/session pain.

## Next

1. operate v1.5 and collect real acquisition/source history;
2. prioritize Myanmar Source Expansion over new infrastructure;
3. add each new source through business-value audit -> network/shape audit -> Direct HTTP fixture -> Source Acquisition Policy -> parser -> baseline -> health -> production;
4. treat real friction as the trigger for Browser, remote Provider, Mac production, API/PDF supplementary adapters or distributed coordination;
5. run the next cross-repo consistency review by 2026-12-03 or at an earlier contract-change trigger;
6. keep future capability gates fail-closed until their real trigger exists.
