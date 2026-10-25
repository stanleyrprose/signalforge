# S01 / S52 / S53 新闻日报交付契约

Status: approved scope and behavior. Runtime observations and release evidence: [operations record](CURRENT-OPERATIONS.md). Updated 2026-10-25.

## Source identities and product boundary

[News inventory](../registry/News-Sources-v1.json) defines current operational aliases: S01 official portal news; S52 = km / Kyemon《镜报》; S53 = mal / Myanma Alinn《缅甸之光》. The two numerical newspaper bindings are prospective aliases effective with this reconciliation, not claims about inconsistent historical labels. Historical receipts remain keyed by km/mal and must not be relabeled.

Tender Core uses its own Source Registry, canonical TENDER, signals, schedule and receipts. S01 news and S01 Tender Assurance coexist. Newspaper activation does not add S52/S53 to the tender registry.

## Daily content

Acquire original source evidence → extract/OCR → deduplicate → Chinese processing → full body attachment and AI Digest → Bangkok Telegram → independent durable receipts → both-host content cleanup.

- S01 includes all recognizable accessible news/information within bounded pagination, regardless of procurement or importance. Its body attachment is UTF-8 Markdown; importance affects Digest ordering only.
- S52/S53 collect their daily newspaper issues, omit advertisements and boilerplate, and include all substantive extracted news in Chinese PDF.
- Readable low-confidence material must be extracted and marked 待核. Unreadable pages/items retain page/URL and failure reason, are skipped, and do not suppress successful content.
- Digest prioritizes politics, policy, economy, diplomacy/geopolitics, international relations, conflict, livelihood and society. Facts, amounts, dates and attribution must be source-backed; uncertainty remains visible.
- AI Provider choice is an engineering decision based on availability, quality, cost and contract. Current workers use authenticated Mac Codex CLI; the product does not permanently require that model/provider.

## Dispatch and recovery

Each source has one successful edition per source date, separate schedule, deduplication, health and receipts. Bangkok alone formally sends SignalForge Telegram.

S01 attempts/reuses Digest before body upload; missing, invalid, rejected or ambiguous body delivery cannot suppress Digest. A Digest failure also cannot suppress the body attempt. Failed components request a separately receipted reason notice. Telegram/SSH-wide outages can prevent that notice; retain explicit failure state. AI quota exhaustion sends the independently deduplicated quota notice and preserves validated progress.

SUCCESS requires a positive Telegram message ID. Explicit rejection is FAILED; ambiguous/PENDING/UNKNOWN outcomes require reconciliation before repeating that component. Success is never overwritten or resent. The current due S01 date takes priority, with at most one prior unfinished date attempted per invocation; one date's failure does not prevent attempting the other. Historical recovery does not invent publication timestamps or substitute an old newspaper issue.

S52/S53 retain independent PDF and Digest component receipts and the existing approved deduplication/human content acceptance; this amendment does not reopen those reviews.

## Cleanup and acceptance

Remove all task-owned originals, OCR, per-task SQLite, translated/AI content, body files, Digest/render files and superseded revisions only after Digest and the selected body attachment have confirmed durable receipts. Retain minimum identity/hash/coverage/dedup/receipt state; protect shared Tender DBs, code/config and credentials. Cleanup failures trigger cleanup-only retries.

For each source verify scheduler execution, actual source content/coverage, extraction/Chinese content, body integrity, Digest, Bangkok sending, independent message IDs/receipts and cleanup on both hosts. Do not infer delivery from rendering, test success or a loaded timer. Detailed S01 body/failure semantics: [Markdown amendment](S01-MARKDOWN-INDEPENDENT-DELIVERY-20261025.md). Historical transport-only exclusions do not revoke this contract.
