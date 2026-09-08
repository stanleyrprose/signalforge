# S39 Ministry of Energy Source Onboarding — Live Production Closure — 2026-09-08

## Result

**PASS / PRODUCTION / GREEN**

S39 onboards the Myanmar Ministry of Energy tender board as an issuer-original Direct HTTP source. It does not use the Mac Browser Provider.

Production implementation SHA: `b8de9b0e2916b8e21f6bf6f7a1df66ce6e5f204b`.

## Source and acquisition shape

- Listing: `https://energy.gov.mm/tenders`
- Detail identity: numeric issuer record `/tenders/<id>`
- Engine: `direct_http`
- Execution: Bangkok SignalForge
- Primary acquisition: HTML
- Supplementary acquisition: exactly one required same-origin official PDF
- PDF path: `/storage/tenders/<opaque>.pdf`
- PDF parser: existing `pypdf==6.16.2`
- Browser: not used
- OCR/image extraction: not used
- Provider contract: unchanged

The parser never performs network I/O. HTML discovers the reviewed PDF URL; the SignalForge engine performs and persists the PDF acquisition before the source parser receives bytes.

The supplementary contract fails closed: Direct HTTP only, `target_kind=PDF`, `same_origin_only=true`, bounded to one required attachment. Provider sources are not authorized to use this supplementary path. The engine independently checks same-origin before issuing the PDF request.

## Fresh live audit

Bangkok strict HTTPS to `https://energy.gov.mm/tenders` was 3/3 HTTP 200. The current four issuer records were 235, 233, 234 and 232.

Reviewed text-native PDF results:

- `energy:235` / `ENERGY-27-2026-2027`: publication `2026-09-04`, deadline `2026-09-18 13:00`; scope includes ICT accessories, API 5L coated line pipe, PDC bit, Siemens IOT module, ICDD software, desktop/UPS and other oil-and-gas materials.
- `energy:233` / `ENERGY-24-2026`: publication `2026-08-14`, deadline `2026-08-28 13:00`; scope includes Computing Server and Storage Server.
- `energy:234` / `ENERGY-25-2026-2027`: publication `2026-08-14`, deadline `2026-08-28 13:00`; scope includes Online UPS, process transmitters and ISO 17025 implementation.
- `energy:232` / `ENERGY-23-2026-2027`: publication `2026-08-04`, deadline `2026-08-18 13:00`; scope includes Fuel Lab Equipment, laboratory furniture/accessories and Solar System items.

S19 MOEP E-Tender was not onboarded: BKK remained TLS RED and Mac C0/C1 returned an administrator-stopped hosting page rather than business content. S23 Ministry of Construction was not onboarded: the issuer certificate is expired and strict TLS fails from both BKK and Mac C0. No certificate bypass was introduced.

## Tests and merge gate

- Targeted S39/engine/acquisition/contract tests: PASS
- Full SignalForge suite before merge: `209 passed`
- `git diff --check`: PASS
- PR #91: CI PASS and squash-merged
- Merge SHA: `b8de9b0e2916b8e21f6bf6f7a1df66ce6e5f204b`

## Deployment

Pre-rollout state:

- active release: `29cdf90554c61bfcdc8bfb6cf4fba16c597652c9`
- DB quick check: `ok`
- canonical items: `189`
- signals: `34`
- failed runs: `31`
- S39 runs: `0`
- provider non-terminal requests: `0`

The timer was frozen before deployment. Exact SHA `b8de9b0e2916b8e21f6bf6f7a1df66ce6e5f204b` deployed successfully.

The rollout deliberately used a `mktemp -d` source directory with mode `0700` to live-verify the previous deploy hardening. The final release root was normalized to `0755`, proving the `cp -a` source-root-mode regression is closed.

## First production baseline

Worker run: `signalforge-20260908T154731Z-b8e83d7f`

SignalForge app run: `e9ca4a06-d058-44fb-a5b4-c1d5e84fa54f`

Result:

```text
baseline=true
status=SUCCESS
discovered=4
candidates=4
fetched=4
details_attempted=4
details_succeeded=4
detail_errors=0
items=4
tenders=4
changed=4
signals_created=0
backlog_remaining=0
```

Durable evidence after baseline:

- S39 canonical: `4`
- S39 customer signals: `0`
- S39 pending discovery items: `0`
- acquisition requests by target kind: `DISCOVERY=1 / HTML=4 / PDF=4`
- EvidenceEnvelopes: `9`
- processing SUCCESS: `5` total = one discovery processing + four detail/PDF business processing records
- detail parser processing: `4/4 SUCCESS`
- physical evidence: four HTML detail files + four PDF files (discovery evidence is also persisted through the acquisition envelope)
- every canonical `evidence_sha256` matches one of the four PDF EvidenceEnvelope hashes
- DB quick check: `ok`

S39 health after baseline:

- fetch: GREEN
- freshness: GREEN
- parse: `4/4 = 1.0`, GREEN
- recovery backlog: `0`, GREEN
- source health: GREEN
- consecutive failures: `0`
- last error: `null`

## Scheduler restoration

The Bangkok timer was restored `enabled/active`. Persistent timer recovery triggered Worker run `signalforge-20260908T155715Z-fce090b1`; the complete `run-due` invocation exited SUCCESS.

S39 correctly returned `NOT_DUE` because its next due time is `2026-09-08T16:17:31.274994Z`. No DB mutation or artificial refresh was used to force an unattended S39 run before its natural due time.

Final SignalForge snapshot after timer restoration:

- `status=PASS`
- `signalforge_health=GREEN`
- canonical items: `193`
- signals: `34`
- recovery backlog: `0`
- S25 has naturally recovered to GREEN (`9/10`, ratio `0.9`) without artificial refreshes
- S27, S38 and S39 are GREEN

## Topology clarification

SignalForge production is Bangkok-only. Beijing is not a SignalForge production node, replica, standby, acquisition provider, source runtime or per-source rollout gate. Historical Beijing zero-footprint checks remain valid historical evidence for the earlier fleet architecture, but new SignalForge source onboarding does not require a Beijing verification step.

## Final decision

**S39 Ministry of Energy = PRODUCTION / GREEN / COMPLETE.**

The reusable new capability is intentionally narrow: a Direct HTTP source may declare a reviewed, required, bounded same-origin PDF supplementary acquisition when business fields materially live in a text-native official PDF. This does not create generic PDF crawling, Browser fallback, OCR, or provider expansion.
