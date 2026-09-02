# GOAL — SignalForge R5 / Gate O

## Goal

Deliver the Bangkok-only SignalForge application slice required by `VPS-Worker-Runtime-SignalForge-PRD-v1.4.5` Gate O.

## Current release boundary

- Source Registry and trigger/fetch contracts live in this repository.
- Only S13 MPT is production-enabled in R5.
- Production engine is Direct HTTP with normal TLS verification.
- Bangkok is the only canonical SignalForge node.
- Beijing must have no `/srv/signalforge`, SignalForge unit, timer, database, or business evidence.
- First successful source run is baseline-only: evidence/canonical records allowed; customer signals forbidden.
- `signalforge-run-due.service` must correlate application scheduler runs to the Worker operational Run created by the R5 Worker provider.
- No Browser/Crawlee production capability in this gate.
- No public webhook ingress in R5.

## Gate O closure

Gate O is complete only after CI and Bangkok live verification prove:

1. Bangkok-only installation and Beijing absence;
2. real MPT fixture captured through standard TLS;
3. parser and canonical tests pass;
4. first live baseline creates zero customer signals;
5. Direct HTTP + official sitemap discovery is the production path;
6. SignalForge scheduler Run stores the same Worker Run ID created for the systemd invocation;
7. worker and existing nanobot/hermes agents remain healthy.

Only after Gate O PASS may `signalforge-run-due.timer` be enabled for 24x7 MPT collection.
