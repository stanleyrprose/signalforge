# Jev Production Shadow Review — 2026-09-19

## Read-only production snapshot

- Bangkok active release: d0bab7f89707893d75f751d532b089c7ea04739d
- production DB: /srv/signalforge/state/signalforge.db
- SQLite quick_check: ok
- snapshot size: 52,817,920 bytes
- snapshot SHA256: 5c9f860165a8e04476a6bee70d83c660ec067b254032edd6a311b2b2054fd058
- canonical_items: 245
- signals: 66
- SignalForge timers: all active

The source DB was opened read-only and copied with SQLite online backup. Jev evaluation ran locally on Mac. No production DB write or Telegram action occurred.

## Shadow result

Current opportunities: 16.

- agreements: 12
- disagreements: 4
- deterministic include: 7
- Jev include: 11
- JEV_ONLY: 4
- DETERMINISTIC_ONLY: 0

Reviewed disagreement outcomes:

- industry:1037 — confirmed deterministic false negative; engineering/environmental-control equipment.
- industry:1044 — confirmed deterministic false negative; explicit construction work.
- industry:1040 — Jev over-inclusive; retain OUT_OF_SCOPE.
- industry:1035 — Jev threshold-edge over-inclusive; retain OUT_OF_SCOPE.

## Deterministic correction

Added narrowly reviewed engineering text coverage for:

- environmental control system
- issuer misspelling variant: enviromental control system
- Burmese construction term: တည်ဆောက်ခြင်း

Post-fix replay:

- industry:1037 -> ENGINEERING / include
- industry:1044 -> ENGINEERING / include
- industry:1040 -> OUT_OF_SCOPE / exclude
- industry:1035 -> OUT_OF_SCOPE / exclude

Validation:

- targeted mission + Jev tests: 7 passed
- full pytest suite: 446 passed
- git diff --check: PASS

Jev remains SHADOW_ONLY. Deterministic SignalForge policy remains authoritative.
