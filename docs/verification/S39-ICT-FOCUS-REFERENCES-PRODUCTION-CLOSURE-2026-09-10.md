# S39 ICT Focus References — Production Closure — 2026-09-10

## Result

**COMPLETE / PASS**

SignalForge now turns the mixed-lot Ministry of Energy opportunity `energy:235` into a more actionable customer view without changing canonical identity, source parsing or signal history.

The tender still exposes all eleven procurement package references, while the read layer separately identifies the four packages with explicit ICT/Telecom relevance:

```text
DMP/L-026(26-27) — Communication and Information Technology accessories
DMP/L-067(26-27) — Siemens IOT Module
DMP/L-073(26-27) — ICDD PDF-2 Software
DMP/L-089(26-27) — Book Scanner / Desktop Computer / UPS
```

## Trigger

The earlier S39 multi-reference rollout made all eleven package identifiers visible, but the Telegram scope excerpt remained bounded. Because the Energy notice is a mixed procurement event, non-ICT packages near the start of the PDF could consume the excerpt while later ICT packages were hidden.

The notice-level `ICT/HIGH` qualification was correct, but the customer still had to inspect all eleven packages to discover which ones justified that relevance.

## Design

This slice is deliberately read-only and source-scoped.

`current_opportunities()` derives focus data only when all of the following are true:

- source is `S39`;
- detail completeness is the reviewed `HTML_ID_PUBLICATION_PLUS_TEXT_PDF_SCOPE_DEADLINE` path;
- a multi-reference DMP bundle already exists;
- scope can be segmented by exact `DMP/L-xxx(yy-yy)` identifiers.

The narrow focus vocabulary is limited to explicit ICT/Telecom terms observed in the reviewed Energy package descriptions, including communication/information, IoT, software, scanner, computer, server, network and telecom language.

No generic lot classifier or ML/NLP model is introduced.

The read view adds:

- `focus_reference_numbers`;
- `focus_reference_count`;
- `focus_relevance=ICT_TELECOM`;
- `focus_scope_summary`.

`business_briefing()` preserves the focus fields and, when focus scope exists, uses it for the bounded attention excerpt instead of the full mixed-lot scope.

Telegram keeps the complete `📌 编号` line and adds a separate `🧩 相关分包` line. The delivery key is unchanged, so display-only enrichment does not replay an already delivered message.

## Test gates

Targeted opportunities + briefing + Telegram tests:

`26 passed`

Full repository suite:

`267 passed`

Regression coverage proves:

- exact S39 source scoping;
- no focus for a single reference;
- non-ICT Energy packages such as Line Pipe and Mud Chemical are excluded;
- DMP-026 / 067 / 073 / 089 are selected from the reviewed mixed scope;
- stray next-item list numbers are removed from segment tails;
- briefing prefers focus scope;
- Telegram renders full references and focus references separately.

## Production-copy verification

A fresh SQLite backup of the real Bangkok production DB was read with the branch implementation.

`energy:235` produced:

```text
focus_reference_count = 4
focus_reference_numbers =
  DMP/L-026(26-27)
  DMP/L-067(26-27)
  DMP/L-073(26-27)
  DMP/L-089(26-27)
focus_relevance = ICT_TELECOM
```

The copy DB SHA256 was unchanged before and after the read:

`d5b14acb83b0bb635cc4206a1fe93fa82a4af44a9f0b5741433cdfcec09b3a7b`

## PR and deployment

- PR #141: `feat: highlight ICT packages in Energy multi-lot notices`
- GitHub Actions verify run: `34491863462` — PASS
- Exact production release: `33a0aafa35ac01225d3b988be842f47245b47514`
- Rollback release: `3700e675327cd599797fc0eaef8ddb8d0e289005`
- Exact git archive SHA256: `678d8ccc32b874f7b53cbaa7006009f3892028821be2572dd7806850ab50d67d`

The exact archive hash matched locally and on Bangkok before deployment.

No source refresh or DB migration was run.

## Live production verification

Post-deploy live state for `energy:235`:

```text
trust/priority          = A / HIGH
reference_count         = 11
focus_reference_count   = 4
focus_reference_numbers = 026 / 067 / 073 / 089
focus_relevance         = ICT_TELECOM
```

`business_briefing()` propagates those four references and prioritizes their descriptions in `scope_excerpt`.

Underlying canonical payload inspection returns no persisted `focus_reference_numbers`, proving the focus remains derived read-model data.

Production invariants remain:

```text
opportunities       = 8 OPEN + 1 UNKNOWN
canonical_items     = 209
signals             = 45
Telegram pending    = 0
DB quick_check      = ok
acquisition timer   = active
Telegram timer      = active
```

## Boundary

This slice does not change:

- S39 parser or source acquisition;
- canonical identity/payload history;
- signal semantics/history;
- qualification trust/priority/relevance policy;
- delivery identity/dedup semantics;
- DB schema;
- source registry/polling;
- Browser/Provider/Worker/Control/Beijing topology.

Future mixed-lot focus rules should remain issuer/pattern-specific until additional evidence justifies a more general abstraction.
