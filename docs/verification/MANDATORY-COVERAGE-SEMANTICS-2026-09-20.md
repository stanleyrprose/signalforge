# Mandatory Coverage Semantics Closure — 2026-09-20

## Problem

The latest Bangkok Assurance run collapsed two materially different mandatory-coverage conditions into one generic review reason:

- S13 / MPT = PARTIAL
- S21 / Myanma Railways = CHECK_FAILED

Both contributed to `MANDATORY_COVERAGE_NOT_FULLY_PROVEN`, even though their evidence states were different.

## Production evidence

Latest reviewed Bangkok run:

- assurance_run_id: `7b9025d2-a8e5-426f-b068-1d7b37ed344b`
- observed_at: `2026-09-19T08:28:52.112399Z`
- mandatory sources: 7
- direct PASS: 5
- PARTIAL: 1 (S13)
- CHECK_FAILED: 1 (S21)
- confirmed GAP: 0

### S13 / MPT

S13 remains `PARTIAL` because issuer sitemap discovery did not expose a reviewed MPT opportunity.

The opportunity itself was recovered through reviewed external official evidence:

- `issuer_page_coverage_debt_retained = true`
- `verified_external_recovery_count = 1`
- `risk_kind = ISSUER_DISCOVERY_PARTIAL`
- no unresolved missing candidate is recorded for that reviewed recovery

This means business coverage for the known opportunity is accounted for, while direct issuer discovery completeness is still not proven.

The source therefore must remain `PARTIAL`; reviewed external recovery must not rewrite it to `PASS`.

### S21 / Myanma Railways

The latest independent coverage check is `CHECK_FAILED`.

Fresh runtime verification on 2026-09-20:

- Mac -> `https://www.railways.gov.mm/category/tender/`: TCP/443 connect timeout
- Mac -> `https://www.railways.gov.mm/tenders/`: TCP/443 connect timeout
- Bangkok -> both issuer URLs: TCP/443 connect timeout

No reliable current official synchronization surface was identified. Search-index evidence is not accepted as proof of issuer completeness.

S21 therefore remains unverified / UNKNOWN and must not be converted to PASS.

## Semantic fix

Coverage status and business recovery are now kept as separate dimensions.

### Direct coverage

`mandatory_coverage_proven` remains strict:

- only `PASS` counts as direct proof
- reviewed external recovery does not increment direct PASS

### Reviewed external recovery

A mandatory PARTIAL source is classified as reviewed-external-recovered only when:

- status is `PARTIAL`
- no confirmed missing URL remains
- `issuer_page_coverage_debt_retained = true`
- `verified_external_recovery_count > 0`
- `risk_kind = ISSUER_DISCOVERY_PARTIAL`

New metrics:

- `mandatory_reviewed_external_recovery_sources/count`
- `mandatory_unresolved_partial_sources/count`
- `mandatory_check_failed_sources/count`
- `mandatory_business_coverage_accounted/rate`

For the current production state, the expected interpretation is:

~~~text
direct PASS                  5 / 7
reviewed external recovery   1 / 7   (S13)
check failed                 1 / 7   (S21)
business coverage accounted  6 / 7
~~~

The 6/7 value is not a replacement for the strict 5/7 direct proof rate.

## Review reasons

The generic coverage review is split into:

- `MANDATORY_COVERAGE_NOT_FULLY_PROVEN` — unresolved PARTIAL/UNPROVEN
- `MANDATORY_COVERAGE_PARTIAL_RECOVERED_EXTERNALLY` — known opportunity recovered but direct discovery remains partial
- `MANDATORY_COVERAGE_CHECK_FAILED` — independent verification failed

Confirmed `GAP` remains a FAIL condition.

## Harness S2

Harness business-quality semantics now distinguish:

- confirmed/unresolved GAP/PARTIAL/UNPROVEN -> FAIL
- CHECK_FAILED / NOT_RUN -> UNKNOWN
- reviewed-external-recovered PARTIAL -> UNKNOWN
- only fully clean mandatory coverage -> PASS

A reviewed external recovery therefore cannot make Definition of Done pass by itself.

Production-state dry-run with the new logic:

~~~text
S13 PARTIAL       recovered=True
S21 CHECK_FAILED  recovered=False

S2.status = UNKNOWN
S2.reason = BUSINESS_COVERAGE_UNVERIFIED
mandatory_coverage_gaps = []
mandatory_coverage_unknown = [S21]
mandatory_coverage_recovered = [S13]
~~~

## MPT Tender landing investigation

The official MPT Tender Information / Procurement pages are reachable from both Mac and Bangkok.

However:

- the tender landing page does not server-render the individual tender records;
- WordPress REST endpoints tested for this purpose return HTTP 403;
- no stable public data endpoint was identified that is suitable for a production coverage contract.

Therefore no new MPT acquisition surface is introduced in this change.

## Boundary

This change does not:

- rewrite S13 PARTIAL to PASS;
- rewrite S21 CHECK_FAILED to PASS;
- weaken Definition of Done;
- change source registry policy;
- change source acquisition/parsers;
- mutate production data;
- change Telegram;
- change schedulers;
- deploy Bangkok.
