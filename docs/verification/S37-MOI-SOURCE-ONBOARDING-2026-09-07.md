# S37 Ministry of Information Ministerial Office Procurement Announcements — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRODUCTION
Result: PRODUCTION / GREEN — LIVE VERIFIED 2026-09-07

## Fresh audit decision

S37 was selected by current business value plus acquisition quality. The audit also used the Mac Browser Plane through CodexPro as an explicit secondary acquisition/verification surface; that did **not** change the frozen SignalForge unattended-production boundary.

### High-value deferred candidate: Ministry of Industry

The Ministry of Industry now serves its current official portal at:

```text
https://www.industrymsme.gov.mm/
```

Mac Browser Plane was invoked locally through CodexPro and returned:

```text
browserctl doctor       = READY
C0 homepage             = HTTP 200 / text/html / 277,435 bytes
C0 /announcements       = HTTP 200 / text/html / 88,309 bytes
production_enabled      = false
remote_invocation       = false
```

The current Industry announcements page contains many commercially strong buyer-side tenders, including steel-factory reagents/gases, raw and production materials, heavy-machinery renovation, Schneider relay/pump-house equipment, Fluid Control Unit equipment, 1,000 tons of HMS-1 steel scrap procurement, construction, laboratory equipment and chemicals.

Bangkok resolves the new host but repeatedly times out opening the HTTPS/TLS connection. Therefore the current state is:

```text
Mac Browser Plane C0 = GREEN
Bangkok Direct HTTP  = RED / CONNECT_TIMEOUT
```

This is a materially better candidate than the old `industry.gov.mm` endpoint, but it is **not** promoted in S37. It remains a high-priority Mac-provider/manual-P0/future-provider-contract candidate. No TLS bypass, proxy substitution or unattended Mac invocation was added.

## Selected source: MOI Ministerial Office

Official mixed department-announcement board:

```text
https://www.moi.gov.mm/department-announcement
```

Bangkok strict Direct HTTP verification:

```text
3 / 3 fetches = HTTP 200
media type    = text/html
artifact      = 45,228 bytes
```

The current page exposes one MOI Ministerial Office tender:

```text
https://www.moi.gov.mm/announcements/81536
```

The detail page was also 3/3 HTTP 200 (`41,575` bytes) from Bangkok.

## Issuer / dedup boundary

The MOI board is a mixed publication surface and can contain announcements originating from other ministries or departments. S37 therefore does not treat the MOI website itself as proof that MOI is the buyer.

A discovery card is selected only when its title simultaneously proves:

```text
ပြန်ကြားရေးဝန်ကြီးဌာန    Ministry of Information
AND
ဝန်ကြီးရုံး                Ministerial Office
AND
opportunity-stage tender semantics
```

Award/result/winner stages are excluded.

This intentionally prevents MOI reposts of other agencies' tenders from entering S37 and avoids creating a new cross-issuer equivalence/dedup contract.

The raw board is mixed, while the **adapter discovery output is tender-only**. `discovery_is_tender_only=true` describes the parser output consumed by the detail scheduler, not the unfiltered webpage.

## Identity

The issuer page exposes native Drupal node identity:

```text
/announcements/81536
```

Canonical contract:

```text
source_record_id = 81536
reference_no     = MOI-NODE-81536
canonical_key    = moi:81536
```

No title/date fingerprint is required.

## HTML business evidence

The selected detail HTML directly states:

- fiscal year 2026-2027;
- purchase of four types of office equipment and one type of furniture for the MOI Ministerial Office;
- tender-form sale window `2026-04-20` through `2026-05-11`;
- final submission deadline `2026-05-15 16:30`;
- Office No.7, Ministry of Information, Nay Pyi Taw and contact information.

The listing independently displays `Apr 09, 2026`; the detail displays `04/09/2026`. S37 interprets the detail site's numeric date as `MM/DD/YYYY`, yielding `2026-04-09`, and fixtures lock the listing/detail consistency.

No tender PDF, scan or image is required for the business event.

## Epistemic contract

```text
publication_date = 2026-04-09
sale_start       = 2026-04-20
sale_end         = 2026-05-11
deadline         = 2026-05-15
```

