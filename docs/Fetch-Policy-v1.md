# Fetch Policy v1

## Production defaults

SignalForge R5 uses Direct HTTP first. TLS certificate and hostname verification are mandatory. `verify=False`, `curl -k`, certificate bypass, browser rendering, and third-party render proxies are not approved production paths.

For S13 MPT the issuer-owned discovery path is `https://mpt.com.mm/page-sitemap.xml`. The Tender landing page is retained as evidence/context only because the 2026-09-02 Bangkok observation returned an empty content body while the official sitemap exposed real Tender detail URLs.

## Bounds

- User-Agent: `SignalForge/0.1 (+commercial-signal-monitor)`
- timeout: 30 seconds
- response limit: 2,000,000 bytes
- sequential detail requests only
- minimum 250 ms delay between detail requests
- initial baseline: newest 40 English pages within the 120-day lookback at most
- steady-state delta: at most 20 new/changed pages per source run
- no crawl-all recovery storm

A page is a MPT Tender only when the structural parser finds both `Reference No` and `Project Name`; URL wording alone is never sufficient.

## Evidence

Parsed Tender detail HTML is stored under the application evidence root using its SHA-256 as the immutable filename. The application database stores the evidence hash, canonical key, source URL and extracted fields. Customer-visible signals contain normalized fields and evidence references, not arbitrary page HTML.


## v1.5 Local Acquisition Contract

v1.5 keeps the R5 Direct HTTP behavior but makes the acquisition lifecycle explicit inside SignalForge:

```text
Source Acquisition Policy
→ AcquisitionRequest
→ AcquisitionAttempt
→ EvidenceEnvelope
→ ProcessingRecord
→ Canonical / Signal
```

`AcquisitionRequest` and `AcquisitionAttempt` are SignalForge business/application state. They are **not** Worker Runs and do not change the Gate Z cardinality of one SignalForge scheduler invocation to one Worker operational Run.

S13 freezes `source_policy_version=8`, `egress_profile=mm-intl-datacenter`, and `DIRECT_HTTP` as the primary method. Failure handling is policy-driven: DNS/connect/429 may retry within existing bounded semantics; HTTP 403 requires review; TLS fails closed; JS-render requirement triggers capability review; parser drift triggers source re-audit. None of these silently enables Browser.

`EvidenceEnvelope` contains acquisition facts only. Parser/normalizer/canonicalizer versions and business interpretation live in SignalForge-owned `ProcessingRecord`.
