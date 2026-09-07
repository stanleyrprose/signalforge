# CHECKPOINT

Date: 2026-09-04 (Asia/Yangon)
Branch: `main` after S28 Department of Fisheries production onboarding closure.

## Production releases

- SignalForge current application: `d1f6d1773390767e73747df75e81383e4997f053`
- Immediate SignalForge rollback (twelve-source S28 release): `7413a9da60a1b0c3bf82ac0b30f00fe625ca75a2`
- Previous eleven-source + locked Mac-provider projection: `0a3e6156f2635fd9509738d3b6c0aa1d073f6c03`
- Previous eleven-source application before Mac-provider projection: `ae894d092f97843280c92228d6b43eda3bf0336f`
- Previous ten-source S05A + S07 + S08A + S10 + S12 + S13 + S20 + S21 + S22 + S25 release: `930c94641b0699072350dcea9344aa55e930e169`
- Previous nine-source S05A + S07 + S08A + S10 + S12 + S13 + S20 + S21 + S22 release: `3f31b937cc8dbe2941e85b1f810f2bd8a9b811fb`
- Previous eight-source S05A + S07 + S08A + S12 + S13 + S20 + S21 + S22 release: `d5222d00e81692ae4f4b8ee3d0a3d7ad70618237`
- Previous SignalForge S05A + S07 + S08A + S13 + S20 + S21 + S22 release: `cb5291fdfcc13a678f63b53072e39089f8c27258`
- Previous SignalForge S05A + S07 + S13 + S20 + S21 + S22 release: `edf3e342ad127b4beac93a285bfb0096a1815aaa`
- Previous SignalForge S05A + S13 + S20 + S21 + S22 release: `3c833d62dcf16ecd9e4b12dafd9ac557417efddb`
- Previous SignalForge S13 + S20 + S21 + S22 release: `255f18f3dd919b6e77b9d3138839f0439062e3bc`
- Previous SignalForge S13 + S21 + S22 release: `9ec2b133ca1c3339abccf34c5f5c86cecd3e6023`
- Previous SignalForge S13 + S21 release: `52c9ab5b5e5643014e1b55a634cc5fbe26c0ebac`
- Previous SignalForge v1.5 S13-only release: `618afaf4e6ef2ac7fdde64931f2a87dbc053a6f6`
- SignalForge v1.4.5 known-good rollback: `d36f38336bf1b10580cffdb7fa96c7db119c2079`
- Worker runtime/provider on Bangkok + Beijing: `0a53558c9233622c69b083d61bed596cbedc0857`
- Control Plane dispatcher/validator: `64ab3a907bb8a18808839176208023a5de976b55`

## Current production health

- Worker fleet: `FULL 2/2`
- Bangkok Worker Runtime: PASS
- Beijing Worker Runtime: PASS
- Bangkok `nanobot-gateway.service`: active
- Beijing `hermes-gateway.service`: active
- Bangkok SignalForge: ENABLED / GREEN
- S05A source health: GREEN
- S05A parse health at baseline: GREEN (`3/3`, ratio `1.0`)
- S05A canonical domain: `REGULATORY_NOTICE`; baseline `items_parsed=3`, `tenders_parsed=0`
- S07 source health: GREEN
- S07 parse health at baseline: GREEN (`1/1`, `BUSINESS_PROCESSING`)
- S07 canonical domain: `REGULATORY_NOTICE`; baseline `items_parsed=5`, `tenders_parsed=0`, `details_attempted=0`
- S08A source health: GREEN
- S08A parse health at baseline: GREEN (`1/1`, `BUSINESS_PROCESSING`)
- S08A canonical domain: `AUCTION_NOTICE`; baseline `items_parsed=4`, `tenders_parsed=0`, `details_attempted=0`
- S10 source health: GREEN
- S10 parse health at baseline: GREEN (`4/4`, ratio `1.0`)
- S10 canonical domain: `REGULATORY_NOTICE`; baseline `items_parsed=12`, `tenders_parsed=0`, health sample `details_attempted=4`
- S10 PDF value gate: TRIGGERED; extraction/runtime packaging: `DEFERRED_ZERO_DEPENDENCY`
- S12 source health: GREEN
- S12 parse health at baseline: GREEN (`9/9`, ratio `1.0`)
- S12 canonical domain: `REGULATORY_NOTICE`; baseline `items_parsed=9`, `tenders_parsed=0`, `details_attempted=9`
- S13 source health: GREEN
- S20 source health: GREEN
- S20 parse health at baseline: GREEN (`5/5`, ratio `1.0`)
- S20 attachment health: DEGRADED (`0/5` current advertised PDFs retrievable; metadata-only/non-blocking)
- S21 source health: GREEN
- S22 source health: GREEN
- S22 parse health at baseline: GREEN (`4/4`, ratio `1.0`)
- S25 source health: GREEN
- S25 parse health at baseline: GREEN (`1/1`, `BUSINESS_PROCESSING`)
- S26 source health: GREEN
- S26 parse health at baseline: GREEN (`2/2`, ratio `1.0`)
- S26 canonical domain: `TENDER`; baseline `items_parsed=2`, `tenders_parsed=2`, `details_attempted=2`
- S28 source health: GREEN
- S28 parse health at baseline: GREEN (`1/1`, `BUSINESS_PROCESSING`)
- S28 canonical domain: `TENDER`; baseline `items_parsed=8`, `tenders_parsed=8`, `details_attempted=0`
- Mac provider projection: `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`
- Bangkok `signalforge-run-due.timer`: enabled / active / waiting
- Beijing SignalForge placement: DISABLED with strict `/srv/signalforge` absence
- SQLite `PRAGMA quick_check`: ok

## Current SignalForge business state

Current live snapshot after S28 onboarding and the separately reviewed Manual Provider Bridge production verification:

```text
current_application=d1f6d1773390767e73747df75e81383e4997f053
canonical_items=124
signals=11
scheduler_runs=458
failed_runs=1
recovery_backlog=0
acquisition_requests=600
acquisition_attempts=600
evidence_envelopes=599
processing_records=599
Worker SignalForge application Runs=574
```

All twelve active sources remain GREEN. The single historical failed run remains the pre-existing/recovered S10 DICA `CONNECT_TIMEOUT`; it is not an S28 or Manual Provider Bridge failure. The durable lifecycle remains one evidence/processing row lower than request/attempt totals because that failed acquisition correctly has no fake evidence/processing row. S28-specific rollout counters remain frozen in the S28 onboarding section below.

Per-source canonical/signal state verified during the paused rollout window:

```text
S05A canonical_items=3  / signals=0 / item_kind=REGULATORY_NOTICE
S07 canonical_items=5   / signals=0 / item_kind=REGULATORY_NOTICE
S08A canonical_items=4  / signals=0 / item_kind=AUCTION_NOTICE
S10 canonical_items=12  / signals=0 / item_kind=REGULATORY_NOTICE
S12 canonical_items=9   / signals=0 / item_kind=REGULATORY_NOTICE
S13 canonical_items=16  / signals=10 / item_kind=TENDER
S20 canonical_items=6   / signals=1 / item_kind=TENDER
S21 canonical_items=45  / signals=0 / item_kind=TENDER
S22 canonical_items=4   / signals=0 / item_kind=TENDER
S25 canonical_items=10  / signals=0 / item_kind=TENDER
S26 canonical_items=2   / signals=0 / item_kind=TENDER
S28 canonical_items=8   / signals=0 / item_kind=TENDER
```

S22 onboarding-owned acquisition lifecycle:

```text
acquisition_requests=5
acquisition_attempts=5
evidence_envelopes=5
processing_records=5
```

The four S22 rows are issuer nodes 1038, 1037, 1036 and 1035. The baseline created no customer signals.

## Production sources

### S05A — Ministry of Commerce Trade Notifications — GREEN / PRODUCTION COMPLETE

Current production release: `3c833d62dcf16ecd9e4b12dafd9ac557417efddb`.

Source/domain shape:

```text
Myanmar Commerce Notifications Drupal view
-> bounded HTML detail fetch
-> ACTIVE_SELECTIVE business classification
-> zero/one REGULATORY_NOTICE canonical item
-> attachment metadata only
```

First baseline: 3 selected regulatory notices, `items_parsed=3`, `tenders_parsed=0`, zero signals.

### S13 — MPT Tender Information — GREEN

Existing production semantics remain unchanged.

### S07 — Myanmar Customs Notifications — GREEN / PRODUCTION COMPLETE

Current production release: `edf3e342ad127b4beac93a285bfb0096a1815aaa`.

Source/domain shape:

```text
Customs /notifications HTML table
-> listing-complete regulatory records
-> one acquisition/evidence/processing lifecycle
-> N REGULATORY_NOTICE canonical items
-> attachment metadata only
```

First baseline: 5 regulatory notices, `items_parsed=5`, `tenders_parsed=0`, `details_attempted=0`, zero signals. Canonical identity uses normalized issuer notification/order number.

### S08A — Myanmar Customs Auction Announcements — GREEN / PRODUCTION COMPLETE

Current production release: `cb5291fdfcc13a678f63b53072e39089f8c27258`.

Source/domain shape:

```text
Customs /Announcements mixed HTML
-> visible-date evidence + auction classifier
-> tender-award/result excluded
-> one acquisition/evidence/processing lifecycle
-> N AUCTION_NOTICE canonical items
-> attachment metadata only
```

First baseline: 4 auction notices, `items_parsed=4`, `tenders_parsed=0`, `details_attempted=0`, zero signals. Current PDF set is mixed text-native/scan; no OCR/PDF production parser was introduced.

