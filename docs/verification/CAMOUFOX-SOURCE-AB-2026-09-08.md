# Camoufox Source A/B — 2026-09-08

Status: **COMPLETE / NO PRODUCTION SOURCE ROUTING CHANGE**

## Purpose

Validate whether Mac Browser Plane's optional Camoufox engine provides measurable acquisition value for current SignalForge production/relevant Myanmar sources before adding any source-level `preferred_engine=camoufox` policy or extending Provider Invocation Contract semantics.

This is an evidence gate, not a rollout gate.

## Baseline contract

At the start of this test:

- SignalForge Provider Invocation Contract v1 exposes provider capabilities C0/C1/C2/C3 but contains **no browser-engine selector**.
- Current production source policies authorize Mac provider invocation only for S38 and S27, and both are currently C0-only.
- Mac Browser Plane owns engine selection internally.
- Camoufox is an optional selective engine; AUTO does not select it.
- TLS verification remains mandatory. No certificate bypass is authorized.

Therefore no SignalForge contract or registry change is justified unless real-source evidence shows a material Camoufox advantage.

## Test method

Each source listing URL was executed through the installed production Mac Browser Plane runtime as an ephemeral C1 job twice in principle: once with explicit `engine=chrome`, once with explicit `engine=camoufox`.

Compared fields:

- terminal job state;
- HTTP status;
- final URL;
- page title/body availability;
- obvious challenge indicators such as CAPTCHA / Cloudflare / access-denied pages;
- Browser Plane browser elapsed time;
- failure class/error when present.

No source-side mutations were performed.

## Results

| Source | URL | Chrome | Camoufox | Decision signal |
| --- | --- | --- | --- | --- |
| S38 Ministry of Industry | `https://www.industrymsme.gov.mm/announcements` | PASS, HTTP 200, ~1.40s browser elapsed | PASS, HTTP 200, ~6.72s | Same content/status; Camoufox materially slower |
| S27 Ministry of Border Affairs | `https://moba.gov.mm/my/tender` | PASS, HTTP 200, ~3.75s | FAIL | Camoufox `SEC_ERROR_UNKNOWN_ISSUER`; Chrome is strictly better |
| S15A Myanma Port Authority | `https://www.mpa.gov.mm/tenders-and-announcement/` | PASS, HTTP 200, ~2.29s | FAIL | Camoufox `SEC_ERROR_UNKNOWN_ISSUER`; Chrome is strictly better |
| S34 PTD | `https://www.ptd.gov.mm/CatAnnouncements.aspx` | PASS, HTTP 200, ~3.76s | PASS, HTTP 200, ~5.80s | Same content/status; Camoufox slower |
| S30 MOFA | `https://www.mofa.gov.mm/category/announcement/` | PASS, HTTP 200, ~6.08s | PASS, HTTP 200, ~8.29s | Same content/status; Camoufox slower |

Observed challenge indicators on successful pages: **none**.

Chrome result: **5/5 successful**.

Camoufox result: **3/5 successful**.

## Failure confirmation

S27 and S15A Camoufox failures were rerun and reproduced. Browser Plane returned:

```text
Page.goto: SEC_ERROR_UNKNOWN_ISSUER
```

for both hosts.

This is a Firefox/Camoufox certificate-chain trust failure, not evidence of browser fingerprint blocking or an anti-bot challenge.

Because SignalForge and Mac Browser Plane require normal TLS verification, the correct response is **not** to disable certificate validation or add a TLS bypass.

## Runtime cleanup

After the A/B and failure reproduction:

- `browser_doctor = READY`;
- stale Profile Leases = `[]`;
- Browser Process Registry ownership residue = `[]`;
- Camoufox package/browser asset remained healthy.

## Decision

**Do not promote Camoufox into SignalForge production source routing.**

Specifically:

1. Do not add `preferred_engine=camoufox` to any current source.
2. Do not extend Provider Invocation Contract v1 with an engine-selector field now.
3. Do not change S38 or S27 provider capability/routing because of Camoufox.
4. Do not interpret HTTP 403/429/TLS errors generically as a reason to retry with Camoufox.
5. Do not bypass TLS verification for S27, S15A, or any other source.
6. Keep Camoufox installed and available as an **optional research/exception engine** in Mac Browser Plane.

## Future promotion gate

Re-open source-level Camoufox routing only when a real source demonstrates all of the following:

- Chrome/Lightpanda failure is reproducible and attributable to browser fingerprint/automation detection rather than DNS, TLS, authentication, authorization, rate limiting, regional policy, or parser drift;
- Camoufox succeeds materially and repeatedly where Chrome does not;
- repeated Camoufox runs leave no process/lease residue;
- evidence fidelity remains equivalent;
- no unsafe C3 action replay is introduced;
- the source-specific gain is large enough to justify Camoufox's higher runtime cost and upstream compatibility risk.

Until that gate is met, production routing remains unchanged.
