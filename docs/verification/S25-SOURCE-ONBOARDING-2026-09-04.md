# S25 MONPIFER Ministry Tenders — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / LIVE AUDIT PASS

## Decision

Allocate the previously reserved `S25` to the Ministry of National Planning, Investment and Foreign Economic Relations (MONPIFER) official tender table:

```text
https://www.monpifer.gov.mm/my/ministry-tenders
```

S25 is an `ACTIVE_PRIMARY` / listing-complete `TENDER` source. The official table itself already exposes the business record needed by SignalForge: visible deadline, tender description, department when present, official PDF metadata and an official Drupal `Read More` article alias.

No detail fetch, PDF parser, OCR, Browser, schema migration or new runtime dependency is required for P0.

## Why S25 was selected instead of forcing S16/S17/S18

A fresh 2026-09-04 audit of the conditional municipal pool found real but capability-expanding gates:

### S16 YCDC — deferred

- Direct HTTP business content is strong.
- `/frontend_tender` is a department index, not a stable list of tender records.
- Each department detail locator is a Laravel-encrypted ciphertext URL that changes on every request.
- No stable numeric tender/dept record ID is exposed in the listing.
- Current `discovery_items` identity is `(source_id, url)` and the same URL is used as transport locator.

Correct onboarding therefore requires an explicit generic contract:

```text
stable discovery identity != ephemeral transport locator
```

That entails discovery/recovery schema semantics and is intentionally not smuggled into one source adapter.

### S17 MCDC — deferred

- Current issuer-original tender posts are stable.
- Tender business detail is carried by official PDFs rather than HTML.
- Two current 2026–2027 tender PDFs were audited and were scan-only (`pypdf` extracted 0 characters from both).

A lightweight text-PDF runtime would therefore not unlock MCDC; Burmese image/OCR capability would be required and is not approved by this source slice.

### S18 NPTDC — deferred

- Correct legacy PHP board path is Direct-HTTP reachable when Burmese characters are encoded but literal parentheses in `ကြော်ငြာသင်ပုန်း(1)` are preserved.
- The board is large/mixed (approximately 3 MB) and includes tender + non-tender notices.
- Current tender specifics are image-based rather than text-complete HTML.

It therefore still requires both segmentation/classification and image/OCR capability.

### Other fresh candidates

- Ministry of Border Affairs: current official tender content exists, but Bangkok production fetcher failed TLS verification. Fail closed; no certificate bypass.
- Survey Department: self-signed TLS in Bangkok production path. Fail closed.
- Myanma Timber Enterprise: stable Joomla article IDs, but current tender content is image-based; OCR gate.
- DOMS: Direct HTTP works, but the tender category mixes invitation, evaluation meeting and award/result stages; a separate procurement-stage classifier is required.

MONPIFER was chosen because it adds business coverage without reopening any frozen runtime/schema capability.

## Bangkok transport audit

Using the actual Bangkok SignalForge production fetcher against the official tender table:

```text
3/3 SUCCESS
bytes=67260 each
body hash prefix=5c4e7ee1bf0d3649 each
elapsed ~=0.26s to 0.49s
```

Direct HTTP is sufficient. Browser gate is not triggered.

## Current official table shape

Current table contains one header plus 10 tender business rows. Representative rows include:

```text
2026-07-14 16:00 — purchase of 19 steel cabinets
2026-06-12 14:00 — Project Progress Monitoring and Reporting System (PPMRS) Upgrade
2026-05-27 14:00 — personnel/salary reporting Phase-1 + two 5kVA/5kW rack UPS systems
2026-05-25 16:00 — ministry procurement
2025 archive rows — construction, Customs/MACCS ICT and related procurement
```

As of the onboarding audit date, the newest visible deadline (`2026-07-14`) is already in the past. The first baseline is therefore historical state used to establish monitoring continuity; it must not be represented as currently open commercial opportunities.

