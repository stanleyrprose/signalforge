# Evidence Retention Audit Debt Closure — 2026-09-20

## Root cause

SignalForge began retaining acquired evidence before parsing in commit `68f1989a9c55dc5cc4eb1a9d54ed9e7d860e1abd` ("fix: retain filtered evidence for assurance review"), committed at 2026-09-16T01:13:39Z.

Bangkok production records the retention-live cutover as:

```text
2026-09-16T01:17:15.604719Z
```

Observed production evidence supports that cutover:

- last zero-item row without retained evidence: 2026-09-16T01:16:07.893724Z
- first zero-item row with retained evidence: 2026-09-16T01:17:50.275126Z
- no missing retained zero-item evidence was observed after the retention-live cutover

Therefore the historical missing files are pre-retention audit debt, not an active retention failure.

## Production counts

Read-only Bangkok audit on 2026-09-20:

```text
zero-item total                 850
replayable                      201
legacy pre-retention missing    649
retention-era missing             0
```

After Jev triage deterministic gates (reviewed/recovered/deduplicated):

```text
scanned                         850
already reviewed                 17
recovered later                 238
duplicate artifact               60
missing evidence                361
legacy missing evidence         361
retention-era missing evidence    0
```

The previous "361 missing retained evidence" observation was therefore entirely legacy debt.

## Existing Assurance behavior

Assurance already distinguishes:

- `filtered_zero_item_legacy_unreplayable_window`
- `filtered_zero_item_retention_era_unreplayable_window`

Only retention-era unreplayability triggers:

```text
FILTERED_EVIDENCE_NOT_REPLAYABLE_AFTER_RETENTION
```

Latest Bangkok metric review observed:

```text
legacy_unreplayable_window        649
retention_era_unreplayable_window  0
```

The review reasons did not include a retention failure.

## Jev triage correction

`jev-noise-triage` now mirrors the same semantics:

- `zero_item_missing_evidence` — compatibility total for absent retained files
- `zero_item_legacy_missing_evidence` — pre-retention diagnostic debt
- `zero_item_retention_era_missing_evidence` — current unexpected retention failure
- `zero_item_empty_evidence_text` — retained file exists but contains no semantic text
- `evidence_retention_status=PASS` when retention-era missing is zero
- `evidence_retention_status=REVIEW` when any retention-era missing exists
- `legacy_missing_evidence_is_diagnostic_only=true`

This prevents historical debt from being presented as a current auditability bug while preserving the debt count for historical transparency.

## Boundary

No historical evidence rows are deleted or rewritten.

No production DB mutation, Telegram change, scheduler change, parser change, or Jev authority change is part of this fix.
