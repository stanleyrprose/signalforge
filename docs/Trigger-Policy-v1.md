# Trigger Policy v1

## R5 trigger model

R5 is polling-first. There is no public webhook ingress in this release.

`signalforge-run-due.timer` wakes the application every five minutes. The application owns source cadence and only runs a source when its durable `next_due_at` is due. S13 MPT starts with a 15-minute source cadence.

Every source execution creates a durable application scheduler Run containing:

- application run id
- trigger id
- source id
- trigger kind (`poll`)
- scheduled/observed time
- correlated Worker operational Run id
- terminal status and changed count

The Worker Run is read from the root-created `/run/worker/apps/signalforge/$INVOCATION_ID.json` descriptor. Production execution fails closed if that correlation descriptor is missing or inconsistent.

## Baseline semantics

The first successful source execution is a baseline. It may create evidence and canonical records, but it must create zero customer-visible signals. Later new canonical records create `NEW` signals; material content changes create `UPDATED` signals.

## Failure/recovery

A failed source attempt schedules a bounded retry window and does not advance the source baseline. Recovery processes only sitemap entries whose identity/lastmod differs from durable source state, subject to the per-run detail-fetch cap. R5 does not implement crawl-all catch-up.
