# S15A MPA Parser Preview — 2026-09-04

**Status:** `PREVIEW PASS / PRODUCTION ONBOARDING DEFERRED`

## Scope

This verification evaluates whether the manually imported Myanma Port Authority (MPA) evidence is structurally suitable for SignalForge canonical onboarding.

It is intentionally non-production:

- S15A remains in `deferred_sources`;
- no S15A source adapter is registered;
- no S15A scheduler path is enabled;
- no canonical item or signal is written;
- no unattended SignalForge→Mac invocation exists;
- no new production dependency is added.

## Listing evidence

Input evidence is the real Mac Browser Plane C0 artifact acquired from:

```text
https://www.mpa.gov.mm/tenders-and-announcement/
```

Artifact evidence from the controlled Manual Provider Bridge run:

```text
HTTP             200
Artifact bytes   252,512
SHA-256          c016d4efcae50f271e5e6860e1567650ee3d215c4ef7d9d31bd029ed4a0ec810
Browser Job      c082bb94-e001-42ba-adeb-564a7fa40878
```

The listing is server-rendered HTML with deterministic rows:

```text
publication date
announcement/tender title
issuer-original detail URL
```

The preview parser extracts all **181** rows from the captured page without Browser DOM execution.

## Title-only provisional classification

After adding explicit disposal/sale semantics, the title-only preview reports:

```text
Total                         181
Provisional TENDER            152
Provisional AUCTION_NOTICE     29
Provisional UNCLASSIFIED        0
```

These counts are deliberately labelled **provisional**.

Explicit disposal/sale indicators include:

```text
လေလံ                    auction
ရောင်းချ                 sale/sell
စာရင်းမှ ပယ်ဖျက်         decommission/remove from register
မလိုအပ်တော့              no longer required
သံတိုသံစအဟောင်း          old scrap steel
ကုန်သေတ္တာအခွံ            empty/container shell disposal context
```

A 30-record evenly distributed human review across the 2021–2026 listing found the revised title-level classification consistent with visible title semantics for procurement, repair, service, equipment purchase and explicit sale/auction records.

However, title-level semantics are **not sufficient for final SignalForge `item_kind`**.

## Critical classification contradiction

Listing record:

```text
02/06/2026
Open Tender Invitation for three Tugs
```

looks like a procurement tender from the title alone.

The linked official PDF states:

```text
The following three Tugs ... will be auctioned through an open tender system
```

Therefore the correct business interpretation is an asset disposal / auction, not a procurement opportunity.

This is direct evidence that:

```text
MPA listing title
!= authoritative final business classification
```

The preview contract therefore exposes:

```text
provisional_item_kind
classification_status = TITLE_ONLY_REQUIRES_DETAIL_PDF
```

and does not claim a final canonical `item_kind`.

## Stable identity audit

The listing exposes WordPress slugs but not numeric post IDs. Detail pages expose a standard WordPress shortlink:

```html
<link rel='shortlink' href='https://www.mpa.gov.mm/?p=<post_id>' />
```

Six live detail probes across years and types all returned HTTP 200 and stable numeric IDs:

```text
2026-08-21 AUCTION_NOTICE  post_id=38289
2026-06-02 title-TENDER    post_id=37867
2026-05-11 TENDER          post_id=37745
2025-05-12 TENDER          post_id=35819
2024-08-06 AUCTION_NOTICE  post_id=34155
2022-07-20 AUCTION_NOTICE  post_id=2392
```

Recommended future canonical identity if S15A is onboarded:

```text
mpa:<wordpress_post_id>
```

The listing slug remains provisional only until the detail shortlink is observed.

## Detail-page structure

Four representative detail pages were audited:

```text
Open Tender Invitation for three Tugs
Generic Burmese Open Tender / Marine Paint
Port EDI Application Operation and Maintenance
Battery (With Acid) 9 Items
```

All four expose exactly one official MPA PDF through an iframe `data-src` URL.

Examples:

```text
Three-Tug-Tender-Eng.pdf
Marine-Paint-Tender-2026.pdf
Open-Tender-Port-EDI-app.pdf
Battery-9-Item-Tender-2025.pdf
```

This means the detail HTML is mainly a stable identity + PDF locator layer. Business-critical tender details live in the PDF.

## PDF accessibility and value audit

The four official PDFs were fetched through installed Mac Browser Plane C0 with strict TLS and all returned HTTP 200.

Current Mac development Python already has `pypdf`; no package was installed for this preview. Text extraction was used only as a non-production audit aid.

Results:

### Three Tugs

```text
HTTP        200
bytes       101,698
pages       2
text chars  2,483
```

The PDF reveals the critical auction/disposal semantics absent from the listing title and multiple operational dates.

### Marine Paint / office stationery

```text
HTTP        200
bytes       105,788
pages       1
text chars  1,070
```

The PDF contains actual purchase scope and a tender submission deadline (4-6-2026 13:00), plus tender-form sale dates.

### Port EDI Application O&M

```text
HTTP        200
bytes       89,201
pages       1
text chars  1,713
```

The PDF contains the service scope, tender number and one-year service period, plus tender schedule information.

### Battery (With Acid) 9 Items

```text
HTTP        200
bytes       110,991
pages       1
text chars  1,091
```

The PDF contains procurement scope and submission deadline (29-5-2025 13:00), plus tender-form availability dates.

## Decision

The MPA source is technically attractive:

- Mac C0 acquisition is stable;
- listing extraction is deterministic;
- detail post identity is strong;
- PDF URLs are issuer-original and deterministic;
- sampled PDFs are text-native enough to expose useful commercial fields.

But **listing-only onboarding is rejected** because it can misclassify disposal auctions as procurement opportunities and omit deadline/scope information.

S15A remains deferred until a separately reviewed PDF supplementary extraction/classification slice is justified.

Required future gate before production onboarding:

```text
Mac/manual acquisition
-> listing parser
-> detail post-id + PDF locator
-> PDF text extraction
-> final TENDER vs AUCTION_NOTICE classification
-> deadline/scope/reference extraction
-> canonical validation
```

This gate does not imply a remote Mac invocation contract. Manual Provider Bridge may continue to provide controlled evidence while the business value is evaluated.

## Implementation added in preview branch

The preview-only code provides:

```text
signalforge mpa-preview --html <response.html> [--limit N]
```

with bounded output and no DB writes.

It also provides pure parsers for:

```text
listing rows
provisional title classification
WordPress post ID
single official PDF iframe URL
```

`mpa-preview` is intentionally absent from the VPS Worker verb manifest.