## Stable identity

Each table row contains an official Drupal `Read More` article alias, for example:

```text
/my/ministry-article/amiusaaciimnkin-rngniimupnnmunng-niungngnkhaaciipaachksyrewnkiitthaan-2
```

The corresponding detail page was audited and exposes underlying Drupal node ID `21057`, proving that the article is an issuer-owned stable record. The numeric node ID is not present in the listing.

P0 intentionally does not add one detail acquisition per row merely to recover a numeric ID. Instead it uses the official article alias as the issuer record identity:

```text
reference_no_kind = issuer_article_alias
canonical_key = monpifer:<official article alias>
```

This preserves the single-listing acquisition shape and avoids unnecessary network work.

## Deadline evidence rule

The current official HTML can contain a mismatch between the machine `datetime` attribute and the time visibly published to users. Example:

```html
<time datetime="2026-07-14T13:00:00Z">07/14/2026 - 16:00</time>
```

P0 freezes the visible `Last Date` text as authoritative business evidence and normalizes it to Myanmar local time (`+06:30`):

```text
07/14/2026 - 16:00
→ 2026-07-14T16:00:00+06:30
```

The machine `datetime` attribute must not silently overwrite the issuer-visible deadline.

## Attachment policy

Official PDF links under:

```text
/sites/default/files/tender_pdf/...
```

are preserved as metadata only.

```text
attachment_policy=METADATA_ONLY_NON_BLOCKING
fetch_in_primary_pipeline=false
```

The listing HTML is already complete enough for event/opportunity monitoring, so S25 does not trigger the S10 PDF extraction/runtime gate.

## Current-live isolated engine

Running the real S25 Registry/adapter/engine path against current public MONPIFER HTML with a temporary SQLite database produced:

```text
status=SUCCESS
baseline=true
listing_complete=true
discovered=10
items=10
tenders=10
details_attempted=0
details_succeeded=0
changed=10
signals_created=0
backlog_remaining=0
```

Persistence/acquisition:

```text
canonical TENDER=10
requests/attempts/evidence/processing=1/1/1/1
PDF requested_url count=0
SQLite quick_check=ok
```

Only one network call was made:

```text
https://www.monpifer.gov.mm/my/ministry-tenders
```

## Update semantics

Fixture regression proves that changing the visible deadline while keeping the same official article alias:

```text
07/14/2026 - 16:00
→ 07/15/2026 - 16:00
```

updates the same canonical item and emits one `UPDATED` signal after baseline. It does not create a duplicate NEW item.

## Verification

```text
targeted suite: 16/16 PASS
full CI-equivalent suite: 59/59 PASS
compileall: PASS
Registry JSON: PASS
shell syntax: PASS
git diff --check: PASS
Bangkok Direct HTTP 3/3: PASS
current-live isolated engine: PASS
```

## Production gate

Production is not complete until:

1. PR CI passes and the exact squash-merged SHA is deployed to Bangkok only;
2. timer is paused and the then-current nine-source state is frozen;
3. deployment itself changes no business counts;
4. reviewed `signalforge-refresh S25` succeeds;
5. first baseline creates the current audited listing records as `TENDER` and zero customer signals;
6. `details_attempted=0` and no detail URL is acquired;
7. exactly one S25 acquisition request/attempt/evidence/processing lifecycle is added;
8. PDF requested URL count remains zero;
9. S25 parse health is GREEN from `BUSINESS_PROCESSING`;
10. one manual source refresh maps to exactly one Worker SignalForge Run;
11. Beijing remains SignalForge-free and rejects `signalforge-refresh S25`;
12. Bangkok + Beijing Worker doctors pass;
13. timer returns to enabled/active/waiting and all ten sources are GREEN;
14. `browser_production_approved=false` remains unchanged;
15. no YCDC identity/locator migration, PDF/OCR runtime, Browser or unrelated capability is introduced by S25.
