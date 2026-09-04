# SignalForge PRD v1.5 — Acquisition Policy & Local Contract Foundation

**项目：** SignalForge / VPS Worker Runtime  
**版本：** v1.5  
**日期：** 2026-09-03  
**状态：** Architecture Frozen / Engineering Implementation Freeze  
**前置基线：** `v1.4.5 Current Authorized Production Scope = COMPLETE / PASS`  
**主题：** **Acquisition Policy & Local Contract Foundation**  
**核心原则：** **Preserve the proven production system; refactor the inside, preserve the outside.**

> **Integration supersession notice (2026-09-04):** Browser / Playwright / Crawlee / Mac Provider 相关未来条款已由 `PRD-v1.5.1-Mac-Browser-Plane-Integration-Amendment.md` 覆盖。v1.5 的 local acquisition、Bangkok-only SignalForge、R0–R2 Direct HTTP、Gate Z cardinality 等已验证生产基线保持不变；旧 VPS Browser/Crawlee R3 不再是等待触发的未来路径，而是 `SUPERSEDED_BY_MAC_BROWSER_PLANE`。后续开发必须同时读取 v1.5.1。

---

# 0. Revision Decision

## 0.1 本轮意见是否采纳

**结论：采纳。**

本版正式撤回上一版将 v1.5 定义为 `Acquisition Policy & Federated Provider Contract` 的过早抽象，更新为：

> **SignalForge v1.5 — Acquisition Policy & Local Contract Foundation**

原因：

1. v1.4.5 已完成真实 Production / Live Verification / Cross-Repo Contract Closure；
2. Bangkok + Direct HTTP + systemd + SignalForge 已证明可以稳定生产运行；
3. 当前没有真实的 SignalForge → Beijing remote acquisition；
4. 当前没有真实的 SignalForge → Mac production acquisition；
5. 当前没有 remote Provider transport / artifact handoff / provider failover 的生产需求；
6. 因此 v1.5 不应为了未来 federation 提前冻结尚未被真实 workload 验证的 Provider ABI；
7. v1.5 当前最大风险不是能力不足，而是为了新抽象破坏已经验证过的 boring production system。

## 0.2 本轮重大变化

```text
v1.4.5
Production Closure ✅
      │
      │ preserve all validated invariants
      ▼
v1.5
Local Acquisition Contract Foundation
      │
      ├─ Source Acquisition Policy
      ├─ AcquisitionRequest
      ├─ AcquisitionAttempt
      ├─ EvidenceEnvelope
      ├─ ProcessingRecord
      └─ S13 compatibility validation
      │
      ▼
More Myanmar Sources
      │
      ▼
Observe real friction
      │
      ├─ JS actually required → Mac Browser Provider requirement (production disabled until separate contract)
      ├─ Browser execution → Mac Browser Plane only
      ├─ China acquisition required → Beijing Remote Provider ADR
      └─ shared browser pain → Browserless ADR
```

---

# 1. Executive Summary

v1.5 不重新建设 SignalForge，也不重新设计 Worker Runtime。

它是一个**向后兼容的 SignalForge 内部 acquisition lifecycle 重构**。

v1.5 的目标不是 `create a distributed acquisition platform`，而是：

```text
make acquisition behavior explicit,
versioned,
testable,
failure-aware,
and reusable across future Myanmar sources
```

当前 production path 仍然是：

```text
Bangkok
+ SignalForge
+ Direct HTTP
+ systemd timer
```

并继续保持：

```text
one signalforge scheduler invocation
→ one Worker operational Run
→ one SignalForge scheduler_run
→ N SignalForge business jobs
```

v1.5 **不得改变这个 cardinality**。

---

# 2. v1.4.5 Is the Frozen Production Baseline

## 2.1 Baseline Status

v1.4.5 当前授权生产范围正式视为：

> **COMPLETE / PASS**

```text
R0 Shared Worker Foundation       PASS
R1 Generic Direct HTTP Runtime    PASS
R2 Scheduling / Operations        PASS
R4 Remote Control / Fleet         PASS
R5 Bangkok SignalForge            PASS
```

条件 Gate：

```text
R3 VPS Browser/Crawlee — SUPERSEDED_BY_MAC_BROWSER_PLANE
R6 Webhook
Gate V Dedicated Identity Retirement
```

