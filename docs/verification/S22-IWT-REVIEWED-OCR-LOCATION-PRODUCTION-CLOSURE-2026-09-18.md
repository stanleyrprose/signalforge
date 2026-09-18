# S22 IWT Reviewed OCR Location — Production Closure

Date: 2026-09-18

## Goal

Close the only current quality gap on the S22 Inland Water Transport Coastal Cargo Vessel tender without rewriting canonical history or broadening SignalForge OCR authority.

## Official evidence

Current opportunity:

- source: S22 Inland Water Transport;
- canonical key: `iwt:1038:2026-08-25`;
- reference: `IWT-NODE-1038`;
- scope: Coastal Cargo Vessel ×1;
- canonical deadline: `2026-11-03 10:00 +06:30`;
- official article: `https://iwt.gov.mm/my/node/1038`;
- official attachment: `https://iwt.gov.mm/my/file-download/download/public/1708`.

The official attachment is a one-page image-only PDF:

- PDF SHA256: `41d2614635fa440c0e226d682b5817f81e2f3c4ca31d9e4e0355332004436386`;
- no text layer;
- 1696×2400 rendered evidence image SHA256: `4f547056c203400c392eeee332ec3bac046e5ee5e444f5643f1647c4328b947a`.

Existing Mac Browser Plane `artifact_ocr` was used locally through the CodexPro bridge. Production OCR profile:

- Tesseract 5.5.3;
- `tessdata_best`;
- fixed `mya+eng`;
- networkless evidence enrichment only.

OCR cross-check:

- PSM 4 mean confidence: 78.73;
- PSM 6 mean confidence: 75.09;
- PSM 11 mean confidence: 75.74.

All three layouts consistently recover the contact/tender-handling address:

`Inland Water Transport, Administration Department / Supply Division, No. 50 Pansodan Road, Yangon Region`.

PSM 4 and PSM 6 also agree on contact numbers:

`01-8250251 / 01-8384252`.

OCR-rendered time digits were not trusted. The canonical structured deadline `2026-11-03 10:00` remains authoritative.

## Dynamic HTML identity finding

The IWT article HTML must not be hash-gated.

Two live requests approximately two seconds apart returned identical tender content and identical length but different SHA256 values. A diff showed the only change was Cloudflare `__CF$cv$params` request ID/timestamp.

Therefore the reviewed overlay uses stable business identity:

- canonical key;
- source ID;
- item kind;
- reference;
- publication date;
- official article URL;
- exact official attachment URL.

The reviewed PDF SHA is preserved as the immutable evidence fingerprint. The read layer does not perform network I/O.

## Implementation

PR #217 merged as:

`ac7130c68b4fd218fa0bec18b3b3755d0ef5953b`

The change adds a source-scoped reviewed IWT OCR overlay. It is read-layer only.

A pre-existing CLI test also used the real `2026-09-18 13:00` deadline without fixing `now`, so it became time-dependent after the deadline passed. Its fixture deadline was changed to a fixed far-future date so the test continues to test the CLI read-only surface rather than wall-clock time.

## Validation

- focused tests: `20/20 PASS` on default Python and Python 3.13;
- full suite: `418/418 PASS` on default Python and Python 3.13;
- compileall: PASS;
- registry parse: PASS;
- shell syntax: PASS;
- `git diff --check`: PASS.

GitHub Actions run `35345575436` did not start repository code because of the account payment/spending-limit state. Equivalent Python 3.13 checks passed locally.

Before merge, the undeployed commit was staged under Bangkok `/tmp` and executed against the live production DB. It produced:

- S22 quality `88`;
- gaps `[]`;
- reviewed location and contact action present;
- reviewed PDF SHA present.

## Production

Bangkok active release:

`ac7130c68b4fd218fa0bec18b3b3755d0ef5953b`

Rollback release:

`cf95214e33d0162396957e3ba9c35c68df1f535a`

Live verification:

- DB `quick_check=ok`;
- S22 canonical payload remains `location=None / next_action_summary=None`;
- S22 canonical attachment URL remains the official PDF;
- S22 Signal count remains exactly `1`;
- read-layer quality `78 -> 88`;
- read-layer gaps `LOCATION_MISSING -> []`;
- reviewed location and phone contact are present;
- all four production timers remain enabled;
- Telegram digest dry-run returns `PASS / pending_count=0`, so deployment created no duplicate daily digest.

The global DB count increased naturally due to a separate S38 acquisition (`industry:1044`) created before this deployment; it is unrelated to the S22 overlay.

## Decision

S22 location recovery is closed.

The Browser Plane OCR capability proved useful exactly in the intended role: recover evidence from an official image-only artifact, cross-check critical fields, then persist the reviewed interpretation in SignalForge without making OCR a canonical truth source or expanding the SignalForge remote Provider contract.

The next higher-value issue is S21 Myanma Railways coverage, where the problem is not field completeness but inability to prove whether new official tenders have appeared while the issuer surface is unreachable.
