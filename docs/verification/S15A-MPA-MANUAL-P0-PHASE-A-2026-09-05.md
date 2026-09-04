# S15A MPA Manual P0 Phase A — Evidence Bundle Preview

Date (Asia/Yangon): 2026-09-05
Status: PRODUCTION LIVE PASS — PHASE B DEFERRED

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

## Production live verification

Phase A was deployed and live-verified on Bangkok as exact application release:

```text
bd4e217d0b036a436290462ce9f1393defd00d6c
```

Rollback remained the previous verified release:

```text
f4a3dfd0ae77797b8fd82911fb908097a1dc97d8
```

The deployment ran while `signalforge-run-due.timer` was intentionally disabled. Immediately after deploy:

```text
active release              = bd4e217d0b036a436290462ce9f1393defd00d6c
SignalForge                 = PASS / GREEN
12/12 active sources        = GREEN
browser_production_approved = false
canonical_items             = 124
signals                     = 11
S15A lifecycle              = 1/1/1/1/1
S15A canonical/signals      = 0/0
SQLite quick_check          = ok
```

No business count changed during deployment.

The previously imported LISTING evidence was reused:

```text
provider_request_id = 74a9b732-6f04-4222-b999-3eac12611647
evidence_id         = 47e48422-d3c0-431e-b787-a5339285f9a6
URL                 = https://www.mpa.gov.mm/tenders-and-announcement/
SHA-256             = c016d4efcae50f271e5e6860e1567650ee3d215c4ef7d9d31bd029ed4a0ec810
```

A real bounded DETAIL provider request was created for:

```text
https://www.mpa.gov.mm/announcements/open-tender-invitation-for-three-tugs-2/
```

and executed manually through Mac Browser Plane C0:

```text
provider_request_id = 88f20980-9e2f-45c4-a6fe-42da3ed484e2
Browser Job         = 0a65f464-19de-4c3a-a05f-73f1d50a1e39
HTTP                = 200
content-type        = text/html; charset=UTF-8
bytes               = 100,820
SHA-256             = 6e90328a949d50e18674ab14aed1d9a1b8a78fa6737513510aec93c34cee6b12
processing          = EVIDENCE_ONLY
```

The imported detail deterministically exposed:

```text
WordPress post ID = 37867
issuer PDF URL    = https://www.mpa.gov.mm/wp-content/uploads/2026/06/Three-Tug-Tender-Eng.pdf
```

A real bounded PDF provider request was then created from that issuer locator and executed manually through Mac Browser Plane C0:

```text
provider_request_id = 9d3aa060-168a-4fcc-9a4c-3262aace2ee1
Browser Job         = 31a8e346-263a-450f-b521-3931db0b66f5
HTTP                = 200
content-type        = application/pdf
bytes               = 101,698
SHA-256             = 9a664132a31c682d48d765c44e5b0d83c5e165bb1aebe9cc770b3f26ba30d046
processing          = EVIDENCE_ONLY
```

After DETAIL + PDF imports, S15A durable state was exactly:

```text
scheduler_runs       = 3
acquisition_requests = 3
acquisition_attempts = 3
evidence_envelopes   = 3
processing_records   = 3
EVIDENCE_ONLY        = 3
canonical_items      = 0
signals              = 0
```

The two new durable provider evidence directories retained production permissions:

```text
provider directory   = 0700
request.json         = 0600
browser-result.json  = 0600
response artifact    = 0640
```

The read-only bundle preview over the three imported provider request IDs returned:

```text
status                        = READY_FOR_MANUAL_COMMIT
canonical candidate           = mpa:37867
identity_status               = WORDPRESS_POST_ID
listing provisional item_kind = TENDER
final PDF item_kind           = AUCTION_NOTICE
classification                = DETERMINISTIC_PDF / AUCTION_EN
publication_date              = 2026-06-02
deadline                      = 2026-06-25T13:00:00+06:30
reference_no                  = MPA-POST-37867
reference_no_kind             = wordpress_post_id
```

The PDF evidence explicitly states that the three tugs will be auctioned through an open tender system, so the live evidence chain proves why listing-only classification is unsafe.

No canonical or signal write occurred during bundle preview.

Paused-window integrity checks:

```text
canonical_items             = 124
signals                     = 11
recovery_backlog            = 0
SQLite quick_check          = ok
Worker SignalForge Runs     = 583
mac production_enabled      = false
mac remote_invocation       = false
browser_production_approved = false
Bangkok Worker doctor       = PASS
Beijing /srv/signalforge    = ABSENT
Beijing Worker doctor       = PASS
```

The two manual Mac provider imports did not create VPS Worker Runs.

After verification, the scheduler timer was restored. One normal due-cycle invocation ran and completed:

```text
timer                       = enabled / active
run-due service             = inactive
SignalForge                 = PASS / GREEN
12/12 active sources        = GREEN
canonical_items             = 124
signals                     = 11
recovery_backlog            = 0
S15A canonical/signals      = 0/0
S15A EVIDENCE_ONLY          = 3
Worker SignalForge Runs     = 584
```

The `583 -> 584` Worker increment came from the resumed normal scheduler invocation, not from the manual Mac provider evidence path.

## Gate result

**Manual P0 Phase A = PRODUCTION LIVE PASS.**

The following are now proven together in production:

```text
bounded LISTING / DETAIL / PDF provider request contract
+ manual Mac C0 acquisition
+ EVIDENCE_ONLY durable import
+ stable WordPress identity
+ issuer-PDF relationship validation
+ deterministic PDF business classification
+ read-only bundle candidate generation
+ zero canonical/signal side effect
```

Phase B remains intentionally separate. An explicit, idempotent **manual canonical commit** may now be designed, but it is not authorized by this Phase A closure. Phase B must not enable unattended Mac invocation or turn S15A into a scheduled active source.
