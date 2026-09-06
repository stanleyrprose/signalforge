# S30 Yangon Region Government Tenders — Source Onboarding

Date (Asia/Yangon): 2026-09-06
Phase: PRE-PRODUCTION
Result: PASS / IMPLEMENTATION READY

## Decision

Onboard the official Yangon Region Government tender category as S30 using the existing Direct-HTTP category -> detail HTML lifecycle.

S30 requires no new Worker, schema, PDF, OCR or Browser capability. It is intentionally `ACTIVE_SELECTIVE` because P0 monitors only the current category page (10 posts). Pagination remains evidence-triggered rather than speculative.

## Why this source

Fresh candidate comparison rejected simpler-looking alternatives for concrete reasons:

- S27 Ministry of Border Affairs remains Bangkok `RED-TLS`: both `moba.gov.mm` and `www.moba.gov.mm` failed strict certificate verification 3/3; no TLS bypass is allowed.
- Ministry of Ethnic Affairs tender details resolve to text-native PDFs. They contain useful scope/deadline fields, but making scheduled PDF acquisition a new production dependency for one source is not justified yet.
- Yangon Region Government is official, Direct-HTTP reachable, has stable WordPress IDs and publishes structured HTML business fields for YCDC, YESC, Roads, Environmental Conservation and other regional agencies.

## Fresh transport audit

Bangkok actual SignalForge fetcher:

```text
https://www.yangon.gov.mm/category/tenders/
3/3 PASS
~197 KB
~1.0 s

representative YESC detail
3/3 PASS
~203-208 KB
~0.95-1.07 s
```

No Browser gate was triggered.

## Current source shape

The current category page exposes 10 WordPress tender articles. Each article has:

```text
<article id="post-<stable-id>" ... category-tenders>
entry-title + official permalink
hidden .updated timestamp
visible opening date
visible closing date
```

Current first-page IDs during audit:

```text
3742  YCDC
3729  YCDC
3722  YCDC
3718  YESC
3713  YCDC
3705  YESC
3701  YESC
3696  YCDC
3693  Environmental Conservation Department, Yangon Region
3691  Roads Department, Yangon Region
```

All 10 current titles are opportunity-stage tender invitations; no award/result record was selected.

Representative detail `postid-3718` proves stable identity exists both in category and detail HTML. Its structured HTML contains:

```text
tender number(s)
department / issuing agency
business type
tender form sale date
closing date
estimated value field
work location
full entry-content scope
```

Example YESC metadata:

```text
publication      2026-07-20
sale date         2026-07-21
closing date      2026-08-04
references        10(T)/YESC/... and 11(T)/YESC/...
scope             power-line relocation materials + UPS procurement
```

The WordPress detail visible post-date (`20 Jul`) matches hidden `.updated=2026-07-20T18:13:08+06:30`. S30 requires this day/month consistency before accepting the full publication date; a mismatched hidden timestamp fails closed.

## Identity and business granularity

Canonical identity:

```text
yangon-region:<wordpress_post_id>
```

One WordPress post remains one canonical tender notice even if its body contains multiple lots/tender numbers. P0 does not manufacture lot-level identities that the publisher does not expose as stable records.

If the structured `တင်ဒါအမှတ်` field contains a real issuer reference, it is preserved verbatim. Empty/generic values such as `-` or `ဖော်ပြပါအတိုင်း` are not treated as tender numbers and fall back to:

```text
YRG-POST-<post_id>
```

## Publisher / overlap policy

The publisher is the official Yangon Region Government portal, but the underlying issuing agency varies by post. Canonical payload therefore keeps both:

```text
publisher = Yangon Region Government
issuer/department = YCDC / YESC / Roads / Environmental Conservation / ...
publisher_scope = REGIONAL_MULTI_AGENCY
```

This is materially different from S01/S04: the regional publisher exposes stable record identity and complete structured business fields rather than contradictory/partial aggregator metadata.

However, future direct YCDC/YESC onboarding must not silently duplicate S30. Registry freezes:

```text
cross_source_overlap_policy = REVIEW_BEFORE_DIRECT_AGENCY_ONBOARDING
```

S16 YCDC-direct remains deferred for its randomized Laravel locator problem and now additionally requires explicit equivalence/exclusion against S30 before activation.

## Coverage policy

P0 uses only:

```text
https://www.yangon.gov.mm/category/tenders/
```

Current page size is 10 posts. At a 30-minute poll cadence this is sufficient for current monitoring absent evidence that more than 10 new tender posts can displace unseen records between collections. Pagination is therefore:

```text
DEFER_UNTIL_REAL_DISPLACEMENT_RISK
```

This is `ACTIVE_SELECTIVE`, not a claim of exhaustive historical backfill.

## Current opportunity age

At audit time (2026-09-06), the newest visible record `post-3742` closed on 2026-09-01. Therefore the initial production baseline represents historical/current-page state, not a currently open opportunity set. First baseline must remain signal-free.

## Implementation

New adapter:

```text
yangon_region_tender
```

Versions:

```text
discovery_parser = yangon-region-wordpress-category-v1
detail_parser    = yangon-region-structured-html-v1
normalizer       = yangon-region-tender-normalize-v1
canonicalizer    = yangon-region-wordpress-post-id-v1
```

The parser scopes business extraction to the tender `<article>`, `.wwm-tender-field` and `.entry-content`; navigation/sidebar labels are excluded.

## Verification

Targeted S30 + contract tests:

```text
10/10 PASS
```

They prove:

- stable WordPress category discovery;
- result-stage title exclusion;
- structured business field extraction;
- visible post-date / updated timestamp cross-check;
- real multi-reference preservation;
- missing reference fallback to post ID;
- initial baseline is signal-free;
- same-post material change becomes one `UPDATED` signal through bounded health probe;
- no PDF/image request occurs.

Full repository suite after implementation:

```text
108/108 PASS
```

Current-live isolated engine using the real website:

```text
baseline=true
status=SUCCESS
discovered=10
candidates=10
fetched=10
items=10
tenders=10
details=10/10
changed=10
signals_created=0
backlog=0

requests/attempts/evidence/processing=11/11/11/11
attachment fetch=0
SQLite quick_check=ok
```

The 10 current canonical keys are `yangon-region:3742` through the selected current-page post IDs above. Live recheck also proved post 3701's generic `ဖော်ပြပါအတိုင်း` reference is rejected and correctly falls back to `YRG-POST-3701`.

## Production gate

S30 is implementation-ready but not production-complete until:

1. PR CI passes and exact merged SHA is identified;
2. Bangkok live release is re-read immediately before rollout to avoid parallel-release downgrade;
3. timer is paused and current business/Worker counters frozen;
4. exact SHA deploy causes zero business-state change before baseline;
5. one reviewed S30 baseline produces the then-current first-page tender set with zero customer signal;
6. S30 acquisition lifecycle contains only category + selected detail HTML, with zero PDF/image fetch;
7. canonical identity remains WordPress post ID and generic reference placeholders do not become business IDs;
8. Worker cardinality/correlation passes;
9. Beijing remains SignalForge-free and both Worker doctors pass;
10. timer resumes and all automated sources return GREEN.
