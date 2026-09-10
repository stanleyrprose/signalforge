# S39 Energy Closing-Context Parser Production Closure — 2026-09-10

## Outcome

S39 Energy previously emitted the evidence label `OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME`, but its parser selected the last date-time anywhere in the extracted PDF. PR #126 closes that evidence-contract mismatch by requiring an explicit bounded tender/closing/submission context. Current canonical business payloads are unchanged.

Exact production runtime: `195515f7a8267ca79155a973d23fff29f1ea52cc`.

Immediate rollback: `1e2f5b74860d0d88b7435789a8482706eddf784e`.

## Trigger

The current-opportunity decision-quality audit found that S39 `energy:235` has an explicit deadline `2026-09-18 13:00`, while the implementation of `_deadline()` merely collected all date-time matches from the PDF and returned `matches[-1]`. That implementation could be wrong if a future issuer PDF placed an opening, briefing or other date-time after the actual bid close.

The risk was upstream correctness rather than a currently wrong canonical. The production evidence label claimed explicit closing semantics that the parser itself did not enforce.

## Evidence audit

All four reviewed S39 text-native PDF fixtures were re-read with pypdf:

- energy:235 -> 2026-09-18 13:00;
- energy:233 -> 2026-08-28 13:00;
- energy:234 -> 2026-08-28 13:00;
- energy:232 -> 2026-08-18 13:00.

Each target date-time sits in a bounded clause that includes tender language before the date-time and closing/final-submission language after it. The PDFs use different embedded Myanmar font mappings, so extracted text contains small glyph-level variations in the closing phrase. A brittle exact-string match would therefore reduce reliability.

The production `energy:235` canonical evidence SHA is:

`4d2ef1694aa6a7221b1a2d46799eadba7f8edb9ef46a2045c573e07c1760c94b`

That SHA exactly equals `tests/fixtures/energy-235.pdf`, proving the reviewed fixture is the same PDF byte sequence used by the current production canonical.

## Parser v2 rule

`energy-html-plus-text-pdf-v1 -> energy-html-plus-text-pdf-v2`.

For each date-time candidate, v2 requires all of the following bounded evidence:

1. `တင်ဒါ` (tender) appears in the preceding 180 normalized characters;
2. the following 300 characters contain the tolerant closing-tail shape used by the reviewed issuer PDFs;
3. the following context also contains `သွင်` (submission) semantics.

Exactly one candidate must satisfy the predicate. Zero or multiple matching candidates fail closed. The parser no longer falls back to the last date-time in the document.

No normalized payload field, normalizer version, canonicalizer version, schema, attachment policy or acquisition method changed.

## Regression gates

Energy targeted tests: `7 passed`.

Full suite: `250 passed`.

New negative/ambiguity coverage proves:

- a valid bid closing context parses normally;
- a later unrelated date-time does not replace the true close;
- a date-time with no closing context returns UNKNOWN;
- two qualifying closing candidates fail closed.

All four reviewed real PDF fixtures retain their prior deadline values.

## Zero-migration proof

A fresh `energy:235` detail HTML was fetched from Bangkok. Branch parser v2 combined that current HTML with the exact production PDF bytes and produced:

```text
deadline         = 2026-09-18
deadline_time    = 13:00
deadline_evidence= OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME
content_hash      = 05fcbb728ea55e100291a1d0471ee1832dcdae0355ba616c48880f957f7d9cc1
```

The current production canonical content hash before deployment was exactly the same:

`05fcbb728ea55e100291a1d0471ee1832dcdae0355ba616c48880f957f7d9cc1`

Therefore this change tightens evidence admission while remaining material-payload identical. No semantic migration guard or backfill is needed.

## PR and exact deployment

PR #126 GitHub Actions verify run `34463254136` completed PASS and squash-merged as:

`195515f7a8267ca79155a973d23fff29f1ea52cc`

Exact git archive SHA256:

`46b4c264dc1b8e08ddeee08ef5fd6aefaf95d543eccebca792cd20732c5459ed`

The hash matched locally and on Bangkok. The existing reviewed deployment script installed:

`/srv/signalforge/releases/195515f7a8267ca79155a973d23fff29f1ea52cc`

Rollback target is the prior stable runtime `1e2f5b74860d0d88b7435789a8482706eddf784e`.

Both acquisition and Telegram timers remained active.

## Production verification

A reviewed `signalforge-refresh@S39.service` execution completed successfully with Worker run:

`signalforge-20260910T095651Z-9da87c0b`

The source had no changed discovery candidate in that run and correctly returned:

```text
status          = SUCCESS
discovered      = 4
changed         = 0
signals_created = 0
```

Because this scheduler run did not re-enter the PDF parser, it was not treated as sufficient parser-live evidence by itself.

A separate deployed-release verification then invoked the active `energy-html-plus-text-pdf-v2` parser on Bangkok using the current live detail HTML plus the exact production evidence PDF bytes. It returned:

```text
parsed_deadline      = 2026-09-18
parsed_time          = 13:00
parsed_evidence      = OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME
parsed_content_hash  = 05fcbb728ea55e100291a1d0471ee1832dcdae0355ba616c48880f957f7d9cc1
production_hash      = 05fcbb728ea55e100291a1d0471ee1832dcdae0355ba616c48880f957f7d9cc1
hash_equal           = true
```

Production signal counts remained unchanged:

- global signals = 45;
- S39 signals = 1;
- DB quick_check = ok.

Final Bangkok state:

```text
status             = PASS
signalforge_health = GREEN
canonical_items    = 194
signals            = 45
recovery_backlog   = 0
Telegram pending   = 0
acquisition timer  = active
Telegram timer     = active
```

## Boundary / next priority

No payload migration, DB schema, new dependency, OCR, Browser Plane, Provider, Worker Plane, Control Plane, Beijing role, public API/webhook or Telegram delivery change was introduced.

The current opportunity audit still shows all eight OPEN opportunities with `deadline_kind=null`. This is a separate customer-semantic issue. Any deadline-kind enrichment should be source-evidence-driven and must not weaken the now-reviewed S39 closing predicate or create parser-only customer signals.
