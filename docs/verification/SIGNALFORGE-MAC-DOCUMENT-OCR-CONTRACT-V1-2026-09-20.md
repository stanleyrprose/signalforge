# SignalForge ↔ Mac Browser Plane DOCUMENT_OCR Contract v1 — 2026-09-20

## Status

SOFTWARE CONTRACT FROZEN / MAC INSTALLED-RUNTIME LIVE VERIFICATION PASS.

This document freezes the request/response boundary for SignalForge review-only PDF OCR. It does not itself authorize Bangkok deployment.

## Invariant

Every mission-relevant official PDF admitted to the SignalForge opportunity-review surface MUST complete visual OCR before its Review Packet may be marked review-ready.

Native PDF text alone is never sufficient for review-ready status.

OCR is evidence, not canonical truth. Human confirmation remains mandatory before any verified-external promotion.

## Responsibility split

Mac Browser Plane owns:

- bounded official-PDF acquisition under Provider policy;
- PDF byte verification;
- PDFKit page rasterization;
- Tesseract `mya+eng` OCR;
- page-level OCR evidence;
- networkless OCR execution.

SignalForge owns:

- mission gate;
- independent native PDF fetch/extraction;
- evidence SHA reconciliation;
- source/template semantics;
- business-field reconciliation;
- Review Packet state;
- Business Digest rendering;
- human-review promotion boundary.

## PIC v1 authorization

Remote OCR authority is exactly:

```text
source_id        S01
source policy    2
capability       DOCUMENT_OCR
mcp_tool         document_ocr
target_role      OFFICIAL_DOCUMENT
scheme           https
host             myanmar.gov.mm
path prefix      /documents/
query            forbidden
fragment         forbidden
max PDF/request  8,000,000 bytes
max run          150 seconds
```

Not authorized:

- `www.myanmar.gov.mm`;
- arbitrary `*.gov.mm`;
- any non-S01 source;
- arbitrary Mac paths;
- raw remote `artifact_ocr`;
- shell/javascript/script execution;
- off-host redirect.

S27 and S38 retain their existing non-OCR Provider capabilities only.

## Request schema

SignalForge uses the existing Provider Invocation v1 envelope. `DOCUMENT_OCR` has no caller-controlled OCR-engine arguments; the Mac Provider owns the fixed OCR execution profile.

Required request fields:

```json
{
  "contract_version": 1,
  "provider_request_id": "<uuid>",
  "provider_id": "mac-mm-01",
  "signalforge_job_id": "<uuid>",
  "acquisition_request_id": "<uuid>",
  "acquisition_attempt_id": "<uuid>",
  "source_id": "S01",
  "source_policy_version": 2,
  "capability": "DOCUMENT_OCR",
  "mcp_tool": "document_ocr",
  "target_role": "OFFICIAL_DOCUMENT",
  "requested_url": "https://myanmar.gov.mm/documents/...",
  "final_url_policy": {
    "mode": "APPROVED_HOST_PATH",
    "https_host": "myanmar.gov.mm",
    "path_prefix": "/documents/",
    "allow_query": false,
    "allow_fragment": false
  },
  "max_bytes": 8000000,
  "max_run_seconds": 150,
  "requested_at": "<UTC timestamp>",
  "expires_at": "<UTC timestamp>",
  "idempotency_key": "sf-provider:<provider_request_id>",
  "interaction_plan": null,
  "request_sha256": "<sha256>"
}
```

The normal request validator remains authoritative for UUIDs, TTL, request SHA, source policy, URL policy and limits.

## Mac execution contract

The Mac Provider execution path is fixed:

```text
approved requested_url
    ↓
browser_fetch
    ↓
runtime-owned PDF
    ↓
verify PDF magic / byte length / fetch SHA
    ↓
document_ocr(psm=6,max_pages=12)
    ↓
require OCR input SHA == fetched PDF SHA
    ↓
portable JSON result
```

The SignalForge request cannot replace this sequence with an arbitrary MCP call or local file path.

## Raw Provider response artifact

The Provider result media type MUST be `application/json`.

The artifact contains:

```json
{
  "fetch": {
    "url": "https://myanmar.gov.mm/documents/...",
    "status": 200,
    "content_type": "application/pdf",
    "body_bytes": 34575,
    "sha256": "<B>"
  },
  "document_ocr": {
    "engine": "tesseract",
    "rasterizer": "macOS PDFKit",
    "model_profile": "tessdata_best",
    "languages": ["mya", "eng"],
    "psm": 6,
    "input_sha256": "<C>",
    "input_bytes": 34575,
    "page_count": 1,
    "processed_pages": 1,
    "page_limit_truncated": false,
    "pages": [
      {
        "page": 1,
        "image_sha256": "...",
        "text": "...",
        "line_count": 20,
        "mean_confidence": 78.5
      }
    ],
    "text": "...",
    "mean_confidence": 78.5,
    "network_access": false,
    "intermediate_images_retained": false
  }
}
```

