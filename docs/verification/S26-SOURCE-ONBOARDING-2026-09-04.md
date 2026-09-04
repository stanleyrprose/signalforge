# S26 DOMS Medical Procurement Opportunities — Source Onboarding

Date (Asia/Yangon): 2026-09-04
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / LIVE AUDIT PASS

## Decision

Allocate `S26` to the Department of Medical Services (DOMS), Ministry of Health, as an issuer-original `ACTIVE_SELECTIVE` medical-procurement opportunity source.

Production discovery uses the official WordPress tender category HTML:

```text
https://www.doms.gov.mm/category/tender/
```

The source intentionally remains inside the frozen v1.5 HTML-first acquisition contract:

```text
category HTML
-> stable WordPress post id + title + issuer permalink
-> opportunity-stage classifier
-> selected detail HTML only
-> TENDER canonical
-> official PDF links as metadata only
```

No schema migration, JSON primary target, PDF extraction, OCR, Browser or remote Provider capability is introduced.

## Candidate selection context

Fresh source comparison before S26 included several issuer-original candidates.

- Ministry of Industry: commercially strong HTML procurement notices, but Bangkok production fetcher failed DNS 3/3; fail closed.
- Ministry of Energy: active and commercially strong, but current detail pages carry business content in embedded official PDFs; HTML exposes mainly title/date. Deferred until PDF runtime value justifies expansion.
- Department of Fisheries: Direct HTTP and listing-complete HTML are viable, but lower current business value/update intensity than DOMS.
- DOMS: Direct HTTP is stable, procurement value is high, stable WordPress post IDs are exposed, and selected opportunity detail HTML/attachment labels carry usable medical-procurement scope without reading PDFs.

DOMS therefore offers the best current business-value-to-complexity ratio while preserving the existing engine.

## Bangkok transport audit

Using the actual Bangkok SignalForge production fetcher:

```text
DOMS tender category HTML: 3/3 SUCCESS
bytes ~=205 KB
elapsed ~=0.67s to 3.71s during sampled run

representative DOMS detail HTML: 3/3 SUCCESS
bytes ~=197 KB
elapsed ~=0.07s to 0.12s during earlier sample
```

Direct HTTP is sufficient. Browser gate is not triggered.

## WordPress identity audit

The tender category emits stable issuer-owned article IDs directly in HTML:

```html
<article id="post-12634" class="... category-tender ...">
<article id="post-12491" class="... category-tender ...">
```

Representative detail HTML independently exposes the same WordPress identity, for example:

```text
postid-12491
wp-json post id=12491
article id=post-12491
```

Canonical identity is therefore:

```text
doms:<wordpress_post_id>
```

Publication date is read from the issuer permalink path (`/YYYY/MM/DD/.../`), not invented from local collection time.

## Why the WordPress REST API is not the production primary

Fresh audit proved that DOMS's public WordPress REST API is technically strong:

```text
/wp-json/wp/v2/posts/12491            -> 3/3 PASS
/wp-json/wp/v2/categories?per_page=100 -> category 38 = tender
/wp-json/wp/v2/posts?categories=38...  -> 3/3 PASS
```

However the frozen v1.5 acquisition contract explicitly requires P0 primary target kind `HTML`. Promoting JSON as a new primary target would be a contract expansion unrelated to the source's actual necessity.

Therefore S26 deliberately uses official HTML even though REST exists. This is an engineering-boundary decision, not a discovery gap.

## Current category shape / selection policy

The current first tender-category page exposes ten recent tender-workflow posts and spans roughly 2026-07-03 through 2026-09-03. The page mixes opportunity creation with later procurement stages.

Current examples include:

```text
12725  2026-09-03  7DMS opening/evaluation meeting                 -> DROP
12717  2026-08-31  6DMS tender winner list                         -> DROP
12686  2026-08-20  7DMS Envelope-B scrutiny meeting                -> DROP
12656  2026-08-12  5DMS supplementary winner list                  -> DROP
12634  2026-08-10  Tender No. 7DMS/2026-2027(L)                    -> SELECT
12589  2026-07-29  3DMS/5DMS winner list                           -> DROP
12510  2026-07-10  3DMS winner list                                -> DROP
12498  2026-07-10  4DMS lab reagents winner list                   -> DROP
12491  2026-07-09  Open Tender — CT/MRI Preventive Maintenance     -> SELECT
12518  2026-07-03  3DMS winner list                                -> DROP
```

S26 P0 classifier fails closed on procurement-stage markers such as winner/result, scrutiny/evaluation, meeting/opening and Envelope-stage notices. It selects only opportunity-origin records with explicit open-tender wording or a clean DMS tender reference not carrying those exclusion stages.

The current first page therefore yields exactly two selected opportunities.

