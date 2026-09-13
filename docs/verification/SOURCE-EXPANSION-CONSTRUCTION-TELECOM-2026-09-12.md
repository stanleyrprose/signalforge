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

- final targeted source/registry/scorecard/opportunity tests: `24 passed`;
- final full suite: `320 passed`;
- live parser smokes: PASS;
- clean-DB baseline semantics: PASS.

Production deployment evidence is appended after CI and live Bangkok activation.


## Production closure — 2026-09-13

PR #164 passed GitHub Actions verify run `34729187724` / job `103648717733` and squash-merged as `14f0301a4dcceaaee9aa2451384c17d36ed1a7bb`. The exact release archive SHA256 was `f72f8ceb735a02f939330d0b250147d81e27c7c05e3136a9c96f865d6de04bd6`, matched locally and on Bangkok, and deployed atomically with rollback target `4e95655be793bd2a22507d3209a76fe3bc87c7f6`.

Formal production Worker baselines completed successfully:

```text
S43: SUCCESS / baseline=true / discovered=2 / changed=2 / signals_created=0 / details=2/2
S44: SUCCESS / baseline=true / discovered=1 / changed=1 / signals_created=0 / listing_complete=true
S45: SUCCESS / baseline=true / discovered=3 / changed=3 / signals_created=0 / listing_complete=true
```

Post-deploy production acceptance:

```text
active release               14f0301a4dcceaaee9aa2451384c17d36ed1a7bb
active sources               30
GREEN sources                30
active-source canonical      216
database canonical           218
raw signals                  53
effective signals            32
known audited noise          21
current opportunities        15 = 14 OPEN + 1 UNKNOWN
priority distribution        8 HIGH / 5 MEDIUM / 2 REVIEW
current ICT/Telecom opps     2
Telegram alerts cumulative   11
Telegram immediate pending   0
recovery backlog             0
DB quick_check               ok
translation ready            true
```

The six new canonical rows are exactly `S43=2 + S44=1 + S45=3`; each new source has `baseline_complete=1`, `consecutive_failures=0`, `last_error=null`, `signals=0`, and source health GREEN. Global canonical count moved `212 -> 218` while global Signal count remained exactly `53`, proving no historical baseline noise. The current business funnel remained exactly 15 opportunities, so the telecom strategic-intelligence rows did not pollute procurement opportunities and the expired S43 construction baseline did not become current business output.

`source-scorecard --window-days 30` reports `30 active / 30 GREEN / 216 active canonical / 218 DB canonical / 53 raw / 32 effective / 21 known noise / 15 opportunities / 2 ICT-Telecom opportunities / 11 Telegram alerts`. Yield-state distribution is now `ACTIONABLE_PROVEN=7 / SIGNAL_PROVEN=3 / BASELINE_ONLY=18 / NOISE_ONLY_HISTORY=1 / EMPTY=1`; S43/S44/S45 begin as `BASELINE_ONLY / STRATEGIC_WATCH`, which is analytical only.

All three production timers are `enabled + active`: acquisition, immediate Telegram delivery, and daily Telegram digest. Mac OAuth translation remains `PASS / ready=true`, with queue `PENDING=0 / FAILED=0`. Immediate Telegram dry-run after deployment returned `PASS / pending_count=0`.

This closes the requested coverage expansion without a Business Fit layer. S23 remains deferred until the issuer repairs its expired TLS certificate. No Browser/OCR expansion, TLS bypass, Beijing role change, schema migration, qualification change, or Telegram delivery-policy change was introduced.