### S10 — DICA Company and Investment Announcements — GREEN / PRODUCTION COMPLETE

Current production release: `3f31b937cc8dbe2941e85b1f810f2bd8a9b811fb`.

Source/domain shape:

```text
DICA announcements WordPress category
-> bounded 12-detail Direct HTTP fetch
-> ACTIVE_SELECTIVE company/investment event classifier
-> REGULATORY_NOTICE canonical item keyed by WordPress post ID
-> official PDF metadata only
```

First baseline: 12 regulatory event items, `items_parsed=12`, `tenders_parsed=0`, parse-health sample `4/4`, zero signals. Categories: company strike-off batch=9, company compliance=1, investment tax incentive=1, investment capital currency=1. PDF business value is proven, but extraction/runtime packaging remains a separate deferred capability.

### S12 — IRD Business Tax Announcements — GREEN / PRODUCTION COMPLETE

Current production release: `d5222d00e81692ae4f4b8ee3d0a3d7ad70618237`.

Source/domain shape:

```text
IRD /announcement-lists HTML
-> bounded 180-day detail fetch
-> ACTIVE_SELECTIVE tax classifier
-> zero/one REGULATORY_NOTICE canonical item
-> attachment metadata only
```

First baseline: 9 tax/regulatory notices, `items_parsed=9`, `tenders_parsed=0`, `details_attempted=9`, parse `9/9`, zero signals. IRD procurement tenders and non-tax institutional noise are excluded.

### S20 — MOEP Main Tender Hub — GREEN / PRODUCTION COMPLETE

First onboarding release: `255f18f3dd919b6e77b9d3138839f0439062e3bc`.

Source shape:

```text
/mm/ignite/page/62 HTML
-> latest 5 official tender items
-> one detail page -> one partial HTML tender
-> attachment metadata only
```

First production baseline through reviewed `signalforge-refresh S20`:

```text
baseline=1
status=SUCCESS
details_attempted=5
details_succeeded=5
tenders_parsed=5
changed=5
signals_created=0
worker_run_id=signalforge-20260904T011731Z-2575d704
```

Worker correlation:

```text
Worker SignalForge Runs: 389 -> 390
latest Worker Run=signalforge-20260904T011731Z-2575d704 / SUCCESS
```

S20 persistence:

```text
requests=6
attempts=6
evidence=6
processing=6
canonical=5
signals=0
PDF requested_url count=0
```

Current official attachment reality is degraded: the latest 5 advertised PDFs returned HTTP 404 from Bangkok. This does not reduce S20 HTML source health because attachments are explicitly `METADATA_ONLY_NON_BLOCKING`. Missing deadline/business-detail fields remain unknown rather than inferred.

Evidence: `docs/verification/S20-SOURCE-ONBOARDING-2026-09-04.md`.

### S21 — Myanma Railways Tenders — GREEN

- Direct HTTP / structured multi-item Railway detail pages.
- 45 canonical items remain durable.
- zero S21 customer signals have been created by the baseline.
- onboarding evidence: `docs/verification/S21-SOURCE-ONBOARDING-2026-09-04.md`.

### S22 — Inland Water Transport Tenders — GREEN / PRODUCTION COMPLETE

Production release: `9ec2b133ca1c3339abccf34c5f5c86cecd3e6023`.

Source shape:

```text
/tenders HTML
-> N Drupal tender nodes
-> one tender node -> one business tender
-> attachment metadata only
```

Canonical identity:

```text
iwt:<issuer Drupal node id>:<publication date>
```

Example:

```text
iwt:1038:2026-08-25
```

The required legacy `reference_no` field is explicit issuer-record metadata (`IWT-NODE-1038`, `reference_no_kind=issuer_record_id`) rather than pretending the node id is a business tender number.

First production baseline through reviewed `signalforge-refresh S22`:

```text
baseline=1
status=SUCCESS
details_attempted=4
details_succeeded=4
tenders_parsed=4
changed=4
signals_created=0
worker_run_id=signalforge-20260904T004652Z-d4992f14
```

Worker correlation:

```text
Worker SignalForge Runs: 381 -> 382
latest Worker Run=signalforge-20260904T004652Z-d4992f14 / SUCCESS
S22 scheduler worker_run_id=same
```

S22 acquisition/evidence persistence:

```text
requests=5
attempts=5
evidence=5
processing=5
canonical=4
signals=0
```

Evidence: `docs/verification/S22-SOURCE-ONBOARDING-2026-09-04.md`.

## S22 transport finding

A bare library-default Python urllib request currently receives HTTP 403 from IWT, but the already-frozen SignalForge application fetcher identity succeeds. Bangkok production egress using the actual SignalForge fetcher returned three consecutive successful Direct HTTP reads of the listing and successfully fetched node 1038.

This is an HTTP client-identity policy difference, not a Browser/JS-render requirement. No Browser gate was triggered and no browser-like spoofing was added.

If the production SignalForge fetcher itself later receives HTTP 403, the existing policy remains `HTTP_403 -> REVIEW`.

## S22 detail-change probe

IWT listing timestamps are publication timestamps and may not change when an existing tender's deadline/body changes.

Tender-only sources now use the newest currently discovered tender for the existing bounded low-frequency detail probe before falling back to static bootstrap seeds.

The regression fixture proved:

```text
same canonical iwt:1038:2026-08-25
deadline 2026-11-03 -> 2026-11-10
result=UPDATED, not duplicate NEW
```

This applies to S21/S22 tender-only discovery and does not change MPT behavior.

## Gate Z reconfirmation after S22

Before S22 baseline:

```text
Worker SignalForge Runs=381
scheduler_runs=128
```

After reviewed S22 baseline:

```text
Worker SignalForge Runs=382
scheduler_runs=129
```

Exactly one Worker operational Run correlated to the S22 manual baseline while five acquisition attempts and four business items remained internal SignalForge state.

After `signalforge-resume`, the persistent timer created one wrapper:

```text
Worker SignalForge Runs: 382 -> 383
```

S13 and S21 had become due during the controlled pause, so that single wrapper processed two business source jobs:

```text
S13 POLL = SUCCESS, details 1/1, signals 0
S21 POLL = SUCCESS, no pending detail, signals 0
scheduler_runs: 129 -> 131
```

This is the intended Gate Z relationship:

> one Worker wrapper Run may own N due SignalForge business source jobs; business jobs do not become separate Worker Runs.

S22 was not run again because its `next_due_at` had not arrived.

## Topology / integrity verification — PASS

- `PRAGMA quick_check=ok`.
- Bangkok Worker doctor: PASS.
- Beijing Worker doctor: PASS.
- Beijing `/srv/signalforge`: absent.
- Beijing `signalforge-refresh S22`: `126 / DENY: SignalForge is Bangkok-only`.
- `signalforge-run-due.timer`: enabled / active / waiting.
- final SignalForge health: GREEN.
- S13/S21/S22 final source health: GREEN.
- final `failed_runs=0`.
- final `recovery_backlog=0`.

## Completed SignalForge / integration gates

### Gate O — Topology / MPT fixture — PASS

Bangkok-only SignalForge and the original MPT pipeline remain proven.

Evidence: `docs/verification/GATE-O-2026-09-02.md`.

### Gate S — Bangkok Recovery Reconciliation — PASS

Recovery backlog remains durable and bounded without crawl-all storms or duplicate signals.

Evidence: `docs/verification/GATE-S-2026-09-02.md`.

### Gate Z — Single-scheduler Invocation — PASS

S22 onboarding reconfirmed both forms:

- one manual source baseline -> one Worker Run;
- one timer wrapper -> multiple due business source rows while remaining one Worker Run.

Evidence: `docs/verification/GATE-Z-2026-09-03.md`, S21 onboarding and S22 onboarding records.

### Gate AA — Cross-repo Verb Compatibility — PASS

- `verb_manifest_version=1` remains live;
- active Source Registry membership now exposes `S13`, `S20`, `S21`, `S22`;
- Beijing continues to reject SignalForge control verbs.

### Gate AB — v1.5 Production Compatibility — PASS

v1.5 remains the frozen acquisition/Worker compatibility baseline.

Evidence: `docs/verification/GATE-AB-2026-09-03.md`.

### S21 Source Onboarding — PASS

Evidence: `docs/verification/S21-SOURCE-ONBOARDING-2026-09-04.md`.

### S22 Source Onboarding — PASS

- PR #16 CI PASS and merged;
- exact SHA deployed to Bangkok only;
- Direct HTTP transport verified using the real SignalForge fetcher identity;
- first baseline signal suppression verified;
- four IWT canonical items durable;
- full closing-time and attachment metadata preserved from HTML;
- no PDF parser or Browser capability added;
- SQLite quick_check ok;
- Worker cardinality/correlation verified;
- Bangkok + Beijing Worker doctors PASS;
- Beijing remains strict zero-footprint and rejects `signalforge-refresh S22`;
- timer restored enabled / active / waiting;
- resumed wrapper processed due S13/S21 correctly with no signals or canonical changes.

Evidence: `docs/verification/S22-SOURCE-ONBOARDING-2026-09-04.md`.

### S20 Source Onboarding — PASS

- PR #18 CI PASS and merged;
- exact SHA `255f18f3dd919b6e77b9d3138839f0439062e3bc` deployed to Bangkok only;
- first baseline parsed 5/5 current MOEP detail pages;
- first baseline created zero customer signals;
- 5 S20 canonical items durable;
- one category + five detail acquisitions persisted; zero PDF requested URLs;
- SQLite quick_check ok;
- Worker cardinality/correlation verified (`389 -> 390`);
- Bangkok + Beijing Worker doctors PASS;
- Beijing remains strict zero-footprint and rejects `signalforge-refresh S20`;
- timer restored enabled / active / waiting with no immediate extra wrapper;
- S13/S21/S22 canonical/signal state remained unchanged.

