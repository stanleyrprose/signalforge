# PIC-v1 R1 Durable Provider Queue — 2026-09-08

> Historical evidence scope — added 2026-10-24: the original observations, PASS/FAIL results, deployment SHAs, source roles, cadence, model choices and next-step recommendations below apply to the recorded date/release/subsystem. They do not establish current authorization, deployment or delivery health. Current product requirements follow [GOAL](../../GOAL.md) and the [S01/S52/S53 news contract](../S01-S52-S53-NEWS-DELIVERY-CONTRACT.md); surviving technical controls require confirmation against current code. This scope note does not change the historical results.

**Phase:** R1  
**Status:** IMPLEMENTED ON FEATURE BRANCH / CI GATE PENDING

## Purpose

Add the durable provider lifecycle on Bangkok without yet enabling cross-host production invocation.

R1 adds two SignalForge-owned tables:

```text
provider_requests
provider_attempts
```

These are business/acquisition-internal SignalForge state and are intentionally not VPS Worker Runs.

## Implemented lifecycle

```text
PENDING
  -> CLAIMED
      -> SUCCEEDED
      -> FAILED
  -> EXPIRED

CLAIMED -- lease expiry while request still valid --> PENDING
```

Implemented behavior:

- contract validation before enqueue;
- enqueue idempotency by provider_request_id + request SHA;
- priority-descending / FIFO claim order;
- `BEGIN IMMEDIATE` atomic claim;
- one high-entropy claim token per attempt;
- only SHA-256(claim token) stored in Bangkok DB;
- provider_attempt_id distinct from provider_request_id;
- bounded 1..300 second claim lease;
- expired lease recovery for read-only/retry-safe work;
- request expiry;
- exactly-once successful completion boundary;
- duplicate identical completion -> `ALREADY_ACCEPTED`;
- conflicting duplicate completion -> fail closed;
- provider failure recording under `PROVIDER_*` namespace;
- queue status counts.

## C0-C3

The queue is capability-neutral after R0 validation and can persist ProviderRequests for:

```text
C0_FETCH
C1_RENDER
C2_INSPECT
C3_BROWSER_USE
```

R1 does not itself execute Browser work. C3 retry semantics remain governed by the R0 request's explicit `retry_safe` + `READ_ONLY_NAVIGATION` contract; R2 must respect that before reclaim/replay behavior is used operationally.

## Production boundary unchanged

R1 deliberately does not change:

```text
Source Registry production_enabled=false
remote_invocation=false
browser_production_approved=false
22 current active sources
SignalForge timers
Bangkok/Beijing Worker runtime
Mac Browser Plane runtime
```

No SSH account/key/forced-command is installed in R1 feature code. That host-level deployment is the next R1B/R2 integration slice after queue CI passes.

## Gate

Expected:

```text
python -m pytest tests/test_provider_invocation.py tests/test_provider_queue.py -q
python -m pytest -q
```
