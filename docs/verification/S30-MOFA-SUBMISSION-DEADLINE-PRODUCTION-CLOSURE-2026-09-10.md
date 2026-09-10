# S30 MOFA Submission-Deadline Parser Production Closure — 2026-09-10

## Outcome

S30 MOFA previously labeled enriched PDF deadlines as `OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME`, but `_pdf_deadline()` selected the maximum date-time found anywhere in the PDF. PR #128 tightens the parser so a deadline is accepted only when the date-time is bound to a tender-submission line. Current production business payload remains byte-equivalent.

- Active runtime: `5ef49168c6f6d9f18f80d02d6b593c7b1fa77d28`
- Rollback: `195515f7a8267ca79155a973d23fff29f1ea52cc`
- Exact archive SHA256: `f3cf2d000c56c789051b9e0920725906d3f7b5fdbf7acc4a3993c46a5c2e1f4a`
- PR #128 CI: PASS

## Trigger and source evidence

The current opportunity `mofa:59800` exposes `deadline=2026-09-18`, `deadline_time=16:30`, and `deadline_evidence=OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME`. The official text-native PDF separately contains tender-form sale dates, the tender-form submission deadline, and an opening-date statement. Therefore selecting the maximum date-time was not a valid long-term evidence contract.

The reviewed PDF explicitly associates `18-9-2026 16:30` with the tender-form submission line. The opening date is separately stated as to be announced later.

Production evidence SHA for `mofa:59800`:

`aad5b2c3e51ffc289edb5018254f364896b01d14bee8fa3be7e362e756e130c7`

This is exactly the SHA of `tests/fixtures/mofa_tender_59800.pdf`, so the reviewed fixture is the exact production evidence bytes.

## Parser v3

Detail parser changes from `mofa-wordpress-html-optional-text-pdf-v2` to `mofa-wordpress-html-optional-text-pdf-v3`.

For each date candidate, v3 requires the same extracted PDF line before the date to contain both:

- `တင်ဒါ` — tender semantics;
- `တင်သွင်` — submission semantics.

The time must appear after the date on that line. Identical duplicated deadline values are deduplicated because MOFA PDFs may repeat notice pages. Exactly one distinct submission deadline must remain; zero or multiple distinct values fail closed.

The parser therefore rejects tender-form sale dates, unrelated event dates, and ambiguous multiple submission deadlines.

No payload field, normalizer, canonicalizer, schema, attachment policy, acquisition method or delivery path changed.

## Tests

- MOFA targeted tests: `8 passed`
- Full suite: `251 passed`
- `git diff --check`: PASS

Added coverage proves:

- a tender-submission line parses normally;
- sale-only date/time is rejected;
- unrelated tender event date/time is rejected;
- duplicate identical submission deadlines are accepted once;
- two different submission deadlines fail closed.

## Zero-migration proof

Before merge, a fresh current MOFA detail HTML was fetched from Bangkok and combined with the exact production PDF bytes. Branch v3 produced:

```text
deadline          = 2026-09-18
deadline_time     = 16:30
deadline_evidence = OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME
content_hash       = e46bd2662665590426e91c64e2e3dad49e6baeb18a3ec41efe37c63266b9b262
```

The production canonical content hash was exactly the same. Therefore the parser tightening changes evidence admission only and requires no semantic migration or backfill.

## PR and deployment

PR #128 squash-merged as:

`5ef49168c6f6d9f18f80d02d6b593c7b1fa77d28`

The exact git archive SHA256 matched locally and on Bangkok:

`f3cf2d000c56c789051b9e0920725906d3f7b5fdbf7acc4a3993c46a5c2e1f4a`

Reviewed release deployment succeeded with previous runtime `195515f7a8267ca79155a973d23fff29f1ea52cc` retained as rollback.

## Production verification

The active deployed v3 parser was invoked on Bangkok with current live MOFA detail HTML plus exact production PDF bytes. It returned:

```text
parser          = mofa-wordpress-html-optional-text-pdf-v3
deadline        = 2026-09-18
time            = 16:30
evidence        = OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME
parsed_hash     = e46bd2662665590426e91c64e2e3dad49e6baeb18a3ec41efe37c63266b9b262
production_hash = e46bd2662665590426e91c64e2e3dad49e6baeb18a3ec41efe37c63266b9b262
hash_equal      = true
```

Reviewed S30 refresh Worker run:

`signalforge-20260910T112656Z-4a72605b`

Result:

```text
status          = SUCCESS
discovered      = 2
changed         = 0
signals_created = 0
```

The scheduler had no changed discovery candidate, so direct deployed-parser verification is the actual parser-live evidence.

Final production state:

```text
status             = PASS
signalforge_health = GREEN
canonical_items    = 194
signals            = 45
recovery_backlog   = 0
S30 signals        = 1
DB quick_check     = ok
opportunities      = 8 OPEN + 1 UNKNOWN
Telegram pending   = 0
```

Both acquisition and Telegram timers remain active.

## Boundary and next slice

No DB migration, schema, new dependency, OCR, Browser Plane, Provider, Worker Plane, Control Plane, Beijing role, public API/webhook or Telegram identity change was introduced.

S30 and S39 now both enforce their claimed closing/submission evidence semantics. The next customer-value gap is that all eight OPEN opportunities still expose `deadline_kind=null`, even where their existing source evidence unambiguously means bid/tender submission close. Treat this as a separate presentation/semantic enrichment problem and avoid rewriting canonical facts merely to improve the read model.
