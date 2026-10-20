# S01 autonomous daily publication (Mac launchd)

Scope: S01 news PDF + Chinese Digest only. Tender Core and MOI newspaper timers remain unchanged.

- Deploy after focused verification, PR/CI/Merge and explicit production authorization.
- Use `deploy/com.stanley.signalforge-s01-news-daily.plist` for the user LaunchAgent.
- Configured for **17:00 Mac local time**; confirm Mac time zone is `Asia/Yangon` before production activation. Runtime edition date is calculated in `Asia/Yangon`.
- The wrapper invokes the existing guarded runner with explicit `--publish`. It reuses the Bangkok S01 sender and existing separate receipt/cleanup protocol.
- One scheduled invocation per day. A Mac shutdown or sleep may skip the event; launchd calendar triggers alone provide no durable catch-up. Do not interpret timer presence as actual delivery.
- Inspect the wrapper exit status, `~/Library/Logs/signalforge-s01-news-daily.*.log`, S01 local/remote receipt ledgers and real Telegram messages before declaring PASS.
- An interrupted or ambiguous Telegram send must be reconciled against receipt state before retrying, not blindly resent. A failed article can remain audit-visible and must not automatically suppress an otherwise valid partial edition.
- The runner currently requires an authenticated **Codex CLI** to perform its AI Chinese review. Cloud GPT migration is separate scope; if Codex is unavailable, fail without pretending to publish.
- This release artifact does not install or enable the LaunchAgent, run a job, send messages, change credentials or modify production.

## macOS protected-directory production workaround

launchd background services cannot reliably open a script inside Documents due to macOS privacy controls. Before bootstrap, stage the GitHub-main source's `signalforge` package and `deploy/run-s01-news-daily.zsh` under `~/Library/Application Support/SignalForge/runtime`; copy the plist to `~/Library/LaunchAgents`. Keep the staged package synced with the merged release and do not edit it as a source of truth.
