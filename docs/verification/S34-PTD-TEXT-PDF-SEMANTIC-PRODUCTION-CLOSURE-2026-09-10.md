# S34 PTD Text-PDF Semantic Production Closure — 2026-09-10

## Outcome

S34 Posts and Telecommunications Department is now production-capable of using its official same-origin tender PDF as a required semantic supplement to the issuer HTML. The production application is `5fc7625da9c19599ef0a1dd1e6b3fca68d90013b` and the final gate is PASS.

The change does not treat every date in a tender PDF as the same business concept. PTD section 3 is represented as `deadline_kind=TENDER_FORM_SALE_CLOSE`: the last date for obtaining/purchasing the tender form, which is an opportunity-participation boundary and is **not** asserted to be a bid-submission deadline. PTD section 6 is retained separately as `tender_opening_date` / `tender_opening_time`. `deadline_time` stays null when the issuer does not state a sale-closing time.

## Why this slice was selected

The existing-source business-value audit found 28 canonical records marked `business_stage=OPPORTUNITY` with no deadline and no customer signal. Rather than add S41/S42 for source count, the audit selected S34 because all six 2026 PTD opportunity records already linked official tender PDFs and their canonical payloads explicitly said `HTML_EVENT_SCOPE_PDF_DEADLINE_UNPARSED`.

This was an existing-capability opportunity: `pypdf==6.16.2` was already an application dependency, so no OCR, new dependency, browser engine, provider or service was required.

## Official PDF evidence audit

All six current S34 official PDFs were fetched from PTD and tested with the existing text-PDF stack. All six are text-native. Five expose a stable, valid section-3 sale-close date and section-6 opening schedule; one PDF has damaged/incomplete extracted date glyphs and correctly remains UNKNOWN.

| Canonical | Sale close | Tender opening | Result |
| --- | --- | --- | --- |
| `ptd:2026-05-19:da5f996299cbbc95` | `2026-06-04` | `2026-06-09 13:30` | parsed |
| `ptd:2026-05-26:739549b4ad40ffc5` | UNKNOWN | UNKNOWN | text-native but schedule unreadable |
| `ptd:2026-06-23:d3580760420bf8bc` | `2026-07-13` | `2026-07-16 13:00` | parsed |
| `ptd:2026-07-30:2cc7b9918c60651f` | `2026-08-14` | `2026-08-18 10:30` | parsed |
| `ptd:2026-07-30:5fa9f5303e79d570` | `2026-08-20` | `2026-08-25 13:30` | parsed |
| `ptd:2026-07-31:a683b1bfdd91b4c7` | `2026-08-20` | `2026-08-25 14:30` | parsed |

The parser is line/section anchored and validates calendar dates. It does not use a broad whole-document regex and does not cross section boundaries to invent a date. If text extraction is present but the schedule is not safely readable, canonical output is `deadline=null`, `deadline_evidence=UNKNOWN_IN_TEXT_NATIVE_PDF_SCHEDULE_UNREADABLE`.

All five parsed sale-close dates are already expired as of 2026-09-10, so this rollout is not used to resurrect historical opportunities as current business leads.

## PR #119 — PTD HTML + PDF semantics

PR #119 added the required single official text-PDF path while preserving Direct HTTP and the existing S34 canonical identity. S34 source policy moved to v2 with one required, same-origin PDF attachment. Parser/normalizer versions moved to PTD semantic v2; canonicalizer identity remained unchanged.

Read surfaces preserve the semantic distinction end to end:

- `opportunities` carries `deadline_kind`, `tender_opening_date`, and `tender_opening_time`;
- `briefing` preserves those fields;
- Telegram renders PTD section-3 dates as `获取标书截止`, not generic `截止`, and renders tender opening separately.

Local targeted and full gates passed; the final pre-merge full suite was `246 passed`. GitHub Actions verify run `34451641329` passed. PR #119 squash-merged as `69ae03d47eab719152f09134f33a35cfef467e80`. Its deployment archive SHA256 was `65fb26f863a4f5c1b53d5dec64a0d3d74d27805cde86972e9634712092880d25`.

A live temporary baseline against the real PTD site produced `discovered=6 / fetched=6 / details=6/6 / changed=6 / signals=0` and reproduced exactly the five parsed schedules plus one unreadable schedule above.

## Production-copy gate exposed a suppression defect

The initial PR #119 rollout attempted to suppress historical parser-capability enrichment only when the previously stored detail SHA matched the newly fetched raw HTML SHA. A production-DB-copy replay disproved that assumption before any real production S34 signal was created.

