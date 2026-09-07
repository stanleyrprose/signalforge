# GOAL — SignalForge Myanmar Source Expansion

## Goal

Expand SignalForge across high-value Myanmar issuer-original sources while preserving the proven v1.5 local acquisition contract and the existing Worker / Control / Fleet boundaries.

## Frozen production boundary

- SignalForge production remains Bangkok-only.
- Beijing remains Generic Worker only and SignalForge-free.
- Direct HTTP remains the default production acquisition method.
- One SignalForge scheduler/service invocation creates one Worker operational Run; source/business jobs and acquisition attempts remain internal SignalForge state.
- `AcquisitionRequest` and `AcquisitionAttempt` are not Worker Runs.
- Worker DB has no SignalForge source/canonical/acquisition business semantics.
- Source adapters follow real issuer shape; there is no universal tender parser requirement.
- TLS/HTTP failures stay fail-closed and do not silently become certificate bypass or Browser escalation.
- Browser execution belongs only to the Mac Browser Plane; VPS Browser/Crawlee R3 is superseded. SignalForge→Mac unattended production invocation remains disabled until a separate Provider Invocation Contract is approved; Browserless/PDF/distributed coordination remain evidence-triggered future capabilities.

## Current production sources

### S10 — DICA Company and Investment Announcements

- production-enabled; first S10 onboarding release was `3f31b937cc8dbe2941e85b1f810f2bd8a9b811fb`;
- issuer-hosted `ACTIVE_SELECTIVE` company/investment event source;
- current page-1 baseline produced 12 `REGULATORY_NOTICE` items: 9 `COMPANY_STRIKE_OFF_BATCH`, 1 `COMPANY_COMPLIANCE_NOTICE`, 1 `INVESTMENT_TAX_INCENTIVE`, 1 `INVESTMENT_CAPITAL_CURRENCY`;
- canonical identity is stable DICA WordPress post ID (`dica-notice:<post_id>`), so publication-date corrections do not create duplicate canonical items;
- first baseline metrics: `items_parsed=12`, `tenders_parsed=0`, health sample `details_attempted=4`, `details_succeeded=4`, zero customer signals;
- official PDFs remain metadata-only in P0 and primary acquisition fetched zero PDFs;
- S10 is the first production source to prove that PDF content would materially improve business detail, so `pdf_value_gate=TRIGGERED`;
- PDF extraction/runtime packaging remains explicitly `DEFERRED_ZERO_DEPENDENCY`; no pypdf/pdftotext/OCR dependency was added;
- source health GREEN;
- evidence: `docs/verification/S10-SOURCE-ONBOARDING-2026-09-04.md`.

### S12 — IRD Business Tax Announcements

- production-enabled; first S12 onboarding release was `d5222d00e81692ae4f4b8ee3d0a3d7ad70618237`;
- issuer-original `ACTIVE_SELECTIVE` tax/regulatory source;
- current first page discovers 16 deterministic announcement records; 180-day baseline fetched 14 details and selected 9 business tax notices;
- canonical domain is `REGULATORY_NOTICE`; categories currently include TAX_REGISTRATION, TAX_FILING, TAX_PAYMENT and TAX_EXEMPTION;
- IRD tenders, anti-corruption campaigns and institutional/noise records are explicitly excluded from S12 P0;
- first baseline metrics: `items_parsed=9`, `tenders_parsed=0`, `details_attempted=9`, parse `9/9 = 1.0`, zero customer signals;
- official PDFs remain metadata-only with safe percent-encoding; primary pipeline fetched zero PDFs;
- issuer record identity is preserved; same-day Myanmar/English legal records are not heuristically merged;
- source health GREEN;
- evidence: `docs/verification/S12-SOURCE-ONBOARDING-2026-09-04.md`.

### S13 — MPT Tender Information

- production-enabled;
- Direct HTTP / issuer sitemap + structured detail parser;
- source health GREEN.

### S07 — Myanmar Customs Notifications

