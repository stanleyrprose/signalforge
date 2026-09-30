# PUBLIC_READ_ACQUIRE Route Telemetry v1

Status: PRODUCTION INSTRUMENTED / 24H OBSERVATION ACTIVE

## Objective

Provide bounded operational visibility for `PUBLIC_READ_ACQUIRE` without changing acquisition routing, source authority, browser authority, or the Provider invocation model.

The telemetry reports request state by source, selected C0/C1 route, selected engine/transport, natural render-trigger evidence, Provider end-to-end latency, artifact size, and the post-instrumentation verification gate.

## Authority boundary

`route_summary` is observational only. It grants no acquisition capability and is not consulted to authorize a request.

Browser Plane still owns route selection. SignalForge cannot use this field to request Lightpanda, Chrome, C2, C3, or another engine.

The summary contains only bounded routing metadata: policy, selected C0/C1 capability, engine/browser-engine/transport identifiers, render trigger/fallback flags, up to two sanitized attempt summaries, and explicit `c2_authorized=false` / `c3_authorized=false`.

It does not contain URLs, artifact paths, page text/body, headers, cookies, credentials, browser profiles, or proxy configuration. SignalForge validates the summary fail-closed before persistence.

## Rollout compatibility

The SignalForge receiver temporarily accepts a missing `route_summary` so Bangkok can be deployed before the Mac Provider. Once the first instrumented successful request is observed, later successful `PUBLIC_READ_ACQUIRE` requests without route telemetry are an operational anomaly.

Required rollout order:

1. Deploy the backward-compatible SignalForge receiver.
2. Deploy the instrumented Mac Provider.
3. Run real S27/S38 diagnostic acquisition.
4. Verify telemetry persistence and a quiet anomaly check.
5. Accumulate the 24-hour observation period.

## Verification gate

The gate states are:

- `NO_DATA`: no instrumented successful public-read request exists.
- `OBSERVING`: instrumentation exists but fewer than 24 hours or fewer than 10 instrumented successes have accumulated.
- `FAIL`: an operational anomaly exists after instrumentation began.
- `PASS`: at least 24 hours and at least 10 instrumented successes have accumulated with zero gate anomalies.

Gate anomalies include terminal Provider failures, missing route summary after instrumentation start, incomplete result-integrity metadata, and unreadable persisted route JSON.

A naturally triggered `C1_RENDER` is recorded for audit but is not itself an anomaly. Routing policy must not be weakened merely to manufacture a C1 event.

## Telegram behavior

`signalforge-public-read-telemetry.timer` evaluates the 24-hour window hourly. Healthy and `OBSERVING` states are silent. Telegram is sent only when an anomaly exists. Alert fingerprints are persisted so an unchanged incident is not repeatedly delivered.

The weekly `assurance-run` includes the public-read telemetry snapshot but retains `sends_telegram=false` and does not change the existing assurance business-metric verdict merely because the telemetry gate is still observing.

## Operational commands

```bash
signalforge public-read-telemetry --window-hours 24
signalforge public-read-telemetry-alert --window-hours 24
```

The first command is read-only reporting. The second is intended for the systemd timer and sends only on anomaly.

## Production rollout evidence — 2026-10-01

Production rollout followed the documented receiver-first order.

Revisions:

- SignalForge receiver / telemetry: `1e537a38e6d3fc770f2041c17b52068b6592024e` (`#272`).
- Mac Browser Plane Provider telemetry: `2aa5201ff67a37e6da797341ae65eee2452acd13` (`#64`).
- SignalForge post-merge verify run `36748322298`: PASS.
- Mac Browser Plane post-merge CI run `36748235583`: PASS.

Receiver-first compatibility was verified before upgrading the Mac Provider. With the old Provider still running, an S38 diagnostic request succeeded through the new Bangkok receiver:

- provider request `85474d64-4207-4a48-9b50-5002d1445015`;
- HTTP `200`;
- `87,883` bytes;
- receiver accepted the legacy manifest without `route_summary`;
- rolling 24H state remained `PASS`;
- 42/42 public-read requests in the window were successful;
- verification gate correctly remained `NO_DATA`.

The Mac production runtime was then upgraded from the reviewed main revision. Post-install Browser Plane Doctor returned `READY`; the running Provider package was verified to contain both `route_summary` support and the fail-closed C1 route-sequence validation.

First instrumented production requests:

- S38 request `a14575a8-c05c-41f7-8ffb-f21198e20010`: HTTP `200`, `87,883` bytes, selected `C0_FETCH`, engine `c0-fetch`, transport `system_curl`.
- S27 request `8bc83506-0c60-41dc-aa11-bc05a96de004`: HTTP `200`, `82,794` bytes, selected `C0_FETCH`, engine `c0-fetch`, transport `system_curl`.

For both requests, Bangkok persisted the bounded `route_summary`, including:

- `policy=public_read_auto_v1`;
- exact one-attempt C0 route sequence;
- `c2_authorized=false`;
- `c3_authorized=false`;
- no URL/body/header/cookie/profile fields in route telemetry.

Immediately after instrumentation:

- 44/44 rolling 24H public-read requests were successful;
- 2 instrumented successes were present;
- selected routes: `C0_FETCH=2`;
- selected transports: `system_curl=2`;
- anomalies: `0`;
- first instrumented request time: `2026-09-30T18:02:50.055102Z`;
- verification gate: `OBSERVING`;
- hourly telemetry timer: `active`;
- explicit alert check: `QUIET` (`sent=false`);
- natural production C1 trigger observed: `false`.

The rollout is therefore live and healthy, but final 24H closure is intentionally deferred until the gate has at least 24 hours of observation and at least 10 instrumented successes with zero gate anomalies. A natural C1 event remains audit-only and is not required for the 24H gate to pass.
