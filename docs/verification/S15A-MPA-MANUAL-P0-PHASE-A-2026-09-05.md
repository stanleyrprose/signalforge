# S15A MPA Manual P0 Phase A — Evidence Bundle Preview

Date (Asia/Yangon): 2026-09-05
Status: IMPLEMENTATION / TEST PASS — LIVE VERIFICATION PENDING

## Decision

Do **not** build a Remote Provider Invocation Contract yet. Fresh MPA listing frequency is low enough for an operator-driven P0:

```text
all listing rows = 181
last 30 days     = 2
last 60 days     = 3
last 90 days     = 3
last 180 days    = 13
last 365 days    = 21
```

The listing was freshly acquired through Mac Browser Plane C0 as Browser Job `e47ddea6-59e2-4a50-aa07-1d2a53dc81da`, HTTP 200, 252,512 bytes, SHA-256 `c016d4efcae50f271e5e6860e1567650ee3d215c4ef7d9d31bd029ed4a0ec810`. At this event rate, a remote daemon/RPC/queue would be disproportionate to current operational burden.

Phase A therefore extends only the existing Manual Provider Bridge evidence path. It does **not** activate S15A and does **not** write canonical items or signals.

## Phase A contract

```text
LISTING provider evidence
  fixed MPA tender hub
       |
       v
DETAIL provider evidence
  explicit https://www.mpa.gov.mm/announcements/.../
  -> stable WordPress post ID
  -> exactly one issuer PDF locator
       |
       v
PDF provider evidence
  explicit https://www.mpa.gov.mm/wp-content/uploads/...pdf
  -> deterministic text-native PDF parser
       |
       v
mpa-provider-bundle-preview
  -> READY_FOR_MANUAL_COMMIT or REVIEW_REQUIRED
  -> no DB/canonical/signal write
```

All three acquisitions remain manual Mac C0 and all imported artifacts remain `EVIDENCE_ONLY`. `production_enabled=false`, `remote_invocation=false`, and `browser_production_approved=false` remain frozen.

## URL security boundary

The bridge does not become an arbitrary URL fetcher. Approved roles are:

```text
LISTING  fixed https://www.mpa.gov.mm/tenders-and-announcement/
DETAIL   host www.mpa.gov.mm, prefix /announcements/, trailing /
PDF      host www.mpa.gov.mm, prefix /wp-content/uploads/, suffix .pdf
```

DETAIL/PDF requests fail closed on another host, non-HTTPS scheme, credentials, non-standard port, query/fragment, path traversal, prefix drift, suffix drift or content-type contract mismatch.

## Durable evidence join

`load_imported_provider_artifact()` accepts only previously imported provider evidence and revalidates:

- unique `provider_request_id` correlation;
- `EVIDENCE_ONLY` processing provenance;
- stored request against the current bounded target contract;
- exactly one stored response artifact;
- SHA-256 and byte count against the EvidenceEnvelope;
- requested URL against the approved target.

The bundle preview then verifies the semantic relationship:

```text
listing contains detail URL
detail exposes WordPress shortlink ID
detail exposes exactly one issuer PDF URL
provided PDF URL equals that issuer locator
PDF parser returns decisive business semantics or REVIEW_REQUIRED
```

A decisive candidate uses canonical identity `mpa:<wordpress_post_id>`. Deadline output is timezone-aware `Asia/Yangon`; explicit MPA reference numbers win, otherwise preview uses `MPA-POST-<post_id>` as an identity reference fallback.

## Verification

Targeted tests after Phase A implementation:

```text
tests.test_provider_bridge + tests.test_mpa = 24/24 PASS
```

They prove:

- legacy fixed-listing Manual Provider Bridge remains backward compatible;
- bounded DETAIL and PDF requests carry the correct role/target kind/content-type contract;
- wrong host/path/query/fragment/traversal/suffix requests fail closed;
- PDF provider import remains `EVIDENCE_ONLY` with zero canonical/signals;
- durable imported artifact loading rechecks SHA/size/provenance;
- listing/detail/PDF relationship mismatch fails closed;
- Three-Tugs-style bundle produces candidate `mpa:37867`, `AUCTION_NOTICE`, publication date `2026-06-02`, deadline `2026-06-25T13:00:00+06:30`;
- `mpa-provider-bundle-preview` is not a Worker verb.

Full repository test discovery:

```text
91/91 PASS
```

## Production gate

Phase A is not complete until the merged exact SHA is live-verified on Bangkok without activating S15A:

1. deploy exact merged SHA through the normal controlled Bangkok release flow;
2. existing 12 active sources remain GREEN and business canonical/signals do not change due to deployment;
3. reuse or freshly import one LISTING evidence artifact;
4. create a bounded DETAIL provider request for one real MPA listing row, execute it manually on Mac C0, transfer/import as `EVIDENCE_ONLY`;
5. create the bounded PDF provider request from the issuer PDF locator, execute manually on Mac C0, transfer/import as `EVIDENCE_ONLY`;
6. run `mpa-provider-bundle-preview` on the three imported provider request IDs;
7. require stable WordPress identity + decisive business semantics + valid evidence relationship;
8. verify S15A canonical/signals remain `0/0`;
9. verify only the expected manual provider evidence lifecycles were added;
10. verify `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`;
11. Beijing remains SignalForge-free and both Worker doctors pass;
12. timer returns enabled/active and all 12 active sources remain GREEN.

Only after this gate passes may Phase B — an explicit, idempotent **manual canonical commit** — be designed. Phase B must not automatically turn the Manual Provider Bridge into unattended remote invocation.
