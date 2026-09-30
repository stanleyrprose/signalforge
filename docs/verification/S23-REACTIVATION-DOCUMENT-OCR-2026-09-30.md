# S23 Ministry of Construction — Reactivation with Document OCR

Date: 2026-09-30 (Asia/Yangon)

## Decision

Reactivate S23 as an ACTIVE_PRIMARY issuer-original Tender source.

The historical strict-TLS blocker is no longer present: the official listing returns HTTP 200 under normal TLS verification from both Bangkok and the Mac Browser Plane. Current tender attachments are scan-only PDFs, so customer-ready business fields use the separately authorized Mac DOCUMENT_OCR capability.

## Authority boundary

- Listing/canonical identity/deadline date: Ministry of Construction issuer-original HTTPS page.
- OCR input: issuer-original PDFs under https://construction.gov.mm/storage/TinDar/.
- OCR is enrichment only.
- OCR business fields are accepted only when the PDF OCR contains the same deadline date as the official listing.
- If OCR confidence/shape/cross-check is insufficient, scope/quantity remain incomplete and the Telegram Customer-Ready Gate suppresses delivery.
- No TLS bypass is introduced.

## Live evidence

Listing:
- Mac strict TLS: HTTP 200, ~147 KB.
- Bangkok strict TLS: HTTP 200, ~147 KB.
- Current records: 2.

Current scan-only documents:
1. Yangon–Mandalay Expressway rest-camp restroom service tender
   - official listing deadline: 2026-10-12
   - OCR recovers 5 service locations
   - OCR close time: 16:00
2. Yadanar Theingha Bridge rehabilitation tender
   - official listing deadline: 2026-10-09
   - OCR recovers bridge length 2,480 ft
   - procurement/transport of construction materials in packages above/below MMK 200 million plus machinery/vehicle rental
   - OCR close time: 16:30

## Runtime design

S23 remains Direct HTTP for its listing. Scan-only official PDFs are enriched through a source-specific PIC target using DOCUMENT_OCR on mac-mm-01.

Successful enrichment is cached in canonical payload by attachment URL. Unchanged documents do not request OCR every polling cycle.

## Customer output contract

S23 is subject to the same 137/138 Telegram contract as all customer Tender cards:
- Chinese-readable output;
- procurement scope;
- quantity/scale;
- confirmed-open deadline;
- no UNKNOWN;
- no untranslated Myanmar text.

Incomplete OCR therefore reduces output volume rather than reducing quality.