- production-enabled; first Customs Notifications onboarding release was `edf3e342ad127b4beac93a285bfb0096a1815aaa`;
- issuer-original `REGULATORY_NOTICE` source;
- listing-complete Direct HTTP shape: one `/notifications` HTML acquisition directly yields current business records;
- canonical identity is normalized issuer notification/order number (`customs-notice:<ref>`);
- first baseline created 5 regulatory canonical items and zero customer signals;
- baseline metrics: `items_parsed=5`, `tenders_parsed=0`, `details_attempted=0`;
- official PDF links remain metadata-only and are not fetched by the primary pipeline;
- parse health uses `BUSINESS_PROCESSING`; first production sample `1/1 = GREEN`;
- source health GREEN;
- evidence: `docs/verification/S07-SOURCE-ONBOARDING-2026-09-04.md`.

### S08A — Myanmar Customs Auction Announcements

- production-enabled; first Customs Auction onboarding release was `cb5291fdfcc13a678f63b53072e39089f8c27258`;
- `ACTIVE_SELECTIVE` auction-opportunity slice from the mixed Customs Announcements page;
- canonical domain is `AUCTION_NOTICE`; tender-award/result records remain explicitly excluded from this slice;
- visible issuer publication text is authoritative because the current HTML `datetime` attribute is stale (`2025-05-13`);
- first baseline created 4 auction canonical items and zero customer signals;
- baseline metrics: `items_parsed=4`, `tenders_parsed=0`, `details_attempted=0`;
- official PDF paths are safely percent-encoded as metadata only; current PDFs are mixed text-native/scan and are not fetched by the primary pipeline;
- no OCR/PDF parser/Browser capability was introduced;
- parse health uses `BUSINESS_PROCESSING`; source health GREEN;
- evidence: `docs/verification/S08A-SOURCE-ONBOARDING-2026-09-04.md`.

### S05A — Ministry of Commerce Trade Notifications

- production-enabled; first regulation-domain onboarding release was `3c833d62dcf16ecd9e4b12dafd9ac557417efddb`;
- first production `REGULATORY_NOTICE` domain slice, explicitly not represented as a tender;
- `ACTIVE_SELECTIVE` Myanmar-language Drupal Notifications discovery;
- current baseline created 3 regulatory canonical items and zero customer signals;
- baseline metrics: `items_parsed=3`, `tenders_parsed=0`, parse `3/3 = 1.0`;
- official PDF links are preserved as metadata only and are not fetched in the primary pipeline;
- source health GREEN;
- evidence: `docs/verification/S05A-SOURCE-ONBOARDING-2026-09-04.md`.

### S20 — MOEP Main Tender Hub

- production-enabled; first onboarding release was `255f18f3dd919b6e77b9d3138839f0439062e3bc`;
- `ACTIVE_SELECTIVE` HTML-first source;
- official discovery: `https://moep.gov.mm/mm/ignite/page/62`;
- current first page exposes five latest tenders with issuer/date/summary/detail URL;
- first production baseline parsed 5/5 detail pages and created zero customer signals;
- source health GREEN / parse `5/5 = 1.0`;
- current advertised PDF attachments are degraded (`0/5` retrievable, HTTP 404) but are metadata-only and non-blocking;
- no PDF parser or Browser capability is in the primary pipeline;
- evidence: `docs/verification/S20-SOURCE-ONBOARDING-2026-09-04.md`.

### S21 — Myanma Railways Tenders

- production-enabled;
- Direct HTTP / category-list discovery + multi-item detail parser;
- first production baseline parsed 45 business tenders from 10 detail pages;
- first baseline created zero customer signals;
- source health GREEN;
- evidence: `docs/verification/S21-SOURCE-ONBOARDING-2026-09-04.md`.

### S22 — Inland Water Transport Tenders

- production-enabled;
- Direct HTTP / Drupal tender-list discovery + one-detail/one-business-item parser;
- current HTML exposes title, scope, publication time, closing time and attachment metadata;
- first production baseline parsed four audited 2026 tender nodes;
- first baseline created zero customer signals;
- source health GREEN;
- evidence: `docs/verification/S22-SOURCE-ONBOARDING-2026-09-04.md`.