其中 R6 / Gate V 仍为 `NOT TRIGGERED`；R3 VPS Browser/Crawlee 不再等待触发，状态正式变为 `SUPERSEDED_BY_MAC_BROWSER_PLANE`。

## 2.2 Rollback Reference

v1.4.5 必须被视为：

```text
Production Baseline
+
Frozen Invariants
+
Known-good Rollback Target
```

v1.5 是：

```text
v1.4.5
+
backward-compatible internal acquisition extension
```

---

# 3. Frozen Invariants

## I-01 — Bangkok-only SignalForge

```text
SignalForge production → Bangkok only
Beijing → Generic Worker only / NO SignalForge
```

## I-02 — Single Scheduler Invocation Boundary

```text
signalforge-run-due.service
        ↓
one Worker operational Run
        ↓
one SignalForge scheduler_run
        ↓
N SignalForge business jobs
```

禁止 `one business job → one Generic worker@ service`。

## I-03 — AcquisitionRequest != Worker Run

```text
AcquisitionRequest != Worker Run
AcquisitionAttempt != Worker Run
```

当前 Bangkok local path 中，Request / Attempt 只是 SignalForge internal acquisition lifecycle。

## I-04 — Business State Remains SignalForge-owned

SignalForge 继续拥有：

```text
source_id
business job
acquisition request
acquisition attempt
parser state
canonical identity
business retry
dedup
signal
review
delivery
```

Worker Runtime 只拥有 process execution envelope / operational run / resource / timeout / identity / operational health。

## I-05 — Worker DB Has No SignalForge Business Semantics

Worker operational DB 不增加 source/acquisition/canonical 业务字段。

## I-06 — Direct HTTP Remains Default

`Direct HTTP = default production acquisition method`。

## I-07 — No Silent Engine Escalation

```text
HTTP failure
→ classify
→ Source Acquisition Policy
→ explicit resolution
```

禁止自动 Browser fallback。

## I-08 — TLS Failure Does Not Become Browser Success

```text
TLS_FAILURE != Browser escalation
```

禁止 production 使用 `verify=False` / `curl -k` / certificate bypass。

## I-09 — No New Distributed Runtime

v1.5 不引入 Redis / Celery / central queue / central scheduler / service discovery / cross-worker task stealing / dynamic distributed lease runtime。

## I-10 — No Automatic Cross-zone Failover

禁止 `Bangkok unavailable → automatically Beijing`。

## I-11 — Mac Browser Plane Is Not an Unattended SignalForge Production Dependency

Mac mini 是 sole Browser Runtime host，但 SignalForge→Mac Browser Provider 当前保持 `production_enabled=false`。继续要求 `Mac offline != SignalForge production stops`；健康的 Bangkok Direct HTTP sources 不得因 Mac 离线而停止。

## I-12 — Browserless Is Not a Base Dependency

Browserless 保留为 Future ADR。

---

# 4. Goals

v1.5 只解决五件核心事情：

1. **Source Acquisition Policy**：显式冻结 source 怎么抓；
2. **AcquisitionRequest + AcquisitionAttempt**：显式表达逻辑 acquisition 与 bounded attempts；
3. **Acquisition-only EvidenceEnvelope**：只描述实际获取到的 acquisition fact；
4. **SignalForge ProcessingRecord**：描述 evidence 如何被解析/规范化/进入 canonical；
5. **S13 Behavior-preserving Compatibility Reference**：证明内部重构不改变现有生产行为。

---

# 5. Non-Goals

v1.5 明确不做：

- Remote Provider transport；
- SignalForge → Beijing remote acquisition；
- SignalForge → Mac production acquisition；
- Singapore / Tokyo provider；
- Provider synchronization；
- Provider failover；
- remote artifact handoff protocol；
- Source Policy Projection deployment；
- Browserless deployment；
- public Worker / Browser API；
- residential proxy；
- CAPTCHA infrastructure；
- stealth browser stack；
- distributed queue；
- PostgreSQL lease queue；
- SignalForge Beijing replica；
- central business DB；
- Redis/Celery；
- auto cross-zone failover；
- speculative Webhook ingress。

以上均属于 Future ADR / Future Capability Gate。

---

# 6. Existing Architecture Preserved

