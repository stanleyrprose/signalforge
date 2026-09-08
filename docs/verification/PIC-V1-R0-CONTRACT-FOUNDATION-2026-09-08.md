# PIC-v1 R0 Contract Foundation — 2026-09-08

**Phase:** R0  
**Status:** IMPLEMENTED ON FEATURE BRANCH / CI GATE PENDING

## Scope

R0 intentionally changes no production execution path. It adds a pure machine contract for the future Bangkok SignalForge -> `mac-mm-01` Provider Invocation path.

Implemented contract concepts:

```text
Provider capabilities:
C0_FETCH        -> browser_fetch
C1_RENDER       -> browser_render
C2_INSPECT      -> browser_inspect
C3_BROWSER_USE  -> browser_use
```

It also implements:

- canonical JSON request SHA-256;
- ProviderRequest UUID correlation validation;
- exact source capability allowlist;
- target-role capability allowlist;
- HTTPS-only URL validation;
- exact URL or exact-host/path-prefix validation;
- credentials/path traversal/query/fragment rejection;
- global and target-specific byte/run-time limits;
- bounded request TTL;
- idempotency-key correlation;
- C3 `READ_ONLY_NAVIGATION` interaction-plan requirement;
- C3 explicit `retry_safe` declaration;
- C3 arbitrary shell/JavaScript/command field rejection.

## Deliberately not changed in R0

- `production_enabled=false` remains unchanged;
- `remote_invocation=false` remains unchanged;
- `browser_production_approved=false` remains unchanged;
- no production source is provider-backed;
- no SignalForge DB migration;
- no SSH key/user/dispatcher;
- no Mac Provider Agent;
- no timer/scheduler behavior change;
- no VPS Browser runtime;
- no public Mac MCP/HTTP/CDP endpoint.

This preserves the current 22-source Direct HTTP production baseline while making the PIC request/security semantics testable before any cross-host transport exists.

## R0 gate

Expected verification:

```text
python -m pytest tests/test_provider_invocation.py -q
python -m pytest -q
git diff --check
```

R1 is authorized only after R0 CI PASS.
