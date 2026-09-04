# S15A MPA Manual P0 Phase B — Explicit Canonical Commit

Date (Asia/Yangon): 2026-09-05
Status: PRODUCTION LIVE PASS — MANUAL P0 CANONICAL BASELINE ACTIVE

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

## Production live verification

Phase B production gate completed on merged main release:

```text
0ff38409a5c0f2a312a79c912e7e411b21cdccd4
```

Previous application release retained as rollback:

```text
bd4e217d0b036a436290462ce9f1393defd00d6c
```

The release-local venv was built successfully before the active symlink changed, and the pre-existing timer state was restored automatically after deploy.

The production baseline reused the Phase A evidence relationship rather than reacquiring it:

```text
LISTING provider request = 74a9b732-6f04-4222-b999-3eac12611647
DETAIL provider request  = 88f20980-9e2f-45c4-a6fe-42da3ed484e2
PDF provider request     = 9d3aa060-168a-4fcc-9a4c-3262aace2ee1
PDF evidence SHA-256     = 9a664132a31c682d48d765c44e5b0d83c5e165bb1aebe9cc770b3f26ba30d046
```

A fresh installed-release preview returned `READY_FOR_MANUAL_COMMIT` with:

```text
canonical_key   = mpa:37867
item_kind       = AUCTION_NOTICE
publication     = 2026-06-02
deadline        = 2026-06-25T13:00:00+06:30
reference       = MPA-POST-37867
classification  = DETERMINISTIC_PDF / AUCTION_EN
listing kind    = TENDER (provisional only)
```

The first production commit intentionally omitted `--emit-signal` and returned:

```text
status          = COMMITTED
action          = CREATED
canonical_key   = mpa:37867
signals_created = 0
processing_id   = 61dde280-ec98-45f0-8b78-59ed1b475921
```

Immediate repetition of the exact same command returned `ALREADY_COMMITTED` with the same processing ID. No duplicate manual processing row or signal was created.

Durable S15A state after the baseline commit:

```text
scheduler_runs        = 4
acquisition_requests  = 4
acquisition_attempts  = 4
evidence_envelopes    = 4
processing_records    = 5
canonical_items       = 1
signals               = 0
manual SUCCESS rows   = 1
SQLite quick_check    = ok
```

The fourth acquisition/evidence lifecycle is a later duplicate Three Tugs PDF manual verification with the same issuer PDF SHA-256. It remains as immutable `EVIDENCE_ONLY` audit evidence; the canonical baseline uses the original Phase A PDF provider request above. No evidence was deleted to manufacture cleaner counts.

Canonical row verification:

```text
canonical_key   = mpa:37867
source_id       = S15A
item_kind       = AUCTION_NOTICE
deadline        = 2026-06-25T13:00:00+06:30
evidence_sha256 = 9a664132a31c682d48d765c44e5b0d83c5e165bb1aebe9cc770b3f26ba30d046
```

Manual-processing provenance is exactly:

```text
parser_version        = mpa-pdf-v1
normalizer_version    = mpa-manual-v1
canonicalizer_version = mpa-manual-v1
status                = SUCCESS
items_found           = 1
canonical_items       = 1
signals_created       = 0
```

Post-gate safety boundaries remained unchanged:

```text
S15A deferred / automated scheduling = true / disabled
mac-mm-01 production_enabled         = false
mac-mm-01 remote_invocation          = false
browser_production_approved          = false
timer                                = enabled / active
```

Global production remained `PASS / GREEN`; all 12 automated active sources remained GREEN. Global business state changed only by the intended baseline canonical item:

```text
canonical_items = 124 -> 125
signals         = 11  -> 11
recovery_backlog = 0
```

Bangkok Worker doctor and Beijing Worker doctor both returned `PASS` when invoked with the documented `WORKER_REPO_ROOT`; Beijing remains SignalForge-free.

**Gate result:** S15A Manual P0 Phase B is PRODUCTION LIVE PASS. MPA is now usable as an operator-driven canonical source without automated acquisition or unsolicited baseline customer signals. Only after repeated real manual operation proves a material operational burden should a remote Provider Invocation Contract be reopened.
