# S36 Department of Agriculture Procurement Announcements — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRODUCTION
Result: PRODUCTION / GREEN — LIVE VERIFIED 2026-09-07

## Fresh source-audit decision

S36 was selected by business value and endpoint quality rather than source-ID order.

### Deferred in this audit

- **Department of Meteorology and Hydrology (DMH / `moezala.gov.mm`)** — Bangkok strict Direct HTTP is healthy, but current 2026 tender nodes are mostly event shells whose procurement specifications or deadlines remain in linked PDFs or images. The source did not justify opening a PDF/OCR gate merely to increase source count.
- **OAG** — current tender business fields remain image/scan based, so it stays outside the current HTML-first P0 boundary.

### Selected

**Department of Agriculture (DOA), Ministry of Agriculture, Livestock and Irrigation** exposes a stable issuer-original mixed announcement board:

```text
https://www.doa.gov.mm/doa/index.php?route=cms/category&path=22
```

Bangkok strict-HTTPS verification returned the page three times as:

```text
HTTP status = 200
media type  = text/html
bytes       = 78,597
```

No TLS bypass, Browser or alternate egress was required.

## Business shape

Each announcement is a stable HTML card with:

```text
article_id
visible article date
full announcement title
```

The title itself contains enough buyer/works scope to form an event without opening the scan/image detail.

Current 2026 examples on the issuer board:

```text
article 574 — Agricultural Institute (Pyinmana) multipurpose hall construction
article 560 — Desktop Computer i5, 45 sets
article 558 — construction works at Agricultural Institute (Pyinmana)
article 573 — laboratory Cylinder + HPLC (with PDA-Detector)
article 559 — agricultural-product quality inspection ISO Lab major renovation
```

All five carry visible listing publication date `2026-05-18`.

The current board also still exposes older buyer-side article `333` (`2024-06-20`, purchase of six types of foreign paper). S36 deliberately does not add a parser-time year cutoff: current issuer-board membership is evidence, and the first baseline suppresses customer signals for all pre-existing records.

## Selection policy

The board is mixed, so `တင်ဒါ` alone is insufficient.

A record must contain `တင်ဒါ` plus at least one buyer/implementation semantic such as:

```text
ဝယ်ယူ
တည်ဆောက်
ဆောက်လုပ်
ပြင်ဆင်
ဝန်ဆောင်မှု
ပစ္စည်း
လုပ်ငန်းအတွက်
```

Records are excluded when title semantics indicate:

```text
တင်ဒါအောင် / အောင်စာရင်း
ရောင်း
လေလံ
ငှား
award / result / winner
```

This keeps procurement/construction opportunities and rejects award/result or seller-side disposal semantics.

## Identity contract

DOA exposes a stable native numeric article ID in its own CMS locator:

```text
https://www.doa.gov.mm/doa/index.php?route=cms/article&path=22&article_id=560
```

Canonical identity is therefore:

```text
canonical_key = doa:<article_id>
reference_no  = DOA-ARTICLE-<article_id>
```

Examples:

```text
doa:574
doa:560
doa:558
doa:573
doa:559
doa:333
```

No title/date fingerprint is needed.

## Epistemic boundary

For S36:

```text
publication_date = visible listing article date
business scope    = issuer listing title
deadline          = null
```

The detail pages are reachable over Direct HTTP, but the supplementary notice content is primarily scan/image based. Therefore:

```text
deadline_evidence          = UNKNOWN_IN_IMAGE_SUPPLEMENT_NOT_PARSED
supplementary_image_policy = UNFETCHED_NON_BLOCKING
```

S36 is intentionally **event/scope detection**, not deadline-complete.

The live article `559` contains a malformed trailing quote in issuer HTML. The parser only strips isolated leading/trailing quote characters during title normalization; it does not rewrite business wording or identity.

## Implementation contract

```text
source_id                         = S36
adapter                           = doa_tender
role                              = ACTIVE_SELECTIVE
engine                            = direct_http
discovery                         = DOA mixed announcement board
listing_complete_business_records = true
poll_interval                     = 1800s
baseline_detail_limit             = 0
delta_detail_limit                = 0
canonical_key                     = issuer_article_id
primary                           = DIRECT_HTTP / HTML
supplementary                     = []
attachment/image mode             = EMBEDDED_IMAGE_UNPARSED_NON_BLOCKING
first baseline customer signal    = false
```

Parser versions:

```text
discovery     = doa-announcement-list-v1
detail        = not-applicable
normalizer    = doa-tender-normalize-v1
canonicalizer = doa-article-id-v1
```

## Local verification

```text
python -m pytest tests/test_doa.py tests/test_contract.py -q
8 passed

git diff --check
PASS
```

Coverage includes:

- stable issuer article-ID identity;
- visible listing publication dates;
- Desktop/HPLC/construction/renovation buyer semantics;
- award/result and sale/auction exclusions;
- generic `tender`-only false-positive protection;
- malformed trailing quote cleanup;
- structural drift fail-closed;
- valid mixed board with zero selected records;
- baseline signal suppression;
- unchanged second poll;
- zero detail/image acquisition.

## Bangkok isolated live-engine verification

The working tree was copied to a temporary Bangkok runtime with isolated SQLite/evidence roots. Production paths were untouched.

First real run:

```text
status            = SUCCESS
baseline          = true
listing_complete  = true
items             = 6
tenders           = 6
details_attempted = 0
changed           = 6
signals_created   = 0
```

Second real run:

```text
status            = SUCCESS
baseline          = false
listing_complete  = true
items             = 6
tenders           = 6
details_attempted = 0
changed           = 0
signals_created   = 0
```

Two-run persistence totals:

```text
requests          = 2
attempts          = 2
evidence          = 2
processing        = 2
canonical         = 6
signals           = 0
non-HTML evidence = 0
SQLite quick_check = ok
```

The live canonical set is exactly:

```text
doa:574  2026-05-18  multipurpose hall construction
doa:560  2026-05-18  Desktop Computer i5 x45
doa:558  2026-05-18  construction works
doa:573  2026-05-18  Cylinder + HPLC (PDA-Detector)
doa:559  2026-05-18  ISO Lab major renovation
doa:333  2024-06-20  six types of foreign paper procurement
```

Every deadline is `null` by design. The second run again fetched only the announcement listing.

## Frozen boundaries

S36 adds no:

- detail-page acquisition in production;
- embedded-image fetch or OCR;
- PDF acquisition/parsing;
- Browser/Crawlee;
- TLS bypass;
- SignalForge→Mac remote invocation;
- schema migration;
- new Worker capability.

## Production gate

Promote only after feature PR + CI PASS, exact merged-SHA Bangkok deployment with scheduler timer paused, reviewed zero-signal S36 baseline, production EvidenceEnvelope/Worker correlation, Bangkok/Beijing doctor and Bangkok-only verification, frozen Mac-provider verification, timer resume and all-source GREEN closure.


## Production closure — 2026-09-07

Exact production application release:

```text
1561d6f5e53026b8f651e1aa40d9e52a3f6ee541
```

Previous application-code rollback target:

```text
5ad60eabc2a86235db413c37c49e4bbe91378f95
```

### Pre-deploy freeze

Immediately before rollout the scheduler was idle, so the timer was disabled without interrupting a Worker Run. Frozen state:

```text
automated_sources     = 20 / 20 GREEN
canonical_items       = 165
signals               = 11
scheduler_runs        = 1599
acquisition_requests  = 1970
acquisition_attempts  = 1970
evidence_envelopes    = 1965
processing_records    = 1967
failed_runs           = 5
recovery_backlog      = 0
timer                 = disabled / inactive
run-due               = inactive
active refresh units  = 0
```

Deploying `1561d6f...` changed none of these counters. All twenty existing sources remained GREEN; only new S36 appeared as `baseline=0 / SOURCE_FRESHNESS_LAG / RED`, which is the expected pre-baseline state.

### Reviewed production baseline

```text
source_id             = S36
trigger_kind          = MANUAL
baseline              = 1
status                = SUCCESS
items_parsed          = 6
tenders_parsed        = 6
details_attempted     = 0
details_succeeded     = 0
changed               = 6
signals_created       = 0
backlog_remaining     = 0
worker_run_id         = signalforge-20260907T134030Z-0b687ac4
```

Baseline moved only the expected counters:

```text
canonical_items       165 -> 171
scheduler_runs        1599 -> 1600
requests/attempts     1970 -> 1971
evidence_envelopes    1965 -> 1966
processing_records    1967 -> 1968
signals               11 -> 11
failed_runs           5 -> 5
recovery_backlog      0 -> 0
```

### Production evidence boundary

S36 production baseline created exactly one EvidenceEnvelope:

```text
requested_url = https://www.doa.gov.mm/doa/index.php?route=cms/category&path=22
HTTP status   = 200
media type    = text/html
artifact      = 78,597 bytes
non-HTML      = 0
```

No detail page, image, PDF, OCR or Browser acquisition was performed. SignalForge DB `quick_check=ok`.

Production canonical rows:

```text
doa:574  publication=2026-05-18  deadline=null  multipurpose hall construction
doa:560  publication=2026-05-18  deadline=null  Desktop Computer i5 x45
doa:558  publication=2026-05-18  deadline=null  construction works
doa:573  publication=2026-05-18  deadline=null  Cylinder + HPLC (PDA-Detector)
doa:559  publication=2026-05-18  deadline=null  ISO Lab major renovation
doa:333  publication=2024-06-20  deadline=null  six types of foreign paper procurement
```

The malformed issuer trailing quote on article `559` is absent from both DB title and payload after normalization.

### Worker / fleet / provider verification

Worker DB contains exactly one matching operational run:

```text
run_id       = signalforge-20260907T134030Z-0b687ac4
application  = signalforge
process_user = signalforge
status       = SUCCESS
exit_code    = 0
```

Additional boundaries:

```text
Worker DB quick_check           = ok
Bangkok workerctl doctor        = PASS
Beijing workerctl doctor        = PASS
Beijing /srv/signalforge        = ABSENT
Beijing signalforge-refresh S36 = 126 / DENY: SignalForge is Bangkok-only
Mac production_enabled          = false
Mac remote_invocation           = false
browser_production_approved     = false
Mac invocation_mode             = manual_or_future_contract
canonical_node                  = bangkok
```

Cumulative `failed_runs` remained `5`; S36 introduced no failure and recovery backlog stayed zero.

### Timer resume and final state

`signalforge-resume` re-enabled the timer. In this rollout, several existing sources were already due, so resume immediately launched one normal `run-due` service invocation. It was allowed to finish. The invocation produced no new canonical item, signal, failed run or backlog.

Final observed state after that natural reconciliation:

```text
application_release   = 1561d6f5e53026b8f651e1aa40d9e52a3f6ee541
automated_sources     = 21 / 21 GREEN
signalforge_health    = GREEN
canonical_items       = 171
signals               = 11
scheduler_runs        = 1603
acquisition_requests  = 1976
acquisition_attempts  = 1976
evidence_envelopes    = 1971
processing_records    = 1973
failed_runs           = 5 (historical / recovered)
recovery_backlog      = 0
timer                 = enabled / active
run-due               = inactive
```

**Gate result: S36 is PRODUCTION / GREEN.**