Evidence: `docs/verification/S20-SOURCE-ONBOARDING-2026-09-04.md`.

### S05A Commerce Regulatory Notice Onboarding — PASS

- PR #21 CI PASS and squash-merged;
- exact SHA `3c833d62dcf16ecd9e4b12dafd9ac557417efddb` deployed to Bangkok only;
- additive schema v5 migrated 70 existing canonical rows to `item_kind=TENDER` with no business/signal changes;
- first baseline created 3 `REGULATORY_NOTICE` canonical items and zero customer signals;
- baseline operational metrics: `items_parsed=3`, `tenders_parsed=0`, parse `3/3`;
- one discovery + fifteen HTML detail acquisitions persisted; PDF requested URLs remained zero;
- Worker cardinality/correlation verified (`404 -> 405`) for the manual refresh;
- timer resume produced one Worker wrapper (`405 -> 406`) while SignalForge scheduler/business counts remained unchanged;
- SQLite quick_check ok;
- Bangkok + Beijing Worker doctors PASS;
- Beijing remains strict zero-footprint and rejects `signalforge-refresh S05A`;
- S13/S20/S21/S22 remained GREEN.

Evidence: `docs/verification/S05A-SOURCE-ONBOARDING-2026-09-04.md`.

### S07 Customs Notifications Onboarding — PASS

- PR #24 CI PASS and squash-merged;
- exact SHA `edf3e342ad127b4beac93a285bfb0096a1815aaa` deployed to Bangkok only;
- pre-deploy state frozen at canonical `74`, signals `11`, scheduler runs `192`, Worker Runs `439`;
- first baseline created 5 `REGULATORY_NOTICE` canonical items and zero customer signals;
- baseline metrics: `items_parsed=5`, `tenders_parsed=0`, `details_attempted=0`;
- exactly one request/attempt/evidence/processing record persisted; no `discovery_items` and zero PDF requested URLs;
- S07 parse health GREEN from `BUSINESS_PROCESSING` (`1/1`);
- Worker cardinality/correlation verified (`439 -> 440`);
- Bangkok + Beijing Worker doctors PASS;
- Beijing remains strict zero-footprint and rejects `signalforge-refresh S07`;
- timer resume wrapper changed Worker Runs `440 -> 441` and processed due S05A/S13/S20/S21/S22 with zero changes/signals;
- timer restored enabled / active / waiting;
- all six sources GREEN;
- PRD v1.5.1 Browser invariant preserved: no VPS Browser runtime and no SignalForge→Mac remote invocation.

Evidence: `docs/verification/S07-SOURCE-ONBOARDING-2026-09-04.md`.

### S08A Customs Auction Announcements Onboarding — PASS

- PR #26 CI PASS and squash-merged;
- exact SHA `cb5291fdfcc13a678f63b53072e39089f8c27258` deployed to Bangkok only;
- immediate rollback is `edf3e342ad127b4beac93a285bfb0096a1815aaa`;
- pre-deploy state frozen at canonical `79`, signals `11`, scheduler runs `198`, Worker Runs `443`;
- first baseline created 4 `AUCTION_NOTICE` canonical items and zero customer signals;
- baseline metrics: `items_parsed=4`, `tenders_parsed=0`, `details_attempted=0`;
- exactly one request/attempt/evidence/processing record persisted; no `discovery_items` and zero PDF requested URLs;
- tender-award/result announcement remained excluded from the auction slice;
- S08A parse health GREEN from `BUSINESS_PROCESSING` (`1/1`);
- Worker cardinality/correlation verified (`443 -> 444`);
- Bangkok + Beijing Worker doctors PASS;
- Beijing remains strict zero-footprint and rejects `signalforge-refresh S08A`;
- pause-window freshness aging temporarily produced `SOURCE_FRESHNESS_LAG` on existing sources without fetch/parse failures;
- timer resume wrapper changed Worker Runs `444 -> 445` and reconciled S05A/S07/S13/S20/S21/S22, all `SUCCESS`, `changed=0`, `signals=0`;
- timer restored enabled / active / waiting;
- all seven sources GREEN;
- PRD v1.5.1 Browser invariant preserved: no VPS Browser runtime and no SignalForge→Mac remote invocation;
- no OCR/PDF production capability introduced.

Evidence: `docs/verification/S08A-SOURCE-ONBOARDING-2026-09-04.md`.

### S12 IRD Business Tax Announcements Onboarding — PASS

- PR #28 CI PASS and squash-merged;
- exact SHA `d5222d00e81692ae4f4b8ee3d0a3d7ad70618237` deployed to Bangkok only;
- immediate rollback is `cb5291fdfcc13a678f63b53072e39089f8c27258`;
- pre-deploy state frozen at canonical `83`, signals `11`, scheduler runs `216`, Worker Runs `455`;
- first baseline created 9 `REGULATORY_NOTICE` canonical items and zero customer signals;
- baseline metrics: `items_parsed=9`, `tenders_parsed=0`, `details_attempted=9`, `details_succeeded=9`;
- S12 categories persisted as TAX_REGISTRATION=3, TAX_PAYMENT=2, TAX_FILING=2, TAX_EXEMPTION=2;
- requests/attempts/evidence/processing=`15/15/15/15`, zero pending discovery items and zero PDF requested URLs;
- S12 parse health GREEN (`9/9`);
- Worker cardinality/correlation verified (`455 -> 456`);
- Bangkok + Beijing Worker doctors PASS;
- Beijing remains strict zero-footprint and rejects `signalforge-refresh S12`;
- timer resume wrapper changed Worker Runs `456 -> 457` and processed due S13/S20/S21/S22, all `SUCCESS`, `changed=0`, `signals=0`;
- timer restored enabled / active / waiting;
- all eight sources GREEN;
- S04 Trade Portal remains deferred for canonical onboarding pending cross-source issuer-resolution/equivalence/dedup;
- PRD v1.5.1 Browser invariant preserved: no VPS Browser runtime and no SignalForge→Mac remote invocation;
- no PDF/OCR production capability introduced.

Evidence: `docs/verification/S12-SOURCE-ONBOARDING-2026-09-04.md`.

### S10 DICA Company and Investment Announcements Onboarding — PASS

- PR #30 CI PASS and squash-merged;
- exact SHA `3f31b937cc8dbe2941e85b1f810f2bd8a9b811fb` deployed to Bangkok only;
- immediate rollback is `d5222d00e81692ae4f4b8ee3d0a3d7ad70618237`;
- pre-deploy state frozen at canonical `92`, signals `11`, scheduler runs `228`, acquisition lifecycle `315/315/315/315`, Worker Runs `462`;
- first baseline created 12 `REGULATORY_NOTICE` canonical items and zero customer signals;
- categories persisted as COMPANY_STRIKE_OFF_BATCH=9, COMPANY_COMPLIANCE_NOTICE=1, INVESTMENT_TAX_INCENTIVE=1, INVESTMENT_CAPITAL_CURRENCY=1;
- baseline metrics: `items_parsed=12`, `tenders_parsed=0`, parse-health sample `details_attempted=4`, `details_succeeded=4`;
- canonical identity is stable WordPress post ID (`dica-notice:<post_id>`), not post ID + publication date;
- requests/attempts/evidence/processing=`13/13/13/13`, zero pending discovery items and zero PDF requested URLs;
- S10 parse health GREEN (`4/4`);
- Worker cardinality/correlation verified (`462 -> 463`);
- Bangkok + Beijing Worker doctors PASS;
- Beijing remains strict zero-footprint and rejects `signalforge-refresh S10`;
- timer resume wrapper changed Worker Runs `463 -> 464` and processed due S12 only, `SUCCESS`, `changed=0`, `signals=0`;
- timer restored enabled / active / waiting;
- all nine sources GREEN;
- PDF value gate is `TRIGGERED`, but production extraction/runtime packaging remains `DEFERRED_ZERO_DEPENDENCY`;
- PRD v1.5.1 Browser invariant preserved: no VPS Browser runtime and no SignalForge→Mac remote invocation;
- no pypdf/pdftotext/OCR dependency introduced.

Evidence: `docs/verification/S10-SOURCE-ONBOARDING-2026-09-04.md`.

### S25 MONPIFER Ministry Tenders Onboarding — PASS

