# SignalForge document authority and consistency audit — 2026-10-24

## Current governing documents

1. `GOAL.md` — dual-product objectives and separation of Tender Core vs News/Policy.
2. `AGENTS.md` — repository development/release gates; does not prove runtime deployment.
3. `docs/PRD-v2.0-TENDER-CORE.md` — Tender Core component only.
4. `docs/S01-S52-S53-NEWS-DELIVERY-CONTRACT.md` — current approved News/Policy S01/S52/S53 source-to-Telegram delivery contract.
5. `docs/S01-ALL-NEWS-REV2.md`, `docs/S01-DAILY-SCHEDULING.md` — S01 implementation-specific requirements, subject to the current news contract.

## Historical snapshots, not current product vetoes

- `CHECKPOINT.md` documents the 2026-10-11 tender-only reset, superseded for product scope by the subsequent dual-product GOAL.
- `docs/NEWSPAPER-DIGEST-V2-CONTRACT.md` records the 2026-10-16 transport-only release slice. Exclusion of S52/S53 source adapters applied **only to that PR**.
- `docs/S01-GOVERNMENT-INTELLIGENCE-REV1.md` records an initial review-first rollout, not a permanent ban on approved daily delivery.
- `docs/verification/*.md` are dated test, incident and production observations. Historical `S01 Assurance-only`, `NOT_DEPLOYED`, `tender-only` and newspaper fallback decisions are valid **for the date, subsystem and evidence recorded**, not assertions about today's News/Policy product scope or live delivery.
- Older PRD v1.5/v1.7, acquisition, provider and trigger policies remain valid for their technical/safety boundaries unless a newer explicit contract supersedes them. Do not globally erase TLS, evidence, procurement qualification or production safety requirements.

## Consistency rules

- S01 News/Policy collection and S01 Tender Assurance may coexist with distinct source roles and separate receipts; S01 news articles do not become canonical tenders.
- S52/S53 are approved newspaper News/Policy sources; the tender Source Registry is not their activation inventory.
- Daily acquisition, Chinese PDF translation, AI Digest, Bangkok Telegram delivery, durable independent receipts, and post-success cleanup are required **outcomes**. Documentation cannot establish whether they are running.
- Historical release gates and model choices (e.g., Mac Codex CLI) are implementation snapshots, not immutable product requirements.
- Do not rewrite dated verification evidence to make it match current policy. For current runtime PASS, inspect actual Mac/Bangkok scheduler logs, Telegram API message IDs and receipt state.

## Audit evidence and residual limitations

- 2026-10-24 local scan: 124 Markdown files, including 23 outside `docs/verification/`; relative Markdown links in the 23 non-verification files: 0 broken.
- Keyword/role scan of historical verification files found S01 `Assurance-only` and `NOT_DEPLOYED` statements tied to September/October tender snapshots; these are not conflicts with the newer independent S01 news pipeline.
- This is a documentation scope reconciliation, **not** a claim that all semantic contradictions across 124 files are mechanically proven absent. Final sign-off requires repository diff review and GitHub reconciliation. Production S01/S52/S53 execution and Telegram receipts remain separately unverified.

## Work takeover checkpoint (2026-10-24; not final acceptance)

- GitHub main read and fetched at `0d0e0632119e14d5867473bb77d97e9d72abd090`; local handoff changes preserved in `3e8c857` before integration.
- Explicit static inventory: 119 formal project Markdown files before adding the takeover report; the count excludes six ignored local `.ai-bridge` notes and tool/cache directories. The earlier 124-file scan used a different scope and is not the current formal-document total.
- All 101 verification Markdown files now carry dated applicability notes. Original-body SHA verification: 101/101 unchanged; relative rendered Markdown path targets: zero missing in the 119-file scan.
- Static path checking does not validate heading anchors, example commands, module/config contracts, external URLs, or semantics. Those gates remain open; no zero-conflict PASS is claimed.
- Full historical file contents have been retrieved, but detailed per-file semantic reconciliation is incomplete. The remaining file matrix and production blockers are recorded in [the takeover report](NEWS-TAKEOVER-AUDIT-20261024.md).
