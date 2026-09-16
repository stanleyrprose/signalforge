# Business-aware coverage risk — 2026-09-16

## Goal

Coverage failures must be communicated in business terms without converting stale retained data into a false claim that no newer tender exists.

## S21 production case

Myanma Railways is a mandatory/core government infrastructure source. Its origin currently times out from Bangkok and Mac egress; browser A/B already proved this is not a browser-engine problem.

Production retained issuer records show:

- retained tender records: 45
- retained tenders still open as of 2026-09-16: 0
- latest retained tender publication date: 2026-09-01
- latest retained tender deadline: 2026-09-14
- last successful issuer acquisition: 2026-09-13

Therefore the correct business interpretation is:

> No retained/known Railways tender is currently open, but this does not prove that no new tender was published after the source became unreachable. The current risk is a future/new-publication discovery blind spot, not a confirmed current missed opportunity.

## Contract

`assurance_status().coverage_risks[]` now exposes retained tender context:

- `retained_tender_count`
- `retained_open_tender_count`
- `latest_retained_tender_publication_date`
- `latest_retained_tender_deadline`
- `retained_tender_context_as_of`
- `retained_tender_context_semantics=RETAINED_STATE_ONLY_NOT_CURRENT_COVERAGE_PROOF`

The digest renders these fields using explicit `留存记录中` wording and preserves the existing warning that coverage-not-proven is not the same as a confirmed miss.

No source routing, acquisition engine, canonical state, Signal, delivery policy, or Assurance PASS/FAIL policy changes.
