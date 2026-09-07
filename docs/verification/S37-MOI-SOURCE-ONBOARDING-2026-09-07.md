# S37 Ministry of Information Ministerial Office Procurement Announcements — Source Onboarding

Date (Asia/Yangon): 2026-09-07
Phase: PRE-PRODUCTION
Result: IMPLEMENTATION / TEST / ISOLATED LIVE PASS — PRODUCTION GATE PENDING

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
