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
