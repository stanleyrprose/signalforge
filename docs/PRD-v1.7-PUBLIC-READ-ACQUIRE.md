# SignalForge PRD v1.7 — PUBLIC_READ_ACQUIRE Provider Extension

**Date:** 2026-09-30
**Status:** PRODUCTION VERIFIED / CLOSED

## Goal

Remove C0-vs-C1 acquisition selection from normal SignalForge HTML source logic. For approved Mac-provider HTML sources, Bangkok asks for one high-level capability:

```text
PUBLIC_READ_ACQUIRE -> browser_acquire
```

Mac Browser Plane owns the bounded internal route:

```text
C0 system curl
  -> bounded curl_cffi retry when C0 evidence permits
  -> conservative content classification
  -> at most one ephemeral C1 render when render evidence requires it
       -> Lightpanda
       -> safe Chrome fallback under existing C1 policy
```

## Production source scope

v1.7 changes only the normal HTML acquisition policy for:

- `S27` Ministry of Border Affairs tender source;
- `S38` Ministry of Industry tender source.

Both move from source policy version 1 to version 2. Their normal provider capability becomes `PUBLIC_READ_ACQUIRE`. `C0_FETCH` remains authorized for bounded diagnostic/backward-compatible use, but is no longer the normal source acquisition choice.

Historical R3 evidence-only and manual-provider-v0 contracts remain unchanged.

## Security boundary

`PUBLIC_READ_ACQUIRE` does not authorize generic Browser escalation. The Provider request must already be approved by the existing source/target/URL/size/time PIC controls, and the Mac Provider Agent independently validates the Router result.

The Mac side fails closed unless:

- acquisition policy is `public_read_auto_v1`;
- selected capability is exactly `C0_FETCH` or `C1_RENDER`;
- Router reports `c2_authorized=false`;
- Router reports `c3_authorized=false`.

Plain auth/rate-limit/network/certificate errors remain non-triggers for C1 under the Acquisition Router contract.

## Runtime budget

The Provider's `max_run_seconds` remains the total remote client budget. Internal C0/C1 stages are bounded by the remaining budget; the composite route does not receive two independent full runtime windows.

## Evidence contract

SignalForge continues to receive one integrity-checked binary artifact through the existing Provider result wire contract:

- selected C0 -> raw HTTP response artifact;
- selected C1 -> complete persisted `rendered.html` artifact.

Lightpanda C1 now persists the same full rendered HTML artifact class required for Provider reuse, so the Bangkok parser does not depend on a bounded `text_excerpt`.

The Provider result wire schema is intentionally unchanged. The manifest still identifies `mcp_tool=browser_acquire` and the Browser job ID. Detailed selected-route evidence remains in Browser Plane's job evidence and is validated on Mac before result submission.

## Non-goals

- no new arbitrary URL authority;
- no proxy/regional egress;
- no C2/C3 authorization through this composite capability;
- no engine selector in the Provider request;
- no change to Artifact OCR authorization;
- no change to manual-provider-v0 or historical R3 evidence-only behavior.

## Verification gates

Before production rollout:

1. Mac Browser Plane full regression must pass;
2. SignalForge full regression must pass;
3. both GitHub PR CI runs must pass;
4. production Provider queue must be drained/idle before source policy v1 -> v2 cutover;
5. old Mac provider contract must be backed up;
6. Mac runtime, Bangkok code/registry, and Mac installed PIC must be switched as one coordinated maintenance action;
7. end-to-end S27/S38 provider smoke must return valid HTML without customer delivery;
8. final Browser Plane Doctor and SignalForge health checks must pass.

## Production closure

Production rollout and live evidence are recorded in `docs/verification/PUBLIC-READ-ACQUIRE-PRODUCTION-CLOSURE-2026-09-30.md`.
