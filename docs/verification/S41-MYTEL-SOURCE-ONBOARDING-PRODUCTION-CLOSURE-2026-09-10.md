# S41 MYTEL Source Onboarding Production Closure — 2026-09-10

## Outcome

SignalForge now monitors MYTEL procurement invitations from Viettel Global's official tender feed as production source `S41`.

- Active runtime: `c5c2327c2300e5d7a22fce3222552bf8c6de7cc9`
- Immediate rollback: `0c310c5185f899a633f91dad0d0afd72810f1974`
- Exact git archive SHA256: `20d307a63c9a71ed948442e3c36fd0f52d0ee3ebb5b0ca8bd8ad0baaa270c7f1`
- PR #132 GitHub Actions verify run `34475619689`: PASS
- Full suite: `260 passed`

S41 is Bangkok Direct HTTP. It does not use Mac Browser Plane, Provider execution, TLS bypass, OCR, PDF acquisition or a new daemon.

## Portfolio-audit trigger

The source-portfolio business-value audit separated technical health from business yield. Nearly all existing active sources were technically GREEN, but only a minority had produced customer signals. The most meaningful historical business output was concentrated in MPT, MOEP, DOMS, MOFA, Industry and Energy; S25's twenty historical `UPDATED` signals were already-known normalization noise and were not treated as business productivity.

Two apparent gaps were rejected before adding a source:

- S40 Ministry of Labour currently exposes mostly tender-result / successful-bid announcements, so its zero current canonical count was not evidence of a parser miss.
- S15A Myanma Port Authority already exists as an intentional Manual P0 source under the previously closed Bangkok strict-TLS / Mac-direct boundary; it was not duplicated.

The clearest missing strategic feed was MYTEL. Viettel Global's official tender archive contains repeated MYTEL network procurement including MW systems, towers, antennas, batteries, OLT/accessories, MTSO equipment, generators and minishelters.

## Acquisition audit

Search-indexed MYTEL pages often point to `beta.viettelglobal.com.vn`. Bangkok strict TLS correctly rejects that hostname because its certificate does not match. Production does not use that host and does not weaken TLS verification.

The formal host `https://viettelglobal.com.vn` is strict-TLS valid from Bangkok. Its first request returns a small Cloudrity bootstrap page setting a `D1N` cookie and reloading. A second strict-TLS request with that cookie returns the real content.

The official tender landing page exposes a load-more endpoint:

`https://viettelglobal.com.vn/en/get-post-press-room?categories_id=82&offset=0&limit=100`

Bounded live tests showed:

```text
limit=50   -> 187108 bytes / 50 rows / 14 MYTEL raw records
limit=100  -> 361660 bytes / 100 rows / 19 MYTEL raw records
limit=240  -> 890201 bytes / 240 rows / 30 MYTEL raw records
limit=500  -> 2085861 bytes / 500 rows / 64 MYTEL raw records
```

`limit=100` already contained all sixteen raw 2026 MYTEL posts found in the 240-row audit, while remaining well below the existing 1 MB source request bound. S41 therefore uses `limit=100`; no pagination engine was added.

## D1N fetch profile

The production HTTP client now has one narrowly authorized profile: `cloudrity_d1n_v1`.

It is restricted to HTTPS and exact hosts `viettelglobal.com.vn` / `www.viettelglobal.com.vn`. It:

1. performs a normal strict-TLS GET;
2. recognizes only the fixed Cloudrity `document.cookie="D1N=<hex>" ... window.location.reload(true)` shape;
3. retries once with `Cookie: D1N=<hex>`;
4. fails if the challenge persists.

It does not evaluate arbitrary JavaScript, disable certificate checks, follow the invalid beta hostname, or create a generic anti-bot framework. The registry must explicitly opt into the profile; injected test fetchers remain unaffected.

Exact branch fetch code was executed from Bangkok before merge and returned the real 361660-byte JSON with 100 feed rows and 19 raw MYTEL records.

## Business parser contract

`mytel-viettelglobal-feed-v1` is a listing-complete official-feed parser. It requires explicit MYTEL issuer evidence and a MYTEL RFP reference; other Viettel overseas subsidiaries are excluded.

### Canonical identity

Invitation and extension posts may vary the textual RFP suffix. A live example uses both:

- `03/2026/MYTEL-ANTENNA & TWINBEAM`
- `03/2026/MYTEL-ANTENNA`

The source audit found repeated serial/year groups only where posts represented the same procurement invitation/extension chain. Canonical identity is therefore MYTEL RFP serial + year, e.g. `mytel:3-2026`. Full latest reference text is still retained in `reference_no`.

This prevents extension notices from becoming duplicate opportunities.

### Version selection

Records for the same RFP are ordered by the official backend `created_at` plus post id. This is intentional because the feed contains demonstrably inconsistent `published_at` values on extension posts. The chosen backend timestamp is retained as `source_created_at` and its date is used as the canonical publication date.

### Deadline semantics

The parser does not collapse all dates into one meaning:

