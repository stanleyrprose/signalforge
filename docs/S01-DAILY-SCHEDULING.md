# S01 autonomous daily publication (Mac launchd)

Scope of this scheduler: S01 news PDF + Chinese Digest only. Project-wide daily news coverage additionally requires independent S52 and S53 newspaper jobs per `S01-S52-S53-NEWS-DELIVERY-CONTRACT.md`. This Mac launchd file is not evidence that S52/S53 are scheduled or that S01 actually delivered. Tender Core and existing MOI newspaper timers remain separately managed.

- Deploy after focused verification, PR/CI/Merge and explicit production authorization.
- Use `deploy/com.stanley.signalforge-s01-news-daily.plist` for the user LaunchAgent.
- Configured for **17:00 Mac local time**; confirm Mac time zone is `Asia/Yangon` before production activation. Runtime edition date is calculated in `Asia/Yangon`.
- The wrapper invokes `signalforge.s01_daily_schedule`, which prepares through the guarded runner and explicitly transfers the immutable edition through the Bangkok S01 sender. Tender Core is outside this path.
- One completed edition per Yangon date, due at 17:00. Hourly and load-time checks resume the oldest started unfinished date, reuse a prepared manifest, and consult durable per-artifact receipts after an interrupted transfer. Before 17:00, the latest due date is yesterday. They do not substitute an old source issue for a new one. Unknown Telegram outcomes remain blocked by the Bangkok sender. A completed date does not reacquire or resend; cleanup retries remain independent. Timer presence still does not prove actual delivery.
- Inspect the wrapper exit status, `~/Library/Logs/signalforge-s01-news-daily.*.log`, S01 local/remote receipt ledgers and real Telegram messages before declaring PASS.
- An interrupted or ambiguous Telegram send must be reconciled against receipt state before retrying, not blindly resent. A failed article can remain audit-visible and must not automatically suppress an otherwise valid partial edition.
- The runner currently requires an authenticated **Codex CLI** to perform its AI Chinese review. Cloud GPT migration is separate scope; if Codex is unavailable, fail without pretending to publish.
- This release artifact does not install or enable the LaunchAgent, run a job, send messages, change credentials or modify production.

## macOS protected-directory production workaround

launchd background services cannot reliably open a script inside Documents due to macOS privacy controls. Before bootstrap, stage the GitHub-main source's `signalforge` package and `deploy/run-s01-news-daily.zsh` under `~/Library/Application Support/SignalForge/runtime`; copy the plist to `~/Library/LaunchAgents`. Keep the staged package synced with the merged release and do not edit it as a source of truth.
