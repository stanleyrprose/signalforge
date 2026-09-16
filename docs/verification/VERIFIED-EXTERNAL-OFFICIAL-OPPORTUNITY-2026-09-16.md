# Verified External Official Opportunity — 2026-09-16

## Problem

S01 Myanmar National Portal independently discovered a current MPT tender for Pobbathiri Exchange Office earthquake repair. The official MPT text PDF is hosted by the National Portal, while the live MPT tender page / S13 canonical surface does not contain the opportunity.

The previous state correctly opened an S13 RED coverage miss, but it left a business-semantics contradiction: the customer had already been shown a fully reviewed official tender while Assurance still treated business coverage as missing.

## Resolution contract

A new non-canonical business state is accepted:

`VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY`

It may count toward customer-facing business coverage only when:

- the document is hosted on an allowlisted official surface;
- the issuer's own document proves issuer identity;
- business scope is reviewed and proven;
- deadline/actionability is reviewed and proven;
- a retained/reviewed document SHA256 is recorded;
- `canonical_truth=false` remains explicit;
- `coverage_origin` and `target_source_id` are explicit.

The state does **not** create or mutate canonical items or Signals.

## MPT verification

Record:

- gap / reviewed identity: `S13:aa3cebae-2f59-5c3c-e840-640c99f0cb92`
- target issuer source: S13 / MPT
- discovery coverage origin: S01 / Myanmar National Portal
- official document SHA256: `3dd5dd18a2395ba1bb18bdc31c9fa9850a98aced98fb05b7453c4380d24c9eea`
- project: Pobbathiri Exchange Office earthquake damage repair
- sector: CONSTRUCTION
- deadline: 2026-09-29 14:00 Myanmar time
- tender submission window starts 09:30
- tender form sale closes 2026-09-24 16:30
- site survey: 2026-09-25

## Business read-model semantics

As of 2026-09-16 production data:

- canonical mission-fit opportunities: 8
- verified external official opportunities: 1
- total customer business opportunities: 9
- tracked canonical current opportunities: 17
- unresolved reviewed coverage gaps: 2 (S23 Construction)

The Business Digest renders the MPT item as:

`[S13 ← S01]`

and explicitly states that it is counted for business coverage but is not a canonical Signal.

## Assurance semantics

S01's live lead resolution treats the MPT lead as covered by `VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY`. The old RED miss is auto-resolved only when a current Assurance run independently sees that exact S01 lead and resolves it through the verified official record. Registry presence alone is insufficient to close a miss.

Issuer-page coverage debt remains visible in the S01 coverage details (`issuer_page_coverage_debt_retained=true`).

If S13 later canonicalizes the exact official URL, canonical coverage supersedes the external record and the external business count becomes zero for that item.
