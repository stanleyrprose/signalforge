# PTD Policy + Strategic Digest — 2026-09-13

## Decision

Add `S46` as a bounded issuer-original telecom strategic-intelligence source and make strategic regulatory/network Signals visible in the existing daily Telegram business digest. No Business Fit layer is introduced.

## S46 source

- Name: `PTD Spectrum and Telecom Policy`
- Official landing/discovery: `https://www.ptd.gov.mm/LawsFP.aspx`
- Engine: Bangkok `direct_http`, strict TLS
- Role: `ACTIVE_SELECTIVE`
- Item kind: `REGULATORY_NOTICE`
- Business stage: `STRATEGIC_INTELLIGENCE`
- Relevance: `TELECOM`
- Poll interval: 6h; retry 30m
- Listing-complete metadata only; official PDF is linked but is not fetched in the primary pipeline.

Selection is bounded to telecom-strategic titles: spectrum/frequency/5G/2600 MHz, digital master plans, broadband, Internet Exchange, numbering, connectivity and telecommunications/ICT plans. Canonical identity is publication date + normalized policy title; the official PDF URL remains payload evidence and the user-facing detail link.

## Live official-page audit

Bangkok strict-TLS access returned HTTP 200. The parser currently selects 9 official baseline records, including:

- `2026-01-16` — ASEAN Digital Master Plan 2026-2030
- `2022-10-31` — Spectrum Roadmap (2022-2026)
- `2020-11-04` — Policies and Frameworks for Internet Exchange
- `2017-04-08` — Spectrum Roadmap (Meet the Needs Over Next 5 Years)
- `2016-10-12` — 2600 MHz Auction Framework with Clarification
- `2010-01-31` — Telecommunications Numbering Plan

Every selected row has an issuer-original HTTPS PDF link.

## Clean baseline verification

A clean temporary SignalForge DB was migrated and S46 was run against the live official endpoint:

```text
S46: SUCCESS / baseline=true / discovered=9 / changed=9 / signals_created=0 / listing_complete=true
opportunities: 0
```

Historical policy documents therefore do not create customer Signals and do not enter the Tender opportunity funnel.

## Daily Digest strategic-notice delivery

Before this slice, the daily digest counted recent `REGULATORY_NOTICE` Signals but did not show their details. This slice adds a bounded `📡 战略动态` section containing at most four Signals from the last 24h whose payload explicitly has `business_stage=STRATEGIC_INTELLIGENCE`. Each row includes source, NEW/UPDATED, strategic kind, publication date, title and an official HTTPS link.

This is deliberately digest-only: strategic notices do not become Tender opportunities and do not create immediate Telegram alerts. Existing opportunity immediate-delivery policy is unchanged.

A TEST_ONLY Signal against the clean DB produced a real `telegram-digest --dry-run --no-network` payload containing:

```text
📡 战略动态
• S46 · NEW · DIGITAL_CONNECTIVITY_POLICY · 2026-01-16 · ASEAN Digital Master Plan 2026-2030 ... · 官方详情
```

The official PTD PDF URL was present in the Telegram HTML anchor.

## Construction / real-estate source audit boundary

YCDC Roads & Bridges / Urban Planning / Urban Land Management were audited before adding another construction source. Unlike existing S16 `frontend_engineering_building_detail/1`, reasonable stable department archive routes returned 404. `/frontend_tender` continues to emit regenerated encrypted locators. The Yangon Region general tender board was also detail-audited; its current first page is dominated by general procurement/YESC content and has low clean construction/housing yield plus overlap risk with S43. Therefore no additional construction source is added merely to increase source count. Existing S16 covers YCDC Building/PPP/Affordable Housing and S43 covers Ministry of Construction road/bridge works.

## Verification

- targeted tests: `19 passed`
- final full suite: `323 passed`
- `git diff --check`: PASS
- live S46 parser: 9 strategic records with official PDF URLs
- clean DB S46 baseline: 9 canonical / 0 Signals
- clean DB opportunities: 0
- TEST_ONLY strategic Signal -> daily digest detail + official link: PASS

Production deployment evidence will be appended after CI and Bangkok activation.
