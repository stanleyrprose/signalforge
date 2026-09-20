# S23 Current PDF Deadline Recovery — 2026-09-20

## Goal

Recover the two current Ministry of Construction S23 board gaps into truthful business states without relaxing the disabled S23 strict-TLS acquisition gate.

The reviewed board items were:

- Yangon — Department of Urban and Housing Development — board `End Date 2026-09-25`;
- Mandalay — Bridge Department Construction Group (2) / Bridge Special Group (5), second open tender — board `End Date 2026-10-09`.

## Boundary

The issuer certificate remains expired. `curl` with normal certificate validation fails for both `construction.gov.mm` and `www.construction.gov.mm`.

TLS bypass was used **only for bounded locator/document recovery**. It does not re-enable S23 acquisition, does not make the issuer health GREEN, and is not itself treated as verification proof.

The existing S23 reviewed-official-document exception remains the authority boundary: issuer document + reviewed SHA + human/visual evidence may support a non-canonical `VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY`; conflicting evidence remains an unresolved coverage gap.

`DOCUMENT_OCR Contract v1` was not expanded. It remains limited to the previously frozen S01 / `myanmar.gov.mm/documents/*` provider boundary.

## Issuer board document locators

The current issuer board HTML links the two records to:

### Yangon

- board title: Department of Urban and Housing Development open tender
- board End Date: `2026-09-25`
- PDF storage path: `/storage/TinDar/tindar_1789378581_jpg.pdf`
- issuer download: `https://construction.gov.mm/letter-download/bed02200-b01f-11f1-b666-953fc0cbe05c`

### Mandalay

- board title: Bridge Department Construction Group (2) / Bridge Special Group (5), second open tender
- board End Date: `2026-10-09`
- PDF storage path: `/storage/TinDar/tindar_1789368878_တံတား.pdf`
- issuer download: `https://construction.gov.mm/letter-download/277e8a90-b009-11f1-b7d8-9993fdcb51ee`

## Dual-egress document identity

The PDF bytes were fetched independently from the Mac and Bangkok exits. Both exits returned identical SHA-256 values:

| Document | SHA-256 |
| --- | --- |
| Yangon | `177900f3bdc02ba5789d731c47f9c84c44f31fb64cd049759547895bfff25a07` |
| Mandalay | `33ce06727d4697160d8611d7ea9b227e0b8961c51f6c54c49a2f6f98427a84bd` |

Both are one-page PDFs and both have zero useful native text characters, so review required visual reading of the scan.

## Yangon reviewed result

The scan identifies the Ministry of Construction / Department of Urban and Housing Development and describes housing-development project work associated with Phase (2)/(3).

Date rows were independently re-read. The visible tender form sale row states:

`တင်ဒါလျှောက်လွှာပုံစံ ရောင်းချမည့်ရက် - (၁၆-၉-၂၀၂၆) မှ (၂၂-၉-၂၀၂၆) ထိ (ရုံးချိန်အတွင်း)`

Normalized:

- tender form sale start: `2026-09-16`;
- tender form sale end: `2026-09-22`.

The visible final submission row states:

`တင်ဒါနောက်ဆုံးတင်သွင်းရမည့်ရက်/အချိန် - ၁-၁၀-၂၀၂၆ ... နေ့လယ် ၁၁:၀၀ နာရီ`

A narrow second visual read independently confirmed the printed time as `11:00`.

Reviewed bid deadline:

- `2026-10-01 11:00` Myanmar local time.

The issuer board `End Date 2026-09-25` is therefore **not** used as the bid-submission deadline.

Disposition:

- issuer document reviewed: yes;
- issuer identity reviewed: yes;
- scope reviewed: yes;
- deadline reviewed: yes;
- canonical truth: false;
- business state: `VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY`;
- coverage origin: `S23_REVIEW`.

## Mandalay reviewed result

The scan describes 2026–2027 Mandalay bridge works and procurement / delivery of project materials.

Visual review extracted:

- tender form sale start: `2026-09-16`;
- tender form sale end: `2026-10-09`;
- bid submission deadline: `2026-10-13 09:30` Myanmar local time.

This explains why the board `End Date 2026-10-09` must not automatically be treated as the bid deadline: in the document it corresponds to the tender-form sale window, while bid submission closes later.

However, the PDF header was visually read as Bridge Special Group `(1)` while the official board title says Bridge Special Group `(5)`. A second narrow model read again returned Burmese digit `၁` / Arabic `1`. Because exact issuer/item identity remains conflicting, the document is **not** promoted.

Disposition:

- document SHA retained;
- true action window retained for review;
- `identity_conflict=BOARD_BRIDGE_SPECIAL_GROUP_5_VS_PDF_OCR_GROUP_1`;
- business state remains unresolved coverage gap;
- no verified-external count increment.

## Production semantics

This change does not:

- enable S23 canonical acquisition;
- bypass strict TLS in scheduled acquisition;
- create a canonical item or Signal;
- change the OCR provider allowlist;
- claim the Mandalay identity conflict is resolved.

It corrects the customer-facing action window and upgrades only the Yangon record whose issuer identity, scope and bid deadline are consistent across the reviewed issuer evidence.
