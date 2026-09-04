# S15A MPA Manual P0 Phase B — Explicit Canonical Commit

Date (Asia/Yangon): 2026-09-05
Status: IMPLEMENTATION / TEST PASS — LIVE BASELINE COMMIT PENDING

## Decision

The user explicitly authorized continuing the recommended S15A Manual P0 onboarding after Phase A live verification. Phase B adds only an **operator-driven, idempotent canonical commit** over already imported LISTING/DETAIL/PDF evidence.

It does **not** activate S15A in the scheduler and does **not** create unattended SignalForge→Mac invocation.

## Contract

```text
LISTING EVIDENCE_ONLY
+ DETAIL EVIDENCE_ONLY
+ PDF EVIDENCE_ONLY
        |
        v
mpa-provider-bundle-preview
        |
        +-- REVIEW_REQUIRED -> STOP
        |
        v
READY_FOR_MANUAL_COMMIT
        |
        v
mpa-provider-bundle-commit
        |
        +-- default: canonical only / zero signal
        +-- --emit-signal: explicit NEW or UPDATED signal when material content changed
```

The PDF SHA is the authoritative canonical evidence digest. Canonical identity remains `mpa:<wordpress_post_id>`.

## Safety and idempotency

`mpa-provider-bundle-commit` revalidates all durable evidence through the existing Manual Provider Bridge loader before writing:

- all three artifacts must be S15A;
- roles must be LISTING / DETAIL / PDF;
- stored request contracts, URL bounds, SHA-256 and byte counts must still validate;
- listing must contain the selected detail URL;
- detail must expose the stable WordPress post ID and exactly one issuer PDF URL;
- the supplied PDF URL must match the detail-page locator;
- PDF business classification must return `READY_FOR_MANUAL_COMMIT` rather than `REVIEW_REQUIRED`.

One PDF evidence artifact may be canonicalized once per `mpa-manual-v1` canonicalizer version. Repeating the same commit returns `ALREADY_COMMITTED` and creates no second canonical-processing record or signal.

## Signal policy

Signal emission is deliberately operator-controlled for Manual P0:

```text
mpa-provider-bundle-commit ...
    -> canonical write/update
    -> signals_created = 0

mpa-provider-bundle-commit ... --emit-signal
    -> if new canonical item: NEW
    -> if materially changed existing item: UPDATED
    -> if unchanged: no signal
```

The first production baseline commit will omit `--emit-signal`.

This avoids inventing a scheduler/source-baseline state machine for a source currently publishing only a few items per month.

## Processing provenance

The provider-import processing rows remain `EVIDENCE_ONLY`. Phase B adds a separate successful processing row against the authoritative PDF evidence:

```text
parser_version        = mpa-pdf-v1
normalizer_version    = mpa-manual-v1
canonicalizer_version = mpa-manual-v1
status                = SUCCESS
items_found           = 1
canonical_items       = 1
signals_created       = 0 or 1
```

The original acquisition/scheduler evidence lifecycle is not rewritten after the fact.

## CLI

```bash
signalforge mpa-provider-bundle-commit \
  --listing-provider-request-id <listing-id> \
  --detail-provider-request-id <detail-id> \
  --pdf-provider-request-id <pdf-id>
```

Optional customer signal emission requires the explicit additional flag:

```text
--emit-signal
```

The commit command is deliberately absent from the VPS Worker verb manifest.

## Verification

Implementation tests:

```text
Phase B targeted tests = 4/4 PASS
full repository suite  = 95/95 PASS
```

They prove:

- first commit creates `mpa:37867` canonical `AUCTION_NOTICE` with zero signal;
- repeated same-evidence commit returns `ALREADY_COMMITTED`;
- a fresh changed PDF evidence bundle can create exactly one `UPDATED` signal only when `--emit-signal` is explicitly enabled;
- `REVIEW_REQUIRED` bundles cannot canonicalize;
- the command is not a Worker verb.

## Production gate

Phase B is not production-complete until:

1. exact merged SHA is deployed through the normal Bangkok release flow;
2. existing 12 active sources remain GREEN and timer stays enabled/active;
3. the already live-verified Three Tugs LISTING/DETAIL/PDF bundle is committed **without** `--emit-signal`;
4. resulting canonical key is `mpa:37867`, item kind `AUCTION_NOTICE`, deadline `2026-06-25T13:00:00+06:30`;
5. S15A canonical count becomes exactly 1 while S15A signals remain 0;
6. repeating the same command returns `ALREADY_COMMITTED` with no duplicate processing/signal;
7. `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false` remain unchanged;
8. S15A remains outside the automated scheduler/active-source set;
9. both Worker doctors pass and Beijing remains SignalForge-free.

Only after repeated real manual operation proves an operational burden should remote Provider Invocation Contract work be reopened.
