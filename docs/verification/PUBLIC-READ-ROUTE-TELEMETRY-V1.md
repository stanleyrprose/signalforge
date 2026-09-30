# PUBLIC_READ_ACQUIRE Route Telemetry v1

Status: IMPLEMENTED / PRODUCTION ROLLOUT PENDING

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
