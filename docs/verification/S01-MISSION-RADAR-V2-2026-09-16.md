# S01 Mission Radar v2 — 2026-09-16

## Business goal

S01 Myanmar National Portal is an **Assurance-only coverage radar** for SignalForge's primary output mission: Myanmar government / SOE tenders in engineering, construction/infrastructure, telecom/ICT infrastructure and energy.

S01 remains non-canonical. Portal `Closing Date` is a discovery hint only.

## Why v2 was needed

The previous single-page scan was not sufficient for current coverage:

- page 1 contained the recovered MPT Pobbathiri opportunity;
- page 2 contained the still-open S38 Electrical / Mechanical spares tender (deadline 2026-09-25);
- page 3 contained the still-open IWT Coastal Vessel tender (deadline 2026-11-03);
- pages 4–6 contained no additional mission leads.

Therefore `current_page_only` could miss current opportunities even though S01 must not crawl all 165 pages / ~1,644 historical records.

## Bounded pagination contract

- maximum pages: 6
- stop after 3 consecutive pages with zero mission leads
- page size remains Portal-native 10 rows
- Portal date remains hint-only
- no canonical item or Signal is created by S01

This bound is evidence-driven by the 2026-09-16 live Portal distribution, not an arbitrary historical crawl depth.

## Mission selection

Positive evidence is restricted to the target sectors:

- construction / road / bridge / civil / repair works
- telecom, network, server, data center, GMDSS, towers and related ICT infrastructure
- electricity / power / substation / transmission / SCADA / hydropower
- clear electrical / mechanical / vessel engineering procurement

Mixed issuers such as Industry and municipal development bodies require title-level mission evidence.

Off-mission vetoes run first. Examples include medical/pharma, laboratory apparatus, chemicals, yarn, ordinary logistics, fuel/diesel and scrap-cutting procurement.

### Negative live sample

A Mandalay City Development Committee card initially looked relevant because it came from the Factory & Motor Vehicle Department. Official Portal JPG OCR proved it was ordinary fuel procurement:

- diesel ~85,000 gallons
- Premium Diesel 45,000 gallons
- Octane-92
- tender form sale 2026-09-15 to 2026-09-18
- tender event 2026-09-28

It is correctly excluded from the mission radar.

## Cross-surface equivalence

URL equality alone is insufficient because National Portal may host an issuer PDF while canonical acquisition uses the issuer detail page.

Only deterministic equivalence proofs are accepted:

1. `EXACT_OFFICIAL_PATH_WWW_HOST_ALIAS`
   - same HTTPS official path after removing a leading `www.` host alias
   - live sample: S38 `industry:1039`

2. `EXACT_ISSUER_TITLE_AND_ATTACHMENT_NAME`
   - target source is explicit
   - Portal title exactly matches an issuer canonical title field
   - Portal official document filename exactly matches canonical `attachment_name`
   - currently source-specific to S22 / IWT
   - live sample: `iwt:1038:2026-08-25`, `IWT_1 Costal Vessel Tender 25-8-2026.pdf`

No fuzzy similarity is used. Portal `Closing Date` is retained only as audit metadata and is not a deciding equivalence field.

## Production-backup replay acceptance

Using a consistent production SQLite backup and live Portal pages 1–6:

- official mission leads: 3
- covered: 3
- unresolved: 0
- confirmed gaps: 0

Resolution:

- MPT Pobbathiri → `VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY`
- S38 Electrical/Mechanical spares → `CANONICAL_EQUIVALENT / EXACT_OFFICIAL_PATH_WWW_HOST_ALIAS`
- IWT Coastal Vessel → `CANONICAL_EQUIVALENT / EXACT_ISSUER_TITLE_AND_ATTACHMENT_NAME`

This is the required release gate for Mission Radar v2.
