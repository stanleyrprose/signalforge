# SignalForge PRD v1.5.1 — Mac Browser Plane Integration Amendment

**项目：** SignalForge / VPS Worker Runtime / Mac Browser Execution Plane  
**版本：** v1.5.1  
**日期：** 2026-09-04  
**状态：** Architecture Frozen / Integration Amendment  
**前置基线：** `SignalForge PRD v1.5 — Acquisition Policy & Local Contract Foundation` + `v1.4.5 Current Authorized Production Scope = COMPLETE / PASS`  
**Browser 基线：** `Mac-Centric Browser Execution Plane R1 v1.4.1`  
**主题：** **Preserve VPS Direct HTTP; move Browser execution exclusively to Mac; do not production-wire cross-host invocation yet.**

---

# 0. Amendment Authority

## 0.1 Why this amendment exists

v1.5 的核心 acquisition lifecycle、Bangkok-only SignalForge、VPS Worker R0–R2 Direct HTTP 与生产 cardinality 已经完成并验证，不重新打开。

本 amendment 只修正一个未来能力方向：

```text
OLD FUTURE DIRECTION
Browser-required source
→ Bangkok/Beijing VPS Browser/Crawlee R3
→ Playwright/Crawlee benchmark/soak
→ VPS Browser production capability
```

现正式替换为：

```text
NEW AUTHORITATIVE DIRECTION
Browser-required source
→ Mac Browser Plane
→ Mac Browser Provider
→ production_enabled=false
→ wait for separate Provider Invocation Contract
```

## 0.2 Precedence

发生 Browser / Playwright / Crawlee / Mac Provider 相关冲突时，优先级为：

```text
Mac-Centric Browser Execution Plane R1 v1.4.1
        ↓
SignalForge PRD v1.5.1 Integration Amendment
        ↓
SignalForge PRD v1.5 existing local-acquisition baseline
        ↓
legacy v1.4.5 R3 future wording
```

v1.5.1 只 supersede Browser-related future clauses；不 supersede 已验证的 v1.5 local acquisition contract。

---

# 1. Executive Decision

冻结以下集成规则：

> **Keep the existing VPS Worker Runtime and Bangkok SignalForge exactly for generic/Direct-HTTP business execution; move only Browser capability to Mac mini, and do not production-wire SignalForge to Mac until a separate secure Provider Invocation Contract is explicitly designed and verified.**

当前 production reality：

```text
Direct HTTP acquisition
→ production-capable on current VPS/SignalForge path

Mac Browser Provider for SignalForge
→ capability exists conceptually
→ production_enabled=false
→ no unattended cross-host invocation contract yet
```

Browser-required source 在 contract 出现前必须：

```text
BLOCKED_CAPABILITY
or
UNSUPPORTED_PENDING_PROVIDER_CONTRACT
```

不得偷偷 fallback 到 VPS Browser，也不得通过 ad-hoc Mac remote execution 绕过。

---

# 2. Frozen Production Baseline — Unchanged

以下全部保持不变：

```text
R0 Shared Worker Foundation       PASS
R1 Generic Direct HTTP Runtime    PASS
R2 Scheduling / Operations        PASS
R4 Remote Control / Fleet         PASS
R5 Bangkok SignalForge            PASS
```

继续冻结：

- Bangkok-only SignalForge；
- Beijing SignalForge zero-footprint；
- Direct HTTP default；
- SignalForge Source Registry / timers / DB / business truth 位于 Bangkok；
- Generic Worker Runtime 在 Bangkok / Beijing 继续有效；
- one SignalForge scheduler/service invocation → one Worker operational Run；
- N business jobs / AcquisitionRequests / AcquisitionAttempts remain internal SignalForge state；
- Worker DB 不持有 SignalForge business semantics；
- no Redis / Celery / central scheduler / distributed queue by default；
- TLS failure fail-closed；
- Browser is never automatic HTTP fallback。

---

# 3. VPS Browser R3 Disposition

## 3.1 Status change

旧状态：

```text
R3 Browser/Crawlee = NOT TRIGGERED
```

