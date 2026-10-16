# S52/S53 — Separate official newspaper sources (development branch)

Date: 2026-10-16. **Not accepted or deployed.** GitHub `main` and Bangkok production currently remain at `c42e176a` with 28 enabled sources.

## Independent sources

| New Source | Official origin | Frequency | Acquisition |
|---|---|---|---|
| S52 · Kyemon / 《镜报》 | https://www.moi.gov.mm/km/ | once daily | Bangkok direct HTTP index + strict MOI PDF issue URL |
| S53 · Myanma Alinn / 《缅甸之光》 | https://www.moi.gov.mm/mal/ | once daily | Bangkok direct HTTP index + strict MOI PDF issue URL |

The 2026-10-16 pages and edition links returned HTTP 200 from Bangkok; the 2026-10-16 Kyemon PDF is 3,602,175 bytes (32 pages). The Myanma Alinn same-day PDF is 2,787,343 bytes. No cloud browser, VPS-Beijing dependency or additional LLM provider is required to fetch source evidence.

## SignalForge boundary

- Only independently proven issuer-authored procurement tenders may generate Canonical or Telegram tender alerts.
- A whole newspaper PDF does **not** constitute one tender; headlines, speeches, private-land notices, property transfers and classified ads are not tender Signals.
- PDF native text extraction of the Oct 16 Kyemon issue contains legacy Burmese PUA glyphs. It is **not** safe to infer a procurement, quantity or deadline from that text. The initial parser fails closed for PUA-damaged pages and archives the source PDF under its evidence digest.
- If native UTF-8 pages ever contain full English tender statements, require an identifiable issuer, tender reference, explicit procurement invitation, item/quantity and bid submission deadline in the *same* short page block. Identical issuer/reference/deadline from Kyemon versus Myanma Alinn is suppressed before signal emission.
- These are new source IDs, not a replacement for S37 (MOI departmental procurement announcements) or S20's manually reviewed Kyemon second-source overlays.
- Pending acceptance: no claim of new genuine tenders, no change in the 28-source production baseline.

## Full newspaper Chinese editions: separate Mac workflow

User also requested **full, page-mapped Simplified Chinese editions** of *both complete newspapers*, not just tender extraction.

That feature is owned by the separate **private Mac repo** `stanleyrprose/macmini_automation`, branch `feat/official-newspaper-full-zh-20261016`; see `docs/DAILY-MOI-NEWSPAPERS-CHINESE.md` there.

Mac uses PDFKit + Tesseract `mya+eng` and a separately authorized translation account; SignalForge does not perform full-page translation, consume Codex OAuth quota, or send multi-page newspaper documents to the tender channel.

## Gates before production

1. Mac full-document OCR quality and page completeness demonstrated on both official PDFs, especially late-page notices/classified ads.
2. No PDF PUA text promoted as authenticated native Unicode and no speculative tender fields.
3. Focused + full regressions, PR, CI, Merge separately authorized.
4. Bangkok release separately authorized, baseline capture of S52/S53, observed evidence preserved, and genuine issuer tender examples independently cross-checked against original newspaper pages.
5. Coverage and false-positive reporting should say REVIEW-ONLY if OCR cannot prove issuer/deadline; avoid false GREEN claims solely from HTTP 200.

The new newspaper sources remain **unproven tender coverage** until gates pass. The Mac Chinese-edition workflow can be independently accepted without merging the SignalForge source changes.