## SignalForge normalized Provider response

`acquire_provider_document_ocr()` validates the raw response and adds:

```json
{
  "provider_contract_version": 1,
  "provider_request_id": "<uuid>",
  "provider_fetch_sha256": "<B>",
  "input_sha256": "<C>",
  "...document_ocr fields...": "..."
}
```

The wrapper rejects:

- malformed/non-JSON Provider artifact;
- missing fetch/OCR sections;
- invalid/non-hex OCR SHA;
- `fetch.sha256 != document_ocr.input_sha256`;
- `fetch.body_bytes != document_ocr.input_bytes`;
- non-2xx PDF fetch;
- `network_access != false`;
- `intermediate_images_retained != false`;
- OCR language profile lacking `mya+eng`;
- unsupported PSM;
- missing page evidence;
- inconsistent `page_count / processed_pages / page_limit_truncated`.

## A = B = C evidence invariant

For dual-evidence review:

```text
A = SignalForge independent native PDF SHA
B = Mac browser_fetch PDF SHA
C = Mac document_ocr input PDF SHA
```

A Review Packet may be `DUAL_EVIDENCE_REVIEW_READY` only when:

```text
A == B == C
```

If B != C:

```text
EVIDENCE_SHA_CONFLICT
PROVIDER_FETCH_AND_OCR_PDF_SHA256_DIFFER
```

If A exists and differs from B/C:

```text
EVIDENCE_SHA_CONFLICT
NATIVE_PROVIDER_AND_OCR_PDF_SHA256_DIFFER
```

If native acquisition is unavailable, the packet may remain OCR-only for human review but can never be dual-evidence-ready.

## MPT template v1

Reviewed profile:

```text
S13_MPT_NUMBERED_TENDER_V1
```

Only this reviewed issuer/template may interpret numbered sections as:

```text
header     → issuer-document evidence
section 1  → project/scope evidence
section 2  → tender-form sale start
section 3  → tender-form sale close
section 4  → site survey
section 5  → bid-submission date/time window
section 6  → submission-location evidence
```

OCR semantics are independently recovered from the visual text for the same fields.

All other issuers remain:

```text
GENERIC_TEXT_ONLY_V1
```

They receive mandatory OCR evidence but do not inherit MPT numbered-section semantics.

## Field reconciliation

Critical fields use one of:

```text
AGREED
NATIVE_ONLY_PROPOSED
OCR_ONLY_PROPOSED
CONFLICT
MISSING
```

For each critical field the Review Packet retains:

```json
{
  "native": "...",
  "ocr": "...",
  "status": "AGREED|NATIVE_ONLY_PROPOSED|OCR_ONLY_PROPOSED|CONFLICT|MISSING"
}
```

Critical fields:

- project location hint;
- tender-form sale start/time;
- tender-form sale close/time;
- site survey date/time;
- proposed bid deadline;
- bid submission start time;
- bid submission end/deadline time.

A conflict clears the merged field and suppresses actionable next-action output.

## Review Packet v1 states

### `DUAL_EVIDENCE_REVIEW_READY`

Requires:

- mandatory OCR completed;
- A=B=C;
- reviewed MPT template;
- proposed deadline present;
- all native critical action/date fields corroborated by OCR;
- no critical conflict.

Still requires human confirmation.

### `DUAL_EVIDENCE_REVIEW_REQUIRED`

OCR completed, but one or more critical native fields are not independently corroborated.

No actionable next-action is emitted.

### `DUAL_EVIDENCE_CONFLICT`

Native and OCR disagree on one or more critical fields.

Both values remain in reconciliation evidence.

No actionable next-action is emitted.

### `OCR_ONLY_REVIEW_PACKET`

Native text is unavailable/insufficient but OCR recovered business evidence.

Human confirmation required; never dual-evidence-ready.

### `OCR_PAGE_LIMIT_REVIEW_REQUIRED`

OCR did not process every PDF page.

Never review-ready.

### `OCR_REQUIRED_FAILED`

Mandatory OCR failed.

Native text MUST NOT be used as a review-ready fallback.

### `OCR_REQUIRED_NOT_AVAILABLE`

No OCR Provider is configured/allowed for the current execution.

Native text MUST NOT be used as a review-ready fallback.

### `EVIDENCE_SHA_CONFLICT`

A/B/C byte identity cannot be proven.

Never review-ready.

### `PARTIAL_REVIEW_PACKET`

OCR exists but the issuer/template semantics are not yet reviewed or critical fields remain incomplete.

