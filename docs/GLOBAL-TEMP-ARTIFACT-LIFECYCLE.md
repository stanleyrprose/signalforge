# SignalForge global temporary artifact lifecycle

Status: approved engineering policy; implementation merged in PRs #322/#323 by main `0d0e063`. Current per-host deployment and production cleanup remain unverified as of 2026-10-24.

## Invariant for every task

Business completion and cleanup are separate. Every source adapter, Tender Core
job, Browser Plane acquisition, OCR job, newspaper workflow and Telegram
delivery must classify outputs as either durable records/evidence or
regenerable temporary artifacts.

1. Never clean before the job has completed its own business success gate.
2. When a delivery is required, both delivery and durable provider receipts
   must be confirmed; unresolved `UNKNOWN` and `PENDING` are not success.
3. Only remove explicit task-owned temporary paths inside a fixed working
   directory, never by global glob/age alone.
4. Preserve retained source evidence, audit reports, business databases,
   provenance, run logs needed for analysis, dispatch receipts and code/config.
5. A failed cleanup creates a warning and a cleanup-only follow-up; it must
   never cause Telegram to be resent or a source to be fetched again.
6. Remote nodes must each confirm their own cleanup. Never assume Mac cleanup
   proves Bangkok cleanup.
7. Future sources cannot claim cleanup compliance without a success predicate,
   a list of task-owned transient paths and an acceptance test.

## Current adapter coverage

| Task | State |
| --- | --- |
| S01 Mac evidence HTML/model working artifacts | Implementation merged; gated by both durable Telegram receipts; live rollout unverified |
| S01 Mac outbox / Bangkok inbox | Existing guarded `s01_daily_transfer` and `s01_daily_cleanup`; retain contracts and verify current receipts |
| Newspaper PDF/Digest | Pending native receipt mapping, independent of S01 |
| Tender Core artifacts | Pending classification of persistent evidence vs temporary files |
| S20 OCR/PDF, Browser Plane and other source workers | Pending per-owner integration and source-specific verification |
| Website monitoring | Pending adapter and durable event/notification acknowledgement |

No broad sweeping deletion is permitted while adapters remain unreviewed.

## Rollout gates

1. Human review and acceptance of scope and code.
2. Affected-path tests, fail/UNKNOWN/success branches, and cleanup-only failure tests.
3. Separate PR/CI/merge release closure.
4. Separate Mac and Bangkok production deployment, with one genuine delivery
   receipt check per integrated workflow, no intentionally duplicate dispatch.
5. Check source evidence and durable receipts still exist after deletion.
