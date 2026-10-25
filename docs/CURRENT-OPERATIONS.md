# SignalForge operational evidence and open boundaries

This file separates approved requirements, implementation, deployment and dated production observations. Requirements live in [GOAL](../GOAL.md), [Tender PRD](PRD-v2.0-TENDER-CORE.md) and [news contract](S01-S52-S53-NEWS-DELIVERY-CONTRACT.md). Repository code is GitHub-owned; actual installed SHAs come from runtime release markers plus the merged PR deployment evidence. A dated observation is not a permanent live-health claim.

## Verified observation — 2026-10-25 21:49 Asia/Yangon

SignalForge Mac and Bangkok runtime: `431cc0a32aaf7440c08c5b2b6c71ab8e90ba1773`, PR [#328](https://github.com/stanleyrprose/signalforge/pull/328). Newspaper producer: `bac371e3885736a8b8e463fb807de7db9dc34172`, macmini_automation PR22. Bangkok newspaper transport v2.2 retains its own component release marker; its differing SHA is not app drift.

| Product/date | Observed production result | Receipts / cleanup |
| --- | --- | --- |
| S01 Oct25 | 202 articles reviewed; 150 unchanged suppressed; 52 new/changed Chinese stories; Markdown 91375 bytes | Digest484 + Markdown487; independent ledgers; both hosts' task content removed |
| km Oct25 | 144 news; Chinese PDF + AI Digest | Digest476 + PDF477; both hosts COMPLETE cleanup |
| mal Oct25 | 143 news; Chinese PDF + AI Digest | Digest478 + PDF479; both hosts COMPLETE cleanup |
| Tender Oct25 | 28 sources attempted, 27 succeeded; S20 timeout | Four tenders470–473; daily report485; COMPLETE_WITH_SOURCE_FAILURES |

S01's superseded PDF UNKNOWN remains historical ledger evidence, not an active Markdown failure; failure notice486 was sent. It was not reset/retried. The body-format replacement was explicitly requested by the owner after Digest receipt. Minimum hashes/receipts survive content deletion.

Mac S01 and newspaper agents were loaded with last exit0; Bangkok due/Assurance/telemetry timers enabled. Database quick_check=ok. Translation and Provider queues contained only terminal states. Main CI for431cc0a passed.

## Remaining conditions and recovery work

- S20 pages return200 through Mac HTTP, Bangkok HTTP and installed Browser Plane C0. Five listing candidates were parsed; three sampled detail pages parsed, but all three issuer-linked PDF HEADs returned404. Missing attachment facts remain unknown. Source availability and evidence completeness are separate; do not guess download URLs or tender fields. No new official PDF evidence was found.
- Eight PUBLIC_READ_ACQUIRE successes in the last24h lacked Route Summary. The installed Mac Provider module lacked the already-merged serializer. It has now been aligned to GitHub mac-browser-plane main d6af131998e122f0ba8f44bfc87fd884a78f6637, with backup/hash/rollback. Real request578722d1-0e3e-48df-b321-dc25b9d476b7 returned200,88198 bytes, C0_FETCH/system_curl and full Route Summary; Tender counters were unchanged. Module SHA256=0b813c3b85ff812e110041a1f662a92a0e1d0b8755e6cdfdc27c4168be560135. New-request route recording is verified; the rolling24h gate remains RECOVERING until historical anomalies leave the window. Historical missing telemetry must not be fabricated or used to stop healthy business dispatch.
- The pending scheduler change prioritizes the current due S01 date and attempts at most one historical pending date independently. Its implementation, verification, merge and deployment must each have evidence; the431cc0a observation above does not validate this change.
- A superseded Oct24 candidate contains202 identities all represented in later confirmed delivered versions. This establishes identity-level supersession, not exact old raw-body equality. Retirement completed at2026-10-25T16:21:24Z after both-host checks: SUPERSEDED_NOT_DELIVERED, minimum audit retained, exact candidate PDF/manifest removed; no resend. See old-candidate-retirement-proof.json.
- Newspaper numerical aliases now have a prospective canonical home in the News inventory. Historical km/mal receipts preserve their original identities.

## Evidence locations

Private, non-Git evidence resides under Mac `~/Library/Logs/SignalForge/acceptance-20261025/`, S01 `~/Library/Application Support/SignalForge/S01Daily/` and newspaper central minimum receipts. Bangkok owns `state/s01-news-ledger.sqlite`, `state/newspaper-digest-receipts/`, daily-cycle checkpoints and the Tender DB. Do not commit downloaded content, runtime databases or credentials.

Full document governance: [authority](DOCUMENT-AUTHORITY-AND-CONSISTENCY-20261024.md). Historical handoff checkpoints: [takeover archive](NEWS-TAKEOVER-AUDIT-20261024.md). Neither this dated evidence nor a CI run alone proves full project closure.
