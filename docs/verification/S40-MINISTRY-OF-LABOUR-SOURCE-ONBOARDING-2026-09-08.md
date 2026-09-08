# S40 Ministry of Labour Source Onboarding — Live Production Closure — 2026-09-08

## Result

**PASS / PRODUCTION WATCHER / GREEN**

S40 monitors the Myanmar Ministry of Labour issuer-original Tender page using Bangkok Direct HTTP. It does not use the Mac Browser Provider and introduces no new acquisition capability beyond the already-live S39 required same-origin text-native PDF path.

Implementation/deployed SHA: `9980584b7deec660d16e5f202ff0056117df88f6`.

## Deliberate scope

- Production discovery: `https://www.mol.gov.mm/tender/` page 1 only.
- The issuer page is ordered newest-first and currently exposes ten workflow/result-stage posts on page 1.
- The official Content Views page-2 URL `https://www.mol.gov.mm/tender/?_page=2` is fixture/regression evidence only; it is not a production discovery URL and is not used for historical backfill.
- No multi-page discovery, JSON target kind, Browser, OCR, Provider expansion or certificate bypass was introduced for S40.
- New opportunity-stage posts are expected to appear at the head of page 1 and will then enter the existing detail + required same-origin PDF path.

This is intentionally simpler than adding a generic pagination subsystem for one source.

## Opportunity-stage semantics

The parser accepts explicit open-tender / invitation / tender-call language and fail-closed excludes workflow/result stages including tender awarded, technical-qualified/score, winner/company lists and result semantics.

Current page-1 records include tender awards and technical-qualified-company announcements for laboratory, construction, Data Center Main Site M&O, Telecommunication Infrastructure Implementation M&O, Smart Net / Antivirus licences and related procurement. They are correctly excluded from business opportunities.

Historical issuer page-2 regression contains four opportunity-stage records selected by the parser, including Smart ID Card Printing, medical equipment, construction works and laboratory tender calls. Result/technical-qualified rows on the same page are excluded.

## PDF regression evidence

Two historical invitation records were frozen as reviewed HTML/PDF fixtures to prove future page-1 opportunity handling without backfilling them into production.

### WordPress post 43883 — Smart ID Card Printing

- publication: `2026-06-25`
- official PDF is same-origin and text-native
- canonical identity: `mol:43883`
- scope includes `SSB Information System` / `Smart ID Card Printing`
- submission deadline: `2026-07-14 16:30`

The issuer PDF expresses the time as Myanmar evening `4:30`; PDF extraction distorts the marker, so regression logic explicitly preserves the PM semantic and prevents a false `04:30` conversion.

### WordPress post 43840 — medical equipment

- publication: `2026-06-19`
- canonical identity: `mol:43840`
- scope includes `Electric High Speed Drill` and `Fibroscan`
- submission deadline: `2026-07-13 16:30`
- business unit: Social Security Board

Both PDFs are parsed by the already-packaged `pypdf==6.16.2` runtime. Parser code performs no network I/O; the engine owns acquisition/evidence.

## Test gate

- targeted MOL / contract / Energy / engine / acquisition tests: `28 passed`
- full SignalForge suite: `215 passed`
- `git diff --check`: PASS
- PR #94: CI PASS and squash-merged
- merged implementation SHA: `9980584b7deec660d16e5f202ff0056117df88f6`

## Production rollout

Pre-rollout:

- active application: `b8de9b0e2916b8e21f6bf6f7a1df66ce6e5f204b`
- DB quick check: `ok`
- canonical items: `193`
- signals: `34`
- failed runs: `31` historical
- S40 runs: `0`
- provider non-terminal requests: `0`

Bangkok timer was frozen before deployment. Exact SHA `9980584b7deec660d16e5f202ff0056117df88f6` deployed successfully; rollback target is the prior S39 application release.

## First production baseline

Worker run: `signalforge-20260908T163346Z-05f65b51`

App run: `b2b3f5ff-4802-441c-9b28-c1efe819d65b`

Result:

```text
baseline=true
status=SUCCESS
discovered=0
candidates=0
details_attempted=0
details_succeeded=0
detail_errors=0
changed=0
signals_created=0
backlog_remaining=0
```

The zero business-item baseline is the expected safe result, not a collection failure.

Durable S40 state:

- canonical: `0`
- customer signals: `0`
- pending: `0`
- acquisition targets: `DISCOVERY=1`
- EvidenceEnvelope: `1`
- processing SUCCESS: `1`
- no detail HTML acquisition
- no PDF acquisition
- DB quick check: `ok`

S40 health after baseline:

- fetch: GREEN
- freshness: GREEN
- recovery backlog: GREEN / 0
- parse: `UNKNOWN` with explicit reason `PARSE_SAMPLE_INSUFFICIENT` because there is currently no opportunity detail sample
- source health: GREEN
- consecutive failures: 0
- last error: null

No artificial health probe or historical detail fetch was used to manufacture parse GREEN.

## Timer restoration

Bangkok timer was restored `enabled/active`.

Timer-triggered Worker `signalforge-20260908T163503Z-f6e89982` completed the full `run-due` invocation `SUCCESS` on the new release. S40 correctly returned `NOT_DUE` until its natural `2026-09-08T17:03:46.458201Z` schedule. No DB due-time mutation was used.

Final snapshot:

- active application: `9980584b7deec660d16e5f202ff0056117df88f6`
- timer: enabled / active
- SignalForge: `PASS / GREEN`
- canonical items: `193`
- signals: `34`
- recovery backlog: `0`
- S40 source health: GREEN

## Topology

SignalForge production remains Bangkok-only. Beijing is not part of the SignalForge production topology and was not checked or modified during this onboarding.

## Final decision

**S40 Ministry of Labour = PRODUCTION WATCHER / GREEN / COMPLETE.**

The honest boundary is that current live page 1 has no opportunity-stage record, so S40 has not yet exercised its detail/PDF path against a current production opportunity. That path is deterministic fixture-verified against issuer-original historical invitations and reuses the already-live S39 attachment acquisition contract. The next real page-1 opportunity will provide the first unattended production detail/PDF sample naturally.
