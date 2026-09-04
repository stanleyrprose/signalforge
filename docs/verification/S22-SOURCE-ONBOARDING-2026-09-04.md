# S22 Inland Water Transport — Source Onboarding Verification

Date (Asia/Yangon): 2026-09-04
Phase: `PRE_PRODUCTION`
Result: **READY_FOR_PR / NOT YET PRODUCTION-COMPLETE**

## Decision

S22 Inland Water Transport (IWT) is the next Myanmar source expansion after S21 Myanma Railways.

The source stays inside the frozen v1.5 architecture:

```text
Bangkok SignalForge
-> Source Acquisition Policy
-> AcquisitionRequest / AcquisitionAttempt
-> LOCAL_BANGKOK Direct HTTP
-> EvidenceEnvelope
-> IWT source adapter
-> ProcessingRecord
-> Canonical / Dedup / Signal
```

No Worker ABI, Control Plane verb, Browser/Browserless, remote Provider, Mac production dependency, Beijing acquisition, PDF parser, Redis/Celery, distributed queue or automatic cross-zone failover is introduced.

## Why S22

The completed engineering source audit classified IWT as:

```text
GREEN-CANDIDATE / PARSE-STRONG
Type A — structured HTML detail
```

The current source exposes enough business information directly in HTML for initial opportunity qualification:

- tender title;
- business scope/body;
- post date;
- closing date/time;
- attachment metadata.

PDF quality remains an independent future dimension and is not required for this HTML source onboarding.

## Fresh transport re-audit

Canonical discovery endpoint:

```text
https://iwt.gov.mm/tenders
```

A bare Python `urllib` request using the library-default User-Agent received HTTP 403 from the current edge policy.

This did **not** represent a Direct HTTP or Browser failure. SignalForge production does not use the library-default identity; the frozen fetcher already sends:

```text
User-Agent: SignalForge/0.1 (+commercial-signal-monitor)
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
```

Using the actual SignalForge fetcher from the Myanmar-side development path returned:

```text
HTTP 200
body=97758 bytes
```

Using the production SignalForge fetcher identity from Bangkok returned three sequential successful reads:

```text
97758 bytes / 0.142s
97758 bytes / 0.119s
97758 bytes / 0.078s
```

The current node 1038 detail was also fetched from Bangkok with the production fetcher and contained both:

```text
field-name-field-close-date-tender
IWT_1 Costal Vessel Tender 25-8-2026
```

Conclusion:

> **LOCAL_BANGKOK + DIRECT_HTTP = PASS**

No Browser/JS-render capability gate is triggered.

## Current live source shape

The current listing parser was executed against live issuer HTML and found 20 tender records on the page.

The first six records were:

```text
1038 — 2026-08-25T08:51:07Z
1037 — 2026-07-25T04:12:54Z
1036 — 2026-04-24T05:00:00Z
1035 — 2026-04-10T04:58:02Z
1034 — 2025-11-21T08:35:27Z
971  — 2025-05-23T06:45:41Z
```

The four 2026 detail pages were fetched and parsed from the live issuer site:

```text
node 1038: publication=2026-08-25, deadline=2026-11-03
node 1037: publication=2026-07-25, deadline=2026-08-25
node 1036: publication=2026-04-24, deadline=2026-05-14
node 1035: publication=2026-04-10, deadline=2026-05-06
```

Observed live attachments:

```text
1038: IWT_1 Costal Vessel Tender 25-8-2026.pdf
1037: IWT CE Open Tender_25-7-2026.pdf
1036: CS Tender_24-4-2026.pdf
1035: CS Tender Data_10-4-2026.pdf
```

The current listing now correctly exposes node 1038 as the newest item. Earlier cached/search views that omitted 1038 were stale and are not used as production discovery truth.

## Source adapter contract

IWT is one issuer detail page -> one business tender:

```text
/tenders HTML
-> N issuer node URLs
-> one node detail HTML
-> zero/one IwtTender
-> one EvidenceEnvelope / ProcessingRecord
-> one canonical upsert
```

The parser is deterministic HTML extraction and requires the issuer page to identify itself as Drupal content type `node--type-tenders`.

Non-tender pages fail closed.

## Canonical identity

Current IWT HTML does not expose a business tender/reference number.

The implementation therefore does **not** pretend the Drupal node id is a real tender number. The legacy required `reference_no` field stores an explicit synthetic issuer-record token:

```text
IWT-NODE-1038
```

and the payload records:

```text
reference_no_kind=issuer_record_id
```

Canonical identity uses issuer-native record id plus publication date:

```text
iwt:<source_record_id>:<publication_date>
```

Example:

```text
iwt:1038:2026-08-25
```

This is stable across body, attachment and deadline edits so those changes become `UPDATED` signals rather than duplicate `NEW` tenders.

It is not URL-only identity: the issuer namespace, issuer-native immutable record id and publication date are explicit canonical components.

## Deadline/time semantics

IWT Drupal exposes machine-readable UTC datetimes while displaying Myanmar local time.

