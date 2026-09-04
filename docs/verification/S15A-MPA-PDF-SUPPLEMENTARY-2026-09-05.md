# S15A MPA PDF Supplementary Slice — 2026-09-05

**Status:** `LIVE RUNTIME PACKAGING PASS / S15A ACTIVATION DEFERRED`

## Purpose

Add the smallest production-packaged PDF text capability required by the MPA source without activating S15A or creating unattended SignalForge→Mac invocation.

## Runtime dependency

SignalForge now declares an exact runtime dependency:

```text
pypdf==6.16.2
```

Bangkok system Python has no `pypdf` and no system `pip`, but `/usr/bin/python3 -m venv` successfully bootstraps pip. Deployment therefore creates one isolated venv per SignalForge release before switching `/srv/signalforge/active`.

```text
/srv/signalforge/releases/<sha>
/srv/signalforge/venvs/<sha>
```

If dependency installation fails, the active release is not switched. Old release + old venv remain available for rollback. No apt/root package installation is required.

## Parser contract

The supplementary parser is intentionally deterministic and bounded:

- maximum PDF bytes: 10 MiB;
- maximum pages: 20;
- maximum extracted text: 100,000 characters;
- encrypted PDFs: fail closed;
- too-short / non-text PDFs: fail closed;
- disposal/auction semantics take precedence over procurement words;
- procurement requires explicit purchase/service/repair/construction/installation/dredging semantics;
- generic `Open Tender` text without decisive business semantics returns `REVIEW_REQUIRED`;
- deadline is emitted only when one date+time candidate is uniquely supported; otherwise `NOT_FOUND` / `AMBIGUOUS`;
- MPA tender reference is emitted only from an explicit reference pattern;
- output includes a bounded evidence excerpt, not an LLM-generated summary.

Operator-only preview command:

```text
signalforge mpa-pdf-preview --pdf <issuer-original.pdf>
```

It is not a VPS Worker verb and writes no SignalForge DB/canonical/signal state.

## Real issuer-PDF verification

Four issuer-original PDFs previously acquired through installed Mac Browser Plane C0 were parsed under both the existing Mac `pypdf 6.14.2` environment and an isolated Python 3.13 venv with the exact production dependency `pypdf 6.16.2`.

| Sample | Final kind | Deadline (Asia/Yangon) | Reference |
| --- | --- | --- | --- |
| Three Tug Tender | `AUCTION_NOTICE` | `2026-06-25T13:00:00` | — |
| Marine Paint Tender | `TENDER` | `2026-06-04T13:00:00` | — |
| Port EDI Application O&M | `TENDER` | `2026-05-21T13:00:00` | `MPA-IR&HRD/01-2026` |
| Battery 9 Items | `TENDER` | `2025-05-29T13:00:00` | — |

The Three Tugs sample remains the critical contradiction test: the listing title looks like a procurement tender while the official PDF says the vessels will be auctioned through an open tender system. PDF semantics correctly override listing-title semantics.

## Verification

```text
local full suite:              86/86 PASS
compileall:                    PASS
bin/signalforge shell syntax:  PASS
deploy script shell syntax:    PASS
Python 3.13 + pypdf 6.16.2:    install PASS
exact-version unit suite:      86/86 PASS
exact-version 4 real PDFs:     4/4 PASS
```

Existing Python 3.13 SQLite `ResourceWarning` output is outside this slice and is not caused by the PDF runtime.

## Bangkok live runtime-packaging verification

The reviewed supplementary implementation had already been deployed to Bangkok as exact application release:

```text
f4a3dfd0ae77797b8fd82911fb908097a1dc97d8
```

This verification did **not** redeploy the application. It validated the live packaging/runtime boundary already active on Bangkok.

Per-release runtime isolation:

