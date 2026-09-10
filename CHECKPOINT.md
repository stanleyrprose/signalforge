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

### S35 Department of Advanced Science and Technology Tenders — PRODUCTION / GREEN

- exact production application release `5ad60eabc2a86235db413c37c49e4bbe91378f95`; previous application-code rollback target `0f8237916b39daa1c2f85d8309e93ff3ced56238`;
- Direct-HTTP issuer archive `https://www.dast.gov.mm/category/tender/` exposes stable native WordPress post IDs; stale `.edu.mm` post/attachment locators are rewritten deterministically to the same issuer's working `.gov.mm` mirror rather than used as a fallback dependency;
- canonical identity is `dast:<wordpress_post_id>`; publication date and business scope come from issuer HTML, and deadlines are emitted only from explicit HTML submission-language dates; official PDF paths are metadata-only;
- production baseline: `MANUAL / baseline=1 / SUCCESS`, `items=6`, `tenders=6`, `details=6/6`, `changed=6`, `signals=0`; deadlines are `2631=2026-08-14`, `2625=2026-07-21`, `2595=2026-05-22`, and `2578/2582/2571=2026-05-07`;
- baseline added exactly seven HTML request/attempt/evidence/processing lifecycles (one archive + six details), zero PDF evidence; SignalForge DB `quick_check=ok`;
- baseline Worker correlation is exactly one `signalforge-20260907T122630Z-ce3da99b / SUCCESS`; Worker DB `quick_check=ok`;
- Bangkok and Beijing Worker doctors PASS; Beijing `/srv/signalforge` remains absent and rejects `signalforge-refresh S35` with `126 / DENY: SignalForge is Bangkok-only`; Mac provider remains `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`;
- rollout waited for an already-activating natural `run-due` invocation to finish before disabling the timer; frozen pre-deploy state was 19/19 GREEN with scheduler/acquisition `1547 / 1901`; deployment itself changed no business/acquisition counts;
- cumulative `failed_runs=5` is unchanged/historical/recovered, backlog 0; timer resume created no extra run because nothing was due; final state is 20/20 GREEN, canonical/signals `165/11`, scheduler `1548`, acquisition request/attempt/evidence/processing `1908/1908/1903/1905`;
- candidate audit controls: YESC was deliberately not duplicated because S20 MOEP already represents it; LBVD returned repeatable Bangkok HTTP 403 and remains deferred/fail-closed.

Evidence: `docs/verification/S35-DAST-SOURCE-ONBOARDING-2026-09-07.md`.

### S36 Department of Agriculture Procurement Announcements — PRODUCTION / GREEN

- exact production application release `1561d6f5e53026b8f651e1aa40d9e52a3f6ee541`; previous application-code rollback target `5ad60eabc2a86235db413c37c49e4bbe91378f95`;
- issuer-original mixed DOA announcement board is Direct-HTTP GREEN and listing-complete at event/scope level; stable numeric `article_id` is the canonical identity, visible listing date is publication evidence, and scan/image detail is explicitly unfetched/non-blocking;
- opportunity classifier requires tender plus buyer/works semantics and excludes award/result and seller-side sale/auction/lease language; canonical identity is `doa:<article_id>`; deadlines remain `null` because they are not exposed as trustworthy listing HTML;
- production baseline: `MANUAL / baseline=1 / SUCCESS`, `items=6`, `tenders=6`, `details=0`, `changed=6`, `signals=0`; current scope includes hall construction, Desktop i5 x45, construction, HPLC/PDA laboratory equipment and ISO Lab renovation, plus one older procurement still present on the issuer board;
- baseline added exactly one HTML request/attempt/evidence/processing lifecycle, artifact `78,597` bytes, zero non-HTML evidence; SignalForge DB `quick_check=ok`;
- baseline Worker correlation is exactly one `signalforge-20260907T134030Z-0b687ac4 / SUCCESS`; Worker DB `quick_check=ok`;
- Bangkok and Beijing Worker doctors PASS; Beijing `/srv/signalforge` remains absent and rejects `signalforge-refresh S36` with `126 / DENY: SignalForge is Bangkok-only`; Mac provider remains `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`;
- frozen pre-deploy state was 20/20 GREEN with canonical/signals `165/11`, scheduler `1599`, acquisition request/attempt/evidence/processing `1970/1970/1965/1967`; deployment itself changed no counters;
- cumulative `failed_runs=5` is unchanged/historical/recovered and backlog remains zero; timer resume immediately started one normal reconciliation because existing sources were due, and that run completed without changing canonical/signals/failed/backlog; final state is 21/21 GREEN, canonical/signals `171/11`, scheduler `1603`, acquisition request/attempt/evidence/processing `1976/1976/1971/1973`, timer enabled/active, run-due inactive;
- fresh candidate control: DMH is transport-GREEN but current procurement specifics remain PDF/image dependent; OAG remains image/scan dependent, so neither opens an OCR/PDF gate in P0.

Evidence: `docs/verification/S36-DOA-SOURCE-ONBOARDING-2026-09-07.md`.

### S37 Ministry of Information Ministerial Office Procurement Announcements — PRODUCTION / GREEN

- exact production application release `d12d70d39794af32e67725700f344f8b50248bb0`; previous application-code rollback target `1561d6f5e53026b8f651e1aa40d9e52a3f6ee541`;
- mixed MOI department-announcement board is Bangkok Direct-HTTP GREEN, but the adapter discovery output is deliberately tender-only and issuer-specific: it requires Ministry of Information + Ministerial Office + opportunity-stage tender language, excluding other-agency reposts and award/result stages;
- native Drupal node identity `moi:<node_id>` is canonical; current node `moi:81536` has publication `2026-04-09`, four office-equipment types + one furniture type, sale window `2026-04-20..2026-05-11`, and explicit HTML deadline `2026-05-15`;
- production baseline: `MANUAL / baseline=1 / SUCCESS`, `items=1`, `tenders=1`, `details=1/1`, `changed=1`, `signals=0`; baseline added exactly two HTML acquisition lifecycles (`45,234`-byte listing + `41,575`-byte detail) and zero non-HTML evidence;
- baseline Worker correlation is exactly one `signalforge-20260907T145146Z-b9ee4d52 / SUCCESS`; SignalForge/Worker DB `quick_check=ok`;
- Bangkok and Beijing Worker doctors PASS; Beijing `/srv/signalforge` remains absent and rejects S37 refresh with `126 / DENY: SignalForge is Bangkok-only`; Mac provider remains `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`;
- frozen pre-deploy state was 21/21 GREEN, canonical/signals `171/11`, scheduler `1652`, acquisition request/attempt/evidence/processing `2030/2030/2025/2027`; deployment itself changed no counters;
- cumulative failed_runs remains 5 historical/recovered, backlog 0; timer resume created no extra run; final state is 22/22 GREEN, canonical/signals `172/11`, scheduler `1653`, acquisition request/attempt/evidence/processing `2032/2032/2027/2029`;
- S37 currently has one successful detail sample against `parse_min_attempts=2`, so `source_health=GREEN` while parse health is `UNKNOWN / PARSE_SAMPLE_INSUFFICIENT`; no artificial extra detail fetch was created;
- source-audit control plane note: CodexPro can invoke Mac Browser Plane for controlled website acquisition/inspection. This turn verified Browser Plane `doctor=READY` and used C0 on `industrymsme.gov.mm`; Industry is Mac-GREEN but Bangkok CONNECT_TIMEOUT and remains outside unattended production pending a separately justified provider/manual-P0 path.

Evidence: `docs/verification/S37-MOI-SOURCE-ONBOARDING-2026-09-07.md`.

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

1. operate S05A + S07 + S08A + S10 + S12 + S13 + S16 + S20 + S21 + S22 + S25 + S26 + S28 + S29 + S30 + S31 + S32 + S33 + S34 + S35 + S36 + S37 and collect real acquisition/source history;
2. choose the next source by business value plus current endpoint quality, not source-ID order or a target source count;
3. prefer another issuer-original Direct-HTTP source that fits the existing acquisition engine before introducing schema/OCR/Browser capability; S32 proved MTE event-level procurement can remain HTML-only, S33 resolved MCRD weak row identity with a bounded event fingerprint + collision guard, and S16 YCDC Building proved a stable department archive can supersede ephemeral ciphertext locators; S34 PTD proves high-value telecom/ICT procurement can stay HTML-event-level with PDF metadata-only deadlines; S35 DAST proves issuer-native WordPress IDs can safely normalize stale issuer-local `.edu.mm` locators onto the same issuer's working `.gov.mm` mirror while keeping scope/deadline HTML-first; S36 DOA proves a business-complete listing title can form the canonical event envelope while scan/image detail stays optional; S37 MOI proves a mixed government publication board can be safely narrowed to issuer-specific opportunity details without introducing aggregator dedup. CodexPro -> Mac Browser Plane is an approved engineering/source-audit path and should be used when it improves acquisition/inspection evidence, while unattended production remains Direct HTTP-first. DMH and OAG remain PDF/image dependent, LBVD is Bangkok HTTP 403, fresh S23 Ministry of Construction still fails Bangkok strict TLS because the issuer certificate is expired, and S27 MOBA still fails strict TLS; Ministry of Industry now uses `industrymsme.gov.mm`, is Mac Browser Plane C0 GREEN but Bangkok CONNECT_TIMEOUT, while Ministry of Energy (embedded PDF), Ministry of Education (image notice) and Tourism (JPG notice) remain deferred under current production capabilities;
4. S01 National Portal stays discovery-aggregator-only until issuer-resolution/equivalence/dedup exists; S04 Trade Portal remains deferred for the same cross-source contract reason;
5. preserve the remaining municipal gates: S16 Building is now production through the stable numeric archive and should not regress to randomized ciphertext locators; S17 still requires Burmese OCR and S18 still requires classifier + OCR; do not force those remaining capabilities into P0;
6. keep S10 PDF supplementary extraction as a separate reviewed runtime-packaging slice and promote it only when its incremental commercial value justifies the dependency;
7. S15A Manual P0 is production live-verified through real operation with two zero-signal canonical items (`mpa:37867` auction baseline and expired procurement `mpa:37841`); current listing has no actionable procurement signal, so keep low-frequency manual operation and do not build unattended remote invocation unless repeated real use proves material operational burden;
8. keep S08A tender-award/result content as a separate future `PROCUREMENT_RESULT` decision;
9. periodically recheck whether MOEP advertised PDFs become retrievable; only then consider a supplementary PDF parser gate;
10. keep Direct HTTP first; if a source truly requires Browser, route the requirement only to Mac Browser Plane and block unattended production until a separate Provider Invocation Contract is live-verified;
11. run the next cross-repo consistency review by 2026-12-03 or an earlier contract-change trigger.