### `REJECTED_INPUT`

Lead is outside the official-review boundary.

## Business Digest v8

All unresolved mission PDF candidates admitted by the daily S01 radar receive Review Packet construction, not only the first two displayed rows.

Telegram display remains capped at two rows.

Rendering semantics:

- ready → `Native+OCR 双证据 · SHA A=B=C`;
- conflict → show the conflicting field and Native/OCR values;
- OCR-only → explicitly identify single-channel evidence;
- page truncation → show processed/total page count;
- SHA conflict → evidence-chain warning;
- OCR failure/unavailable → explicitly state that Native text cannot substitute for mandatory OCR;
- generic template → state that Native+OCR completed but issuer template semantics remain unreviewed.

No review candidate increments `current_opportunities`.

## Authority boundary

All packets remain:

```text
authority          HUMAN_REVIEW_REQUIRED
production_effect  NONE
writes             NONE
canonical_truth    false
verified_external  false
```

Human-reviewed promotion is a separate action under the existing Alternate Official Coverage rule.

## Installed Mac Provider live verification

The frozen S01 request schema was exercised against the **installed** Mac Browser Plane runtime without deploying the new SignalForge release to Bangkok. A one-shot in-memory Provider transport supplied the real claim envelope to the installed Provider Agent; all browser/PDF/OCR work used the installed MCP/runtime rather than mocks.

Request evidence:

```text
provider_request_id  2cec3f7b-bba5-4f22-a939-eedca909270d
capability           DOCUMENT_OCR
source               S01
target role          OFFICIAL_DOCUMENT
requested URL        Pobbathiri MPT/MDDC official National Portal PDF
```

Installed Mac Provider execution:

```text
run_once             ACCEPTED
browser_job_id       e0c07651-6498-47ae-ae96-de715055cae1
state                SUCCEEDED
mcp_tool             document_ocr
HTTP                  200
media type            application/json
fetch bytes           34575
engine                tesseract
rasterizer            macOS PDFKit
model                  tessdata_best
languages             mya + eng
PSM                   6
pages                 1 / 1
mean OCR confidence   73.26
network_access        false
intermediate images   not retained
```

Mac fetch and OCR byte identity:

```text
B = browser_fetch SHA
3dd5dd18a2395ba1bb18bdc31c9fa9850a98aced98fb05b7453c4380d24c9eea

C = document_ocr input SHA
3dd5dd18a2395ba1bb18bdc31c9fa9850a98aced98fb05b7453c4380d24c9eea

B == C = true
```

The real Provider JSON artifact was then passed through the SignalForge v1 wrapper and combined with a fresh independent SignalForge native fetch of the same official PDF.

Review Packet result:

```text
status                    DUAL_EVIDENCE_REVIEW_READY
template                   S13_MPT_NUMBERED_TENDER_V1
A = native SHA             3dd5dd18a2395ba1bb18bdc31c9fa9850a98aced98fb05b7453c4380d24c9eea
B = provider fetch SHA     3dd5dd18a2395ba1bb18bdc31c9fa9850a98aced98fb05b7453c4380d24c9eea
C = OCR input SHA          3dd5dd18a2395ba1bb18bdc31c9fa9850a98aced98fb05b7453c4380d24c9eea
A == B == C                true
conflict fields            0
native-only fields         0
OCR-only fields            0
```

All reviewed MPT v1 critical fields independently agreed:

```text
project location           Pobbathiri Township, Nay Pyi Taw       AGREED
tender sale start          2026-09-11                              AGREED
tender sale close          2026-09-24                              AGREED
tender sale close time     16:30                                   AGREED
site survey                2026-09-25                              AGREED
bid deadline               2026-09-29                              AGREED
bid submission start       09:30                                   AGREED
bid submission end         14:00                                   AGREED
```

Derived proposed action summary:

```text
Tender form sale closes 2026-09-24 16:30;
Site survey 2026-09-25;
Bid submission 2026-09-29 09:30-14:00
```

This remains **proposed evidence under HUMAN_REVIEW_REQUIRED**. The live verification did not create a canonical item, Signal, miss, verified-external opportunity or Bangkok production request.

The Browser Plane job evidence for `e0c07651-6498-47ae-ae96-de715055cae1` is retained in the Mac runtime audit surface. Temporary local claim/wire files used for the one-shot verification are not part of production state.

## Software verification

After freezing the contract and preserving historical R3 evidence-only compatibility:

```text
Targeted Contract/Wrapper/Review/Digest tests   60 / 60 PASS
Full pytest                                     488 passed
Full unittest discovery                         482 tests / OK
compileall                                      PASS
Provider Invocation Contract JSON               PASS
Source Registry JSON                            PASS
shell syntax                                    PASS
git diff --check                                PASS
```
