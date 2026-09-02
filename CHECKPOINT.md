# CHECKPOINT

Date: 2026-09-02 (Asia/Yangon)
Branch: `docs/gate-s-live-evidence`

## Production releases

- SignalForge application: `ef02915663eb6d5f9f70208eeaf07c28a07874da`
- Worker runtime/provider: `32caaed78e7e8557bd260c932a57e84745522c79`
- Control Plane closed verbs: `584e38ea4fc1a73817f878fcdcf5d64cf2efe91d`
- Gate O evidence merge: `4875036fabe7f7e1682773b33bf03cf1d25b0086`

## Gate O status

Gate O is PASS and MPT 24x7 polling is enabled on Bangkok.

- Bangkok-only SignalForge / Beijing strict absence: PASS
- real MPT Direct HTTP pipeline: PASS
- baseline suppression: PASS
- Worker Run correlation: PASS

## Gate S status

Gate S — Bangkok Recovery Reconciliation is PASS on 2026-09-02.

- implementation PR #3 CI PASS and squash merge: `ef02915663eb6d5f9f70208eeaf07c28a07874da`;
- pre-migration consistent SQLite backup: `quick_check=ok`;
- production schema migrated in place from v1 to v2, preserving canonical/evidence state and creating no false backlog;
- observed sitemap `lastmod` is separated from processed `fetched_lastmod`;
- pending recovery work survives snapshots and process boundaries;
- baseline detail debt remains retryable with one-time signal suppression;
- recovery scheduler rows carry `RECONCILIATION`, `recovery=1`, and durable outage-window metadata;
- isolated Bangkok LIVE_SHORT using exact deployed code drained five changed items as `2 + 2 + 1` bounded batches;
- backlog progressed `3 -> 1 -> 0` with no crawl-all storm;
- canonical keys remained unique and an unchanged follow-up produced zero duplicate signal;
- backlog health was visible through `signalforge status`;
- logical fixture recovery completed in 600s against the declared 1800s recovery SLO;
- isolated fixture did not mutate production SignalForge state;
- production timer was restored to enabled / active / waiting;
- Bangkok Worker/Nanobot and Beijing Worker/Hermes remained healthy;
- Beijing `/srv/signalforge` remains absent.

Sanitized live evidence is in `docs/verification/GATE-S-2026-09-02.md` and is pending documentation PR/CI merge.

## Next applicable R5 gate

Gate Z — SignalForge Single-scheduler Invocation is next. PRD acceptance requires:

- `signalforge-run-due.service` runs under `signalforge` identity;
- SignalForge does not use Generic `worker@.service`;
- no per-source production timers by default;
- one scheduler invocation maps to exactly one Worker operational Run;
- N business Jobs remain in SignalForge DB;
- Worker DB contains only opaque application correlation;
- `signalforge` cannot write `worker.db`;
- Beijing has strict zero SignalForge footprint.

## Next

1. commit/push/PR/CI/merge Gate S evidence and this checkpoint;
2. clean temporary Gate S staging/scripts while retaining the persistent pre-migration SQLite backup;
3. execute Gate Z LIVE_SHORT against the exact production releases using a controlled scheduler invocation;
4. verify unit identity/timer topology, Worker-to-business cardinality, DB ownership/ACL and Beijing strict absence;
5. write and merge Gate Z evidence;
6. then continue to the next applicable PRD gate, skipping R3 Browser and R6 Webhook gates unless their capabilities are actually being introduced.
