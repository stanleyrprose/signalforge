# S42 ATOM Source Audit — Deferred — 2026-09-10

## Decision

Do not onboard an ATOM Myanmar production source at this time.

The bounded source audit found evidence that ATOM operates a real supplier/sourcing function, but it did not find a public, repeatable tender/RFP/RFQ listing or supplier bidding surface suitable for SignalForge acquisition. This is therefore a source-availability decision, not a claim that ATOM has no procurement activity.

`S42` remains unassigned/deferred. No registry entry, parser, Browser/Provider dependency, credentialed portal automation or scraping workaround is added.

## Why ATOM was audited

After S41 MYTEL production activation, SignalForge telecom coverage includes:

- MPT tender monitoring (`S13`);
- PTD telecom-sector government procurement (`S34`);
- MYTEL procurement via Viettel Global (`S41`).

ATOM is the remaining major operator-level coverage gap worth checking before adding less strategic sources.

## Official public-site evidence

Bounded public searches of ATOM's official web properties found:

- an official Supply Chain Sustainability page describing supplier standards, monitoring and supplier engagement;
- business/customer/partner contact surfaces;
- no public tender/RFP/RFQ/procurement listing discovered through the reviewed public pages.

This supports the existence of supplier management but does not expose a production acquisition surface.

Official pages reviewed include:

- `https://www.atom.com.mm/my/about/sustainability/supplychain`
- `https://www.atom.com.mm/en`
- `https://arena.atom.com.mm/en/personal/contact`
- `https://business.atom.com.mm/`

## Bangkok sitemap / robots gate

Bangkok strict-TLS probes were run against the official host.

`https://www.atom.com.mm/robots.txt`

```text
HTTP 200
24 bytes
tender      0
procurement 0
supplier    0
rfp         0
rfq         0
sourcing    0
```

`https://www.atom.com.mm/sitemap.xml`

```text
HTTP 200
131679 bytes
tender      0
procurement 0
supplier    0
rfp         0
rfq         0
sourcing    0
```

`https://www.atom.com.mm/sitemap_index.xml`

```text
HTTP 404
```

The sitemap result is evidence only about ATOM's indexed public web surface. It does not prove that credentialed or invitation-only procurement systems do not exist.

## Search gate

Bounded searches included combinations of:

- `ATOM Myanmar tender procurement RFP 2026`
- `site:atom.com.mm tender procurement vendor RFQ RFP`
- `site:atom.com.mm Request for Proposal / tender / procurement`
- `ATOM Myanmar supplier portal`
- `ATOM Myanmar Coupa`
- `ATOM Myanmar e-bidding`
- `ATOM Myanmar sourcing portal`

Results were dominated by ATOM business/customer pages, supply-chain sustainability material, partner applications and third-party professional profiles. No official public tender listing or repeatable procurement feed was identified.

Third-party professional-profile evidence suggests ATOM uses internal RFx/sourcing processes, but such evidence is not authoritative enough to define a SignalForge production source and provides no public acquisition endpoint.

## Production gate evaluation

A production source requires a stable evidence path that can be monitored without credentials or policy-bypassing behavior.

ATOM currently fails that gate because the audit did not identify:

- an official public tender archive;
- an official public RFQ/RFP feed;
- a public supplier-bidding portal with repeatable anonymous access;
- a public structured API/feed containing procurement events.

Therefore no acquisition-engine test is warranted. There is nothing to justify Direct HTTP, Mac Browser Plane, Provider, login automation or a new capability.

## Boundary

Do not create S42 merely to represent ATOM as an organization.

Re-open this audit only when one of these evidence triggers appears:

1. ATOM publishes an official tender/RFP/RFQ page or public supplier portal;
2. an official ATOM page links to a public procurement platform;
3. a real current procurement opportunity reveals a stable official public URL that can be audited;
4. the user explicitly provides authorized supplier-portal access and separately approves credentialed acquisition design.

Until then, operator-level procurement intelligence for ATOM must come from normal sales/account channels or manually supplied evidence, not SignalForge unattended public-web collection.

## Portfolio conclusion

S41 MYTEL was worth onboarding because an official, structured, repeatable public procurement feed existed and could be acquired safely from Bangkok. ATOM does not currently meet the same source-quality bar.

This validates the portfolio rule:

> Strategic importance alone does not justify a production source; SignalForge needs a trustworthy and maintainable acquisition surface.

No runtime, registry, database, scheduler, delivery policy, Browser Plane, Provider or Beijing role changes result from this audit.
