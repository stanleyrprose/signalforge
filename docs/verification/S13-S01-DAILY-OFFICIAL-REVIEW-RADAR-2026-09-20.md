# S13 / S01 Daily Official Review Radar — 2026-09-20

## Goal

Reduce the chance that a new MPT / MDDC opportunity published outside the MPT website tender pages remains invisible until the weekly Assurance run or manual inspection.

This change improves review visibility only. It does not promote an aggregator lead into canonical truth.

## Root cause

S13 direct discovery is not merely a parser problem.

The reviewed Pobbathiri Exchange Office earthquake-repair tender proves that MPT procurement publication can use multiple official surfaces:

1. ordinary MPT tender detail pages under `mpt.com.mm`;
2. official MPT / MDDC newspaper or tender documents hosted through Myanmar National Portal.

The Pobbathiri opportunity:

- was discovered by S01 Myanmar National Portal;
- was backed by a Portal-hosted official MPT text PDF;
- was not present in the MPT page sitemap;
- was not found through MPT site search for Pobbathiri / Exchange Office / earthquake-repair terms;
- has no corresponding MPT detail page in the issuer website evidence reviewed.

Therefore forcing S13 sitemap discovery to find this opportunity would encode a false assumption about issuer publication policy.

## MPT Tender Information landing-page recheck

Official landing page:

```text
https://mpt.com.mm/en/about-home/tenders/
```

The raw page contains CSS references to `tablepress-319`, but no tender table rows.

Mac Browser Plane cross-check:

### Lightpanda C1

- job: `afd78e1e-33c8-4549-bbb8-bd535ce34313`
- state: SUCCEEDED
- HTTP: 200
- rendered content: navigation/footer only; no tender rows

### Chrome C1

- job: `4320e9b0-5c29-4345-b8d9-f2ed6820d175`
- state: SUCCEEDED
- HTTP: 200
- rendered DOM:
  - `tablepress-319`: CSS references only
  - `<table`: 0
  - `Reference No`: 0
  - `Project Name`: 0
  - known tender names: 0
  - only tender-like link: the Tender Information page itself

The landing page is therefore not a usable current listing surface. Adding more browser capability would not recover missing rows.

TablePress authenticated REST is not accepted as a public production discovery contract.

## Existing S01 capability

S01 is already an Assurance-only official aggregator radar:

- bounded scan of Myanmar National Portal tender pages;
- mission filter for engineering, construction, telecom/ICT infrastructure and energy;
- target-source hinting;
- closing date is hint-only;
- `canonical_truth=false`;
- `aggregator_only=true`.

The Pobbathiri fixture already proves that S01 maps the Ministry of Digital Development and Communications / Myanma Posts and Telecommunications lead to `target_source_hint=S13`.

The source-hint logic was therefore not the missing capability.

## Visibility gap

Before this change:

```text
S01 fresh official lead
    ↓
unresolved_leads in Assurance supplemental coverage
    ↓
weekly Assurance state / JSON only
    ↓
manual inspection required
```

Business Digest calls `audit()`, not the weekly `run_assurance()`, so a new unresolved S01 lead could remain absent from the daily business output.

The weekly Assurance timer is not sufficiently fresh for this purpose.

## Daily read-only radar

Business Digest v6 now performs a fresh, bounded, read-only S01 snapshot when `audit_network=true`.

It reuses the existing aggregator reconciliation logic rather than creating a second interpretation path:

- canonical URL -> covered;
- strict canonical equivalence -> covered;
- reviewed verified external official opportunity -> covered;
- reviewed coverage gap -> confirmed gap;
- otherwise -> unresolved lead.

No Assurance run, DB row, canonical item, Signal, miss or manual promotion is created by this read-model call.

## Review-candidate gate

Only unresolved leads satisfying all of the following may be shown:

- `evidence_kind=NATIONAL_PORTAL_HOSTED_DOCUMENT`;
- `aggregator_only=true`;
- `canonical_truth=false`;
- non-empty `target_source_hint`;
- official Myanmar National Portal `/documents/` URL;
- mission sector is one of:
  - TELECOM_ICT_INFRA
  - CONSTRUCTION
  - ENERGY
  - ENGINEERING.

Candidates are sorted by closing-date hint, then target source and lead identity.

## Business Digest semantics

Structured fields:

- `official_review_candidate_count`
- `official_review_candidates`
- `official_review_radar_status`
- `official_review_radar_policy=FRESH_S01_AGGREGATOR_ONLY_NONCANONICAL_REVIEW_REQUIRED`

Telegram rendering:

```text
🕵️ 待核验官方线索
```

At most two rows are displayed.

Each row shows:

- official Portal agency;
- target source as `[target ← S01]`;
- title;
- `closing_date_hint` explicitly as a hint;
- exact Portal-hosted candidate-document link when it satisfies the reviewed host/path/length boundary, otherwise the short National Portal landing link.

The section explicitly states:

- not yet reviewed;
- closing date is hint-only;
- not counted in opportunity totals;
- not a canonical Signal.

All unresolved candidates remain available in the structured digest even though display is capped at two.

## Failure semantics

A daily radar failure must not fail the entire Business Digest.

When the S01 snapshot raises an acquisition/runtime error:

- digest remains deliverable;
- `official_review_radar_status=CHECK_FAILED`;
- candidate count is zero;
- Telegram shows a compact warning that external-official-lead completeness cannot be confirmed;
- the output must not claim that there are no new opportunities.

When `audit_network=false`, the read-only wrapper respects the offline contract and performs no network fetch.

## Production smoke

A Bangkok SQLite online backup was copied to Mac and used only for read-only reconciliation with the live S01 network surface.

SHA-256 of the transferred gzip matched on Bangkok and Mac.

Result:

```text
S01 status          PASS
official leads      7
covered             7
missing             0
unresolved          0
verified external   1
review candidates   0
```

The verified external item is the already reviewed Pobbathiri MPT opportunity.

No new unresolved candidate was present at smoke time.

Temporary Bangkok and Mac snapshot files were deleted after verification.

## Boundary

This change does not:

- change S13 from PARTIAL to PASS;
- claim MPT website discovery is complete;
- change S01 into a canonical source;
- trust National Portal closing dates as canonical deadlines;
- create automatic RED misses from unresolved leads;
- create canonical items or Signals;
- increment current-opportunity counts;
- change Source Registry source policy;
- change Telegram immediate-alert behavior;
- add a new database table;
- deploy Bangkok as part of the PR.
