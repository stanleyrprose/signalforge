# S29 DWIR Waterway and River Works Tenders — Source Onboarding

Date (Asia/Yangon): 2026-09-05
Phase: PRE-PRODUCTION
Result: PASS / IMPLEMENTATION READY

## Decision

Allocate `S29` to the Directorate of Water Resources and Improvement of River Systems (DWIR), Ministry of Transport, as an issuer-original `ACTIVE_PRIMARY` tender source.

Production discovery uses the official DWIR homepage rather than the much heavier news category:

```text
https://www.dwir.gov.mm/
```

Source shape:

```text
DWIR homepage Latest News (~41 KB)
-> opportunity-stage tender links only
-> stable Joomla numeric article ID
-> issuer detail HTML
-> TENDER canonical item
-> embedded base64 image ignored / non-blocking
```

No schema migration, PDF extraction, OCR, Browser, JSON-primary target, Worker-runtime or Control-Plane capability is introduced.

## Why homepage discovery

Fresh Bangkok audit compared the issuer's available public discovery surfaces:

```text
DWIR news category     ~4.37 MB
RSS feed               ~5.77 MB
homepage Latest News   ~41 KB
```

The category and feed embed large article/image payloads; URL `limit=5` is ignored by the issuer. The homepage is more than two orders of magnitude lighter while still exposing the latest tender records.

Using the actual Bangkok SignalForge production fetcher, homepage Direct HTTP was stable 3/3 at roughly 0.17–0.29 seconds and exposed the current tender article IDs `298`, `297`, `296`, and `289`.

Browser gate is not triggered.

## Identity and discovery date

DWIR detail URLs contain a stable issuer-native Joomla numeric article ID, for example:

```text
/index.php/news-events/dwir-news/298-tender
/index.php/news-events/dwir-news/297-<Myanmar slug>
```

Canonical identity is:

```text
dwir:<joomla_article_id>
```

The slug and publication date are deliberately excluded from the canonical key so issuer title/date corrections update the same item rather than create duplicate `NEW` records.

Myanmar slugs are RFC percent-encoded before Direct HTTP. No Browser fallback is used.

The homepage date is discovery ordering evidence only. Fresh audit found a real issuer discrepancy for article `298`:

```text
homepage Latest News date = 2026-08-06
detail visible publication date = 2026-08-07
```

The detail visible date is authoritative for the canonical `publication_date`.

## Current business evidence

Fresh detail audit using the Bangkok production fetcher established:

### Article 298 — 2026-08-07

HTML text directly states FY2026-2027 tenders for riverbank erosion protection works, waterway-improvement works, whole-work tenders and work-material procurement.

The page contains an embedded base64 JPEG, but the event-level business scope is already present in HTML text. The image is not OCR'd.

### Article 297 — 2026-05-29

HTML directly states an Open Tender and exposes a fragmented issuer reference equivalent to:

```text
TENDER No.(2)Q/2026-2027
```

The parser normalizes only deterministic whitespace/digit fragmentation. Missing additional scope/deadline fields remain unknown.

### Article 296 — 2026-05-11

HTML directly lists office-building repair/maintenance, fencing, riverbank protection, waterway improvement/dredging and work-material procurement.

### Article 289 — 2025-09-19

The issuer title exposes:

```text
TENDER No.(3) M&E/2025-2026
```

It remains inside the 365-day initial baseline window.

## Selection boundary

Homepage discovery selects tender/opportunity titles and explicitly excludes procurement-outcome semantics including tender winners, awards and results.

A valid Latest News module with zero matching tenders is accepted as an empty successful discovery. Disappearance of the Latest News structure fails closed as parser drift.

## Deadline and embedded-image boundary

Current audited details do not expose a reliable tender deadline in HTML text, so:

```text
deadline = null
deadline_evidence = UNKNOWN_NOT_IN_HTML_TEXT
```

Embedded data images are counted only as evidence of partial detail shape:

```text
embedded_image_policy = UNPARSED_NON_BLOCKING
detail_completeness = HTML_TEXT_PARTIAL_EMBEDDED_IMAGE_UNPARSED
```

No image bytes, PDF, attachment, OCR service or Browser capability are requested by the primary pipeline.

## Update semantics

Fixture regression proves:

```text
same Joomla article ID
same canonical key
HTML scope changes
-> one UPDATED signal after baseline
-> no duplicate NEW item
```

The low-frequency health probe rechecks the newest known tender detail even when homepage discovery metadata is unchanged.

## Bangkok current-live isolated engine

The current S29 worktree was copied only to `/tmp` on Bangkok and executed with the existing production release venv against a temporary SQLite/evidence directory. Production DB/timer were not touched.

Result:

```text
status=SUCCESS
baseline=true
discovered=4
candidates=4
fetched=4
details_attempted=4
details_succeeded=4
items=4
tenders=4
changed=4
signals_created=0
backlog_remaining=0
```

Canonical rows:

```text
dwir:289  TENDER No.(3)M&E/2025-2026  publication=2025-09-19
dwir:296  DWIR-POST-296               publication=2026-05-11
dwir:297  TENDER No.(2)Q/2026-2027    publication=2026-05-29
dwir:298  DWIR-POST-298               publication=2026-08-07
```

Persistence/acquisition:

```text
canonical=4
signals=0
requests/attempts/evidence/processing=5/5/5/5
pending=0
SQLite quick_check=ok
```

Those five acquisitions are exactly one homepage discovery plus four issuer detail HTML requests. No PDF/image URL was fetched.

## Verification

```text
S29 + contract targeted tests = 10/10 PASS
full repository suite         = 102/102 PASS
Registry JSON                 = PASS
compileall                    = PASS
shell syntax                  = PASS
git diff --check              = PASS
```

Tests cover:

- lightweight homepage discovery and current four records;
- winner/result exclusion;
- RFC encoding of Myanmar detail slugs;
- valid-empty bulletin vs structural drift;
- stable Joomla numeric identity;
- detail publication date overriding homepage discovery date;
- split Tender No normalization;
- HTML event scope and null deadline;
- embedded-image non-processing;
- signal-free baseline;
- bounded health probe producing exactly one `UPDATED` on a material same-ID edit;
- zero PDF/image acquisition.

## Production gate

S29 is implementation-ready but not production-complete until:

1. PR CI passes and exact merged SHA is identified;
2. current Bangkok application is re-read immediately before rollout because parallel work may advance production;
3. candidate must not downgrade a newer production release;
4. timer is paused and current business/Worker counters are frozen;
5. exact SHA deploy causes zero business-state change before baseline;
6. one reviewed S29 baseline produces the then-current issuer-visible tender set with zero customer signal;
7. S29 acquisition lifecycle contains only homepage + selected HTML detail requests and no PDF/image fetch;
8. Worker cardinality/correlation passes;
9. Beijing remains SignalForge-free and both Worker doctors pass;
10. timer resumes and all automated sources return GREEN.