- explicit `Deadline for submitting the Proposal Document` -> `BID_SUBMISSION_DEADLINE`;
- extension-only `Time to collect bid documents` -> `TENDER_FORM_SALE_CLOSE`;
- missing/invalid actionable time -> UNKNOWN.

Tender opening is separately retained where the invitation explicitly states it.

No extension-only document-collection date is asserted to be a bid-submission deadline.

## Live feed parser audit

The real bounded `limit=100` feed contained nineteen raw MYTEL posts. After RFP-version folding it produced fifteen canonical RFPs.

Latest-version breakdown:

```text
15 canonical RFPs
12 latest versions dated 2026
3 latest versions dated 2025
8 BID_SUBMISSION_DEADLINE
4 TENDER_FORM_SALE_CLOSE
3 UNKNOWN (older 2025 records; not guessed)
```

All twelve latest-version 2026 RFPs had an actionable date. Example 2026 procurement families include Tower SST/RTT, MTSO Equipment, OLT, MW System, Battery, Antenna, Foundation, Optical Cable Accessories, Generator and Minishelter.

The live audit also preserved issuer inconsistencies instead of silently correcting them; for example a record whose RFP suffix says OLT while its purchase name says Optical Cable Accessories remains represented from the explicit source fields rather than inferred into a different identity.

## Tests and pre-merge live gate

Final targeted S41 + closed-contract tests: `12 passed`.

Full suite: `260 passed`.

Tests cover:

- exact host-bound D1N cookie retry;
- rejection of other hosts;
- persistent challenge fail-closed;
- non-MYTEL feed exclusion;
- invalid JSON fail-closed;
- invitation + extension folding;
- suffix drift across the same RFP serial/year;
- explicit bid deadline vs document-collection close semantics;
- erroneous `published_at` not controlling version order;
- silent baseline;
- future new RFP -> `NEW` signal through the existing engine.

Before merge, the complete branch commit was archived and run on Bangkok using a temporary DB and the default production acquisition path. It exercised engine -> D1N bootstrap -> official feed -> parser -> canonicalization in one path:

```text
run 1: baseline=true  / discovered=15 / changed=15 / signals_created=0
run 2: baseline=false / discovered=15 / changed=0  / signals_created=0
canonical=15
signals=0
quick_check=ok
```

No production DB/source state was changed by this gate.

## Merge and deployment

PR #132 squash-merged as:

`c5c2327c2300e5d7a22fce3222552bf8c6de7cc9`

The exact git archive SHA256 matched locally and on Bangkok:

`20d307a63c9a71ed948442e3c36fd0f52d0ee3ebb5b0ca8bd8ad0baaa270c7f1`

The reviewed release script deployed it successfully with previous runtime `0c310c5185f899a633f91dad0d0afd72810f1974` retained as rollback.

## Production baseline and verification

First reviewed S41 Worker run:

`signalforge-20260910T121631Z-e0b86f14`

Result:

```text
baseline=true
status=SUCCESS
discovered=15
items=15
tenders=15
changed=15
signals_created=0
```

Second reviewed run:

`signalforge-20260910T121702Z-86d64458`

Result:

```text
baseline=false
status=SUCCESS
discovered=15
changed=0
signals_created=0
```

All imported MYTEL records are currently historical/expired, so actionable-baseline reconciliation correctly emitted no customer signal.

Production after activation:

```text
S41 canonical       = 15
S41 signals         = 0
global canonical    = 209
global signals      = 45
DB quick_check      = ok
current opportunities = 8 OPEN + 1 UNKNOWN
Telegram pending    = 0
```

The customer opportunity set is therefore unchanged; S41 does not resurrect historical tenders.

Latest S41 evidence is recorded as:

```text
media_type    = application/json
content_length= 361660
fetch_method  = DIRECT_HTTP
artifact_sha256 = a2c3bb54169f8e30fd27a6d82e8cbb53f9451e2efe6e7fa89fe264d45034cb3a
```

S41 source health after two production business-processing runs:

```text
source_health     = GREEN
fetch_health      = GREEN
freshness_health  = GREEN
parse_health      = GREEN
parse_attempts    = 2
parse_successes   = 2
parse_success_ratio = 1.0
consecutive_failures = 0
```

`next_due_at=2026-09-10T12:47:03.166034Z`, proving S41 is enrolled in the normal 30-minute scheduler cadence. Acquisition and Telegram timers remain active. Global SignalForge remains `PASS / GREEN`.

## Boundary and next priority

This activation adds a high-strategic-fit telecom procurement source but does not change delivery policy. Future MYTEL RFPs will pass through existing qualification and Telegram rules. A current, complete MYTEL tender will naturally classify as TELECOM because the official issuer is Telecom International Myanmar and will be HIGH when actionable.

Do not respond to this successful activation by mechanically adding more sources. The portfolio audit should now monitor business yield by source and only onboard another source where there is a similarly evidenced coverage gap. Technical GREEN alone is not a reason to retain or expand source count, and raw signal count must continue to exclude known historical parser/normalization noise when judging value.
