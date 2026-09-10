# Read-Layer Deadline Kind Production Closure — 2026-09-10

## Outcome

PR #130 enriches the customer read model with source-reviewed deadline semantics without rewriting canonical facts. The eight current OPEN opportunities now expose `deadline_kind=BID_SUBMISSION_DEADLINE`; the one UNKNOWN DOMS opportunity remains `deadline_kind=null`.

Exact production runtime: `0c310c5185f899a633f91dad0d0afd72810f1974`.

Immediate rollback: `5ef49168c6f6d9f18f80d02d6b593c7b1fa77d28`.

Exact archive SHA256: `393eeef9fc7cbd04a4a92838dc0f41a64e93dd6627fef63b0bf20414124810ee`.

## Why read-layer instead of canonical migration

S30 MOFA, S38 Industry and S39 Energy already carry source-specific evidence proving that their current deadline values mean tender/bid submission close. However their historical canonical payloads did not include `deadline_kind`.

Rewriting those canonical rows only to improve presentation would create parser-only material changes and unnecessary customer signals. Therefore `current_opportunities()` derives the semantic label at read time.

Canonical `deadline_kind`, when present, always wins. The fallback is deliberately source-scoped:

- S30 + `OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME` -> `BID_SUBMISSION_DEADLINE`;
- S39 + `OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME` -> `BID_SUBMISSION_DEADLINE`;
- S38 + `EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME` -> `BID_SUBMISSION_DEADLINE`.

No other source/evidence pair is inferred.

This is important because the PDF evidence label is also used by other sources whose semantics have not been reviewed under the same contract.

## Verification

Targeted opportunity/briefing/Telegram tests: `20 passed`.

Full suite: `252 passed`.

`git diff --check`: PASS.

A copy of the real production DB was read through the branch implementation before merge. Results:

```text
opportunities = 9
OPEN          = 8
UNKNOWN       = 1
BID_SUBMISSION_DEADLINE = 8
null kind     = 1
```

The eight enriched rows were S30/S38/S39. `doms:12735` stayed UNKNOWN/null.

The production snapshot file SHA256 was identical before and after `current_opportunities()`, proving the view did not mutate the copied DB.

## PR and deployment

PR #130 Actions run `34471797826` completed PASS and squash-merged as:

`0c310c5185f899a633f91dad0d0afd72810f1974`

The exact git archive SHA256 matched locally and on Bangkok:

`393eeef9fc7cbd04a4a92838dc0f41a64e93dd6627fef63b0bf20414124810ee`

The reviewed release script deployed the release successfully. Rollback is `5ef49168c6f6d9f18f80d02d6b593c7b1fa77d28`.

No source refresh or DB migration was required because the change is read-only.

## Production verification

The deployed `signalforge opportunities` output returned:

```text
count       = 9
OPEN        = 8
UNKNOWN     = 1
kind counts = BID_SUBMISSION_DEADLINE: 8, null: 1
```

All six current S38 Industry rows, S39 `energy:235`, and S30 `mofa:59800` now expose `BID_SUBMISSION_DEADLINE`. DOMS remains null/UNKNOWN.

A direct read of canonical payloads confirmed all eight underlying canonical `deadline_kind` values are still null. Therefore the enrichment is strictly read-layer and did not rewrite facts or generate signals.

`business_briefing()` propagates the derived kind for the three current OPEN attention items, and Telegram renders all three with the Chinese label `投标截止`.

Existing delivery receipts are not invalidated by this presentation-only change, so Telegram does not resend already-delivered messages. Dry-run remains `pending_count=0`.

Final production state:

```text
status             = PASS
signalforge_health = GREEN
canonical_items    = 194
signals            = 45
recovery_backlog   = 0
opportunities      = 8 OPEN + 1 UNKNOWN
Telegram pending   = 0
acquisition timer  = active
Telegram timer     = active
```

## Boundary

No canonical payload migration, signal rewrite, DB schema, source parser, dependency, OCR, Browser Plane, Provider, Worker Plane, Control Plane, Beijing role, public API/webhook or Telegram identity change was introduced.

The next business-value question is separate: Telegram delivery currently consumes only `briefing.attention`. The five MEDIUM opportunities remain in `watchlist` as a compact summary and are not individually pushed. Before changing that, audit whether this is the intended signal-to-noise policy rather than automatically promoting or delivering every MEDIUM item.

## MEDIUM watchlist delivery audit — no change

The existing product contract intentionally delivers only `HIGH + REVIEW` attention rows to Telegram and keeps MEDIUM opportunities in the compact watchlist. This was re-audited rather than automatically expanding Telegram delivery.

All five current MEDIUM opportunities are S38 INDUSTRIAL items without ICT/Telecom strategic fit. Their deadlines are preserved in the opportunity view, and qualification is recalculated from current time on every briefing/delivery run. Therefore a MEDIUM item automatically becomes HIGH when it enters the <=72h urgency window.

A production DB snapshot was evaluated at `2026-09-12T00:00:00Z`. At that time `industry:1034` (deadline `2026-09-14 16:00` Myanmar time) moved from MEDIUM to:

```text
priority_band    = HIGH
urgency          = URGENT
attention_action = ACT_NOW
deadline_kind    = BID_SUBMISSION_DEADLINE
```

The Telegram dry-run produced exactly one new pending item: `industry:1034 ACT_NOW`. The other four not-yet-urgent industrial opportunities remained in the MEDIUM watchlist. Existing previously delivered HIGH/REVIEW items were not replayed.

Conclusion: keep Telegram v1 delivery policy unchanged. Do not individually push all MEDIUM items and do not add a second summary-delivery mechanism at this time. The existing dynamic promotion provides the intended low-noise path from watchlist to actionable alert.
