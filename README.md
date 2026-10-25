# SignalForge

SignalForge has two approved, independently controlled Myanmar intelligence products. Bangkok owns production Telegram delivery; Mac may perform approved source processing.

**Tender Core:** `official tender source -> acquisition/parser -> canonical tender -> NEW/UPDATED signal -> readiness/translation -> Telegram`.

**News/Policy (S01/S52/S53):** `daily official news/newspapers -> extraction/OCR -> Chinese translation -> PDF + AI Digest -> Bangkok Telegram -> independent receipts -> temporary-file cleanup after successful delivery`.

Current news behavior follows [the Oct 25 owner amendment](docs/NEWS-PROCESSING-POLICY-20261025.md): force readable low-confidence items as 待核, mark/skip unreadable pages, and remove all task content after both TG receipts. This amendment is implemented only on a development branch and is not deployed.

See `GOAL.md`, `docs/S01-S52-S53-NEWS-DELIVERY-CONTRACT.md` and `AGENTS.md`. The two products have separate schedules, source identities, deduplication, delivery receipts and health metrics. The repository still excludes precursor tracking, multi-tenant/customer profiles and pilot feedback. This describes the approved product scope; it is not a claim that all three news sources have passed live production acceptance.

## Source of truth

GitHub `stanleyrprose/signalforge` is the sole source of truth. `main` is the accepted baseline; development branches are pushed as work-in-progress only when repository workflow rules allow it. Local worktrees are disposable and must never become an independent source of truth.

## Primary delivery

```sh
signalforge telegram-deliver --dry-run
signalforge telegram-deliver
```

`telegram-deliver` sends each undelivered formal tender Signal once. Sector and priority metadata do not suppress a formal `TENDER`. Delivery remains fail-closed for correctness/readiness problems and untranslated Myanmar text.

A notice prioritizes buyer, procurement scope, quantity/lot, explicit amount when present, deadline/opening date, tender number, location and official source. Missing source facts remain missing; they are not synthesized.

## Reliability surfaces

```sh
signalforge status
signalforge assurance-status
signalforge assurance-run --no-network
signalforge source-scorecard
signalforge business-kpis
signalforge misses
signalforge noise-samples
```

Assurance, source health, missed-signal review, noise sampling, evidence retention, OCR and translation are retained because they directly protect tender delivery quality.

## Local development

Follow `AGENTS.md`. During implementation do not run tests or CI. After explicit review/authorization, the standard verification commands are:

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q signalforge tests
python -m json.tool registry/Source-Registry-v1.yaml >/dev/null
sh -n bin/signalforge
sh -n deploy/deploy-signalforge-release.sh
```

## Production layout

```text
/srv/signalforge/
  active -> releases/<signalforge-sha>
  releases/
  venvs/<signalforge-sha>/
  state/signalforge.db
  evidence/
  artifacts/
  tmp/
  locks/
```

Formal SignalForge Telegram dispatch is Bangkok-owned; approved acquisition, OCR, translation and rendering may run on Mac. Runtime state, credentials, evidence and databases are not stored in Git.