- PR #32 CI PASS and squash-merged;
- exact production application SHA `930c94641b0699072350dcea9344aa55e930e169` deployed to Bangkok only;
- immediate rollback is `3f31b937cc8dbe2941e85b1f810f2bd8a9b811fb`;
- frozen pre-deploy nine-source state: canonical `104`, signals `11`, scheduler runs `315`, acquisition lifecycle `430/430/430/430`, failed `0`, recovery backlog `0`;
- deployment itself changed no business counts and left S25 at canonical/signals `0/0`;
- first reviewed S25 baseline created 10 `TENDER` canonical items and zero customer signals;
- baseline metrics: `items_parsed=10`, `tenders_parsed=10`, `details_attempted=0`, `details_succeeded=0`;
- exactly one S25 request/attempt/evidence/processing lifecycle persisted; requested URL was only `https://www.monpifer.gov.mm/my/ministry-tenders`; PDF requested URL count remained zero;
- S25 canonical identity uses the issuer-owned Drupal article alias (`monpifer:<article_alias>`), while the hidden numeric Drupal node ID is intentionally not fetched per row in P0;
- visible `Last Date` text is authoritative where the issuer page's hidden machine `datetime` disagrees;
- S25 parse health GREEN from `BUSINESS_PROCESSING` (`1/1`);
- manual baseline Worker Run `signalforge-20260904T125653Z-f810ed17` correlates exactly to the S25 scheduler row;
- the Worker count transition around rollout is causally separated: `508` observed before the final pre-pause timer tick, `509` normal timer wrapper at `12:55:10Z`, `510` reviewed manual S25 baseline; therefore the manual refresh added exactly one Worker Run;
- Bangkok + Beijing Worker doctors PASS;
- Beijing `/srv/signalforge` remains absent and `signalforge-refresh S25` returns `126 / DENY: SignalForge is Bangkok-only`;
- timer resume created one normal Worker wrapper `signalforge-20260904T130038Z-c53c154f` that processed seven due source jobs (S08A/S10/S12/S13/S20/S21/S22), all `SUCCESS`, `changed=0`, `signals=0`; S25 was not due and was not fetched again;
- final steady state: all ten sources GREEN, canonical `114`, signals `11`, scheduler runs `323`, acquisition lifecycle `439/439/439/439`, failed `0`, recovery backlog `0`, Worker SignalForge Runs `511`;
- timer restored enabled / active / waiting;
- `browser_production_approved=false` remains frozen;
- no schema migration, YCDC identity/locator contract, PDF extraction, OCR, Browser or remote Provider capability was introduced.

Evidence: `docs/verification/S25-SOURCE-ONBOARDING-2026-09-04.md`.

### S26 DOMS Medical Procurement Opportunities Onboarding — PASS

- PR #34 CI PASS and squash-merged;
- exact production application SHA `ae894d092f97843280c92228d6b43eda3bf0336f` deployed to Bangkok only;
- immediate rollback is `930c94641b0699072350dcea9344aa55e930e169`;
- frozen pre-deploy ten-source state: canonical `114`, signals `11`, scheduler runs `358`, acquisition lifecycle `480/480/479/479`, failed `1`, recovery backlog `0`, Worker SignalForge Runs `530`;
- the one pre-existing failed run was an S10 DICA `CONNECT_TIMEOUT` at `14:05:13Z`; S10 recovered at `14:15Z` and remained GREEN, so it is historical fail-closed evidence rather than an S26 rollout failure;
- deployment itself changed no business/acquisition counts and left S26 at canonical/signals `0/0` before baseline;
- first reviewed S26 baseline selected 2 opportunity-origin `TENDER` canonical items and zero customer signals;
- baseline metrics: `items_parsed=2`, `tenders_parsed=2`, `details_attempted=2`, `details_succeeded=2`, `changed=2`;
- S26 acquisition lifecycle is exactly `3/3/3/3`: one category HTML + two selected detail HTML pages; PDF requested URL count is zero;
- production canonical identities are `doms:12634` (`7DMS/2026-2027(L)`) and `doms:12491` (CT/MRI Preventive Maintenance); both deadlines remain unknown/null because issuer HTML does not supply reliable closing evidence;
- award/result, Envelope, opening/evaluation and scrutiny-meeting posts remain fail-closed excluded from the opportunity slice;
- manual baseline Worker Run `signalforge-20260904T144640Z-e5ee0dce` correlates exactly to the S26 scheduler row; Worker Runs `530 -> 531`;
- Bangkok + Beijing `workerctl doctor` PASS;
- Beijing `/srv/signalforge` remains absent and installed dispatcher returns `126 / DENY: SignalForge is Bangkok-only` for `signalforge-refresh S26`;
- timer resume created one normal Worker wrapper `signalforge-20260904T145148Z-f0f1b9e9` that processed eight due source jobs (S08A/S10/S12/S13/S20/S21/S22/S25), all `SUCCESS`, `changed=0`, `signals=0`; S26 was not fetched again;
- final steady state: all eleven sources GREEN, canonical `116`, signals `11`, scheduler runs `367`, acquisition lifecycle `495/495/494/494`, failed `1` (pre-existing recovered S10 timeout), recovery backlog `0`, Worker SignalForge Runs `532`;
- timer restored enabled / active / waiting; run-due service inactive;
- `browser_production_approved=false` remains frozen;
- no JSON-primary contract, schema migration, PDF extraction, OCR, Browser, remote Provider, Worker-runtime or Control-Plane capability was introduced.

Evidence: `docs/verification/S26-SOURCE-ONBOARDING-2026-09-04.md`.

### S28 Department of Fisheries Open Tenders Onboarding — PASS

- PR #38 CI PASS and squash-merged;
- exact production application SHA `7413a9da60a1b0c3bf82ac0b30f00fe625ca75a2` deployed to Bangkok only;
- immediate rollback is the already-live Mac-provider projection release `0a3e6156f2635fd9509738d3b6c0aa1d073f6c03`;
- before pause the live provider boundary was `production_enabled=false`, `invocation_mode=manual_or_future_contract`, `remote_invocation=false`, `browser_production_approved=false`;
- frozen pre-deploy eleven-source state: canonical `116`, signals `11`, scheduler runs `399`, acquisition lifecycle `533/533/532/532`, failed `1` (pre-existing recovered S10 timeout), recovery backlog `0`, Worker SignalForge Runs `549`;
- deployment itself changed no business/acquisition counts and left S28 at canonical/signals `0/0` before baseline;
- first reviewed S28 baseline created 8 listing-complete `TENDER` canonical items and zero customer signals;
- baseline metrics: `items_parsed=8`, `tenders_parsed=8`, `details_attempted=0`, `details_succeeded=0`, `changed=8`;
- S28 lifecycle is exactly `1/1/1/1`: only `https://www.dof.gov.mm/index.php/my/tender` was requested; detail/PDF requested URL count is zero;
- canonical identity uses issuer tender aliases (`dof:<alias>`); publication/sale/deadline fields preserve separate issuer evidence, including historical inconsistencies rather than heuristically rewriting them;
- S28 parse health GREEN from `BUSINESS_PROCESSING` (`1/1`);
- manual baseline Worker Run `signalforge-20260904T162016Z-e786baa0` correlates exactly to the S28 scheduler row; Worker Runs `549 -> 550`;
- Bangkok + Beijing `workerctl doctor` PASS;
- Beijing `/srv/signalforge` remains absent and installed dispatcher returns `126 / DENY: SignalForge is Bangkok-only` for `signalforge-refresh S28`;
- timer resume created one normal Worker wrapper `signalforge-20260904T162128Z-eb642231` that processed four due source jobs (S13/S20/S21/S22), all `SUCCESS`, `changed=0`, `signals=0`; S28 was not fetched again;
- final steady state: all twelve sources GREEN, canonical `124`, signals `11`, scheduler runs `404`, acquisition lifecycle `538/538/537/537`, failed `1` (pre-existing recovered S10 timeout), recovery backlog `0`, Worker SignalForge Runs `551`;
- timer restored enabled / active / waiting; run-due service inactive;
- Mac provider remains locked and `browser_production_approved=false` remains frozen;
- no schema migration, PDF/OCR runtime, Browser, JSON-primary target, remote Provider invocation, Worker-runtime or Control-Plane capability was introduced by S28.

Evidence: `docs/verification/S28-SOURCE-ONBOARDING-2026-09-04.md`.

### Mac/Bangkok Source Network Re-Audit — PASS / NO ONBOARDING CHANGE

- read-only live re-audit compared Mac Browser Plane direct C0 observations with Bangkok production-network strict-TLS behavior;
- control sources remain healthy from Bangkok: MPT S13 `HTTP 200 / ssl_verify_result=0 / 80,226 bytes`; Commerce S05A `HTTP 200 / ssl_verify_result=0 / 108,222 bytes`;
- MPA S15A/S15B remains environment-split: Mac direct C0 GREEN, Bangkok strict-TLS RED with `curl 60 / ssl_verify_result=20 / unable to get local issuer certificate`;
- Ministry of Border Affairs Tender is registered as deferred candidate S27: Mac direct C0 GREEN with deterministic `?page=N` pagination, Bangkok strict-TLS RED with the same curl-60 issuer-chain failure;
- these failures are classified as provider/environment-specific `TLS_FAILURE`, not `JS_RENDER_REQUIRED`;
- no `-k`/`--insecure`, CA-ignore, Browser escalation, VPS Playwright, or SignalForge→Mac remote invocation was introduced;
- S13/S05A remain ACTIVE Direct HTTP; S15A/S15B remain deferred; S27 is deferred only; S04 Trade Portal remains deferred for issuer-resolution/dedup rather than network reasons;
- `browser_production_approved=false` and Mac Provider `production_enabled=false` remain frozen.

Evidence: `docs/verification/MAC-BKK-SOURCE-NETWORK-REAUDIT-2026-09-04.md`.

### Mac Browser Provider Capability Projection — PASS

- `registry/Source-Registry-v1.yaml` now carries a machine-readable `providers.mac-mm-01` projection;
- `Registry.load()` fail-closes if the provider identity, direct-only network boundary, authorized C0/C1/C2 capabilities, or disabled C3/remote-invocation boundary drifts;
- Mac Browser Plane exposes its local authoritative manifest through `browserctl capabilities`;
- SignalForge projection remains descriptive/decision-support only: `production_enabled=false`, `invocation_mode=manual_or_future_contract`, no RPC/API/SSH invocation path added;
- active source execution remains Bangkok Direct HTTP and no existing source routing changed.

### Manual Provider Bridge v0 — PRODUCTION EVIDENCE-ONLY PASS

