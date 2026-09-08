# PIC-v1 R1C Provider Artifact Submit — 2026-09-08

**Status:** FEATURE IMPLEMENTATION / LOCAL TEST PASS

## Purpose

Close the transport contract gap between a successful Mac Browser Plane job and durable Bangkok evidence return. R1B originally accepted only result hash/job metadata; R1C replaces that remote completion verb with a bounded binary submit contract.

## Wire format

```text
<one UTF-8 JSON manifest line>\n
<exact raw artifact bytes>
```

No tar/archive, SFTP, scp path or shared filesystem is part of the protocol.

Manifest fields are exact and closed:

```text
contract_version
provider_request_id
provider_attempt_id
claim_token
browser_job_id
request_sha256
state
mcp_tool
final_url
http_status
media_type
artifact_bytes
artifact_sha256
```

## Validation

Bangkok verifies before accepting:

- manifest framing and exact fields;
- contract version/state;
- max artifact 16 MiB;
- exact byte count and EOF;
- SHA-256;
- current ProviderRequest state;
- current ProviderAttempt ownership;
- claim-token hash;
- request SHA;
- MCP tool correlation;
- final URL equals the approved request URL in R1C;
- idempotent duplicate result semantics.

Successful evidence storage:

```text
<evidence_root>/provider-results/<provider_request_id>/
  manifest.json   0600
  response.bin    0640
parent directory  0700
```

ProviderRequest persists artifact path/bytes/media type/final URL/status/request SHA. This is durable provider-return evidence only; R1C does not yet create the normal source `EvidenceEnvelope` or run business parsers.

## Dispatcher

Remote verb is now:

```text
provider-submit-v1
```

The old metadata-only `provider-complete-v1` is not a remote dispatcher command. `provider-submit-v1` is consumed only at the binary stdin boundary.

## Verification

```text
python -m pytest tests/test_provider_queue.py tests/test_provider_dispatcher.py tests/test_provider_result.py -q
20 passed

python -m pytest -q
183 passed
```

Production flags remain disabled; no SSH credentials or Mac Provider Agent are installed by R1C.