```text
vps-control-plane → SSH / root / privileged command boundary
vps-worker-plane  → controlled Generic execution / operational runtime
SignalForge       → Myanmar source / acquisition / evidence / canonical / signal
```

---

# 7. New v1.5 Internal Architecture

```text
                         systemd
                            │
                            ▼
                 signalforge-run-due.service
                            │
                            ▼
                 Worker Application Run
                            │
                            ▼
                 SignalForge scheduler_run
                            │
               ┌────────────┼────────────┐
               │            │            │
               ▼            ▼            ▼
          business A    business B    business N
               │
               ▼
       Source Acquisition Policy
               │
               ▼
       AcquisitionRequest
               │
               ▼
       AcquisitionAttempt
               │
               ▼
       Local Acquisition Adapter
               │
               ▼
        EvidenceEnvelope
               │
               ▼
        ProcessingRecord
               │
               ▼
      Canonical / Dedup / Signal
```

新 contract lives inside SignalForge，不是新的 Worker Runtime。

---

# 8. Source Acquisition Policy

## 8.1 Policy Structure

不使用混杂的 `DIRECT_THEN_BROWSER / HTML_PLUS_PDF` 大 enum，改为结构化 transition policy：

```yaml
source_id: S13
source_policy_version: 8

egress_profile: mm-intl-datacenter

acquisition_policy:
  enabled: true

  primary:
    method: DIRECT_HTTP
    target_kind: HTML

  supplementary: []

  escalation:
    DNS_FAILURE:
      action: RETRY
    CONNECT_TIMEOUT:
      action: RETRY
    HTTP_429:
      action: RETRY
    HTTP_403:
      action: REVIEW
    TLS_FAILURE:
      action: FAIL
    JS_RENDER_REQUIRED:
      action: REVIEW_CAPABILITY
    PARSER_DRIFT:
      action: REAUDIT
```

`egress_profile` 本版只是 source acquisition requirement metadata；当前 deterministic mapping 仍为 `mm-intl-datacenter → Bangkok`。v1.5 不实现 Provider Registry 或 dynamic provider resolution。

---

# 9. AcquisitionRequest v1

`AcquisitionRequest` 表示 SignalForge 决定需要对某个 allowlisted Source 执行一次逻辑 acquisition；它不是 process execution。

```yaml
schema_version: 1
request_id: <uuid>
scheduler_run_id: <signalforge-scheduler-run-id>
app_job_ref: <opaque-signalforge-job-ref>
source_id: S13
source_policy_version: 8
mode: production
reason: SCHEDULED
egress_profile: mm-intl-datacenter
requested_at: 2026-09-03T00:00:00Z
policy:
  primary_method: DIRECT_HTTP
  target_kind: HTML
  timeout_seconds: 30
expected:
  content_types:
    - text/html
```

允许的 reason：

```text
SCHEDULED
MANUAL
RECONCILIATION
HEALTH_PROBE
DIAGNOSTIC
```

Production request 不接受 arbitrary shell / executable / systemd unit / worker selection / arbitrary public URL supplied by remote caller。URL 继续由 SignalForge allowlisted Source Registry / source implementation决定。

---

# 10. AcquisitionAttempt v1

一个 logical request 可以有多个 bounded attempts，因此 `Request != Attempt`。

```yaml
schema_version: 1
attempt_id: <uuid>
request_id: <uuid>
attempt_number: 1
source_id: S13
source_policy_version: 8
method: DIRECT_HTTP
egress_profile: mm-intl-datacenter
started_at: ...
finished_at: ...
outcome:
  status: SUCCESS
  acquisition_failure_class: null
```

v1.5 不引入第二套 distributed retry system；禁止多个层同时自动 retry 同一 failure。

---

# 11. EvidenceEnvelope v1

`EvidenceEnvelope` 只描述 acquisition fact，不描述 business interpretation。

```yaml
schema_version: 1
evidence_id: <uuid>
request_id: <uuid>
attempt_id: <uuid>
scheduler_run_id: <signalforge-scheduler-run-id>
app_job_ref: <opaque>
source_id: S13
source_policy_version: 8
provider:
  execution_scope: LOCAL_BANGKOK
  provider_id: bkk-local
  provider_baseline_version: 1
egress_profile: mm-intl-datacenter
fetch_method: DIRECT_HTTP
started_at: ...
fetched_at: ...
requested_url: ...
final_url: ...
http:
  status: 200
  media_type: text/html
  content_length: 12345
artifact:
  artifact_id: ...
  sha256: ...
  bytes: 12345
  media_type: text/html
acquisition_failure_class: null
```

