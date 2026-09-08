# PIC v1 R3 Isolated Live Verification — PASS

Date (Asia/Yangon): 2026-09-08
Status: R3 LIVE PASS / R4 NOT ENABLED

## Scope

This gate verified the real Bangkok-origin Provider Invocation Contract path for all four approved Mac Browser Plane capability classes without enabling provider-backed production or any S38 business-output path.

Target: `https://www.industrymsme.gov.mm/announcements`

```text
S38 verification-only
BKK ProviderRequest durable queue
-> dedicated Mac->BKK restricted SSH claim
-> Mac Provider Agent
-> local mac-browser-mcp stdio
-> existing Browser Plane worker / C0+C1+C2+C3
-> restricted SSH submit
-> BKK durable provider evidence
```

## Exact software / deployment state

- Bangkok SignalForge application release: `aafa4195d2b747226a379e668911f7f686287c78`.
- Previous rollback release: `d12d70d39794af32e67725700f344f8b50248bb0`.
- R3 harness and provider queue are inherited from merged PIC baseline `443e0f456a2320468527ac48160b6f69f8e24814`.
- Mac Browser Plane Provider Agent was the already-installed merged R2 runtime.
- Production flags remained frozen: `browser_production_approved=false`; the R3 contract itself remained `enabled=false` / evidence-only.

## Dedicated provider SSH identity

A new unattended provider credential was created instead of reusing an administrative/root key.

```text
BKK Unix user: signalforge-provider
key type: Ed25519
public-key fingerprint: SHA256:0m4dyyxo63gHlh5H4HbCDNEPPU2FQIUIGR1DinKnfJQ
private key location: Mac-only; not stored on BKK or GitHub
```

The BKK `authorized_keys` entry uses `restrict,no-user-rc,command=...`; the forced wrapper accepts only `provider-claim-v1`, `provider-submit-v1`, `provider-fail-v1`, and `provider-status-v1`. The wrapper can sudo only those four exact dispatcher forms to the existing `signalforge` process identity. No root shell, PTY, forwarding, SFTP, arbitrary command, Worker verb, or systemctl authority is granted.

Negative test: attempting `id` through the provider key returned `126 / DENY: unsupported provider command`.

## S25 recovery before R3

The MONPIFER Drupal path regression was deployed before R3. A real S25 refresh then succeeded with `items=10`, `tenders=10`, and `consecutive_failures=0`. Source health remains temporarily RED only because its rolling parse-health window still contains prior failures; no artificial refresh loop was used to manufacture GREEN.

The recovery refresh emitted 10 `UPDATED` signals because issuer transport metadata changed with the `/index.php/` path shape. Those records are retained for review; no destructive DB cleanup was performed in this gate.

## R3 gate

Gate ID: `26ece5bb-fe15-47ae-a6b0-a7b4882d778f`

Exactly four ProviderRequests were prepared with a 180-second TTL. They were claimed from the durable queue and completed through the real Mac provider path:

| Capability | ProviderRequest | Browser job | Artifact | Media | Verified |
|---|---|---|---:|---|---|
| C0_FETCH | `051346cd-cdf2-4be3-88aa-c78ccfe1804f` | `7920dfc6-06f8-4601-9723-af3a161479d4` | 88,628 B | `text/html` | yes |
| C1_RENDER | `70871b3d-1f8d-4c35-ab93-b3c28938955d` | `6521de2d-a088-4a5e-8001-f287938954ad` | 9,257 B | `application/json` | yes |
| C2_INSPECT | `21d8465d-16ea-49e7-9c31-e78a710d3c9d` | `2db1e1f3-df54-4753-8fe7-cb3f9e5f7363` | 18,925 B | `application/json` | yes |
| C3_BROWSER_USE | `45db4a0b-4e6e-440b-baf3-c4401a2fb69d` | `3f261dba-5db9-4912-82d1-7fe604631ca9` | 35,368 B | `application/json` | yes |

Final BKK gate result: `PASS`; every request state is `SUCCEEDED`, every artifact/final-URL/correlation check is verified, and provider queue status is `SUCCEEDED=4` with PENDING/CLAIMED/FAILED/EXPIRED/CANCELLED all zero.

## Business isolation

R3 status verified for S38:

```text
scheduler_runs = 0
canonical_items = 0
signals = 0
```

No Source Registry production activation, parser, canonicalizer, dedup, customer signal, review, or delivery path ran for S38.

## Mac and rollback verification

Post-gate `browserctl doctor` returned `READY`; SQLite integrity/WAL/ownership and Chrome/Playwright checks all passed.

The provider credential disable path was live-tested by temporarily disabling its `authorized_keys` file: the provider key immediately failed authentication while the independent admin channel remained available. Restoring mode `0600` restored provider status access with the same `SUCCEEDED=4` durable queue state.

## Decision

**PIC v1 R3 = PASS.**

R4 provider production enablement is now technically unblocked by R3, but it is not performed by this gate. Production provider/browser flags remain false until the separately reviewed R4 slice deliberately changes them.