## PIC v1 R3 live closure — 2026-09-08

This section is the authoritative R3 live closure and supersedes any earlier pre-credential status.

### Result

**PIC v1 R3 = LIVE PASS.** The real Bangkok-origin path was verified end-to-end for C0/C1/C2/C3 against verification-only S38 and `https://www.industrymsme.gov.mm/announcements`.

Gate:

```text
gate_id = 26ece5bb-fe15-47ae-a6b0-a7b4882d778f
C0_FETCH        SUCCEEDED / verified
C1_RENDER       SUCCEEDED / verified
C2_INSPECT      SUCCEEDED / verified
C3_BROWSER_USE  SUCCEEDED / verified
provider queue  SUCCEEDED=4; all other states=0
S38 scheduler_runs=0
S38 canonical_items=0
S38 signals=0
```

Evidence: `docs/verification/PIC-V1-R3-LIVE-PASS-2026-09-08.md`.

### Host credential boundary

A dedicated BKK user `signalforge-provider` and a new Mac-only Ed25519 provider key were installed. The public-key fingerprint is `SHA256:0m4dyyxo63gHlh5H4HbCDNEPPU2FQIUIGR1DinKnfJQ`.

The provider key is forced through `/usr/local/libexec/signalforge-provider-ssh-dispatch`, accepts only the four PIC dispatcher verbs, and can sudo only those exact forms to the existing `signalforge` identity. An arbitrary `id` command was live-denied with exit 126. The provider credential disable/restore path was also live verified.

Administrative/root SSH credentials are not used by the unattended Provider Agent.

### Software / production state

- BKK SignalForge exact deployed application release: `aafa4195d2b747226a379e668911f7f686287c78`;
- previous rollback release: `d12d70d39794af32e67725700f344f8b50248bb0`;
- Mac Browser Plane post-gate doctor: `READY`;
- `browser_production_approved=false` remains frozen;
- R3 isolated contract remains evidence-only / top-level disabled;
- R4 production enablement has **not** been performed.

### S25 recovery note

The MONPIFER `/index.php/` path regression is fixed and a real post-deploy S25 refresh succeeded with 10 parsed tenders and `consecutive_failures=0`. Its rolling parse-health window remains RED temporarily because it contains old failures; do not manufacture GREEN by repeated refreshes.

The recovery refresh emitted 10 `UPDATED` signals because transport/attachment metadata changed with the issuer path shape. No destructive cleanup was performed. Treat this as a separate signal-noise/equivalence review item before altering historical production records.

### Next

R3 no longer blocks the Provider Invocation Contract. The next PIC slice is R4 Provider Production Enable, but it must deliberately change the frozen production flags and must not be conflated with this evidence-only gate. Until R4 is separately reviewed/executed, healthy production acquisition remains Direct HTTP-first and the Mac provider remains non-production.

## Authoritative current provider/source checkpoint — 2026-09-08

This section supersedes the older pre-R4 state above without rewriting historical evidence.

- PIC R4/R5 is production-live. Mac Browser Provider uses dedicated restricted pull SSH + local MCP stdio; no public Mac listener and no generic Direct-HTTP failure fallback.
- S38 Ministry of Industry is the first provider-backed source and remains production GREEN / C0-only.
- S27 Ministry of Border Affairs is now the second explicit provider-backed source on implementation SHA `29cdf90554c61bfcdc8bfb6cf4fba16c597652c9`.
- Fresh S27 network split remains: Bangkok strict TLS 6/6 curl-60, Mac C0 listing/detail HTTP 200. Production policy is therefore explicit provider routing, not fallback.
- S27 allowlist: exact `https://moba.gov.mm/my/tender` LISTING, same-host `/my/tender/<id>` DETAIL, C0 only, query/fragment denied, PDF metadata-only.
- S27 first production baseline: Worker `signalforge-20260908T151231Z-d816f1d3`, app `9621ea2a-3c8c-4206-93c8-07f5e1d3c2b6`, `SUCCESS / discovered=7 / candidates=6 / details=6/6 / changed=6 / signals=0 / backlog=0`.
- Durable S27 state: canonical 6, signals 0, provider SUCCEEDED 7/non-success 0, evidence 7, processing SUCCESS 7, DB quick check `ok`; source health GREEN / parse 6 of 6.
- Beijing `/srv/signalforge` remains absent and `/usr/local/sbin/gha-root-dispatch` rejects `signalforge-refresh S27` with exit 126 / `DENY: SignalForge is Bangkok-only`.
- Bangkok timer is restored enabled/active. Immediate timer-triggered scheduler Worker `signalforge-20260908T151524Z-ddbdc70c` completed SUCCESS; S27 correctly returned NOT_DUE until `2026-09-08T15:42:32.230651Z`.
- S27 rollout exposed a deploy root-mode bug when a 0700 `mktemp -d` source was copied with `cp -a`. Rollback preserved the old active release and timer OFF. Candidate root was normalized to 0755, exact-SHA deploy then succeeded, and the deploy script is hardened to normalize `$STAGE` after copy.

Evidence: `docs/verification/S27-MOBA-PROVIDER-SOURCE-ONBOARDING-2026-09-08.md`.

## Authoritative S39 / current topology checkpoint — 2026-09-08

This section supersedes the S27-only current checkpoint above without rewriting historical verification records.

- SignalForge production topology is **Bangkok-only**. Beijing has no SignalForge production role and is no longer a per-source onboarding/rollout gate; historical Beijing zero-footprint checks remain historical evidence only.
- S39 Ministry of Energy is production-enabled on exact application release `b8de9b0e2916b8e21f6bf6f7a1df66ce6e5f204b` and uses Bangkok Direct HTTP only; Mac Browser Provider configuration was not changed.
- S39 source shape: listing HTML -> numeric detail HTML -> exactly one required same-origin text-native official PDF; parser performs no network I/O.
- First baseline Worker `signalforge-20260908T154731Z-b8e83d7f`, app `e9ca4a06-d058-44fb-a5b4-c1d5e84fa54f`: `SUCCESS / discovered=4 / details=4/4 / changed=4 / signals=0 / backlog=0`.
- Durable S39 state: canonical 4, signals 0, pending 0, acquisition targets `DISCOVERY=1 / HTML=4 / PDF=4`, EvidenceEnvelope 9, detail business processing 4/4 SUCCESS, PDF Evidence hashes match all canonical evidence hashes, DB quick check `ok`.
- S39 health: GREEN; fetch GREEN, freshness GREEN, parse 4/4, consecutive failures 0, last error null.
- Deployment hardening was live re-verified: a 0700 `mktemp -d` rollout source produced a final 0755 release root and deployed successfully.
- Bangkok timer is enabled/active. Timer-triggered Worker `signalforge-20260908T155715Z-fce090b1` completed `run-due` SUCCESS; S39 correctly remained NOT_DUE until `2026-09-08T16:17:31.274994Z` rather than being artificially forced.
- Final SignalForge state: `PASS / GREEN`, canonical items 193, signals 34, recovery backlog 0. S25 recovered naturally to GREEN at parse 9/10 without artificial refreshes.

Evidence: `docs/verification/S39-MINISTRY-OF-ENERGY-SOURCE-ONBOARDING-2026-09-08.md`.

## Authoritative S40 current checkpoint — 2026-09-08

This section supersedes the S39-only current application checkpoint above while preserving historical records.

