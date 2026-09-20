# External Official Review Packet v0 — 2026-09-20

## Goal

Turn fresh S01 National Portal unresolved official-document leads into bounded, evidence-backed review packets so a reviewer no longer has to manually download a text-native PDF and hunt for scope, dates and action windows before deciding whether the item can become a reviewed `VERIFIED_EXTERNAL_OFFICIAL_OPPORTUNITY`.

This is a pre-review capability only.

## Authority boundary

Every packet declares:

- `authority=HUMAN_REVIEW_REQUIRED`
- `production_effect=NONE`
- `writes=NONE`
- `review_state=PENDING_HUMAN_CONFIRMATION`
- `canonical_truth=false`
- `verified_external=false`

The packet cannot create or mutate:

- canonical items;
- Signals;
- misses;
- manual promotions;
- reviewed coverage-gap registry records;
- verified-external opportunities;
- opportunity counts.

Promotion still requires a separate human-reviewed change satisfying the existing alternate-official-coverage rule in `GOAL.md`.

## Input boundary

v0 accepts only an unresolved S01 lead that is already admitted by the daily official-review radar and satisfies:

- `evidence_kind=NATIONAL_PORTAL_HOSTED_DOCUMENT`;
- `aggregator_only=true`;
- `canonical_truth=false`;
- non-empty `target_source_hint`;
- HTTPS host exactly `myanmar.gov.mm` or `www.myanmar.gov.mm`;
- path begins with `/documents/`;
- normal HTTPS port only.

Arbitrary external targets are rejected before any fetch.

## Acquisition boundary

The packet builder:

1. downloads at most 8 MB;
2. uses a 12-second per-document timeout;
3. verifies PDF magic;
4. computes SHA-256;
5. parses text with the already packaged `pypdf` dependency;
6. retains only bounded text/evidence excerpts in the packet.

The daily digest enriches at most the first two review candidates. This keeps the packet feature bounded even if S01 returns many unresolved leads.

An unexpected packet-builder exception is converted into `PACKET_BUILD_FAILED` and does not fail the Business Digest.

## Extraction semantics

v0 is intentionally deterministic and evidence-first.

It does not ask a model to invent structured fields from arbitrary text.

For the reviewed S13/MPT numbered-tender template profile (`S13_MPT_NUMBERED_TENDER_V0`), it recognizes:

- PDF header — issuer-document evidence;
- section 1 — procurement / project scope evidence;
- section 2 — tender-form sale start;
- section 3 — tender-form sale close;
- section 4 — site-survey date;
- section 5 — bid-submission window / proposed deadline;
- section 6 — tender-form / submission-location evidence.

For other issuers, v0 uses `GENERIC_TEXT_ONLY_V0`: it may expose header/scope text as review evidence, but it does **not** reuse MPT section-number semantics to infer dates or actions. Such packets remain partial until that issuer/template is separately reviewed.

All extracted business values are stored under `proposed_fields`.

Important naming:

- `proposed_deadline`, not `deadline_verified`;
- `project_location_hint`, not verified location;
- `issuer_hint`, not verified issuer;
- `next_action_summary` is derived from proposed date/time fields.

No proposed field is accepted as reviewed truth by the packet itself.

## Text-native vs OCR boundary

Packet status:

- `TEXT_NATIVE_REVIEW_READY` — sufficient text plus scope and proposed bid deadline;
- `PARTIAL_REVIEW_PACKET` — text exists but either required evidence is incomplete or the issuer/template semantics have not been reviewed;
- `NEEDS_OCR_OR_MANUAL_REVIEW` — PDF text layer is too sparse;
- `FETCH_FAILED`;
- `NOT_PDF`;
- `PDF_PARSE_FAILED`;
- `REJECTED_INPUT`.

v0 does not add a new OCR runtime.

A scan-only official PDF is explicitly escalated to OCR/manual review rather than guessed from filename, Portal metadata or unrelated text.

