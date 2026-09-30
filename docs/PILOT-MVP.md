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

Each paying pilot has an independent `profile_id`. Pilot delivery receipts are stored separately from the owner feed, so the same Tender Signal can be delivered once to each matching pilot without one customer's receipt suppressing another customer's notification. Manual promotions remain owner/operator-only; pilot delivery is canonical Tender-only.

Manual pilot delivery uses the existing bot token with the customer's Telegram chat ID and Business Profile:

```sh
SIGNALFORGE_TELEGRAM_CHAT_ID=<customer-chat-id> \
  signalforge telegram-deliver --profile profiles/customer-a.json
```

Repeated execution for the same `profile_id + canonical_key + signal_id` is idempotent.

Paying-pilot delivery also has a Business Readiness Gate. A matched Tender is withheld from the customer feed unless the deadline is confirmed open, the procurement scope is actionable, and quantity/scale is explicitly explained. If the production translation path still leaves Myanmar script in the customer message, delivery fails closed instead of sending untranslated text. Internal sentinels such as `UNKNOWN` are never customer-facing.

For a production-equivalent quality preview without writing pilot delivery receipts:

```sh
signalforge telegram-deliver \
  --dry-run \
  --translate-preview \
  --profile profiles/customer-a.json
```

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

SignalForge now keeps pilot attribution in successful Telegram delivery receipts (`profile_id` + match score) and records explicit customer outcome events.

Operator examples:

```sh
signalforge pilot-feedback \
  --profile-id pilot-ict \
  --canonical-key mpt:tender-123 \
  --signal-id sig-123 \
  --event WORTH_REVIEWING \
  --note "Customer asked sales team to review"

signalforge pilot-feedback \
  --profile-id pilot-ict \
  --canonical-key mpt:tender-123 \
  --signal-id sig-123 \
  --event ACTION_TAKEN \
  --note "Contacted local partner"

signalforge pilot-feedback \
  --profile-id pilot-ict \
  --canonical-key mpt:tender-123 \
  --signal-id sig-123 \
  --event BID_OR_QUOTE_INITIATED \
  --note "Quotation preparation started"

signalforge pilot-report --profile-id pilot-ict
```

Allowed outcome events are `ACKNOWLEDGED`, `WORTH_REVIEWING`, `ACTION_TAKEN`, `BID_OR_QUOTE_INITIATED`, and `DISMISSED`. Feedback is accepted only when the tender has an attributed successful delivery for that profile; this prevents ungrounded commercial-outcome claims.

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
