# Telegram Burmese → Chinese via Mac OAuth — Production Closure — 2026-09-12

## Scope

This closure covers presentation-only Myanmar/Burmese → Simplified-Chinese translation for SignalForge Telegram delivery. It does **not** change canonical evidence, Signal facts, deadlines, references, source routing, delivery identity, or Browser Plane C0–C3 capabilities.

Default provider priority is:

1. `mac_oauth_llm`
2. Microsoft Translator, if explicitly configured
3. Google Cloud Translation, if explicitly configured
4. original Myanmar text as fail-open fallback

Translation failure must never suppress a business alert.

## Architecture

SignalForge Bangkok owns an independent durable translation queue. The existing Mac pull provider reuses its restricted outbound SSH transport but translation has separate exact verbs:

- `translation-claim-v1`
- `translation-submit-v1`
- `translation-fail-v1`
- `translation-status-v1`

Browser Provider Invocation Contract remains exactly C0/C1/C2/C3. Translation is not a Browser MCP capability, does not add an inbound Mac listener, and does not expose generic shell execution.

The Bangkok forced-command wrapper and sudoers policy are release-owned and authorize only the four existing browser-provider verbs plus the four translation verbs. Arbitrary commands continue to fail closed.

## Mac OAuth runtime

Mac Browser Plane PR #43 introduced the OAuth translation sidecar and merged as:

- `e0a5af7c6b25a16f64de201f2847031e2310de1b`

Mac Browser Plane PR #44 hardened it and merged as:

- `3fee64c3fe7450bf1ed291cbbea19cf85b6485e0`
- Actions run `34683893317`
- test job `103527350347` PASS

Production Mac runtime is installed from `3fee64c3...`.

Translation uses ChatGPT OAuth through Codex CLI with:

- `gpt-5.6-luna`
- low reasoning
- ephemeral execution
- read-only sandbox
- user config/rules ignored
- constrained environment
- JSON output schema
- CLI-level disable of `shell_tool`, Browser Use, Computer Use, Apps, and Plugins
- public source text treated as inert untrusted data

Tender terminology is explicitly constrained so `အိတ်ဖွင့်တင်ဒါ` is rendered as `公开招标`, not `开标` / `开标招标`.

A real installed-runtime smoke returned:

- `အိတ်ဖွင့်တင်ဒါ 15.9.2026` → `公开招标 15.9.2026`
- `ရန်ကုန်` → `仰光`
- protected date `15.9.2026` preserved verbatim

Mac targeted provider/translation tests: `21 passed`.
Mac full suite: `72 passed`.
Browser Plane doctor remained `READY` after deployment.

## SignalForge implementation

SignalForge PR #160 merged as:

- `73e406c3b8be4d8a458e5c55a1765e5bf26c318a`
- Actions run `34682781222`
- verify job `103524377014` PASS

Local verification before merge:

- targeted translation/provider/delivery tests: `49 passed`
- full suite: `315 passed`

Important invariants:

- Telegram translation is presentation-only.
- Dry-run does not enqueue LLM translation work.
- One Telegram item batches Myanmar fields into one translation request.
- References, dates and numeric tokens are protected and validated verbatim.
- Successful translations are cached by deterministic input cache key.
- Provider error, timeout, malformed output, protected-token drift, missing Mac heartbeat, or missing cloud credentials all fail open to the original Myanmar text.
- Microsoft and Google Cloud providers remain optional; no additional cloud translation key is required for the Mac OAuth path.

## Bangkok production deployment

Pre-deploy runtime:

- `281bdcd4886ad51ab02262b11f87fec9e188d05c`

Production deployment:

- runtime `73e406c3b8be4d8a458e5c55a1765e5bf26c318a`
- rollback `281bdcd4886ad51ab02262b11f87fec9e188d05c`
- release archive SHA256 `53e28f694b50886beca28d77e2b6288b35ac1c2b1dfb845faa80d1275907cb3f`
- Mac and Bangkok archive SHA matched exactly
- reviewed atomic deploy completed successfully
- acquisition, immediate Telegram, and digest timers all restored as `enabled / active`

The pre-existing overall `RED / DEGRADED` source-health state was caused by S16/YCDC repeated network timeouts and is unrelated to this translation feature. Recovery backlog was `0` before deployment.

## Live translation queue verification

After deployment the Mac provider heartbeat reported:

- `provider_id=mac-oauth-llm`
- `status=PASS`
- `ready=true`
- poll age observed at `2s` and later `9s`
- source language `my`
- target language `zh-Hans`

Before the smoke all translation queue states were zero.

A real no-Telegram end-to-end request was created on Bangkok:

- translation request `10541b96-a973-4fce-8616-c9bb37de6a6c`
- BKK `PENDING` → Mac pull → OAuth Luna → BKK `SUCCEEDED`
- result SHA256 `af93b74c1a88084e7fffd41d100fc3e122941939f61d1c164c1621f8dfc639ee`
- duration `7748 ms`
- usage `9950` tokens
- result values `["公开招标 15.9.2026", "仰光"]`

The follow-up queue status showed `SUCCEEDED=1`, `PENDING=0`, `CLAIMED=0`, `FAILED=0`, `EXPIRED=0`, and `ready=true`.

## Telegram presentation smoke

A production renderer smoke used a synthetic test-only Myanmar attention item and the real Bangkok → Mac OAuth translation path, but did **not** invoke the Telegram API.

The final renderer produced Chinese presentation text including:

- title `公开招标 15.9.2026`
- location `仰光`
- scope `公开招标 6,243`
- next action `公开招标`
- unchanged quantity `6,243`
- unchanged reference `TEST-6/2026`
- the explicit marker `缅文内容已机器翻译为中文（事实以官方原文为准）`

This confirms the translation result reaches the actual Telegram renderer rather than only succeeding in an isolated translation function.

Production delivery dry-runs after deployment:

- `telegram-deliver --dry-run`: `PASS`, `pending_count=0`
- `telegram-digest --dry-run`: `PASS`, already deduplicated for the day, `pending_count=0`

No Telegram message was sent as part of verification.

## Final state

**PASS / PRODUCTION ACCEPTED**

SignalForge Telegram delivery will now translate Myanmar-script presentation fields to Simplified Chinese when the Mac OAuth provider is healthy. If the Mac is unavailable, OAuth expires, quota is unavailable, validation fails, or any translation backend fails, SignalForge continues delivery using the original Myanmar text.

Canonical truth and source evidence remain unchanged. Browser Plane C0–C3 remains unchanged. No public Mac listener was introduced.
