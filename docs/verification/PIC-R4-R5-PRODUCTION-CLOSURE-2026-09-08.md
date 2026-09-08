# PIC v1 R4/R5 Production Closure — 2026-09-08

## Decision

**R4 Provider Production Enable = COMPLETE / PASS.**

**R5 First Provider-backed Source (S38 Ministry of Industry) = PRODUCTION / GREEN.**

This closure does not authorize generic Browser fallback. S38 is explicitly routed to `mac-mm-01` and production authorization remains limited to `C0_FETCH` for the exact Ministry of Industry listing and issuer-local `/announcements/<id>` detail URLs. C1/C2/C3 remain R3-verified platform capabilities but are not authorized for S38 production.

## Final production topology

```text
Bangkok SignalForge scheduler
  -> S38 source policy: engine=provider / mac-mm-01 / C0_FETCH
  -> Bangkok durable ProviderRequest
  -> Mac launchd Provider Agent outbound restricted SSH pull
  -> local mac-browser-mcp stdio
  -> Browser Plane C0 fetch
  -> restricted SSH result submit
  -> Bangkok durable EvidenceEnvelope
  -> existing parser / canonical / signal pipeline
```

The Mac opens no Browser/MCP/CDP production listener. The Provider Agent uses the dedicated `signalforge-provider` restricted identity and not an administrative SSH identity.

## Git / release chain

Mac Browser Plane:

- R4 production enable PR #30 -> `f5072ac4f0cf180282f8af9bdd20d7ff9d49d5b1`;
- backlog-drain production regression PR #31 -> `7a13bcb1ab8acf0a69585bbddc0a6d88cd56d9ea`;
- installed Mac runtime is built from `7a13bcb1...`.

SignalForge:

- R4/R5 implementation PR #84 -> `f79a9a8884a84ea7d4e5567699afac80b68e2771`;
- fresh ProviderRequest clock fix PR #85 -> `99163412fc7ea74ebba49e3f784030d8a9c0bdab`;
- per-source scheduler failure isolation PR #86 -> `63cefb36839058cf793cd1a198b00a364925bf70`;
- S38 business-processing health sampling PR #87 -> `1d88b54d22f43e818a055a5c605a14c728816aad`;
- final Bangkok active application release is `1d88b54d...`;
- immediate application rollback target at final deploy was `63cefb36...`.

## Live rollout findings and fixes

### 1. Initial baseline proved the real cross-host path but exposed TTL aging

The first reviewed production S38 baseline traversed the real Bangkok -> Mac -> Bangkok path and kept `signals_created=0`, but only partially completed:

```text
discovered          = 16
details_attempted   = 16
details_succeeded   = 4
changed             = 4
signals_created     = 0
backlog_remaining   = 10
```

Root cause: later ProviderRequests reused the scheduler run's fixed `observed_at` as their request clock. Requests created later in the batch therefore inherited an already-aged TTL and expired before claim.

PR #85 changed ProviderRequest creation/TTL to the actual enqueue clock while preserving scheduler `observed_at` for application evidence semantics. Regression coverage explicitly uses a scheduler observed time ten minutes older than the ProviderRequest enqueue time.

### 2. Batch throughput exposed idle-delay amplification

The Mac Provider Agent originally slept the full 10-second idle poll interval after every completed request. This unnecessarily stretched a multi-detail production batch toward the SignalForge systemd timeout.

PR #31 changed the agent to:

```text
NO_WORK   -> sleep configured poll interval
work done -> immediately drain next request
```

Installed-runtime verification:

```text
batch_drain_delay = 0.0
idle_delay        = 10.0
```

After #85 + #31, baseline reconciliation completed in bounded batches with zero detail transport errors:

```text
backlog 10 -> 4   signals_created=0
backlog  4 -> 0   signals_created=0
```

All four remaining baseline items still carried `suppress_signal_once=1` immediately before the final reconciliation batch. Final baseline reconciliation therefore did not turn historical tender records into customer signals.

### 3. Mac-offline isolation was live-verified

The Provider LaunchAgent was deliberately stopped while the Browser Plane itself remained healthy:

```text
Provider Agent = offline
browserctl doctor = READY
```

S38 then failed in a bounded way after its 90-second acquisition timeout:

```text
TimeoutError: provider acquisition timed out: S38 LISTING
```

A concurrent S37 attempt was correctly rejected by the existing Worker application admission guard (`FAILED_RESOURCE_GUARD: application admission 1/1`), proving application-run serialization remained enforced.

After S38 released the application admission slot, S37 was run again while the Provider Agent was still offline and completed:

```text
S37 = SUCCESS
changed = 0
signals_created = 0
```

Therefore Mac Provider unavailability affects the provider source, not Direct HTTP acquisition.