## Discovery-window decision

P0 monitors only the official first category page.

The current ten-post window already spans about two months of issuer activity, while S26 polls every 30 minutes. There is no production evidence that ten newer workflow posts could displace an unseen new opportunity within one poll/recovery window.

Pagination is therefore not added speculatively. It becomes an evidence-triggered follow-up only if real history shows displacement risk.

## Current selected business records

### WordPress post 12634

```text
reference = 7DMS/2026-2027(L)
publication_date = 2026-08-10
canonical = doms:12634
```

The HTML detail carries official attachment labels that directly expose procurement scope, including:

```text
Oncology Medicine
Nuclear Medicine (Reagent)
Antibiotics
Uro Surgery
Radiation Therapy
Renal Medical
Ortho
Neuro Surgery
Maxillo Facial Surgery
Neuro Medicine
Haematology
GI
EYE
ENT
Dental
Cardiac Surgery
Cardiac Medicine (Paed)
Cardiac Medicine (Adult)
```

The parser deduplicates repeated `Download` anchors by official attachment URL and prefers the meaningful issuer label.

### WordPress post 12491

```text
reference = DOMS-POST-12491
reference_no_kind = wordpress_post_id
publication_date = 2026-07-09
canonical = doms:12491
```

HTML body itself states FY2026-2027 and the business scope: preventive maintenance for CT (Computed Tomography) and MRI (Magnetic Resonance Imaging) equipment used across DOMS hospitals.

A synthetic tender number is not invented when the issuer does not publish one in HTML.

## Deadline boundary

The current selected detail HTML does not provide a reliable tender closing deadline.

Therefore:

```text
deadline = unknown / null
deadline_evidence = UNKNOWN_NOT_IN_HTML_TEXT
```

S26 does not infer a deadline from images, PDF content, chronology or later procurement-stage notices.

## Attachment boundary

Selected 7DMS/5DMS records expose official attachments under:

```text
https://www.doms.gov.mm/wp-content/uploads/...
```

S26 preserves these as metadata only.

```text
attachment_policy = METADATA_ONLY_NON_BLOCKING
fetch_in_primary_pipeline = false
```

External/non-DOMS PDF links are rejected by the parser. PDFs are never requested by S26 P0.

## Same-post update semantics

A WordPress post may be edited while keeping the same permalink date and post ID. S26 therefore marks its parser output as tender-only discovery and uses the existing bounded parse-health probe to revisit the newest confirmed opportunity at the configured interval.

Fixture regression proves:

```text
same post_id=12634
same canonical=doms:12634
changed HTML scope/attachment label
-> one UPDATED signal after baseline
-> no duplicate NEW item
```

No engine change was required.

## Current-live isolated engine

Running the real S26 Registry/adapter/engine path against current public DOMS HTML with a temporary SQLite database produced:

```text
status=SUCCESS
baseline=true
discovered=2
candidates=2
fetched=2
items=2
tenders=2
details_attempted=2
details_succeeded=2
changed=2
signals_created=0
backlog_remaining=0
```

Persistence/acquisition:

```text
canonical TENDER=2
requests/attempts/evidence/processing=3/3/3/3
PDF requested_url count=0
SQLite quick_check=ok
```

Requested URLs were exactly:

```text
https://www.doms.gov.mm/category/tender/
https://www.doms.gov.mm/2026/08/10/<7DMS issuer slug>/
https://www.doms.gov.mm/2026/07/09/<open-tender issuer slug>/
```

## Verification

```text
targeted suite: 14/14 PASS
full CI-equivalent suite: 64/64 PASS
compileall: PASS
Registry JSON: PASS
shell syntax: PASS
current-live parser: PASS
current-live isolated engine: PASS
Bangkok Direct HTTP: PASS
```

## Production gate

Production remains incomplete until:

1. GitHub PR CI passes and the exact squash-merged SHA is deployed to Bangkok only;
2. the then-current ten-source production state is frozen after a controlled timer pause;
3. deployment itself changes no business counts;
4. reviewed `signalforge-refresh S26` succeeds;
5. baseline reflects the actual current selected opportunity count (expected 2 if issuer state is unchanged) and creates zero customer signals;
6. detail fetch count equals selected opportunity count and excludes award/evaluation posts;
7. no PDF URL is requested;
8. S26 parse health is GREEN;
9. one manual source refresh maps to exactly one Worker SignalForge Run;
10. Beijing remains SignalForge-free and rejects `signalforge-refresh S26`;
11. Bangkok + Beijing Worker doctors pass;
12. timer returns to enabled/active/waiting and all eleven sources are GREEN;
13. `browser_production_approved=false` remains unchanged;
14. no JSON-primary contract, schema migration, PDF/OCR runtime, Browser or unrelated capability is introduced.
