# S01 daily publication — Mac launchd

Current contract: [daily news](S01-S52-S53-NEWS-DELIVERY-CONTRACT.md); dated deployment and actual receipts: [operations](CURRENT-OPERATIONS.md). This scheduler covers S01 Markdown + Digest only. Newspaper and Tender jobs remain separate.

- Source: `deploy/com.stanley.signalforge-s01-news-daily.plist`; wrapper `deploy/run-s01-news-daily.zsh`; Python `signalforge.s01_daily_schedule`.
- Calendar trigger17:00 in Mac local time, with hourly StartInterval3600 and RunAtLoad. Confirm the Mac timezone is Asia/Yangon. Before17:00 Yangon, latest due date is yesterday.
- One successful edition per date. Current due date first; at most one older pending date is additionally attempted per invocation. Failure/corruption in a historical journal cannot prevent the current date from being attempted. Successful dates reuse receipts and perform cleanup-only recovery; no reacquisition/resend.
- Existing prepared manifests and retained acquisition/validated AI work are reused. PENDING/UNKNOWN component outcomes require reconciliation; the other component can still proceed. Article-level unreadability stays audit-visible and does not suppress successful content.
- The current worker uses authenticated Mac Codex CLI. Quota failure requests a separately deduplicated Bangkok notice and retains progress. The product does not permanently require that Provider.
- Formal sending occurs on Bangkok; its independent ledger is the authority for sends. Mac imports checksum-bound selected-body/Digest receipts before both-host content cleanup.
- Inspect launchd exit status, `~/Library/Logs/signalforge-s01-news-daily.*.log`, daily journals, local/remote receipts and actual message IDs. A loaded timer is not delivery evidence.

## Protected-directory staging

launchd cannot reliably open Documents scripts under macOS privacy controls. Stage the merged release's `signalforge` package and wrapper under `~/Library/Application Support/SignalForge/runtime`; install the plist under `~/Library/LaunchAgents`. Persist repository/SHA in runtime/release.json. Never edit staged code as SOT. Before replace/restart, verify no S01 task is running, retain rollback, and preserve ledgers/pending content.

The current-day-priority change requires its own affected-path verification, CI and deployment evidence; older production results do not validate unshipped changes.
