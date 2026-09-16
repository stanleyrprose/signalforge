# Outage-aware retry backoff — 2026-09-16

## Problem

Production S21 (Myanma Railways) accumulated more than 500 consecutive acquisition failures while the issuer origin remained unreachable from both Bangkok and Mac egress. The source used `retry_interval_seconds=300`, so every failed run scheduled another attempt five minutes later indefinitely.

The Browser Escalation Candidate Report separately proved this is not a browser-engine problem: the dominant evidence is `CONNECT_TIMEOUT` and current browser A/B candidate count is zero.

## Scope

This change is scheduler-only. It does not change:

- source acquisition engines or Browser Plane routing;
- acquisition/evidence/processing schemas;
- source health thresholds;
- canonicalization, ranking, Mission Focus, Telegram, or digest behavior;
- the recorded failure class or failure count.

Backoff is driven only by a persisted failed acquisition attempt belonging to the current scheduler run. Parser/normalizer/business exceptions with no qualifying acquisition failure continue to use the configured base retry interval.

## Policy

Qualifying outage-like acquisition failures:

- `CONNECT_TIMEOUT`
- `DNS_FAILURE`
- `HTTP_429`
- `HTTP_5XX`

For the consecutive-failure count *after* the current failed run:

- failures 1–3: `1 × retry_interval_seconds`
- failures 4–6: `2 × retry_interval_seconds`
- failures 7–9: `4 × retry_interval_seconds`
- failures 10+: exponential growth continues but is capped at `recovery_slo_seconds`

If `recovery_slo_seconds` is unavailable, the cap falls back to at least the source poll interval. The cap is never lower than the configured base retry interval.

For S21 this produces:

- 1–3 failures: 300 s
- 4–6 failures: 600 s
- 7–9 failures: 1200 s
- 10+ failures: 1800 s cap

A success retains existing behavior: `consecutive_failures` resets to zero and normal poll scheduling resumes.

## Boundaries

`TRANSPORT_UNKNOWN`, HTTP 403, TLS, provider lifecycle failures, parser drift, and other non-qualified failures do not receive this outage backoff. Their scheduling semantics remain unchanged. This avoids hiding unknown or policy-relevant failures behind progressively slower retries.

The backoff never authorizes browser escalation or a source-routing change.

## Verification target

- targeted Railway/Engine/Acquisition tests;
- full repository regression;
- Python 3.13 workflow-equivalent verification;
- production S21 controlled failure after deployment must persist `CONNECT_TIMEOUT`, increment the existing failure count, and schedule `next_due_at` approximately 1800 seconds after the controlled run rather than 300 seconds.
