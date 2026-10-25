# GOAL — SignalForge Myanmar Tender Alerts + News/Policy Intelligence

> Current S01 amendment (2026-10-25): [Markdown body + independently attempted Digest](docs/S01-MARKDOWN-INDEPENDENT-DELIVERY-20261025.md) supersedes S01 PDF wording below. S52/S53 retain PDF. Content cleanup requires the selected body attachment and Digest receipts. This is approved behavior; deployment/production evidence is recorded separately.

Updated: 2026-10-25

The latest [news processing amendment](docs/NEWS-PROCESSING-POLICY-20261025.md) governs current news retention and unreadable-page handling: source content is retained during processing/recovery, then all task content is deleted after confirmed PDF + Digest delivery, keeping minimum dedup/receipt state. Low-confidence readable text is extracted as 待核; unreadable pages are marked/skipped. This is approved behavior, not deployed acceptance. No regression/system tests or PR/CI/Merge without new explicit approval.

**Current owner-approved scope:** S01/S52/S53 daily news acquisition, Chinese translation/PDF, AI editorial Digest and independent Bangkok Telegram delivery, as specified in `docs/S01-S52-S53-NEWS-DELIVERY-CONTRACT.md`. Historical references to future source authorization below describe the 2026-10-16 baseline; they do not revoke the owner's subsequent instruction. Actual activation/delivery remains unverified until production evidence is obtained.
Status: owner-approved product-goal expansion; implementation and production activation remain separately gated.

## Primary goals

SignalForge has two authorized, independently operated product outputs:

1. **Government/SOE Tender Alerts:** Detect new or materially updated official Myanmar government / state-owned-enterprise procurement tenders promptly and deliver clear Simplified-Chinese notifications to Telegram.
2. **Myanmar News & Policy Digest:** Acquire reliable Myanmar news, government announcements, policy and economic developments, translate relevant Burmese material into Simplified Chinese, deduplicate and assess importance, produce a source-auditable Chinese PDF and an editorial Chinese Digest, and deliver them through a separately controlled Telegram daily output.

Both goals prioritize verified, useful content over raw source counts. The news/policy goal does **not** redefine a news article as a procurement tender or weaken tender correctness gates.

## Separation of outputs and lifecycle

- **Tender Core** retains its existing canonical `TENDER` model, new/materially-updated signals, source inventory, qualification gates, scheduler, Telegram notices, delivery receipts and KPIs.
- **News/Policy Intelligence** has separate source eligibility, collection/review states, article/event deduplication, editorial ranking, PDF/Digest artifacts, dispatch controls, delivery receipts and coverage measures. It may reuse bounded acquisition, OCR, translation, rendering and transport capabilities without routing non-tenders into Tender Core.
- A government announcement that independently qualifies as a formal procurement tender must satisfy Tender Core evidence and readiness rules before entering that pipeline. Cross-output links or deduplication must not silently discard a tender.
- Both outputs may use the same Bangkok-owned Telegram bot transport but require distinguishable messages and independent idempotency/receipts. The initial review-first rollout has already received owner content acceptance; current recovery work preserves that acceptance and verifies deployment and production delivery separately.
- This GOAL authorizes the **product scope**, not immediate source activation, automatic sends, purchases, credentials, gateway changes or production deployment. Detailed requirements and acceptance gates belong to an updated PRD before implementation.

## Tender delivery contract

Every formal `TENDER` is eligible for the primary Telegram path regardless of sector or commercial priority, subject only to existing fail-closed correctness and safety gates.

When official evidence contains the facts, a Telegram notice should expose:

1. procuring entity / buyer;
2. concise procurement scope / item description;
3. quantity, lots or units;
4. explicit price, budget or monetary amount;
5. tender / reference number;
6. submission, document-sale and opening dates as applicable;
7. location; and
8. direct official-source link.

Myanmar/Burmese presentation text may be translated to Simplified Chinese. Canonical evidence remains issuer-original evidence. Numbers, dates, references, model names and monetary values must not be invented or silently changed.

## News/Policy Digest delivery contract

- Coverage may include material Myanmar politics, policy, economy, foreign relations/geopolitics, business, public services, social developments, and domestic conflict/security news where reliable public evidence is available.
- Preserve original article/document identity, publisher, publication date when known, source URL and acquired evidence during processing and recovery. After confirmed paired news delivery, the Oct 25 amendment removes content and retains only minimum identity/hash/counters/receipt state. Clearly distinguish an original report, an official claim, independent corroboration and editorial/AI inference.
- Produce a comprehensive, reviewable Chinese PDF edition/collection and a shorter prioritized Chinese Digest for reading in Telegram. Each item must be traceable to its source; missing, disputed or unverifiable details must remain explicitly uncertain.
- Translate Burmese into readable Simplified Chinese without inventing amounts, dates, statements or named entities. Eliminate advertisements, boilerplate and irrelevant duplicates without hiding material stories.
- Deterministic identity/content matching should precede bounded AI-assisted semantic deduplication, topic classification and importance ranking. Scores and editorial inclusion are not tender qualification gates.
- The Digest should emphasize consequential policy, politics, economy, foreign relations/geopolitics and public-interest developments, rather than maximizing the number of articles. Coverage auditing must account for important omitted content.
- PDF and Telegram delivery should be reproducible and individually receipted; failures must not be recorded as successful deliveries.

