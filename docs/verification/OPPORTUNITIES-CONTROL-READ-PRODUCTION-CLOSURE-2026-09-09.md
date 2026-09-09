# SignalForge Opportunities Control Read — Production Closure — 2026-09-09

## Result

**PASS / LIVE / CLOSED REMOTE READ PATH**

SignalForge already exposed the local read-only command `signalforge opportunities`. This closure proves that the same current opportunity view is safely consumable through the existing Bangkok VPS Control Plane without introducing a public API, arbitrary SSH shell, new daemon, listener, database write, scheduler mutation, Browser capability, or Beijing dependency.

## Exact production versions

- SignalForge application: `77334ea49acc494c845a4dd38413c65ac2240f6d`
- vps-control-plane policy: `007398a26b7d42a4b0edde4627f0c08b46c33998`
- installed Bangkok dispatcher SHA256: `2545deaf1d99dc1c2c021d094f26f9c70c938458550b73291b2dfeef2ce3acf3`
- previous dispatcher was preserved as `/usr/local/sbin/gha-root-dispatch.pre-007398a`

## Closed verb contract

SignalForge manifest v1 now declares:

`signalforge-opportunities -> opportunities`

The Bangkok root dispatcher accepts the verb only when all existing SignalForge guards pass:

- no argument is allowed;
- host must be Bangkok/nanobot;
- SignalForge executable/service must exist;
- the live SignalForge versioned manifest must contain the exact verb;
- execution is delegated as the dedicated `signalforge` user;
- command is exactly `signalforge opportunities`.

No URL, source ID, shell fragment, filesystem path, SQL, or arbitrary application argument is accepted.

## Fail-closed rollout

Rollout order deliberately installed the application manifest before the new dispatcher.

Before the dispatcher update, live Bangkok invocation:

`SSH_ORIGINAL_COMMAND=signalforge-opportunities /usr/local/sbin/gha-root-dispatch`

returned:

- exit `126`;
- `DENY: command is not allowlisted`.

This proves the intermediate rollout state failed closed.

After the reviewed dispatcher was installed, an extra-argument negative test:

`signalforge-opportunities extra`

still returned exit `126`.

## Bangkok live read

The final closed dispatcher invocation returned:

- status `PASS`;
- count `9`;
- `OPEN=8`;
- `UNKNOWN=1`;
- `EXPIRED=0`.

Canonical keys at the verification snapshot:

- `industry:1022`
- `industry:1034`
- `energy:235`
- `mofa:59800`
- `industry:1037`
- `industry:1036`
- `industry:1039`
- `industry:1035`
- `doms:12735`

The read is signal-backed and canonical-deduplicated; it does not create or modify canonical items or signals.

## GitHub Actions end-to-end gate

The production GitHub Actions workflow `VPS Control` was manually dispatched with:

- `target=bangkok`
- `operation=signalforge-opportunities`
- empty `worker_arg`

Run ID: `34318367015`.

The run completed **SUCCESS**. It checked out exact Control Plane main `007398a26b7d42a4b0edde4627f0c08b46c33998`, selected Bangkok, installed the dedicated Actions SSH material, resolved the closed no-argument operation, and invoked the forced-command SSH channel. The remote output was the same live SignalForge opportunity view: `9` rows, `8 OPEN + 1 UNKNOWN`.

This proves the supported automation path is:

`GitHub Actions -> restricted Actions SSH key -> forced root dispatcher -> live SignalForge manifest validation -> signalforge user -> signalforge opportunities`

It does not depend on the Mac administrator SSH key or an unrestricted remote shell.

## Beijing invariant

No Control Plane or SignalForge deployment was performed on Beijing for this slice.

A read-only negative probe on Beijing for `signalforge-opportunities` returned:

- exit `126`;
- `DENY: command is not allowlisted`.

Beijing therefore remains outside SignalForge production topology.

## Scheduler / database post-gate state

At 2026-09-09 12:45 Myanmar time, after timer restoration, a natural Bangkok `signalforge-run-due.service` invocation completed `SUCCESS` on the new application release.

Final verified production state:

- SignalForge active release: `77334ea49acc494c845a4dd38413c65ac2240f6d`;
- timer: enabled / active;
- run-due service: inactive after successful completion;
- overall status: `PASS / GREEN`;
- non-GREEN sources: none;
- canonical items: `193`;
- signals: `42`;
- recovery backlog: `0`;
- SQLite quick check: `ok`;
- closed opportunity read: `PASS / 9 / 8 OPEN + 1 UNKNOWN`.

## Product implication

SignalForge now has a minimal externally consumable, still-closed read path for authorized automation agents. A public HTTP API, Telegram push service, webhook delivery layer, dashboard, or relevance-ranking engine is not required to consume the current opportunity set.

The next product decision should therefore be driven by user value: either define explicit commercial relevance/prioritization rules, or add a delivery channel only when push delivery is actually required.