- bridge scope remains intentionally narrow: `mac-mm-01`, S15A only, direct C0 fetch only, evidence-only import;
- `signalforge provider-request S15A` emits a browserctl-compatible request with explicit `signalforge_job_id`, `acquisition_request_id`, `acquisition_attempt_id`, and `provider_request_id` correlation;
- installed Mac Browser Plane consumed the real S15A request successfully: Browser Job `c082bb94-e001-42ba-adeb-564a7fa40878`, HTTP 200, 252,512-byte HTML, SHA-256 `c016d4efcae50f271e5e6860e1567650ee3d215c4ef7d9d31bd029ed4a0ec810`;
- local isolated import passed first, then exact main release `d1f6d1773390767e73747df75e81383e4997f053` was deployed over the already-live S28 release `7413a9da60a1b0c3bf82ac0b30f00fe625ca75a2`;
- production `provider-import` wrote exactly one S15A scheduler/request/attempt/evidence/processing lifecycle, with `provider_id=mac-mm-01`, `execution_scope=MAC_LOCAL_MANUAL_BRIDGE`, `fetch_method=C0_FETCH`, processing status `EVIDENCE_ONLY` and parser/normalizer/canonicalizer all `none`;
- S15A canonical items/signals remain exactly `0/0`; overall canonical/signals remained `124/11` immediately after import;
- repeated production import returned `ALREADY_IMPORTED` and created no duplicates;
- production evidence permissions verified: provider directory `0700`, request/result JSON `0600`, raw HTML `0640`, all owned by `signalforge:signalforge`;
- post-import SignalForge remained `PASS/GREEN`, recovery backlog `0`, timer `enabled/active`, `browser_production_approved=false`;
- SHA/content-type/request-contract tampering fails closed;
- `provider-request` / `provider-import` remain absent from the VPS Worker verb manifest, so this still does not create unattended SignalForge→Mac invocation;
- no schema migration, no new daemon/API/queue, no TLS bypass, no S15A source onboarding, and no customer signal creation were introduced.

Evidence/runbook: `docs/MANUAL-PROVIDER-BRIDGE-v0.md`.

### S15A MPA Parser Preview — PASS / PRODUCTION ONBOARDING DEFERRED

- real Manual Provider Bridge listing evidence parses deterministically into all `181` MPA listing rows without Browser DOM execution;
- title-only classification is explicitly provisional: `152` provisional `TENDER`, `29` provisional `AUCTION_NOTICE`, `0` provisional unclassified after disposal/sale semantics were added;
- a 30-record evenly distributed human review across 2021–2026 found the revised title-level classification consistent with visible title semantics, but title text is not authoritative enough for final `item_kind`;
- critical counterexample: `Open Tender Invitation for three Tugs` looks like procurement from the listing title, while the linked official PDF states the three tugs will be auctioned through an open tender system; listing-only canonicalization is therefore rejected;
- six live detail probes across 2022–2026 returned HTTP 200 and stable WordPress shortlink IDs (`38289`, `37867`, `37745`, `35819`, `34155`, `2392`), supporting future canonical identity `mpa:<wordpress_post_id>` rather than slug identity;
- four representative detail pages each exposed exactly one issuer-original PDF iframe; the detail HTML is principally an identity + PDF locator layer;
- all four sampled PDFs were fetched through installed Mac Browser Plane C0 with strict TLS and were text-native enough in the audit to expose commercially useful semantics such as procurement/disposal classification, deadline, scope, tender number and service period;
- the initial parser preview used Mac-local `pypdf` only; the follow-on reviewed slice now promotes an exact `pypdf==6.16.2` runtime dependency in a per-release SignalForge venv without activating S15A;
- preview implementation remains read-only (`signalforge mpa-preview --html ...`, `signalforge mpa-pdf-preview --pdf ...`), bounded, absent from the VPS Worker verb manifest, and writes no DB/canonical/signal state;
- S15A remains deferred and Mac provider remains `production_enabled=false` / `remote_invocation=false`.

Evidence: `docs/verification/S15A-MPA-PARSER-PREVIEW-2026-09-04.md`.

### S15A PDF Supplementary Slice — LIVE RUNTIME PACKAGING PASS / ACTIVATION DEFERRED

- exact runtime dependency: `pypdf==6.16.2`;
- Bangkok preflight proved `/usr/bin/python3 -m venv` bootstraps pip even though system Python itself has no `pypdf`/pip module;
- deployment now builds `/srv/signalforge/venvs/<release>` before switching `active`, and release-local `bin/signalforge` uses `.venv/bin/python` when present;
- dependency install/version verification fails deployment before active-release switch; previous release + venv remain the rollback target;
- deterministic PDF parser limits: 10 MiB, 20 pages, 100k extracted chars; encrypted/non-text/oversized/ambiguous inputs fail closed;
- final PDF classification prioritizes disposal/auction semantics over generic tender/procurement words; generic `Open Tender` without decisive business semantics returns `REVIEW_REQUIRED`;
- deadline is emitted only from uniquely supported date+time evidence; explicit MPA reference numbers are normalized without inference;
- four real issuer PDFs passed under exact Python 3.13 + `pypdf 6.16.2`: Three Tugs=`AUCTION_NOTICE` / `2026-06-25T13:00`, Marine Paint=`TENDER` / `2026-06-04T13:00`, Port EDI=`TENDER` / `2026-05-21T13:00` / `MPA-IR&HRD/01-2026`, Battery=`TENDER` / `2025-05-29T13:00`;
- full implementation suite passed before merge; S15A still has no active adapter/scheduler/canonical path;
- Bangkok is now live on exact release `f4a3dfd0ae77797b8fd82911fb908097a1dc97d8` with release-local venv `/srv/signalforge/venvs/f4a3dfd0ae77797b8fd82911fb908097a1dc97d8`, Python `3.13.5`, `pypdf 6.16.2`; system Python still cannot import `pypdf`;
- previous release `d1f6d1773390767e73747df75e81383e4997f053` remains present and its `signalforge status` command passes, preserving immediate runtime rollback;
- fresh Mac Browser Plane C0 verification fetched `Three-Tug-Tender-Eng.pdf` as Browser Job `0e0e0062-7792-4f9b-a4b3-3a10b70597f7`, HTTP 200, 101,698 bytes, SHA-256 `9a664132a31c682d48d765c44e5b0d83c5e165bb1aebe9cc770b3f26ba30d046`;
- live Bangkok `mpa-pdf-preview` classified that artifact as `AUCTION_NOTICE`, basis `AUCTION_EN`, deadline `2026-06-25T13:00:00`, with no provider-import or source activation;
- S15A durable state remained exactly scheduler/request/attempt/evidence/processing `1/1/1/1/1`, canonical/signals `0/0` before and after preview; the existing lifecycle is the prior Manual Provider Bridge `EVIDENCE_ONLY` import;
- post-preview production remained PASS/GREEN, all twelve active sources GREEN, canonical/signals `124/11`, backlog `0`, timer enabled/active and `browser_production_approved=false`;
- Beijing `/srv/signalforge` remains absent and Beijing Worker doctor remains PASS;
- production PDF runtime packaging gate is therefore LIVE-VERIFIED, while S15A activation remains deferred pending an explicit decision on operator-driven manual acquisition vs a future separately reviewed remote Provider Invocation Contract.

Evidence: `docs/verification/S15A-MPA-PDF-SUPPLEMENTARY-2026-09-05.md`.

### S15A Manual P0 Phase A — PRODUCTION LIVE PASS / PHASE B AUTHORIZED

- fresh Mac C0 listing audit still parses 181 MPA rows; observed publication volume is low: 2 records in 30 days, 3 in 60/90 days, 13 in 180 days, 21 in 365 days;
- current evidence does not justify a Remote Provider Invocation Contract; operator-driven C0 remains the smaller operational design;
- Manual Provider Bridge now supports bounded S15A `LISTING`, `DETAIL` and `PDF` target roles while keeping `production_enabled=false`, `remote_invocation=false` and `EVIDENCE_ONLY` imports;
- LISTING remains the fixed MPA tender hub; DETAIL is restricted to issuer `/announcements/.../`; PDF is restricted to issuer `/wp-content/uploads/...pdf`; wrong host/path/query/fragment/traversal/content-type contracts fail closed;
- legacy listing provider requests without `target_role` remain backward-compatible as `LISTING`;
- durable provider artifact loading requires unique request correlation, `EVIDENCE_ONLY` provenance, current request-contract validity and exact stored SHA/byte verification;
- read-only `mpa-provider-bundle-preview` joins imported listing/detail/PDF evidence and validates `listing -> detail -> issuer PDF` relationship before deriving stable `mpa:<wordpress_post_id>` identity and deterministic PDF business fields;
- Phase A still creates zero canonical items and zero customer signals; `mpa-provider-bundle-preview` is not a Worker verb;
- targeted MPA/provider tests `24/24 PASS`; full repository test discovery `91/91 PASS`;
- exact merged application SHA `bd4e217d0b036a436290462ce9f1393defd00d6c` is deployed on Bangkok; rollback remains `f4a3dfd0ae77797b8fd82911fb908097a1dc97d8`;
- deployment caused zero business-count change: canonical/signals stayed `124/11`, all twelve active sources stayed GREEN and S15A stayed `0/0`;
- existing listing evidence `74a9b732-...` was reused; real bounded DETAIL `88f20980-...` and PDF `9d3aa060-...` provider requests were executed manually through Mac C0 and imported as `EVIDENCE_ONLY`;
- detail Browser Job `0a65f464-...` returned HTTP 200 / 100,820 bytes / SHA `6e90328a...`; PDF Browser Job `31a8e346-...` returned HTTP 200 / 101,698 bytes / SHA `9a664132...`;
- live bundle preview returned `READY_FOR_MANUAL_COMMIT`, `mpa:37867`, final `AUCTION_NOTICE`, deadline `2026-06-25T13:00:00+06:30`, while listing provisional kind was `TENDER`;
- S15A durable state is now exactly `3/3/3/3/3`, all three processing records `EVIDENCE_ONLY`, canonical/signals `0/0`; provider evidence permissions remain `0700/0600/0600/0640`;
- manual Mac evidence added no VPS Worker Runs; Worker Runs stayed `583` through the paused window; both Worker doctors PASS and Beijing remains SignalForge zero-footprint;
- timer was restored enabled/active; one normal due cycle completed, Worker Runs became `584`, all twelve sources remain GREEN, global canonical/signals remain `124/11`, backlog `0`;
- Manual P0 Phase A is therefore PRODUCTION LIVE PASS. Phase B manual canonical commit is now technically eligible for design but remains a separate explicit authorization boundary.