- SignalForge production remains Bangkok-only; Beijing is outside the production topology and is not a per-source rollout gate.
- Active application release is `9980584b7deec660d16e5f202ff0056117df88f6`; immediate rollback target is `b8de9b0e2916b8e21f6bf6f7a1df66ce6e5f204b`.
- S40 Ministry of Labour is a Bangkok Direct HTTP `ACTIVE_SELECTIVE` watcher on `https://www.mol.gov.mm/tender/` page 1 only. No Mac Provider change, Browser, OCR, JSON acquisition or multi-page production discovery was introduced.
- Current page 1 contains only workflow/result-stage tender posts, so first baseline correctly produced zero business items rather than admitting awards/technical-qualified rows.
- First baseline Worker `signalforge-20260908T163346Z-05f65b51`, app `b2b3f5ff-4802-441c-9b28-c1efe819d65b`: `SUCCESS / discovered=0 / candidates=0 / changed=0 / signals=0 / backlog=0`.
- Durable S40 state: canonical 0, signals 0, pending 0, acquisition `DISCOVERY=1`, EvidenceEnvelope 1, processing SUCCESS 1, DB quick check `ok`; no detail or PDF production acquisition occurred because no current opportunity exists.
- Historical issuer page-2 fixtures prove opportunity-stage selection and required same-origin text-PDF parsing for Smart ID Card Printing (`2026-07-14 16:30`) and medical equipment (`2026-07-13 16:30`, Electric High Speed Drill + Fibroscan); those records are not production backfilled.
- S40 source health is GREEN: fetch/freshness/recovery GREEN, consecutive failures 0, last error null; parse is honestly `UNKNOWN / PARSE_SAMPLE_INSUFFICIENT` until a real current opportunity supplies a production detail sample.
- Bangkok timer is enabled/active. Timer Worker `signalforge-20260908T163503Z-f6e89982` completed `run-due` SUCCESS on the new release; S40 correctly returned NOT_DUE until `2026-09-08T17:03:46.458201Z`.
- Overall SignalForge remains `PASS / GREEN`, canonical items 193, signals 34, recovery backlog 0.

Evidence: `docs/verification/S40-MINISTRY-OF-LABOUR-SOURCE-ONBOARDING-2026-09-08.md`.

## Authoritative signal-quality checkpoint — S25 + S30 — 2026-09-09

This checkpoint supersedes the S40-only application checkpoint for current production state without rewriting historical source-onboarding evidence.

- Active Bangkok application release: `38ba382bd132769dd89e784331f06c3ae7e3392a`; timer enabled/active; DB quick check `ok`.
- Overall SignalForge: `PASS / GREEN`; canonical items `193`; signals `35`; recovery backlog `0`; all current sources GREEN.
- S25 MONPIFER signal noise from equivalent `/index.php/sites/...` vs `/sites/...` PDF URLs is fixed at source-parser normalization boundary by PR #96 / `a7e979743cfe092c7af20ed6a460fb5c74c4b75a`. Production live verification parsed the same 10 tenders with `changed=0 / signals=0`; historical noisy signals remain preserved.
- S30 MOFA optional text-PDF enrichment is production live on PR #97 / `38ba382bd132769dd89e784331f06c3ae7e3392a`. It is Bangkok Direct HTTP only; same-origin PDF, max one, optional; PDF failure falls back to HTML metadata; S39/S40 required-PDF contracts remain fail-closed.
- Current `mofa:59800` is a still-actionable ICT tender published 2026-09-04. Normal unattended scheduler processing at `2026-09-08T17:50:03.314007Z` enriched it to deadline `2026-09-18 16:30` and scope including Data Server / PowerEdge R750-XS / Windows Server 2025 / Microsoft SQL Server 2022, then emitted exactly one `UPDATED` signal.
- The canonical evidence SHA is `aad5b2c3e51ffc289edb5018254f364896b01d14bee8fa3be7e362e756e130c7`. All four S30 PDF acquisition artifacts observed through the current snapshot match that SHA; repeated later PDF probes produced no duplicate customer signal.
- Product priority: continue business-value audits of existing production sources for semantic noise and missing deadline/scope before adding S41/S42 merely to increase source count. Resume source expansion when a genuine issuer coverage gap has higher expected value.
- Beijing remains outside SignalForge production topology and is not part of this checkpoint or future per-source quality audits.

Evidence: `docs/verification/SIGNAL-QUALITY-S25-S30-PRODUCTION-CLOSURE-2026-09-09.md`.

## Authoritative actionable-baseline checkpoint — 2026-09-09

This checkpoint supersedes the S25/S30-only current production counters while preserving that closure as historical evidence.

- Active Bangkok application release: `6f10d0f5a7cf37ca11d8461c03a54b3ff9f648c7`; timer enabled/active; DB quick check `ok`.
- Overall SignalForge: `PASS / GREEN`; canonical items `193`; signals `42`; recovery backlog `0`; all current sources GREEN.
- PR #99 adds per-source opt-in actionable baseline reconciliation. Initial scope is S38/S39 only: `TENDER + OPPORTUNITY`, no existing signal, explicit deadline+time, minimum 12 hours remaining, maximum 3 signals per source run, nearest deadline first, atomic idempotent insert, signal reason `ACTIONABLE_BASELINE_RECONCILIATION`.
- First baseline behavior remains unchanged and signal-free. This is not historical backfill; it repairs baseline-suppressed canonicals that remain genuinely open.
- S39 live gate: app `855a944b-4f37-4174-8f3b-3fcdefc5f05a`, `changed=0 / signals_created=1`; only `energy:235` was promoted, deadline `2026-09-18 13:00`.
- S38 live gate batch 1: app `22df739b-37a7-4cfc-ae02-5fb396bdf7ec`, signals 3 for `industry:1022` (09-11), `industry:1034` (09-14), `industry:1037` (09-22), all 16:00.
- S38 live gate batch 2: app `0044b9f4-747a-4da6-b7c6-fde0e1c29975`, signals 3 for remaining eligible `industry:1036` (09-24), `industry:1039` (09-25), `industry:1035` (10-02), all 16:00.
- Third S38 and second S39 executions were idempotent: SUCCESS / changed 0 / signals_created 0. Expired S38 `industry:1025` and `industry:1033` have zero signals; future-deadline unsignaled S38/S39 count is zero.
- Timer restoration produced two closely spaced normal `run-due` invocations; both completed SUCCESS with sources NOT_DUE and total signals unchanged at 42, providing an additional scheduler-level idempotency proof.
- Full suite `217 passed`; no schema/daemon/Browser/Provider capability expansion was introduced.
- Beijing remains outside SignalForge production topology and is not part of this checkpoint.

Evidence: `docs/verification/ACTIONABLE-BASELINE-RECONCILIATION-PRODUCTION-CLOSURE-2026-09-09.md`.

## Authoritative current-opportunities checkpoint — 2026-09-09

This checkpoint supersedes the actionable-baseline-only application snapshot for current runtime state while preserving that production closure as historical evidence.

- Active Bangkok application release: `9f6ee1e39737c9226574d2a7bb9f3dc92fbf2691`; immediate rollback target `6f10d0f5a7cf37ca11d8461c03a54b3ff9f648c7`; timer enabled/active; run-due inactive after successful completion; DB quick check `ok`.
- Overall SignalForge: `PASS / GREEN`; canonical items `193`; signals `42`; recovery backlog `0`; all current sources GREEN.
- PR #101 adds read-only `signalforge opportunities`; it is not in the Worker verb manifest and does not alter DB schema/writes, scheduler, acquisition, signal generation, Provider or Browser policy.
- Default view contains only signal-backed canonical `TENDER / OPPORTUNITY` records, deduped to one row per canonical, using current canonical business fields. OPEN and UNKNOWN deadlines are visible; EXPIRED is hidden by default and available only via explicit `--include-expired`.
- Live production view returned `9` rows: `8 OPEN + 1 UNKNOWN`. OPEN keys are `industry:1022`, `industry:1034`, `energy:235`, `mofa:59800`, `industry:1037`, `industry:1036`, `industry:1039`, `industry:1035`; UNKNOWN is `doms:12735`. Each had exactly one signal at the verification snapshot.
- Historical S25 duplicate signal rows do not duplicate the current opportunities view because the view groups by canonical and displays current canonical state.
- Read-only verification preserved `193 canonical / 42 signals`; the restored timer then ran a normal scheduler cycle SUCCESS on the new release. Real due health probes including S13/S34/S39 succeeded with no signal change; a post-cycle opportunity read remained `8 OPEN + 1 UNKNOWN`.
- Full suite `220 passed`; targeted opportunity/contract tests `7 passed`.
- Beijing remains outside SignalForge production topology.

Evidence: `docs/verification/CURRENT-OPPORTUNITIES-VIEW-PRODUCTION-CLOSURE-2026-09-09.md`.

## Authoritative closed opportunities control-read checkpoint — 2026-09-09

This checkpoint supersedes the local-only current-opportunities runtime snapshot for remote-consumption state while preserving the prior closure as historical evidence.

