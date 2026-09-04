# S28 Department of Fisheries Open Tenders — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRODUCTION
Result: PASS / PRODUCTION COMPLETE

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

## Production rollout closure

PR #38 passed GitHub `verify` and was squash-merged. The exact production application SHA is:

```text
7413a9da60a1b0c3bf82ac0b30f00fe625ca75a2
```

Immediately before S28 rollout, live Bangkok was already running the separately merged/deployed Mac-provider projection release:

```text
0a3e6156f2635fd9509738d3b6c0aa1d073f6c03
```

That release is the immediate S28 rollback target. Its live provider boundary was verified before pause:

```text
mac-mm-01 production_enabled=false
invocation_mode=manual_or_future_contract
remote_invocation=false
browser_production_approved=false
```

Thus the actual production transition for this rollout was `0a3e6156... -> 7413a9da...`; the Mac-provider projection was pre-existing production state, not an S28 side effect.

The controlled pre-deploy snapshot after timer pause was:

```text
canonical_items=116
signals=11
scheduler_runs=399
acquisition_requests=533
acquisition_attempts=533
evidence_envelopes=532
processing_records=532
failed_runs=1
recovery_backlog=0
Worker SignalForge Runs=549
timer=disabled / inactive
run-due service=inactive
active refresh=0
```

The single failed run remained the previously recovered S10 DICA `CONNECT_TIMEOUT`; all eleven existing sources were GREEN and backlog was zero.

Exact-SHA deployment succeeded:

```text
deployment=success
release=7413a9da60a1b0c3bf82ac0b30f00fe625ca75a2
previous=0a3e6156f2635fd9509738d3b6c0aa1d073f6c03
timer_preexisting=0
```

Deployment itself changed no business/acquisition counts. S28 appeared in the manifest as `NOT_INITIALIZED` with canonical/signals `0/0`, while the Mac provider remained locked (`production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`).

The first reviewed S28 baseline ran through `signalforge-refresh@S28.service`:

```text
worker_run_id=signalforge-20260904T162016Z-e786baa0
trigger_type=MANUAL
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

Persistence after baseline:

```text
canonical_items: 116 -> 124
signals: 11 -> 11
scheduler_runs: 399 -> 400
S28 requests/attempts/evidence/processing=1/1/1/1
S28 canonical_items=8
S28 signals=0
S28 PDF requested_url count=0
SQLite quick_check=ok
```

The eight production canonical rows exactly preserve issuer-visible identity/publication/deadline evidence, including the historical inconsistencies documented above. No source-side date was silently corrected.

Worker cardinality/correlation passed:

```text
Worker SignalForge Runs: 549 -> 550
latest manual run=signalforge-20260904T162016Z-e786baa0 / SUCCESS
S28 scheduler worker_run_id matches exactly
```

Topology/runtime gates passed:

```text
Bangkok workerctl doctor = PASS
Beijing workerctl doctor = PASS
Beijing /srv/signalforge = ABSENT
Beijing signalforge-refresh S28 = 126 / DENY: SignalForge is Bangkok-only
browser_production_approved=false
```

After timer resume, Persistent reconciliation created one normal Worker wrapper:

```text
signalforge-20260904T162128Z-eb642231
```

That wrapper processed four due source jobs:

```text
S13 / S20 / S21 / S22
```

All four were `SUCCESS`, `changed=0`, `signals=0`. S28 was not due and was not fetched again.

Final observed steady state:

```text
12/12 sources GREEN
overall=PASS / GREEN
canonical_items=124
signals=11
scheduler_runs=404
acquisition_requests=538
acquisition_attempts=538
evidence_envelopes=537
processing_records=537
failed_runs=1   # pre-existing recovered S10 timeout
recovery_backlog=0
Worker SignalForge Runs=551
timer=enabled / active
run-due service=inactive
browser_production_approved=false
```

No schema migration, PDF/OCR runtime, Browser, JSON-primary target, remote Provider invocation, Worker-runtime or Control-Plane capability was introduced by S28.

The S28 rollout itself was pinned to `7413a9da60a1b0c3bf82ac0b30f00fe625ca75a2`. A later, separately reviewed Manual Provider Bridge production verification intentionally superseded the application release with `d1f6d1773390767e73747df75e81383e4997f053`; S28 remained active/GREEN with its eight canonical items and zero S28 customer signals. That later release change is not an S28 side effect. Any docs-only closure SHA must not be redeployed merely to update facts.