The deadline is emitted only when a D-M-Y date occurs in the explicit HTML final-submission language around `နောက်ဆုံးထား`. Missing or structurally ambiguous deadline evidence fails the detail parse closed rather than guessing.

## Implementation contract

```text
source_id                  = S37
adapter                    = moi_tender
role                       = ACTIVE_SELECTIVE
engine                     = direct_http
discovery_url              = https://www.moi.gov.mm/department-announcement
discovery_is_tender_only   = true   # adapter output, not raw board
baseline_lookback_days     = 180
baseline_detail_limit      = 4
delta_detail_limit         = 4
canonical_key              = drupal_node_id
first_baseline_signal      = false
primary                    = DIRECT_HTTP / HTML
supplementary              = []
attachment_mode            = HTML_ONLY_NO_ATTACHMENT_REQUIRED
```

Parser versions:

```text
discovery     = moi-department-announcement-v1
detail        = moi-drupal-announcement-v1
normalizer    = moi-tender-normalize-v1
canonicalizer = moi-drupal-node-id-v1
```

## Local verification

```text
python -m pytest tests/test_moi.py tests/test_contract.py -q
10 passed

git diff --check
PASS
```

Tests lock:

- issuer-specific Ministerial Office selection;
- other-agency repost exclusion;
- award/result exclusion;
- native Drupal node identity;
- listing English-month date;
- detail `MM/DD/YYYY` publication-date interpretation;
- Myanmar-digit sale-window extraction;
- explicit HTML deadline extraction;
- deadline/node mismatch fail-closed;
- baseline signal suppression;
- unchanged second poll does not refetch detail;
- zero non-HTML evidence.

## Bangkok isolated live-engine verification

The working tree was copied to a temporary Bangkok runtime with isolated DB/evidence roots. Production paths were untouched.

First real run:

```text
status            = SUCCESS
baseline          = true
discovered        = 1
candidates        = 1
fetched           = 1
items             = 1
tenders           = 1
details_attempted = 1
details_succeeded = 1
changed           = 1
signals_created   = 0
```

Second real run:

```text
status            = SUCCESS
baseline          = false
discovered        = 1
candidates        = 0
fetched           = 0
items             = 0
tenders           = 0
details_attempted = 0
changed           = 0
signals_created   = 0
```

Canonical result:

```text
canonical_key = moi:81536
publication   = 2026-04-09
sale_start    = 2026-04-20
sale_end      = 2026-05-11
deadline      = 2026-05-15
```

Two-run acquisition totals:

```text
requests          = 3
attempts          = 3
evidence          = 3
processing        = 3
canonical         = 1
signals           = 0
non-HTML evidence = 0
SQLite quick_check = ok
```

Evidence sizes:

```text
listing  = 45,228 bytes (run 1)
detail   = 41,575 bytes (run 1)
listing  = 45,228 bytes (run 2)
```

## Frozen boundaries

S37 adds no:

- PDF parser or download;
- image/OCR capability;
- Browser production dependency;
- SignalForge-to-Mac unattended invocation;
- proxy or TLS bypass;
- cross-issuer dedup/equivalence schema;
- Worker capability;
- schema migration.

Mac Browser Plane is now an explicit audit/controlled-acquisition option available through CodexPro, but `mac-mm-01` remains disabled for unattended SignalForge production unless a separate reviewed Provider Invocation Contract changes that boundary.

## Production gate

Promote only after feature PR + CI PASS, exact merged-SHA Bangkok deployment with timer safely paused, reviewed S37 zero-signal baseline, SignalForge Evidence/Worker correlation, Bangkok/Beijing fleet checks, frozen Mac-provider verification, timer resume, natural reconciliation completion if immediately due, and all-source GREEN closure.


## Production closure — 2026-09-07

Exact application release:

```text
d12d70d39794af32e67725700f344f8b50248bb0
```

Previous application-code rollback target:

```text
1561d6f5e53026b8f651e1aa40d9e52a3f6ee541
```

### Pre-deploy freeze

The scheduler was idle and no refresh unit was active when the timer was disabled. Frozen state:

