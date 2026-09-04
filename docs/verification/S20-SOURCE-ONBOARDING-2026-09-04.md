# S20 MOEP Main Tender Hub — Source Onboarding Verification

Date (Asia/Yangon): 2026-09-04
Phase: `PRE_PRODUCTION`
Result: **READY_FOR_PR / NOT YET PRODUCTION-COMPLETE**

## Decision

S20 MOEP Main Tender Hub is implemented as an **HTML-first ACTIVE_SELECTIVE** SignalForge source.

The primary pipeline remains:

```text
Bangkok SignalForge
-> Direct HTTP category HTML
-> Direct HTTP detail HTML
-> EvidenceEnvelope
-> MOEP parser
-> ProcessingRecord
-> Canonical / Dedup / Signal
```

Advertised PDF attachments are **metadata-only and non-blocking**. No PDF parser, Browser, remote Provider, Mac production path, Beijing acquisition, Redis/Celery, distributed queue or new Worker/Control ABI is introduced.

## Fresh source audit

Stable official category endpoint:

```text
https://moep.gov.mm/mm/ignite/page/62
```

The previously guessed `/mm/ignite/tender` endpoint now returns 404 and is not used.

The category page is a stable tender listing with pagination (`/62/5`, `/62/10`, etc.). The first page currently exposes five latest items with:

- title;
- summary;
- issuer;
- publication date;
- detail URL.

Current leading content ids:

```text
7141 — 2026-09-02 — EPGE
7124 — 2026-08-27 — DHPI
7121 — 2026-08-25 — EPGE
7112 — 2026-08-24 — DPTSC
7103 — 2026-08-18 — YESC
```

## Bangkok transport matrix

Using the actual SignalForge production Direct HTTP fetcher identity from Bangkok:

```text
category list: 1/1 OK
latest detail HTML: 5/5 OK
latest advertised PDFs: 0/5 OK; all five returned HTTP 404
```

Therefore:

> HTML source health and attachment health must remain separate.

A broken official attachment must not convert a healthy tender discovery/detail source into acquisition failure.

## Business-information boundary

Current HTML reliably identifies a tender event and issuer, but business qualification depth varies.

The latest five HTML pages reliably expose issuer/date/summary/attachment metadata, while detailed equipment lots and closing dates are often absent from HTML. Some older pages contain richer scope directly in HTML, but this is not stable enough to claim full detail coverage.

The implementation therefore records:

```text
detail_completeness=HTML_PARTIAL_ATTACHMENT_METADATA
```

Unknown fields, including current closing dates, remain `null`. SignalForge does not infer them from publication date, attachment filename or surrounding text.

## Attachment policy

Registry policy:

```text
mode=METADATA_ONLY_NON_BLOCKING
current_health=DEGRADED_HTTP_404
fetch_in_primary_pipeline=false
```

The parser records only attachment name and official URL. Unit/engine regression proves the primary fetcher is never called for the PDF.

A future PDF supplementary adapter is allowed only after official attachments become retrievable and a text-native/scan extraction gate is run. PDF failure must stay independent from HTML source health.

## Canonical identity

MOEP current pages do not expose a stable business tender number in HTML. The implementation uses issuer-native content id plus publication date:

```text
moep:<content_id>:<publication_date>
```

Example:

```text
moep:7141:2026-09-02
```

The legacy required `reference_no` is explicit issuer-record metadata:

```text
MOEP-CONTENT-7141
reference_no_kind=issuer_record_id
```

This identity remains stable across HTML summary/body/attachment edits so those edits become `UPDATED`, not duplicate `NEW`, signals.

## Discovery boundary

Initial production discovery intentionally monitors the latest official category page only, currently five items.

Reason:

- poll interval is 15 minutes;
- S20 is `ACTIVE_SELECTIVE` rather than a claimed exhaustive archive crawler;
- no evidence yet shows more than five new tenders can displace unseen items inside one normal collection/recovery window;
- full pagination would widen recovery/crawl behavior without current evidence.

If real production history demonstrates page-displacement loss risk, paginated discovery becomes an evidence-triggered follow-up gate.

## Source policy

```text
source_id=S20
adapter=moep
role=ACTIVE_SELECTIVE
engine=direct_http
network_zone=myanmar-international
egress_profile=mm-intl-datacenter
discovery_url=https://moep.gov.mm/mm/ignite/page/62
poll_interval_seconds=900
baseline_detail_limit=5
delta_detail_limit=5
first_baseline_customer_signal=false
source_policy_version=1
```

## Live parser verification

The new parser was executed against current official HTML after implementation:

```text
listing entries=5
latest detail parsed=5/5
```

The parser recovered content ids 7141/7124/7121/7112/7103, their issuers and publication dates, while leaving unavailable deadlines as `null` and preserving attachment names as metadata.

## Regression proof

Targeted affected suite:

```text
20/20 PASS
```

Full CI-equivalent SignalForge suite:

```text
33/33 PASS
```

Critical behavior regression:

```text
baseline -> canonical rows created / signals=0
PDF URL advertised -> never fetched by primary pipeline
same content id + same publication date + changed HTML scope -> UPDATED once
canonical identity -> unchanged
```

Release hygiene:

```text
registry JSON validation                    PASS
python3 -m compileall -q signalforge tests PASS
sh -n bin/signalforge                      PASS
sh -n deploy/deploy-signalforge-release.sh PASS
git diff --check                           PASS
```

## Production acceptance after merge

S20 remains not production-complete until the exact merged SHA passes:

1. pause Bangkok SignalForge timer through the reviewed Control Plane verb;
2. snapshot S13/S21/S22/global canonical/signal/Worker state;
3. deploy the exact merged SHA to Bangkok only;
4. confirm Beijing remains strict SignalForge zero-footprint;
5. run reviewed `signalforge-refresh S20` once;
6. prove first S20 baseline creates zero customer signals;
7. prove one manual refresh correlates to exactly one Worker application Run;
8. verify S20 requests/attempts/evidence/processing/canonical rows are durable;
9. verify no PDF acquisition attempt exists for S20;
10. verify S13/S21/S22 business state remains intact;
11. verify SQLite `quick_check=ok` and both Worker doctors PASS;
12. verify Beijing rejects `signalforge-refresh S20`;
13. restore timer enabled / active / waiting and inspect any persistent due wrapper;
14. promote this evidence to `PRODUCTION / PASS` and update `CHECKPOINT.md` / `GOAL.md`.