Evidence: `docs/verification/S15A-MPA-MANUAL-P0-PHASE-A-2026-09-05.md`.

### S15A Manual P0 Phase B — PRODUCTION LIVE PASS

- explicit user authorization was received to continue the recommended Manual P0 onboarding after Phase A production live verification;
- operator-only `mpa-provider-bundle-commit` reuses the three durable LISTING/DETAIL/PDF provider artifacts and revalidates the same evidence relationship before any write;
- canonical identity remains `mpa:<wordpress_post_id>` and authoritative canonical evidence digest is the issuer PDF SHA-256;
- first/manual baseline commits default to zero customer signal; `--emit-signal` is required explicitly for NEW/UPDATED emission when content materially changes;
- one PDF evidence artifact can be committed once per `mpa-manual-v1` canonicalizer version; repeat returns `ALREADY_COMMITTED` without a second processing row or signal;
- provider-import rows remain `EVIDENCE_ONLY`; canonical commit writes a separate `SUCCESS` processing row with parser `mpa-pdf-v1`, normalizer/canonicalizer `mpa-manual-v1`;
- `REVIEW_REQUIRED` bundles fail closed and the commit command is absent from the VPS Worker verb manifest;
- targeted Phase B tests 4/4 PASS; full repository suite 95/95 PASS; PR #49 and merged main verify PASS;
- exact merged release `0ff38409a5c0f2a312a79c912e7e411b21cdccd4` is live on Bangkok; previous `bd4e217d0b036a436290462ce9f1393defd00d6c` remains the application rollback target;
- installed-release preview of Phase A bundle `74a9b732-... / 88f20980-... / 9d3aa060-...` returned `READY_FOR_MANUAL_COMMIT`, stable `mpa:37867`, final `AUCTION_NOTICE`, deadline `2026-06-25T13:00:00+06:30`;
- the first production commit omitted `--emit-signal` and returned `COMMITTED / CREATED`, processing `61dde280-ec98-45f0-8b78-59ed1b475921`; immediate repeat returned `ALREADY_COMMITTED` with the same processing ID;
- S15A durable state after baseline is scheduler/request/attempt/evidence/processing `4/4/4/4/5`, canonical/signals `1/0`; exactly one `mpa-manual-v1` SUCCESS processing row exists and SQLite `quick_check=ok`;
- the fourth evidence lifecycle is an immutable duplicate Three Tugs PDF manual verification with the same issuer SHA; the canonical baseline uses original Phase A PDF provider request `9d3aa060-...` and no audit evidence was deleted;
- global canonical/signals changed only `124/11 -> 125/11`; SignalForge remained PASS/GREEN, all 12 automated sources GREEN, backlog 0, timer enabled/active;
- S15A remains outside automated scheduling; Mac provider remains `production_enabled=false` / `remote_invocation=false` and `browser_production_approved=false`;
- Bangkok and Beijing Worker doctors PASS with documented `WORKER_REPO_ROOT`; Beijing remains SignalForge zero-footprint;
- Phase B is therefore PRODUCTION LIVE PASS. Operate MPA as a low-frequency manual canonical source; do not build unattended remote invocation until repeated real use proves material operator burden.

Evidence: `docs/verification/S15A-MPA-MANUAL-P0-PHASE-B-2026-09-05.md`.

### S15A first real operational tender run — PASS / NO CURRENT ACTIONABLE SIGNAL

- fresh current MPA listing audit confirmed the newest 2026-08-21 / 08-13 / 07-21 records are auction/disposal; the 2026-06-02 Three Tugs record remains PDF-proven `AUCTION_NOTICE`;
- the newest actual procurement candidate is the 2026-05-29 Port EDI Mini Data Center Infrastructure Refreshment Phase II (1 Lot) tender;
- fresh LISTING / DETAIL / PDF Mac C0 evidence imported successfully under provider requests `7ebc2c88-... / 8bbcd4f8-... / bd1a016c-...`; stable identity is `mpa:37841` and issuer reference is `MPA-IR&HRD/03-2026`;
- the first parser pass failed closed as `REVIEW_REQUIRED` because Burmese service text was fragmented by PDF extraction; real issuer evidence justified one narrow deterministic addition, `infrastructure refreshment -> INFRA_REFRESH_EN -> TENDER`, with disposal semantics still higher priority;
- PR #52 and merged main CI PASS; full suite 96/96 PASS; exact release `6ec3e74b832b5e0033ac571d451cd41f0b69de77` is live on Bangkok with `0ff38409...` retained as rollback;
- installed-release bundle preview returned `READY_FOR_MANUAL_COMMIT`, `mpa:37841`, `TENDER`, deadline `2026-06-18T13:00:00+06:30`;
- because the deadline was already expired on 2026-09-05, the operator committed the item without `--emit-signal`; processing `58c4d3c8-...` created the canonical item and zero signals, and repeat returned `ALREADY_COMMITTED`;
- post-run global canonical/signals are `126/11`; S15A canonical/signals are `2/0`; all 12 automated sources remain GREEN, timer enabled/active and SQLite `quick_check=ok`;
- operational conclusion: current MPA has no actionable procurement opportunity as of 2026-09-05. Do not emit a synthetic test signal; wait for the first genuinely new, still-open MPA procurement item.

Evidence: `docs/verification/S15A-MPA-FIRST-OPERATIONAL-TENDER-2026-09-05.md`.

### S29 DWIR Waterway and River Works — PRODUCTION / GREEN

- exact production application release `e62410eb1cc7894f6a5f3305dcf2eab0d99b2bb8`; previous application-code rollback target `6ec3e74b832b5e0033ac571d451cd41f0b69de77`;
- issuer-original `ACTIVE_PRIMARY` source uses lightweight `https://www.dwir.gov.mm/` homepage discovery rather than the multi-megabyte category/RSS surfaces;
- stable canonical identity is `dwir:<joomla_article_id>`; current baseline canonical items are `dwir:289`, `dwir:296`, `dwir:297`, `dwir:298`;
- first reviewed production baseline: `MANUAL / baseline=1 / SUCCESS`, `items=4`, `tenders=4`, `details=4/4`, `changed=4`, `signals=0`;
- S29 persistence after baseline is canonical/signals `4/0` and request/attempt/evidence/processing `5/5/5/5`; EvidenceEnvelopes are exactly one homepage + four issuer detail HTML requests, with zero PDF/image acquisition;
- baseline Worker correlation is exactly `signalforge-20260904T223221Z-3f413c30 / SUCCESS`;
- rollout timer was inadvertently left disabled after baseline. On 2026-09-06 all automated sources were RED only from `SOURCE_FRESHNESS_LAG` (~32h); fetch/parse remained GREEN, `last_error=None`, `consecutive_failures=0`, backlog 0;
- Beijing Worker doctor PASS, `/srv/signalforge` absent, and installed dispatcher returns `126 / DENY: SignalForge is Bangkok-only` for S29 refresh; Bangkok Worker doctor PASS;
- timer resume created one reconciliation Worker Run `signalforge-20260906T064322Z-d58fd92b` covering all 13 overdue automated source jobs; every job returned `SUCCESS / changed=0 / signals=0`;
- final observed state: 13/13 automated sources GREEN, overall PASS/GREEN, canonical/signals `130/11`, scheduler `593`, acquisition request/attempt/evidence/processing `772/772/771/773`, backlog 0, Worker SignalForge Runs `625`, timer enabled/active, `browser_production_approved=false`;
- cumulative `failed_runs=1` remains the previously recovered S10 CONNECT_TIMEOUT and is not an S29 regression.

Evidence: `docs/verification/S29-DWIR-SOURCE-ONBOARDING-2026-09-05.md`.

### S30 MOFA Procurement Invitations — PRODUCTION / GREEN

