# CHECKPOINT

Date: 2026-09-02 (Asia/Yangon)
Branch: `feat/r5-mpt-gate-o`

## Completed locally

- independent private `stanleyrprose/signalforge` repository created;
- R5 Source Registry / Fetch Policy / Trigger Policy frozen;
- S13 Direct HTTP discovery corrected to official `page-sitemap.xml`;
- real Bangkok MPT detail structure captured and minimized into parser fixture;
- SQLite source/discovery/canonical/signal/scheduler state implemented;
- first-baseline signal suppression implemented;
- material NEW/UPDATED semantics implemented;
- transient detail-fetch retryability preserved after sitemap snapshot;
- Worker application correlation is fail-closed and Bangkok-only;
- Bangkok deploy script and disabled-by-default systemd timer implemented;
- focused tests and GitHub Actions workflow implemented.

## Next

1. run final minimal tests / syntax / diff review;
2. commit and push branch;
3. PR + GitHub Actions;
4. merge exact SHA;
5. deploy SignalForge to Bangkok only with timer disabled;
6. execute real baseline through `signalforge-run-due.service`;
7. verify zero signals + real MPT canonical/evidence + Worker Run correlation;
8. verify Beijing absence and both agents healthy;
9. write Gate O live evidence;
10. add closed SignalForge verbs to `vps-control-plane`;
11. enable timer only after Gate O PASS.
