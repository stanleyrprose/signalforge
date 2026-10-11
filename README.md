# SignalForge

SignalForge is a Bangkok-only Myanmar government/SOE tender notification application.

Its single product path is:

`official source -> acquisition/parser -> canonical tender -> NEW/UPDATED signal -> readiness/translation -> Telegram`

The active repository intentionally excludes early-project precursor tracking, multi-tenant/customer profiles, pilot feedback, strategic/news feeds, and a separate business-digest product.

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

Production is Bangkok-only. Runtime state, credentials, evidence and databases are not stored in Git.