- exact production application release `61d6984bf0efd05dddcac0791bba00cf741f3052`; previous application-code rollback target `e62410eb1cc7894f6a5f3305dcf2eab0d99b2bb8`;
- `ACTIVE_SELECTIVE` Direct-HTTP source uses the MOFA Announcement category and selected WordPress detail HTML; stable identity is `mofa:<wordpress_post_id>`;
- reviewed first production baseline: `MANUAL / baseline=1 / SUCCESS`, `items=2`, `tenders=2`, `details=2/2`, `changed=2`, `signals=0`; canonical items are `mofa:59800` (2026-09-04) and `mofa:56952` (2026-06-23), both with deadline `null`;
- persistence is canonical/signals `2/0` and request/attempt/evidence/processing `3/3/3/3`; all three EvidenceEnvelopes are HTML (category + 2 details), with zero PDF/JPG/PNG acquisition;
- baseline Worker correlation is exactly one `signalforge-20260907T031617Z-36a3d084 / SUCCESS`; Worker DB and SignalForge DB `quick_check=ok`;
- Bangkok and Beijing Worker doctors PASS; Beijing `/srv/signalforge` is absent and its dispatcher rejects `signalforge-refresh S30` with `126 / DENY: SignalForge is Bangkok-only`;
- Mac provider remains `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`, invocation mode `manual_or_future_contract`;
- timer resume created reconciliation Worker Run `signalforge-20260907T032122Z-3892216e` covering S13/S20/S21/S22, all `SUCCESS / changed=0 / signals=0`;
- final observed state: 14/14 automated sources GREEN, overall PASS/GREEN, canonical/signals `132/11`, scheduler `1207`, acquisition request/attempt/evidence/processing `1501/1501/1499/1501`, backlog 0, timer enabled/active, run-due inactive;
- cumulative `failed_runs=2` consists of recovered S10 and S28 read timeouts; S28 resumed SUCCESS about ten minutes after its 2026-09-06 timeout and remained healthy.

Evidence: `docs/verification/S30-MOFA-SOURCE-ONBOARDING-2026-09-06.md`.

### S31 MOEA Procurement Invitations — PRODUCTION / GREEN

- exact production application release `f751c8f13ae86740a227ba2cd00518d68cde2edc`; previous application-code rollback target `61d6984bf0efd05dddcac0791bba00cf741f3052`;
- `ACTIVE_SELECTIVE` Direct-HTTP listing-complete source uses the MOEA tender archive; business narrative is recovered from issuer CMS HTML comments while PDF links remain metadata-only;
- selection includes procurement invitation/call records, excludes tender award/result stages and clearly non-procurement lease/auction records; explicit deadlines are emitted only from an HTML-comment `နောက်ဆုံး` final-date marker;
- source-local stable-enough archive identity is `moea:<publication_date>:<sha256(date+normalized_title)[:16]>`; title correction can create a new identity because the issuer exposes no native row ID, while same identity + different attachment fails closed;
- reviewed first production baseline: `MANUAL / baseline=1 / SUCCESS`, `items=9`, `tenders=9`, `details=0`, `changed=9`, `signals=0`; newest selected record is 2026-07-27 with deadline `2026-08-07`;
- persistence after baseline is canonical/signals `9/0` and request/attempt/evidence/processing `1/1/1/1`; the single EvidenceEnvelope is `text/html` 90,396 bytes and PDF evidence count is zero;
- baseline Worker correlation is exactly one `signalforge-20260907T040008Z-4db411d6 / SUCCESS`; Worker DB and SignalForge DB `quick_check=ok`;
- Bangkok and Beijing Worker doctors PASS; Beijing `/srv/signalforge` remains absent and rejects `signalforge-refresh S31` with `126 / DENY: SignalForge is Bangkok-only`; Mac provider remains `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`;
- timer resume created reconciliation Worker Run `signalforge-20260907T040055Z-db7c468a` for S05A/S07/S08A/S10/S12/S25/S26/S28/S29; all nine returned `SUCCESS / changed=0 / signals=0`;
- final observed state: 15/15 automated sources GREEN, overall PASS/GREEN, canonical/signals `141/11`, scheduler `1235`, acquisition request/attempt/evidence/processing `1532/1532/1530/1532`, failed_runs 2 historical/recovered, backlog 0, timer enabled/active, run-due inactive.

Evidence: `docs/verification/S31-MOEA-SOURCE-ONBOARDING-2026-09-07.md`.

### S32 Myanma Timber Enterprise Procurement Invitations — PRODUCTION / GREEN

- exact production application release `2edaf3259d168344544f5a5cd09ab1d2c37fe563`; previous application-code rollback target `f751c8f13ae86740a227ba2cd00518d68cde2edc`;
- `ACTIVE_SELECTIVE` Direct-HTTP listing-complete source uses the MTE announcement archive and requires explicit buyer-side procurement semantics; timber/open-tender sale/auction events and ambiguous title-only open tenders are excluded;
- canonical identity is issuer-native Joomla article ID (`mte:<article_id>`); selected production baseline records are `mte:1600` (visible tender no. `၁/၂၆-၂၇`, transportation service procurement) and `mte:1415` (diesel procurement);
- publication date and deadline are deliberately `null`: archive HTML exposes neither trustworthy field and S32 does not infer them from collection time/URL slug or parse image supplements;
- reviewed first production baseline: `MANUAL / baseline=1 / SUCCESS`, `items=2`, `tenders=2`, `details=0`, `changed=2`, `signals=0`;
- persistence added exactly one request/attempt/evidence/processing lifecycle; sole EvidenceEnvelope is `text/html` 46,158 bytes, with zero detail/image acquisition;
- baseline Worker correlation is exactly one `signalforge-20260907T060955Z-b9a81d4d / SUCCESS`; SignalForge DB and Worker DB `quick_check=ok`;
- Bangkok and Beijing Worker doctors PASS; Beijing `/srv/signalforge` remains absent and rejects `signalforge-refresh S32` with `126 / DENY: SignalForge is Bangkok-only`; Mac provider remains `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`;
- pre-rollout cumulative `failed_runs=4` includes two new S29 DWIR failures (HTTP 522 at ~05:10Z and read timeout at ~05:20Z); S29 recovered at ~05:30Z and again ~06:05Z with `SUCCESS / changed=0 / signals=0`, so all four failures are historical/recovered and backlog is zero;
- timer resume was clean and created no run because no source was due at that instant; final state is 16/16 automated sources GREEN, canonical/signals `143/11`, scheduler `1301`, acquisition request/attempt/evidence/processing `1609/1609/1605/1607`, failed_runs 4 historical/recovered, backlog 0, timer enabled/active, run-due inactive.

Evidence: `docs/verification/S32-MTE-SOURCE-ONBOARDING-2026-09-07.md`.

### S33 Ministry of Cooperatives and Rural Development Tenders — PRODUCTION / GREEN

- exact production application release `a4d55bf4ad8cf1977b5e874fa9b652d880c2b2a7`; previous application-code rollback target `2edaf3259d168344544f5a5cd09ab1d2c37fe563`;
- `ACTIVE_SELECTIVE` one-fetch Direct-HTTP listing-complete source uses the structured MCRD tender board; each selected row provides title, explicit closing date, department and primary-document metadata; publication date remains `null`;
- source-local canonical identity is `mcrd:<closing_date>:<sha256(normalized_title|closing_date|department)[:16]>`; the primary document URL is deliberately excluded from identity and same event identity with a different primary document fails closed for re-audit;
- reviewed first production baseline: `MANUAL / baseline=1 / SUCCESS`, `items=5`, `tenders=5`, `details=0`, `changed=5`, `signals=0`; current newest row closes `2026-05-15`, so baseline suppression correctly emitted no signal;
- persistence added exactly one request/attempt/evidence/processing lifecycle; sole EvidenceEnvelope is `text/html` 52,527 bytes, with zero linked PDF/JPEG acquisition;
- baseline Worker correlation is exactly one `signalforge-20260907T064353Z-74f21b24 / SUCCESS`; SignalForge DB and Worker DB `quick_check=ok`;
- Bangkok and Beijing Worker doctors PASS; Beijing `/srv/signalforge` remains absent and rejects `signalforge-refresh S33` with `126 / DENY: SignalForge is Bangkok-only`; Mac provider remains `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`;
- fresh S23 Ministry of Construction re-audit found current actionable September 2026 tenders but Bangkok strict TLS fails with an expired issuer certificate, so S23 remains deferred with no certificate bypass;
- cumulative `failed_runs=4` remains the existing recovered S10/S28/S29 history; S33 added no failure and backlog is zero;
- timer resume was clean and created no scheduler run because nothing was due at that instant; final state is 17/17 automated sources GREEN, canonical/signals `148/11`, scheduler `1322`, acquisition request/attempt/evidence/processing `1635/1635/1631/1633`, failed_runs 4 historical/recovered, backlog 0, timer enabled/active/waiting, run-due inactive.

Evidence: `docs/verification/S33-MCRD-SOURCE-ONBOARDING-2026-09-07.md`.

### S16 YCDC Engineering Department (Building) — PRODUCTION / GREEN