EvidenceEnvelope 禁止包含 parser_version / canonical_id / signal_id / customer classification / review status / business priority。

---

# 12. ProcessingRecord v1

由 SignalForge 拥有，表示 Evidence 如何被解释为业务事实。

```yaml
schema_version: 1
processing_id: <uuid>
evidence_id: <uuid>
request_id: <uuid>
attempt_id: <uuid>
source_id: S13
parser_version: mpt-v3
normalizer_version: mpt-normalize-v1
canonicalizer_version: tender-canonical-v1
started_at: ...
finished_at: ...
parse:
  status: SUCCESS
  processing_failure_class: null
result:
  items_found: 1
  canonical_items: 1
  signals_created: 0
```

---

# 13. Failure Taxonomy

## 13.1 AcquisitionFailure

```text
DNS_FAILURE
TLS_FAILURE
CONNECT_TIMEOUT
HTTP_403
HTTP_404
HTTP_429
HTTP_5XX
AUTH_REQUIRED
BOT_BLOCKED
JS_RENDER_REQUIRED
CONTENT_EMPTY
CONTENT_TYPE_MISMATCH
CONTENT_VALIDATION_FAILURE
TRANSPORT_UNKNOWN
```

## 13.2 ProcessingFailure

```text
HTML_PARSE_FAILURE
PDF_PARSE_FAILURE
PARSER_DRIFT
NORMALIZATION_FAILURE
CANONICAL_VALIDATION_FAILURE
PROCESSING_UNKNOWN
```

---

# 14. Failure-aware Resolution

生产决策由 Source Acquisition Policy 决定：

```text
DNS_FAILURE      → bounded retry
HTTP_429         → bounded retry / Retry-After
HTTP_403         → review
TLS_FAILURE      → fail / audit; never certificate bypass; never automatic Browser
JS_RENDER_REQUIRED → source capability review; Browser execution may only target Mac Browser Plane, and stays blocked while Mac Provider is production-disabled
PARSER_DRIFT     → processing re-audit; not Browser
```

---

# 15. Browser Policy

v1.5 P0 不实现新的 Browser production capability。

只有 `real source + fixture evidence + Direct HTTP insufficient specifically because JS rendering is required` 才能确认 Browser requirement。

一旦 Browser requirement 被真实证据确认，执行 host 只能是 **Mac Browser Plane**；不得再进入 Bangkok/Beijing Direct Playwright/Crawlee benchmark/soak 路径。当前 Mac Browser Provider 对 SignalForge 保持 `production_enabled=false`，因此 Browser-required source 必须 blocked/unsupported，直到独立 Provider Invocation Contract 设计、评审、实现并 live-verify。

Browserless 只有在 Mac Browser Plane 出现 multiple real browser consumers / duplicated lifecycle / remote sessions / queueing/orphan operational pain 等真实 friction 后才启动 Future ADR；不得把 Browserless 当作跨主机调用捷径。

---

# 16. Mac mini Role

Mac mini 现正式定义为 **sole Browser Runtime host**；Browser Plane 承担 Playwright / Chrome / Browser Use / Chrome DevTools MCP / Browser profiles / session leases / browser evidence / resource governor。

当前用途：source audit / network comparison / residential egress test / interactive debugging / browser investigation / OpenClaw/Hermes local tasks。

Mac Browser Plane 不拥有 SignalForge Source Registry / DB / Canonical / Signal / Review / Delivery。Mac Browser Provider 对 SignalForge 当前仍为 `production_enabled=false`，且 Mac 不进入 v1.5 unattended production dependency graph。

---

# 17. Health Compatibility

v1.5 不重新造第二套 source-health model。

继续保留当前 production fields：

```text
fetch_health
freshness_health
parse_health
recovery_backlog_health
source_health
reason_code
```

内部可增加 acquisition observability：

```text
acquisition_requests
acquisition_attempts
acquisition_successes
acquisition_failures_by_class
average_acquisition_duration
processing_attempts
processing_successes
processing_failures_by_class
```

