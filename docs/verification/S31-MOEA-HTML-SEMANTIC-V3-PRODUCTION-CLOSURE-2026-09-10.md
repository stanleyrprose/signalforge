# S31 MOEA HTML Semantic v3 Production Closure — 2026-09-10

## Outcome

The existing-source deadline audit found one remaining S31 HTML-only semantic gap after v2: issuer record `moea:2023-06-09:c4536709e24937fd` explicitly states a tender-application submission final date, but the v2 parser recognized only the shorter tender-submission phrase. PR #124 closes that gap without adding PDF acquisition, OCR, a new source, schema, identity or runtime capability.

Exact production application release:

`1e2f5b74860d0d88b7435789a8482706eddf784e`

Immediate rollback:

`038a78e195df0a8ea98f256d7bc2862e0234f6f8`

## Audit that triggered v3

After S31 v2 closure, a read-only production audit examined every canonical satisfying:

- `business_stage=OPPORTUNITY`;
- no customer signal;
- `deadline=null`.

The count was 26 at the start of this slice. Existing canonical HTML/business text was scanned for explicit final-date, close-date, acceptance and submission language plus date patterns.

Only one record had enough existing text evidence to support an additional safe deadline rule:

`moea:2023-06-09:c4536709e24937fd`

Its hidden issuer HTML comment contains:

```text
တင်ဒါလျှောက်လွှာ စတင်ရောင်းချမည့်ရက် - (၁၂ -၆-၂၀၂၃)
တင်ဒါလျှောက်လွှာ တင်သွင်းရမည့်နောက်ဆုံးရက် - (၂၇ - ၆-၂၀၂၃)
```

The second phrase is an explicit tender-application submission final date and is semantically equivalent to the already accepted S31 bid-submission deadline pattern.

The remaining groups did not expose another safe HTML-only deadline:

- S26 DOMS: HTML scope/attachment metadata; no explicit actionable date in current HTML text;
- S29 DWIR: current HTML business text contains submission invitations but no actionable date; important schedule content remains in embedded images;
- S30 MOFA historical `mofa:56952`: JPG attachment; HTML has publication date but no deadline;
- remaining S31 rows: no additional explicit actionable HTML date pattern;
- S32 MTE: image supplement required for deadline;
- S34 PTD historical pre-enrichment rows: deadline remains in PDF path and all are expired; no forced historical backfill;
- S36 DOA: image supplement required for deadline.

Therefore v3 remains an HTML-only semantic improvement and OCR is still not justified by current business value.

## Semantic change

S31 now recognizes two explicit final-submission forms:

```text
တင်ဒါတင်သွင်းရမည့်နောက်ဆုံးရက်
တင်ဒါလျှောက်လွှာ တင်သွင်းရမည့်နောက်ဆုံးရက်
```

Both require a valid day-month-year date inside a bounded tail. Both map to:

```text
deadline_kind     = BID_SUBMISSION_DEADLINE
deadline_evidence = EXPLICIT_HTML_COMMENT_FINAL_SUBMISSION_DATE
```

The existing v2 acceptance-window rule remains unchanged:

```text
တင်ဒါလျှောက်လွှာလက်ခံမည့်ရက်
-> TENDER_APPLICATION_ACCEPTANCE_CLOSE
```

A tender-form sale window alone, unrelated generic `နောက်ဆုံး`, invalid date/time or missing explicit marker still fails closed.

The canonicalizer remains `moea-archive-event-fingerprint-v1`. Production acquisition remains one MOEA archive HTML request; PDF attachments remain metadata-only and are not fetched.

## Versioned migration guard

S31 payload semantic version changes from 2 to 3. Parser/normalizer change from:

```text
moea-tender-archive-card-v2 -> v3
moea-tender-normalize-v2    -> v3
```

The earlier one-off legacy migration boolean was replaced with a source-configured transition:

```json
{
  "listing_semantic_migration": {
    "from_version": 2,
    "to_version": 3,
    "suppress_signal": true
  }
}
```

The engine suppresses a customer signal only when:

1. the source explicitly configures a valid increasing semantic transition;
2. the existing canonical is exactly the configured `from_version`;
3. the newly parsed canonical is exactly the configured `to_version`;
4. after excluding only `deadline`, `deadline_time`, `deadline_kind`, `deadline_evidence`, and `semantic_version`, every business payload field is identical.

This avoids the unsafe alternative of suppressing any `UNKNOWN -> known deadline` change inside the same semantic version. A real issuer-side deadline addition/change after migration remains a normal material update and creates `UPDATED`.

## Tests

Targeted S31/contract tests:

`12 passed`

Full suite:

`249 passed`

`git diff --check`: PASS.

Regression coverage includes:

- original explicit bid-submission final-date pattern;
- new tender-application-submission final-date synonym -> `2023-06-27`;
- application-acceptance window -> `2026-06-10 16:00`;
- sale-only and unrelated final-date phrases remain non-actionable;
- configured v2 -> v3 semantic migration produces zero signal;
- a later v3 deadline correction produces one normal `UPDATED` signal.

## Live issuer and production-copy gate

A fresh live MOEA archive fetch contained 9 selected procurement invitations. Branch v3 parsing returned, among others:

```text
2026-07-27  2026-08-07        BID_SUBMISSION_DEADLINE
2026-05-28  2026-06-10 16:00  TENDER_APPLICATION_ACCEPTANCE_CLOSE
2026-02-04  UNKNOWN
2024-05-17  2024-06-10 16:00  TENDER_APPLICATION_ACCEPTANCE_CLOSE
2023-06-09  2023-06-27        BID_SUBMISSION_DEADLINE
```

A fresh copy of the real production database was replayed with the live issuer HTML before merge. Initial production state was `S31 v2=9 / v3=0 / global signals=45 / S31 signals=0`. The replay returned:

```text
status          = SUCCESS
changed         = 9
signals_created = 0
global signals  = 45 -> 45
S31 signals     = 0 -> 0
S31 v2          = 9
S31 v3 after    = 9
2023-06-09      = 2023-06-27 / BID_SUBMISSION_DEADLINE / semantic_version=3
```

The real production DB was untouched by this pre-merge gate.

## PR and exact deployment

PR #124 GitHub Actions verify run `34462131786` completed PASS. PR #124 squash-merged as:

`1e2f5b74860d0d88b7435789a8482706eddf784e`

Exact git archive SHA256:

`a7a2a8c01b526df93006460f020e8dc7e0acffafde7a6cbf316c6cf581fc932a`

The hash matched locally and on Bangkok. The existing reviewed release script deployed:

`/srv/signalforge/releases/1e2f5b74860d0d88b7435789a8482706eddf784e`

Previous stable runtime / immediate rollback:

`038a78e195df0a8ea98f256d7bc2862e0234f6f8`

Both acquisition and Telegram timers remained active.

## Formal production migration

Before S31 migration:

```text
DB quick_check = ok
signals        = 45
S31 signals    = 0
S31 v2         = 9
S31 v3         = 0
```

Reviewed Worker-boundary refresh:

`systemctl start signalforge-refresh@S31.service`

Worker correlation:

`signalforge-20260910T094447Z-d486be93`

Application result:

```text
trigger_type      = MANUAL
status            = SUCCESS
listing_complete  = true
items             = 9
tenders           = 9
changed           = 9
signals_created   = 0
details_attempted = 0
backlog_remaining = 0
```

After migration:

```text
DB quick_check = ok
signals        = 45
S31 signals    = 0
S31 v2         = 0
S31 v3         = 9
```

Confirmed production rows include:

```text
2023-06-09  deadline=2023-06-27       kind=BID_SUBMISSION_DEADLINE
2026-05-28  deadline=2026-06-10 16:00 kind=TENDER_APPLICATION_ACCEPTANCE_CLOSE
2026-02-04  deadline=UNKNOWN
```

The recovered 2023 deadline is historical/expired, therefore current customer output remains exactly `9 opportunities = 8 OPEN + 1 UNKNOWN`. Telegram dry-run remains `PASS / pending_count=0`.

## Remaining UNKNOWN audit state

After v3, silent `OPPORTUNITY + deadline=null` count is 25:

```text
S26 = 2
S29 = 4
S30 = 1
S31 = 5
S32 = 2
S34 = 5
S36 = 6
```

A full scan of their already-normalized HTML/business text found no second record with enough explicit actionable date semantics for a safe HTML-only parser improvement. These 25 therefore do not justify another immediate semantic patch.

## Final production state

```text
status             = PASS
signalforge_health = GREEN
canonical_items    = 194
signals            = 45
recovery_backlog   = 0
DB quick_check     = ok
acquisition timer  = active
Telegram timer     = active
```

No schema, new Python dependency, OCR, PDF production acquisition, Browser Plane, Provider, Worker Plane, Control Plane, Beijing role, public API/webhook or Telegram delivery-identity change was introduced.

## Next priority

Do not continue reducing historical UNKNOWN count merely for completeness. The remaining 25 are evidence-limited, predominantly image/PDF dependent or expired. The next business-value audit should move to the nine current customer opportunities and inspect whether their relevance, priority, scope, deadline semantics and customer-facing signal payloads are sufficiently decision-useful. OCR should be introduced only if a current actionable opportunity demonstrates a material missed-decision value.