### S25 — MONPIFER Ministry Tenders

- production-enabled on current application release `930c94641b0699072350dcea9344aa55e930e169`;
- issuer-original `ACTIVE_PRIMARY` listing-complete tender source at `https://www.monpifer.gov.mm/my/ministry-tenders`;
- one official HTML acquisition directly yields current tender business rows; no synthetic detail stage is required;
- first production baseline created 10 `TENDER` canonical items and zero customer signals;
- baseline metrics: `items_parsed=10`, `tenders_parsed=10`, `details_attempted=0`;
- canonical identity uses the issuer-owned Drupal article alias (`monpifer:<article_alias>`); numeric Drupal node ID was audited but is intentionally not fetched per row in P0;
- issuer-visible `Last Date` text is authoritative where the hidden HTML `datetime` attribute disagrees;
- official PDFs remain metadata-only and the primary pipeline fetched zero PDFs;
- parse health uses `BUSINESS_PROCESSING`; first production sample `1/1 = GREEN`;
- no schema migration, PDF parser, OCR, Browser or YCDC identity/locator capability was introduced;
- source health GREEN;
- evidence: `docs/verification/S25-SOURCE-ONBOARDING-2026-09-04.md`.

### S26 — DOMS Medical Procurement Opportunities

- production-enabled on current application release `ae894d092f97843280c92228d6b43eda3bf0336f`;
- issuer-original `ACTIVE_SELECTIVE` medical-procurement opportunity source at `https://www.doms.gov.mm/category/tender/`;
- official WordPress category HTML exposes stable `post-<id>` identity; production intentionally stays on HTML even though DOMS REST is available because frozen v1.5 primary target kind remains `HTML`;
- first production baseline selected exactly 2 opportunity-origin `TENDER` items from the mixed tender-workflow page and created zero customer signals;
- baseline metrics: `items_parsed=2`, `tenders_parsed=2`, `details_attempted=2`, `details_succeeded=2`;
- canonical identity is stable WordPress post ID (`doms:<post_id>`); current records are `doms:12634` (`7DMS/2026-2027(L)`) and `doms:12491` (CT/MRI Preventive Maintenance);
- award/result, Envelope, opening/evaluation and scrutiny-meeting posts are fail-closed excluded from the opportunity slice;
- reliable deadline is absent from selected HTML and remains `null / unknown`, never inferred from later workflow events or attachments;
- official PDF links remain metadata-only; first baseline fetched zero PDFs and persisted exactly 3 acquisition lifecycles (category + 2 selected details);
- bounded parse-health probe preserves same-post `UPDATED` semantics without changing engine/schema;
- Bangkok + Beijing Worker doctors PASS; Beijing remains SignalForge-free and returns `126 / DENY: SignalForge is Bangkok-only` for S26 refresh;
- source health GREEN; all eleven production sources GREEN after timer restoration;
- evidence: `docs/verification/S26-SOURCE-ONBOARDING-2026-09-04.md`.

### S28 — Department of Fisheries Open Tenders

- first production-enabled on release `7413a9da60a1b0c3bf82ac0b30f00fe625ca75a2`; remains active/GREEN under current application `d1f6d1773390767e73747df75e81383e4997f053`;
- issuer-original `ACTIVE_PRIMARY` listing-complete tender source at `https://www.dof.gov.mm/index.php/my/tender`;
- one official HTML acquisition directly yields all issuer-visible tender cards; no synthetic detail stage or attachment fetch is required;
- first production baseline created 8 `TENDER` canonical items and zero customer signals;
- baseline metrics: `items_parsed=8`, `tenders_parsed=8`, `details_attempted=0`, `details_succeeded=0`;
- canonical identity uses the issuer-owned tender alias (`dof:<issuer_tender_alias>`);
- publication date comes from the card `<time datetime>` while sale date and closing date come from their respective visible texts; historical issuer inconsistencies are preserved rather than heuristically repaired;
- first baseline persisted exactly one request/attempt/evidence/processing lifecycle and zero PDF requests;
- parse health uses `BUSINESS_PROCESSING`; first production sample `1/1 = GREEN`;
- immediate S28 rollback is live-preexisting Mac-provider projection release `0a3e6156f2635fd9509738d3b6c0aa1d073f6c03`;
- Mac provider remains locked: `production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`;
- Bangkok + Beijing Worker doctors PASS; Beijing remains SignalForge-free and returns `126 / DENY: SignalForge is Bangkok-only` for S28 refresh;
- source health GREEN; all twelve production sources GREEN after timer restoration;
- evidence: `docs/verification/S28-SOURCE-ONBOARDING-2026-09-04.md`.

