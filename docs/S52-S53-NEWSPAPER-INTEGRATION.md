# S52/S53 — Myanmar State Newspaper Source Integration (development contract)

Updated: 2026-10-16. Status: DEVELOPMENT ONLY — source IDs reserved; no Tender Core registry activation.

## Purpose and source identity
- S52 and S53 designate the two official MOI newspaper acquisition feeds, **Kyemon** (`km`) and **Myanma Alinn** (`mal`). The binding of each numerical ID to its paper must be confirmed against the authoritative source list before activating an executable registry; do not infer it from the number.
- Treat the original dated, publisher-hosted newspaper PDF as the primary evidence. Store the exact issue URL, publication/issue date, retrieval timestamp, SHA-256, page count and per-page OCR coverage. Never substitute yesterday's issue for missing today's issue.
- News/policy sources are independent of formal procurement sources. Do **not** add either source to `registry/Source-Registry-v1.yaml` or change Tender Core TENDER qualification.

## Reuse already operational components
- Canonical Mac producer: `stanleyrprose/macmini_automation` `scripts/newspaper_daily_delivery.py`, `scripts/newspaper_digest_ai.py`, `scripts/newspaper_news_editor.py`, and `scripts/newspaper_news_publication.py`.
- Mac acquisition uses MOI issue PDFs, PDFKit, Tesseract Burmese/English OCR and the existing **Mac Codex CLI authenticated session** for all LLM translation, editorial classification, seven-day comparison, semantic deduplication and Chinese Digest generation. Do not add Cloud GPT, antigravity, a Bangkok inference provider, new credentials or paid APIs.
- Bangkok-only delivery uses the already merged `tools/send_newspaper_daily_digest_tg.py` and `tools/newspaper_telegram_transport.py` with the existing SignalForge Bot; Mac must not send to that Bot directly.
- Preserve existing Mac `com.stanley.moi-newspaper-prepare` and `com.stanley.moi-newspaper-deliver` tasks and versioned Bangkok sender; **do not install a second S52/S53 scheduler or resend previously delivered PDF/Digest**.

## Required output, gates and evidence
1. For each paper/day, process **all** released newspaper pages and reconcile every identified news/article candidate to a disposition ledger. Exclude advertising/boilerplate from the Chinese *news* publication; never use top-N filtering to shrink the full-edition Chinese PDF.
2. Keep original attribution. Mark unverified numbers, foreign-exchange units, government/conflict claims and OCR ambiguities explicitly. Source-publisher claims are not independently corroborated facts.
3. Only the shorter Digest is selectively ranked. AI must evaluate every article in the full Chinese edition; the item count and document/source checksums must reconcile. Prior-seven-day novelty requires historical evidence; missing history means UNKNOWN, not NEW.
4. Prefer important politics, policy, economy, foreign relations/geopolitics, security/conflict and livelihoods in the Digest. Numeric FX/market tables require verifiable date, currency, quote units and amounts; otherwise exclude from Digest while retaining in the comprehensive edition where appropriate.
5. Verify source PDF SHA, Chinese PDF SHA, complete OCR/page ledger and AI-assessment completeness before Bangkok send. Deliver Chinese Digest then full Chinese PDF, maintaining independent immutable `paper/date/source-SHA` receipts from tender messages. If send outcome is ambiguous, block unattended retries.
6. Existing production schedule is **10:00 Asia/Yangon delivery target**, with early preparation and bounded afternoon recovery windows. Late/unavailable editions get a clearly marked status notification; do not manufacture completeness or on-time success.

## Acceptance and release boundary
- Existing newspaper automation already has a standalone 10:00 production schedule as documented in `macmini_automation/docs/NEWSPAPER-10AM-YANGON-PRODUCTION.md` and checkpoint. This source-integration contract does **not** establish that S52/S53 source-specific acceptance or a new release has passed.
- First verify numerical source/paper mapping, then collect real live evidence from both feeds: URL, issue date, page audit, edition PDF, AI Digest schema/coverage, Telegram receipts and repeat-run no-duplicate behavior.
- During development: dedicated branch and static review only, no tests, PR, CI, merge or production deployment until separately authorized under `AGENTS.md`.
- Do not alter the existing production timer, Bangkok Tender Core runtime, source registry, bot credentials or pending local S01 work merely by adopting this contract.