The timed-out ProviderRequest was left untouched until its TTL elapsed. After Provider Agent restoration it was marked `EXPIRED / PROVIDER_REQUEST_EXPIRED`; it was not executed as orphan work.

The deliberate offline gate added one expected historical S38 failed scheduler run. A subsequent unattended S38 run cleared `consecutive_failures` to zero.

### 4. Production scheduler failure isolation was hardened

The first timer-driven post-gate scheduler run exposed an unrelated S29 transient failure:

```text
S29 -> RuntimeError: all bounded detail candidates failed
```

The old `run_due()` propagated that exception immediately, so later sources were starved. PR #86 changed `run_due()` to isolate exceptions per source:

- failed source remains explicitly `FAILED`;
- its error is retained;
- later sources still execute;
- overall run-due remains `FAILED` if any source failed.

Regression coverage requires an S29 exception not to block later S38 execution. Full suite after the change: **198 passed**.

S29 subsequently recovered naturally to `SUCCESS / GREEN` without a source-specific code change.

### 5. S38 parse-health sampling was corrected without brushing data

S38 initially showed RED parse health even after successful provider recovery because `DETAIL_SCHEDULER` treated a successfully parsed detail that intentionally produced zero final tender records as a parse failure.

Production DB inspection showed the latest ten S38 business-processing records were **10/10 SUCCESS**, including legitimate `items_found=0` decisions. PR #87 therefore changes only S38 health sampling to `BUSINESS_PROCESSING`.

This is not a parser/canonical/signal change. Transport failures remain represented by fetch health; actual parser/normalizer failures remain represented by failed processing records.

After deploying #87, S38 health became:

```text
fetch_health          = GREEN
freshness_health      = GREEN
parse_health          = GREEN
parse_success_ratio   = 1.0 (10/10)
recovery_backlog      = 0
source_health         = GREEN
reason_code           = OK
consecutive_failures  = 0
```

No extra source runs were used to manufacture this GREEN state.

## Unattended production proof

After the offline gate, S38 had a normal retry due time. The Provider Agent was restored, then the production systemd timer was re-enabled with `Persistent=true`; no `refresh-source S38` command was issued for recovery.

The timer triggered `signalforge-run-due.service`, which eventually executed S38 through the provider path:

```text
started_at          = 2026-09-08T14:20:54.213550Z
trigger_kind        = POLL
status              = SUCCESS
changed             = 0
signals_created     = 0
backlog_remaining   = 0
error               = null
```

Source state after this unattended run:

```text
last_error            = null
consecutive_failures  = 0
next_due_at            = 2026-09-08T14:50:54.213550Z
```

This is the production proof that S38 automatically uses the Mac Browser Provider without ChatGPT/CodexPro/operator intervention.

## Final production snapshot

Bangkok:

```text
active_release              = 1d88b54d22f43e818a055a5c605a14c728816aad
timer_enabled               = enabled
timer_active                = active
DB quick_check              = ok
canonical_items             = 183
signals                     = 34
historical failed_runs      = 31
S38 canonical_items         = 8
S38 signals                 = 0
S38 pending                 = 0
S38 Provider SUCCEEDED      = 24
S38 Provider FAILED/EXPIRED = 11   # rollout/offline-gate history
S38 EvidenceEnvelopes       = 20
```

Mac:

```text
repo/runtime source SHA = 7a13bcb1ab8acf0a69585bbddc0a6d88cd56d9ea
Provider LaunchAgent     = running
production_enabled       = true
invocation_mode          = pull_ssh_v1
remote_invocation        = true
Provider TCP listeners   = none
Provider stderr tail     = empty
```

## Remaining non-R4/R5 health note

Overall SignalForge status remains `DEGRADED / RED` because **S25** still carries the already-known rolling parse-health history from the MONPIFER `/index.php/` drift incident:

```text
S25 fetch/freshness       = GREEN/GREEN
S25 consecutive_failures  = 0
S25 last_error            = null
S25 parse window          = 6/10 -> RED
```

This is not an R4/R5 regression and must not be artificially washed out by repeated refreshes. It can recover naturally as successful processing replaces historical failures in the rolling window.

## Closed invariants

- Bangkok remains the SignalForge canonical node.
- Existing Direct HTTP sources remain Direct HTTP by explicit source policy.
- There is no generic HTTP-failure -> Browser fallback.
- S38 is the first unattended provider-backed source.
- S38 production uses C0 only.
- C1/C2/C3 remain available platform capabilities but require source-specific production authorization.
- Mac remains pull-only for this remote production path; no Browser/MCP/CDP listener is exposed.
- Provider SSH identity is dedicated, non-root, and forced-command restricted.
- Provider outage is bounded to provider acquisition and does not disable Direct HTTP sources.
- One source failure no longer prevents later due sources from being evaluated.
- First S38 baseline/reconciliation emitted zero customer signals.