### S29 — DWIR Waterway and River Works Tenders

- production-enabled on exact application release `e62410eb1cc7894f6a5f3305dcf2eab0d99b2bb8`; previous application-code rollback target `6ec3e74b832b5e0033ac571d451cd41f0b69de77`;
- issuer-original `ACTIVE_PRIMARY` tender source uses the lightweight DWIR homepage Latest News surface (`https://www.dwir.gov.mm/`) for discovery and selected issuer detail HTML for business evidence;
- stable identity uses issuer-native Joomla numeric article ID (`dwir:<article_id>`), excluding slug/date from the key;
- first production baseline created 4 `TENDER` canonical items and zero customer signals; baseline metrics `items=4`, `tenders=4`, `details=4/4`;
- persisted acquisition lifecycle is exactly homepage + four HTML details (`5/5/5/5` request/attempt/evidence/processing), with no PDF/image acquisition;
- HTML scope is authoritative at event level; current deadline remains `null / UNKNOWN_NOT_IN_HTML_TEXT`; embedded base64 images are unparsed/non-blocking;
- Worker baseline correlation `signalforge-20260904T223221Z-3f413c30` PASS; Bangkok/Beijing Worker doctors PASS and Beijing refresh is denied `126 / Bangkok-only`;
- delayed post-rollout timer resume was closed on 2026-09-06: one reconciliation Worker wrapper refreshed all 13 overdue automated sources, all `SUCCESS / changed=0 / signals=0`;
- source health GREEN; 13/13 automated sources GREEN after timer restoration;
- evidence: `docs/verification/S29-DWIR-SOURCE-ONBOARDING-2026-09-05.md`.

### S30 — MOFA Procurement Invitations

- production-enabled on exact application release `61d6984bf0efd05dddcac0791bba00cf741f3052`; previous application-code rollback target `e62410eb1cc7894f6a5f3305dcf2eab0d99b2bb8`;
- issuer-original `ACTIVE_SELECTIVE` source uses `https://www.mofa.gov.mm/category/announcement/` plus selected WordPress detail HTML;
- stable canonical identity is WordPress post ID (`mofa:<post_id>`); first production baseline created `mofa:59800` and `mofa:56952`;
- first reviewed baseline was `MANUAL / SUCCESS`, `items=2`, `tenders=2`, `details=2/2`, `changed=2`, `signals=0`;
- acquisition lifecycle is exactly category + two HTML details (`3/3/3/3` request/attempt/evidence/processing), with zero PDF/JPG/PNG acquisition; attachment URLs/names remain metadata only and missing deadlines remain `null`;
- Worker correlation `signalforge-20260907T031617Z-36a3d084` is exactly one SUCCESS Worker Run; Bangkok/Beijing Worker doctors PASS, Beijing remains SignalForge-free and rejects S30 refresh with `126 / Bangkok-only`;
- timer-resume reconciliation was clean; 14/14 automated sources GREEN, backlog 0, Mac provider remains locked (`production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`);
- evidence: `docs/verification/S30-MOFA-SOURCE-ONBOARDING-2026-09-06.md`.

### S31 — MOEA Procurement Invitations

