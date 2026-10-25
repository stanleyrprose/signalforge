# SignalForge — Development Agent Rules

> Current S01 amendment (2026-10-25): [Markdown body + independently attempted Digest](docs/S01-MARKDOWN-INDEPENDENT-DELIVERY-20261025.md) supersedes S01 PDF wording below. S52/S53 retain PDF. Content cleanup requires the selected body attachment and Digest receipts. This is approved behavior; deployment/production evidence is recorded separately.

## Active owner execution boundary — 2026-10-25

The owner initially limited this continuation to implementation/static review, then explicitly authorized PR, Merge and real deployment on 2026-10-25. Perform the required CI/affected-path verification and release checks for this approved slice; do not expand to unrelated regression/system work. Prior release approvals and prior passing test counts do not validate the new [news processing amendment](docs/NEWS-PROCESSING-POLICY-20261025.md). Preserve pending/unknown delivery inputs. Production is still the last accepted deployed release.

## Development lifecycle (Agent Development Policy v1.0)

- Read this repository's current branch, **`docs/PRD-v2.0-TENDER-CORE.md` (Tender Core component PRD), `GOAL.md` and `docs/S01-S52-S53-NEWS-DELIVERY-CONTRACT.md` (current dual-product scope)**, actual workflow triggers and project operational constraints before code changes. Older PRDs are lower-level historical/technical references and cannot expand product scope.
- Work on a **development branch**. During implementation **only write code and inspect static diffs**; do not run tests or acceptance commands.
- Commit locally and Push the development branch to GitHub as work-in-progress SOT only after verifying that the Push **will not trigger GitHub CI, an open PR synchronize event, or an external auto-deployment**. If uncertain or unsafe, stop before Push.
- **No PR, CI, Merge or deployment while code or required human review is unfinished.**
- Only after implementation and human acceptance are complete, and with explicit authorization, run affected-path tests and fix failures. Then obtain release-closure authorization for PR, CI, checks and Merge. Deployment requires separate approval.
- Do not put runtime data, client/customer details, secrets, downloaded content or privileged credentials in Git.
- **GitHub is the sole source of truth for project code, rules, PRDs, and current documentation.** Local worktrees are disposable working copies; do not treat unpushed local state as authoritative.

## Current dual-product scope

- The current owner-approved product scope includes Tender Core **and** separately operated S01/S52/S53 news acquisition, Chinese translation/PDF, AI Digest and Bangkok Telegram delivery. See `GOAL.md` and `docs/S01-S52-S53-NEWS-DELIVERY-CONTRACT.md`. Historical tender-only reset/PR documents cannot silently exclude the news pipeline.
- Preserve independent schedules, source inventories, deduplication and Telegram receipts. Do not infer production PASS from scope documentation.

## SignalForge boundaries

- Do not modify or interrupt retained tender-source collection, schedules, Telegram tender delivery, production job states, or deployed collectors as part of an engineering-instruction change.
- Preserve project-specific evidence/provenance and production gating rules; if a conflict exists, apply the stricter rule and request clarification.
- A README link or a file in another repository is not sufficient to prove a running Agent has loaded a policy.

This policy file is self-contained and governs development only. It does not authorize operation of production collectors, scheduled automations or customer-facing alerts.

## Global temporary-file cleanup requirement

For every existing and future SignalForge source/job on Mac, Bangkok or other workers: classify task-owned intermediate files at design time; after its business success gate and durable delivery receipts (where applicable), clean only explicitly allowlisted regenerable temporary artifacts. Never remove persistent business/audit/receipt DBs, code, configurations or credentials. The owner's 2026-10-25 news-only amendment explicitly reclassifies original/OCR/translated content and per-task review SQLite as disposable after confirmed PDF + Digest delivery; this does not permit deleting shared Tender Core or delivery ledgers. Preserve unresolved delivery states (`UNKNOWN`/`PENDING`) and recovery artifacts. Cleanup failure must not repeat acquisition, publication or Telegram dispatch. Multi-node cleanup needs independent per-node evidence. See `docs/GLOBAL-TEMP-ARTIFACT-LIFECYCLE.md`. This is an engineering policy; it does not itself grant permission to operate production systems.
