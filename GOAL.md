# GOAL — SignalForge Myanmar Government/SOE Tender Alerts

## Primary goal

SignalForge has one product goal:

> Detect new or materially updated official Myanmar government / state-owned-enterprise procurement tenders promptly and deliver clear Simplified-Chinese notifications to Telegram.

Everything in the active codebase must directly support that path or its reliability.

## Delivery contract

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

## In scope

- official tender-source acquisition and source-specific parsers;
- canonicalization, material-change detection and deduplication;
- evidence/provenance retention;
- bounded OCR/document extraction needed to read official tender evidence;
- presentation translation;
- qualification/readiness rules that prevent incorrect or unusable alerts;
- source health, missed-signal/noise review and Assurance;
- immediate Telegram delivery and delivery receipts;
- KPIs for tender coverage, timeliness and notice completeness.

## Explicitly out of scope

- early-project / precursor discovery;
- project-to-procurement lead-time tracking or linking;
- multi-tenant/customer profiles;
- customer-specific tender filtering;
- pilot feedback / inline Telegram feedback workflows;
- public SaaS, billing or customer portal features;
- strategic/news/policy intelligence feeds that cannot create formal procurement tenders;
- daily strategic/business digest as a separate product.

Git history is the archive for retired capabilities. They are not retained in the active tree merely for possible future reuse.

## Business-success metrics

1. **Tender delivery coverage** — official new/materially-updated tenders successfully delivered.
2. **Delivery timeliness** — observation/signal-to-Telegram latency where timestamps are available.
3. **Notice completeness** — buyer, scope, quantity/lot, explicit amount, deadline/opening date, reference and official link when present in source evidence.
4. **Reliability** — duplicate prevention, source health, reviewed misses, false-negative noise sampling and delivery receipt integrity.

A high source count, GREEN health state or large raw Signal count is not success unless it improves reliable tender delivery.

## Production boundaries

- Production is Bangkok-only.
- Direct HTTP remains the default acquisition method.
- Mac Browser Plane/provider capabilities are used only through existing reviewed, bounded contracts where a retained tender source genuinely requires them.
- TLS/HTTP failures remain fail-closed; no generic certificate bypass or browser fallback is introduced.
- Worker operational state does not absorb SignalForge business semantics.

## Source policy

`registry/Source-Registry-v1.yaml` is the executable source inventory. Active entries must be capable of producing formal government/SOE procurement tender evidence. Pure regulatory, policy, telecom-news, official-news and precursor-only sources do not belong in the active registry.

## Source of truth

GitHub repository `stanleyrprose/signalforge` is the sole source of truth for code, rules, PRDs and current documentation.

- `main` is the accepted baseline.
- Development happens on GitHub-backed feature/refactor branches.
- Local Mac worktrees are disposable working copies.
- Unpushed local changes are never authoritative.
- Runtime state, secrets, downloaded evidence and production databases remain outside Git.
