# CHECKPOINT — SignalForge Dual-Goal Status

Updated: 2026-10-18
Baseline: `main` at `e4eb9a5ae3613adb42059d9304bb5a53b2d30c1a` (merged PR #312)
Status: documentation reconciliation; production daily-operation acceptance remains separately gated.

## Authoritative scope

`GOAL.md` (updated 2026-10-16) defines **two independent outputs**:

1. **Tender Core** — official Myanmar government/SOE tender acquisition, evidence, qualified new/material-change signals, Simplified-Chinese Telegram notices and delivery receipts.
2. **News/Policy Intelligence** — separate news/policy acquisition and review, Chinese PDF edition, prioritized Chinese Digest and independently receipted Bangkok Telegram delivery.

News articles must not be inserted into canonical `TENDER` records merely to obtain delivery. The tender-only exclusions in `docs/PRD-v2.0-TENDER-CORE.md` still govern **Tender Core**, not the separately authorized news goal. The 2026-10-11 tender-only reset is a historical milestone, not the current whole-product scope. Detailed news rollout gates remain subject to approved product requirements and deployment acceptance.

## Implemented and evidenced (not equivalent to continuous production acceptance)

- Tender Core retains the formal tender evidence → canonicalization → signal/readiness → Chinese presentation → Telegram/receipt path, source health, OCR/provider contracts, Assurance and missed-signal/noise review.
- On 2026-10-12 the tender-core reset had 429 repository tests passing; this is **historical verification**, not a current production health claim.
- PR #310 (merged 2026-10-16): dual-goal `GOAL.md` authorization.
- PR #311 (merged 2026-10-17): isolated S01 all-news Rev2 Chinese PDF/Digest, Bangkok transport and checksum/receipt handoff. Its PR acceptance recorded Telegram preview messages 411/412; the PR explicitly did not claim unattended daily deployment.
- PR #312 (merged 2026-10-18): guarded S01 daily news runner and partial-coverage delivery. Live acceptance recorded five listing pages, 51 discovered, 50 translated, a 15-page PDF, and successful Bangkok Telegram messages 420/421. Failed articles remain in audit rather than blocking the whole edition.

These are specific S01 acceptance observations, **not** proof that S52/S53 or all other sources are active, or that every daily unattended run succeeds.

## Scheduling: desired contract vs repository configuration vs live runtime

**Approved product behavior:** `GOAL.md` calls for one daily Tender Core acquisition/delivery cycle and a separate daily News/Policy output. The pipelines require independent readiness, idempotency and receipts.

**Configuration checked at this baseline:**

- `systemd/signalforge-run-due.timer`: `OnCalendar=*-*-* 00:00:00 UTC` (daily).
- `systemd/signalforge-telegram-deliver.timer`: `OnCalendar=*-*-* 00:30:00 UTC` (daily).
- Each timer uses `Persistent=true`; randomized delay means exact invocation time may vary.
- S01 has a guarded daily runner implemented in code via PR #312. A merged runner is **not** proof of an enabled unattended production timer.

**Live activation unknown in this checkpoint:** deployed revision, active Bangkok/Mac timers, most recent successful Tender and News runs, daily delivery receipts, and end-to-end coverage have not been independently confirmed here. Inspect production runtime state rather than infer it from Git.

The old 2026-10-11 checkpoint's 15/30-minute source polling and 5-minute scheduler/delivery claims are superseded as a **current product/configuration description**. Do not reuse its old 27-source count as today's enabled-source count without querying the live registry/runtime.

## Outstanding acceptance evidence

- **Tender:** current enabled official tender sources, last daily source outcomes, discovered/qualified tenders, Telegram success receipts, completeness and known misses.
- **News:** individually approved/activated sources (including S01/S52/S53 as applicable), most recent unattended run, article/PDF/Digest coverage and omissions, successful Telegram receipts.
- **Operations:** independently verified systemd/scheduler enablement, recovery/idempotency after failure, and deployed code revision against GitHub `main`.

Until this evidence is recorded, classify the dual-goal system as **partially demonstrated; continuous production delivery not yet verified**.

## Retired scope and historical reference

Precursor/lead-time analysis, multi-tenant/customer profiles, pilot feedback and public SaaS remain outside the authorized product. The earlier Tender Core reset and its tests are preserved in Git history and `docs/PRD-v2.0-TENDER-CORE.md`, rather than being described as the present whole-product checkpoint.

## Change control

GitHub `stanleyrprose/signalforge` is the sole code/document SOT. This checkpoint is documentary: it does not change schedulers, enable sources, trigger Telegram delivery or authorize deployment. Development/verification/PR/CI/Merge/deployment gates remain governed by `AGENTS.md`.
