# Manual Provider Bridge v0

**Status:** implemented for controlled evidence-only use.

## Purpose

Bridge one real source acquisition from SignalForge to the Mac Browser Plane without creating a network RPC/API/SSH invocation contract.

Current approved use case:

```text
S15A — Myanma Port Authority Tender Category
Bangkok strict TLS = RED
Mac direct C0      = GREEN
```

This is an execution-environment difference, not evidence that Browser rendering is required.

## Hard boundary

Manual Provider Bridge v0 is intentionally narrow:

```text
supported provider   = mac-mm-01
supported source     = S15A only
supported task       = C0 fetch only
network              = Mac direct only
processing           = EVIDENCE_ONLY
remote invocation    = disabled
production routing   = unchanged
```

It does **not**:

- enable `production_enabled` on the Mac provider;
- add a SignalForge→Mac HTTP API, SSH command path, webhook, queue or daemon;
- add Browser runtime to Bangkok/Beijing;
- bypass TLS verification;
- enable C1 generic interaction, C2 remote diagnostics or C3 Browser Agent;
- onboard S15A as an active SignalForge source;
- parse/canonicalize imported MPA evidence;
- create customer signals from imported MPA evidence.

`provider-request` and `provider-import` are deliberately absent from the VPS Worker verb manifest, so the Worker dispatcher cannot invoke them as scheduled production verbs.

## Lifecycle correlation

Each exported request contains explicit IDs:

```text
signalforge_job_id
acquisition_request_id
acquisition_attempt_id
provider_request_id
```

After Mac execution, `browser_job_id` is taken from the `browserctl` result.

The import maps them into existing SignalForge lifecycle storage without a schema change:

```text
scheduler_runs.app_run_id         = signalforge_job_id
scheduler_runs.trigger_id         = provider_request_id
scheduler_runs.worker_run_id      = browser_job_id
acquisition_requests.request_id   = acquisition_request_id
acquisition_requests.app_job_ref  = provider_request_id
acquisition_attempts.attempt_id   = acquisition_attempt_id
evidence_envelopes.app_job_ref    = provider_request_id
```

## Step 1 — export the request

From a SignalForge checkout/release containing this bridge:

```bash
signalforge provider-request S15A --output /tmp/s15a-provider-request.json
```

The request file is mode `0600` and is directly compatible with `browserctl run`. Extra `_provider_request` metadata is ignored by the Browser Plane JobSpec parser but is preserved for SignalForge import validation.

## Step 2 — execute on Mac

On the Mac mini:

```bash
/Users/xu/agent-browser-runtime/app/venv/bin/browserctl run \
  --file /tmp/s15a-provider-request.json \
  > /tmp/s15a-browser-result.json
```

Expected v0 result:

```text
state  = SUCCEEDED
engine = c0-fetch
status = 2xx
```

The result contains `artifact_path`, `sha256`, `body_bytes`, `content_type`, final URL and `browser_job_id`.

## Step 3 — move three files to Bangkok

Manual operator transfer only:

```text
request JSON
browser result JSON
raw response artifact
```

No persistent transport service is introduced by this bridge.

## Step 4 — import on Bangkok

Run as the `signalforge` process user against the canonical production state/evidence roots:

```bash
signalforge provider-import \
  --request <request.json> \
  --result <browser-result.json> \
  --artifact <response.html>
```

The importer validates before DB insertion:

- provider/source/bridge version;
- approved S15A URL;
- direct-only C0 request;
- source policy/provider baseline;
- profile/egress/expected content-type contract;
- Browser Job `SUCCEEDED` state;
- `c0-fetch` engine;
- successful HTTP status;
- final URL equals the approved candidate URL;
- artifact SHA-256;
- artifact byte count;
- observed content type.

Tampering or contract drift fails closed.

## Stored evidence

Successful import stores:

```text
<evidence_root>/S15A/provider/<provider_request_id>/
├── request.json          0600
├── browser-result.json   0600
└── response.html         0640
```

The provider directory is `0700`.

A successful import creates exactly one row in each existing lifecycle layer:

```text
scheduler_runs
acquisition_requests
acquisition_attempts
evidence_envelopes
processing_records
```

The processing record is explicitly:

```text
status                = EVIDENCE_ONLY
parser_version        = none
normalizer_version    = none
canonicalizer_version = none
items_found           = 0
canonical_items       = 0
signals_created       = 0
```

So evidence presence cannot be mistaken for source onboarding or business processing.

## Idempotency

Re-importing the same request/artifact returns:

```text
ALREADY_IMPORTED
```

and does not create duplicate lifecycle rows.

If an existing request ID points to a different provider or SHA-256, import fails closed.

## Current evidence

Pre-merge live smoke on 2026-09-04:

```text
Source             S15A MPA Tender Category
Mac browser job    c082bb94-e001-42ba-adeb-564a7fa40878
HTTP               200
Artifact bytes     252,512
SHA-256            c016d4efcae50f271e5e6860e1567650ee3d215c4ef7d9d31bd029ed4a0ec810
Local temp import  IMPORTED_EVIDENCE_ONLY
Repeated import    ALREADY_IMPORTED
```

This live smoke used the installed Mac Browser Plane and an isolated temporary SignalForge database/evidence root. Production import is a separate controlled verification step after merge/deployment.

## Reopen rule

Do not automate this bridge merely because v0 works.

Consider a real remote Provider Invocation Contract only after repeated manual use proves that:

1. the source has durable business value;
2. the Mac execution path is materially required;
3. manual transfer is a meaningful operational burden; and
4. authentication, request authorization, idempotency, correlation, offline behavior and evidence return justify the extra system complexity.
