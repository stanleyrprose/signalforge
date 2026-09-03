# Trigger Policy v1

## R5 trigger model

R5 is polling-first. There is no public webhook ingress in this release.

`signalforge-run-due.timer` wakes the application every five minutes. The application owns source cadence and only runs a source when its durable `next_due_at` is due. S13 MPT starts with a 15-minute source cadence.

Every source execution creates a durable application scheduler Run containing:

- application run id
- trigger id
- source id
- trigger kind (`POLL`, `MANUAL`, or `RECONCILIATION` in R5)
- scheduled/observed time
- correlated Worker operational Run id
- terminal status and changed count

The Worker Run is read from the root-created `/run/worker/apps/signalforge/$INVOCATION_ID.json` descriptor. Production execution fails closed if that correlation descriptor is missing or inconsistent.

## Manual source refresh

Manual refresh is a closed source-ID operation, not a direct arbitrary application command. The reviewed path is:

```text
control-plane/Mac admin
→ signalforge-refresh <source_id>
→ validate Source Registry grammar + active membership
→ systemctl start signalforge-refresh@<source_id>.service
→ Worker prepare-application
→ signalforge refresh-source <source_id>
→ Worker finalize-application
```

The refresh template uses the same `signalforge` UID, `worker-signalforge.slice`, resource limits, sandbox and `/proc` isolation as the default scheduler. `refresh-source` forces a source execution even when `next_due_at` is in the future and records `trigger_kind=MANUAL` with an opaque correlated Worker Run. Arbitrary URLs are never accepted.

## Baseline semantics

The first successful source execution is a baseline. It may create evidence and canonical records, but it must create zero customer-visible signals. Later new canonical records create `NEW` signals; material content changes create `UPDATED` signals.

## Failure/recovery

A failed source attempt schedules a bounded retry window and does not discard a pending detail item. Discovery state separates the issuer-observed `lastmod` from the last successfully processed `fetched_lastmod`; updating a sitemap snapshot therefore cannot acknowledge work that has not actually been fetched.

Bangkok recovery is explicit and bounded:

- normal source cadence: 15 minutes for S13;
- recovery batch retry cadence while backlog remains: 5 minutes;
- per-run detail cap: `delta_detail_limit` (20 for S13 production);
- a missed-window run is recorded as `trigger_kind=RECONCILIATION`, `recovery=1`, with `outage_window_start/end`;
- the recovery window remains durable until pending backlog reaches zero;
- `signalforge status` exposes backlog count, oldest pending age and GREEN/YELLOW/RED recovery-backlog health;
- canonical upsert/dedup remains identical during recovery;
- no Bangkok outage causes Beijing takeover or an immediate crawl-all.

Baseline debt is also safe: a page discovered during the first baseline but temporarily failing detail fetch keeps a one-time signal-suppression marker until its first successful processing, so a transient baseline fetch failure cannot later create a false `NEW` customer signal.

S13 operating objectives for R5 are internal objectives rather than an external SLA: `DELAY_TOLERANT_MONITORED`, 15-minute business-data RPO target, 30-minute collection RTO/recovery SLO for the declared fixture, and a degraded-health indicator while recovery backlog exists.
