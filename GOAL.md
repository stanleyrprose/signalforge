# GOAL — SignalForge v1.5 Production Closure

## Goal

Run SignalForge v1.5 — Acquisition Policy & Local Contract Foundation on top of the completed v1.4.5 production baseline without changing the proven external Worker/Control/Fleet/S13 behavior.

## Frozen production boundary

- SignalForge production is Bangkok-only.
- Beijing is Generic Worker only and must remain SignalForge-free.
- Direct HTTP is the default production acquisition method.
- One `signalforge-run-due.service` invocation creates one Worker operational Run; N business/source Jobs remain internal SignalForge state.
- `AcquisitionRequest` and `AcquisitionAttempt` are SignalForge-internal lifecycle objects, not Worker Runs.
- Worker DB contains no SignalForge acquisition/canonical business semantics.
- Source acquisition policy is explicit and fail-closed; TLS failure does not become certificate bypass or automatic Browser escalation.
- No remote Provider, Mac production dependency, Browserless, Redis/Celery, central scheduler, distributed queue, automatic Beijing failover or speculative Webhook is part of v1.5.

## v1.5 closure

v1.5 P0 is complete only when:

1. the additive acquisition schema and local contracts pass CI/fixture/DB migration verification;
2. exact reviewed SHA is deployed to Bangkok only;
3. Gate Z scheduler cardinality remains unchanged;
4. closed Control Plane verb/manifest behavior remains fail-closed;
5. S13 canonical/signal behavior remains equivalent;
6. manual refresh and recovery behavior remain equivalent;
7. Bangkok and Beijing Worker health remain PASS;
8. Beijing remains strict SignalForge zero-footprint;
9. SQLite quick_check and business-state preservation pass;
10. `signalforge-run-due.timer` is restored to enabled/active/waiting;
11. Gate AB is recorded as PASS.

Current result: **v1.5 P0 = IMPLEMENTED / CI PASS / DEPLOYED / GATE AB PASS / PRODUCTION COMPLETE**.

Evidence: `docs/verification/GATE-AB-2026-09-03.md`.

## Next authorized direction

Operate the current system and expand valuable Myanmar sources using the same local acquisition contract. Capability expansion is evidence-triggered: Direct HTTP first; Browser/remote Provider/Mac production/distributed coordination only after a real source or operational bottleneck proves the need.
