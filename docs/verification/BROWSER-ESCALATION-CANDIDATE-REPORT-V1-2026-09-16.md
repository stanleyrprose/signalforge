# Browser Escalation Candidate Report v1 — 2026-09-16

## Purpose

Add a read-only SignalForge diagnostic that converts existing acquisition-failure evidence into a bounded list of sources worth testing with Mac Browser Plane. The report exists to stop ad-hoc browser-engine guessing and does not change production routing.

Local CLI:

```text
signalforge browser-escalation-candidates --window-days 7 --limit 20
```

The command is intentionally **not** added to the remote Control Plane verb manifest in v1.

## Evidence boundary

The report reads existing `acquisition_attempts`, `acquisition_requests`, `source_state`, and the current Source Registry. It performs no network I/O and no browser execution.

Only failed primary webpage acquisition attempts inside the requested time window are considered: `DISCOVERY` listing fetches and `HTML` detail fetches. PDF failures are excluded because they are not evidence for choosing a browser rendering engine.

## Classification policy

### `AB_TEST_CANDIDATE`

The following existing acquisition failure classes are sufficient to justify a bounded diagnostic A/B, not a routing change:

- `BOT_BLOCKED`
- `JS_RENDER_REQUIRED`
- `CONTENT_EMPTY`

Recommended diagnostic: same URL / same Mac egress / same time window across Chrome, nodriver, and Camoufox. Production routing remains unchanged until a repeatable incremental win is demonstrated.

### `REVIEW_FIRST`

- `HTTP_403`
- `TRANSPORT_UNKNOWN`

A generic HTTP 403 is never converted directly into browser escalation. Authentication, authorization, regional policy, WAF policy, rate limiting, or account state must be excluded first.

### `NOT_BROWSER`

DNS, strict-TLS, connect-timeout, 404, 429, 5xx, authentication, content-contract, and Provider lifecycle/integrity failures are classified as non-browser problems.

## Real-source rationale

The policy is derived from 2026-09-16 live source A/B evidence rather than generic browser assumptions:

- S21 Myanma Railways: Mac strict curl, Chrome, nodriver, and Camoufox all timed out. This is a network/origin reachability case, not a browser-engine case.
- S16 YCDC: an empty Lightpanda shell was recoverable by both Chrome and nodriver. Empty content is therefore valid browser A/B evidence, but not evidence for nodriver promotion by itself.
- S19 MOEP E-Tender: Chrome and nodriver returned the same administrator-stopped hosting page. A browser cannot repair issuer hosting state.
- S41 MYTEL/Viettel: ordinary strict curl received a D1N JavaScript cookie challenge while multiple browser engines could obtain the real JSON feed. Browser capability can add value, but nodriver had no unique advantage.
- LBVD: historical Bangkok HTTP 403 did not reproduce as a Mac browser-specific block; multiple browser engines returned the same real tender content. This is why HTTP 403 remains review-only.

Mac Browser Plane also now enforces `nonempty_rendered_body_v1`, so an empty C1 shell is no longer accepted as successful browser evidence.

## Output contract

Each source row exposes:

- source identity/name/role/priority;
- current acquisition engine and optional HTTP fetch profile;
- decision and candidate score;
- failure-class counts in the selected window;
- latest failed acquisition method/egress/time;
- current consecutive failures, last error, and last success;
- whether bounded browser A/B is eligible;
- a human-readable recommendation.

The top-level policy explicitly states:

- read-only;
- no browser execution;
- no source-routing mutation;
- generic HTTP 403 is not a browser trigger;
- TLS/DNS/timeout/auth are not browser triggers;
- an A/B result is required before any routing change.

## Verification

Implementation tests cover:

- `CONTENT_EMPTY` and `BOT_BLOCKED` -> `AB_TEST_CANDIDATE`;
- repeated `HTTP_403` -> `REVIEW_FIRST`, never browser-eligible;
- `CONNECT_TIMEOUT` -> `NOT_BROWSER` even with a high consecutive-failure count;
- PDF failures excluded from browser evidence;
- failures outside the selected time window ignored;
- window/limit bounds;
- existing remote verb manifest unchanged.

Targeted report + contract tests: **8/8 PASS**.

Full repository regression after implementation: **377/377 PASS**.

No schema migration, source-registry mutation, scheduler change, Browser Provider contract change, remote verb expansion, delivery change, or production route change is introduced by v1.