新状态：

```text
R3 VPS Browser/Crawlee
= SUPERSEDED_BY_MAC_BROWSER_PLANE
= NOT TO BE IMPLEMENTED ON BANGKOK OR BEIJING
```

这不是 `FAILED`，也不是等待未来 source 触发后继续实施 VPS R3。

## 3.2 Forbidden VPS Browser work

不得因为 SignalForge source 需要 Browser 而：

- 在 Bangkok 安装 Chrome / Chromium / Playwright / Crawlee；
- 在 Beijing 安装 Chrome / Chromium / Playwright / Crawlee；
- 为 VPS 增加 Browser profile/session/lease state；
- 在 `vps-worker-plane` 增加 SignalForge-specific Browser logic；
- 做 Bangkok Browser memory benchmark / Crawlee 24h soak 作为生产准入路径。

相关旧 Gate O2 / P / Q 文本如果仍存在，只能保留为历史证据，并必须标记：

```text
SUPERSEDED_BY_MAC_BROWSER_PLANE
```

---

# 4. Mac mini Browser Role

## 4.1 Sole Browser Runtime Host

Browser execution exclusively belongs to Mac mini Browser Plane：

- Playwright；
- Chrome；
- Browser Use；
- Chrome DevTools MCP；
- Browser profiles；
- Browser sessions / control leases；
- Browser evidence / trace；
- Browser resource governor。

VPS 不再是第二套 Browser Runtime。

## 4.2 What Mac does NOT own

Mac Browser Plane 不拥有：

- SignalForge Source Registry；
- TriggerEvent；
- SignalForge business Job；
- CanonicalDocument / canonical business record；
- Dedup；
- Signal；
- Review；
- Delivery；
- SignalForge business timers；
- SignalForge primary DB。

SignalForge 仍是 business truth owner。

---

# 5. Execution Provider Distinction

Source Acquisition Policy 必须概念上区分 acquisition execution provider：

```text
HTTP-capable source
→ current SignalForge/VPS Direct HTTP execution path

Browser-required source
→ Mac Browser Provider
```

当前不要求实现完整 Provider Registry，但 policy/model 不得再表达：

```text
JS_RENDER_REQUIRED
→ install/enable Browser on Bangkok
```

建议保留的 provider projection：

```yaml
provider_id: mac-mm-01
provider_type: browser
production_enabled: false
invocation_mode: manual_or_future_contract
```

`production_enabled=false` 是当前 invariant，不是临时文档说明。

2026-09-04 后，这个 projection 已经落入 `registry/Source-Registry-v1.yaml` 的 `providers.mac-mm-01`，并由 `Registry.load()` 做 fail-closed contract validation。当前机器可读能力边界包括：

```text
C0 fetch/raw artifact       = enabled
C1 render                   = enabled
C1 generic interaction      = disabled
C2 read-only inspect        = enabled
C3 Browser Agent            = disabled
persistent profile          = enabled
remote invocation           = disabled
network                     = direct-only
```

Mac Browser Plane 本身的 authoritative local manifest 由 `browserctl capabilities` 输出。SignalForge 保存的是用于 acquisition 决策的静态 provider projection；它不构成远程调用通道。

---

# 6. Required Lifecycle Separation

冻结三类生命周期：

```text
SignalForge business Job
!=
VPS Worker operational Run
!=
Browser Job
```

若未来 Browser Provider Contract 实施，至少需要显式 correlation：

```text
signalforge_job_id
acquisition_request_id
acquisition_attempt_id
provider_request_id
browser_job_id
```

任何一个 ID 都不得隐式替代另一个 lifecycle ID。

---

# 7. Failure-aware Resolution — Updated

继续保持：

```text
DNS_FAILURE        → bounded retry
HTTP_429           → bounded retry / Retry-After
HTTP_403           → review
TLS_FAILURE        → fail / audit; never certificate bypass
PARSER_DRIFT       → processing re-audit
```

Browser-related resolution 改为：

