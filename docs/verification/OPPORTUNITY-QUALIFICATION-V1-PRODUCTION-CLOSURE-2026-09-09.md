# Opportunity Qualification v1 — Production Closure — 2026-09-09

## Result

> **COMPLETE / PASS**

SignalForge now adds a deterministic, read-only qualification layer to the existing signal-backed `signalforge opportunities` view. This slice does not create or mutate canonical items, signals, evidence, scheduler state, acquisition state, Browser policy, Provider policy, or DB schema.

Exact production application release:

`08153c47b1efc67c85776f551da2e1130b2d1c63`

Immediate rollback target:

`5e599801be58a58ce983e61d2b1564c6ef6a83a9`

Deployment archive SHA256 matched locally and on Bangkok:

`927ddc89a778c88e20261abd83ec015a404bc33c0812409d359edec2378dc9d5`

## Policy v1

Every current signal-backed `TENDER / OPPORTUNITY` row now exposes:

- `qualification_policy_version=1`
- `trust_grade`: `A / B / C`
- `actionability`: `OPEN / UNKNOWN / EXPIRED`
- `urgency`: `URGENT / SOON / NORMAL / UNKNOWN / EXPIRED`
- `evidence_level`
- `completeness`: `FULL / PARTIAL / MINIMAL`
- `relevance_categories`
- `primary_relevance`
- `priority_band`: `HIGH / MEDIUM / REVIEW / LOW`
- `qualification_reasons`
- `source_engine`

### Trust

- **A**: business scope is present and the deadline is explicit/evidence-backed.
- **B**: issuer event/reference is trustworthy but business actionability is incomplete, such as a missing deadline.
- **C**: minimum evidence only; not sufficient for ordinary actionable presentation.

### Priority

- **HIGH**: OPEN + A and either ICT/Telecom relevance or <=72h remaining.
- **MEDIUM**: OPEN + A.
- **REVIEW**: partial/unknown but still trustworthy enough to surface for human review.
- **LOW**: expired or C-grade.

This is intentionally rules-based and explainable. No ML/ranking model is introduced.

## Evidence semantics

Current evidence labels include:

- `OFFICIAL_HTML_VIA_PROVIDER`
- `OFFICIAL_HTML_PLUS_TEXT_PDF`
- `OFFICIAL_HTML`

Provider use is not treated as lower trust by itself. Trust is based on business completeness/evidence, while the acquisition engine remains explicit in the output.

## Relevance v1

Current categories are:

- `TELECOM`
- `ICT`
- `ENERGY`
- `INDUSTRIAL`
- `MEDICAL`
- `CONSTRUCTION`
- `OTHER`

The implementation uses conservative deterministic keyword evidence plus narrow source-domain fallback. Regression tests explicitly prevent broad terms such as `PowerEdge`, `Power Supply`, `Engine Power`, or ordinary `Electrical Spare Parts` from creating false ENERGY classifications.

## Tests

- qualification + opportunity targeted tests: `6 passed`
- full suite: `224 passed`
- `git diff --check`: PASS

## Production-DB preview

Before deployment, a SQLite backup of the live Bangkok DB was evaluated with the new reader. It produced:

- current opportunities: `9`
- OPEN: `8`
- UNKNOWN: `1`
- trust: `A=8 / B=1 / C=0`
- priority: `HIGH=3 / MEDIUM=5 / REVIEW=1 / LOW=0`

This preview was read-only and did not mutate production.

## Live production verification

After exact-SHA deployment, `signalforge opportunities` returned the same nine current opportunities:

| Canonical | Trust | Priority | Relevance | Urgency | Evidence |
| --- | --- | --- | --- | --- | --- |
| `industry:1022` | A | HIGH | INDUSTRIAL | URGENT | OFFICIAL_HTML_VIA_PROVIDER |
| `energy:235` | A | HIGH | ICT | NORMAL | OFFICIAL_HTML_PLUS_TEXT_PDF |
| `mofa:59800` | A | HIGH | ICT | NORMAL | OFFICIAL_HTML_PLUS_TEXT_PDF |
| `industry:1034` | A | MEDIUM | INDUSTRIAL | SOON | OFFICIAL_HTML_VIA_PROVIDER |
| `industry:1037` | A | MEDIUM | INDUSTRIAL | NORMAL | OFFICIAL_HTML_VIA_PROVIDER |
| `industry:1036` | A | MEDIUM | INDUSTRIAL | NORMAL | OFFICIAL_HTML_VIA_PROVIDER |
| `industry:1039` | A | MEDIUM | INDUSTRIAL | NORMAL | OFFICIAL_HTML_VIA_PROVIDER |
| `industry:1035` | A | MEDIUM | INDUSTRIAL | NORMAL | OFFICIAL_HTML_VIA_PROVIDER |
| `doms:12735` | B | REVIEW | MEDICAL | UNKNOWN | OFFICIAL_HTML |

Summary live counts:

- trust: `A=8 / B=1 / C=0`
- priority: `HIGH=3 / MEDIUM=5 / REVIEW=1 / LOW=0`
- relevance: `ICT=2 / ENERGY=1 / INDUSTRIAL=7 / MEDICAL=1 / CONSTRUCTION=1`

`doms:12735` remains deliberately `deadline=UNKNOWN`; qualification does not infer a missing date.

## Business-state invariants

The read-only rollout preserved production business state:

- canonical items: `194`
- signals: `44`
- DB quick check: `ok`
- overall SignalForge: `PASS / GREEN`
- recovery backlog: `0`
- Bangkok timer: enabled / active

No source refresh was used to validate the feature.

## Closed control-path verification

The existing Bangkok forced dispatcher command:

`signalforge-opportunities`

returned `PASS`, `qualification_policy_version=1`, the same qualification counts, and the same nine qualified rows. No Control Plane change was required because the existing closed read verb already invokes `signalforge opportunities`.

## Boundary

This slice does **not** add:

- customer push/delivery
- personalized scoring profiles
- ML ranking
- public API
- DB write path
- new acquisition engine
- OCR
- Browser capability expansion
- Provider capability expansion
- Beijing dependency

The next product step should consume these deterministic qualification fields for delivery/briefing, rather than adding more platform infrastructure by default.
