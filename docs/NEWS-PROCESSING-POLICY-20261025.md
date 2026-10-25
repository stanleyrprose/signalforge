# News processing and cleanup — owner amendment 2026-10-25

Status: owner-approved behavior and explicit PR/Merge/deployment authorization received 2026-10-25. Release verification is now in progress; no production PASS is claimed before actual rollout. This amendment supersedes earlier news-only retention and unreadable-page blocking rules; historical records keep their dated results.

1. After both Telegram PDF and Digest have confirmed durable message receipts, remove all content files belonging to that task on Mac and Bangkok: originals, OCR, per-task processing DBs, source text, translations, prompts/model outputs, PDFs, Digest, render files and superseded revisions. Retain only minimum identity/hash/coverage counters and independent dedup/delivery receipts outside content. Shared Tender Core DBs, delivery ledgers, code, configuration and credentials are outside this deletion scope. Pending/unknown delivery content is not cleaned.
2. Readable low-confidence content is forcibly extracted through the existing source-evidence controls and marked 待核. A low OCR score or small word count alone is not grounds for omission.
3. Truly unreadable pages receive a page number and explicit reason. Skip those pages, retain all other readable news, and generate/send PDF plus Digest. PDF and Digest disclose skipped pages; this is not a claim that those pages contained no news. If no Digest story qualifies, send an explicit empty-result Digest with the PDF, never invented news.
4. No regression/system tests, new PR, CI or Merge without a new explicit approval for those actions. Current work is code/docs and static review only. Earlier test counts and deployed releases do not validate this amendment.

The previous runtime is still active until separately approved release and coordinated deployment. New sender admission and producer fields must be deployed compatibly. Do not run an unmerged development branch as production to bypass the gate. Cleanup failure retries cleanup only and must never resend.


Static review checkpoint: Python syntax compilation passed; no application execution, regression/system tests, CI or production rollout was performed for this amendment. Existing tests that encode earlier original-retention or unreadable-page blocking expectations are historical to that contract and have not been run as evidence for the new behavior. The next authorized acceptance must update those expectations and verify receipt-gated full-content cleanup, low-confidence forced extraction, unreadable-page markers and unchanged Telegram idempotency.

Latest authorization: the owner explicitly requested PR creation, Merge and real deployment after the initial static-only hold. Required CI and affected-path verification are now permitted for this slice; previous static-only statements describe the earlier checkpoint.
