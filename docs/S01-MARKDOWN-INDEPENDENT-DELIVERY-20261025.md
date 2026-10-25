# S01 Markdown 正文与独立 Digest 投递 — 2026-10-25

Status: owner-approved; implemented, merged and deployed by PR328 at `431cc0a32aaf7440c08c5b2b6c71ab8e90ba1773`. Real Oct25 Digest484 and Markdown487 have independent success receipts; task content was removed on both hosts. See [dated operations](CURRENT-OPERATIONS.md).

## Current contract

- S01 daily Chinese body is a UTF-8 `.md` document, containing every included item, source URL, factual Chinese content, importance rationale and uncertainty. Unreadable items remain explicitly marked. This replaces the S01 PDF requirement; S52/S53 retain their newspaper PDF contract.
- Generate the Digest independently of attachment rendering/upload. Bangkok attempts Digest delivery even if the attachment is missing, invalid, rejected, timed out or has a previous UNKNOWN. A successful component is never resent. A failed Digest does not suppress the attachment.
- Definitive Telegram HTTP 4xx rejections are FAILED; transport timeout/ambiguous outcomes are UNKNOWN. UNKNOWN is never automatically reset. Notices report the affected component and safe failure reason through Bangkok, with independent durable idempotency. A notice failure must not suppress the other business component. Telegram-wide outages may also prevent the failure notice; keep explicit state for reconciliation.
- Article completion and content cleanup require Digest SUCCESS plus the selected body attachment SUCCESS. Legacy PDF manifests/receipts remain readable. A retained old PDF UNKNOWN is historical evidence, not an MD success receipt.
- The owner explicitly requested replacing the current oversized PDF with Markdown after confirming Digest receipt. Migration must reuse Digest message484, retain the old PDF UNKNOWN without resetting or retrying it, bind the new manifest/checksum, and remove superseded task content only after Markdown and Digest are confirmed.

## Scope and evidence

No Tender source-registry, canonical rules, schedule or new browser-routing framework is changed. S20 diagnostics are public read-only requests, not a production source activation.

Observed 2026-10-25 09:42 UTC: S20 `https://moep.gov.mm/mm/ignite/page/62` returned HTTP200 through Bangkok urllib (0.85s), Mac urllib (0.73s) and installed Mac Browser Plane (system_curl C0, about0.96s,186107 bytes). Browser rendering was not needed. The earlier daily timeout is a historical failure; the exact transient network/server cause is unproven. HTTP200 alone is not a tender coverage/PDF availability PASS.

This amendment takes precedence over older S01 PDF wording. Historical verification outcomes are not rewritten. The release and real delivery evidence above were added after actual deployment.
