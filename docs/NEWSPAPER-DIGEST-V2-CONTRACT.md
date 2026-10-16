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

## V2.1 审核版投递（2026-10-16）

用户反馈：外汇市场报价表缺具体可核的价格、单位与日期，外交/地缘政治比例过低。Mac V2.1只在有**经原报核实的币种、买卖价、单位、日期**时准许报价表进入Digest；当期外汇表OCR单位缺失，已从Digest排除（完整版PDF保持原样）。外交从V2一条提升为V2.1的三条：缅印项目MOU、缅日议会交流组织、缅越外交会见。115/115真实AI评估直接复用，无额外模型运行；Telegram消息分配12条，独立正式Tender Canonical。

Mac生成 `Chinese-News-Telegram-Digest-v2.1.json`，通过现有 `newspaper-digest-v2` schema和PDF SHA验收。Bangkok端 `tools/send_newspaper_daily_digest_tg.py` 新增 `--review-tag v2-1`，在人工作业 `--digest-only --preview` 下按修订版本保存**独立幂等回执**，不覆盖之前V2消息395回执或正式生产日刊回执。**Bangkok SignalForge Bot 已向用户TG发送 V2.1 人工验收 Digest：消息ID396。** 先前已通过的完整中文PDF消息391未重发。审阅回复在ChatGPT会话 `V2.1 PASS` 或 `V2.1 REVISE`，目前仍待用户反馈。

开发分支尚未PR/CI/Merge或按日报调度部署；其他SignalForge生产来源/推送不因这次人工审核发生变更。