---

# 18. Evidence Authority Is Independent from Fetch Method

Authority：

```text
ISSUER_ORIGINAL
OFFICIAL_MIRROR
TRUSTED_PORTAL
THIRD_PARTY
TRIGGER_ONLY
```

Representation：

```text
RAW_HTTP
API_RESPONSE
PDF
RENDERED_DOM
SCREENSHOT
WEBHOOK_PAYLOAD
```

Browser 不自动提高或降低 evidence authority。

---

# 19. Database / Persistence

v1.5 在 SignalForge DB 做 additive schema extension，可新增等价结构：

```text
acquisition_requests
acquisition_attempts
evidence_envelopes
processing_records
```

要求：

- additive migration；
- existing canonical/evidence/signal state preserved；
- migration quick_check；
- no destructive rewrite；
- no Worker DB schema change for SignalForge acquisition semantics。

---

# 20. S13 = Compatibility Reference, Not Migration

不称 `Migrate S13 to new architecture`，而称：

> **S13 behavior-preserving compatibility implementation**

必须证明 `Before v1.5 == After v1.5`，包括：

```text
same timer behavior
same source_id
same Gate Z cardinality
same Worker application-run cardinality
same canonical identity
same baseline suppression
same meaningful-change behavior
same signal behavior
same source health semantics
same manual refresh behavior
same recovery behavior
same Fleet behavior
```

---

# 21. Gate AB — v1.4.5 Production Compatibility [MANDATORY]

这是 v1.5 最重要的新 Gate。

## AB-1 Gate Z unchanged

```text
one signalforge scheduler invocation
→ exactly one Worker operational Run
N business jobs
→ remain internal SignalForge jobs
```

## AB-2 Gate AA unchanged

verb_manifest compatibility / closed SignalForge verbs / unregistered verb denial保持不变。

## AB-3 Placement unchanged

```text
Bangkok → SignalForge ENABLED
Beijing → SignalForge DISABLED / zero application footprint
```

## AB-4 Timer unchanged

`signalforge-run-due.timer` 继续作为同一 systemd reliability backbone。

## AB-5 S13 business behavior unchanged

source_id / canonical identity / baseline suppression / meaningful-change output / duplicate-signal behavior保持一致。

## AB-6 Manual Refresh unchanged

`signalforge-refresh S13` 继续走 approved systemd boundary + MANUAL provenance + one Worker application Run；invalid source在业务执行前 DENY。

## AB-7 Recovery unchanged

Gate S semantics保持 bounded recovery / no crawl-all storm / canonical dedup / visible backlog / RTO-SLO behavior。

## AB-8 Fleet unchanged

```text
Bangkok: Worker PASS / SignalForge ENABLED / GREEN
Beijing: Worker PASS / SignalForge DISABLED
```

## AB-9 Business-state preservation

升级前后验证 canonical row count / signal row count / evidence integrity / schema quick_check，无非预期变化。

---

# 22. Implementation Scope — P0 Only

v1.5 P0 只做：

1. Source Acquisition Policy；
2. AcquisitionRequest v1；
3. AcquisitionAttempt v1；
4. acquisition-only EvidenceEnvelope v1；
5. SignalForge-owned ProcessingRecord v1；
6. AcquisitionFailure / ProcessingFailure split；
7. S13 compatibility implementation；
8. Gate AB zero-regression proof。

---

# 23. P1 — After P0, Still Local

P0稳定后才考虑：

- more Myanmar Sources using the same local contract；
- PDF supplementary evidence adapter if a real source requires it；
- API adapter if a real source requires it；
- richer source acquisition metrics；
- source-level policy re-audit tooling。

仍不引入 remote provider。

---

# 24. Future ADR — Remote Acquisition Provider

只有出现真实需求时才设计 Provider Registry ownership / Provider capability / Source Policy Projection / SSRF validation / remote transport / artifact transfer / remote correlation / provider Worker Run / failover / provider health。

---

# 25. Future ADR — Mac Production Provider

旧的 generic “Mac production acquisition provider” 方向由 v1.5.1 收敛为 **Mac Browser Provider**。只有真实 Browser-required source 出现后，才允许单独设计 Provider Invocation Contract；必须覆盖 authentication / source allowlist / SSRF boundary / timeout / idempotency / evidence return / correlation / Mac offline semantics / no public CDP / no arbitrary URL or command injection。当前不得预建。

