# S15A MPA PDF Supplementary Slice — 2026-09-05

**Status:** `IMPLEMENTATION PASS / S15A ACTIVATION DEFERRED`

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

The next decision after live runtime packaging verification is whether to onboard S15A using the already-proven manual acquisition path, or leave it deferred until remote provider automation is justified.
