# S39 Energy Multi-Reference Read-Layer Production Closure — 2026-09-10

## Outcome

SignalForge now exposes the eleven explicit `DMP/L-*` procurement package references inside current Energy tender `energy:235` through the customer read model, without rewriting canonical facts or signal history.

- PR #136: `feat: expose Energy multi-lot references in read view`
- CI verify run: `34481911436` — PASS
- Exact production runtime: `20f2a7e8cd92671e98155bf963a291cd9a5ec3ba`
- Rollback: `c5c2327c2300e5d7a22fce3222552bf8c6de7cc9`
- Exact git archive SHA256: `7d2f8ad0e584d8bc703c5bb6d6e75428b2e13c5f13b9ffbd5878735b3e5a47b6`
- Targeted opportunities tests: `8 passed`
- Full suite: `262 passed`

## Trigger

The customer decision-quality audit found that `energy:235` is a HIGH/A/ICT current opportunity with an explicit tender deadline, but `reference_numbers` and `reference_count` were null even though its reviewed text-native official PDF scope contains eleven distinct procurement package references.

The notice is one tender event with multiple purchase packages. Splitting it into eleven canonical tenders would change identity semantics and was not justified. Rewriting the S39 parser/canonical payload solely for display would also create unnecessary migration risk.

The smallest correct solution is therefore read-layer derivation.

## Evidence reviewed

The exact reviewed Energy PDF text contains the following package identifiers:

```text
DMP/L-026(26-27)
DMP/L-040(26-27)
DMP/L-048(26-27)
DMP/L-067(26-27)
DMP/L-073(26-27)
DMP/L-089(26-27)
DMP/L-092(26-27)
DMP/L-093(26-27)
DMP/L-101(26-27)
DMP/L-104(26-27)
DMP/L-113(26-27)
```

The source text sometimes contains harmless spacing such as `DMP/L- 067(26-27)`; the read view normalizes this to `DMP/L-067(26-27)`.

Other reviewed Energy PDFs use different issuer reference grammars, including forms such as `30(LPT)MPE-Mann/26-27` and `PPRD/LP/...`. Those grammars were deliberately not generalized into this slice.

## Read-layer contract

`current_opportunities()` now applies a source-scoped reference bundle rule:

1. canonical `reference_numbers`, when present and non-empty, always win;
2. derivation is permitted only for source `S39`;
3. the canonical must carry reviewed Energy text-PDF completeness `HTML_ID_PUBLICATION_PLUS_TEXT_PDF_SCOPE_DEADLINE`;
4. only exact `DMP/L-xxx(yy-yy)` references are admitted;
5. references are normalized and deduplicated in source order;
6. at least two distinct references are required, otherwise derivation fails closed;
7. derived evidence is `OFFICIAL_TEXT_NATIVE_PDF_SCOPE_DMP_REFERENCE_PATTERN`.

No generic Energy reference parser was introduced.

## Test gates

Targeted `tests/test_opportunities.py`: `8 passed`.

Full suite: `262 passed`.

Regression tests prove:

- source scoping to S39;
- exact DMP pattern normalization;
- deduplication;
- a single match remains un-enriched;
- wrong completeness remains un-enriched;
- explicit canonical reference bundles override derivation;
- a signal-backed S39 opportunity receives the derived bundle while preserving its existing top-level notice reference and deadline semantics.

## Production-copy gate

A fresh SQLite backup of the real production DB was read with the branch implementation.

Result for `energy:235`:

```text
reference_count = 11
reference_numbers =
  DMP/L-026(26-27)
  DMP/L-040(26-27)
  DMP/L-048(26-27)
  DMP/L-067(26-27)
  DMP/L-073(26-27)
  DMP/L-089(26-27)
  DMP/L-092(26-27)
  DMP/L-093(26-27)
  DMP/L-101(26-27)
  DMP/L-104(26-27)
  DMP/L-113(26-27)
reference_numbers_evidence = OFFICIAL_TEXT_NATIVE_PDF_SCOPE_DMP_REFERENCE_PATTERN
```

`business_briefing()` propagated all eleven references and the existing Telegram renderer displayed them in the `📌 编号` line.

The copied DB SHA256 was identical before and after the read:

`c07779fb55e1939d958c71784c96e5bf1ef196500dc513fe8329839f4dc1885f`

This proves the slice is read-only.

## Merge and deployment

PR #136 passed GitHub Actions run `34481911436` and squash-merged as:

`20f2a7e8cd92671e98155bf963a291cd9a5ec3ba`

The exact git archive SHA256 matched locally and on Bangkok:

`7d2f8ad0e584d8bc703c5bb6d6e75428b2e13c5f13b9ffbd5878735b3e5a47b6`

The reviewed release script deployed the exact archive successfully, retaining previous runtime `c5c2327c2300e5d7a22fce3222552bf8c6de7cc9` as rollback.

No source refresh or DB migration was run because the change is purely read-layer.

## Production verification

Post-deploy live state:

```text
active runtime      = 20f2a7e8cd92671e98155bf963a291cd9a5ec3ba
SignalForge status  = PASS
SignalForge health  = GREEN
canonical_items     = 209
signals             = 45
recovery backlog    = 0
opportunities       = 8 OPEN + 1 UNKNOWN
acquisition timer   = active
Telegram timer      = active
Telegram pending    = 0
DB quick_check      = ok
```

Live `energy:235` now returns `reference_count=11` and the exact eleven identifiers above. Its briefing attention item carries all eleven.

Direct DB inspection confirms the underlying canonical payload still has:

```text
reference_numbers = null
reference_count   = null
```

Global signal count remains 45. Existing Telegram receipts are not replayed by the display-only improvement.

## Boundary

This slice does not change:

- S39 source acquisition or parser;
- canonical identity or payload history;
- signal semantics/history;
- qualification policy;
- Telegram delivery identity/policy;
- source registry roles or polling;
- DB schema;
- Browser/Provider/Worker/Control/Beijing topology.

Future reference grammars should be added only after their issuer patterns are independently reviewed. Do not convert this exact DMP rule into a generic alphanumeric reference heuristic.
