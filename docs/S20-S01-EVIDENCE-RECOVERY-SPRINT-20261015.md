# SignalForge Sprint: S20 PDF evidence recovery + S01 issuer tender extraction

> Historical sprint snapshot: the development/release status, counts and future actions below describe 2026-10-15 only. This is Tender Core evidence work, not the S01 news product. For current scope see [the news contract](S01-S52-S53-NEWS-DELIVERY-CONTRACT.md); for current observed deployment see [the takeover audit](NEWS-TAKEOVER-AUDIT-20261024.md). Preserve the dated results.

Date: 2026-10-15
Status: DEVELOPMENT BRANCH; NOT TESTED / NOT RELEASED
Baseline: GitHub main `7370156326f499465ea1136db45ca672b0644f47`

## Product target

Recover meaningful and defensible tender facts for government / SOE procurements, without adding sources, workflows or LLMs. Success is **not** a higher GREEN count; measure (1) independently evidenced new canonical tenders, (2) issuer-evidenced item, quantity/lot and *bid submission deadline* on the **same** canonical, and (3) verified missed or duplicate Telegram signals.

## Actual issuer evidence / constraints

- **S20**: 13 existing tender canonical rows have no raw `canonical_items.deadline`. Historic separately reviewed overlays can carry deadlines and quantities in opportunity/quality views. Recent issuer HTML pages link to PDF documents whose exact original addresses return HTTP 404, including `EPGE-2352.pdf`, `EPGE-2277.pdf` and `YESC-5357.pdf`. Verified GET against `/mm/userfile/`, `/userfile/` and www host also returned 404, so do not claim the latest documents are restored or that missing bid dates are known.
- **S01**: the live National Portal currently presents two reviewed image-backed issuer notices (not text PDF documents). Reviewed fuel procurement has 85,000 / 20,000 / 45,000 gallons, but no trustworthy bid-submission deadline; the independently reviewed Convention Centre item is an **asset lease**, not a procurement tender. Result is **zero** eligible canonical tenders, not a fetch failure.

## Implementation for this sprint

1. **S20:** The existing five-document, 45-day PDF availability check stays bounded. When an issuer PDF is actually available, a second same-origin HTTPS GET (2 MB limit, 6s timeout) archives the original exact PDF and SHA-256 under the private evidence root. Native PDF text is retained separately for evidence review. Scanned / malformed PDFs remain review-only; recovered text, HEAD metadata and web snippets never fabricate a bid deadline or create a signal. Historical identity-matched reviewed attachments remain usable as independently sourced quality evidence.
2. **S01:** The immutable reviewed-image manifest is keyed by actual source image SHA-256. Promotion requires an existing HUMAN_APPROVED official-image row, exact hash match, verified formal *procurement* nature, non-empty issuer/scope/quantity, and a separately verified unambiguous **bid-submission** deadline. Document-sale and tender-opening dates are expressly ineligible substitutes. Canonicalization uses existing dedup/receipts; a historical expired deadline creates no NEW signal. Identical image hashes are not emitted twice.
3. **Daily report:** present how many S01 images were reviewed, blocked or actually inserted; show S20 official 404s, recovered original PDFs and remaining OCR/review queue. Do not count OCR candidates or stale approved facts as new current tenders.

## Acceptance matrix for a separately authorized test and release

| Gate | Expected |
|---|---|
| S01 fuel image, no bid submission deadline | Block; not canonical / not Telegram |
| S01 venue lease with date | Exclude; not a procurement |
| S01 future original image, independent verified issuer + item + lot + bid deadline | One canonical / one signal, second run zero duplicates |
| S01 wrong hash / other host / OCR alone | Fail closed |
| S20 official HEAD 404 | Explicit missing evidence; zero fabricated data |
| S20 verified official PDF appears | Capture original sha/file; native text review-only, no unreviewed auto deadline |
| S20 invalid/redirected/non-PDF or oversize | Fail closed |
| 28-source baseline, OCR, Telegram, daily-cycle | Regression unaffected |
| Production release | Separate approval for tests, PR/CI/Merge, deployment and live measurements |

### Metrics (distinguish baseline from success)

- **Baseline:** S01 0 verified canonical; S20 13 canonical with 0 raw deadlines, although some old reviewed attachment overlays contain independent dated evidence.
- **Real-world improvement:** Count new *source-backed* tenders and additional verified item / quantity / submission-deadline fields only after a successful authorized production cycle. Code coverage and mocked successes are not business wins.
- **Unknown until live capture:** whether MOEP rehosts currently broken PDFs; whether new S01 issuer-authored images supply actual submission deadlines. Neither can be inferred.

S21 true-cycle dedup verification is independently scheduled after the 2026-10-16 06:30 Yangon acquisition. No change to source cadence.
