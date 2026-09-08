# PIC-v1 R1D — C3 Retry Safety + Final URL Policy

**Date:** 2026-09-08  
**Status:** FEATURE IMPLEMENTATION / LOCAL TEST PASS

## C3 lease recovery

C0/C1/C2 remain read-only and may be reclaimed after a claim lease expires while the ProviderRequest is still valid. C3 is different:

```text
C3 retry_safe=true
-> expired claim may requeue

C3 retry_safe=false
-> request FAILED
-> failure_class = PROVIDER_LEASE_EXPIRED_NO_RETRY
-> no automatic replay
```

This prevents ambiguous partial Browser interaction from being repeated merely because the transport lease expired.

## C3 action alignment

PIC v1.1 now uses the subset that the real Mac MCP actually exposes and that remains inside the Provider read-only-navigation boundary:

```text
snapshot
navigate
click
wait
type
select
press
screenshot
```

`scroll` is removed because it is not a current MCP Browser Use action. `download` remains outside PIC v1.1 even though the local MCP supports it, because provider-download artifact/side-effect semantics are not yet defined.

## Final URL policy

ProviderRequest now freezes a machine-verifiable `final_url_policy` inside the request SHA. Default behavior remains:

```text
EXACT_REQUESTED
```

A source target can explicitly authorize:

```text
APPROVED_HOST_PATH
https_host=<exact issuer host>
path_prefix=<bounded prefix>
allow_query=<bool>
allow_fragment=<bool>
```

This enables legitimate C1/C2/C3 same-issuer navigation without weakening result validation to arbitrary redirects. Bangkok validates the returned final URL against the policy embedded in the hashed request.

## Verification

Targeted provider tests cover non-retry-safe C3 failure, retry-safe C3 reclaim, action alignment, exact final URL and bounded host/path final URL.