```text
HTTP failed
!= automatically Browser

JS_RENDER_REQUIRED
→ verify source evidence
→ verify Source Acquisition Policy permits Browser
→ route to Mac Browser Provider conceptually
→ if provider production_enabled=false:
     BLOCKED_CAPABILITY / UNSUPPORTED_PENDING_PROVIDER_CONTRACT
```

2026-09-04 live re-audit also establishes a concrete network-environment case:

```text
MPA / MOBA
Mac direct C0      = GREEN
Bangkok strict TLS = RED
```

This must be classified as provider/environment-specific `TLS_FAILURE`, not `JS_RENDER_REQUIRED` and not evidence that Browser execution is required. While Mac provider production is disabled, the correct production disposition is `FAIL / AUDIT / DEFER`; do not bypass TLS and do not create an ad-hoc SignalForge→Mac route merely to make the source green.

Evidence: `docs/verification/MAC-BKK-SOURCE-NETWORK-REAUDIT-2026-09-04.md`.

明确禁止：

```text
JS_RENDER_REQUIRED
→ Bangkok Playwright
```

---

# 8. Mac Provider Current Status

当前 frozen status：

```yaml
provider_id: mac-mm-01
provider_type: browser
production_enabled: false
invocation_mode: manual_or_future_contract
```

这意味着当前允许：

- source audit；
- interactive browser investigation；
- manual evidence gathering outside unattended production；
- Browser Plane 自身 local browserctl / SQLite lifecycle；
- **Manual Provider Bridge v0**：对显式批准的 deferred candidate，由人工导出 request、在 Mac 本地执行、再人工导入 evidence bundle；当前仅 S15A + C0 fetch + `EVIDENCE_ONLY`。

Manual Provider Bridge v0 不改变 `production_enabled=false`：它没有 SignalForge→Mac 网络调用通道，`provider-request` / `provider-import` 也不进入 VPS Worker verb manifest。当前仍不允许 SignalForge unattended production 依赖 Mac remote invocation。

操作与验证边界见 `docs/MANUAL-PROVIDER-BRIDGE-v0.md`。

---

# 9. Cross-host Invocation Hard Boundary

在单独 Provider Invocation Contract 之前，禁止：

1. Bangkok SignalForge 通过 unrestricted SSH 调用 Mac 任意命令；
2. 新建 ad-hoc unauthenticated HTTP Browser API；
3. public exposure of Mac CDP / port 9222；
4. 将 Browser URL 直接变成 unrestricted remote URL execution surface；
5. SignalForge runtime 动态拼 shell command 发送到 Mac；
6. Browser Plane 复制 SignalForge business state；
7. 将 Mac SQLite 当成 SignalForge canonical truth；
8. 用 shared filesystem hack 代替正式 evidence return contract。

---

# 10. Mac Offline Semantics

Mac offline 的正确语义：

```text
Mac Browser Provider unavailable
```

不是：

```text
SignalForge unavailable
```

因此：

- Bangkok healthy 时，所有 Direct HTTP sources 继续正常采集；
- SignalForge scheduler / DB / canonical / signal processing 继续运行；
- Browser-required source 单独进入 capability-unavailable state；
- 不允许 Mac outage 扩散成全局 SignalForge outage。

---

# 11. Beijing Role — Explicitly Unchanged

`Browser China = DISABLED` 只表示：

```text
Mac Browser China path unavailable
```

不表示：

```text
Beijing Generic Worker unavailable
```

Beijing 继续承担：

- China Mainland Direct HTTP / API；
- ETL；
- cleaning；
- batch；
- generic Linux Worker tasks。

Beijing 不获得 SignalForge Browser Runtime。

---

# 12. Physical Host vs Logical Role

Bangkok physical VPS 当前可以同时是：

```text
Bangkok VPS
├── SignalForge application host
├── Generic Worker Runtime host
└── optional Browser-egress network endpoint
```

只有第三个 Browser-egress logical role 可以按 Browser Plane 语境理解为 disposable。

不得将：

```text
Browser egress VPS is disposable
```

误读为：

```text
Bangkok SignalForge host is stateless/disposable
```

当前 SignalForge 架构中后者是错误的。

