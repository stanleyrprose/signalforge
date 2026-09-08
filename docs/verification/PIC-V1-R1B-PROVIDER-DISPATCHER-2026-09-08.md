# PIC-v1 R1B Restricted Provider Dispatcher — 2026-09-08

**Status:** FEATURE IMPLEMENTATION / CI GATE PENDING

## Contract

The future dedicated Mac->Bangkok SSH key is intended to be forced directly into:

```text
bin/signalforge-provider-dispatcher
```

The executable reads only `SSH_ORIGINAL_COMMAND` and recognizes exactly:

```text
provider-claim-v1
provider-status-v1
provider-complete-v1
provider-fail-v1
```

It does not parse or execute shell commands. Commands with arguments, whitespace variants, or unknown verbs are denied.

`provider_id` is not client-controlled. The dispatcher is pinned in code to `mac-mm-01`.

`complete` and `fail` accept one bounded JSON stdin object with an exact field set. Extra fields are rejected. The dispatcher emits compact JSON only and suppresses traceback/environment details across the SSH boundary.

## Host-level hardening required before live use

The dispatcher code alone does not authorize or install SSH access. Live R1B requires a separately approved host change:

- dedicated non-root Bangkok OS identity;
- dedicated Mac->Bangkok SSH key, not the administrative/root key;
- authorized_keys forced-command binding;
- `no-pty`;
- `no-agent-forwarding`;
- `no-port-forwarding`;
- `no-X11-forwarding`;
- `no-user-rc`;
- no generic Worker verb access.

That credential/privilege change is a Hard Stop and is intentionally not performed by this feature branch.

## Production boundary

Still unchanged:

```text
production_enabled=false
remote_invocation=false
browser_production_approved=false
```

No provider-backed active source exists yet.
