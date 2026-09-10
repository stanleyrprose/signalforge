# S13 Parser-Only Signal Noise + DOMS Audit Production Closure — 2026-09-10

## Scope

This closure records two business-value audits performed after the S13 MPT Semantic v2 rollout:

1. a real production `UPDATED` signal for an expired MPT tender that was caused by reparsing byte-identical issuer evidence with the new semantic parser rather than by an issuer-side change; and
2. a bounded audit of the current DOMS `doms:12735` official PDF attachments to determine whether the existing text-PDF runtime could improve its missing deadline/scope without introducing OCR.

The resulting production code change is intentionally limited to parser-only signal suppression for single-detail evidence. No schema, dependency, source registry/policy, acquisition method, Browser Plane, Provider, Worker Plane, Control Plane, Beijing role, or delivery identity change is introduced.

## Production trigger

Before this slice, Bangkok production was healthy (`PASS / GREEN`) with `194` canonical items, recovery backlog `0`, Telegram delivery caught up, but total signals had increased from `44` to `45`.

The new row was:

```text
2026-09-09T17:15:12.735583Z | S13 | mpt:CCO-2026-001 | UPDATED
```

Current canonical state for `mpt:CCO-2026-001` is:

- issuer: MPT
- reference: `CCO-2026-001`
- title/project: `Purchasing of Top-up Card with QR code`
- publication date: `2026-07-17`
- official deadline: `2026-08-06`
- business stage: `OPPORTUNITY`
- procurement stage: `PRE_QUALIFICATION`

The deadline was already expired when the signal was created, so the opportunity and Telegram presentation layers correctly excluded it from current actionable output. The problem was upstream signal provenance: the row was the only signal ever recorded for that canonical and appeared after the S13 parser/normalizer changed to Semantic v2.

PR #115 explicitly intended parser-version changes alone not to create historical `UPDATED` noise. The deployment avoided a forced refresh, but a later normal health probe reparsed the stored page under the new semantic model. Because the engine compared the normalized canonical payload hash, newly derived semantic fields changed the hash even though the issuer evidence bytes had not changed.

## Root cause

Before this fix, detail processing used two different identities for two different purposes:

- `discovery_items.content_hash`: SHA-256 of the last successfully fetched detail evidence for that URL;
- `canonical_items.content_hash`: SHA-256 of the normalized business payload emitted by the parser/normalizer.

`_upsert_tender()` correctly treated a normalized payload change as a canonical change, but it also emitted `UPDATED` whenever that payload hash changed and the run was not baseline/suppressed. That is correct for an issuer-side content change but incorrect when a parser/normalizer upgrade derives additional fields from byte-identical evidence.

## Implemented rule

PR #117 adds the minimal sufficient distinction for single-detail sources:

> If the current detail has no fetched attachment bundle and the previous `discovery_items.content_hash` equals the current raw `detail_capture.sha256`, the engine may update the canonical payload but suppresses the customer-facing signal.

Therefore:

- same raw HTML bytes + new parser semantics -> canonical may change, no `UPDATED` signal;
- changed raw HTML bytes -> normal `NEW/UPDATED` semantics remain;
- attachment-backed HTML+PDF pipelines -> unchanged by this rule.

This is deliberately not generalized into a multi-evidence fingerprint or schema migration.

## Multi-evidence boundary discovered by testing

The first implementation compared the current canonical evidence digest generically. Full-suite testing immediately rejected that design through the existing S30 MOFA regression:

```text
FAILED tests/test_mofa.py::MofaEngineTests::test_baseline_fetches_optional_pdf_and_probe_updates_same_post
239 passed, 1 failed
```

S30 combines HTML and an optional official PDF. Its HTML may genuinely change while the PDF remains byte-identical. Since the old canonical `evidence_sha256` can refer to the PDF, a single digest cannot prove that the complete evidence bundle is unchanged.

The implementation was therefore narrowed to `not attachment_captures` and comparison against the raw current detail HTML SHA. After the correction, the full suite passed:

