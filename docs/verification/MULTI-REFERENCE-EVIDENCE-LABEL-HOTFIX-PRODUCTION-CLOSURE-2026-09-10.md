# Multi-Reference Evidence Label Hotfix — Production Closure — 2026-09-10

## Outcome

PR #138 corrects the evidence provenance reason exposed after S39 multi-reference read-layer enrichment.

Before the fix, qualification v1 appended `MULTI_REFERENCE_HTML_TITLE` whenever `reference_count > 1`, regardless of where the references came from. That was correct for DOMS but incorrect for `energy:235`, whose eleven derived package identifiers come from reviewed official text-PDF scope.

The fix changes only the explanatory qualification reason:

- `reference_numbers_evidence=HTML_TITLE` -> `MULTI_REFERENCE_HTML_TITLE`;
- `OFFICIAL_TEXT_NATIVE_PDF_SCOPE_*` -> `MULTI_REFERENCE_OFFICIAL_PDF_SCOPE`;
- other multi-reference provenance -> `MULTI_REFERENCE_EVIDENCE`.

Trust, relevance, priority, urgency, actionability and qualification-policy decision semantics are unchanged; `qualification_policy_version` remains 1.

## Verification

- Targeted qualification + opportunity tests: `12 passed`.
- Full suite: `263 passed`.
- PR #138 GitHub Actions verify run `34482888173`: PASS.
- Exact production runtime: `3700e675327cd599797fc0eaef8ddb8d0e289005`.
- Rollback: `20f2a7e8cd92671e98155bf963a291cd9a5ec3ba`.
- Exact archive SHA256: `521424aa404b32b1af54257f50a6d0c8da42e8c65e4fcda1d4cc1af115d7da82`.

Post-deploy production verification:

```text
energy:235 qualification reason = MULTI_REFERENCE_OFFICIAL_PDF_SCOPE
energy:235 reference_count       = 11
energy:235 trust/priority         = A / HIGH
doms:12735 qualification reason  = MULTI_REFERENCE_HTML_TITLE
qualification_policy_version      = 1
opportunities                     = 8 OPEN + 1 UNKNOWN
canonical_items                   = 209
signals                           = 45
Telegram pending                  = 0
DB quick_check                    = ok
acquisition timer                 = active
Telegram timer                    = active
```

No source refresh, canonical migration, signal mutation, DB schema, source registry, delivery policy, Browser/Provider/Worker/Control/Beijing change occurred.
