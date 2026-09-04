# Mac/Bangkok Source Network Re-Audit — 2026-09-04

## Purpose

Validate whether Mac Browser Plane source acceptance results can be projected directly into Bangkok SignalForge production acquisition.

This audit is intentionally read-only on Bangkok. No TLS bypass, package installation, Browser runtime, source enablement, timer change, or production data mutation was performed.

## Frozen integration boundary

```text
SignalForge production C0
→ Bangkok VPS Direct HTTP

Mac Browser Plane
→ Mac mini direct Internet
→ local C0/C1/C2 only
→ SignalForge unattended production provider remains disabled
```

A source reachable from Mac does not automatically become production-reachable from Bangkok.

## Live strict-TLS results

### Control source — MPT Tender

Bangkok command shape:

```text
curl -L --max-time 30 <MPT Tender URL>
```

Observed:

```text
HTTP status      = 200
ssl_verify_result= 0
content-type     = text/html; charset=UTF-8
bytes            = 80,226
```

Disposition:

```text
Bangkok C0 GREEN
Current S13 DIRECT_HTTP production path remains valid.
```

### Control source — Ministry of Commerce 2026 Notifications

Observed from Bangkok:

```text
HTTP status      = 200
ssl_verify_result= 0
content-type     = text/html; charset=UTF-8
bytes            = 108,222
```

Disposition:

```text
Bangkok C0 GREEN
Current S05A DIRECT_HTTP production model remains valid.
```

### MPA Tender Category

URL:

```text
https://www.mpa.gov.mm/tenders-and-announcement/
```

Mac Browser Plane prior acceptance:

```text
Mac direct C0
→ HTTP 200
→ complete static HTML available
→ real tender PDF also HTTP 200
```

Bangkok strict-TLS re-audit:

```text
curl exit        = 60
HTTP status      = 000
ssl_verify_result= 20
error            = unable to get local issuer certificate
```

Disposition:

```text
Mac C0 GREEN
Bangkok C0 RED-TLS
S15A/S15B remain excluded/deferred from unattended production.
```

Do not use `-k`, `--insecure`, certificate-ignore flags, or Browser escalation to hide this failure.

### Ministry of Border Affairs Tender

URL:

```text
https://moba.gov.mm/tender
```

Mac Browser Plane prior acceptance:

```text
Mac direct C0
→ HTTP 200
→ static business content present
→ visible Load More reduces to deterministic ?page=N URLs
```

Bangkok strict-TLS re-audit:

```text
curl exit        = 60
HTTP status      = 000
ssl_verify_result= 20
error            = unable to get local issuer certificate
```

Disposition:

```text
Mac C0 GREEN
Bangkok C0 RED-TLS
Candidate is DEFERRED, not production-onboarded.
```

## Interpretation

The results prove an execution-environment difference, not a Browser requirement.

```text
MPA/MOBA Bangkok TLS failure
!= JS_RENDER_REQUIRED
!= reason to install Playwright on Bangkok
!= reason to disable TLS verification
!= reason to activate SignalForge→Mac remote invocation
```

The source-policy resolution remains:

```text
TLS_FAILURE on current production provider
→ FAIL / AUDIT
→ keep source disabled/deferred
```

Mac reachability is useful source-audit evidence only while:

```yaml
mac_browser_provider:
  production_enabled: false
```

## Source disposition after re-audit

| Source | Mac direct | Bangkok strict TLS | Production disposition |
| --- | --- | --- | --- |
| MPT Tender / S13 | PASS | PASS | Keep ACTIVE Direct HTTP |
| Commerce / S05A | PASS | PASS | Keep ACTIVE Direct HTTP |
| MPA / S15A/S15B | PASS | FAIL TLS | Keep deferred/excluded |
| MOBA Tender / candidate S27 | PASS | FAIL TLS | Register deferred candidate only |
| Myanmar National Trade Portal / S04 | PASS | not material to current decision | Keep deferred aggregator pending issuer-resolution/dedup contract |

## No architecture change

This audit does not reopen v1.5.1.

Preserved invariants:

- Bangkok remains SignalForge canonical production node.
- VPS Browser/Crawlee R3 remains superseded.
- `browser_production_approved=false` remains frozen.
- Mac Browser Provider remains `production_enabled=false`.
- No SignalForge→Mac RPC/SSH/HTTP invocation is added.
- No TLS verification bypass is allowed.

## Trigger for future reconsideration

Reconsider MPA/MOBA only if one of the following occurs:

1. their certificate chains become valid from the Bangkok production environment; or
2. a separately reviewed and justified provider contract is introduced for a real business requirement.

Do not prebuild option 2 merely to onboard these sources.