```text
automated_sources     = 21 / 21 GREEN
canonical_items       = 171
signals               = 11
scheduler_runs        = 1652
acquisition_requests  = 2030
acquisition_attempts  = 2030
evidence_envelopes    = 2025
processing_records    = 2027
failed_runs           = 5
recovery_backlog      = 0
timer                 = disabled / inactive
run-due               = inactive
active refresh units  = 0
```

Deploying `d12d70d...` changed none of these counters. The existing 21 sources remained GREEN; new S37 appeared as the expected `baseline=0 / SOURCE_FRESHNESS_LAG / RED`.

### Reviewed production baseline

```text
source_id             = S37
trigger_kind          = MANUAL
baseline              = 1
status                = SUCCESS
items_parsed          = 1
tenders_parsed        = 1
details_attempted     = 1
details_succeeded     = 1
changed               = 1
signals_created       = 0
backlog_remaining     = 0
worker_run_id         = signalforge-20260907T145146Z-b9ee4d52
```

Expected counter movement only:

```text
canonical_items       171 -> 172
scheduler_runs        1652 -> 1653
requests/attempts     2030 -> 2032
evidence_envelopes    2025 -> 2027
processing_records    2027 -> 2029
signals               11 -> 11
failed_runs           5 -> 5
recovery_backlog      0 -> 0
```

### Production evidence

S37 baseline produced exactly two HTML EvidenceEnvelopes:

```text
listing  https://www.moi.gov.mm/department-announcement  HTTP 200  text/html  45,234 bytes
detail   https://www.moi.gov.mm/announcements/81536      HTTP 200  text/html  41,575 bytes
non-HTML evidence = 0
```

SignalForge DB `quick_check=ok`. Production canonical values:

```text
canonical_key = moi:81536
publication   = 2026-04-09
sale_start    = 2026-04-20
sale_end      = 2026-05-11
deadline      = 2026-05-15
```

No PDF, image, OCR or Browser evidence is part of the S37 production lifecycle.

### Worker / fleet / provider boundary

Worker DB contains exactly one matching operational run:

```text
run_id       = signalforge-20260907T145146Z-b9ee4d52
application  = signalforge
process_user = signalforge
status       = SUCCESS
exit_code    = 0
```

Boundary verification:

```text
SignalForge DB quick_check       = ok
Worker DB quick_check            = ok
Bangkok workerctl doctor         = PASS
Beijing workerctl doctor         = PASS
Beijing /srv/signalforge         = ABSENT
Beijing signalforge-refresh S37  = 126 / DENY: SignalForge is Bangkok-only
Mac production_enabled           = false
Mac remote_invocation            = false
browser_production_approved      = false
Mac invocation_mode              = manual_or_future_contract
canonical_node                   = bangkok
```

The same turn separately verified the Mac Browser Plane itself as `doctor=READY` and successfully used C0 through CodexPro to audit the Ministry of Industry. That proves the controlled Mac acquisition path is available to engineering/source-audit agents without making it an unattended SignalForge production dependency.

S37 has one successful detail sample while its health policy requests two samples before declaring `parse_health=GREEN`. Therefore immediately after baseline:

```text
source_health = GREEN
parse_health  = UNKNOWN
reason_code   = PARSE_SAMPLE_INSUFFICIENT
```

This is an insufficient-history state, not a parse failure. No artificial second detail fetch was created; future natural detail processing can satisfy the sample threshold.

### Timer resume and final state

`signalforge-resume` restored the timer. No source was due at that instant, so resume created no extra scheduler run. Final observed state:

```text
application_release   = d12d70d39794af32e67725700f344f8b50248bb0
automated_sources     = 22 / 22 GREEN
signalforge_health    = GREEN
canonical_items       = 172
signals               = 11
scheduler_runs        = 1653
acquisition_requests  = 2032
acquisition_attempts  = 2032
evidence_envelopes    = 2027
processing_records    = 2029
failed_runs           = 5 (historical / recovered)
recovery_backlog      = 0
timer                 = enabled / active
run-due               = inactive
```

**Gate result: S37 is PRODUCTION / GREEN.**
