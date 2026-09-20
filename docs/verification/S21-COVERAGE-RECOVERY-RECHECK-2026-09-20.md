# S21 Myanma Railways Coverage Recovery Recheck — 2026-09-20

## Goal

Determine whether S21 can be safely restored from `CHECK_FAILED` through another official-origin acquisition path without weakening the coverage standard.

## Current issuer surface

Official endpoints:

```text
https://www.railways.gov.mm/category/tender/
https://www.railways.gov.mm/tenders/
```

DNS at the time of verification:

```text
railways.gov.mm      -> 18.136.56.210
www.railways.gov.mm  -> 18.136.56.210
```

No IPv6 address was observed.

## Runtime reachability

### Mac direct

The following all timed out establishing a connection:

- HTTP / bare host
- HTTP / www host
- HTTPS / bare host
- HTTPS / www category feed

### Bangkok direct

The same HTTP/HTTPS variants also timed out.

This confirms that changing path, scheme, bare-vs-www host, or WordPress feed does not recover the issuer origin from the currently approved egresses.

## Mac Browser Plane / Provider investigation

Mac Browser Plane health:

```text
browserctl doctor = READY
Provider LaunchAgent = running
provider agent = pull_ssh_v1
```

SignalForge Provider contract is intentionally source-allowlisted. S21 is not currently authorized, so no remote Provider contract bypass was attempted.

The Browser Plane architecture states:

- C0 FETCH uses macOS system curl;
- C1 RENDER uses the internal browser engine router.

Therefore C0 cannot improve the already observed direct curl timeout.

A local read-only C1 Render smoke was run against the Railways official tender category:

- job_id: `bac4bc7b-e840-4294-93f2-150e9bb24662`
- task_type: `automate` / C1
- profile: ephemeral public-research
- result: `FAILED`
- failure_class: `AUTOMATION_FAILED`
- partial_effect_possible: false
- error: `Page.goto: Timeout 20000ms exceeded`

The browser-engine path therefore does not recover the origin either.

## Official mirror investigation

Myanmar National Portal and Ministry-hosted evidence can contain Myanma Railways tenders, but the observed publication history is not a continuous synchronized mirror of the Railways tender surface.

The existing S01 National Portal radar remains useful for discovery and has already been hardened for Myanma Railways title recognition.

It must not be treated as proof that all issuer tenders are covered.

## Search-index observation

External search indexing still showed the Railways official tender listing and official pages being crawled recently, with the newest indexed tender dated 2026-09-01.

This is diagnostic evidence that the issuer site is not necessarily globally offline.

Search indexing is third-party, delayed, and non-exhaustive, so it is not accepted as coverage proof or canonical truth.

## Decision

Do not add:

- a weak third-party tender mirror;
- search-engine HTML scraping as coverage proof;
- a redundant S21 Mac Provider policy;
- a new browser engine;
- a new VPS solely to make the metric green.

S21 should remain:

```text
CHECK_FAILED / BUSINESS_COVERAGE_UNVERIFIED
```

until one of these becomes true:

1. issuer origin becomes reachable from an approved production path;
2. a reliable official synchronized surface is proven;
3. reviewed official external evidence recovers a specific current opportunity, in which case recovery is recorded without claiming direct issuer completeness.

## Boundary

No Source Registry, Provider contract, acquisition parser, canonical state, scheduler, or Telegram change is justified by this recheck.
