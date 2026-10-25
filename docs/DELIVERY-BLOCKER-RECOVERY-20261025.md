# Delivery blocker recovery — 2026-10-25

Owner request: investigate missing S01 and Tender delivery blockers; explicitly send an S01 failure notice to Telegram if AI quota is exhausted. Existing authorization for related PR/CI/Merge/deployment persists; no unrelated system testing or source-policy changes.

Verified observations:
- S01 Oct25 saved 202 details and 38 validated AI batches before quota exhaustion. Resuming retained acquisition after the indicated recovery time completed all 202 reviews; 150 unchanged bodies were suppressed and 52 new/changed articles produced a 15-page PDF.
- Bangkok confirmed Digest message 484. PDF upload ended UNKNOWN, without a message ID. Do not reset this state, resend, or clean its recovery content until independent reconciliation.
- Tender Oct25 attempted all 28 sources; S20 timed out, while four formal tenders were delivered with IDs 470–473. The following daily report failed with HTTP400. Its plain error text contains an unescaped angle-bracket token while the transport uses HTML.

Implementation:
- Detect AI usage limits immediately, retain completed work, and request a Bangkok-owned failure notice with its own source/day/failure receipt. Repeated quota events do not repeat successful notices; ambiguous notice sends block blind retry. Keep the acquisition snapshot so retry does not replace raw HTML and invalidate validated batches.
- Escape/split plain daily-report text within Telegram limits, recording each part before dispatch. Known rejected parts can retry; unknown outcomes require reconciliation.
- A malformed signal/presentation or definitive item-level HTTP400 does not suppress valid later tender items. Successful receipts remain unchanged; unsuccessful items do not receive success receipts. Shared network/authentication failures and ambiguous transport errors remain explicit failures.
- The daily report distinguishes blocked/failed messages from no newly discovered tenders. Partial delivery preserves acquisition and sent receipts for a later retry instead of declaring the day complete.

Status: implementation; required affected-path checks/CI and release evidence follow separately. No fake failure will be sent solely to exercise the production Bot.