- Active Bangkok SignalForge release: `77334ea49acc494c845a4dd38413c65ac2240f6d`; immediate application rollback target `9f6ee1e39737c9226574d2a7bb9f3dc92fbf2691`.
- Active reviewed vps-control-plane policy: `007398a26b7d42a4b0edde4627f0c08b46c33998`; installed Bangkok dispatcher SHA256 `2545deaf1d99dc1c2c021d094f26f9c70c938458550b73291b2dfeef2ce3acf3`; previous dispatcher preserved as `gha-root-dispatch.pre-007398a`.
- SignalForge manifest version remains `1` and now includes exact no-argument read verb `signalforge-opportunities -> opportunities`; no generic argument surface was added.
- Fail-closed rollout proof: before dispatcher deployment the new verb returned `126 / DENY`; after deployment, `signalforge-opportunities extra` also returned `126`. Valid Bangkok invocation returned `PASS / 9` with `8 OPEN + 1 UNKNOWN`.
- GitHub Actions `VPS Control` run `34318367015` completed SUCCESS from exact Control Plane main `007398a...`, using the dedicated restricted Actions SSH key and forced dispatcher, and returned the same 9-row production opportunity view.
- Beijing received no deployment for this slice and a read-only negative probe remained `126 / DENY`; Beijing is still outside SignalForge production topology.
- Natural Bangkok scheduler invocation at 2026-09-09 12:45 Myanmar time completed SUCCESS on `77334ea...`; final status remains `PASS / GREEN`, all sources GREEN, canonical `193`, signals `42`, recovery backlog `0`, DB quick check `ok`, timer enabled/active.
- No public HTTP API, new listener/daemon, arbitrary remote shell, DB write path, scheduler mutation, Browser capability, Provider capability, or delivery subsystem was introduced.

Evidence: `docs/verification/OPPORTUNITIES-CONTROL-READ-PRODUCTION-CLOSURE-2026-09-09.md`.

## Authoritative opportunity-qualification checkpoint — 2026-09-09

This checkpoint supersedes the closed-read-only runtime snapshot for current opportunity presentation while preserving all earlier closures as historical evidence.

- Active Bangkok SignalForge release: `08153c47b1efc67c85776f551da2e1130b2d1c63`; immediate rollback target `5e599801be58a58ce983e61d2b1564c6ef6a83a9`.
- Deployment archive SHA256: `927ddc89a778c88e20261abd83ec015a404bc33c0812409d359edec2378dc9d5`, identical locally and on Bangkok.
- PR #106 adds read-time Opportunity Qualification policy v1 only. No canonical/signal write, schema, scheduler, acquisition, Browser, Provider or Control Plane contract change.
- Full suite: `224 passed`; targeted qualification/opportunity tests: `6 passed`; whitespace gate PASS.
- Overall production: `PASS / GREEN`; canonical `194`; signals `44`; recovery backlog `0`; DB quick check `ok`; Bangkok timer enabled/active.
- Current view remains nine signal-backed opportunities: `8 OPEN + 1 UNKNOWN`. Trust distribution is `A=8 / B=1 / C=0`; priority is `HIGH=3 / MEDIUM=5 / REVIEW=1 / LOW=0`.
- HIGH: `industry:1022` because it is A-grade and <=72h remaining; `energy:235` and `mofa:59800` because they are A-grade ICT opportunities. MEDIUM contains the other five A-grade Industry opportunities. `doms:12735` remains `B / REVIEW / MEDICAL / deadline UNKNOWN`.
- Evidence semantics are explicit: Industry uses `OFFICIAL_HTML_VIA_PROVIDER`; Energy and MOFA use `OFFICIAL_HTML_PLUS_TEXT_PDF`; DOMS uses `OFFICIAL_HTML` with partial completeness.
- Existing closed dispatcher `signalforge-opportunities` returned `PASS`, qualification policy version 1 and the same nine qualified rows. No Control Plane deployment was required.
- Qualification remains deterministic/non-ML and does not infer missing facts. Relevance v1 regression explicitly rejects false ENERGY matches from `PowerEdge`, ordinary `Power Supply`, `Engine Power`, and ordinary `Electrical Spare Parts`.

Evidence: `docs/verification/OPPORTUNITY-QUALIFICATION-V1-PRODUCTION-CLOSURE-2026-09-09.md`.

## Authoritative Business Briefing v1 checkpoint — 2026-09-09

This checkpoint supersedes the qualification-only presentation checkpoint for current read-delivery state while preserving all earlier closures as historical evidence.

- Active Bangkok SignalForge release: `a61f9f7e7ef0af9be22bafd778f17bfe5f3a5ebc`; immediate rollback target `08153c47b1efc67c85776f551da2e1130b2d1c63`.
- Deployment archive SHA256: `b056278fc0aad8f3a70c80789031ba33a08c2b42edbd95e0d15cf72220023d38`, identical locally and on Bangkok.
- PR #108 adds read-only `signalforge briefing` and manifest verb `signalforge-briefing`; full suite `227 passed`; targeted briefing/contract/opportunity/qualification tests `13 passed`.
- Briefing policy v1 expands only `HIGH + REVIEW`, maps attention to `ACT_NOW / PRIORITIZE / REVIEW`, and summarizes MEDIUM opportunities in a compact watchlist. Natural-language rendering is explicitly external and facts must not be inferred.
- Production DB backup preview and live application both returned 9 current opportunities -> 4 attention rows (`ACT_NOW=1 / PRIORITIZE=2 / REVIEW=1`) + 5 MEDIUM watchlist rows. Attention keys are `industry:1022`, `energy:235`, `mofa:59800`, and `doms:12735`.
- Active reviewed vps-control-plane policy: `061d260c3dddddac64d82107929e96cb7c85fe98`; installed Bangkok dispatcher SHA256 `fcd15ba510b300c3bb511bb8a3f7c6765d7b2c2afdd55a19a83b3791e64862d3`; previous dispatcher preserved as `gha-root-dispatch.pre-061d260`.
- Fail-closed proof: before dispatcher deployment `signalforge-briefing` returned `126 / DENY`; after deployment, `signalforge-briefing extra` remained `126`, valid no-argument invocation returned PASS with the same 4/5 briefing, and Beijing remained `126 / DENY` without deployment.
- Final production state: `PASS / GREEN`; canonical `194`; signals `44`; recovery backlog `0`; DB quick check `ok`; Bangkok timer enabled/active.
- No public API, new listener/daemon, credentials, LLM runtime, DB write, scheduler mutation, acquisition change, Browser capability, Provider capability, or Beijing dependency was introduced.

Evidence: `docs/verification/BUSINESS-BRIEFING-V1-PRODUCTION-CLOSURE-2026-09-09.md`.

## Authoritative Telegram Delivery v1 credential-gate checkpoint — 2026-09-09

This checkpoint supersedes the briefing-only runtime snapshot for current delivery readiness while preserving the prior closure as historical evidence.

- Active Bangkok SignalForge release: `489d05f5b36189dc8292b51032edf49e0e102b4d`; immediate rollback target `a61f9f7e7ef0af9be22bafd778f17bfe5f3a5ebc`.
- Deployment archive SHA256: `ccc50cab9cee209512a8cccd7eb1c91ee24a7209893ae9833170bb350d22fceb`, identical locally and on Bangkok.
- PR #110 adds Telegram Delivery v1; full suite `234 passed`; production schema is now v6 with generic successful `delivery_receipts`.
- Delivery identity is `channel + canonical_key + latest_signal_id + attention_action`; this deduplicates repeated timer checks while allowing new Signals and action escalation to notify. Transport guarantee is `AT_LEAST_ONCE_WITH_SUCCESS_RECEIPT_DEDUP`.
- BKK systemd verification PASS. `signalforge-telegram-deliver.service` and `.timer` are installed; timer is intentionally `disabled / inactive` pending credentials. Deployment preserves its prior enabled state after later upgrades.
- Secret contract is root-managed `/etc/signalforge/telegram.env` containing `SIGNALFORGE_TELEGRAM_BOT_TOKEN` and `SIGNALFORGE_TELEGRAM_CHAT_ID`. Deployment does not create the file and no secret is stored in Git.
- BKK strict TLS reachability to `api.telegram.org` PASS. No Browser, Provider, proxy or TLS weakening is required for Telegram delivery.
- Live production dry-run returned exactly four pending events: `industry:1022 ACT_NOW`, `energy:235 PRIORITIZE`, `mofa:59800 PRIORITIZE`, `doms:12735 REVIEW`; the five MEDIUM watchlist items are not delivered.
- Final safe-disabled state: overall `PASS / GREEN`; canonical `194`; signals `44`; delivery receipts `0`; recovery backlog `0`; DB quick check `ok`; main SignalForge timer enabled/active; Telegram timer disabled/inactive; secret file absent; no Telegram message sent.
- Hard gate remaining: operator-local configuration of bot token and target chat ID on Bangkok, followed by reviewed first delivery, receipt/idempotency verification and explicit timer enable.

Evidence: `docs/verification/TELEGRAM-DELIVERY-V1-CREDENTIAL-GATE-2026-09-09.md`.

## Authoritative Telegram Delivery v1 production checkpoint — 2026-09-09

This checkpoint supersedes the prior Telegram credential-gate checkpoint for current delivery state while preserving that checkpoint as historical evidence.