```text
240 passed
```

Existing regressions continue to prove both important sides of the boundary:

- a real MPT HTML material change still emits `UPDATED`;
- a MOFA HTML change with an unchanged PDF still emits `UPDATED`.

## Tests and review

Pre-merge verification:

- `tests/test_engine.py`: `7 passed`
- MPT + opportunities + briefing + Telegram targeted set: `21 passed`
- full suite: `240 passed`
- GitHub Actions PR check `verify`: PASS, run `34443774429`

Code PR:

- PR: `#117 fix: suppress parser-only detail update signals`
- feature commit: `42f5d82`
- squash merge / production code SHA: `9f4605fd55039704d335da7bda33662b9c234528`

## Bangkok deployment

The exact merge SHA was archived and deployed with the existing reviewed release script.

- deployed release: `9f4605fd55039704d335da7bda33662b9c234528`
- immediate rollback target: `21c162e0333c328e06f9a83ad7bee7b1bdf2abdf`
- local deployment archive SHA-256: `9af6e74b96638e3e52018833b846abb51458235420f49080951ab6b9520b830c`
- deploy result: `deployment=success`
- main acquisition timer: active
- Telegram delivery timer: active
- post-deploy Telegram dry-run: `PASS / pending_count=0`

Post-deploy production health:

- SignalForge: `PASS / GREEN`
- canonical items: `194`
- signals: `45`
- recovery backlog: `0`
- DB `PRAGMA quick_check`: `ok`

The historical parser-only `UPDATED` row is intentionally preserved as audit history. This slice prevents recurrence; it does not rewrite production history.

## Production-copy verification with real stored evidence

A read-only backup of the production SQLite database was copied to `/tmp`; the real production database was never mutated. In the copy, `mpt:CCO-2026-001` was temporarily reduced to a legacy semantic payload, then the deployed `9f4605f...` runtime reparsed the exact stored production detail evidence.

Real stored detail evidence SHA-256:

```text
3334984f1fc2a56e601261eeea84f9c6356a82ef11ccffb05b8d0e560fb4c971
```

Result:

```json
{
  "status": "SUCCESS",
  "health_probe": true,
  "changed": 1,
  "signals_created": 0,
  "signals_before": 45,
  "signals_after": 45,
  "canonical_business_stage": "OPPORTUNITY",
  "canonical_deadline": "2026-08-06"
}
```

This directly verifies the intended invariant: canonical semantics can be upgraded from identical source evidence without pretending that the issuer published an update.

## DOMS `doms:12735` audit

`doms:12735` remains the only current `B / REVIEW` opportunity because the official HTML identifies three medical procurement references/attachments but does not expose a reliable deadline or detailed scope.

The official post exposes three same-origin PDFs corresponding to:

- `8DMS/2026-2027(L)`
- `9DMS/2026-2027(L)`
- `10DMS/2026-2027(F)`

All three were fetched only for this bounded audit and parsed with the already-deployed `pypdf==6.16.2` runtime:

| Attachment | Pages | Extracted text chars |
|---|---:|---:|
| 8DMS | 2 | 1 |
| 9DMS | 5 | 4 |
| 10DMS | 2 | 1 |

All three are effectively scan-only. Text-PDF enrichment therefore cannot responsibly recover the missing deadline/scope.

Decision: keep `doms:12735` as `deadline UNKNOWN / REVIEW`; do not introduce OCR merely for this record. OCR remains an evidence-triggered future capability and should only be activated when a broader source/value case justifies its runtime/dependency/quality costs.

Temporary audit PDFs and production-copy verification files were removed after the checks.

## Closure / next routing

The current product priority remains business-value quality auditing of existing production sources rather than adding S41/S42 solely to increase source count. The next slice should look for another evidence-backed semantic-noise or missing-business-field problem that can be solved inside existing capabilities. DOMS OCR is explicitly not the default next step.