```text
active release = f4a3dfd0ae77797b8fd82911fb908097a1dc97d8
venv           = /srv/signalforge/venvs/f4a3dfd0ae77797b8fd82911fb908097a1dc97d8
Python         = 3.13.5
pypdf          = 6.16.2
system Python import pypdf = FAIL / exit 1
```

Therefore `pypdf` is isolated to the SignalForge release venv rather than installed into Bangkok system Python.

The previous Manual Provider Bridge production release remains present and executable as the immediate runtime rollback:

```text
d1f6d1773390767e73747df75e81383e4997f053
old-release signalforge status = PASS
```

A fresh issuer-original contradiction sample was acquired through installed Mac Browser Plane C0 with strict TLS:

```text
PDF            = Three-Tug-Tender-Eng.pdf
Browser Job    = 0e0e0062-7792-4f9b-a4b3-3a10b70597f7
HTTP           = 200
content-type   = application/pdf
bytes          = 101,698
SHA-256        = 9a664132a31c682d48d765c44e5b0d83c5e165bb1aebe9cc770b3f26ba30d046
engine         = c0-fetch
```

The artifact was transferred manually to Bangkok only for operator-preview verification. No `provider-import`, scheduler onboarding, source activation or remote invocation occurred.

Running the live release as the dedicated `signalforge` user:

```text
signalforge mpa-pdf-preview --pdf <Three-Tug-Tender-Eng.pdf>
```

returned:

```text
status                = PREVIEW_ONLY
source_id             = S15A
final_item_kind       = AUCTION_NOTICE
classification_status = DETERMINISTIC_PDF
classification_basis  = AUCTION_EN
deadline_local        = 2026-06-25T13:00:00
deadline_timezone     = Asia/Yangon
deadline_status       = FOUND
page_count            = 2
text_chars             = 1941
```

The extracted evidence excerpt explicitly states that the three tugs "will be auctioned through an open tender system", proving on the live Bangkok runtime that PDF semantics correctly override the misleading procurement-like listing title.

S15A durable state was compared immediately before and after preview:

```text
scheduler_runs       1 -> 1
acquisition_requests 1 -> 1
acquisition_attempts 1 -> 1
evidence_envelopes   1 -> 1
processing_records   1 -> 1
canonical_items      0 -> 0
signals              0 -> 0
SQLite quick_check   ok -> ok
```

The existing `1/1/1/1/1` S15A lifecycle is the previously verified Manual Provider Bridge `EVIDENCE_ONLY` import. The PDF preview created **no** new DB lifecycle, canonical item or customer signal.

Post-verification production state remained:

```text
12/12 active sources GREEN
SignalForge status          = PASS
SignalForge health          = GREEN
canonical_items             = 124
signals                     = 11
scheduler_runs              = 466
acquisition requests        = 612
acquisition attempts        = 612
evidence envelopes          = 611
processing records          = 611
failed_runs                 = 1   # pre-existing recovered S10 timeout
recovery_backlog            = 0
browser_production_approved = false
timer                       = enabled / active
```

Beijing remained outside the SignalForge application boundary (`/srv/signalforge = ABSENT`) and its Worker Runtime doctor remained `PASS`.

**Gate result:** production runtime packaging for deterministic text-native PDF parsing is now live-verified on Bangkok. S15A activation remains a separate decision because source execution still depends on the controlled manual Mac C0 acquisition path and no unattended provider invocation contract exists.

## Hard boundary

This slice does **not**:

- enable S15A;
- create an S15A source adapter or scheduler path;
- write canonical items or signals;
- add OCR;
- add an LLM parser;
- add Browser Agent/C3;
- bypass Bangkok TLS validation;
- create RPC/SSH/API automation to Mac;
- change `mac-mm-01 production_enabled=false` or `remote_invocation=false`.

Live runtime packaging verification is complete. The next decision is whether to onboard S15A using the already-proven **manual** Mac C0 acquisition path as an explicitly operator-driven P0, or leave S15A deferred until repeated manual evidence justifies a separately reviewed remote Provider Invocation Contract.
