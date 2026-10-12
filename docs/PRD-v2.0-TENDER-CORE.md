# PRD v2.0 — SignalForge Tender Core

Status: APPROVED PRODUCT BASELINE
Updated: 2026-10-11
Repository: stanleyrprose/signalforge

## 1. Product objective

SignalForge exists to detect new or materially updated official Myanmar government/SOE procurement tenders and deliver useful Simplified-Chinese Telegram alerts promptly.

No second product is implied by the repository.

## 2. Authoritative runtime path

```text
official tender source
  -> scheduled acquisition
  -> source-specific parser / bounded OCR when required
  -> retained official evidence + provenance
  -> canonical TENDER
  -> NEW / UPDATED signal
  -> correctness/readiness gates
  -> Simplified-Chinese presentation translation
  -> Telegram
  -> delivery receipt
```

Every retained production source must be capable of contributing formal procurement tender evidence. Formal `TENDER` records are eligible for Telegram regardless of sector or commercial priority, subject only to correctness/safety gates and delivery deduplication.

## 3. Required alert content

When present in official evidence, expose:

- procuring entity;
- procurement scope/items;
- quantity, lots or units;
- explicit budget/price/amount;
- tender/reference number;
- submission/document-sale/opening dates as applicable;
- location;
- direct official-source URL.

Unknown fields remain unknown. Do not infer numbers, dates, references, product models or money values.

## 4. Required reliability capabilities

Keep only reliability machinery that protects the tender path:

- source health and scheduler recovery;
- canonicalization/material-change detection/deduplication;
- evidence/provenance retention;
- source-specific PDF/image/document OCR where a retained tender source requires it;
- Myanmar/Burmese -> Simplified-Chinese presentation translation;
- fail-closed readiness/qualification rules;
- delivery receipts;
- independent coverage audit;
- missed-signal ledger;
- random/noise false-negative review;
- Assurance/metric-validity review;
- bounded provider/Mac Browser Plane acquisition contracts required by retained tender sources.

These are supporting controls, not separate products.

## 5. Explicitly out of scope

Do not implement or retain:

- project precursor / early-project monitoring;
- project-to-procurement linking or lead-time metrics;
- multi-tenant/customer profile architecture;
- per-customer Telegram filtering;
- pilot-validation/feedback workflows;
- Telegram inline relevance/action buttons;
- standalone strategic/business digest;
- pure policy, regulation, operator-network-news or official-news feeds that cannot produce formal tenders;
- generic browser escalation layers not used by a retained tender source;
- SaaS billing, customer portal or generalized plugin architecture.

If a future requirement needs one of these, it requires a new approved PRD rather than dormant code or feature flags.

## 6. Source policy

`registry/Source-Registry-v1.yaml` is the executable source inventory.

An active source must satisfy all of:

1. official government/SOE or issuer-original procurement surface;
2. can produce a formal tender record;
3. has a bounded acquisition/parser contract;
4. has source health policy;
5. preserves evidence/provenance;
6. passes activation gating where defined.

Deferred sources may remain only when they are plausible future tender sources blocked by a concrete acquisition/OCR/TLS limitation. Non-tender context sources do not belong in the registry.

## 7. Telegram semantics

Primary delivery is one global owner feed.

- one canonical signal is delivered once per `(channel, canonical_key, signal_id)` semantic identity;
- no customer/profile branches;
- no feedback callback polling;
- Myanmar text must not leak to the final Chinese presentation when production translation is required;
- missing normalized quantity may be presented truthfully as “详见官方原文” rather than fabricated;
- transport failure must not create a success receipt.

## 8. Data and migration boundary

Legacy production SQLite databases may contain tables/columns from retired precursor/pilot/digest features.

The refactor does not destructively drop production data. New schema initialization stops creating retired product tables where safe; old residue may remain inert until a separately approved maintenance operation.

## 9. Deployment boundary

Production remains Bangkok-only. Mac/provider execution is used only by retained source contracts. Direct HTTP is the default.

Retired systemd digest/feedback units should be disabled/stopped/removed during the next approved deployment, but no deployment is authorized by this PRD itself.

## 10. Success metrics

Primary:

- formal tender discovery/delivery coverage;
- Signal-created-to-Telegram success latency: target <= 300 seconds; report recent median/P95 and within-target rate;
- source-publication-to-Telegram normal-path objective: <= 35 minutes for the current 15/30-minute source polling policy, excluding issuer/network/provider degradation and only where publication timing is observable;
- notice field completeness;
- duplicate-free delivery;
- reviewed missed-signal count / false-negative rate;
- high-value-source coverage proof.

Secondary operational source counts or GREEN states are not business success by themselves.

## 11. Source of truth and development lifecycle

GitHub `stanleyrprose/signalforge` is the sole SOT.

- `main` is accepted production-development baseline.
- Local worktrees are disposable.
- Development branches may be pushed as WIP only when push cannot trigger CI/PR synchronization/auto-deploy.
- During implementation: code + static diff inspection only.
- Tests require explicit implementation-complete authorization.
- PR/CI/Merge require release-closure authorization.
- Deployment requires separate approval.

## 12. Relationship to older documents

This PRD controls current product scope. Older acquisition/provider PRDs may remain as lower-level technical contract references only where their code paths are still retained.

Any older document that describes precursor, multi-tenant/pilot, standalone digest, non-tender strategic feeds or removed generic escalation capability is historical and must not override this PRD.


## 2026-10-12 user-approved daily cadence amendment (implementation in progress)

- Source polling interval: 86400 seconds for every active source.
- Due scheduler: once daily, with Telegram delivery no more than once per day and only after that day's acquisition cycle finishes. A fixed 30-minute offset alone does not establish this guarantee.
- This replaces the earlier 15/30-minute polling and 300-second/35-minute latency targets.
- Meaningful tender extraction audit: item + quantity/lot + issuer-evidenced bid submission deadline must be present within the same canonical tender; a portal card closing-date hint is not an issuer deadline. Missing recent tenders and network/parse failures must be reported separately.
- S01 National Portal promotion must retain issuer-authored evidence and avoid duplicate S51 and other issuer-source signals. Do not mark source GREEN from HTTP success alone.
- Production deployment and live audit are separately gated; this amendment does not claim production verification.

## 2026-10-12 S01/S51 Mac Browser Plane routing amendment

S01 and S51 use the existing mac-mm-01 PUBLIC_READ_ACQUIRE provider for discovery HTML, detail HTML and same-origin PDF; they no longer use Bangkok direct_http. This is a targeted routing change, not a global disabling of TLS validation. Mac Browser Plane must fetch and retain original document bytes and evidence provenance. If browser acquisition fails, record TLS/browser failure rather than manufacturing a tender. S01 remains a separate issuer-PDF parser, while S51 retains its Digital Development parser; exact URL deduplication is applied before S01 canonical insertion. Production verification requires real portal HTML and issuer PDF evidence.
