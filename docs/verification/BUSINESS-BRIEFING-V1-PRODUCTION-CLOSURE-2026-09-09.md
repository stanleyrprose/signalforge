# Business Briefing v1 — Production Closure — 2026-09-09

## Result

> **COMPLETE / PASS**

SignalForge now exposes a deterministic, read-only business briefing derived from the existing qualified current-opportunity view. The briefing is a delivery contract for ChatGPT or another authorized agent; it does not contain an LLM and does not mutate business state.

## Exact releases

SignalForge implementation PR #108 merged as:

`a61f9f7e7ef0af9be22bafd778f17bfe5f3a5ebc`

Immediate application rollback target:

`08153c47b1efc67c85776f551da2e1130b2d1c63`

SignalForge deployment archive SHA256, identical locally and on Bangkok:

`b056278fc0aad8f3a70c80789031ba33a08c2b42edbd95e0d15cf72220023d38`

Matching Control Plane read verb PR #16 merged as:

`061d260c3dddddac64d82107929e96cb7c85fe98`

Installed Bangkok dispatcher SHA256:

`fcd15ba510b300c3bb511bb8a3f7c6765d7b2c2afdd55a19a83b3791e64862d3`

Previous dispatcher was preserved as `/usr/local/sbin/gha-root-dispatch.pre-061d260`.

## Briefing contract

New local CLI:

`signalforge briefing`

New closed manifest verb:

`signalforge-briefing -> briefing`

Policy version:

`briefing_policy_version=1`

The briefing consumes `signalforge opportunities` and does not query issuers itself. It expands only opportunities whose `priority_band` is `HIGH` or `REVIEW`.

Attention actions are deterministic:

- `ACT_NOW`: HIGH and <=72h urgency
- `PRIORITIZE`: other HIGH opportunities
- `REVIEW`: qualified REVIEW opportunities requiring human follow-up

MEDIUM opportunities are not expanded into attention rows. They are retained as a compact watchlist with count, primary-relevance counts and canonical keys.

Every attention row carries current canonical facts and provenance needed by an external renderer:

- canonical key
- attention action
- priority / trust / relevance / urgency
- issuer and title
- reference number(s)
- deadline facts
- evidence level / completeness
- bounded scope excerpt
- deterministic `why_now` reason codes
- latest signal provenance
- official URL

The delivery contract explicitly states `facts_must_not_be_inferred=true` and `generator=external_agent_or_chatgpt`.

## Tests

SignalForge:

- targeted briefing/contract/opportunity/qualification tests: `13 passed`
- full suite: `227 passed`
- `git diff --check`: PASS

Control Plane:

- dispatcher bash syntax: PASS
- manifest validator py_compile: PASS
- CI PR #16: PASS
- `git diff --check`: PASS

## Production-DB preview

Before deployment, a SQLite backup of the live Bangkok production DB was evaluated using the implementation branch.

Result:

- current opportunities: `9`
- attention: `4`
- `ACT_NOW=1`
- `PRIORITIZE=2`
- `REVIEW=1`
- MEDIUM watchlist: `5`

The four attention rows were:

1. `industry:1022` — `ACT_NOW / HIGH / INDUSTRIAL`
2. `energy:235` — `PRIORITIZE / HIGH / ICT`
3. `mofa:59800` — `PRIORITIZE / HIGH / ICT`
4. `doms:12735` — `REVIEW / REVIEW / MEDICAL`

No production DB state was modified by the preview.

## Fail-closed rollout

The SignalForge application and manifest were deployed before the Control Plane dispatcher.

In this intermediate state:

`SSH_ORIGINAL_COMMAND=signalforge-briefing /usr/local/sbin/gha-root-dispatch`

returned:

`126 / DENY: command is not allowlisted`

This proved that the application capability did not become remotely reachable before the reviewed Control Plane policy was installed.

After Control Plane deployment:

- `signalforge-briefing extra` returned `126`
- valid `signalforge-briefing` returned `PASS`
- valid result was `attention=4`, `ACT_NOW=1 / PRIORITIZE=2 / REVIEW=1`, watchlist `5`
- Beijing received no deployment and a read-only probe remained `126 / DENY`

The forced dispatcher still validates the SignalForge verb manifest before invocation and runs the application as the dedicated `signalforge` user.

## Final production state

After timer restoration:

- active SignalForge application: `a61f9f7e7ef0af9be22bafd778f17bfe5f3a5ebc`
- Bangkok timer: enabled / active
- overall SignalForge: `PASS / GREEN`
- canonical items: `194`
- signals: `44`
- recovery backlog: `0`
- DB quick check: `ok`

The briefing rollout changed no canonical item and created no signal.

## Boundary

Business Briefing v1 does **not** add:

- Telegram / Feishu / email delivery
- credentials or secrets
- public HTTP API
- new listener or daemon
- natural-language generation inside SignalForge
- ML ranking
- personalized scoring profile
- DB write path
- acquisition change
- Browser or Provider capability change
- Beijing dependency

The next product decision is delivery cadence/channel. The briefing contract is intentionally reusable by ChatGPT, GitHub Actions, Telegram, Feishu or another authorized consumer without changing the evidence/canonical/signal core.
