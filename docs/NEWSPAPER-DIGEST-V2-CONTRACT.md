# Bangkok SignalForge Bot newspaper Digest V2 transport contract

**Development / not deployed** · 2026-10-16.

The Mac-produced Chinese full-newspaper PDF remains the source of truth; a separate AI-based editorial Digest may accompany the PDF. User priority: Myanmar politics, policy, domestic conflict/peace, economy, diplomacy/geopolitics/international relations, livelihood and society. Routine tender and construction business are not allowed to monopolize the Digest.

`tools/send_newspaper_daily_digest_tg.py` continues to accept the prior V1 format for previously sent messages, and adds stricter V2 admission:

- `schema_version=newspaper-digest-v2`.
- `selection_method=AI_SEMANTIC_WITH_RULES`; legacy rules-only cannot masquerade as AI.
- `ai_assessed_count == edition_news_count`: every article in the published full edition assessed.
- `ai_input_fingerprint` is SHA-256 over current article bodies, version/model and prior history.
- `novelty_baseline=AVAILABLE|NO_HISTORY` — no claims of information delta without actual comparable previous editions.
- Each selected item contains a Chinese evidence-bounded `why_it_matters` and `novelty_status`.
- PDF SHA and issuer document SHA match the provided bundle; Telegram messages remain inside provider limits and retain independent paper/date receipt state. Human-review issues use Digest-only mode to avoid redelivering an already accepted PDF.

AI inference runs on the Mac with its existing authenticated Codex account. Bangkok never calls a model: it only verifies and sends validated payloads via the existing SignalForge Telegram Bot. This **does not** write tender Canonical records or alter the current 28-source Bangkok production schedule.

2026-10-16 the first Mac AI call hit a temporary OAuth quota limit, but **after user confirmed quota recovery the real 115/115 articles completed**. The actual V2 JSON passed validation on the Mac and was transferred to the Bangkok VPS. **Bangkok sent the AI V2 Digest-only preview via the existing SignalForge Bot, Telegram message ID 395.** The previously approved full R06 PDF (Telegram message 391) was not resent; V1 Digest message 394 and its delivery receipt remain intact. There is no 7-day historical baseline, so novelty remains `UNKNOWN`; no new paid model or credential was provisioned. User acceptance of the V2 Digest is still pending, with no PR/merge/daily production release.

Project source: Mac repo `scripts/newspaper_digest_ai.py`, editorial design `docs/NEWSPAPER-TELEGRAM-DIGEST-REV2.md`. This Bangkok repo's schema contract must be merged/deployed together with the Mac V2 payload producer, after user authorization.