PTD is an ASP.NET site whose raw detail HTML can change in non-business bytes. On the temporary production copy, exact release `69ae03d...` correctly enriched one historical canonical but returned `changed=1 / signals_created=1`, moving the copied signal count `45 -> 46` and S34 `0 -> 1`. The real production DB remained `45` total signals and `0` S34 signals.

This was treated as a failed production-copy gate, not as acceptable historical noise.

A direct `refresh-source S34` invocation outside systemd also correctly failed closed because the Worker `INVOCATION_ID` descriptor was absent. The reviewed `systemctl start signalforge-refresh@S34.service` path then ran successfully with an authenticated Worker correlation (`signalforge-20260910T075224Z-9fe758c9`), but had `candidates=0` because a recent normal S34 health probe had already refreshed the detail scheduler state. Production state was not forced or rewritten to manufacture a candidate.

## PR #120 — semantic-only initial enrichment suppression

PR #120 replaced raw-byte equality with a one-time semantic projection rule. Suppression is possible only when all of the following are true:

1. the source explicitly opts in with `suppress_signal_on_initial_attachment_enrichment=true`;
2. the previous canonical exists for the same key;
3. the previous canonical is explicitly the pre-v2 PTD shape: `attachment_policy=METADATA_ONLY_NON_BLOCKING` and `detail_completeness=HTML_EVENT_SCOPE_PDF_DEADLINE_UNPARSED`;
4. after removing only the PDF/capability-transition fields, every remaining business payload field is identical.

The excluded transition fields are deadline/deadline-time/kind/evidence, tender-opening date/time/evidence, attachment policy, and detail-completeness. Therefore an ASP.NET raw-byte drift cannot create a false signal, while a title/scope/reference or other business-semantic change is not suppressed.

The guard is inherently one-time. Once an S34 canonical has the v2 attachment policy, later official PDF schedule changes are normal business updates. The regression suite explicitly proves a later sale-close change from `2026-08-20` to `2026-08-21` creates one `UPDATED` signal.

Targeted PTD + engine gate: `16 passed`. Full suite: `246 passed`. GitHub Actions verify run `34452719347` passed. PR #120 squash-merged as exact final production code SHA `5fc7625da9c19599ef0a1dd1e6b3fca68d90013b`.

## Exact production deployment and verification

Final deployment archive SHA256:

`526efb4855bd54b44511629879749ca9d945585372cb5d3fa63de5dc912de61c`

The archive hash matched locally and on Bangkok. Deployment completed successfully with active release:

`/srv/signalforge/releases/5fc7625da9c19599ef0a1dd1e6b3fca68d90013b`

The deploy script recorded immediate previous release `69ae03d47eab719152f09134f33a35cfef467e80`. That intermediate release contains the raw-SHA suppression defect found above and is **not the preferred semantic rollback**. The known-good pre-S34-feature application `9f4605fd55039704d335da7bda33662b9c234528` remains present and is the safer feature-level rollback target if the S34 PDF semantic capability itself must be removed.

Exact deployed-release production-copy verification used a fresh SQLite backup of the real production database, the active `5fc7625...` code, its release venv, and the live PTD source. It returned:

```text
status             = SUCCESS
health_probe       = true
candidates         = 1
fetched            = 1
detail_errors      = 0
details            = 1/1
changed            = 1
signals_created    = 0
signals            = 45 -> 45
S34 signals        = 0 -> 0
deadline           = 2026-08-20
deadline_kind      = TENDER_FORM_SALE_CLOSE
tender_opening     = 2026-08-25 14:30
```

The real production database was not mutated by this production-copy replay.

Final live Bangkok state after the hotfix deployment:

```text
status                 = PASS
signalforge_health     = GREEN
canonical_items        = 194
signals                = 45
S34 signals            = 0
recovery_backlog       = 0
DB quick_check         = ok
acquisition timer      = active
Telegram timer         = active
Telegram dry-run       = PASS / pending_count=0
```

## Historical migration policy

There is no forced historical S34 backfill. The five newly parseable historical participation deadlines are already expired, so rewriting all six production canonicals solely for completeness would create no current customer value and would unnecessarily widen the deployment operation.

Normal health probes may progressively enrich old S34 records using the one-time semantic suppression guard. A genuinely new PTD tender will enter the v2 pipeline immediately: issuer HTML plus its required official PDF, semantic participation deadline when safely available, separate tender-opening schedule, and normal NEW-signal behavior for a new canonical.

## Scope boundary and next priority

This closure introduces no OCR, new dependency, DB schema, Browser Plane change, Provider change, Worker Plane change, Control Plane change, Beijing role, public API, webhook, or Telegram delivery-identity change. `pypdf` was already in the application dependency set.

Continue the existing-source business-value audit. Prefer recovering trustworthy deadline/scope semantics from already linked official evidence with existing capabilities before adding S41/S42 merely to increase source count.
