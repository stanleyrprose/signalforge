# S01 / S52 / S53 新闻采集与 Telegram 日报交付契约

Status: owner-approved product scope; production status must be verified independently. Updated: 2026-10-24.

## Mandatory source coverage

- S01: official government news and announcements; collect all accessible news/information within bounded crawling, not only tender notices. Preserve tender qualification as a separate Tender Core pipeline.
- S52 and S53: approved newspaper sources; collect the daily editions, preserve original PDF/evidence, extract and translate substantive news to Simplified Chinese.
- Each source runs once daily, with explicit source-specific schedule, run ID, date, completion status, and error evidence. Failure of one source must not suppress the others.

## End-to-end daily delivery

For each source: acquire and record original evidence → extract/OCR → deduplicate while retaining coverage audit → translate into readable Simplified Chinese → produce reviewable Chinese PDF → generate concise, AI-assisted Chinese Digest emphasizing politics, policy, economy, diplomacy/geopolitics, conflict, livelihood and important developments → deliver PDF and Digest via the Bangkok-owned SignalForge Telegram bot → persist source/date/artifact-specific Telegram message IDs and independent receipts → clean related temporary files on Mac and Bangkok after confirmed successful delivery.

No fabricated dates, amounts, claims or source links. Do not claim delivery from a successful local render alone. A Telegram failure remains retryable and must not trigger premature cleanup. Repeated runs must not redeliver already accepted PDFs/Digests. Preserve minimum durable receipt/audit evidence and distinguish business delivery health from provider route telemetry.

## Scope clarification

The statement in `docs/NEWSPAPER-DIGEST-V2-CONTRACT.md` that S52/S53 acquisition was excluded describes only that historical transport-only PR. It is **not** a permanent product exclusion. S01/S52/S53 news acquisition, Chinese PDF translation, editorial Digest and independent daily Telegram dispatch are now in the approved SignalForge News/Policy product scope. Activation and actual production health must be established by deployment/runtime evidence, not by this document alone.

## Production acceptance

For S01, S52 and S53 separately verify: daily scheduler triggered; acquisition and source coverage; extraction/translation; valid PDF; Digest; Bangkok sender execution; Telegram API response/message ID; durable independent receipt; post-send cleanup on both hosts. Mark PASS only when all checks have evidence. Record explicit FAILED/UNKNOWN for any missing stage. Do not interrupt Tender Core.
