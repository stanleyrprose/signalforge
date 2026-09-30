# PUBLIC_READ_ACQUIRE Production Closure — 2026-09-30

**Status:** VERIFIED / CLOSED

## Scope

This closes the coordinated production rollout that moves normal provider-backed HTML acquisition for S27 and S38 from caller-selected C0_FETCH to the high-level Provider capability PUBLIC_READ_ACQUIRE -> browser_acquire.

SignalForge now asks to read one approved public URL. Mac Browser Plane owns the bounded internal route:

C0 system curl -> bounded curl_cffi retry when C0 evidence permits -> conservative render classification -> at most one ephemeral C1 render when evidence requires it -> Lightpanda -> safe Chrome fallback under the existing C1 policy.

C2 and C3 are not authorized by this composite capability.

## Reviewed revisions

### Mac Browser Plane

- Provider authorization merged on main: 998f110b853dbcbe0b924e7e312bbde4bc3ef130
- Main CI run: 36698567726 — PASS
- Provider map includes PUBLIC_READ_ACQUIRE -> browser_acquire
- Installed Mac PIC authorizes S27 and S38 source policy version 2 with PUBLIC_READ_ACQUIRE plus diagnostic C0_FETCH.
- S01 remains DOCUMENT_OCR.

### SignalForge

- Provider routing feature merged on main: ac5c2e6b9b04966949d97561c5605eaafa6df164
- Feature main verify run: 36698602630 — PASS
- Production active release observed during closure: ead5a123e558f42fe39af3f7212fa3f2b34364c0
- That production release contains the ac5c2e6 public-read routing feature.
- Production PIC and Source Registry both report S27.provider_capability = PUBLIC_READ_ACQUIRE and S38.provider_capability = PUBLIC_READ_ACQUIRE, both at source policy version 2.

The repository main advanced after the active release during closure verification. That does not invalidate this closure: the active production release already contains the complete PUBLIC_READ_ACQUIRE feature and passed the live gates below.

## Production readiness state

Before the explicit diagnostic smoke:

- Provider queue had no PENDING or CLAIMED rows.
- Existing provider history: EXPIRED 235, FAILED 14, SUCCEEDED 2366.
- Mac Provider LaunchAgent was running.
- Mac Browser Plane Doctor returned READY.
- curl_cffi_c0b was ready.
- Lightpanda was installed and ready.
- stale profile leases: none.
- owned Browser processes left behind: none.
- Bangkok timers were all enabled and active: signalforge-run-due.timer, signalforge-telegram-deliver.timer, signalforge-telegram-digest.timer, and signalforge-assurance.timer.

## End-to-end production smoke

The smoke used SignalForge's diagnostic acquisition path. This path uses the real production Provider queue and Mac Provider but does not create customer Telegram delivery.

### S38 — Ministry of Industry

- Provider request: f4eddd3d-39ba-4f74-832d-7a533d83b795
- capability: PUBLIC_READ_ACQUIRE
- target role: LISTING
- final URL: https://www.industrymsme.gov.mm/announcements
- HTTP: 200
- artifact bytes: 87883
- SHA-256: ed5c7ed723e4dce6eab8100b7764651d52a85ba95e7b661edee023aed7dafae3
- Browser job: b1d2671b-21a9-45f7-b5a7-eee0e494b890
- final internal engine: c0-fetch
- final transport: system_curl

The Mac artifact byte count and SHA-256 exactly matched the artifact accepted by Bangkok.

### S27 — Ministry of Border Affairs

- Provider request: 936b5db2-b5af-4991-9ba4-6e8c7718de4c
- capability: PUBLIC_READ_ACQUIRE
- target role: LISTING
- final URL: https://moba.gov.mm/my/tender
- HTTP: 200
- artifact bytes: 82794
- SHA-256: 871c699d4a664227cdfa5e3ca1975ed087aeb0beafdd41e4bc209e3ad0939f23
- Browser job: f0925cef-dd17-4b3e-b240-054bd002d908
- final internal engine: c0-fetch
- final transport: system_curl

The Mac artifact byte count and SHA-256 exactly matched the artifact accepted by Bangkok.

## Observed production behavior after cutover

At closure time, production contained 21 PUBLIC_READ_ACQUIRE requests:

- total: 21
- SUCCEEDED: 21
- failed/expired/cancelled: 0
- S27: 10 / 10 succeeded
- S38: 11 / 11 succeeded
- local Browser job correlation missing: 0

For all 21 requests, the final internal route was PUBLIC_READ_ACQUIRE -> C0_FETCH -> system_curl.

Observed selected Browser-job execution latency:

- minimum: 0.578 s
- average: 1.134 s
- maximum: 5.249 s

This is the desired behavior for the current S27/S38 pages: Browser Plane retains authority to render when conservative evidence requires it, but does not start C1 when C0 already returns substantive HTML.

## C1 live-evidence boundary

No S27/S38 production request in this observation window naturally triggered C1.

Therefore this closure does not claim a real S27/S38 production C1 fallback occurred. The C1 branch is covered by the reviewed Browser Plane router implementation and regression tests, including complete rendered-HTML artifact persistence for Lightpanda/Chrome, but live production evidence in this closure only proves the C0-selected branch.

A future natural C1 trigger should be observed and audited rather than forced by weakening the escalation policy.

## Security invariants preserved

- HTTPS/source/target/path allowlists remain authoritative.
- SignalForge cannot select Lightpanda, Chrome, Camoufox, or another Browser engine.
- plain 403, plain 429, timeout, DNS failure, connection refusal, or certificate failure do not independently authorize C1.
- C2 and C3 remain unauthorized by PUBLIC_READ_ACQUIRE.
- no inbound public listener/CDP endpoint was added to the Mac.
- no proxy or regional-egress authority was added.
- Provider max_run_seconds remains the total remote client budget.
- SignalForge continues to receive one integrity-bound HTML artifact through the existing Provider result framing.

## Operational conclusion

The caller-facing acquisition contract is now:

SignalForge: read this approved public URL.

Mac Browser Plane: choose C0 -> optionally C0b -> optionally C1 only with evidence -> return one full HTML artifact.

SignalForge no longer needs source logic that predicts whether C0 or C1 is required.

**Final state: VERIFIED / CLOSED.**
