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


## 2026-10-15 explicit S41 owner-approved issuer TLS exception

- Owner explicitly accepts reduced transport trust for **S41 MYTEL only** to restore issuer-original tender feed access while Viettel Global's certificate is expired.
- Perform a standard TLS-verifying request first. A second request without certificate verification is allowed **only when the original failure specifically says the certificate expired**, and only for HTTPS on `viettelglobal.com.vn` or `www.viettelglobal.com.vn`. No HTTP downgrade, non-issuer redirect, global SSL override, or fallback on host mismatch/unknown CA.
- Preserve the original D1N challenge, canonical verification, business readiness checks and signal/delivery de-duplication. Emit an auditable warning whenever relaxed verification is actually exercised. This exception does not prove authenticity against an active MITM; owner knowingly accepts the risk.
- Revert the exception after issuer certificate renewal has been independently verified; no other source receives this exception.

## 2026-10-15 S20 official PDF route degradation handling

- MOEP issuer HTML contains links under `/mm/userfile/` that return HTTP 404, including recent and older documents. Never invent alternate download links or deadline/quantity from missing PDFs.
- Keep existing HTML-based Canonical evidence and non-blocking metadata policy. After daily tender delivery, perform a bounded HEAD-only check of up to five recent official S20 tender attachments and save the result in the daily state checkpoint. Include HTTP 404 count in the once-daily coverage report. This availability check is not PDF evidence, parsing or canonical promotion.

## 2026-10-16 owner-approved S01 Government Intelligence exception

The owner approved a **separate S01 Government Intelligence information output**, while preserving the existing Tender Core. The pure-news exclusion in Section 5 continues to apply **to the Tender Core pipeline**, but does not prohibit this independently gated S01 output. Its scope, evidence fields, deduplication, non-tender classification, review-first rollout and separate Bangkok Telegram digest are defined in `docs/S01-GOVERNMENT-INTELLIGENCE-REV1.md`.

Do not route Government Intelligence into canonical `TENDER` records, tender signals, tender Telegram receipts, or tender health/coverage KPIs. No automatic production delivery until the review-only Chinese preview is accepted.
