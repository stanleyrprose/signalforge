# S47 Yangon Region Government — YCDC Mission Tenders

Date: 2026-09-16

## Business reason

SignalForge's primary mission is Myanmar government / SOE tender intelligence in engineering, construction/infrastructure, telecom/ICT infrastructure and energy.

A live coverage audit found a current Yangon City Development Committee tender on the official Yangon Region Government tender surface that was not present in any existing SignalForge source. Production searches for `HDPE`, `HRB-400`, `246.201`, `25000`, `Fogging`, and the YCDC issuer name returned zero matching canonical records.

Existing coverage did not contain this opportunity:

- S16 monitors the YCDC Engineering Department Building-detail surface and did not have the current procurement;
- S43 monitors the Yangon Region Ministry of Construction category and does not cover YCDC procurement posts.

This is therefore a real source-portfolio coverage gap, not a parser/read-layer gap in an existing source.

## Current acceptance tender

Official Yangon Region Government WordPress post, published 2026-09-15:

- issuer: Yangon City Development Committee (YCDC)
- tender-form sale starts: 2026-09-17
- final submission deadline: **2026-09-29 12:00 Myanmar time**
- mission-relevant construction materials:
  - HDPE pipe and fittings — 1 Lot
  - cement — 25,000 bags
  - HRB-400 rebar — 246.201 tons
  - sand / aggregate / chipping / crushed dust
- the same tender also contains water-treatment chemicals and a fogging machine; those are retained in full canonical scope but deliberately omitted from the mission-focused presentation summary.

The old Yangon construction parser incorrectly selected 2026-09-17 (the form-sale start) as the deadline. S47 therefore has a dedicated final-submission parser and does not reuse S43 deadline semantics.

## Source boundary

Source id: `S47`

Name: `Yangon Region Government — YCDC Mission Tenders`

Discovery:

`https://www.yangon.gov.mm/category/tenders/`

The generic Yangon Region tender category is reused only for discovery. A detail record is accepted into S47 only when:

1. the official detail body identifies YCDC; and
2. the detail contains explicit target-sector evidence for construction/infrastructure, engineering or telecom/ICT infrastructure.

This prevents S47 from canonicalizing:

- Ministry of Construction records already owned by S43;
- YESC or other agencies on the generic tender category;
- YCDC ordinary fuel / office / commodity procurement without target-sector content.

Full official scope is retained. `focus_scope_summary` is a presentation-safe mission subset.

## Read-layer improvements

Two generic read-layer fixes were required and are not S47 hard-coded routing exceptions:

1. parser-provided `focus_scope_summary` and `mission_sector_hint` now survive into the opportunity view;
2. supported canonical `relevance_categories` are honored by qualification with provenance `CANONICAL_RELEVANCE_CATEGORY` before keyword-derived categories are added.

The business digest also prevents one canonical opportunity from appearing both in `24h 新增/更新` and the later MEDIUM watchlist. Legacy count-only watchlist briefings retain their compatibility message.

## Production-backup onboarding replay

A consistent copy of the production SQLite database plus live Yangon Region listing/detail evidence was used for a two-run onboarding replay.

Run 1 — silent baseline:

- discovered: 10
- detail candidates: 10
- detail success: 4
- YCDC mission canonical created: 4
- customer Signals: 0

This is intentional baseline suppression.

Run 2 — normal actionable-baseline reconciliation:

- detail candidates: 0
- Signal created: 1
- Signal reason: `ACTIONABLE_BASELINE_RECONCILIATION`
- canonical: `yangon-ycdc-mission:3755`

Current result:

- tracked current opportunities: 17 → 18
- mission business opportunities: 9 → **10**
- S47 current opportunities: 1
- primary relevance: `CONSTRUCTION`
- priority: `MEDIUM`
- deadline: `2026-09-29T12:00:00+06:30`
- digest S47 occurrence count: 1
- digest length: ~2,869 / 4,096

Visible mission summary contains HDPE, cement and HRB-400; PACl, NaOCl and Fogging do not appear in the main summary.

## Portfolio decision

S47 starts as `STRATEGIC_WATCH`, not CORE. Its future value should be judged by mission-fit business yield, not raw canonical or Signal volume.
