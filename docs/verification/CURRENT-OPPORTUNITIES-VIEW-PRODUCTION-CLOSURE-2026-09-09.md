# Current Opportunities View — Production Closure — 2026-09-09

## Result

**PASS / PRODUCTION LIVE / READ-ONLY CUSTOMER-CONSUMABLE VIEW**

SignalForge had reached a point where acquisition, canonicalization and signal generation were production-stable, but the repository still had no minimal reader that answered the product question: “What signal-backed tender opportunities are currently actionable?” Signals were written and counted, but no CLI/feed deduplicated repeated updates, applied current deadline state, or exposed the current canonical business fields.

PR #101 adds the smallest useful read surface:

`signalforge opportunities`

This is intentionally not a dashboard, API service, delivery subsystem or new Worker verb.

## Read semantics

The view is derived only from existing durable SignalForge state.

Default eligibility:

- canonical `item_kind=TENDER`;
- current canonical `business_stage=OPPORTUNITY`;
- canonical has at least one existing customer signal;
- one row per canonical regardless of signal history length;
- business fields come from the current canonical payload, not a stale historical signal payload;
- `OPEN` deadlines are shown;
- deadline `UNKNOWN` rows remain visible and explicitly marked;
- `EXPIRED` rows are hidden by default;
- `--include-expired` can expose expired rows for audit;
- `--source-id` provides a source filter;
- `--limit` is bounded to 1..500, default 50.

Each returned row includes current tender identity/business fields plus signal provenance:

- source ID / canonical key;
- title / reference number;
- publication date;
- deadline / deadline time / normalized Myanmar-local deadline timestamp;
- `deadline_status` (`OPEN`, `UNKNOWN`, `EXPIRED`);
- remaining seconds when deadline is known;
- issuer / location / scope;
- detail completeness;
- canonical URL;
- latest signal type / timestamp / reason;
- total signal count for the canonical.

## Safety / architecture boundary

The command is deliberately absent from the versioned Worker verb manifest. Therefore the production Control/Worker invocation surface remains unchanged.

The implementation introduces:

- no DB schema change;
- no DB write;
- no scheduler behavior change;
- no acquisition behavior change;
- no signal-generation behavior change;
- no Provider or Browser capability;
- no new daemon/service/listener;
- no Beijing dependency.

Unsignaled canonicals are not silently promoted into this view. Signal policy remains the gate for customer-visible opportunity eligibility; the reader only presents signal-backed current canonical state.

## Test gate

Targeted opportunities/contract tests:

`7 passed`

Full SignalForge suite:

`220 passed`

`git diff --check`: PASS.

PR #101 passed CI and squash-merged as:

`9f6ee1e39737c9226574d2a7bb9f3dc92fbf2691`

## Production rollout

Pre-deploy production state:

- active release: `6f10d0f5a7cf37ca11d8461c03a54b3ff9f648c7`;
- canonical items: `193`;
- signals: `42`;
- SQLite quick check: `ok`;
- timer enabled/active before reviewed freeze.

The timer was frozen for exact-release deployment. Archive SHA matched locally/remotely:

`5930863d92cda9bf70cb697dd29ea7a839a14e81e1afdc46cf1fc2113a0f1b39`

Exact release `9f6ee1e39737c9226574d2a7bb9f3dc92fbf2691` deployed successfully with rollback target `6f10d0f5a7cf37ca11d8461c03a54b3ff9f648c7`. Timer remained disabled during the read-only live gate.

## Live opportunities gate

The installed production CLI was executed as the dedicated `signalforge` user against the production DB.

Default result:

- status: `PASS`;
- count: `9`;
- total matching: `9`;
- OPEN: `8`;
- UNKNOWN: `1`;
- EXPIRED: `0`.

Current rows at the verification snapshot, in default order:

1. `industry:1022` — OPEN — 2026-09-11 16:00
2. `industry:1034` — OPEN — 2026-09-14 16:00
3. `energy:235` — OPEN — 2026-09-18 13:00
4. `mofa:59800` — OPEN — 2026-09-18 16:30
5. `industry:1037` — OPEN — 2026-09-22 16:00
6. `industry:1036` — OPEN — 2026-09-24 16:00
7. `industry:1039` — OPEN — 2026-09-25 16:00
8. `industry:1035` — OPEN — 2026-10-02 16:00
9. `doms:12735` — UNKNOWN deadline

Each of the nine rows had `signal_count=1` in the live snapshot.

The same read left durable business state unchanged:

- canonical items: `193`;
- signals: `42`;
- SQLite quick check: `ok`.

This also proves that the earlier historical S25 URL-only signal noise does not create duplicate rows in the current opportunity view: repeated signal history is collapsed to the current canonical.

## Timer restoration / unattended scheduler gate

Bangkok timer was restored `enabled/active` after the read-only gate.

A normal production `run-due` then completed `SUCCESS` on exact release `9f6ee1e39737c9226574d2a7bb9f3dc92fbf2691`. It exercised real due work including S13, S20, S21, S22, S34, S37, S39 and S38; health probes that ran completed successfully and created zero new signals.

Final production status after that scheduler cycle:

- active application: `9f6ee1e39737c9226574d2a7bb9f3dc92fbf2691`;
- timer: enabled / active;
- run-due: inactive after successful completion;
- SignalForge: `PASS / GREEN`;
- non-GREEN sources: none;
- canonical items: `193`;
- signals: `42`;
- recovery backlog: `0`;
- SQLite quick check: `ok`.

A second read of `signalforge opportunities` after the scheduler cycle still returned the same current snapshot of `8 OPEN + 1 UNKNOWN` opportunities.

## Product implication

SignalForge now has a minimal end-to-end product path:

`issuer evidence -> canonical business facts -> customer signal -> current opportunity view`

The next slice should not default to a dashboard or machine-learning ranking system. Ranking/prioritization is only justified once explicit business relevance criteria are defined. Until then, the current read surface is deliberately factual, deterministic and provenance-preserving.
