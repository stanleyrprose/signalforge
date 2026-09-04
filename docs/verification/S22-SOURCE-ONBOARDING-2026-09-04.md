# S22 Inland Water Transport — Source Onboarding Verification

Date (Asia/Yangon): 2026-09-04
Phase: `PRODUCTION`
Result: **PASS / PRODUCTION COMPLETE**

## Decision

S22 Inland Water Transport (IWT) is production-enabled as the third SignalForge Myanmar source after S13 MPT and S21 Myanma Railways.

It stays inside the frozen v1.5 architecture:

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

No Worker ABI, Control Plane verb, Browser/Browserless, remote Provider, Mac production dependency, Beijing acquisition, PDF parser, Redis/Celery, distributed queue or automatic cross-zone failover was introduced.

## Release

- implementation PR: `#16 feat: onboard Inland Water Transport S22`
- PR CI `verify`: PASS
- SignalForge production release: `9ec2b133ca1c3339abccf34c5f5c86cecd3e6023`
- immediate rollback release: `52c9ab5b5e5643014e1b55a634cc5fbe26c0ebac`
- Worker runtime/provider: `0a53558c9233622c69b083d61bed596cbedc0857`
- Control Plane: `64ab3a907bb8a18808839176208023a5de976b55`

The live Bangkok `/srv/signalforge/active` symlink was verified to resolve to the exact merged SHA.

## Fresh transport re-audit

Canonical discovery endpoint:

```text
https://iwt.gov.mm/tenders
```

A bare Python urllib request using the library-default User-Agent returned HTTP 403. This was not a Direct HTTP failure: the frozen SignalForge fetcher already uses its own explicit application identity:

```text
User-Agent: SignalForge/0.1 (+commercial-signal-monitor)
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
```

The actual SignalForge fetcher succeeded from the Myanmar-side development path with a 97,758-byte HTML response.

Bangkok production egress using that same SignalForge fetcher completed three consecutive listing reads:

```text
97758 bytes / 0.142s
97758 bytes / 0.119s
97758 bytes / 0.078s
```

Bangkok also fetched the newest audited detail node 1038 and its HTML contained both the closing-date field and vessel-tender attachment metadata.

Conclusion:

> **LOCAL_BANGKOK + DIRECT_HTTP = PASS**

The default-urllib 403 is an HTTP client-identity policy difference, not a Browser/JS-render requirement. No Browser gate was triggered and no browser-like spoofing was added. If the real SignalForge fetcher later receives 403, the frozen policy remains `HTTP_403 -> REVIEW`.

## Live source shape

The new parser was run directly against the current issuer listing and found 20 tender records.

The current leading records included:

```text
1038 — 2026-08-25T08:51:07Z
1037 — 2026-07-25T04:12:54Z
1036 — 2026-04-24T05:00:00Z
1035 — 2026-04-10T04:58:02Z
1034 — 2025-11-21T08:35:27Z
971  — 2025-05-23T06:45:41Z
```

All four audited 2026 detail nodes parsed successfully from live issuer HTML:

```text
1038: publication=2026-08-25 / deadline=2026-11-03
1037: publication=2026-07-25 / deadline=2026-08-25
1036: publication=2026-04-24 / deadline=2026-05-14
1035: publication=2026-04-10 / deadline=2026-05-06
```

Observed live attachments:

```text
1038: IWT_1 Costal Vessel Tender 25-8-2026.pdf
1037: IWT CE Open Tender_25-7-2026.pdf
1036: CS Tender_24-4-2026.pdf
1035: CS Tender Data_10-4-2026.pdf
```

## Adapter / identity contract

IWT is a deterministic Type-A HTML source:

```text
/tenders HTML
-> N issuer node URLs
-> one tender-node HTML
-> zero/one IwtTender
-> one EvidenceEnvelope / ProcessingRecord
-> one canonical upsert
```

The detail parser requires the issuer page to identify itself as Drupal content type `node--type-tenders`; non-tender pages fail closed.

IWT currently does not expose a true business tender/reference number in HTML. The implementation therefore does not pretend the Drupal node id is a tender number.

The required legacy DB field is explicit issuer-record metadata:

```text
reference_no=IWT-NODE-1038
reference_no_kind=issuer_record_id
```

Canonical identity is:

```text
iwt:<source_record_id>:<publication_date>
```

Example:

```text
iwt:1038:2026-08-25
```

The identity is stable across body, deadline and attachment edits, so those changes produce `UPDATED` rather than duplicate `NEW` signals.

## Closing-time semantics

IWT exposes machine-readable UTC time while displaying Myanmar local time. For node 1038:

```text
source UTC:   2026-11-03T03:30:00Z
Yangon local: 2026-11-03T10:00:00+06:30
```

The adapter preserves both date-level compatibility and commercially important time detail:

```text
deadline=2026-11-03
deadline_datetime_utc=2026-11-03T03:30:00Z
deadline_datetime_local=2026-11-03T10:00:00+06:30
```

## PDF boundary

HTML already supplies identity, scope and closing time. S22 therefore records only:

```text
attachment_name
attachment_url
```

No PDF is fetched or parsed by the S22 adapter. This preserves the audit rule that PDF quality is separate from HTML source health and avoids widening scope without a demonstrated business-data gap.

## Latest-detail probe

IWT listing timestamps are publication timestamps, not reliable modification timestamps. Existing tender deadlines or bodies may change without a new listing timestamp.