---

# 26. Future ADR — Browser Capability

触发：`real source + Direct HTTP insufficient + JS_RENDER_REQUIRED`。确认 Browser requirement 后仅允许指向 **Mac Browser Plane**；VPS Browser/Crawlee R3 已 superseded。若 Mac Browser Provider 仍 `production_enabled=false`，source 必须保持 capability-blocked，不能自动降级为 Bangkok/Beijing Browser。

---

# 27. Future ADR — Browserless

只有 `multiple real browser consumers + shared lifecycle/queue/remote-session pain` 才评估，并执行独立 License Review。

---

# 28. Future ADR — Distributed Queue

只有 sustained scheduling contention / queue wait / cross-worker coordination / DAG / measurable SQLite bottleneck / real automatic Generic failover need 才评估。即使未来引入，Queue 也只是 execution coordination，不能成为 business source of truth。

---

# 29. Release Plan

## v1.5-A — Contract Schema

实现 Source Acquisition Policy / Request / Attempt / EvidenceEnvelope / ProcessingRecord / failure taxonomy，仅在 tests / fixture / isolated DB 验证。

## v1.5-B — S13 Compatibility Refactor

使用现有 S13 MPT Direct HTTP 接入新 internal contract。

## v1.5-C — Zero Regression Gate

执行 Gate AB；只有 PASS 才允许 production deploy。

## v1.5-D — Observe

上线后收集真实 production history，不立即开始 remote provider。

---

# 30. Implementation Order

```text
1. Freeze v1.5 PRD
2. Snapshot v1.4.5 production baseline metrics
3. Add additive SignalForge DB schema
4. Define Source Acquisition Policy schema
5. Define AcquisitionRequest
6. Define AcquisitionAttempt
7. Define EvidenceEnvelope
8. Define ProcessingRecord
9. Split failure taxonomy
10. Add local Direct HTTP adapter contract
11. Adapt S13 without behavior change
12. Run fixture regression
13. Run production DB clone migration
14. Deploy exact SHA Bangkok-only
15. Run Gate AB
16. Observe production
17. Start Source Expansion
```

---

# 31. Required Tests

Unit：Source Acquisition Policy validation / invalid failure-action combination / Request schema / Attempt cardinality / EvidenceEnvelope schema / ProcessingRecord schema / failure enums。

Fixture：S13 known tender / non-tender / baseline / unchanged / changed / parser drift / HTTP error classification。

DB：additive migration / canonical unchanged / signal unchanged / quick_check / rollback compatibility where supported。

Integration：

```text
scheduler_run
→ request
→ attempt
→ evidence
→ processing
→ canonical
```

同时保持 one Worker Run。

---

# 32. Architecture DoD

- [ ] v1.4.5 formally documented as frozen production baseline.
- [ ] SignalForge remains Bangkok-only.
- [ ] Beijing remains SignalForge-free.
- [ ] `signalforge-run-due.service` behavior unchanged.
- [ ] One scheduler invocation still creates exactly one Worker operational Run.
- [ ] N business Jobs remain internal SignalForge Jobs.
- [ ] `AcquisitionRequest != Worker Run`.
- [ ] `AcquisitionAttempt != Worker Run`.
- [ ] Source Acquisition Policy schema defined.
- [ ] AcquisitionRequest v1 defined.
- [ ] AcquisitionAttempt v1 defined.
- [ ] EvidenceEnvelope v1 contains acquisition facts only.
- [ ] ProcessingRecord v1 is SignalForge-owned.
- [ ] AcquisitionFailure / ProcessingFailure separate.
- [ ] Direct HTTP remains default.
- [ ] Browser is not automatic fallback.
- [ ] TLS failure never auto-escalates to Browser.
- [ ] Mac is the sole Browser Runtime host, while SignalForge→Mac unattended production invocation remains disabled.
- [ ] VPS Browser/Crawlee R3 is `SUPERSEDED_BY_MAC_BROWSER_PLANE`.
- [ ] Browser-required sources remain blocked while Mac Browser Provider is `production_enabled=false`.
- [ ] Browserless remains Future ADR.
- [ ] No Provider Registry implementation introduced.
- [ ] No remote Provider transport introduced.
- [ ] No Redis/Celery/central scheduler introduced.
- [ ] S13 behavior before/after equivalent.
- [ ] Gate Z remains PASS.
- [ ] Gate AA remains PASS.
- [ ] Gate S behavior remains PASS.
- [ ] Manual refresh behavior remains PASS.
- [ ] Fleet still returns Bangkok SignalForge GREEN / Beijing DISABLED.
- [ ] Production canonical/signal state not unexpectedly modified.
- [ ] Gate AB zero-regression PASS.