- Active Bangkok SignalForge release: `489d05f5b36189dc8292b51032edf49e0e102b4d`; immediate rollback target `a61f9f7e7ef0af9be22bafd778f17bfe5f3a5ebc`.
- Telegram secret file exists locally on Bangkok with `0640 root:signalforge`; credential values are not stored in Git or this checkpoint.
- First real Telegram delivery completed SUCCESS and sent four attention events: `industry:1022 ACT_NOW`, `energy:235 PRIORITIZE`, `mofa:59800 PRIORITIZE`, `doms:12735 REVIEW`. Provider message IDs were `3,4,5,6`; delivery receipts became `4`.
- Immediate second delivery returned `PASS / pending_count=0 / sent_count=0`; receipt count remained `4`. Same signal/action state therefore does not repeat.
- Delivery identity remains `channel + canonical_key + latest_signal_id + attention_action`; new Signals and action escalation remain eligible to notify. Transport semantics are `AT_LEAST_ONCE_WITH_SUCCESS_RECEIPT_DEDUP`.
- `signalforge-telegram-deliver.timer` is now enabled/active. `signalforge-run-due.timer` remains enabled/active.
- Final production: `PASS / GREEN`; canonical `194`; signals `44`; recovery backlog `0`; DB quick check `ok`; Telegram receipts `4`.
- No public API, webhook, inbound bot command handler, Browser change, Provider change, Beijing dependency or MEDIUM-watchlist delivery was introduced.

Evidence: `docs/verification/TELEGRAM-DELIVERY-V1-PRODUCTION-CLOSURE-2026-09-09.md`.

## Authoritative Telegram Message UX v1.1 checkpoint — 2026-09-09

- Active Bangkok release: `ff9df1af9ebf7e144b33b94aec7f6d32782a1992`; rollback `489d05f5b36189dc8292b51032edf49e0e102b4d`.
- PR #113 is presentation-only: Chinese static action/field labels, compact evidence labels, 240-character scope cap and surfaced Signal type. Official titles/facts remain untranslated and uninferred.
- Full suite `235 passed`; deployment archive SHA256 `7dddcc93ae218a43d2b8addfff88d0191a5da9c020ee220dfc0842d7dd1f09e6`.
- Exact live renderer card lengths are 643 / 581 / 746 / 754 chars for Industry / Energy / MOFA / DOMS attention rows.
- Post-deploy delivery invocation returned `PASS / pending_count=0 / sent_count=0`; successful receipt count remained `4`, proving message text does not participate in delivery identity and old events were not resent.
- Final production: `PASS / GREEN`; DB quick check `ok`; `194 canonical / 44 signals / backlog 0 / 4 Telegram receipts`; acquisition and Telegram timers enabled/active.
- No qualification, delivery eligibility, receipt identity, timer, schema, acquisition, Browser or Provider change.

Evidence: `docs/verification/TELEGRAM-MESSAGE-UX-V1.1-PRODUCTION-CLOSURE-2026-09-09.md`.

## Authoritative S13 MPT Semantic v2 checkpoint — 2026-09-09

- Active Bangkok release: `21c162e0333c328e06f9a83ad7bee7b1bdf2abdf`; rollback `ff9df1af9ebf7e144b33b94aec7f6d32782a1992`; archive SHA256 `2698747d39ea4275b192c103d67caa4319a6e188cb30238e613c9aef6496f948`.
- S13 runtime parser is `mpt-v4`, normalizer `mpt-normalize-v2`; Direct HTTP acquisition and canonical identity are unchanged.
- v2 emits business stage, scope summary, detail completeness, deadline evidence/candidates and evidence-backed `PRE_QUALIFICATION`; full/abbreviated English month names are supported.
- Deadline policy is fail-closed: only a unique official candidate not earlier than publication is accepted. `mpt:202604-CTO-029` remains deadline-conflicted because official candidates `2026-03-06` and `2025-03-06` both precede publication `2026-04-08`.
- Read-only audit of all 16 stored official MPT pages: `15 OPPORTUNITY / 1 TENDER_NOTICE`, minimum scope length 41, all 16 currently show Pre-Qualification evidence.
- End-to-end regression proves a future MPT mobile-network/fiber tender becomes `OPEN / A / HIGH / TELECOM / OFFICIAL_HTML / direct_http`; full suite `239 passed`, targeted gate `27 passed`.
- No migration, historical canonical rewrite, business-enrichment backfill or forced S13 refresh was performed. Pre/post deploy S13 stayed `16 canonical / 10 signals`; global stayed `194 canonical / 44 signals`; Telegram receipts stayed 4 and post-deploy delivery returned zero pending/sent.
- Current production S13 opportunities remain zero intentionally because historical payloads remain untouched. The next genuine new or officially changed MPT page will naturally use semantic v2.
- Final production: `PASS / GREEN`, DB quick check `ok`, backlog 0, acquisition and Telegram timers enabled/active.

Evidence: `docs/verification/S13-MPT-SEMANTIC-V2-PRODUCTION-CLOSURE-2026-09-09.md`.

## Authoritative signal-quality checkpoint — parser-only suppression + DOMS audit — 2026-09-10

This section supersedes the S13 Semantic v2 application snapshot above for current production state while preserving that closure and its pre-natural-probe counters as historical evidence.

- Active Bangkok SignalForge release: `9f4605fd55039704d335da7bda33662b9c234528`; immediate rollback target: `21c162e0333c328e06f9a83ad7bee7b1bdf2abdf`; local deployment archive SHA256: `9af6e74b96638e3e52018833b846abb51458235420f49080951ab6b9520b830c`.
- A normal post-Semantic-v2 S13 health probe created production signal `mpt:CCO-2026-001 / UPDATED` at `2026-09-09T17:15:12.735583Z`. The tender deadline was already `2026-08-06`; investigation showed the canonical payload was being enriched from byte-identical official detail evidence rather than an issuer-side source change.
- PR #117 adds the minimal fix: for detail pipelines with no attachment captures, if the previous discovery detail SHA equals the current raw `detail_capture.sha256`, canonical semantics may update but customer signal emission is suppressed. A real raw HTML change still emits `UPDATED`.
- Multi-evidence HTML+PDF pipelines remain outside this rule. The first generic implementation caused the existing S30 MOFA regression to fail (`239 passed / 1 failed`) because HTML can change while its PDF remains identical. The rule was narrowed instead of introducing a new evidence-bundle schema; final full suite is `240 passed` and targeted engine/MPT/opportunity/briefing/Telegram gates pass.
- GitHub Actions PR `verify` run `34443774429` PASS; PR #117 squash-merged as exact production code SHA `9f4605fd55039704d335da7bda33662b9c234528`.
- Production-copy verification used the real stored S13 detail evidence SHA `3334984f1fc2a56e601261eeea84f9c6356a82ef11ccffb05b8d0e560fb4c971`: the deployed runtime returned `SUCCESS / health_probe=true / changed=1 / signals_created=0`, restored `business_stage=OPPORTUNITY / deadline=2026-08-06`, and kept the copied signal count `45 -> 45`. The real production DB was not mutated.
- The historical parser-only signal is intentionally retained as audit history; no canonical/signal deletion or historical rewrite was performed.
- DOMS `doms:12735` remains `B / REVIEW / MEDICAL / deadline UNKNOWN`. All three current issuer PDFs were audited with existing `pypdf==6.16.2` and are effectively scan-only: 8DMS `2 pages / 1 extracted char`, 9DMS `5 / 4`, 10DMS `2 / 1`. Text-PDF enrichment is therefore insufficient; OCR remains deferred rather than being introduced for one record.
- Final live Bangkok state: `PASS / GREEN`; `194 canonical / 45 signals / recovery backlog 0`; DB quick check `ok`; acquisition and Telegram timers active; Telegram dry-run `pending_count=0`.
- No schema, dependency, source registry/policy, Browser Plane, Provider, Worker Plane, Control Plane, Beijing role or Telegram delivery-identity change was introduced. Product priority remains existing-source semantic/missing-field audits before source-count expansion.

Evidence: `docs/verification/S13-PARSER-NOISE-DOMS-AUDIT-PRODUCTION-CLOSURE-2026-09-10.md`.

## Authoritative S34 PTD text-PDF semantic checkpoint — 2026-09-10

This section supersedes the prior S34 metadata-only snapshot and the prior current-runtime application snapshot for present SignalForge production state while preserving both as historical evidence.

