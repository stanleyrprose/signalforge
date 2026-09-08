# S27 Ministry of Border Affairs — Provider C0 Source Onboarding

Date (Asia/Yangon): 2026-09-08
Phase: PRODUCTION
Result: PRODUCTION / GREEN — LIVE VERIFIED

## Selection decision

S27 was registered as a deferred candidate because the issuer website was Mac-C0 reachable but Bangkok strict TLS failed on an incomplete issuer certificate chain. The earlier source-network audit allowed reconsideration only if either the issuer certificate chain became valid from Bangkok or a separately reviewed Provider Invocation Contract existed for a real business requirement.

PIC R4/R5 is now independently production-live through S38, so reconsidering S27 no longer means prebuilding a provider merely to onboard MOBA.

Fresh 2026-09-08 audit preserved the original network split:

- Bangkok listing `https://moba.gov.mm/my/tender`: strict HTTPS failed 3/3 with curl 60 / unable to get local issuer certificate;
- Bangkok detail `https://moba.gov.mm/my/tender/3475`: strict HTTPS failed 3/3 with the same issuer-chain error;
- Mac Browser Plane C0 listing: HTTP 200 / `text/html` / 84,281 bytes / job `5a329634-f573-4c35-ad94-5bed472b505d`;
- Mac Browser Plane C0 detail 3475: HTTP 200 / `text/html` / 56,479 bytes / job `69f2aaae-e418-49fa-ba95-676a05685c23`.

No TLS bypass, `verify=false`, proxy fallback, or generic Direct-HTTP-failure-to-Browser escalation was introduced.

## Production acquisition contract

S27 is the second explicit provider-backed production source.

```text
source_id             = S27
engine                = provider
provider_id           = mac-mm-01
provider_capability   = C0_FETCH
provider LISTING      = exact https://moba.gov.mm/my/tender
provider DETAIL       = https://moba.gov.mm/my/tender/<issuer node id>
query / fragment      = forbidden
C1 / C2 / C3          = not source-authorized
PDF primary fetch     = disabled
first baseline signal = false
```

The Provider contract remains pull-only through the dedicated restricted SSH identity and local Mac MCP stdio runtime. No inbound Mac listener is added.

## Business-shape contract

The official Drupal tender table exposes tender-form sale date, tender-form closing date, title, stable detail URL and official PDF metadata.

The opportunity classifier includes tender invitations/open tender records and excludes outcome-stage rows. Fresh fixture examples prove:

- `3475` — opportunity, sale date `2026-08-24`, deadline `2026-09-08`;
- `3395` — Desktop Computer 122 sets procurement, deadline `2026-06-05`;
- `3400` / `3401` — tender-success/company-result records, excluded.

Stable issuer-native identity is the Drupal tender node id:

```text
canonical_key = moba:<node_id>
reference_no  = MOBA-TENDER-<node_id>
```

Publication date is not exposed by the audited tender fields and remains `null / NOT_PUBLISHED_BY_ISSUER`; it is not inferred from sale date, collection time or PDF metadata.

Official PDFs are `METADATA_ONLY_NON_BLOCKING`; scope and deadline are already available in HTML and no PDF parser/OCR capability is required.

## Implementation verification

Implementation PR: SignalForge #89.
Merged implementation SHA:

```text
29cdf90554c61bfcdc8bfb6cf4fba16c597652c9
```

Verification before merge:

```text
targeted parser/contract/provider suite = 31 passed
full SignalForge suite                  = 202 passed
git diff --check                        = PASS
GitHub verify                           = PASS
```

Production contract regression proves C0 listing/detail requests are accepted while C1 and query-bearing detail requests are rejected.

## Rollout freeze and deployment recovery

Pre-deploy Bangkok state:

```text
active release    = 1d88b54d22f43e818a055a5c605a14c728816aad
timer             = disabled / inactive
run-due           = inactive
refresh active    = 0
DB quick_check    = ok
canonical_items   = 183
signals           = 34
failed_runs       = 31
provider pending  = 0
provider claimed  = 0
```

The first exact-SHA deployment attempt exposed a deployment-packaging mode bug. The rollout source directory came from `mktemp -d` (0700); `cp -a SOURCE/. STAGE/` preserved that root mode onto the staged release. The new release root therefore became `0700 root:root` and the deploy smoke failed with:

```text
env: /srv/signalforge/active/bin/signalforge: Permission denied
exit 126
```

The deploy rollback trap worked: `active` remained on the prior release and the timer remained disabled. The candidate binary itself was healthy; only directory traversal was blocked.

Recovery was bounded:

1. normalize only the candidate release root to 0755;
2. verify the `signalforge` identity can execute the candidate CLI;
3. rerun the reviewed deploy script against the already-built exact release;
4. migrate/status smoke PASS;
5. active release becomes `29cdf90554c61bfcdc8bfb6cf4fba16c597652c9` with timer still OFF.

The deployment script is hardened in the closure change by normalizing `$STAGE` to 0755 immediately after `cp -a`, preventing restrictive source-root metadata from making a release untraversable.

## First production baseline

Worker run:

```text
worker_run_id = signalforge-20260908T151231Z-d816f1d3
app_run_id    = 9621ea2a-3c8c-4206-93c8-07f5e1d3c2b6
trigger       = MANUAL
baseline      = true
status        = SUCCESS
```

Result:

```text
discovered        = 7
candidates         = 6
fetched            = 6
details_attempted  = 6
details_succeeded  = 6
detail_errors      = 0
items              = 6
tenders            = 6
changed            = 6
signals_created    = 0
backlog_remaining  = 0
```

The seventh discovered opportunity is a 2025-07 record outside the 180-day baseline window; 7 -> 6 is therefore expected selection behavior, not a fetch failure.

Post-baseline durable state:

```text
S27 canonical              = 6
S27 signals                = 0
S27 pending                = 0
S27 provider SUCCEEDED     = 7
S27 provider non-SUCCEEDED = 0
S27 EvidenceEnvelope       = 7
S27 processing SUCCESS     = 7
DB quick_check             = ok
```

Canonical rows are `moba:3371`, `moba:3372`, `moba:3374`, `moba:3375`, `moba:3395`, and `moba:3475`.

S27 health after baseline:

```text
fetch       = GREEN
freshness   = GREEN
parse       = GREEN / 6 of 6
recovery    = GREEN / backlog 0
source      = GREEN
failures    = 0
last_error  = null
```

## Cross-node / scheduler invariants

Beijing remains Generic Worker only:

```text
/srv/signalforge absent = yes
forced dispatcher       = /usr/local/sbin/gha-root-dispatch
signalforge-refresh S27 = exit 126
stderr                  = DENY: SignalForge is Bangkok-only
```

After baseline, Bangkok timer was restored to enabled/active. `Persistent=true` immediately invoked production `run-due`; Worker run `signalforge-20260908T151524Z-ddbdc70c` completed `SUCCESS`. S27 correctly returned `NOT_DUE` because its next due time was `2026-09-08T15:42:32.230651Z`; due Direct-HTTP sources executed normally.

## Final boundary

S27 does not broaden the platform invocation surface:

- Direct HTTP remains the default for healthy sources;
- only explicit provider sources enter the Mac queue;
- S27 is C0-only despite the platform having proven C1/C2/C3 capability;
- no arbitrary URL, shell, Browser fallback, PDF/OCR or inbound Mac listener is introduced;
- S27 customer signals remain zero for the historical first baseline;
- Bangkok remains the only SignalForge canonical production node.

S27 is therefore **PRODUCTION / GREEN**.
