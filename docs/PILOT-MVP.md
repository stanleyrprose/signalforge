# SignalForge Tender Radar Pilot MVP

## Product promise

SignalForge delivers official Myanmar government/SOE tender changes to Telegram in clear Simplified Chinese, with the procurement facts visible before the user opens the original source.

Each notice prefers:
- buyer / procuring entity;
- procurement scope / item description;
- quantity / lot / units when explicitly available;
- explicit price / budget / amount when present;
- tender / reference number;
- submission, form-sale and opening dates where available;
- location; and
- direct official-source evidence.

Missing facts remain missing. The pilot never invents quantity, price, deadline or tender identity.

## Pilot customer

Initial ICP:
- Chinese equipment exporters;
- local distributors representing Chinese suppliers;
- EPC / system integrators;
- telecom / ICT suppliers;
- power, energy, engineering and construction suppliers.

## Business profile

Customer-specific filtering is deterministic and optional.

Fields:
- profile_id / customer name;
- delivery_mode: ALL_TENDERS or MATCHED_ONLY;
- relevance_categories;
- product keywords;
- target buyer keywords;
- explicit exclusion keywords;
- minimum match score.

The current production owner feed should remain ALL_TENDERS unless explicitly configured otherwise.

## Matching boundary

Rules Before LLM:
- category match = structured relevance metadata;
- product match = exact normalized keyword containment in tender facts;
- buyer match = exact normalized keyword containment in issuer;
- exclusion match is fail-closed;
- no LLM decides whether an official tender exists;
- no fuzzy model is allowed to mutate canonical facts.

LLM/translation may improve Chinese presentation only after the tender fact has been admitted.

## Pilot delivery

Primary channel: Telegram.

Pilot flow:

Official source
→ acquisition / OCR when authorized
→ canonical TENDER
→ Signal
→ Chinese presentation
→ optional Business Profile match
→ Telegram
→ official source link

No dashboard is required for the first paying pilots.

## Commercial validation

Before building self-service SaaS, onboard 5–10 pilot companies manually.

Ask one concrete question:

Would you pay RMB 200–500/month for a feed that monitors Myanmar government/SOE tenders and sends only relevant procurement notices in Chinese with scope, quantity, price when available, deadlines and official evidence?

Track:
1. relevant tenders delivered;
2. customer opened / acknowledged;
3. customer marked worth reviewing;
4. customer took a business action;
5. bid / quotation / partner outreach initiated.

The North Star is not source count or raw Signal count. It is customer action caused by relevant tender intelligence.

## Explicitly out of scope for Pilot MVP

- public signup/auth;
- billing;
- public API;
- CRM;
- opportunity pipeline management;
- generalized early-project precursor discovery;
- autonomous bid/no-bid decisions;
- automatic tender submission;
- arbitrary browser fallback;
- unreviewed fuzzy project-to-tender linking.

Only after paid pilot validation should a Cloudflare Worker/D1 self-service control plane be considered.
