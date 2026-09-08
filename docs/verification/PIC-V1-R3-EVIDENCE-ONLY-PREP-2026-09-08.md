# PIC-v1 R3 Evidence-Only Live Gate Preparation — 2026-09-08

**Status:** IMPLEMENTED / LIVE TRANSPORT CREDENTIAL GATE PENDING

## Purpose

Prepare the real Bangkok-origin C0+C1+C2+C3 live verification without enabling Mac Browser Plane as a production SignalForge provider and without creating any customer/business output path.

R3 remains isolated from normal source execution:

```text
Source ID               S38 (verification-only; absent from production Source Registry)
Target                  https://www.industrymsme.gov.mm/announcements
Verification mode       EVIDENCE_ONLY
Production provider     disabled
Remote invocation flag  disabled
Browser production      disabled
Customer signals        forbidden
```

The isolated contract is:

```text
registry/Provider-Invocation-Contract-v1-r3-evidence-only.json
```

It authorizes exactly C0/C1/C2/C3 against the exact Ministry of Industry announcements URL. It is not the production provider contract.

## R3 harness

Prepare four durable ProviderRequests on Bangkok:

```text
/srv/signalforge/active/bin/signalforge provider-r3-prepare
```

The command returns one `gate_id` shared by exactly four ProviderRequests:

```text
C0_FETCH        -> browser_fetch
C1_RENDER       -> browser_render
C2_INSPECT      -> browser_inspect
C3_BROWSER_USE  -> browser_use
```

C3 uses one deterministic `snapshot` action with:

```text
side_effect_class = READ_ONLY_NAVIGATION
retry_safe        = true
```

No business parser, canonicalizer, scheduler run or signal path is invoked.

Check the gate using the returned UUID:

```text
/srv/signalforge/active/bin/signalforge provider-r3-status <gate_id>
```

`PASS` requires all of the following:

- exactly C0+C1+C2+C3 are present;
- all four ProviderRequests are `SUCCEEDED`;
- request/result SHA correlation passes;
- durable artifact file exists and its SHA/byte count matches DB metadata;
- returned final URL satisfies the request's hashed final-URL policy;
- C0 artifact is `text/html`;
- C1/C2/C3 artifacts are canonical JSON with the expected Browser Plane engine;
- S38 has zero scheduler runs, zero canonical items and zero signals.

## Mac execution order

The Provider Agent should already be running and polling before `provider-r3-prepare` is issued because R3 requests intentionally have a short 180-second TTL.

After the dedicated SSH transport exists, the Mac-side command shape is:

```text
/Users/xu/agent-browser-runtime/app/venv/bin/mac-browser-provider-agent \
  --host <dedicated-provider-ssh-host> \
  --identity-file <dedicated-provider-private-key> \
  --contract /Users/xu/Documents/mcpx-projects/signalforge/registry/Provider-Invocation-Contract-v1-r3-evidence-only.json \
  --interval-sec 2
```

The agent still executes browser capability locally through `mac-browser-mcp` stdio. No HTTP/MCP/CDP listener is opened on the Mac.

## Bangkok forced-command boundary

The release dispatcher path is:

```text
/srv/signalforge/active/bin/signalforge-provider-dispatcher
```

The release deploy script now explicitly marks both `signalforge` and `signalforge-provider-dispatcher` executable.

The future dedicated key must be bound to the dispatcher using a forced-command `authorized_keys` policy equivalent to:

```text
restrict,command="/srv/signalforge/active/bin/signalforge-provider-dispatcher" <DEDICATED_PUBLIC_KEY>
```

This must be a dedicated non-root SSH identity/key. Administrative/root SSH keys must not be reused.

The dispatcher accepts only:

```text
provider-claim-v1
provider-status-v1
provider-submit-v1
provider-fail-v1
```

## Hard Stop still outstanding

R3 cannot be executed end-to-end until the host credential boundary is explicitly installed:

1. dedicated non-root Bangkok provider SSH identity;
2. new dedicated Mac-to-Bangkok SSH key;
3. forced-command `authorized_keys` binding with forwarding/PTY/user-rc disabled;
4. Mac SSH host entry using only that identity.

Those are credential/OS-permission changes and are intentionally not created by this feature implementation.

## Rollback

Before R4, rollback is simply:

- stop the Mac Provider Agent;
- remove/disable the dedicated provider SSH authorization if it has been installed;
- leave production Mac provider flags false;
- allow any pending R3 ProviderRequests to expire.

Healthy Bangkok Direct HTTP sources remain independent throughout the R3 test.
