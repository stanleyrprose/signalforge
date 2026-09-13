# Construction + Telecom Source Expansion — 2026-09-12

## Decision

Add three issuer-original, low-complexity Direct HTTP sources without adding a Business Fit layer or expanding Browser/OCR capability:

- `S43` — Yangon Region Ministry of Construction Tenders;
- `S44` — ATOM 5G Network Technology Announcements;
- `S45` — MPT Network and Technology News.

All three begin as analytical `STRATEGIC_WATCH`. Source tiering is not a runtime priority change.

## Why these sources

### S43 — construction / engineering

Source: `https://www.yangon.gov.mm/category/ministry-of-construction/`

The official Yangon Region Government WordPress category is strict-TLS reachable from Bangkok and exposes stable WordPress post identities, official detail URLs, publication timestamps and tender content. Current 2026 records include Roads Department road/bridge works and materials tenders.

The source is preferable to forcing the previously deferred national Ministry of Construction endpoint. `S23` remains deferred because the national construction site content is live but Bangkok strict TLS rejects its expired certificate. SignalForge does not disable TLS verification or create an insecure exception merely to increase source count.

S43 characteristics:

- Direct HTTP from Bangkok;
- issuer-original HTTPS;
- stable WordPress post ID canonical identity;
- discovery category is construction-specific;
- detail HTML provides road/bridge construction scope and submission/close dates;
- no Browser, OCR or attachment dependency;
- historical baseline is suppressed from customer Signal delivery.

Live pre-production parser smoke discovered two current-category 2026 records and parsed:

- post `3691` — publication `2026-06-09`, deadline `2026-06-24`;
- post `3689` — publication `2026-06-09`, deadline `2026-06-22`.

Both are historical/expired at activation time, so they are baseline evidence rather than customer opportunities.

### S44 — ATOM 5G network technology

Source API: `https://www.atom.com.mm/api/v1/medias?locale=en&search=5G&page=1`

ATOM's own media UI calls an official structured JSON API. A bounded `search=5G` query is used rather than ingesting all ATOM media content, avoiding promotions, CSR, sports and customer campaigns.

The current official API result is media id `567`, published `2024-06-11`, covering ATOM's successful 5G trials. Future ATOM items whose official media metadata contains `5G` will be discovered through the same endpoint.

S44 characteristics:

- Direct HTTP / strict TLS;
- official JSON API;
- stable official media ID canonical identity;
- `REGULATORY_NOTICE` / `STRATEGIC_INTELLIGENCE`, not a Tender;
- TELECOM relevance;
- no Browser/OCR/detail fetch;
- historical baseline suppressed from customer Signal delivery.

### S45 — MPT network / fiber / 4G technology

Source: `https://mpt.com.mm/en/about-home/media-press-releases/latest-news/`

MPT's official Latest News listing is directly reachable from Bangkok and exposes title, publication date, excerpt and official detail URL. A bounded technology filter selects explicit network terms such as 5G, 4G/LTE, network expansion, fiber/FTTH, core/transport/radio network, spectrum, backhaul, infrastructure and network sites.

Live pre-production parser smoke selected three official MPT records:

- `2026-08-06` — Emergency Network Solutions;
- `2026-07-14` — Expanded Network, including new network sites / 4G LTE upgrades;
- `2026-07-08` — copper-network migration to high-speed fiber.

S45 is also `REGULATORY_NOTICE` / `STRATEGIC_INTELLIGENCE`, not a Tender, and therefore does not pollute the procurement opportunity funnel.

## Baseline semantics verification

A clean temporary SignalForge database was migrated and all three sources were run against the live official endpoints with test Worker correlation.

```text
S43: SUCCESS / discovered 2 / canonical changed 2 / signals_created 0
S44: SUCCESS / discovered 1 / canonical changed 1 / signals_created 0
S45: SUCCESS / discovered 3 / canonical changed 3 / signals_created 0
```

Running `opportunities` against that clean database returned exactly `0` current opportunities. This verifies that S44/S45 `REGULATORY_NOTICE` rows do not masquerade as procurement opportunities and that S43's historical expired tenders are not surfaced as current business opportunities.

## Telegram current-opportunity snapshot

Before source expansion, the live production opportunity set remained exactly 15 records: `8 HIGH / 5 MEDIUM / 2 REVIEW`, `14 OPEN + 1 UNKNOWN`.

At the user's request, SignalForge sent one manual summary plus all 15 current opportunities to the configured Telegram chat. Every opportunity message includes the issuer, reference, action/deadline status and a clickable official detail link.

Result:

```text
opportunities_sent = 15
messages_total      = 16
Telegram message IDs = 17..32
```

This was a manual read-only opportunity snapshot and intentionally did not insert normal Signal delivery receipts; automatic delivery dedupe semantics are unchanged.

## Safety / architecture boundaries preserved

This expansion does not authorize:

- insecure TLS bypass;
- S23 national Ministry of Construction activation while its certificate is invalid;
- Browser Plane fallback for these three sources;
- OCR or PDF extraction;
- telecom promotion/CSR/news ingestion without explicit network-technology semantics;
- treating telecom strategic intelligence as Tender opportunities;
- changing Beijing's role;
- changing existing source polling, qualification or Telegram policies.

## Pre-merge verification

- targeted source/registry/opportunity tests: `23 passed` before final tier assertion;
- full suite before final naming/tier assertion: `319 passed`;
- live parser smokes: PASS;
- clean-DB baseline semantics: PASS.

Production deployment evidence is appended after CI and live Bangkok activation.