Example node 1038:

```text
source UTC:   2026-11-03T03:30:00Z
Yangon local: 2026-11-03T10:00:00+06:30
```

SignalForge stores:

```text
deadline=2026-11-03
deadline_datetime_utc=2026-11-03T03:30:00Z
deadline_datetime_local=2026-11-03T10:00:00+06:30
```

This avoids losing the commercially important closing time while preserving the existing canonical table's date-level `deadline` field.

## Attachment boundary

The HTML adapter records only:

```text
attachment_name
attachment_url
```

It does **not** fetch, parse or score the PDF during S22 onboarding.

Reason:

- HTML already provides identity, scope and closing time;
- the existing audit explicitly separated PDF quality from HTML source health;
- adding PDF extraction without a concrete business-data gap would unnecessarily widen v1.5 scope.

A future PDF supplementary adapter remains evidence-triggered.

## Latest-detail probe behavior

IWT listing timestamps are publication timestamps, not reliable modification timestamps. A deadline/body change can therefore occur without changing the listing timestamp.

For tender-only discovery sources, the bounded low-frequency detail health probe now chooses the **newest currently discovered tender** before static bootstrap seeds.

This improves both S21 and S22 without changing MPT behavior.

The regression fixture proves:

```text
baseline canonical = iwt:1038:2026-08-25
deadline             = 2026-11-03

later detail probe:
deadline             = 2026-11-10
canonical            = unchanged
signal               = UPDATED
```

The probe remains bounded to one detail page at the existing one-hour parse-probe interval when there is no normal pending candidate.

## Source policy

```text
source_id=S22
adapter=iwt
role=ACTIVE_PRIMARY
network_zone=myanmar-international
engine=direct_http
egress_profile=mm-intl-datacenter
source_policy_version=1
poll_interval_seconds=900
baseline_lookback_days=120
baseline_detail_limit=10
delta_detail_limit=10
first_baseline_customer_signal=false
```

Bootstrap seeds preserve the four audited 2026 nodes:

```text
https://iwt.gov.mm/my/node/1038
https://iwt.gov.mm/my/node/1037
https://iwt.gov.mm/my/node/1036
https://iwt.gov.mm/my/node/1035
```

Failure policy preserves v1.5 semantics:

```text
HTTP_403 -> REVIEW
TLS_FAILURE -> FAIL
JS_RENDER_REQUIRED -> REVIEW_CAPABILITY
PARSER_DRIFT -> REAUDIT
```

The fresh default-urllib 403 does not weaken this policy: production SignalForge fetches succeeded using the already-frozen application User-Agent. If the production fetcher itself begins returning 403, the source will enter REVIEW rather than silently spoofing a browser identity.

## Implementation

Added:

- `signalforge/iwt.py` — Drupal tender listing/detail parser, issuer-record identity, Myanmar-local time normalization, attachment metadata;
- IWT source adapter registration;
- S22 active Source Registry policy;
- IWT listing/detail fixtures;
- parser + engine regression tests;
- CI inclusion for `tests.test_iwt`.

Small engine change:

- tender-only sources use the newest discovery item for the existing bounded parse/detail probe before falling back to static seed URLs.

No acquisition schema, Worker schema, Worker ABI, Control Plane grammar or deployment topology changed.

## Pre-production verification

Targeted S22 + directly affected regression suite:

```text
16/16 PASS
```

CI-equivalent SignalForge unit suite:

```text
29/29 PASS
```

Release checks:

```text
python3 -m json.tool registry/Source-Registry-v1.yaml PASS
python3 -m compileall -q signalforge tests        PASS
sh -n bin/signalforge                            PASS
sh -n deploy/deploy-signalforge-release.sh       PASS
git diff --check                                 PASS
```

The new parser was also run against current live IWT listing plus the four 2026 detail pages, not only fixtures.

## Production acceptance after merge

S22 remains **not production-complete** until all of the following pass on the exact merged SHA:

1. pause the production timer through the reviewed Control Plane verb;
2. snapshot S13/S21/canonical/signal/Worker Run state;
3. deploy the exact merged SignalForge SHA to Bangkok only;
4. verify Beijing remains strict SignalForge zero-footprint;
5. execute reviewed `signalforge-refresh S22` once to establish the first baseline;
6. prove the S22 baseline creates zero customer signals;
7. prove exactly one Worker application Run correlates to the S22 manual baseline invocation;
8. verify S22 acquisition/evidence/processing rows and canonical rows are durable;
9. verify S13 and S21 business state remains intact;
10. verify SQLite `quick_check=ok`;
11. verify Bangkok + Beijing Worker doctors remain PASS;
12. verify Beijing rejects `signalforge-refresh S22` with the Bangkok-only control-plane guard;
13. restore `signalforge-run-due.timer` to enabled / active / waiting;
14. record final live onboarding evidence and update `CHECKPOINT.md` / `GOAL.md`.

Until those steps pass, this record remains `PRE_PRODUCTION`.