- Active Bangkok SignalForge release: `5fc7625da9c19599ef0a1dd1e6b3fca68d90013b`; final deployment archive SHA256 `526efb4855bd54b44511629879749ca9d945585372cb5d3fa63de5dc912de61c`, matched locally and on Bangkok.
- Deploy-script immediate previous release is `69ae03d47eab719152f09134f33a35cfef467e80`, but that intermediate PR #119 release contains the raw-SHA initial-enrichment suppression defect found by production-copy verification. It is not the preferred semantic rollback. Known-good pre-S34-feature release `9f4605fd55039704d335da7bda33662b9c234528` remains available and is the safer feature-level rollback if PTD PDF semantics must be removed.
- S34 remains `ACTIVE_SELECTIVE / direct_http`; source policy is v2 and requires exactly one same-origin official text PDF in the primary detail pipeline. Canonical identity remains `ptd:<publication_date>:<sha256(publication_date|normalized_scope_summary)[:16]>`. No Browser or Provider acquisition was added.
- Official evidence audit: all 6 current PTD tender PDFs are text-native with existing `pypdf==6.16.2`; 5 yield stable schedules and 1 remains UNKNOWN because extracted date glyphs are incomplete. No OCR or new dependency was introduced.
- PTD schedule semantics are explicit: section 3 -> `deadline_kind=TENDER_FORM_SALE_CLOSE` (tender-form sale/availability close, not asserted bid-submission deadline); section 6 -> separate `tender_opening_date/time`; sale-close `deadline_time` remains null when unstated. Read surfaces preserve the distinction through `opportunities -> briefing -> Telegram`; Telegram uses `获取标书截止` and shows opening separately.
- PR #119 verify run `34451641329` PASS; squash merge `69ae03d47eab719152f09134f33a35cfef467e80`; pre-merge full suite `246 passed`. A real PTD temporary baseline returned `discovered=6 / fetched=6 / details=6/6 / changed=6 / signals=0`.
- Production-copy gate on `69ae03d...` exposed that ASP.NET raw detail bytes may drift without business-semantic change: temporary copied state returned `changed=1 / signals_created=1 / signals 45->46 / S34 0->1`. The real production DB was not mutated and remained `45 / S34=0`.
- PR #120 replaces raw-SHA suppression with a one-time semantic projection. It applies only to explicitly opted-in S34 pre-v2 canonicals (`METADATA_ONLY_NON_BLOCKING` + `HTML_EVENT_SCOPE_PDF_DEADLINE_UNPARSED`) and only when all non-PDF business fields are identical. Once enriched, a later actual PDF schedule change emits normal `UPDATED`; regression proves `2026-08-20 -> 2026-08-21` creates one signal. Targeted PTD+engine `16 passed`; full suite `246 passed`; verify run `34452719347` PASS; squash merge/final production SHA `5fc7625da9c19599ef0a1dd1e6b3fca68d90013b`.
- Reviewed manual Worker boundary remains intact. Direct `refresh-source S34` outside systemd failed closed on missing `INVOCATION_ID`; `signalforge-refresh@S34.service` ran with Worker correlation `signalforge-20260910T075224Z-9fe758c9` and SUCCESS. It had zero detail candidates because the previous normal health probe was still fresh; no production state was manipulated to manufacture a candidate.
- Exact deployed `5fc7625...` production-copy verification using a fresh real DB backup and live PTD source returned `SUCCESS / health_probe=true / candidates=1 / fetched=1 / details=1/1 / changed=1 / signals_created=0 / signals 45->45 / S34 0->0`; the copied `ptd:2026-07-31:a683b1bfdd91b4c7` became sale close `2026-08-20`, opening `2026-08-25 14:30`.
- No forced historical S34 backfill is performed: all 5 safely parsed sale-close dates are already expired. Natural health probes may progressively enrich old canonicals without false customer signals; genuinely new PTD tenders use HTML+required PDF semantic v2 on first processing and retain normal NEW-signal semantics.
- Final live Bangkok: `PASS / GREEN`; `194 canonical / 45 signals / S34 signals 0 / recovery backlog 0`; DB quick check `ok`; acquisition and Telegram timers active; Telegram dry-run `pending_count=0`.
- No schema, OCR, new dependency, Browser Plane, Provider, Worker Plane, Control Plane, Beijing role, public API/webhook or Telegram delivery-identity change. Product priority remains existing-source semantic/missing-field audit before source-count expansion.

Evidence: `docs/verification/S34-PTD-TEXT-PDF-SEMANTIC-PRODUCTION-CLOSURE-2026-09-10.md`.

## Authoritative S31 MOEA HTML Semantic v2 checkpoint — 2026-09-10

This section supersedes the prior S31 semantic/runtime snapshot for current production state while preserving the original S31 onboarding closure as historical evidence.

- Active Bangkok SignalForge release: `038a78e195df0a8ea98f256d7bc2862e0234f6f8`; immediate rollback target `5fc7625da9c19599ef0a1dd1e6b3fca68d90013b`; deployment archive SHA256 `5a8dcb0cf17c77b94d23e41976f1c8071aa964a57b3716a6ab4e34f505168ff3`, matched locally and on Bangkok.
- PR #122 Actions verify run `34455774263` PASS; exact squash merge/runtime SHA `038a78e195df0a8ea98f256d7bc2862e0234f6f8`; targeted MOEA/contract/Telegram tests `22 passed`; full suite `249 passed`; `git diff --check` PASS.
- S31 remains `ACTIVE_SELECTIVE / direct_http / listing_complete_business_records=true`. Production acquisition is unchanged: one issuer archive HTML page only. Official PDF links remain `METADATA_ONLY_NON_BLOCKING / fetch_in_primary_pipeline=false`; no PDF production fetch or OCR was added. Canonicalizer remains `moea-archive-event-fingerprint-v1`.
- Parser/normalizer are now `moea-tender-archive-card-v2 / moea-tender-normalize-v2`. Canonical payload adds `semantic_version=2`, `deadline_time`, `deadline_kind` and explicit deadline evidence.
- Deadline semantics are fail-closed: `BID_SUBMISSION_DEADLINE` requires exact tender-submission-final-date phrase `တင်ဒါတင်သွင်းရမည့်နောက်ဆုံးရက်`; `TENDER_APPLICATION_ACCEPTANCE_CLOSE` requires the explicit application-acceptance marker `တင်ဒါလျှောက်လွှာလက်ခံမည့်ရက်` and a valid bounded date range, using the range end and end time. A form-sale-only range and unrelated generic `နောက်ဆုံး` date are not promoted.
- Live issuer audit: `2026-07-27 -> 2026-08-07 / BID_SUBMISSION_DEADLINE`; `2026-05-28 -> 2026-06-10 16:00 / TENDER_APPLICATION_ACCEPTANCE_CLOSE`; `2026-02-04 -> UNKNOWN`. The same acceptance-window pattern appears in `2024-05-17 -> 2024-06-10 16:00`, confirming the rule is not one-record-specific.
- The three current 2026 official MOEA PDFs were audited with existing `pypdf` and are text-native, but are corroboration only. The 2026-02-04 PDF contains schedule data, yet production intentionally leaves that row UNKNOWN rather than adding a listing-level PDF acquisition contract for an expired historical record.
- Read-only business-value audit that selected this slice found 28 silent/deadline-unknown OPPORTUNITY canonicals. S29/S32/S36 are embedded-image paths; S30 historical `mofa:56952` uses JPG; DOMS current attachments are scan-heavy. These remain OCR-gated rather than driving capability expansion.
- One-time listing semantic migration guard is source opt-in via `suppress_signal_on_initial_listing_semantic_enrichment=true`. It applies only when the old canonical lacks `semantic_version`, the new canonical is v2, and every non-transition business field is identical. Transition fields are only deadline/deadline-time/deadline-kind/deadline-evidence/semantic-version. Once a row is v2, subsequent deadline changes create normal `UPDATED` signals; regression coverage proves this.
- Fresh production-copy replay before merge: 9 real legacy S31 canonicals -> `changed=9 / signals_created=0 / global signals 45->45 / S31 signals 0->0 / v2 0->9`; May-28 became `2026-06-10 16:00 / TENDER_APPLICATION_ACCEPTANCE_CLOSE`. Real production DB was not mutated by the replay.
- Reviewed production Worker refresh `signalforge-refresh@S31.service` created Worker run `signalforge-20260910T083612Z-03b7f75a` and application result `MANUAL / SUCCESS / listing_complete=true / items=9 / tenders=9 / changed=9 / signals_created=0 / details_attempted=0 / backlog=0`.
- Formal production after migration: S31 semantic v2 `9/9`; S31 customer signals remain `0`; global signals remain `45`; DB quick check `ok`. Current customer opportunities remain `9 = 8 OPEN + 1 UNKNOWN`; Telegram dry-run `PASS / pending_count=0`.
- Final Bangkok state: `PASS / GREEN`; `194 canonical / 45 signals / recovery backlog 0`; acquisition and Telegram timers active.
- No DB schema, new dependency, OCR, PDF production acquisition, Browser Plane, Provider, Worker Plane, Control Plane, Beijing role, public API/webhook or Telegram delivery-identity change. Continue existing-source semantic/signal-noise audits and only introduce OCR when a current actionable opportunity provides enough value to justify it.

Evidence: `docs/verification/S31-MOEA-HTML-SEMANTIC-V2-PRODUCTION-CLOSURE-2026-09-10.md`.

## Authoritative S31 MOEA HTML Semantic v3 checkpoint — 2026-09-10

This section supersedes the S31 v2 current-state snapshot while preserving the v2 closure as historical evidence.

