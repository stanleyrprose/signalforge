# S01 Government Intelligence (historical review-first baseline)

> Current owner-approved S01 scope is daily news acquisition, Chinese Markdown body and AI Digest, Bangkok Telegram delivery, and independent receipts per `S01-S52-S53-NEWS-DELIVERY-CONTRACT.md`. Review-first restrictions below describe the initial rollout gate; they do not revoke later owner authorization. Production PASS still requires runtime evidence. — Rev1 (owner-approved scope, implementation gate)

## Goal and boundary

Extract high-value non-procurement official notices from S01 National Portal without contaminating SignalForge Tender Core. Tender remains the only canonical `TENDER` and tender Telegram feed. Government Intelligence is an independent, evidence-backed output category, not a tender signal, and must not affect tender health, coverage KPIs or deduplication.

## MVP

- Reuse S01 existing once-daily Mac Browser Plane acquisition and original HTML/image/PDF evidence. No extra crawling schedule or new provider.
- Include: material government investment/project announcements, telecom/ICT, construction, power/energy policy and projects, and official state asset sale/lease announcements with commercial relevance.
- Exclude: advertising, ceremony-only stories, generic speeches, routine personnel news, duplicates, unverified portal hints, and unrelated topics.
- Each record: source URL, official issuing body, original publication date (if supported), concise Chinese headline, Chinese factual summary, sector/category, why it matters, original evidence hash and review state. Never invent missing figures, dates, amounts or opportunities.
- Maintain separate `government_intelligence_items` identity and delivery receipts; never insert into `canonical_items` or `signals`, and never use tender Telegram delivery receipts.
- First run is review-only: coverage count, candidates, excluded reasons, source evidence and a Chinese preview. Do not automatically send a new Telegram stream until real evidence and output format pass acceptance.
- After approval, send a separate clearly labeled Government Intelligence digest once daily through Bangkok's existing Telegram bot. No independent bot or Mac direct-to-SignalForge TG route.
- Dedup by official issuer document identity and evidence hash, with material-change review; rehosting, URL changes and formatting alone do not create new items.

## Release gates

1. Update PRD with approved scope exception while keeping Tender Core's existing exclusions for its own path.
2. Test classification against real S01 image notices: MCDC fuel tender stays in Tender review path; Mandalay Convention Centre lease is a Government Intelligence candidate, not a tender.
3. Real-source coverage audit: candidates + filtered items + missed high-value notices; bilingual evidence traceability.
4. Human review of Chinese digest preview; only then enable independent Bangkok Telegram digest and perform live delivery acceptance.

## Explicit non-goals

No generic all-news crawler, project precursor scoring, multi-tenant personalization, extra LLM calls for every page, or changes to tender admission/health logic.