---

# 13. Source Onboarding Decision Tree — Updated

未来 source onboarding 使用：

```text
Source candidate
↓
business-value audit
↓
network / shape audit
↓
Can issuer evidence be acquired by Direct HTTP/API?
├─ YES
│  ↓
│  current VPS/SignalForge local acquisition contract
│  ↓
│  parser / canonical / health / baseline / production
│
└─ NO
   ↓
classify failure
   ↓
Is browser execution specifically required?
├─ NO → fix HTTP/auth/parser/source-policy issue
└─ YES
   ↓
Mac Browser Provider required
   ↓
production_enabled?
├─ NO → BLOCK / manual audit only
└─ YES → only after separate Provider Invocation Contract approval
```

这棵决策树替代旧的：

```text
Browser required
→ VPS Browser benchmark
→ Crawlee/Playwright soak
→ enable Browser on VPS
```

---

# 14. Current Source Expansion Impact

当前已生产的 Direct HTTP sources 不受影响。

对于正在审计/扩展的 source：

- Direct HTTP sufficiency 已证明 → 按当前 v1.5 local contract 继续；
- PDF attachment 可达但 HTML 足够 → PDF 仍可保持 metadata-only；
- HTTP failure / bot block → 先分类，不自动 Browser；
- 真正 JS-render-required → 不在 VPS 上实现 Browser；进入 Mac Provider blocked gate。

因此 source expansion 继续优先于 infrastructure expansion。

---

# 15. Evidence Authority Remains Fetch-method Independent

继续保留：

```text
Authority:
ISSUER_ORIGINAL
OFFICIAL_MIRROR
TRUSTED_PORTAL
THIRD_PARTY
TRIGGER_ONLY

Representation:
RAW_HTTP
API_RESPONSE
PDF
RENDERED_DOM
SCREENSHOT
WEBHOOK_PAYLOAD
```

Browser / Mac Provider 不自动提高 evidence authority。

未来 Browser evidence return 也必须回到 SignalForge EvidenceEnvelope / ProcessingRecord / canonical lifecycle，而不是创建第二套 business truth。

---

# 16. Future Provider Invocation Contract — Separate PRD Only

只有出现一个真实 Browser-required SignalForge source 时，才允许新 PRD 设计 cross-host contract。

该 PRD 至少必须定义：

- Provider Request schema；
- provider request / attempt / Browser Job correlation IDs；
- authentication / authorization；
- source allowlist；
- SSRF boundary；
- Mac reachability model；
- timeout；
- idempotency；
- retry semantics；
- evidence return envelope；
- evidence integrity / hash；
- failure semantics when Mac offline；
- manual vs unattended execution；
- no public CDP；
- no arbitrary URL injection；
- no arbitrary command injection；
- provider health / observability；
- operational rollback / disable switch。

在真实 Browser-required source 出现之前：

> **Do not prebuild this contract.**

---

# 17. Browserless Disposition

Browserless 不属于当前 SignalForge production path。

如果未来 Mac Browser Plane 已经承载多个真实 browser consumers，出现 measurable：

- duplicated lifecycle；
- session queue pain；
- orphan session pain；
- shared remote-session management pain；

才单独启动 Browserless ADR + License Review。

Browserless 不得成为“为了连 Mac 而先搭一个服务”的捷径。

---

# 18. Hard Stops

## HS-01 — VPS Browser Installation

如果 source onboarding 要求在 Bangkok/Beijing 安装 Chrome/Playwright/Crawlee：

```text
STOP
→ SUPERSEDED_BY_MAC_BROWSER_PLANE
```

## HS-02 — Implicit Remote Mac Invocation

如果实现要求 Bangkok SignalForge 直接 SSH/HTTP/CDP 调用 Mac，且没有独立 reviewed Provider Invocation Contract：

```text
STOP
```

## HS-03 — Mac Becomes Business Truth Owner

如果设计将 Source Registry / canonical / signal / review / business timer 移到 Mac：

```text
STOP
```

## HS-04 — Direct HTTP Regression