- Active Bangkok runtime: `1e2f5b74860d0d88b7435789a8482706eddf784e`; rollback: `038a78e195df0a8ea98f256d7bc2862e0234f6f8`; archive SHA256: `a7a2a8c01b526df93006460f020e8dc7e0acffafde7a6cbf316c6cf581fc932a`.
- PR #124 verify run `34462131786` PASS; targeted S31/contract tests `12 passed`; full suite `249 passed`; `git diff --check` PASS.
- S31 remains Bangkok `ACTIVE_SELECTIVE / direct_http / HTML-only / listing_complete_business_records=true`; PDF attachments remain metadata-only and unfetched; canonicalizer remains `moea-archive-event-fingerprint-v1`.
- Parser/normalizer are `moea-tender-archive-card-v3 / moea-tender-normalize-v3`; payload `semantic_version=3`. v3 adds exact support for `တင်ဒါလျှောက်လွှာ တင်သွင်းရမည့်နောက်ဆုံးရက်` as `BID_SUBMISSION_DEADLINE`; existing explicit bid-submission and application-acceptance rules are unchanged and remain fail-closed.
- Source-configured `listing_semantic_migration = {from_version:2,to_version:3,suppress_signal:true}` replaces the earlier one-off legacy boolean. Signal suppression occurs only for this exact increasing semantic transition and only when every non-deadline business field is identical. Same-version issuer deadline changes are not suppressed.
- Fresh live MOEA page still returns 9 selected procurement records. v3 parses `2023-06-09 -> 2023-06-27 / BID_SUBMISSION_DEADLINE`, `2026-05-28 -> 2026-06-10 16:00 / TENDER_APPLICATION_ACCEPTANCE_CLOSE`, and keeps `2026-02-04 -> UNKNOWN`.
- Fresh production-copy replay: `SUCCESS / changed=9 / signals_created=0 / global signals 45->45 / S31 signals 0->0 / v2=9 -> v3=9`; real DB untouched by this gate.
- Reviewed production Worker refresh: `signalforge-20260910T094447Z-d486be93`; application result `MANUAL / SUCCESS / items=9 / tenders=9 / changed=9 / signals_created=0 / details_attempted=0 / backlog=0`. Production after refresh: `S31 v2=0 / v3=9`, global signals `45`, S31 signals `0`, DB quick check `ok`.
- Current customer output remains `9 opportunities = 8 OPEN + 1 UNKNOWN`; Telegram dry-run `PASS / pending_count=0`. Final Bangkok: `PASS / GREEN / 194 canonical / 45 signals / recovery backlog 0`, acquisition and Telegram timers active.
- Silent `OPPORTUNITY + no signal + deadline=null` is now 25: `S26=2, S29=4, S30=1, S31=5, S32=2, S34=5, S36=6`. Full normalized HTML/business-text scan found no second record with enough explicit actionable date semantics for another safe HTML-only patch. Do not introduce OCR or PDF acquisition to reduce historical UNKNOWN counts.
- No schema, new dependency, OCR, Browser Plane, Provider, Worker Plane, Control Plane, Beijing role, public API/webhook or Telegram delivery-identity change. Next product-quality slice is the nine current customer opportunities.

Evidence: `docs/verification/S31-MOEA-HTML-SEMANTIC-V3-PRODUCTION-CLOSURE-2026-09-10.md`.

## Authoritative S39 Energy closing-context checkpoint — 2026-09-10

- Active Bangkok runtime: `195515f7a8267ca79155a973d23fff29f1ea52cc`; rollback: `1e2f5b74860d0d88b7435789a8482706eddf784e`; archive SHA256 `46b4c264dc1b8e08ddeee08ef5fd6aefaf95d543eccebca792cd20732c5459ed`.
- PR #126 verify run `34463254136` PASS; Energy targeted tests `7 passed`; full suite `250 passed`; current payload schema/normalizer/canonicalizer unchanged.
- S39 detail parser is `energy-html-plus-text-pdf-v2`. Deadline extraction no longer chooses the final date-time in the document. It requires exactly one bounded date-time with tender context before it, tolerant closing/final semantics after it and submission semantics after it; no qualifying candidate or ambiguity fails closed.
- All four reviewed text-native Energy PDF fixtures preserve the prior deadlines. Production `energy:235` evidence SHA is exactly the fixture SHA `4d2ef1694aa6a7221b1a2d46799eadba7f8edb9ef46a2045c573e07c1760c94b`.
- Current live HTML + exact production PDF parsed by branch and deployed v2 both yield `2026-09-18 13:00 / OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME` with content hash `05fcbb728ea55e100291a1d0471ee1832dcdae0355ba616c48880f957f7d9cc1`, equal to production; therefore no migration/backfill or parser-only signal.
- Reviewed S39 Worker run `signalforge-20260910T095651Z-9da87c0b`: `SUCCESS / discovered=4 / changed=0 / signals_created=0`. The scheduler had no changed candidate, so direct deployed-parser verification supplies the actual parser-live evidence and returned `hash_equal=true`.
- Final production: `PASS / GREEN`, `194 canonical / 45 signals / recovery backlog 0`, S39 signals `1`, DB quick check `ok`, Telegram pending `0`, acquisition + Telegram timers active.
- No schema, dependency, payload migration, OCR, Browser/Provider/Worker/Control/Beijing/public API change. Next product-quality issue: all eight OPEN opportunities still have `deadline_kind=null`; treat that separately and source-evidence-first.

Evidence: `docs/verification/S39-ENERGY-CLOSING-CONTEXT-PRODUCTION-CLOSURE-2026-09-10.md`.

## Authoritative S30 MOFA submission-deadline checkpoint — 2026-09-10

- Active Bangkok runtime: `5ef49168c6f6d9f18f80d02d6b593c7b1fa77d28`; rollback: `195515f7a8267ca79155a973d23fff29f1ea52cc`; archive SHA256 `f3cf2d000c56c789051b9e0920725906d3f7b5fdbf7acc4a3993c46a5c2e1f4a`.
- PR #128 CI PASS; MOFA targeted tests `8 passed`; full suite `251 passed`; `git diff --check` PASS.
- S30 detail parser is `mofa-wordpress-html-optional-text-pdf-v3`. It no longer selects the maximum PDF date-time; it accepts one distinct date-time bound to a tender-submission line, deduplicates repeated identical notice values, and fails closed on no or conflicting submission deadlines.
- Production `mofa:59800` evidence SHA `aad5b2c3e51ffc289edb5018254f364896b01d14bee8fa3be7e362e756e130c7` exactly equals the reviewed fixture. Current live HTML + exact production PDF yields `2026-09-18 16:30 / OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME` and content hash `e46bd2662665590426e91c64e2e3dad49e6baeb18a3ec41efe37c63266b9b262`, equal to production. No migration/backfill or parser-only signal.
- Reviewed S30 Worker run `signalforge-20260910T112656Z-4a72605b`: `SUCCESS / discovered=2 / changed=0 / signals_created=0`. Direct active-release parser verification supplies parser-live evidence and returned `hash_equal=true`.
- Final production: `PASS/GREEN`, `194 canonical / 45 signals / recovery backlog 0`, S30 signals `1`, DB quick check `ok`, opportunities `8 OPEN + 1 UNKNOWN`, Telegram pending `0`; acquisition and Telegram timers active.
- No schema/dependency/OCR/Browser/Provider/Worker/Control/Beijing/public API change. Next product-quality issue is read-layer `deadline_kind` enrichment for the eight OPEN opportunities where existing evidence unambiguously indicates bid submission close.

Evidence: `docs/verification/S30-MOFA-SUBMISSION-DEADLINE-PRODUCTION-CLOSURE-2026-09-10.md`.

## Authoritative read-layer deadline-kind checkpoint — 2026-09-10

- Active Bangkok runtime: `0c310c5185f899a633f91dad0d0afd72810f1974`; rollback `5ef49168c6f6d9f18f80d02d6b593c7b1fa77d28`; archive SHA256 `393eeef9fc7cbd04a4a92838dc0f41a64e93dd6627fef63b0bf20414124810ee`.
- PR #130 Actions run `34471797826` PASS; targeted opportunity/briefing/Telegram tests `20 passed`; full suite `252 passed`; `git diff --check` PASS.
- Read-layer derivation is source-scoped and canonical-first: S30/S39 reviewed PDF close evidence and S38 explicit HTML tender-close evidence derive `BID_SUBMISSION_DEADLINE`; other sources are not inferred.
- Production snapshot and deployed view both return `9 opportunities = 8 OPEN + 1 UNKNOWN`; all eight OPEN now have `BID_SUBMISSION_DEADLINE`, DOMS UNKNOWN remains null. Snapshot DB SHA stayed identical before/after read.
- Direct production DB audit confirms the eight underlying canonical `deadline_kind` fields remain null, proving no canonical migration. Global signals remain 45.
- `business_briefing` propagates the derived kind; all three current OPEN attention items render Telegram deadline label `投标截止`. Existing receipts are not replayed; Telegram dry-run pending0.
- Final Bangkok `PASS/GREEN`, `194 canonical / 45 signals / recovery backlog 0`; acquisition + Telegram timers active.
- No schema/source-parser/dependency/OCR/Browser/Provider/Worker/Control/Beijing/public API change. Next audit is MEDIUM watchlist delivery policy, not forced promotion of all medium opportunities.

Evidence: `docs/verification/READ-LAYER-DEADLINE-KIND-PRODUCTION-CLOSURE-2026-09-10.md`.

- MEDIUM watchlist delivery re-audit: NO CHANGE. On a production DB snapshot at `2026-09-12T00:00:00Z`, `industry:1034` automatically promotes to `HIGH / URGENT / ACT_NOW` inside the <=72h window and becomes the only new Telegram pending item; four later industrial MEDIUM items remain watchlist-only. Existing delivery receipts prevent replay. This validates the intended low-noise dynamic promotion path; no MEDIUM bulk delivery or extra summary channel is authorized.

## Authoritative S41 MYTEL production checkpoint — 2026-09-10