- exact production application release `794e0190d1d878d92e9a0580a28b93b6c82dada0`; previous application-code rollback target `a4d55bf4ad8cf1977b5e874fa9b652d880c2b2a7`;
- previous S16 deferral is resolved for the Building department by stable issuer-original numeric archive `https://www.ycdc.gov.mm/frontend_engineering_building_detail/1`; generic randomized ciphertext tender locators are not used by production;
- `ACTIVE_SELECTIVE` one-fetch Direct-HTTP classifier keeps PPP/building implementation scope and excludes lease/concession, auction, sale and demolition-sale scope; exclusion is evaluated only on the scope paragraph to avoid false negatives from tender-form sale-date wording;
- source-local canonical identity is `ycdc-building:<deadline>:<sha256(explicit_deadline|normalized_scope_summary)[:16]>`; same identity + different normalized full block fails closed for re-audit;
- reviewed first production baseline: `MANUAL / baseline=1 / SUCCESS`, `items=5`, `tenders=5`, `details=0`, `changed=5`, `signals=0`; newest selected PPP/building event deadline is `2026-02-27`; the newer `2026-08-10` lease/concession event is correctly excluded;
- persistence added exactly one request/attempt/evidence/processing lifecycle; sole EvidenceEnvelope is `text/html` 60,673 bytes, with zero detail/attachment acquisition; publication dates remain `null`;
- baseline Worker correlation is exactly one `signalforge-20260907T091305Z-669065f6 / SUCCESS`; SignalForge DB and Worker DB `quick_check=ok`;
- Bangkok and Beijing Worker doctors PASS; Beijing `/srv/signalforge` remains absent and rejects `signalforge-refresh S16` with `126 / DENY: SignalForge is Bangkok-only`; Mac provider remains `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`;
- pre-rollout cumulative `failed_runs=5` includes a new S25 MONPIFER HTTP 522 at ~08:30Z that recovered at ~08:40Z with `SUCCESS / changed=0 / signals=0`; all five failures are historical/recovered and backlog is zero;
- timer resume was clean and created no scheduler run because nothing was due at that instant; final state is 18/18 automated sources GREEN, canonical/signals `153/11`, scheduler `1415`, acquisition request/attempt/evidence/processing `1747/1747/1742/1744`, failed_runs 5 historical/recovered, backlog 0, timer enabled/active, run-due inactive.

Evidence: `docs/verification/S16-YCDC-BUILDING-SOURCE-ACTIVATION-2026-09-07.md`.

### S34 Posts and Telecommunications Department Open Tenders — PRODUCTION / GREEN

- exact production application release `0f8237916b39daa1c2f85d8309e93ff3ced56238`; previous application-code rollback target `794e0190d1d878d92e9a0580a28b93b6c82dada0`;
- `ACTIVE_SELECTIVE` Direct-HTTP source uses the issuer PTD tender category plus selected detail HTML; opportunity-stage invitations are included and tender-winner/award/result stages are excluded;
- current canonical scope covers six telecom/ICT procurement shapes: earthquake RF-monitoring recovery equipment, RF monitoring spare parts, Bago monitoring-station equipment, monitoring-vehicle equipment, Nay Pyi Taw/Pathein construction, and All DNS / `.mm Root DNS` / second-level DNS operations and maintenance;
- canonical identity is `ptd:<publication_date>:<sha256(publication_date|normalized_scope_summary)[:16]>`; PTD opaque encoded detail locator stays transport/audit metadata, not business identity;
- publication date is explicit issuer HTML; deadline is deliberately `null` because deadline/rule information remains in linked PDF metadata that P0 does not fetch or parse;
- reviewed first production baseline: `MANUAL / baseline=1 / SUCCESS`, `items=6`, `tenders=6`, `details=6/6`, `changed=6`, `signals=0`;
- baseline added exactly seven HTML request/attempt/evidence/processing lifecycles (one 85,873-byte category + six detail pages), zero PDF evidence, and SignalForge DB `quick_check=ok`;
- baseline Worker correlation is exactly one `signalforge-20260907T102115Z-c639cb75 / SUCCESS`; Worker DB `quick_check=ok`;
- Bangkok and Beijing Worker doctors PASS; Beijing `/srv/signalforge` remains absent and rejects `signalforge-refresh S34` with `126 / DENY: SignalForge is Bangkok-only`; Mac provider remains `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`;
- cumulative `failed_runs=5` is unchanged and historical/recovered; S34 added no failure and backlog is zero;
- timer resume was clean and created no scheduler run because nothing was due at that instant; final state is 19/19 automated sources GREEN, canonical/signals `159/11`, scheduler `1457`, acquisition request/attempt/evidence/processing `1799/1799/1794/1796`, failed_runs 5 historical/recovered, backlog 0, timer enabled/active, run-due inactive;
- OAG remains deferred because current tender scope/deadline content is scan/JPG-only and requires a separately approved Burmese image/OCR capability.

Evidence: `docs/verification/S34-PTD-SOURCE-ONBOARDING-2026-09-07.md`.

## Frozen acquisition invariants

```text
Default active-source production path:
Source Acquisition Policy
-> AcquisitionRequest
-> AcquisitionAttempt
-> Local Direct HTTP adapter
-> EvidenceEnvelope
-> source-specific parser/normalizer/canonicalizer
-> ProcessingRecord
-> Canonical / Dedup / Signal

Controlled manual-provider evidence path:
approved deferred candidate
-> provider-request
-> operator transfer
-> Mac C0
-> operator transfer
-> provider-import
-> EvidenceEnvelope
-> ProcessingRecord(EVIDENCE_ONLY)
-> no Canonical / no Signal
```

Still frozen:

- `AcquisitionRequest != Worker Run`;
- `AcquisitionAttempt != Worker Run`;
- Worker DB has no SignalForge business/acquisition semantics;
- Direct HTTP remains default;
- no silent Browser escalation;
- TLS failure never becomes certificate bypass or automatic Browser success;
- no remote Provider transport, Redis/Celery, central scheduler or automatic cross-zone failover;
- Mac mini is the sole Browser Runtime host; SignalForge→Mac unattended production invocation remains disabled;
- Beijing remains Generic Worker only.

## Conditional future gates / superseded Browser path

- VPS Browser/Crawlee Gates O2/P/Q: `SUPERSEDED_BY_MAC_BROWSER_PLANE`; do not implement on Bangkok/Beijing. A real JS-render-required source may only create a Mac Browser Provider requirement, which stays blocked while `production_enabled=false`.
- Webhook Gate T: only after a real webhook use case and ingress/auth/dedup contract exist.
- Dedicated identity Gate V: before the first real dedicated Generic Job retirement.
- Remote Provider ADR: only after a real source proves Bangkok local acquisition insufficient.
- Mac Browser Provider Invocation Contract: only after repeated manual-provider evidence proves that a real high-value source materially requires the Mac execution environment and the operational burden justifies automation; must be a separate reviewed cross-host contract, not ad-hoc SSH/HTTP/CDP.
- Browserless ADR: only after multiple real browser consumers create shared lifecycle/queue/session pain.
- PDF supplementary adapter: only when issuer HTML lacks business-critical fields whose extraction materially improves the commercial signal or when PDF semantics are required to prevent business misclassification.

S20, S22, S05A, S07, S08A, S12, S25, S26 and S28 triggered none of these capability gates. S10 remains the first source to trigger the PDF supplementary **value** gate because the official PDFs contain company-level and policy-level business facts absent from HTML. S15A separately triggers a PDF supplementary **classification + business-fields** gate: listing-only semantics can misclassify asset-disposal auctions as procurement tenders and omit deadline/scope/reference facts. S15A deterministic PDF runtime packaging and Manual P0 evidence-bundle processing are production live-verified; explicit operator-only canonical commit is now authorized/implemented, while unattended provider invocation remains deferred. S10 enrichment is still a separate future production extraction decision. Fresh municipal audits now split the result cleanly: S16 YCDC Building closed its discovery-identity vs ephemeral transport-locator gate through a stable numeric issuer archive and is production live-verified, while the generic randomized ciphertext YCDC transport remains unused; S17 MCDC still requires Burmese image/OCR for current scan-only tender PDFs; S18 NPTDC still requires mixed-board segmentation plus image/OCR. None of the remaining gates should be bypassed merely to increase source count.

## Next

1. operate S05A + S07 + S08A + S10 + S12 + S13 + S16 + S20 + S21 + S22 + S25 + S26 + S28 + S29 + S30 + S31 + S32 + S33 + S34 and collect real acquisition/source history;
2. choose the next source by business value plus current endpoint quality, not source-ID order or a target source count;
3. prefer another issuer-original Direct-HTTP source that fits the existing acquisition engine before introducing schema/OCR/Browser capability; S32 proved MTE event-level procurement can remain HTML-only, S33 resolved MCRD weak row identity with a bounded event fingerprint + collision guard, and S16 YCDC Building proved a stable department archive can supersede ephemeral ciphertext locators; S34 PTD proves high-value telecom/ICT procurement can stay HTML-event-level with PDF metadata-only deadlines; OAG is currently image-only for business fields, fresh S23 Ministry of Construction still fails Bangkok strict TLS because the issuer certificate is expired, and S27 MOBA still fails strict TLS; Ministry of Industry (Bangkok DNS), Ministry of Energy (embedded PDF), Ministry of Education (image notice) and Tourism (JPG notice) remain deferred under current capabilities;
4. S01 National Portal stays discovery-aggregator-only until issuer-resolution/equivalence/dedup exists; S04 Trade Portal remains deferred for the same cross-source contract reason;
5. preserve the remaining municipal gates: S16 Building is now production through the stable numeric archive and should not regress to randomized ciphertext locators; S17 still requires Burmese OCR and S18 still requires classifier + OCR; do not force those remaining capabilities into P0;
6. keep S10 PDF supplementary extraction as a separate reviewed runtime-packaging slice and promote it only when its incremental commercial value justifies the dependency;
7. S15A Manual P0 is production live-verified through real operation with two zero-signal canonical items (`mpa:37867` auction baseline and expired procurement `mpa:37841`); current listing has no actionable procurement signal, so keep low-frequency manual operation and do not build unattended remote invocation unless repeated real use proves material operational burden;
8. keep S08A tender-award/result content as a separate future `PROCUREMENT_RESULT` decision;
9. periodically recheck whether MOEP advertised PDFs become retrievable; only then consider a supplementary PDF parser gate;
10. keep Direct HTTP first; if a source truly requires Browser, route the requirement only to Mac Browser Plane and block unattended production until a separate Provider Invocation Contract is live-verified;
11. run the next cross-repo consistency review by 2026-12-03 or an earlier contract-change trigger.
