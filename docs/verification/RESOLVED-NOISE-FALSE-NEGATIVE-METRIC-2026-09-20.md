# Resolved Noise False-Negative Metric Semantics — 2026-09-20

## Problem

The latest Bangkok Metric Validity review reported:

```text
RECENT_NOISE_FALSE_NEGATIVE_EXISTS
```

because one noise sample in the 30-day review window had been classified `FALSE_NEGATIVE`.

That sample was not an active defect.

## Production evidence

Noise sample:

- noise_sample_id: `ed9d3858-2813-434e-ae03-3baaedc55ba0`
- source: S22 / Inland Water Transport
- candidate: historical zero-item processing record
- reviewed_at: 2026-09-19T08:17:24.582348Z

Review evidence states that historical parser v1 returned zero after issuer URL drifted to:

```text
/index.php/my/node/<id>
```

The current parser replays the same retained artifact as 20 tender entries.

The corresponding Miss Ledger record:

- miss_id: `0750c776-d509-427a-a58e-6bf30cee2980`
- detected_by: `NOISE_REVIEW`
- severity: `RED`
- status: `RESOLVED`
- resolved_at: 2026-09-19T08:17:41.380651Z
- resolution basis: parser fix `a0258c51f25449c8f0221e444f5e2eb19cc15805`, replay verification, and canonical recovery of the relevant tender

There are currently no OPEN misses from this false negative.

## Root cause

Metric Validity counted every recent `FALSE_NEGATIVE` as a current review blocker regardless of the lifecycle state of its linked Miss Ledger record.

This mixed two different questions:

1. Did a false negative occur within the quality review window?
2. Is that false negative still an unresolved current risk?

The first is a historical quality metric.
The second is a current operational risk.

## Fix

The original metrics remain:

- `noise_false_negatives_window`
- `noise_false_negative_rate`

These continue to preserve historical quality evidence.

New lifecycle metrics:

- `noise_false_negatives_open_window`
- `noise_false_negatives_closed_window`
- `noise_false_negatives_untracked_window`

Classification uses the `noise_sample_id` stored in `missed_signals.metadata_json`.

### OPEN

If any linked Noise Review miss is `OPEN`, the sample is current unresolved risk.

Review reason:

```text
RECENT_UNRESOLVED_NOISE_FALSE_NEGATIVE_EXISTS
```

### CLOSED

If linked miss records exist and none is OPEN, the historical false negative remains in the rate/count but does not by itself block current Metric Validity.

Closed states include resolved/closed Miss Ledger outcomes such as `RESOLVED` or `FALSE_POSITIVE`.

### UNTRACKED

If a recent `FALSE_NEGATIVE` has no usable linked Miss Ledger record, the audit chain is incomplete.

Review reason:

```text
RECENT_UNTRACKED_NOISE_FALSE_NEGATIVE_EXISTS
```

Malformed or non-object Miss Ledger metadata does not crash Assurance; it leaves the false negative untracked.

## Production classification

Read-only Bangkok classification on 2026-09-20:

```text
false_negative_total = 1
open                 = 0
closed               = 1
untracked            = 0
```

The current S22 historical false negative is therefore retained as historical quality evidence but is not an unresolved false-negative blocker.

## Boundary

This change does not:

- delete or rewrite the historical noise review;
- delete or rewrite the resolved miss;
- reduce the historical false-negative count or rate;
- alter parser behavior;
- alter canonical items or Signals;
- alter Telegram;
- alter source acquisition;
- change Miss Ledger resolution authority.
