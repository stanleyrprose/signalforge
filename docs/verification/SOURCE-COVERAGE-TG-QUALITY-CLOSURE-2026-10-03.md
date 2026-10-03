# SignalForge Source Coverage + Telegram Quality Closure — 2026-10-03

## Objective

Improve upstream government/SOE Tender coverage and downstream Telegram usefulness before external customer onboarding.

## Source coverage changes

### S15A — Myanma Port Authority

Production was RED with repeated PROVIDER_CONTRACT_MISMATCH. The Bangkok requests were valid source_policy_version=2 requests. Root cause was the Mac Browser Provider runtime using a stale local Provider Invocation Contract that did not include S15A.

Actions:
- backed up the Mac provider contract;
- synchronized the repository Provider-Invocation-Contract-v1.json to the Mac provider runtime;
- verified SHA256 equality;
- restarted com.stanley.mac-browser-provider;
- ran the supported systemd refresh path.

Live acceptance:
- LISTING: SUCCEEDED
- DETAIL: SUCCEEDED
- PDF: SUCCEEDED
- source_state consecutive_failures=0
- source health=GREEN / reason=OK

### S21 — Myanma Railways

S21 had been retired on 2026-09-27 because the former official origin path repeatedly timed out.

On 2026-10-03 the official site was re-audited. The old /category/tender/ route is no longer valid, but the redesigned official site exposes Tender posts at:

https://www.railways.gov.mm/posts?category=tender

The live page returned HTTP 200 and contained a new Tender published 2026-10-02. The redesigned DOM uses mr-blog-card listing cards and /posts/<opaque-id> detail URLs.

Changes:
- reactivate S21 as ACTIVE_PRIMARY;
- use the new official Tender discovery URL;
- keep historical data;
- support both the current redesigned DOM and legacy WordPress fixtures;
- parse ISO listing timestamps;
- parse the current detail publication date;
- bound detail parsing to the primary article so related-Tender excerpts cannot leak another Tender's deadline into the current record;
- classify S21 as STRATEGIC_WATCH while post-reactivation stability is observed.

### S29 — DWIR

DWIR remains a known explicit coverage risk. Both Mac and Bangkok direct official-origin requests currently return HTTP 500. Search-engine caches still expose recent official DWIR Tender pages, but SignalForge does not treat cached search results as equivalent to a live authoritative issuer fetch.

Decision: keep S29 enabled and RED/diagnostic; do not bypass the issuer with unverifiable inference or mark the source GREEN.

## Telegram delivery changes

Production dry-run showed that 12 current Tender records were being blocked from Telegram. Most were blocked only because quantity_or_lot_summary was not separately normalized, even when the official procurement scope itself contained useful quantity/scale language.

Previous behavior:
- missing normalized quantity/scale => QUANTITY_OR_SCALE_NOT_EXPLAINED => no Telegram card.

New behavior:
- missing normalized quantity is no longer a hard delivery block when scope and open deadline are otherwise actionable;
- Telegram states truthfully: 数量/规模：已核验摘要未单列；详见采购内容/官方原文;
- no quantity is inferred;
- publication date is shown when known;
- explicit price/budget label becomes 预算/价格（原文）;
- deadline urgency is shown for deadlines within 72 hours using Asia/Yangon local time;
- same-day deadline without a verified time is rendered as an explicit verification warning;
- customer-scope exclusions, closed/unknown deadlines, non-Tender items and non-actionable scope remain fail-closed.

## Policy versions

- briefing_policy_version: 4
- source_scorecard_version: 8

## Verification

- focused source/TG/contract/scorecard tests: 54/54 PASS
- full suite: 617/617 PASS
- live S15A production refresh: PASS
- live redesigned Railways listing/detail parser smoke: PASS

## Product meaning

Coverage quality is measured by recoverable official Tender surfaces and customer-deliverable procurement facts, not by raw source count.

The immediate priority after this release is to monitor:
- S21 post-reactivation stability and business yield;
- S29 DWIR official-origin recovery or a reviewed official replacement surface;
- Telegram delivery volume after removing the false quantity-only gate;
- whether quantity/budget normalization should be enriched source-by-source without again becoming a global notification blocker.