- production-enabled on exact application release `f751c8f13ae86740a227ba2cd00518d68cde2edc`; previous application-code rollback target `61d6984bf0efd05dddcac0791bba00cf741f3052`;
- issuer-original `ACTIVE_SELECTIVE` source uses the MOEA tender archive `https://portal.moea.gov.mm/index.php?page=ORwuBwpT`; one HTML card includes title/date/location/PDF metadata while the issuer CMS comment contains business narrative;
- listing-complete selective classifier includes procurement invitations while excluding tender awards/results and lease/auction records; official PDFs are never fetched;
- source-local canonical identity is `moea:<publication_date>:<event_fingerprint>` from publication date + normalized title, with same-identity/different-attachment collision fail-closed behavior;
- reviewed first baseline was `MANUAL / SUCCESS`, `items=9`, `tenders=9`, `details=0`, `changed=9`, `signals=0`; newest 2026-07-27 event has explicit HTML-comment deadline `2026-08-07`;
- baseline persistence is canonical/signals `9/0` and request/attempt/evidence/processing `1/1/1/1`; the sole EvidenceEnvelope is the 90,396-byte HTML archive page and PDF evidence is zero;
- Worker correlation `signalforge-20260907T040008Z-4db411d6` is exactly one SUCCESS Worker Run; Bangkok/Beijing Worker doctors PASS, Beijing remains SignalForge-free and rejects S31 refresh with `126 / Bangkok-only`;
- timer-resume reconciliation was clean; 15/15 automated sources GREEN, canonical/signals `141/11`, backlog 0, Mac provider remains locked (`production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`);
- evidence: `docs/verification/S31-MOEA-SOURCE-ONBOARDING-2026-09-07.md`.

### S32 — Myanma Timber Enterprise Procurement Invitations

- production-enabled on exact application release `2edaf3259d168344544f5a5cd09ab1d2c37fe563`; previous application-code rollback target `f751c8f13ae86740a227ba2cd00518d68cde2edc`;
- issuer-original `ACTIVE_SELECTIVE` source uses `https://mte.gov.mm/index.php/en/annoucements` as a one-fetch listing-complete HTML archive;
- classification requires explicit buyer-side procurement semantics and excludes MTE timber/open-tender sale or auction semantics, so `Open Tender` alone is never promoted to procurement;
- canonical identity is issuer-native Joomla article ID (`mte:<article_id>`); current selected records are `mte:1600` service procurement and historical `mte:1415` diesel procurement;
- reviewed first baseline was `MANUAL / SUCCESS`, `items=2`, `tenders=2`, `details=0`, `changed=2`, `signals=0`; publication date and deadline remain `null` because issuer HTML does not expose trustworthy values and image supplements are not parsed;
- baseline persistence added exactly one HTML acquisition lifecycle; the sole EvidenceEnvelope is the 46,158-byte announcement archive page, with zero detail/image acquisition;
- Worker correlation `signalforge-20260907T060955Z-b9a81d4d` is exactly one SUCCESS Worker Run; Bangkok/Beijing Worker doctors PASS, Beijing remains SignalForge-free and rejects S32 refresh with `126 / Bangkok-only`;
- cumulative failed_runs=4 is historical/recovered: prior S10/S28 timeouts plus two S29 DWIR transport failures (522 + timeout) that recovered with subsequent SUCCESS runs; backlog remains 0;
- timer restoration is clean; 16/16 automated sources GREEN, canonical/signals `143/11`, Mac provider remains locked (`production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`);
- evidence: `docs/verification/S32-MTE-SOURCE-ONBOARDING-2026-09-07.md`.

## Current result

> **S05A + S07 + S08A + S10 + S12 + S13 + S20 + S21 + S22 + S25 + S26 + S28 + S29 + S30 + S31 + S32 = PRODUCTION / GREEN**
>
> **S15A MPA = Manual P0 canonical source / operator-driven / no unattended scheduling**

SignalForge has now proven sixteen automated source/domain shapes under the same v1.5 acquisition lifecycle, plus the separate S15A Manual P0 canonical path:

