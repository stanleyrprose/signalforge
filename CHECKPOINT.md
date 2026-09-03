# CHECKPOINT

Date: 2026-09-03 (Asia/Yangon)
Branch: `main` after closure PR merge; this checkpoint update is docs-only.

## Production releases

- SignalForge application: `d36f38336bf1b10580cffdb7fa96c7db119c2079`
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

## Source Health contract — production

SignalForge owns business/source health semantics. Current S13 policy includes:

- freshness thresholds relative to 900s polling interval;
- rolling tender parser success with minimum sample count;
- bounded low-frequency parser health probe;
- fetch failure health;
- recovery backlog health;
- application-owned `signalforge_health=GREEN|YELLOW|RED` plus bounded `reason_code`.

Production schema is v3. Historical v2 rows safely migrated without changing canonical/signal counts. Worker Fleet only consumes the bounded summary and does not recompute business health.

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
- inactive source `S99` is rejected with 126 before systemd start and creates no Worker Run;
- active `S13` succeeds and creates exactly one Worker application Run;
- Beijing returns `126 / DENY: SignalForge is Bangkok-only`.

Final live valid refresh moved SignalForge scheduler Runs `73 -> 74` and Worker SignalForge application Runs `259 -> 260`, while customer Signals remained `10`.

## Worker / host safeguards now relied on by SignalForge

- root-owned Worker operational DBs; SignalForge write denied;
- `ProtectProc=invisible` + `ProcSubset=pid` cross-UID isolation verified live;
- Bangkok child slices benchmarked under real SignalForge + Generic concurrent load;
- Bangkok Generic slice: 128M High / 192M Max / 50% CPU;
- Bangkok SignalForge slice: 384M High / 512M Max / 100% CPU;
- aggregate Worker slice: 600M High / 800M Max / 150% CPU;
- health history writes only sanitized samples to `diagnostics.db`, 14-day retention;
- Host Baseline v2 journald budget is live on both VPS hosts;
- local break-glass uses root-only `worker-admin`, real TTY, human reason and audit.

## v1.4.5 closure

The authorized production scope — R0–R2 Shared Worker Runtime + Bangkok-only R5 SignalForge — is implementation/deployment/live-verification/cross-repo-contract **PASS**.

Worker closure records:

- `vps-worker-plane/docs/verification/V1.4.5-MANDATORY-CLOSURE-2026-09-03.md`
- `vps-worker-plane/docs/verification/contract-review/2026-09-03.md`

Next calendar cross-repo review is due no later than **2026-12-03**, or earlier after a major/minor production release, security-boundary change, Job Runtime ABI change, incompatible Trigger/Webhook schema change, or identity-model change.

## Conditional future gates — NOT TRIGGERED

Do not implement these merely to complete a checklist:

- Browser/Crawlee Gates O2/P/Q: only after a real source fixture proves Direct HTTP insufficient.
- Webhook Gate T: only after a real webhook provider/use case and ingress/auth/dedup contract exist.
- Dedicated identity Gate V: before the first real dedicated Generic Job retirement; no production retirement exists yet.

## Next

1. operate the current production system and collect real S13 business/source history;
2. treat any new source as a SignalForge Source Registry/business change, not a Worker Generic Job by default;
3. use Direct HTTP first and escalate to Browser only on fixture evidence;
4. run the next cross-repo consistency review by 2026-12-03 or at an earlier contract-change trigger;
5. keep future capability gates fail-closed until their real trigger exists.