## Myanmar date/time normalization

The reviewed Pobbathiri PDF exposed two extraction edge cases that v0 now handles deterministically:

1. pypdf split the site-survey year as `20 26`; the date parser accepts spacing inside the four-digit year and validates the resulting calendar date.
2. section 3 states evening `04:30` in Myanmar (`ညနေ/ညေန` context); a single time under explicit PM/evening context is normalized to `16:30`.

Bid-submission section 5 with `09:30 ... 14:00` remains an explicit time window and is not subject to the single-time PM conversion.

## Pobbathiri live smoke

Official document:

`https://myanmar.gov.mm/documents/20143/0/Newspaper+advertiement+10082026.pdf/aa3cebae-2f59-5c3c-e840-640c99f0cb92`

Live result:

```text
status                  TEXT_NATIVE_REVIEW_READY
document_sha256         3dd5dd18a2395ba1bb18bdc31c9fa9850a98aced98fb05b7453c4380d24c9eea
document_bytes          34575
pdf_pages               1
project_location_hint   Pobbathiri Township, Nay Pyi Taw
tender sale start       2026-09-11
tender sale close       2026-09-24 16:30
site survey             2026-09-25
bid submission          2026-09-29 09:30-14:00
```

Derived action summary:

```text
Tender form sale closes 2026-09-24 16:30;
Site survey 2026-09-25;
Bid submission 2026-09-29 09:30-14:00
```

The SHA and all key dates/times above match the already human-reviewed Pobbathiri record in `Reviewed-Coverage-Gaps-v1.json`.

This is validation evidence for the extractor, not automatic re-verification of the record.

## Business Digest v7

For at most two unresolved candidates, Business Digest now attaches `review_packet`.

Structured summary adds:

- `official_review_packet_ready_count`.

Telegram shows:

- candidate identity and exact official document link;
- `文本PDF预审` when text-native packet is ready;
- SHA prefix;
- proposed project-location hint when available;
- compact translated scope evidence;
- derived proposed action summary.

For a text-native PDF from an unreviewed issuer/template:

```text
预审：PDF文本已提取，但该机构模板语义尚未核验；不自动解释编号日期
```

For scan-only PDFs:

```text
预审：PDF文本层不足，需 OCR/人工读取
```

For fetch/parse/build failure, the original candidate remains visible and the digest instructs the reviewer to open the official document manually.

The footer states that all packet fields are `proposed evidence` and require human confirmation before any upgrade.

## Failure semantics

A packet failure never means the underlying lead is invalid.

It means only that automatic pre-review did not complete.

Therefore:

- candidate remains visible;
- opportunity count remains unchanged;
- no miss is opened;
- no canonical truth is inferred;
- no verified-external truth is inferred;
- reviewer can still open the exact official document.

## Tests

Dedicated unit coverage locks:

- strict Portal-document boundary;
- no fetch for rejected external URL;
- SHA calculation;
- deterministic numbered-section extraction;
- spaced-year normalization;
- evening 04:30 -> 16:30 normalization;
- site-survey extraction;
- bid-submission window extraction;
- scan-only PDF -> OCR/manual-review state;
- fetch failure stays review-only;
- only first two daily candidates receive packets;
- one ready + one OCR packet renders correctly;
- packet-builder exception does not fail the digest;
- packet candidates do not increment current opportunity totals;
- Telegram output remains subject to the existing 4096-character limiter.

## Explicit non-goals

v0 does not:

- add a generic LLM extraction backend;
- add OCR to Bangkok;
- add Mac Browser Plane OCR invocation;
- persist downloaded candidate PDFs to production evidence storage;
- auto-edit `Reviewed-Coverage-Gaps-v1.json`;
- auto-promote a packet;
- infer truth from National Portal `Closing Date`;
- change S01 into a canonical source;
- change S13 coverage status;
- change scheduler or immediate Telegram-alert behavior.