---

# 33. Hard Stops

## HS-01 — Gate Z Regression

如果实现要求 Bangkok默认 `one AcquisitionAttempt → one Worker Run`：STOP → Architecture Review。

## HS-02 — Worker ABI Expansion

如果 v1.5 要求 Worker理解 source_id / app_job_id / canonical state / acquisition semantics：STOP → Cross-repo Contract Review。

## HS-03 — Remote Provider Appears

任何 Bangkok SignalForge → Beijing/Mac/Singapore remote execution 必须进入 Future Remote Provider ADR，不得顺带塞进 v1.5。

## HS-04 — Browser Production

不得在 Bangkok/Beijing 启用 Browser production。真实 source requiring browser 只能形成 Mac Browser Provider requirement；独立 Provider Invocation Contract live-verify 前不得 unattended production-enable。

## HS-05 — Browserless

进入 commercial production 前必须 Architecture Review + License Review。

## HS-06 — Mac Production Dependency

必须独立 Provider Invocation Contract PRD；禁止 ad-hoc SSH / HTTP / public CDP / arbitrary command 或 URL surface。

## HS-07 — Automatic Cross-zone Failover

必须单独 Source Policy / Security Review。

---

# 34. Engineering Principles

1. Preserve proven behavior before improving abstraction.
2. Refactor inside; preserve outside.
3. Acquisition lifecycle belongs to SignalForge.
4. Worker Run is execution, not business acquisition.
5. Policy is explicit; production does not dynamically guess strategy.
6. Failure classification precedes escalation.
7. Direct HTTP remains boring default.
8. Browser capability is earned by source evidence and executes only on Mac Browser Plane.
9. Do not freeze remote-provider abstractions before real remote-provider experience.
10. Future capability must not redefine current business truth.
11. Zero regression is a release feature.
12. More valuable sources are now more important than more infrastructure.

---

# 35. Post-v1.5 Product Direction

v1.5 完成后优先进入 Myanmar Source Expansion：

```text
Source candidate
↓
business-value audit
↓
network / shape audit
↓
Direct HTTP fixture
↓
Source Acquisition Policy
↓
parser
↓
baseline
↓
health
↓
production
```

真实 friction 再触发 capability。

---

# 36. Final Architecture

```text
                      v1.4.5 Worker Plane
                    known-good production
                             │
                    one application Run
                             │
                             ▼
                     SignalForge Bangkok
                             │
                     scheduler_run
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
       Job A               Job B              Job N
          │
          ▼
   Acquisition Policy
          │
          ▼
  AcquisitionRequest
          │
          ▼
  AcquisitionAttempt
          │
          ▼
  Local Direct HTTP Adapter
          │
          ▼
   EvidenceEnvelope
          │
          ▼
   ProcessingRecord
          │
          ▼
 Canonical / Dedup / Signal
```

v1.5 到这里结束，不包含 Remote Provider / SignalForge→Mac production invocation / Beijing acquisition / Browserless / distributed queue。Browser runtime host 已由 v1.5.1 固定为 Mac；跨主机 production invocation 仍未实现。

---

# 37. Final Recommendation

> **Freeze v1.4.5 as the production baseline.**
>
> **Use v1.5 only to formalize the local SignalForge acquisition lifecycle.**
>
> **Do not introduce federation until a real source forces federation.**
>
> **Browser-specific addendum:** Do not implement VPS Browser/Crawlee R3. Browser execution belongs only to Mac Browser Plane; keep the Mac Provider production-disabled until a separate secure invocation contract is proven.

版本主题：

> **SignalForge v1.5 — Acquisition Policy & Local Contract Foundation**

最终原则：

> **不要为了未来可能存在的复杂度，破坏已经验证过的 boring production system。**