如果 Browser integration 要求改坏/关闭现有 Bangkok/Beijing Direct HTTP：

```text
STOP
```

## HS-05 — Mac Outage Becomes SignalForge Outage

如果 Direct HTTP source 因 Mac offline 停止：

```text
STOP
```

## HS-06 — Beijing Generic Worker Disabled by Browser Policy

如果 `China Browser disabled` 被实现为 Beijing Worker disabled：

```text
STOP
```

## HS-07 — Automatic Browser Fallback

如果 HTTP/TLS/parser failure 自动产生 Browser work：

```text
STOP
```

---

# 19. Architecture DoD — v1.5.1

- [ ] v1.5 local acquisition contract remains unchanged.
- [ ] v1.4.5 production R0–R2 / R4 / R5 remain frozen.
- [ ] VPS Browser/Crawlee R3 is explicitly marked `SUPERSEDED_BY_MAC_BROWSER_PLANE`.
- [ ] No Browser binaries are added to Bangkok/Beijing for SignalForge.
- [ ] Mac mini is the sole Browser Runtime host.
- [ ] SignalForge remains Bangkok-only business truth owner.
- [ ] VPS Worker remains generic and business-agnostic.
- [ ] Beijing Generic Worker remains enabled.
- [ ] Direct HTTP remains the default production path.
- [ ] `HTTP failed != automatically Browser` remains enforced.
- [ ] Browser-required source routes conceptually only to Mac Browser Provider.
- [ ] Mac Browser Provider remains `production_enabled=false`.
- [ ] Browser-required sources remain blocked while provider is disabled.
- [ ] No remote Mac invocation channel is introduced by this amendment.
- [ ] No public CDP / arbitrary URL / arbitrary command execution surface exists.
- [ ] Mac outage does not affect healthy Direct HTTP sources.
- [ ] Browser Job lifecycle remains distinct from SignalForge Job and Worker Run.
- [ ] Future cross-host production integration requires a separate reviewed Provider Invocation Contract PRD.

---

# 20. Engineering Principles — Updated

1. Preserve proven VPS production behavior.
2. Browser capability belongs to the Mac Browser Plane, not VPS R3.
3. SignalForge owns business truth; Browser Plane owns Browser execution.
4. VPS Worker owns generic Linux execution, not Browser business semantics.
5. Direct HTTP remains the boring production default.
6. Failure classification precedes capability escalation.
7. `HTTP failed != Browser required`.
8. Browser-required work is source-policy-approved, never dynamically guessed.
9. Mac Provider is disabled until a real cross-host contract exists.
10. No ad-hoc remote invocation in place of a reviewed Provider ABI.
11. One physical host may have multiple logical roles; do not confuse role disposability with host disposability.
12. More valuable sources remain more important than speculative infrastructure.

---

# 21. Final Architecture

```text
                         SignalForge
                        Bangkok VPS
                            │
                     Acquisition Policy
                            │
              ┌─────────────┴──────────────┐
              │                            │
       Direct HTTP/API                Browser-required
              │                            │
              ▼                            ▼
 current VPS/SignalForge            Mac Browser Provider
 local acquisition path             production_enabled=false
              │                            │
              │                      [NO unattended
              │                       cross-host contract yet]
              │                            │
              │                            ▼
              │                    Mac Browser Plane
              │                 Playwright / Chrome /
              │                 BrowserUse / DevTools
              │
              ▼
 EvidenceEnvelope / ProcessingRecord
              │
              ▼
 Canonical / Dedup / Signal / Review / Delivery
```

Mac Browser Plane 不持有最后一行 business truth。

---

# 22. Current Recommendation

> **Do not reopen v1.5 or v1.4.5 production architecture.**
>
> **Treat VPS Browser/Crawlee R3 as superseded, not merely untriggered.**
>
> **Continue Direct HTTP source expansion on the existing Bangkok SignalForge/VPS Worker path.**
>
> **When a real source proves Browser is required, route that requirement only toward Mac Browser Plane—but keep it blocked from unattended production until a separate secure Provider Invocation Contract is designed, reviewed, implemented, and live-verified.**
