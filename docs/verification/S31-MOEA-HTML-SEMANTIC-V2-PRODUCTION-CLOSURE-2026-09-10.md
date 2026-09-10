# S31 MOEA HTML Semantic v2 Production Closure — 2026-09-10

## Outcome

S31 Ministry of Ethnic Affairs (MOEA) remains an HTML-only Bangkok Direct HTTP source, but its hidden issuer HTML comments now expose more precise actionable deadline semantics. Exact production application release is `038a78e195df0a8ea98f256d7bc2862e0234f6f8`.

The change deliberately does **not** add PDF acquisition or OCR. Official PDFs were used only as audit corroboration to decide whether the existing HTML evidence was sufficient.

## Existing-source audit that selected S31

A read-only production audit found 28 canonical records with all three properties: `business_stage=OPPORTUNITY`, no customer signal, and `deadline=null`.

The relevant source groups were:

- S26 DOMS: 2;
- S29 DWIR: 4;
- S30 MOFA: 1;
- S31 MOEA: 7;
- S32 MTE: 2;
- S34 PTD: 6 historical pre-v2 records;
- S36 DOA: 6.

S29/S32/S36 are embedded-image paths and would require OCR. S30 historical `mofa:56952` uses a JPG attachment and likewise requires OCR. S26 remains lower priority because the current DOMS evidence audit already showed scan-only attachment behavior. S34 semantic v2 was already closed. S31 was therefore the best next slice that could improve business semantics without adding a new runtime capability.

## MOEA evidence audit

S31 uses one issuer archive page:

`https://portal.moea.gov.mm/index.php?page=ORwuBwpT`

The archive contains structured tender cards and hidden HTML comments. Three current 2026 procurement invitations were checked against both the live hidden comments and their official PDFs.

### 2026-07-27

The hidden HTML comment explicitly contains the phrase `တင်ဒါတင်သွင်းရမည့်နောက်ဆုံးရက်` and date `2026-08-07`. This is represented as:

```text
deadline          = 2026-08-07
deadline_kind     = BID_SUBMISSION_DEADLINE
deadline_evidence = EXPLICIT_HTML_COMMENT_FINAL_SUBMISSION_DATE
```

The linked official PDF is text-native and corroborates the same submission deadline.

### 2026-05-28

The hidden comment describes three procurement lots and explicitly states a tender-application acceptance window from `2026-05-29` through `2026-06-10`, during `09:30` to `16:00`, followed by language saying tenders after the specified period will not be considered.

v2 therefore represents the window end as:

```text
deadline          = 2026-06-10
deadline_time     = 16:00
deadline_kind     = TENDER_APPLICATION_ACCEPTANCE_CLOSE
deadline_evidence = EXPLICIT_HTML_COMMENT_TENDER_APPLICATION_ACCEPTANCE_WINDOW_END
```

The linked official PDF is text-native and independently corroborates the same window. The same acceptance-window structure also appears in the issuer's 2024-05-17 record, demonstrating that the rule is not tailored to one 2026 item.

### 2026-02-04

The archive card has no usable hidden narrative. Its official PDF is text-native and contains tender-sale/event dates, but production v2 keeps this canonical `deadline=null` because adding listing-level PDF acquisition would expand the engine contract for a historical record. The current slice remains HTML-only.

## Epistemic boundary

The v2 parser distinguishes business date meanings rather than converting any nearby date into a deadline.

- `BID_SUBMISSION_DEADLINE` requires the explicit Burmese tender-submission-final-date phrase `တင်ဒါတင်သွင်းရမည့်နောက်ဆုံးရက်`.
- `TENDER_APPLICATION_ACCEPTANCE_CLOSE` requires the explicit tender-application acceptance marker `တင်ဒါလျှောက်လွှာလက်ခံမည့်ရက်`, at least two valid dates in that bounded segment, and uses the second date as the close. When a start/end time pair is present, the second time is used as the close time.
- A tender-form sale window by itself is not promoted to an actionable deadline.
- An unrelated generic `နောက်ဆုံး` phrase is not promoted to a bid deadline.
- Invalid dates/times fail closed.

Telegram preserves the distinction: `BID_SUBMISSION_DEADLINE` renders as `投标截止`; `TENDER_APPLICATION_ACCEPTANCE_CLOSE` renders as `投标申请接收截止`. Existing PTD `TENDER_FORM_SALE_CLOSE` remains `获取标书截止`.

## Implementation

PR #122 changes only the existing S31 semantic path plus the smallest source-opt-in migration guard:

- `moea-tender-archive-card-v1 -> v2`;
- `moea-tender-normalize-v1 -> v2`;
- canonicalizer remains `moea-archive-event-fingerprint-v1`;
- S31 stays `listing_complete_business_records=true`;
- acquisition stays `DIRECT_HTTP / HTML`;
- PDF attachment mode stays `METADATA_ONLY_NON_BLOCKING` with `fetch_in_primary_pipeline=false`;
- canonical payload adds `deadline_time`, `deadline_kind`, explicit `deadline_evidence`, and `semantic_version=2`.

A source-local opt-in, `suppress_signal_on_initial_listing_semantic_enrichment=true`, activates a one-time generic listing migration guard. The guard suppresses a parser-only historical signal only when:

1. the same canonical already exists;
2. the previous payload has no `semantic_version`;
3. the new payload is `semantic_version=2`;
4. after excluding only `deadline`, `deadline_time`, `deadline_kind`, `deadline_evidence`, and `semantic_version`, all business payload fields are identical.

Once a canonical is v2, the guard cannot apply again. A regression mutates a v2 deadline and proves the correction creates a normal `UPDATED` signal.

## Test and pre-production gates

Targeted MOEA/contract/Telegram tests: `22 passed`.

Full suite after the final evidence tightening: `249 passed`.

`git diff --check`: PASS.

Live branch parser audit over the current issuer archive returned 9 procurement invitations. Relevant rows included:

```text
2026-07-27  2026-08-07        BID_SUBMISSION_DEADLINE
2026-05-28  2026-06-10 16:00  TENDER_APPLICATION_ACCEPTANCE_CLOSE
2026-02-04  UNKNOWN           UNKNOWN_NO_ACTIONABLE_DEADLINE_IN_HTML_COMMENT
2024-05-17  2024-06-10 16:00  TENDER_APPLICATION_ACCEPTANCE_CLOSE
2023-06-09  2023-06-27        BID_SUBMISSION_DEADLINE
```

A fresh production-DB-copy replay before merge used the real 9 legacy S31 canonical records plus current issuer HTML. It returned:

```text
status            = SUCCESS
changed           = 9
signals_created   = 0
global signals    = 45 -> 45
S31 signals       = 0 -> 0
S31 semantic v2   = 0 -> 9
2026-05-28        = 2026-06-10 16:00 / TENDER_APPLICATION_ACCEPTANCE_CLOSE
```

The real production DB was not changed by this gate.

PR #122 GitHub Actions verify run `34455774263` passed. The PR squash-merged as exact runtime SHA `038a78e195df0a8ea98f256d7bc2862e0234f6f8`.

## Exact production deployment

The exact merged commit was archived with SHA256:

`5a8dcb0cf17c77b94d23e41976f1c8071aa964a57b3716a6ab4e34f505168ff3`

The hash matched locally and on Bangkok. The existing reviewed deployment script installed:

`/srv/signalforge/releases/038a78e195df0a8ea98f256d7bc2862e0234f6f8`

Immediate rollback target is the previous stable application:

`5fc7625da9c19599ef0a1dd1e6b3fca68d90013b`

Both acquisition and Telegram timers were active before and after deployment.

## Production migration verification

Before the reviewed S31 refresh:

```text
signals       = 45
S31 signals   = 0
S31 canonical = 9
S31 v2        = 0
DB quick_check = ok
```

The supported Worker-boundary command `systemctl start signalforge-refresh@S31.service` created Worker run:

`signalforge-20260910T083612Z-03b7f75a`

The production application run returned:

```text
trigger_type       = MANUAL
status             = SUCCESS
listing_complete   = true
items              = 9
tenders            = 9
changed            = 9
signals_created    = 0
details_attempted  = 0
backlog_remaining  = 0
```

After the refresh:

```text
signals       = 45
S31 signals   = 0
S31 v2        = 9
DB quick_check = ok
```

The three 2026 canonicals are exactly:

```text
2026-07-27  deadline=2026-08-07       kind=BID_SUBMISSION_DEADLINE
2026-05-28  deadline=2026-06-10 16:00 kind=TENDER_APPLICATION_ACCEPTANCE_CLOSE
2026-02-04  deadline=UNKNOWN          kind=UNKNOWN
```

Because the newly enriched historical deadlines are expired, the current customer read remains unchanged: `9` signal-backed opportunities = `8 OPEN + 1 UNKNOWN`. Telegram dry-run is `PASS / pending_count=0`.

Final Bangkok state:

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

## Scope boundary and next priority

No PDF production fetch, OCR, new Python dependency, DB schema, Browser Plane, Provider, Worker Plane, Control Plane, Beijing role, public API/webhook or Telegram delivery-identity change was introduced.

The remaining silent/deadline-unknown groups are predominantly image/scan dependent. Do not add OCR solely to exhaust historical records. Continue business-value and semantic-noise auditing of existing production sources; only introduce OCR when a current actionable opportunity demonstrates enough value to justify that capability.
