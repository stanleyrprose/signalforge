# S20 Official-Newspaper Recovery + S21 Outage Decision — Production Closure

Date: 2026-09-18

## Scope

This checkpoint closes the 2026-09-17 S20 business-detail recovery release and records the 2026-09-18 S21/YESC follow-up decisions. The goal remains customer-facing high-quality Myanmar government/SOE tenders in engineering, construction, telecom/ICT infrastructure and energy.

## S20 reviewed official recovery

PR #207 merged as release `9b96e6d31c781d18f3c6e8457edb59151fe57ea7` and was deployed to Bangkok production.

The read-only reviewed enrichment recovers three S20/MOEP events from exact Ministry of Information / Kyemon official text PDFs without mutating canonical rows or creating Signals:

- `moep:7144:2026-09-04` / DPTSC 44(T): bid deadline `2026-09-17 14:00`; now correctly expired from the current-opportunity view.
- `moep:7151:2026-09-08` / EPGE 69(Re-T) + 70(Re-T): bid deadline `2026-09-22 13:00`; explicit purchase/submission mechanics recovered.
- `moep:7157:2026-09-11` / DPTSC 45(T): bid deadline `2026-10-01 14:00`; explicit purchase/submission mechanics recovered.
- `moep:7150:2026-09-08` / YESC remains fail-closed `UNKNOWN / REVIEW`: no exact second official evidence was found.

Production S20 read model after deployment:

- current: `2 OPEN + 1 UNKNOWN`;
- trust: `2 A + 1 B`;
- priority: `2 MEDIUM + 1 REVIEW`;
- EPGE quality: `95 / VERY_HIGH`;
- DPTSC 45(T) quality: `83 / HIGH`.

Business Digest Attention dropped from six items to three: two truly urgent HIGH opportunities plus one YESC human-review item. S20 business-detail risk dropped from four unresolved current opportunities to one unresolved plus three reviewed official recoveries.

## Validation

- focused related tests: `55/55 PASS`;
- full suite: `398/398 PASS`;
- Python 3.13 full suite: `398/398 PASS`;
- production DB copy read-only preview left the DB SHA unchanged;
- live production DB: `PRAGMA quick_check = ok`;
- production timers: run-due, Telegram deliver, Telegram digest and assurance all `enabled`;
- 2026-09-18 Telegram business-digest dry-run: `PASS`, `pending_count=1` because this is the new 2026-09-18 daily digest, not replay of prior receipts.

GitHub Actions for PR #207 did not execute code because the account job was rejected by GitHub billing/spending-limit state. This is not treated as a code-test failure; equivalent Python 3.13 workflow validation passed locally.

## S21 Myanma Railways incident decision

No new SignalForge implementation is authorized for S21 at this checkpoint.

Live transport diagnostics from Bangkok:

- DNS resolves `www.railways.gov.mm -> 18.136.56.210`;
- IPv4 TCP connect to both HTTP/80 and HTTPS/443 times out before HTTP/TLS application processing;
- prior Mac strict curl, Chrome, nodriver and Camoufox diagnostics also timed out;
- therefore this remains an issuer/origin/network reachability incident, not a parser or browser-engine problem.

Existing outage-aware retry/backoff and S01 National Portal backup radar remain the correct minimal degradation strategy. The system must keep exposing S21 as a coverage risk; it must not mark the source healthy merely to clear global RED/DEGRADED status.

A proposed MOI/Kyemon newspaper fallback was rejected by a ground-truth gate: the known 2026-09-01 Railways tender containing `326/မမ/CE` is not present in the 2026-09-01 Kyemon text PDF. Therefore the S20 newspaper-recovery pattern must not be mechanically generalized to S21.

## YESC direct-source gate

YESC's official site is not added as a new SignalForge source.

Diagnostics:

- `www.yesc.com.mm -> 59.153.89.99`;
- origin returns HTTP 200 when TLS verification is bypassed for diagnosis only;
- leaf certificate is valid for `yesc.com.mm` / `www.yesc.com.mm` through 2026-11-22;
- server sends only the leaf certificate and omits the GlobalSign GCC R6 AlphaSSL CA 2025 intermediate, causing strict verification to fail;
- the indexed official `/tender` surface currently shows its latest tender as 2024-06-06, so repairing this TLS chain would not recover the 2026 S20/YESC event.

Result: no TLS bypass, no source onboarding and no duplicate low-value acquisition path. `moep:7150:2026-09-08` remains explicitly incomplete until an exact official second source is found.

## Current decision

Do not add sources or browser capability merely to improve health metrics. Continue optimizing customer-visible tender content:

1. preserve S21 coverage-risk truth while issuer reachability is down;
2. keep YESC 7150 UNKNOWN rather than guessing;
3. prioritize exact official evidence recovery and high-value government/SOE tender discovery;
4. treat source health, business-detail coverage and customer opportunity quality as separate metrics.
