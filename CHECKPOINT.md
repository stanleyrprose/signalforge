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

## Implementation and verification status

Implementation, static review and authorized local verification are complete on `refactor/tender-core-only`.

Validation completed on 2026-10-12:

- affected core-path suite: 112/112 PASS;
- MPA/provider/database focused suite after cleanup: 42/42 PASS;
- complete repository suite: 429/429 PASS;
- `python -m compileall -q signalforge tests`: PASS;
- Source Registry and Provider Invocation Contract JSON validation: PASS;
- `sh -n bin/signalforge` and `sh -n deploy/deploy-signalforge-release.sh`: PASS.

Validation found and fixed two stale refactor residues: the registry loader still required retired C2/C3 provider capability flags, and MPA still retained manual-preview-only helpers/tests after the manual provider bridge was removed.

Current implementation facts:

- 27 enabled sources, all explicitly `item_kind=TENDER`;
- source polling is 15 or 30 minutes and runtime validation rejects enabled sources slower than 30 minutes;
- due-source scheduling is every 5 minutes; Telegram delivery is every 5 minutes at the :45 second offset;
- Telegram's internal current-tender read is unbounded and no longer has the 500-row read-view cap;
- source scorecard/business KPI yield is not mission-filtered; mission classification is analytical metadata only;
- business KPI measures recent Signal-created-to-Telegram success latency from existing receipts;
- Assurance uses `tender_coverage` for bounded independent MPT/MYTEL reconciliation; the retired ATOM surface trigger is removed;
- precursor, project-link/lead-time, customer profile, pilot feedback, standalone digest, non-tender news/policy sources, manual provider bridge and generic C2/C3 browser escalation are retired from the active tree;
- static consistency audit found no missing relative imports, no missing adapters for active sources, and no invalid provider capability references;
- GitHub remains the sole project SOT.

Per `AGENTS.md`, PR creation, GitHub CI, merge, deployment and production Telegram sends still require the next explicit release-closure/deployment gates.
