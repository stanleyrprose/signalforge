# S28 Department of Fisheries Open Tenders — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / LIVE AUDIT PASS

## Decision

Allocate `S28` to the Department of Fisheries (DOF), Ministry of Agriculture, Livestock and Irrigation, as an issuer-original `ACTIVE_PRIMARY` tender source.

Production discovery uses the official tender listing:

```text
https://www.dof.gov.mm/index.php/my/tender
```

Source shape:

```text
one official listing HTML
-> one card per tender
-> issuer tender alias + publication datetime + scope + tender-form sale date + closing date
-> complete TENDER canonical item
-> no synthetic detail stage
```

No schema migration, PDF extraction, OCR, Browser, JSON-primary target, Worker-runtime or Control-Plane capability is introduced.

## Candidate selection context

Fresh audit for the twelfth production source compared current issuer-original public surfaces rather than allocating by source-ID order.

- Ministry of Education tender announcements: Bangkok Direct HTTP succeeds, and Drupal node identity is stable, but current tender detail node `4059` carries the business notice as an image; HTML exposes only title/type. It therefore requires image/OCR for useful business facts and is not onboarded in this slice.
- Ministry of Hotels/Tourism and Culture: the 2026-08-27 Swiss Challenge notice is commercially interesting and current, but the tender notice is a JPG attachment. It remains image/OCR-gated.
- S27 Ministry of Border Affairs remains separately deferred because Bangkok strict TLS is RED; the ID is not reused.
- DOF: Bangkok Direct HTTP is stable, the official listing HTML is complete enough to form the tender business record without detail/PDF/OCR, and the page includes construction, laboratory/equipment, website-security/National-Single-Window and machinery procurement examples.

S28 therefore gives the best current value-to-complexity ratio without expanding the runtime.

## Bangkok transport gate

Using the actual Bangkok SignalForge production fetcher against the DOF listing:

```text
attempt 1: SUCCESS / 67481 bytes / ~0.386s
attempt 2: SUCCESS / 67481 bytes / ~0.086s
attempt 3: SUCCESS / 67481 bytes / ~0.124s
```

The page contains dynamic theme/view identifiers, so whole-body hash changes are not treated as business change evidence; parser/canonical material fields determine business updates.

Direct HTTP is sufficient. Browser gate is not triggered.

For comparison, the Ministry of Education tender category also passed Bangkok Direct HTTP 3/3, but current detail business content is image-based. Transport success alone is therefore not sufficient for source promotion.

## Official listing identity and business fields

Each DOF card exposes an issuer-owned detail alias such as:

```text
/my/tender/2026-05-21t1546220630
/my/tender/2026-04-02t1507400630
/my/tender/2026-04-02t1507400630-0
/my/tender/2026-04-02t1507400630-1
```

The alias is stable enough to act as the issuer record identity for P0, analogous to the already-proven issuer-owned Drupal alias approach used by S25.

Canonical identity:

```text
dof:<issuer_tender_alias>
```

Example:

```text
dof:2026-05-21t1546220630
```

The card also exposes:

- HTML `<time datetime>` publication timestamp;
- business scope/description;
- visible tender-form sale date;
- visible tender closing date.

No detail request is necessary to construct the canonical item.

## Current issuer-visible records

Current live parser returns eight complete tender cards from the official listing.

The four 2026 rows currently include:

```text
2026-05-21
scope: second tender for 10 construction works
tender-form sale date: 2026-05-21
closing date: 2026-06-01

2026-04-02
scope: construction works
tender-form sale date: 2026-04-20
closing date: 2026-04-28

2026-04-02
scope: construction works
tender-form sale date: 2026-04-20
closing date: 2026-04-28

2026-04-02
scope: laboratory items, office equipment/furniture, Website security and National Single Window system
tender-form sale date: 2026-04-06
closing date: 2026-04-24
```

Older visible rows cover machinery, nursery construction, diesel engines/dredger pumps and laboratory/office equipment.