```text
Commerce: one Drupal notice -> zero/one selected REGULATORY_NOTICE + attachment metadata
Customs Notifications: one listing HTML -> N REGULATORY_NOTICE records, no synthetic detail stage
Customs Auctions:      one mixed announcements HTML -> selected AUCTION_NOTICE records, award/result excluded
DICA:                  one WordPress category -> selective event detail -> REGULATORY_NOTICE + PDF metadata
IRD:                   one announcement list -> selective tax detail fetch -> REGULATORY_NOTICE
MPT:      one detail page -> zero/one tender
MOEP:     one category item -> one partial HTML tender + attachment metadata
Railways: one detail page -> N tender rows
IWT:      one Drupal tender node -> one tender + attachment metadata
MONPIFER: one official tender table -> N complete TENDER records + PDF metadata, no detail fetch
DOMS:     one WordPress tender category -> selected opportunity detail HTML -> TENDER + PDF metadata
DOF:      one official tender-card listing -> N complete TENDER records, no detail/attachment fetch
DWIR:     one lightweight homepage -> selected Joomla detail HTML -> TENDER, embedded image non-blocking
MOFA:     one mixed Announcement category -> selected WordPress detail HTML -> TENDER + attachment metadata
MOEA:     one tender archive HTML -> selected invitation records + CMS-comment business fields + PDF metadata
MTE:      one announcement archive HTML -> buyer-side procurement only, Joomla ID identity, image supplements unparsed
MPA:      manual LISTING + DETAIL + PDF evidence bundle -> operator-only canonical TENDER/AUCTION_NOTICE
```

All remain inside one Bangkok SignalForge application boundary and the existing Worker operational envelope.

## Important S20 epistemic boundary

MOEP currently provides strong discovery but incomplete business qualification in HTML. The latest advertised PDFs return HTTP 404 from Bangkok and must not be treated as usable evidence.

Therefore:

```text
HTML tender event = production evidence
PDF URL           = attachment metadata only
PDF content       = unavailable / not claimed
missing deadline  = unknown, not inferred
```

If MOEP attachments become reliably retrievable, a supplementary PDF gate may be evaluated independently. It must not weaken HTML source health or become a silent hard dependency.

## Next authorized direction

Continue source expansion one source at a time through:

```text
business-value audit
-> fresh network / endpoint / shape re-audit
-> Direct HTTP fixture
-> source adapter / parser
-> baseline suppression
-> health
-> exact-SHA production deploy
-> live verification
-> checkpoint closure
```

The next engineering slice should still be selected by business value and current evidence, not source-ID order or a source-count target. S01 National Portal and S04 Trade Portal remain deferred as canonical sources because aggregator metadata/duplication needs an explicit issuer-resolution/equivalence/dedup contract. S16 YCDC now has a concrete identity/transport-locator gate; S17 MCDC and S18 NPTDC require image/OCR capability for current business specifics and remain deferred rather than forcing runtime expansion. Fresh S26 candidate audit also showed Ministry of Industry failing Bangkok DNS and Ministry of Energy carrying current business detail primarily in embedded PDFs; S28 audit additionally found current Ministry of Education and Tourism tender specifics to be image-based. None justified weakening the existing contract. PDF gates are source-specific: S10 triggered an enrichment/value gate, while S15A triggered a classification + business-fields gate because listing-only semantics can misclassify disposal auctions as procurement tenders. S15A deterministic PDF runtime packaging, Manual P0 Phase A, and Phase B manual canonical commit are now production live-verified on Bangkok. MPA is usable as a low-frequency operator-driven canonical source with stable `mpa:<wordpress_post_id>` identity, explicit zero-signal baseline behavior, and no scheduled S15A activation. Fresh MPA activity remains low (2 records/30d, 3/90d, 13/180d), so a Remote Provider Invocation Contract is still not justified; unattended Mac invocation remains unapproved. Continue operating S15A manually until repeated real use proves material operator burden. S10 enrichment remains a separate future parser-use-case decision, and S08A tender-award/result content remains a separate future `PROCUREMENT_RESULT` decision.
