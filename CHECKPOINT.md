# CHECKPOINT — Tender Core Reset

Updated: 2026-10-11

## Decision

SignalForge is reset to one product objective: official Myanmar government/SOE tender detection and timely Simplified-Chinese Telegram delivery.

The following product directions are retired from the active tree:

- project precursor / early-project acquisition;
- project-to-procurement lead-time and link-review workflows;
- multi-tenant/customer business profiles;
- pilot validation and Telegram inline feedback;
- pure strategic/news/regulatory intelligence inputs;
- separate daily business/strategic digest delivery.

Git history remains the archive; retired code is not preserved in the current tree for hypothetical future reuse.

## Baseline

- GitHub repository: `stanleyrprose/signalforge`
- authoritative baseline used for this refactor: `main` at `69cc69101039fadab7dcd8fa32bff875bf0e3545`
- implementation branch: `refactor/tender-core-only`
- GitHub is the sole project SOT; local worktrees are disposable.

## Core runtime retained

`registry tender sources -> run_due/run_source -> source adapters -> evidence/canonical items -> Signals -> briefing/readiness -> Chinese presentation translation -> telegram_deliver -> delivery_receipts`

Reliability layers retained: source health, Assurance, missed-signal review, noise false-negative review, evidence/provenance, OCR/provider contracts required by retained tender sources, and delivery deduplication.

## Implementation status

Core-only refactor is in implementation review. Per `AGENTS.md`, no tests, CI, PR, merge, deployment or production Telegram send is authorized during this phase.

The next gate after static review is explicit authorization to run affected-path verification.