Because listing-complete engine semantics do not apply `baseline_lookback_days` filtering inside the parser, P0 deliberately takes the entire issuer-visible listing as one silent initial baseline. It does not inject a hidden wall-clock filter into the adapter.

## Historical issuer inconsistency boundary

The official page contains historical inconsistencies. Examples observed during audit include:

```text
alias contains 2025-10-01
visible/HTML publication datetime = 2025-09-30

historical 2024 card publication = 2024-08-19
visible sale date = 2024-04-08
visible closing date = 2024-04-30
```

S28 does not attempt to repair or reinterpret these issuer facts.

Evidence policy is:

```text
publication_date      = HTML <time datetime> date
tender_form_sale_date = visible sale-date text
deadline              = visible closing-date text
identity              = issuer tender alias
```

A mismatch among those fields remains an issuer-data fact, not a parser error.

## Deadline/date parser boundary

Myanmar digits are normalized only for deterministic calendar parsing. Parsed dates are validated against the real Gregorian calendar.

Example:

```text
တင်ဒါနောက်ဆုံးလက်ခံမည့်နေ့ရက် ၁-၆-၂၀၂၆
-> deadline = 2026-06-01
```

No closing time is present on the listing, so S28 stores a date rather than inventing an end-of-day timestamp.

## Detail / attachment boundary

Fresh detail audit of the latest DOF record confirms an underlying stable Drupal node (`nid=282`), but the listing already contains the business fields needed for P0.

Fetching every detail solely to recover a numeric node ID would add N requests without improving the current business signal. S28 therefore intentionally uses the issuer listing alias as identity and does not create a synthetic detail stage.

The primary pipeline requests no PDF or image attachment.

```text
attachment_policy = METADATA_ONLY_NON_BLOCKING
current listing attachment requirement = none
fetch_in_primary_pipeline = false
```

## Same-alias update semantics

Fixture regression proves:

```text
same issuer alias
same canonical key
visible closing date changes
-> one UPDATED signal after baseline
-> no duplicate NEW item
```

The business hash is based on canonical material fields, not the dynamic Drupal view DOM identifier.

## Current-live isolated engine

Running the real S28 Registry/adapter/engine path against current public DOF HTML with a temporary SQLite database produced:

```text
status=SUCCESS
baseline=true
listing_complete=true
discovered=8
items=8
tenders=8
details_attempted=0
details_succeeded=0
changed=8
signals_created=0
backlog_remaining=0
```

Persistence/acquisition:

```text
canonical TENDER=8
requests/attempts/evidence/processing=1/1/1/1
PDF requested_url count=0
SQLite quick_check=ok
```

Current publication-date range represented by the issuer-visible page is `2024-08-19` through `2026-05-21`.

## Verification

```text
targeted suite: 12/12 PASS
full CI-equivalent suite: 67/67 PASS
current-live parser: PASS (8 records)
current-live isolated engine: PASS
Bangkok Direct HTTP: 3/3 PASS
Registry JSON: PASS
```

## Production gate

Production remains incomplete until:

1. GitHub PR CI passes and the exact squash-merged SHA is deployed to Bangkok only;
2. the then-current eleven-source state is frozen under a controlled timer pause;
3. deployment itself changes no business/acquisition counts;
4. reviewed `signalforge-refresh S28` succeeds;
5. baseline reflects the actual issuer-visible row count (expected 8 if the page is unchanged) and creates zero customer signals;
6. S28 persists exactly one discovery acquisition lifecycle and zero detail/PDF requests;
7. S28 parse health is GREEN using `BUSINESS_PROCESSING`;
8. one manual S28 refresh maps to exactly one Worker SignalForge Run;
9. Beijing remains SignalForge-free and rejects `signalforge-refresh S28`;
10. Bangkok + Beijing Worker doctors pass;
11. timer returns to enabled/active/waiting and all twelve sources are GREEN;
12. `browser_production_approved=false` remains unchanged;
13. no schema/OCR/PDF/Browser/JSON-primary/runtime capability is introduced.
