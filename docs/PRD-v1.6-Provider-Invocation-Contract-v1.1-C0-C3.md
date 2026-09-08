# SignalForge PRD v1.6 — Provider Invocation Contract v1.1 (C0+C1+C2+C3)

**Date:** 2026-09-08  
**Status:** FROZEN DESIGN / IMPLEMENTATION AUTHORIZED BY CONTINUATION  
**Provider:** `mac-mm-01`  
**Transport direction:** Mac-initiated pull over restricted SSH  
**Local execution interface:** `mac-browser-mcp` over stdio only

## 1. Decision

Bangkok SignalForge is authorized to invoke all four currently approved Mac Browser Plane capability classes through the Provider Invocation Contract:

```text
C0_FETCH        -> browser_fetch
C1_RENDER       -> browser_render
C2_INSPECT      -> browser_inspect
C3_BROWSER_USE  -> browser_use
```

Provider-level capability does not imply every source can use every capability. Authorization is three-layered:

```text
Provider supports C0+C1+C2+C3
-> Source policy explicitly allowlists capability
-> Each ProviderRequest names exactly one capability and target role
```

No capability may auto-escalate to another capability.

## 2. Meaning of Provider Invocation Contract

`Provider` = execution capability provider. `mac-mm-01` supplies the Mac network/browser environment but does not own SignalForge business truth.

`Invocation` = one explicit execution transaction with its own request/correlation IDs, timeout, evidence and failure state.

`Contract` = machine-verifiable rules covering authorization, URL boundary, lifecycle correlation, idempotency, integrity, retries, offline behavior and rollback.

The phrase therefore means: **the machine contract that governs how SignalForge invokes an execution provider.**

## 3. Architecture

```text
Bangkok SignalForge
  -> durable ProviderRequest
  <- Mac provider agent pulls via restricted outbound SSH
  -> Mac local mac-browser-mcp stdio
  -> existing Browser Plane JobStore / LaunchAgent worker
  <- result + raw artifact
  <- Mac submits through the same restricted SSH identity
  -> Bangkok validates and creates EvidenceEnvelope
  -> existing parser/canonical/dedup/signal lifecycle
```

Logical invocation direction is SignalForge -> Provider. Network connection direction is Mac -> Bangkok.

## 4. Why pull-over-SSH

Selected because it introduces the smallest new attack/operations surface:

- no public Mac HTTP API;
- no public MCP endpoint;
- no public CDP;
- no reverse tunnel;
- no VPN dependency;
- no Bangkok-to-Mac inbound reachability requirement;
- no CodexPro dependency in unattended production.

A dedicated provider SSH identity must be separate from the existing administrative/root key and must be forced-command/no-shell/no-forwarding.

## 5. Ownership invariants

Bangkok remains owner of:

- Source Registry;
- ProviderRequest durable truth;
- AcquisitionRequest/Attempt;
- EvidenceEnvelope/ProcessingRecord;
- Canonical/Dedup/Signal/Review/Delivery.

Mac owns only Browser Plane operational execution state. Mac Browser Job is not a VPS Worker Run.

```text
SignalForge Job != Worker Run != ProviderRequest != ProviderAttempt != Browser Job
```

## 6. Capability contract

### C0_FETCH

Raw strict-TLS acquisition. Read-only. Automatic retry/lease recovery can be permitted under idempotent request semantics.

### C1_RENDER

Deterministic render/read acquisition. Read-only. Same source/URL policy boundaries apply.

### C2_INSPECT

Read-only browser diagnostics/inspection. It must not mutate account/site state.

### C3_BROWSER_USE

Deterministic Browser Use interaction is authorized for unattended SignalForge work when the source policy explicitly permits it.

C3 does **not** authorize an unrestricted autonomous Browser Agent. Each request must carry a bounded interaction plan classified as `READ_ONLY_NAVIGATION`. Permitted plan actions are bounded navigation/inspection operations such as snapshot, navigate, click, wait, type, select, scroll and screenshot. Arbitrary JavaScript, shell, command execution, purchasing, messaging, account changes, destructive actions or external business-state mutation are outside PIC v1.1.

C3 must declare `retry_safe` explicitly. A C3 plan that is not demonstrably retry-safe must not be automatically replayed after ambiguous partial execution.

## 7. ProviderRequest v1

Minimum fields:

```text
contract_version
provider_request_id
provider_id
signalforge_job_id
acquisition_request_id
acquisition_attempt_id
source_id
source_policy_version
capability
mcp_tool
target_role
requested_url
max_bytes
max_run_seconds
requested_at
expires_at
idempotency_key
interaction_plan
request_sha256
```

The request SHA is the SHA-256 of canonical JSON excluding `request_sha256` itself.

## 8. Source authorization

Provider support is global; actual use is source-specific. Each provider-backed source must explicitly declare:

```text
allowed_capabilities
source_policy_version
target roles
exact URLs and/or exact HTTPS host + bounded path prefix
query/fragment policy
max bytes
max run time
```

Arbitrary user/model-provided URL execution is prohibited.

## 9. SSRF and URL boundary

Provider requests are HTTPS-only. Reject:

- credentials in URL;
- non-approved host;
- private/literal arbitrary address;
- path traversal;
- unapproved query/fragment;
- off-host redirect;
- `file:`, `data:`, `javascript:` and equivalent non-HTTPS schemes.

Bangkok validates before enqueue and Mac validates again before local MCP execution.

## 10. Transport and dispatcher

Future R1 introduces a dedicated Mac->Bangkok SSH identity and a forced-command provider dispatcher with only:

```text
provider-claim-v1
provider-submit-v1
provider-fail-v1
provider-status-v1
```

No shell, root, port forwarding, SFTP, arbitrary file read, systemctl or Worker verbs.

## 11. Claim/lease model

ProviderRequest state machine:

```text
PENDING -> CLAIMED -> SUCCEEDED | FAILED | EXPIRED | CANCELLED
CLAIMED --lease expiry/read-only recovery--> PENDING
```

Claim returns a `provider_attempt_id`, high-entropy claim token and lease expiry. Bangkok stores only the claim-token hash. Submit must present the current token.

C0/C1/C2 can use at-least-once execution + exactly-once evidence commit. C3 automatic replay is allowed only when its request explicitly declares a retry-safe read-only plan.

## 12. Evidence/result integrity

Returned result must correlate:

```text
provider_request_id
provider_attempt_id
browser_job_id
request_sha256
requested_url
final_url
HTTP status
media type
artifact byte count
artifact SHA-256
```

Only after validation may Bangkok create an `EvidenceEnvelope` and enter normal source-specific processing.

## 13. Mac offline semantics

Mac offline means provider-backed source acquisition is delayed/degraded. It never means global SignalForge outage. Healthy Bangkok Direct HTTP sources continue normally.

Provider failures are distinct from HTTP/parser failures, including:

```text
PROVIDER_DISABLED
PROVIDER_UNAVAILABLE
PROVIDER_TIMEOUT
PROVIDER_REQUEST_EXPIRED
PROVIDER_POLICY_REJECTED
PROVIDER_CONTRACT_MISMATCH
PROVIDER_LEASE_CONFLICT
PROVIDER_RESULT_INVALID
PROVIDER_ARTIFACT_HASH_MISMATCH
PROVIDER_IDEMPOTENCY_CONFLICT
```

## 14. CodexPro boundary

Cloud ChatGPT -> CodexPro -> local Mac Browser Plane MCP remains an approved engineering/source-audit path. CodexPro is **not** the unattended SignalForge production broker.

Production PIC reuses the same local Browser Plane/MCP runtime but has its own durable request, authorization, correlation, idempotency and evidence lifecycle.

## 15. Rollout

```text
R0 Contract Foundation
  schema/hash/URL/capability/C3-plan validation; zero production behavior change

R1 Bangkok Queue + Restricted SSH Dispatcher
  durable provider request/attempt, atomic claim/lease, submit/import

R2 Mac Provider Agent
  claim -> local MCP stdio -> result -> submit

R3 Isolated Live Verification
  prove BKK-origin C0+C1+C2+C3 end-to-end, initially EVIDENCE_ONLY

R4 Provider Production Enable
  only after R0-R3 PASS; flip provider production/remote flags

R5 First Provider-backed Source
  recommended: Ministry of Industry `industrymsme.gov.mm`
```

PIC cannot be declared complete if only C0 is live-tested. R3 must verify BKK-origin calls through the real provider path to all of C0, C1, C2 and C3.

## 16. Hard stops

STOP if implementation introduces:

- public Mac Browser/MCP/CDP listener;
- reuse of administrative/root SSH key for unattended provider;
- arbitrary URL or arbitrary shell execution;
- automatic HTTP/TLS/parser failure -> Browser escalation without source policy;
- CodexPro as a production dependency;
- Mac outage stopping healthy Direct HTTP sources;
- C3 arbitrary autonomous-agent authority or external write/business side effects.

## 17. Definition of Done

- ProviderRequest v1 contract frozen and machine-validated;
- C0+C1+C2+C3 all represented in provider capability/tool contract;
- double source/URL/capability validation;
- dedicated least-privilege pull-SSH identity;
- claim/lease/idempotency/result integrity implemented;
- Mac Provider Agent uses only local `mac-browser-mcp` stdio;
- BKK-origin C0/C1/C2/C3 isolated live PASS;
- Mac offline isolation PASS;
- no public Browser/MCP/CDP endpoint;
- first provider-backed source baseline produces zero customer signals;
- Bangkok/Beijing Worker invariants remain unchanged;
- rollback/disable path live verified.