- Active Bangkok runtime: `c5c2327c2300e5d7a22fce3222552bf8c6de7cc9`; rollback `0c310c5185f899a633f91dad0d0afd72810f1974`; archive SHA256 `20d307a63c9a71ed948442e3c36fd0f52d0ee3ebb5b0ca8bd8ad0baaa270c7f1`.
- PR #132 Actions run `34475619689` PASS; S41+contract `12 passed`; full suite `260 passed`.
- S41 = `MYTEL Procurement Invitations via Viettel Global`, `ACTIVE_PRIMARY`, Bangkok `direct_http`, listing-complete official category-82 JSON feed, poll 1800s, request max 1MB, bounded `offset=0&limit=100`. Formal `viettelglobal.com.vn` strict TLS only; invalid `beta.*` certificate is never bypassed.
- Source-scoped `cloudrity_d1n_v1` performs one strict-TLS bootstrap + one D1N-cookie retry on the exact formal host only; persistent challenge fails. No generic JS renderer/anti-bot framework and no Browser/Provider dependency.
- Canonical identity is MYTEL RFP serial+year, so invitation/extension suffix drift updates one tender. Full latest reference remains payload data. Explicit Proposal submission deadline => `BID_SUBMISSION_DEADLINE`; extension-only bid-document collection close => `TENDER_FORM_SALE_CLOSE`; UNKNOWN remains fail-closed.
- Live100 audit: 361660 bytes / 100 global tender rows / 19 raw MYTEL posts -> 15 canonical RFPs; 12 latest-version 2026 canonical all actionable; 8 bid-submission + 4 document-collection close; 3 older 2025 UNKNOWN.
- Pre-merge BKK temp end-to-end: baseline changed15/signals0; second identical run changed0/signals0; DB quick_check ok.
- Production baseline Worker `signalforge-20260910T121631Z-e0b86f14`: baseline=true / SUCCESS / discovered15 / changed15 / signals0. Second Worker `signalforge-20260910T121702Z-86d64458`: baseline=false / SUCCESS / changed0 / signals0.
- Production now `209 canonical / 45 signals / recovery backlog0`; S41 canonical15/signals0; DB quick_check ok; opportunities remain `8 OPEN + 1 UNKNOWN`; Telegram pending0. Latest S41 evidence `application/json / 361660 bytes / DIRECT_HTTP / sha256 a2c3bb54169f8e30fd27a6d82e8cbb53f9451e2efe6e7fa89fe264d45034cb3a`.
- S41 source/fetch/freshness/parse health GREEN; 2/2 business-processing successes; next_due `2026-09-10T12:47:03.166034Z`; acquisition + Telegram timers active.
- Portfolio policy after activation: Technical GREEN != Business Yield. Do not add another source merely to increase count; prioritize measured strategic coverage/yield and exclude known historical parser-normalization noise from productivity judgments.

Evidence: `docs/verification/S41-MYTEL-SOURCE-ONBOARDING-PRODUCTION-CLOSURE-2026-09-10.md`.

## S42 ATOM source audit checkpoint — DEFERRED — 2026-09-10

- No S42 production source is added. ATOM remains a strategic coverage gap but fails the current public-acquisition-surface gate.
- Official ATOM public pages confirm supplier/supply-chain operations, but bounded searches found no official public tender/RFP/RFQ listing or repeatable anonymous supplier bidding feed.
- Bangkok strict-TLS `https://www.atom.com.mm/sitemap.xml`: HTTP 200 / 131679 bytes; keyword counts `tender=0, procurement=0, supplier=0, rfp=0, rfq=0, sourcing=0`. `robots.txt`: HTTP 200 / 24 bytes with the same zero procurement keywords. `sitemap_index.xml`: HTTP 404.
- This is not evidence that ATOM has no procurement activity; private/invitation-only sourcing may exist. It is evidence that the reviewed public web does not currently provide a maintainable SignalForge production source.
- Do not add registry/parser/Browser/Provider/credentialed portal automation merely because ATOM is strategically important. Re-open only with an official public procurement surface, a real current opportunity revealing a stable official URL, or separately authorized credentialed-access design.
- Runtime remains `c5c2327c2300e5d7a22fce3222552bf8c6de7cc9`; no production deploy or database/delivery change is required.

Evidence: `docs/verification/S42-ATOM-SOURCE-AUDIT-DEFERRED-2026-09-10.md`.

## Authoritative source-portfolio business-yield checkpoint — 2026-09-10

- Production runtime remains `c5c2327c2300e5d7a22fce3222552bf8c6de7cc9`; this audit makes no runtime/source-registry/database/delivery change.
- Current production = `209 canonical / 45 raw signals / recovery backlog0`. Effective business-signal accounting for portfolio decisions is **24**: exclude 20 known S25 normalization-noise UPDATED rows and the one preserved S13 parser-only historical UPDATED (`mpt:CCO-2026-001`). No history is deleted or rewritten.
- Effective yield observed: S13=10, S38=6, S20=3, S26=2, S08A=1, S30=1, S39=1; all other active sources currently 0.
- All active sources are baseline-complete with `consecutive_failures=0` at the audit snapshot. First production runs span only 2026-09-02 through 2026-09-10, so zero signal is not sufficient evidence for demotion.
- Provisional analytical tiers only: Core/proven = `S13,S20,S30,S38,S39`; Strategic Watch = `S16,S21,S22,S27,S34,S35,S41`; Context/regulatory/selective = `S05A,S07,S08A,S10,S12,S26`; Observation/low-yield candidates = `S25,S28,S29,S31,S32,S33,S36,S37,S40`.
- These tiers do not replace registry `ACTIVE_PRIMARY/ACTIVE_SELECTIVE`, priority, polling, Direct HTTP/Provider role or scheduler behavior. No source is disabled, downgraded or slowed by this audit.
- Default pruning/promotion decision gate: 30 days of production observation per source. Earlier review is allowed only for concrete repeated health failure, recurring false/duplicate signals, a missed current high-value opportunity, repeated high-value yield, or evidence the issuer surface is structurally irrelevant/result-only.
- Source-count expansion remains gated: S41 passed because a trustworthy official procurement feed exists; S42 ATOM is deferred because no qualifying public procurement surface was found.

Evidence: `docs/verification/SOURCE-PORTFOLIO-BUSINESS-YIELD-AUDIT-2026-09-10.md`.

## Authoritative S39 Energy multi-reference read-layer checkpoint — 2026-09-10

- Active Bangkok runtime: `20f2a7e8cd92671e98155bf963a291cd9a5ec3ba`; rollback `c5c2327c2300e5d7a22fce3222552bf8c6de7cc9`; archive SHA256 `7d2f8ad0e584d8bc703c5bb6d6e75428b2e13c5f13b9ffbd5878735b3e5a47b6`.
- PR #136 Actions run `34481911436` PASS; targeted opportunities tests `8 passed`; full suite `262 passed`.
- Pure read-layer enrichment only. Canonical `reference_numbers` always wins. Derived bundle is authorized only for S39 + reviewed Energy text-PDF completeness + at least two distinct exact `DMP/L-xxx(yy-yy)` references. Other issuer reference grammars remain fail-closed/null.
- Production-copy gate: `energy:235` derives 11 DMP references; briefing propagates all 11; Telegram renders them in its existing reference line; DB SHA `c07779fb55e1939d958c71784c96e5bf1ef196500dc513fe8329839f4dc1885f` unchanged before/after read.
- Post-deploy live `energy:235`: `reference_count=11`, evidence `OFFICIAL_TEXT_NATIVE_PDF_SCOPE_DMP_REFERENCE_PATTERN`; underlying canonical payload still has null `reference_numbers/reference_count`.
- Final production: `PASS/GREEN / 209 canonical / 45 signals / recovery backlog0 / opportunities 8 OPEN + 1 UNKNOWN / Telegram pending0 / DB quick_check ok`; acquisition and Telegram timers active.
- No source refresh, DB migration, parser/canonical/signal/qualification/delivery-policy/registry/Browser/Provider/Worker/Control/Beijing change.

Evidence: `docs/verification/S39-ENERGY-MULTI-REFERENCE-READ-LAYER-PRODUCTION-CLOSURE-2026-09-10.md`.

## Authoritative multi-reference evidence-label hotfix checkpoint — 2026-09-10

- Active Bangkok runtime: `3700e675327cd599797fc0eaef8ddb8d0e289005`; rollback `20f2a7e8cd92671e98155bf963a291cd9a5ec3ba`; archive SHA256 `521424aa404b32b1af54257f50a6d0c8da42e8c65e4fcda1d4cc1af115d7da82`.
- PR #138 Actions run `34482888173` PASS; targeted qualification/opportunity tests `12 passed`; full suite `263 passed`.
- Qualification v1 decision logic is unchanged. Multi-reference explanation now follows evidence provenance: DOMS HTML title -> `MULTI_REFERENCE_HTML_TITLE`; S39 official PDF scope -> `MULTI_REFERENCE_OFFICIAL_PDF_SCOPE`; other provenance -> `MULTI_REFERENCE_EVIDENCE`.
- Live `energy:235` remains `A/HIGH`, reference_count=11; `doms:12735` retains its HTML-title reason. `qualification_policy_version=1`.
- Final production: `209 canonical / 45 signals / 8 OPEN + 1 UNKNOWN / backlog0 / Telegram pending0 / DB quick_check ok`; both timers active. No source refresh or state migration.

Evidence: `docs/verification/MULTI-REFERENCE-EVIDENCE-LABEL-HOTFIX-PRODUCTION-CLOSURE-2026-09-10.md`.
