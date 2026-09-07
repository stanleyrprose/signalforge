# S36 Department of Agriculture Procurement Announcements — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / ISOLATED LIVE PASS — PRODUCTION GATE PENDING

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
