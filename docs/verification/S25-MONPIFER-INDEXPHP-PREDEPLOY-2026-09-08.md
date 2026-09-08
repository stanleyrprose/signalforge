# S25 MONPIFER index.php path regression — pre-deploy checkpoint

Date: 2026-09-08 (Asia/Yangon)

Status: SOFTWARE FIX MERGED / BANGKOK DEPLOYMENT PENDING

## Incident

Bangkok SignalForge health became RED because S25 MONPIFER accumulated repeated:

```text
MonpiferParseError: no recognized MONPIFER tender rows
```

This failure predates and is independent of Provider Invocation Contract R3 work.

## Root cause

The issuer page remains live and structurally exposes the same tender table, but Drupal now emits front-controller links through `/index.php/...`:

```text
/index.php/sites/default/files/tender_pdf/...
/index.php/my/ministry-article/...
```

The existing parser only admitted:

```text
/sites/default/files/tender_pdf/...
/my/ministry-article/...
```

The row content, deadline format, tender semantics and issuer host did not require a broader parser/runtime change.

## Live evidence

Mac Browser Plane C0 and C2 were used against:

```text
https://www.monpifer.gov.mm/my/ministry-tenders
```

Results:

- C0 strict-TLS fetch: HTTP 200, 67,113 bytes.
- C2 inspect: HTTP 200; page title `Tenders | Ministry of National Planning, Investment and Foreign Economic Relations`.
- The current page still exposes the five-column tender table: `Last Date / Tender Description / Tender PDF / Tender Department / Read More`.
- Current live hrefs resolve through `/index.php/...`.
- The pre-fix parser reproduced the production failure against that live evidence: zero recognized tenders and `MonpiferParseError`.

## Fix

Merged PR #81 to `main` as:

```text
aafa4195d2b747226a379e668911f7f686287c78
```

The fix:

- accepts only the optional issuer-local `/index.php/` front-controller prefix;
- keeps the existing HTTPS + MONPIFER host allowlist;
- keeps the existing article and tender-PDF path allowlists;
- normalizes article URLs back to `/my/ministry-article/<alias>` so canonical identity remains `monpifer:<article_alias>`;
- preserves the issuer-advertised PDF locator as metadata only;
- adds no dependency, schema, scheduler, Browser-production or PIC authority change.

## Verification

```text
python3 -m pytest tests/test_monpifer.py -q
4 passed

python3 -m pytest -q
192 passed
```

GitHub PR verification also passed before merge.

## Production boundary

The software repair is merged but is not yet deployed to Bangkok.

Existing `vps-control-plane` authority still does not include a SignalForge application-deploy verb. Its generic `deploy` operation deploys the VPS agent release, while SignalForge operations remain limited to status/run/refresh/pause/resume.

CodexPro also cannot currently reuse the operator's normal Bangkok administrative SSH identity. The `vps-bkk` host alias is unavailable in the controlled environment, and the earlier direct root path did not have usable authentication.

Do not solve this by broadening the privileged dispatcher or copying an administrative private key into the automation context.

## Next production action

Deploy exact SignalForge SHA:

```text
aafa4195d2b747226a379e668911f7f686287c78
```

through an already-authorized Bangkok administrator channel, then:

1. verify `signalforge status`;
2. run a bounded `S25` refresh;
3. confirm S25 returns SUCCESS and source health GREEN;
4. confirm canonical identity did not duplicate existing MONPIFER records;
5. confirm scheduler backlog remains zero and other sources remain unaffected.

This production deployment remains separate from the PIC R3 credential gate.