For tender-only discovery sources, the existing bounded low-frequency detail probe now chooses the newest currently discovered tender before static bootstrap seeds.

Regression proof:

```text
canonical=iwt:1038:2026-08-25
deadline=2026-11-03

later detail probe:
deadline=2026-11-10
canonical unchanged
signal=UPDATED
```

This also improves S21 tender-only probing and does not change MPT behavior.

## Pre-production verification

Targeted S22 + directly affected regression suite:

```text
16/16 PASS
```

CI-equivalent SignalForge unit suite:

```text
29/29 PASS
```

Release hygiene:

```text
registry JSON validation                          PASS
python3 -m compileall -q signalforge tests       PASS
sh -n bin/signalforge                            PASS
sh -n deploy/deploy-signalforge-release.sh       PASS
git diff --check                                 PASS
```

## Controlled production rollout

The production timer was paused through the reviewed Control Plane verb before deployment.

Frozen pre-deploy state:

```text
release=52c9ab5b5e5643014e1b55a634cc5fbe26c0ebac
canonical_items=61
signals=10
scheduler_runs=128
acquisition_requests=132
acquisition_attempts=132
evidence_envelopes=132
processing_records=132
failed_runs=0
recovery_backlog=0
Worker SignalForge Runs=381
S13=GREEN
S21=GREEN
timer=disabled/inactive
```

The exact merged SHA was deployed from a Git archive to Bangkok only. Deploy result:

```text
deployment=success
release=9ec2b133ca1c3339abccf34c5f5c86cecd3e6023
previous=52c9ab5b5e5643014e1b55a634cc5fbe26c0ebac
timer_preexisting=0
```

Post-deploy manifest:

```text
verb_manifest_version=1
active_source_ids=[S13,S21,S22]
```

## First S22 production baseline — PASS

Reviewed invocation:

```text
signalforge-refresh S22
```

Live result:

```text
trigger_kind=MANUAL
baseline=1
status=SUCCESS
details_attempted=4
details_succeeded=4
tenders_parsed=4
changed=4
signals_created=0
worker_run_id=signalforge-20260904T004652Z-d4992f14
```

Business state:

```text
canonical_items: 61 -> 65
signals:         10 -> 10
scheduler_runs: 128 -> 129
```

Therefore the first IWT baseline created four durable canonical records and zero customer signals.

## Acquisition / evidence persistence — PASS

The baseline fetched one discovery page plus four detail pages:

```text
S22 acquisition_requests=5
S22 acquisition_attempts=5
S22 evidence_envelopes=5
S22 processing_records=5
S22 canonical_items=4
S22 signals=0
PRAGMA quick_check=ok
```

Per-source state during the paused window remained:

```text
S13 canonical/signals=16/10
S21 canonical/signals=45/0
S22 canonical/signals=4/0
```

No S13/S21 business-state pollution occurred.

## Worker cardinality / correlation — PASS

Before S22 baseline:

```text
Worker SignalForge Runs=381
```

After S22 baseline:

```text
Worker SignalForge Runs=382
latest Worker Run=signalforge-20260904T004652Z-d4992f14 / SUCCESS
```

The S22 scheduler row stores that same Worker Run ID. Thus one reviewed manual source refresh created exactly one Worker operational Run while five acquisition attempts and four business items stayed internal SignalForge state.

## Topology / Worker verification — PASS

Bangkok Worker doctor: PASS.

Beijing Worker doctor: PASS.

Beijing remained strict zero-footprint:

```text
/srv/signalforge absent
```

and the reviewed S22 refresh verb on Beijing failed closed:

```text
126 / DENY: SignalForge is Bangkok-only
```

## Timer restoration / Gate Z — PASS

`signalforge-resume` restored:

```text
signalforge-run-due.timer=enabled/active/waiting
signalforge-run-due.service=inactive/dead after completion
Result=success
ExecMainStatus=0
```

The persistent timer immediately created one Worker wrapper:

```text
Worker SignalForge Runs: 382 -> 383
```

S13 and S21 had become due during the controlled pause, so that one wrapper processed two SignalForge business jobs:

```text
S13 POLL=SUCCESS / details 1/1 / signals 0
S21 POLL=SUCCESS / no pending detail / signals 0
scheduler_runs: 129 -> 131
```

S22 was not run again because its next due time had not arrived.

This reconfirms Gate Z:

> one Worker wrapper Run can contain N due SignalForge source jobs; source jobs and acquisition attempts do not become Worker Runs.

## Final production state

```text
SignalForge release=9ec2b133ca1c3339abccf34c5f5c86cecd3e6023
active sources=S13,S21,S22
SignalForge health=GREEN
S13 health=GREEN
S21 health=GREEN
S22 health=GREEN
canonical_items=65
signals=10
scheduler_runs=131
acquisition_requests=140
acquisition_attempts=140
evidence_envelopes=140
processing_records=140
Worker SignalForge Runs=383
failed_runs=0
recovery_backlog=0
SQLite quick_check=ok
Bangkok Worker doctor=PASS
Beijing Worker doctor=PASS
Beijing SignalForge footprint=ABSENT
timer=enabled/active/waiting
```

## Conclusion

S22 Inland Water Transport onboarding is **PASS / PRODUCTION COMPLETE**.

It proves a third issuer shape can run under the same local SignalForge acquisition/Worker boundary while preserving baseline signal suppression, source-specific canonical identity, full closing-time metadata, Bangkok-only placement, Direct HTTP first, and one-Worker-wrapper-to-many-business-jobs Gate Z semantics.
