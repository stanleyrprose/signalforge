# S30 MOFA Procurement Invitations — Source Onboarding

Date (Asia/Yangon): 2026-09-06  
Phase: PRE-PRODUCTION  
Result: IMPLEMENTATION / TEST PASS — PRODUCTION GATE PENDING

## Source decision

S30 is assigned to the **Ministry of Foreign Affairs Procurement Invitations** issuer-original surface:

```text
landing/discovery = https://www.mofa.gov.mm/category/announcement/
role              = ACTIVE_SELECTIVE
engine            = direct_http
primary kind      = HTML
canonical         = mofa:<wordpress_post_id>
attachment        = METADATA_ONLY_NON_BLOCKING
```

The official Announcement category is preferred over the full homepage because it is smaller and still carries the current tender record. The category is mixed-content; selection is therefore title-stage and fail-closed rather than treating every announcement as procurement.

## Why MOFA was selected now

The current issuer page contains a genuinely fresh procurement opportunity published **2026-09-04**:

```text
နိုင်ငံခြားရေးဝန်ကြီးဌာနအတွက် အိတ်ဖွင့်တင်ဒါခေါ်ယူခြင်း
```

HTML states that FY2026-2027 goods are to be purchased in Myanmar kyat and invites open tender submissions. The stable WordPress post is `59800`.

Three other candidates were freshly audited before selecting MOFA:

- MOEA: Bangkok Direct HTTP is green, but current tender records are mostly title/date + attachment and mix tender outcome records; less attractive than MOFA's current event-level HTML.
- MCRD: Bangkok Direct HTTP is green and table business fields are strong, but no issuer-stable row identity is exposed; attachment paths are not unique enough to safely substitute as canonical identity.
- MOL/SSB: technically strong WordPress selective source, but the current page 1 contains ten evaluation/award-stage records and zero new invitations; historical page 2 proves the shape, but onboarding an immediately empty source is lower value than current MOFA.

No source-count target was used to justify S30.

## Bangkok transport audit

Actual production SignalForge fetcher from Bangkok:

```text
https://www.mofa.gov.mm/
3/3 PASS
217,722 bytes
~0.79-0.81 sec
same body SHA across all three samples

https://www.mofa.gov.mm/category/announcement/
3/3 PASS
118,564 bytes
~0.29-0.42 sec
same body SHA across all three samples
```

The guessed `/category/tender/` returns 404 and is not used.

No Browser, Mac Provider, TLS bypass, proxy fallback, JSON primary, OCR or new runtime capability is triggered.

## Current source shape

The Announcement category currently exposes ten recent posts. The selector returns exactly two procurement invitations:

```text
2026-09-04 -> current open tender -> post 59800
2026-06-23 -> office equipment/furniture, 7 lots -> post 56952
```

It excludes at least:

```text
2026-07-28 tender award result
job vacancy announcements
training/course announcements
other ministry notices
```

Opportunity tokens include open-tender / tender-invitation semantics. Award, technical-evaluation and result semantics have explicit exclusion priority.

## Stable identity and business evidence

### Current 2026-09-04 tender

```text
canonical_key    = mofa:59800
reference_no     = MOFA-POST-59800
reference_kind   = wordpress_post_id
publication_date = 2026-09-04
item_kind        = TENDER
deadline         = null
```

HTML business scope is sufficient for event-level monitoring. One official attachment is exposed:

```text
Tender-Announcement.pdf
https://www.mofa.gov.mm/wp-content/uploads/2026/09/Tender-Announcement.pdf
```

The PDF is metadata only and is not fetched by S30.

### Historical 2026-06-23 invitation

```text
canonical_key    = mofa:56952
publication_date = 2026-06-23
scope            = office equipment and furniture, 7 lots
```

Its issuer attachment is a JPG rather than PDF. S30 therefore treats official PDF/JPG/PNG attachments uniformly as **metadata only**. It does not OCR or infer business fields from an image.

## Epistemic boundary

```text
HTML title / publication / event scope = production evidence
WordPress post ID                      = canonical identity
attachment URL/name                    = metadata only
attachment content                     = not acquired / not claimed
deadline absent from HTML              = unknown, never inferred
```

The source intentionally does not claim the PDF/image contents.

## Implementation

New adapter module:

```text
signalforge/mofa.py
```

Adapter contract:

```text
mofa_tender
mofa-announcement-category-v1
mofa-wordpress-html-v1
mofa-tender-normalize-v1
mofa-wordpress-post-id-v1
```

Registry S30:

```text
ACTIVE_SELECTIVE
poll=1800s
baseline lookback=120d
baseline detail limit=10
delta detail limit=10
parse probe=7200s
first baseline signal=false
supplementary=[]
attachment fetch=false
```

## Test evidence

S30 targeted tests:

```text
5/5 PASS
```

They prove:

- category selection returns the two invitations and excludes award/job noise;
- category-structure disappearance fails closed;
- current detail uses stable post ID and PDF metadata only;
- older detail accepts issuer JPG metadata without OCR;
- first baseline is signal-free;
- PDF/JPG URLs are never fetched;
- low-frequency probe on changed same-post HTML yields exactly one `UPDATED`, not duplicate `NEW`.

Full repository suite after active-manifest fixture update:

```text
107/107 PASS
```

## Current-live isolated engine

Using the live MOFA category and live detail HTML against a temporary SQLite database:

```text
status            = SUCCESS
baseline          = true
discovered        = 2
candidates        = 2
fetched           = 2
details           = 2/2
items             = 2
tenders           = 2
changed           = 2
signals_created   = 0
backlog_remaining = 0
```

Persistence:

```text
mofa:59800 TENDER 2026-09-04 deadline=null
mofa:56952 TENDER 2026-06-23 deadline=null
lifecycle = 3/3/3/3
attachment acquisitions = 0
SQLite quick_check = ok
```

## Production gate

S30 may be promoted only after:

1. PR CI passes and the exact merged SHA is known;
2. Bangkok current release/counters are freshly frozen because parallel sessions may advance production;
3. timer is paused and no run/refresh is active;
4. exact merged SHA deploy produces zero business-state change;
5. one reviewed manual S30 baseline returns the live issuer result (currently 2 TENDER) with zero signals and zero attachment fetch;
6. S30 becomes GREEN and all pre-existing automated sources remain GREEN;
7. Worker run correlation is one manual source refresh -> one Worker operational run;
8. Beijing remains SignalForge-free and both Worker doctors pass;
9. Mac provider remains `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`;
10. timer resumes enabled/active and post-resume reconciliation is clean.

No additional runtime capability is authorized by S30.
