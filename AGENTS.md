# SignalForge — Development Agent Rules

## Development lifecycle (Agent Development Policy v1.0)

- Read this repository's current branch, **`docs/PRD-v2.0-TENDER-CORE.md` (the approved current product PRD)**, actual workflow triggers and project operational constraints before code changes. Older PRDs are lower-level historical/technical references and cannot expand product scope.
- Work on a **development branch**. During implementation **only write code and inspect static diffs**; do not run tests or acceptance commands.
- Commit locally and Push the development branch to GitHub as work-in-progress SOT only after verifying that the Push **will not trigger GitHub CI, an open PR synchronize event, or an external auto-deployment**. If uncertain or unsafe, stop before Push.
- **No PR, CI, Merge or deployment while code or required human review is unfinished.**
- Only after implementation and human acceptance are complete, and with explicit authorization, run affected-path tests and fix failures. Then obtain release-closure authorization for PR, CI, checks and Merge. Deployment requires separate approval.
- Do not put runtime data, client/customer details, secrets, downloaded content or privileged credentials in Git.
- **GitHub is the sole source of truth for project code, rules, PRDs, and current documentation.** Local worktrees are disposable working copies; do not treat unpushed local state as authoritative.

## SignalForge boundaries

- Do not modify or interrupt retained tender-source collection, schedules, Telegram tender delivery, production job states, or deployed collectors as part of an engineering-instruction change.
- Preserve project-specific evidence/provenance and production gating rules; if a conflict exists, apply the stricter rule and request clarification.
- A README link or a file in another repository is not sufficient to prove a running Agent has loaded a policy.

This policy file is self-contained and governs development only. It does not authorize operation of production collectors, scheduled automations or customer-facing alerts.

## Global temporary-file cleanup requirement

For every existing and future SignalForge source/job on Mac, Bangkok or other workers: classify task-owned intermediate files at design time; after its business success gate and durable delivery receipts (where applicable), clean only explicitly allowlisted regenerable temporary artifacts. Never remove business evidence, audit records, DBs, code, configurations or receipts. Preserve unresolved delivery states (`UNKNOWN`/`PENDING`) and recovery artifacts. Cleanup failure must not repeat acquisition, publication or Telegram dispatch. Multi-node cleanup needs independent per-node evidence. See `docs/GLOBAL-TEMP-ARTIFACT-LIFECYCLE.md`. This is an engineering policy; it does not itself grant permission to operate production systems.