## In scope — Tender Core

- official tender-source acquisition and source-specific parsers;
- canonicalization, material-change detection and deduplication;
- evidence/provenance retention;
- bounded OCR/document extraction needed to read official tender evidence;
- presentation translation;
- qualification/readiness rules that prevent incorrect or unusable alerts;
- source health, missed-signal/noise review and Assurance;
- once-daily Telegram delivery after the daily acquisition cycle and delivery receipts;
- KPIs for tender coverage, timeliness and notice completeness.

## In scope — separate News/Policy Intelligence

- bounded collection from explicitly approved news, newspaper and official-policy sources, including separately approved S01/S52/S53 work when source contracts are established;
- original-evidence retention, Burmese-to-Chinese translation, classification, editorial prioritization and cross-source deduplication;
- independently reviewable Chinese PDF and short Chinese Telegram Digest;
- separate daily dispatch, idempotency, receipts, completeness/coverage review and missed-important-item audit;
- use of an approved cloud-model interface where it is supported and validated, without requiring Codex CLI as a production inference dependency.

## Explicitly out of scope unless separately authorized

- early-project / precursor discovery and project-to-procurement lead-time tracking;
- multi-tenant/customer profiles or customer-specific tender filtering;
- pilot feedback / inline Telegram feedback workflows;
- public SaaS, billing or customer portal features;
- classifying ordinary news as tender signals, relaxing tender evidence gates, or mixing news health and delivery metrics with procurement KPIs;
- new infrastructure, credentials, paid commitments or production scheduling merely as a consequence of this GOAL change.

Git history is the archive for retired capabilities; scope expansion alone does not require restoring old implementations.

## Business-success metrics

### Tender Core

1. **Tender delivery coverage** — official new/materially-updated tenders successfully delivered.
2. **Delivery timeliness** — source acquisition, due scheduling and Telegram delivery run once per day; receipts record actual latency.
3. **Notice completeness** — buyer, scope, quantity/lot, explicit amount, deadline/opening date, reference and official link when present in source evidence.
4. **Reliability** — duplicate prevention, source health, reviewed misses, false-negative noise sampling and delivery receipt integrity.

### News/Policy Intelligence

1. **Evidence-backed coverage** — material stories captured versus independently audited source output, including important omissions.
2. **Translation fidelity** — preserved factual claims, numbers, dates, publisher attribution and explicit uncertainty.
3. **Editorial utility** — low duplicate rate, auditable selection/ranking and useful Chinese PDF plus prioritized Digest.
4. **Delivery reliability** — separate daily completion, artifact integrity, unique Telegram sends and truthful delivery receipts.

A high source count or GREEN health state alone is not business success.

## Production boundaries

- Tender Core production orchestration and formal SignalForge Telegram transport remain Bangkok-owned. Mac may run approved news collection, OCR, AI translation, PDF generation and independent news schedules; approved Tender acquisition uses its bounded Provider contracts. Mac never sends the formal SignalForge Telegram output directly.
- Direct HTTP remains the default for Tender Core unless a source-specific approved contract specifies otherwise. Existing TLS/fail-closed exceptions are source-specific, not global.
- Keep tender and news schedulers, readiness decisions, canonical data and receipts logically independent. Reuse working primitives rather than adding duplicate infrastructure.
- AI/model provider selection and authentication must be supported, verified and cost-accountable. Codex CLI is not a required News/Policy production inference layer.
- Worker operational state does not absorb SignalForge business semantics.

## Source policy

- `registry/Source-Registry-v1.yaml` remains the **Tender Core** executable source inventory. Its active entries must be capable of producing formal government/SOE procurement tender evidence.
- Non-tender news, official newspapers and policy sources belong to a **separate News/Policy source inventory/contract**, not the canonical Tender Core registry. **S01/S52/S53 are now explicitly approved for daily News/Policy delivery** by `docs/S01-S52-S53-NEWS-DELIVERY-CONTRACT.md`; this does not silently activate runtime services or merge them into Tender Core.

## Source of truth and change gates

GitHub repository `stanleyrprose/signalforge` is the sole source of truth for code, rules, PRDs and current documentation.

- `main` is the accepted baseline; development takes place on GitHub-backed branches.
- This GOAL records owner authorization for the second product objective. The older tender-only exclusions in `docs/PRD-v2.0-TENDER-CORE.md` govern **Tender Core** only. The approved separate News/Policy product requirements are now reconciled in `docs/S01-S52-S53-NEWS-DELIVERY-CONTRACT.md`; runtime activation and actual delivery require evidence.
- This change alone does not assert that S52/S53, cloud GPT inference, PDF generation or independent daily Telegram delivery are already implemented or production-ready.
- Runtime state, secrets, downloaded evidence and production databases remain outside Git. Tests, PR/CI/Merge and deployment follow the project development gates.
