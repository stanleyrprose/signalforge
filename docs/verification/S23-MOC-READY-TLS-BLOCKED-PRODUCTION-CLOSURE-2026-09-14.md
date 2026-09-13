# S23 National Ministry of Construction — READY_TLS_BLOCKED Production Closure

Date: 2026-09-14 (Asia/Bangkok/Myanmar-adjacent operator date)

## Decision

S23 is now **implementation-ready but intentionally scheduler-inactive**. The remaining blocker is issuer-side TLS: `construction.gov.mm` still presents an expired certificate under normal strict verification. SignalForge must not use `curl -k`, `--insecure`, browser certificate interstitial bypass, or an unverified mirror to turn this source green.

Current state:

- source id: `S23`
- source: Ministry of Construction National Tenders
- adapter: `moc_tender`
- engine: Bangkok `direct_http`
- listing mode: `listing_complete_business_records=true`
- production enablement: `enabled=false`
- activation gate: `STRICT_TLS_HTTPS / BLOCKED_ISSUER_CERT_EXPIRED`
- PDF handling: metadata only; no attachment fetch required for primary acquisition
- active source count remains 31

## What was implemented

The parser consumes the issuer tender-board cards directly and preserves only explicit official facts:

- issuer UUID from `/letter-download/<uuid>` as canonical identity
- official title
- official region badge
- official `End Date` as a date-only `TENDER_END_DATE`
- official download URL
- official `/storage/TinDar/*.pdf` URL as metadata only

No deadline time is invented. Award/result-stage titles are excluded. Download/PDF URLs are same-host constrained and invalid identity cards fail closed.

The source is fully declared in the registry but remains disabled. A generic Registry fail-closed rule rejects any enabled source whose `enable_only_after_gate_pass=true` gate is not `PASS`, so merely changing `S23.enabled=true` while the TLS gate is blocked cannot start production.

`deploy/check-moc-activation-gate.sh` performs a normal strict-HTTPS GET and requires HTTP 200. It deliberately contains no certificate bypass.

## Real issuer-shape replay

A previously captured audit-only copy of the live official HTML was replayed through the new parser. It produced exactly the two reviewed current cards:

1. `moc:18be5b60-accb-11f1-b41f-3517e3a380a0`
   - Highway maintenance/repair/supervision group tender
   - region: Nay Pyi Taw region badge
   - End Date: `2026-09-23`

2. `moc:0f39a580-a813-11f1-97b9-bbf17f490ccf`
   - Bridge Department Construction Group (4) / Bridge Special Group (16) tender
   - region: Ayeyarwady region badge
   - End Date: `2026-09-16`

The audit-only HTML was obtained earlier solely to inspect issuer structure while the certificate was expired. It is **not production Evidence** and was not inserted into canonical items or Signals.

## Verification

- targeted MOC + contract tests: `8 passed`
- full suite: `333 passed`
- `git diff --check`: PASS
- real saved issuer HTML parser replay: `2 records`, expected UUID/date/region values
- Mac strict activation gate: FAIL as expected, `curl_rc=60 / certificate has expired`
- Bangkok strict activation gate: same FAIL
- PR #172 Actions run `34771313418`, job `103761309219`: PASS

## Production deployment

- merged/deployed runtime: `b46f12b98d6a765c1a4a19e9c3c72dd96f764fb2`
- rollback: `b8bcf6d2d41d7899cdc21397b8ec029b624f8b84`
- release archive SHA256: `45579ea4b6e4e61f7f361fe4826fdecb7e65f1b28f4e4727aadb3de8c6f6fe62`

Post-deploy S23 isolation:

```text
active_sources      31
s23_enabled         false
s23_gate            BLOCKED_ISSUER_CERT_EXPIRED
s23_scheduler_runs  0
s23_canonical       0
s23_signals         0
```

The acquisition, immediate Telegram, and daily Digest timers all remained active.

## Activation procedure

Activation is a separate future change, not part of this closure:

1. Run `/srv/signalforge/active/deploy/check-moc-activation-gate.sh` on Bangkok.
2. Require `gate=PASS source=S23 tls=strict http_status=200`.
3. Re-fetch the live issuer page under strict TLS and confirm parser output/identity against the current board.
4. Change the registry gate status to `PASS` and `enabled=true` in one reviewed PR.
5. Run a silent first baseline, then a normal second run so still-actionable baseline tenders may enter the existing bounded reconciliation path without historical alert spam.
6. Verify source health, opportunity semantics, Telegram policy, and no duplicate canonical identities.

Until step 1 passes, S23 stays `READY_TLS_BLOCKED`.

## Unrelated production health note

Immediately after this deployment, global SignalForge status was `DEGRADED` / health RED because **S21 Myanma Railways** had accumulated 33 issuer fetch timeouts. S23 had zero scheduler runs and did not cause that state. This is a separate source-health issue and should not be mixed into the MOC activation decision.
