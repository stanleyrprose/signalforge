# GOAL — SignalForge Myanmar Source Expansion

## Goal

Expand SignalForge across high-value Myanmar issuer-original sources while preserving the proven v1.5 local acquisition contract and the existing Worker / Control / Fleet boundaries.

## Frozen production boundary

- SignalForge production remains Bangkok-only.
- Beijing is outside the current SignalForge production topology: it is not a SignalForge node, replica, standby, acquisition provider, source runtime, or per-source rollout gate. Historical Beijing zero-footprint checks remain historical evidence only and are not repeated for new source onboarding.
- Direct HTTP remains the default production acquisition method.
- One SignalForge scheduler/service invocation creates one Worker operational Run; source/business jobs and acquisition attempts remain internal SignalForge state.
- `AcquisitionRequest` and `AcquisitionAttempt` are not Worker Runs.
- Worker DB has no SignalForge source/canonical/acquisition business semantics.
- Source adapters follow real issuer shape; there is no universal tender parser requirement.
- TLS/HTTP failures stay fail-closed and do not silently become certificate bypass or Browser escalation.
- Browser execution belongs only to the Mac Browser Plane; VPS Browser/Crawlee R3 is superseded. SignalForge→Mac unattended production invocation is permitted only through the live-reviewed PIC pull-SSH contract and explicit source/URL/capability allowlists; there is no generic HTTP/TLS failure fallback. Browserless/PDF/distributed coordination remain evidence-triggered future capabilities.

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

### S33 — Ministry of Cooperatives and Rural Development Tenders

- production-enabled on exact application release `a4d55bf4ad8cf1977b5e874fa9b652d880c2b2a7`; previous application-code rollback target `2edaf3259d168344544f5a5cd09ab1d2c37fe563`;
- issuer-original `ACTIVE_SELECTIVE` source uses the structured MCRD tender board `https://www.mcrd.gov.mm/index.php?page=dGluZGEmbW8%3D` as one listing-complete Direct-HTTP HTML acquisition;
- board rows expose title, explicit closing date, department and primary document metadata; publication date is not exposed and remains `null`; linked PDF/JPEG content is never fetched in P0;
- source-local canonical identity is `mcrd:<closing_date>:<sha256(normalized_title|closing_date|department)[:16]>`; primary document is excluded from identity and acts as a fail-closed collision guard if replaced under the same event identity;
- first reviewed production baseline was `MANUAL / SUCCESS`, `items=5`, `tenders=5`, `details=0`, `changed=5`, `signals=0`; newest row has deadline `2026-05-15`;
- baseline persistence added exactly one HTML request/attempt/evidence/processing lifecycle; sole EvidenceEnvelope is 52,527 bytes, with zero linked-document acquisition;
- Worker correlation `signalforge-20260907T064353Z-74f21b24` is exactly one SUCCESS Worker Run; Bangkok/Beijing Worker doctors PASS, Beijing remains SignalForge-free and rejects S33 refresh with `126 / Bangkok-only`;
- S23 Ministry of Construction was freshly re-audited because it has current September 2026 tenders, but Bangkok strict TLS still fails because the issuer certificate is expired; it remains deferred with no TLS bypass;
- cumulative failed_runs remains 4 historical/recovered, backlog 0; timer restoration is clean and 17/17 automated sources are GREEN, canonical/signals `148/11`, Mac provider remains locked (`production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`);
- evidence: `docs/verification/S33-MCRD-SOURCE-ONBOARDING-2026-09-07.md`.

### S16 — YCDC Engineering Department (Building) Tender Opportunities

- production-enabled on exact application release `794e0190d1d878d92e9a0580a28b93b6c82dada0`; previous application-code rollback target `a4d55bf4ad8cf1977b5e874fa9b652d880c2b2a7`;
- the previously deferred YCDC identity/transport-locator blocker is resolved for this department by issuer-original stable numeric archive `https://www.ycdc.gov.mm/frontend_engineering_building_detail/1`; the randomized ciphertext tender transport is no longer required;
- `ACTIVE_SELECTIVE` classifier keeps PPP/building implementation opportunities and excludes scope-level lease/concession, auction, sale and demolition-sale semantics; exclusion is scoped to the business paragraph so `တင်ဒါပုံစံရောင်းချမည့်ရက်` does not cause a false negative;
- source-local canonical identity is `ycdc-building:<deadline>:<sha256(explicit_deadline|normalized_scope_summary)[:16]>`, with same-identity/different-full-block collision fail-closed behavior;
- reviewed first production baseline was `MANUAL / SUCCESS`, `items=5`, `tenders=5`, `details=0`, `changed=5`, `signals=0`; newest selected PPP/building event has deadline `2026-02-27`, while the newer 2026-08-10 lease/concession event is correctly excluded;
- baseline persistence added exactly one 60,673-byte HTML acquisition lifecycle and zero detail/attachment acquisition; publication dates remain `null` and deadlines come only from explicit HTML final-submission dates;
- Worker correlation `signalforge-20260907T091305Z-669065f6` is exactly one SUCCESS Worker Run; Bangkok/Beijing Worker doctors PASS, Beijing remains SignalForge-free and rejects S16 refresh with `126 / Bangkok-only`;
- cumulative failed_runs=5 is historical/recovered; the fifth event is S25 MONPIFER HTTP 522 at ~08:30Z followed by SUCCESS at ~08:40Z; backlog remains 0;
- timer restoration is clean; 18/18 automated sources GREEN, canonical/signals `153/11`, Mac provider remains locked (`production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`);
- evidence: `docs/verification/S16-YCDC-BUILDING-SOURCE-ACTIVATION-2026-09-07.md`.

### S34 — Posts and Telecommunications Department Open Tenders

- production-enabled on exact application release `0f8237916b39daa1c2f85d8309e93ff3ced56238`; previous application-code rollback target `794e0190d1d878d92e9a0580a28b93b6c82dada0`;
- issuer-original `ACTIVE_SELECTIVE` source uses the PTD tender category and selected detail HTML, excluding tender-winner/award/result stages; current business scope includes RF-monitoring recovery equipment, RF spare parts, Bago monitoring-station equipment, monitoring-vehicle equipment, Nay Pyi Taw/Pathein construction and `.mm Root DNS` / second-level DNS operations and maintenance;
- publication dates come from explicit HTML `Posted on` fields; deadlines remain `null` because deadline/rule details are in linked official PDFs that remain metadata-only and are never fetched in P0;
- canonical identity is `ptd:<publication_date>:<sha256(publication_date|normalized_scope_summary)[:16]>`; opaque encoded PTD detail locators are transport/audit metadata rather than business identity, allowing same-day generic-title tenders to remain distinct by scope;
- reviewed first production baseline was `MANUAL / SUCCESS`, `items=6`, `tenders=6`, `details=6/6`, `changed=6`, `signals=0`;
- baseline persistence added exactly seven HTML request/attempt/evidence/processing lifecycles (one category + six details), with zero PDF evidence; SignalForge DB `quick_check=ok`;
- Worker correlation `signalforge-20260907T102115Z-c639cb75` is exactly one SUCCESS Worker Run; Bangkok/Beijing Worker doctors PASS, Beijing remains SignalForge-free and rejects S34 refresh with `126 / Bangkok-only`;
- cumulative failed_runs remains 5 historical/recovered, backlog 0; timer restoration is clean and 19/19 automated sources are GREEN, canonical/signals `159/11`, Mac provider remains locked (`production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`);
- OAG remains deferred because current tender business fields are scan/JPG-only and would require a separately approved Burmese image/OCR capability;
- evidence: `docs/verification/S34-PTD-SOURCE-ONBOARDING-2026-09-07.md`.

### S35 — Department of Advanced Science and Technology Tenders

- production-enabled on exact application release `5ad60eabc2a86235db413c37c49e4bbe91378f95`; previous application-code rollback target `0f8237916b39daa1c2f85d8309e93ff3ced56238`;
- issuer-original DAST tender archive `https://www.dast.gov.mm/category/tender/` is Direct-HTTP GREEN and currently exposes six 2026 WordPress tender posts; stale issuer links to `dast.edu.mm/?p=<id>` are deterministically normalized by the native post ID to the same issuer's working `www.dast.gov.mm/?p=<id>` mirror;
- canonical identity is issuer-native `dast:<wordpress_post_id>`; detail HTML supplies publication date, full business scope and explicit submission deadline, while official PDF paths remain metadata-only;
- current scope includes Polytechnic University QA/QC, six construction works, Reference Book procurement, 209 construction works, general QA/QC and teaching/equipment/office/furniture procurement; parsed deadlines are `2026-08-14`, `2026-07-21`, `2026-05-22` and `2026-05-07`;
- reviewed production baseline was `MANUAL / SUCCESS`, `items=6`, `tenders=6`, `details=6/6`, `changed=6`, `signals=0`; all six were historical/expired at baseline time;
- baseline added exactly seven HTML acquisition lifecycles (one 114,471-byte archive + six detail pages) and zero PDF evidence; SignalForge and Worker DB `quick_check=ok`;
- Worker correlation `signalforge-20260907T122630Z-ce3da99b` is exactly one SUCCESS Worker Run; Bangkok/Beijing Worker doctors PASS, Beijing remains SignalForge-free and rejects S35 refresh with `126 / Bangkok-only`;
- cumulative failed_runs remains 5 historical/recovered, backlog 0; timer restoration is clean and 20/20 automated sources are GREEN, canonical/signals `165/11`, Mac provider remains locked (`production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`);
- fresh candidate controls: YESC was not duplicated because current YESC opportunities are already represented through S20 MOEP; LBVD returned HTTP 403 repeatedly from Bangkok and remains outside production;
- evidence: `docs/verification/S35-DAST-SOURCE-ONBOARDING-2026-09-07.md`.

### S36 — Department of Agriculture Procurement Announcements

- production-enabled on exact application release `1561d6f5e53026b8f651e1aa40d9e52a3f6ee541`; previous application-code rollback target `5ad60eabc2a86235db413c37c49e4bbe91378f95`;
- issuer-original mixed announcement board `https://www.doa.gov.mm/doa/index.php?route=cms/category&path=22` is Bangkok strict-HTTPS GREEN and is handled as a listing-complete business source: the title itself carries procurement/construction scope, while scan/image detail remains unfetched supplementary evidence;
- classifier requires tender semantics plus buyer/implementation language and excludes award/result, sale, auction and lease semantics; current canonical set includes multipurpose hall construction, Desktop Computer i5 x45, construction works, Cylinder + HPLC (PDA-Detector), ISO Lab major renovation, plus one older paper-procurement article still present on the issuer board;
- canonical identity is issuer-native `doa:<article_id>`; publication date comes from the visible listing date; deadline remains `null` with `UNKNOWN_IN_IMAGE_SUPPLEMENT_NOT_PARSED`;
- reviewed production baseline was `MANUAL / SUCCESS`, `items=6`, `tenders=6`, `details=0`, `changed=6`, `signals=0`; it added exactly one 78,597-byte HTML request/attempt/evidence/processing lifecycle and zero non-HTML evidence;
- Worker correlation `signalforge-20260907T134030Z-0b687ac4` is exactly one SUCCESS Worker Run; SignalForge/Worker DB quick checks and Bangkok/Beijing Worker doctors PASS, Beijing remains SignalForge-free and rejects S36 refresh with `126 / Bangkok-only`;
- cumulative failed_runs remains 5 historical/recovered, backlog 0; timer resume immediately reconciled already-due existing sources and completed cleanly; final state is 21/21 automated sources GREEN, canonical/signals `171/11`, Mac provider remains locked (`production_enabled=false`, `remote_invocation=false`, `browser_production_approved=false`);
- fresh audit control: DMH transport is GREEN but current business specifics remain PDF/image-dependent; OAG remains image/scan dependent. Neither justified opening a PDF/OCR capability gate;
- evidence: `docs/verification/S36-DOA-SOURCE-ONBOARDING-2026-09-07.md`.

### S37 — Ministry of Information Ministerial Office Procurement Announcements

- production-enabled on exact application release `d12d70d39794af32e67725700f344f8b50248bb0`; previous application-code rollback target `1561d6f5e53026b8f651e1aa40d9e52a3f6ee541`;
- official MOI mixed department-announcement board is Bangkok Direct-HTTP GREEN; the adapter selects only titles that explicitly prove `Ministry of Information + Ministerial Office + opportunity-stage tender`, excluding award/result stages and other-agency reposts so no new cross-issuer dedup contract is needed;
- canonical identity is issuer-native Drupal `moi:<node_id>`; current node `moi:81536` contains HTML-complete business evidence for four types of office equipment plus one type of furniture, publication `2026-04-09`, tender-form sale window `2026-04-20..2026-05-11`, and explicit deadline `2026-05-15`;
- reviewed production baseline was `MANUAL / SUCCESS`, `items=1`, `tenders=1`, `details=1/1`, `changed=1`, `signals=0`; it added exactly two HTML request/attempt/evidence/processing lifecycles (listing + detail), zero non-HTML evidence;
- Worker correlation `signalforge-20260907T145146Z-b9ee4d52` is exactly one SUCCESS Worker Run; SignalForge/Worker DB checks and Bangkok/Beijing Worker doctors PASS, Beijing remains SignalForge-free and rejects S37 refresh with `126 / Bangkok-only`;
- cumulative failed_runs remains 5 historical/recovered, backlog 0; timer resume created no extra scheduler run; final state is 22/22 automated sources GREEN, canonical/signals `172/11`; Mac production flags remain locked;
- source-audit capability note: CodexPro can invoke the Mac Browser Plane for controlled C0/C1/C2/C3-use website acquisition/inspection. This turn used Mac C0 to verify the current Ministry of Industry portal and high-value tender board. Industry is Mac-GREEN but Bangkok CONNECT_TIMEOUT, so it remains a provider/manual-P0 candidate rather than unattended production;
- evidence: `docs/verification/S37-MOI-SOURCE-ONBOARDING-2026-09-07.md`.

## Current result

> **S05A + S07 + S08A + S10 + S12 + S13 + S16 + S20 + S21 + S22 + S25 + S26 + S28 + S29 + S30 + S31 + S32 + S33 + S34 + S35 + S36 + S37 = PRODUCTION / GREEN**
>
> **S15A MPA = Manual P0 canonical source / operator-driven / no unattended scheduling**

SignalForge has now proven twenty-two automated source/domain shapes under the same v1.5 acquisition lifecycle, plus the separate S15A Manual P0 canonical path:

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
MCRD:     one structured tender board -> N TENDER rows + explicit closing date + primary-document metadata
YCDC Building: one stable numeric department archive -> selected PPP/building implementation TENDER rows, lease/sale/auction excluded
PTD:      one tender category -> selected telecom/ICT detail HTML -> TENDER + PDF metadata, award/result excluded
DAST:     one WordPress tender archive -> official .gov.mm detail HTML -> TENDER + explicit HTML deadline + PDF metadata
DOA:      one mixed announcement listing -> buyer/works TENDER events from article title + issuer article-ID identity, image supplements unparsed
MOI:      one mixed department-announcement board -> issuer-specific Ministerial Office detail HTML -> TENDER + explicit sale window/deadline
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
-> fresh network / endpoint / shape re-audit (Bangkok Direct HTTP first; CodexPro -> Mac Browser Plane allowed for controlled audit/acquisition when useful)
-> Direct HTTP fixture
-> source adapter / parser
-> baseline suppression
-> health
-> exact-SHA production deploy
-> live verification
-> checkpoint closure
```

The next engineering slice should still be selected by business value and current evidence, not source-ID order or a source-count target. S01 National Portal and S04 Trade Portal remain deferred as canonical sources because aggregator metadata/duplication needs an explicit issuer-resolution/equivalence/dedup contract. S16 YCDC Building has now closed its old identity/transport-locator gate through the stable numeric department archive; the generic randomized ciphertext YCDC tender transport remains unused. S17 MCDC and S18 NPTDC still require image/OCR capability for current business specifics and remain deferred rather than forcing runtime expansion. S34 PTD proves high-value telecom/ICT procurement can remain HTML-event-level even when deadlines live in PDF; S35 DAST proves a stale issuer-local host can be removed from the runtime path when the same native WordPress IDs are served by the issuer's working official `.gov.mm` mirror, while preserving HTML scope/deadline evidence. S36 DOA proves that an issuer listing title can itself be the complete event/scope envelope when stable article identity and visible publication date are available, allowing scan/image detail to remain a non-blocking supplement. DMH and OAG remain deferred because their current business-specific value is materially PDF/image dependent; LBVD is currently Bangkok HTTP 403, and YESC is not duplicated outside S20 MOEP. Fresh S37 re-audit supersedes the old Ministry of Industry DNS note: the ministry now serves `industrymsme.gov.mm`; Mac Browser Plane C0 is GREEN and exposes many high-value current tenders, while Bangkok resolves the host but times out establishing the HTTPS connection, so Industry remains a high-priority provider/manual-P0 candidate rather than unattended production. Ministry of Energy still carries current business detail primarily in embedded PDFs; S28 audit additionally found current Ministry of Education and Tourism tender specifics to be image-based. None justified weakening the existing contract. PDF gates are source-specific: S10 triggered an enrichment/value gate, while S15A triggered a classification + business-fields gate because listing-only semantics can misclassify disposal auctions as procurement tenders. S15A deterministic PDF runtime packaging, Manual P0 Phase A, and Phase B manual canonical commit are now production live-verified on Bangkok. MPA is usable as a low-frequency operator-driven canonical source with stable `mpa:<wordpress_post_id>` identity, explicit zero-signal baseline behavior, and no scheduled S15A activation. Fresh MPA activity remains low (2 records/30d, 3/90d, 13/180d), so a Remote Provider Invocation Contract is still not justified; unattended Mac invocation remains unapproved. Continue operating S15A manually until repeated real use proves material operator burden. S10 enrichment remains a separate future parser-use-case decision, and S08A tender-award/result content remains a separate future `PROCUREMENT_RESULT` decision.


## PIC v1 R3 closure and R4/R5 production-enable slice — 2026-09-08

R3 is complete and live-verified. Gate `26ece5bb-fe15-47ae-a6b0-a7b4882d778f` proved Bangkok-origin C0/C1/C2/C3 through the dedicated restricted pull-SSH identity, local Mac MCP stdio runtime, durable result import, zero S38 business side effects, and live credential disable/restore. R3 closure is merged at `406a3e32f8f5d3a7269e2c6c3aac0e3975e6fd76`.

The next authorized slice is now R4 Provider Production Enable + R5 first provider-backed source. The implementation candidate deliberately changes the old cross-host flags to `browser_production_approved=true`, `mac-mm-01 production_enabled=true`, `invocation_mode=pull_ssh_v1`, and `remote_invocation=true`. This does **not** create an inbound Mac listener or an automatic Direct HTTP failure fallback.

R5 source `S38` is Ministry of Industry `https://www.industrymsme.gov.mm/announcements`. It is explicitly routed as `engine=provider`, `provider_id=mac-mm-01`, `provider_capability=C0_FETCH`, with production PIC authorization limited to the exact listing URL plus `/announcements/<id>` detail paths. C1/C2/C3 remain globally verified capabilities but are not authorized for S38 production. Healthy Direct HTTP sources remain first in `run_due`; S38 runs last so Mac/provider failure cannot prevent due Direct HTTP sources from executing.

Fresh Mac acquisition on 2026-09-08 found 16 current tender listings. Detail `1036` is HTML-complete with publication `2026-09-03`, Chemical Reagent + Sample Gas scope, and explicit deadline `2026-09-24 16:00`. No PDF/OCR/JS-render capability is required for the first production source.

Implementation status in the feature branch: SignalForge full suite `197 passed`; Mac Provider Agent launchd/production projection implementation is under test. Production runtime deployment, first zero-signal S38 baseline, Mac-offline isolation, timer resume, and final checkpoint remain required before R4/R5 can be called live-complete.

## PIC v1 R4/R5 production closure — 2026-09-08

R4 Provider Production Enable and R5 first Provider-backed source are **COMPLETE / PASS**. S38 Ministry of Industry is now unattended production through `Bangkok durable queue -> Mac restricted pull SSH -> local MCP stdio -> C0 -> Bangkok evidence -> parser/canonical/signal`. Production authorization remains source/URL/capability bounded; S38 is C0-only and there is no generic Direct HTTP failure fallback.

Final releases: Mac Browser Plane runtime source `7a13bcb1ab8acf0a69585bbddc0a6d88cd56d9ea`; Bangkok SignalForge `1d88b54d22f43e818a055a5c605a14c728816aad`. The production timer is enabled/active. The unattended S38 recovery run at `2026-09-08T14:20:54.213550Z` was `POLL / SUCCESS / changed=0 / signals=0 / backlog=0`, with `consecutive_failures=0` afterwards. Final S38 health is GREEN with business-processing parse sample 10/10, 8 canonical tender records, zero S38 customer signals, zero pending backlog, and DB quick check `ok`.

Live rollout found and closed four production semantics bugs rather than masking them: ProviderRequest TTL reused scheduler time (#85), Provider Agent slept between backlog jobs (#31 in mac-browser-plane), one source exception aborted later due sources (#86), and S38 used the wrong parse-health sample surface (#87). See `docs/verification/PIC-R4-R5-PRODUCTION-CLOSURE-2026-09-08.md` for evidence, offline isolation, rollback boundaries, and exact counters.

Overall SignalForge remains `DEGRADED / RED` only because S25 still has historical MONPIFER parse failures in its rolling 10-sample window (currently 6/10) despite current fetch/freshness success, zero consecutive failures, and no current error. Do not brush this green with artificial refreshes; allow the window to recover naturally.

## S27 MOBA Provider C0 production closure — 2026-09-08

S27 Ministry of Border Affairs is now the second explicit provider-backed production source and is **PRODUCTION / GREEN** on exact implementation release `29cdf90554c61bfcdc8bfb6cf4fba16c597652c9`.

Fresh Bangkok strict HTTPS remained RED on both listing and detail with 6/6 curl-60 issuer-chain failures, while fresh Mac Browser Plane C0 returned HTTP 200 for the 84,281-byte listing and 56,479-byte detail 3475. The prior S27 re-audit gate is now satisfied because PIC R4/R5 already exists independently in production; no provider was created solely for MOBA.

Production authorization is limited to C0, the exact listing `https://moba.gov.mm/my/tender`, and same-host `/my/tender/<id>` detail paths. Query/fragment, C1/C2/C3, PDF primary fetch, TLS bypass and automatic Direct-HTTP failure fallback remain disallowed. Canonical identity is issuer-native Drupal tender node ID (`moba:<id>`); opportunity rows are selected while award/result rows are excluded.

First production baseline: `SUCCESS / discovered=7 / candidates=6 / details=6/6 / changed=6 / signals=0 / backlog=0`. Durable state is six S27 canonical items, zero S27 signals, seven provider requests all SUCCEEDED, seven EvidenceEnvelopes, seven successful processing records, and DB quick check `ok`. S27 health is GREEN with parse 6/6.

Beijing remains SignalForge-free and its current forced dispatcher rejects `signalforge-refresh S27` with `126 / DENY: SignalForge is Bangkok-only`. Bangkok timer is restored enabled/active and the immediate scheduler run completed SUCCESS.

The rollout also exposed a deploy packaging mode bug: `cp -a SOURCE/. STAGE/` can copy a restrictive `mktemp -d` root mode onto the staged release. Rollback worked and production never switched to the untraversable candidate. The deploy script is hardened to normalize `$STAGE` to 0755 after the copy. Full details: `docs/verification/S27-MOBA-PROVIDER-SOURCE-ONBOARDING-2026-09-08.md`.

## S39 Ministry of Energy Direct HTTP + required PDF production closure — 2026-09-08

S39 Ministry of Energy is **PRODUCTION / GREEN / COMPLETE** on exact implementation release `b8de9b0e2916b8e21f6bf6f7a1df66ce6e5f204b`. It is a Bangkok Direct HTTP source and does not use the Mac Browser Provider.

The reviewed source shape is one HTML listing, numeric `/tenders/<id>` detail HTML, and exactly one required same-origin text-native official PDF per detail. The engine owns both HTML and PDF acquisition/evidence; the parser performs no network I/O. Supplementary PDF acquisition is fail-closed, Direct-HTTP-only, bounded to one required same-origin PDF, and is not authorized for Provider sources.

First production baseline Worker `signalforge-20260908T154731Z-b8e83d7f`, app `e9ca4a06-d058-44fb-a5b4-c1d5e84fa54f`: `SUCCESS / discovered=4 / details=4/4 / changed=4 / signals=0 / backlog=0`. Durable S39 state is canonical 4, signals 0, acquisition targets `DISCOVERY=1 / HTML=4 / PDF=4`, evidence 9, business processing 4/4 SUCCESS, canonical evidence hashes all matched PDF EvidenceEnvelope hashes, and DB quick check `ok`.

S39 health is GREEN (`fetch=GREEN / freshness=GREEN / parse=4/4 / recovery backlog=0`). The timer is restored enabled/active; timer-triggered Worker `signalforge-20260908T155715Z-fce090b1` completed the full `run-due` invocation SUCCESS, with S39 correctly `NOT_DUE` until its natural `2026-09-08T16:17:31.274994Z` schedule. No DB mutation was used to force an unattended sample early.

Final SignalForge status is now **PASS / GREEN** with canonical items `193`, signals `34`, recovery backlog `0`; S25 also recovered naturally to GREEN at `9/10 = 0.9` without artificial refreshes. Live verification: `docs/verification/S39-MINISTRY-OF-ENERGY-SOURCE-ONBOARDING-2026-09-08.md`.

## S40 Ministry of Labour production watcher closure — 2026-09-08

S40 Ministry of Labour is **PRODUCTION WATCHER / GREEN / COMPLETE** on exact application release `9980584b7deec660d16e5f202ff0056117df88f6`. It is Bangkok Direct HTTP only and does not change Mac Browser Provider policy.

The deliberately narrow production discovery surface is issuer page 1 `https://www.mol.gov.mm/tender/`. Current page 1 contains ten workflow/result-stage posts, all correctly excluded; therefore the first live baseline is intentionally `SUCCESS / discovered=0 / canonical=0 / signals=0 / backlog=0`. The official Content Views `?_page=2` surface is used only as regression evidence and is not a production backfill path, avoiding a generic multi-page discovery subsystem for one source.

Historical issuer-original invitation fixtures prove the already-live S39 required same-origin text-PDF path works for future MOL opportunities: Smart ID Card Printing (`mol:43883`) parses deadline `2026-07-14 16:30`, and medical equipment (`mol:43840`) parses Electric High Speed Drill + Fibroscan with deadline `2026-07-13 16:30`. Award/result/technical-qualified stages are fail-closed excluded. The Myanmar evening `4:30` marker is explicitly regression-tested so it cannot be misread as `04:30`.

Production baseline Worker `signalforge-20260908T163346Z-05f65b51`, app `b2b3f5ff-4802-441c-9b28-c1efe819d65b` persisted exactly one DISCOVERY acquisition/evidence/processing lifecycle, zero detail/PDF acquisitions, zero canonical, zero signals and DB quick check `ok`. Source health is GREEN; parse is honestly `UNKNOWN / PARSE_SAMPLE_INSUFFICIENT` until a real page-1 opportunity provides the first production detail sample.

Bangkok timer is restored enabled/active. Timer Worker `signalforge-20260908T163503Z-f6e89982` completed `run-due` SUCCESS on the new release, with S40 correctly `NOT_DUE` until its natural `2026-09-08T17:03:46.458201Z` schedule. Overall SignalForge remains `PASS / GREEN`, canonical `193`, signals `34`, recovery backlog `0`. Live verification: `docs/verification/S40-MINISTRY-OF-LABOUR-SOURCE-ONBOARDING-2026-09-08.md`.

## Signal quality / business completeness closure — S25 + S30 — 2026-09-09

The next optimization priority is no longer raw source count. A fresh source-gap audit found no S41 candidate with higher value than fixing two production quality issues in already-live sources.

S25 MONPIFER had emitted 20 noisy `UPDATED` signals on 2026-09-08 because the issuer alternated equivalent PDF paths with and without `/index.php`. PR #96 canonicalizes official S25 attachment URLs at the source parser boundary; regression proves the URL-only change is `changed=0 / signals=0` while a real deadline change still emits one update. Exact release `a7e979743cfe092c7af20ed6a460fb5c74c4b75a` was live-verified against the current 10-tender page with zero new signals. Historical noisy signals were preserved.

S30 MOFA then exposed a business-completeness gap: current canonical `mofa:59800` was a 2026-09-04 open tender with no deadline because material facts lived in the official `Tender-Announcement.pdf`. PR #97 adds optional, same-origin, max-one text-PDF enrichment for S30 while preserving HTML metadata fallback and leaving required-PDF S39/S40 fail-closed. Exact production release `38ba382bd132769dd89e784331f06c3ae7e3392a` naturally enriched the canonical via scheduler processing at `2026-09-08T17:50:03.314007Z` to deadline `2026-09-18 16:30`, with Data Server / PowerEdge R750-XS / Windows Server 2025 / SQL Server 2022 scope, and emitted exactly one `UPDATED` customer signal. Four later/total PDF acquisitions share the same evidence SHA and did not duplicate the signal.

Current production is `PASS / GREEN`: active application `38ba382bd132769dd89e784331f06c3ae7e3392a`, canonical `193`, signals `35`, recovery backlog `0`, all sources GREEN, DB quick check `ok`, Bangkok timer enabled/active. Continue auditing existing sources for semantic signal noise and missing business fields before adding sources solely to increase source count. Evidence: `docs/verification/SIGNAL-QUALITY-S25-S30-PRODUCTION-CLOSURE-2026-09-09.md`.

## Actionable baseline reconciliation production closure — 2026-09-09

Business-value audit found seven high-confidence tenders that were still open but had never produced a customer signal because they first entered canonical state during a signal-suppressed source baseline. PR #99 introduces an opt-in reconciliation rule that preserves zero-signal first baselines while preventing such actionable records from remaining permanently silent.

Initial authorization is limited to S38 Industry and S39 Energy. Eligibility requires `TENDER + OPPORTUNITY`, explicit parseable deadline and deadline time, no prior signal, and at least 12 hours remaining. Reconciliation is bounded to three signals per source run, nearest deadline first, and inserts atomically with `signal_reason=ACTIONABLE_BASELINE_RECONCILIATION`. Full suite remains `217 passed`; PR #99 merged as exact production SHA `6f10d0f5a7cf37ca11d8461c03a54b3ff9f648c7`.

Live rollout recovered exactly seven open opportunities: S39 `energy:235` (`2026-09-18 13:00`) and six S38 Industry tenders with deadlines `2026-09-11`, `09-14`, `09-22`, `09-24`, `09-25`, and `10-02` at `16:00`. S39 emitted 1 signal; S38 emitted two bounded batches of 3. Third S38 and second S39 runs emitted 0; expired S38 `industry:1025` and `industry:1033` remained unsignaled; future-deadline unsignaled S38/S39 count is now 0.

Current production is `PASS / GREEN`: application `6f10d0f5a7cf37ca11d8461c03a54b3ff9f648c7`, canonical `193`, signals `42`, recovery backlog `0`, all sources GREEN, DB quick check `ok`, Bangkok timer enabled/active. Two closely spaced normal `run-due` invocations after timer restoration both completed SUCCESS with S38/S39 NOT_DUE and no duplicate signals. Evidence: `docs/verification/ACTIONABLE-BASELINE-RECONCILIATION-PRODUCTION-CLOSURE-2026-09-09.md`.

## Current opportunities read view production closure — 2026-09-09

PR #101 adds the smallest customer-consumable read surface, `signalforge opportunities`. It is read-only and signal-backed: one current row per signaled `TENDER / OPPORTUNITY` canonical, current canonical business fields, OPEN + UNKNOWN deadlines by default, expired rows hidden unless explicitly requested, plus source/limit filters and signal provenance. It is deliberately absent from the Worker verb manifest and introduces no DB schema/write, scheduler, acquisition, signal-generation, Browser or Provider change.

Targeted tests pass `7/7`; full suite is now `220/220`. PR #101 merged and exact application release `9f6ee1e39737c9226574d2a7bb9f3dc92fbf2691` was deployed to Bangkok. Production live read returned exactly `9` current signal-backed opportunities: `8 OPEN + 1 UNKNOWN`, deduped by canonical; historic S25 repeated signals therefore do not duplicate the current view. The read changed no business counters (`193 canonical / 42 signals`, DB quick check `ok`).

Bangkok timer was restored enabled/active. A subsequent normal `run-due` completed SUCCESS on the new release with due source health probes succeeding and `signals_created=0`; final SignalForge remains `PASS / GREEN`, all sources GREEN, recovery backlog `0`. A second opportunity read remained `8 OPEN + 1 UNKNOWN`. Evidence: `docs/verification/CURRENT-OPPORTUNITIES-VIEW-PRODUCTION-CLOSURE-2026-09-09.md`.

## Closed opportunities control read production closure — 2026-09-09

PR #103 extends the existing SignalForge manifest v1 with one closed, no-argument read verb: `signalforge-opportunities -> opportunities`. Exact production application release is `77334ea49acc494c845a4dd38413c65ac2240f6d`; full suite remains `220 passed`. The verb itself does not change the local opportunity reader, DB schema/writes, scheduler, acquisition, signal generation, Browser or Provider policy.

vps-control-plane PR #14 (`007398a26b7d42a4b0edde4627f0c08b46c33998`) adds the matching Bangkok-only forced-dispatcher operation. Rollout was fail-closed: after the SignalForge manifest deployed but before dispatcher deployment, the new operation still returned `126 / DENY`; after deployment, an extra-argument probe still returned `126`. The valid closed invocation returned `PASS / 9 opportunities / 8 OPEN + 1 UNKNOWN`. Beijing was not deployed and a read-only probe remained `126 / DENY`.

GitHub Actions `VPS Control` run `34318367015` then proved the complete supported automation path from GitHub-hosted runner through the dedicated restricted Actions SSH key and forced dispatcher to the live SignalForge manifest and dedicated `signalforge` user. The run completed SUCCESS and returned the same 9-row current opportunity view. At 2026-09-09 12:45 Myanmar time, a natural scheduler invocation also completed SUCCESS; production remained `PASS / GREEN`, `193 canonical / 42 signals / backlog 0`, DB quick check `ok`, timer enabled/active. Evidence: `docs/verification/OPPORTUNITIES-CONTROL-READ-PRODUCTION-CLOSURE-2026-09-09.md`.

## Opportunity Qualification v1 production closure — 2026-09-09

PR #106 adds a deterministic, read-only qualification layer to `signalforge opportunities` without changing canonical/signal generation, acquisition, scheduler, DB schema, Browser or Provider policy. Policy v1 exposes trust grade, actionability, urgency, evidence level, completeness, relevance categories, priority band, qualification reasons and source engine. The rules are deliberately explainable and non-ML.

Production exact release `08153c47b1efc67c85776f551da2e1130b2d1c63` was deployed with rollback target `5e599801be58a58ce983e61d2b1564c6ef6a83a9`; deployment archive SHA256 was `927ddc89a778c88e20261abd83ec015a404bc33c0812409d359edec2378dc9d5`. Full suite is `224 passed`.

Live production remains `PASS / GREEN`, DB quick check `ok`, timer enabled/active, canonical `194`, signals `44`, backlog `0`. The nine current signal-backed opportunities classify as `A=8 / B=1 / C=0` and `HIGH=3 / MEDIUM=5 / REVIEW=1 / LOW=0`. HIGH currently contains urgent `industry:1022`, ICT `energy:235`, and ICT `mofa:59800`; `doms:12735` remains `B / REVIEW / MEDICAL / deadline UNKNOWN` rather than inferring a missing deadline. Existing closed dispatcher `signalforge-opportunities` returned the same qualified view with no Control Plane change. Evidence: `docs/verification/OPPORTUNITY-QUALIFICATION-V1-PRODUCTION-CLOSURE-2026-09-09.md`.

## Business Briefing v1 production closure — 2026-09-09

PR #108 adds the smallest delivery-oriented read contract, `signalforge briefing`. It derives only from the qualified current-opportunity view, expands `HIGH + REVIEW`, summarizes `MEDIUM` as a compact watchlist, and emits deterministic `ACT_NOW / PRIORITIZE / REVIEW` attention actions plus `why_now` reason codes. No LLM, DB write, acquisition, scheduler, signal-generation, Browser or Provider change was introduced.

Exact SignalForge production application is `a61f9f7e7ef0af9be22bafd778f17bfe5f3a5ebc`, rollback target `08153c47b1efc67c85776f551da2e1130b2d1c63`, deployment archive SHA256 `b056278fc0aad8f3a70c80789031ba33a08c2b42edbd95e0d15cf72220023d38`. Full suite is `227 passed`. Live production briefing returns four attention items from nine current opportunities: `ACT_NOW=1 / PRIORITIZE=2 / REVIEW=1`; the remaining five MEDIUM Industry opportunities stay in watchlist only.

vps-control-plane PR #16 (`061d260c3dddddac64d82107929e96cb7c85fe98`) adds the matching no-argument Bangkok-only `signalforge-briefing` read verb. Rollout remained fail-closed: old dispatcher returned `126 / DENY`, extra argument still returns `126`, valid Bangkok call returns PASS, and Beijing remains `126 / DENY`. Final production remains `PASS / GREEN`, `194 canonical / 44 signals / backlog 0`, DB quick check `ok`, timer enabled/active. Evidence: `docs/verification/BUSINESS-BRIEFING-V1-PRODUCTION-CLOSURE-2026-09-09.md`.

## Telegram Delivery v1 credential gate — 2026-09-09

PR #110 adds Telegram attention delivery on top of Business Briefing v1. Delivery is receipt-deduplicated by `channel + canonical + latest signal + attention action`, so the same event/action does not repeat every timer cycle, a new signal can notify again, and an unchanged signal can notify again only when attention escalates such as `PRIORITIZE -> ACT_NOW`. Schema v6 adds generic successful `delivery_receipts`; Telegram transport is `AT_LEAST_ONCE_WITH_SUCCESS_RECEIPT_DEDUP` because Telegram has no exactly-once idempotency key.

Exact production release is `489d05f5b36189dc8292b51032edf49e0e102b4d`, rollback `a61f9f7e7ef0af9be22bafd778f17bfe5f3a5ebc`, archive SHA256 `ccc50cab9cee209512a8cccd7eb1c91ee24a7209893ae9833170bb350d22fceb`. Full suite is `234 passed`; BKK systemd unit verification and strict-TLS Telegram API reachability PASS. Production schema migrated through v6 with `194 canonical / 44 signals / 0 delivery receipts`, DB quick check `ok`, main timer enabled/active and overall `PASS / GREEN`.

The Telegram service/timer are installed but intentionally `disabled / inactive`; `/etc/signalforge/telegram.env` is absent and no message has been sent. Live production dry-run returns exactly four pending events: `industry:1022 ACT_NOW`, `energy:235 PRIORITIZE`, `mofa:59800 PRIORITIZE`, and `doms:12735 REVIEW`; MEDIUM watchlist items are excluded. Final activation is gated on operator-local Bangkok configuration of bot token + chat ID. Evidence: `docs/verification/TELEGRAM-DELIVERY-V1-CREDENTIAL-GATE-2026-09-09.md`.

## Telegram Delivery v1 production closure — 2026-09-09

Telegram Delivery v1 is now production-complete on Bangkok. Exact application remains `489d05f5b36189dc8292b51032edf49e0e102b4d`, rollback `a61f9f7e7ef0af9be22bafd778f17bfe5f3a5ebc`. The operator-local Telegram secret contract is active without exposing credentials in Git.

First real delivery sent exactly four Business Briefing attention events (`industry:1022 ACT_NOW`, `energy:235 PRIORITIZE`, `mofa:59800 PRIORITIZE`, `doms:12735 REVIEW`) and created four successful receipts. An immediate second execution returned `pending_count=0 / sent_count=0`, proving successful-receipt dedup for unchanged signal/action state. Telegram delivery timer is now enabled/active while the main acquisition timer remains enabled/active. Final production remains `PASS / GREEN`, DB quick check `ok`, `194 canonical / 44 signals / backlog 0 / 4 Telegram receipts`. Evidence: `docs/verification/TELEGRAM-DELIVERY-V1-PRODUCTION-CLOSURE-2026-09-09.md`.

## Telegram Message UX v1.1 production closure — 2026-09-09

PR #113 (`ff9df1af9ebf7e144b33b94aec7f6d32782a1992`) makes Telegram attention notifications compact business cards with deterministic Chinese static labels, bounded 240-character scope, clearer evidence provenance and Signal type. No LLM/translation API or delivery-policy change was introduced. Deployment archive SHA256 is `7dddcc93ae218a43d2b8addfff88d0191a5da9c020ee220dfc0842d7dd1f09e6`; full suite `235 passed`. Post-deploy delivery returned `pending_count=0 / sent_count=0` and receipts remained 4, proving renderer changes do not resend delivered events. Production remains `PASS / GREEN`, `194 canonical / 44 signals / backlog 0`, DB `ok`, both acquisition and Telegram timers enabled/active. Evidence: `docs/verification/TELEGRAM-MESSAGE-UX-V1.1-PRODUCTION-CLOSURE-2026-09-09.md`.

## S13 MPT Semantic v2 production closure — 2026-09-09

PR #115 upgrades MPT to `mpt-v4 / mpt-normalize-v2` while keeping Direct HTTP acquisition and canonical identity unchanged. Exact production release is `21c162e0333c328e06f9a83ad7bee7b1bdf2abdf`, rollback `ff9df1af9ebf7e144b33b94aec7f6d32782a1992`, archive SHA256 `2698747d39ea4275b192c103d67caa4319a6e188cb30238e613c9aef6496f948`. Full suite is `239 passed`.

Semantic v2 adds business stage, scope summary, completeness, deadline evidence/candidates and evidence-backed pre-qualification semantics; abbreviated month deadlines are supported. Deadline selection is fail-closed against publication date, so the BTS Battery FY26 page with official pre-publication date conflicts becomes `TENDER_NOTICE / deadline UNKNOWN` rather than an invented opportunity deadline. Read-only audit of all 16 stored MPT official pages produced `15 OPPORTUNITY / 1 TENDER_NOTICE`, minimum scope length 41. A synthetic future telecom tender proves normal `current_opportunities -> A/HIGH/TELECOM` behavior.

No historical migration/backfill or forced S13 refresh was performed. S13 remained exactly `16 canonical / 10 signals`, global production remained `194 canonical / 44 signals / backlog 0 / 4 Telegram receipts`, DB `ok`, health `PASS / GREEN`, both timers enabled/active, and Telegram post-deploy returned `pending=0 / sent=0`. Current S13 opportunity view intentionally remains empty until a genuine new/changed MPT page is naturally processed. Evidence: `docs/verification/S13-MPT-SEMANTIC-V2-PRODUCTION-CLOSURE-2026-09-09.md`.

## Parser-only signal suppression + DOMS audit production closure — 2026-09-10

A post-rollout business-value audit found that the next natural S13 health probe did not receive a genuinely changed MPT tender, but still emitted one historical `UPDATED` signal for expired `mpt:CCO-2026-001` (`deadline=2026-08-06`). The canonical had been reinterpreted by Semantic v2 from byte-identical official HTML. This exposed a distinction that the previous deployment-only gate did not cover: canonical semantic evolution is not automatically issuer-side change.

PR #117 fixes that failure mode with the smallest evidence-aware rule. For detail pipelines with no fetched attachment bundle, byte-identical raw detail SHA may update canonical semantics but suppresses the customer-facing signal. Real HTML byte changes still emit `UPDATED`. Attachment-backed HTML+PDF pipelines are deliberately excluded because full-suite testing proved that one digest cannot represent the entire evidence bundle: an initial generic implementation broke the existing S30 MOFA HTML-change/same-PDF regression, so the change was narrowed rather than introducing a new evidence-bundle schema. Final full suite is `240 passed`; GitHub Actions run `34443774429` passed; exact production release is `9f4605fd55039704d335da7bda33662b9c234528` with rollback `21c162e0333c328e06f9a83ad7bee7b1bdf2abdf`.

Production-copy verification using the real stored S13 detail evidence SHA `3334984f1fc2a56e601261eeea84f9c6356a82ef11ccffb05b8d0e560fb4c971` proved `changed=1 / signals_created=0 / signals 45->45` while restoring the v2 canonical payload. Live Bangkok remains `PASS / GREEN`, `194 canonical / 45 signals / backlog 0`, DB quick check `ok`, both acquisition and Telegram timers active, and Telegram dry-run has zero pending messages. The historical false signal remains preserved for audit rather than deleted.

The same audit attempted to improve current `doms:12735` using only existing PDF capability. Its three issuer PDFs were all effectively scan-only under `pypdf==6.16.2` (2/5/2 pages with only 1/4/1 extracted characters), so deadline/scope remain `UNKNOWN / REVIEW`. OCR is not activated for this single record; it remains an evidence-triggered future capability. Continue existing-source semantic/missing-field audits before adding S41/S42 solely for source count. Evidence: `docs/verification/S13-PARSER-NOISE-DOMS-AUDIT-PRODUCTION-CLOSURE-2026-09-10.md`.

## S34 PTD text-PDF semantic production closure — 2026-09-10

The existing-source business-value audit found 28 `OPPORTUNITY` canonicals with no deadline and no customer signal. S34 PTD was selected before adding new sources because its six 2026 procurement records already linked official PDFs and explicitly carried `HTML_EVENT_SCOPE_PDF_DEADLINE_UNPARSED`. All six PTD PDFs are text-native under the existing `pypdf==6.16.2` stack; five expose a safely parseable schedule and one remains fail-closed UNKNOWN because extracted date glyphs are incomplete. No OCR or new dependency was introduced.

PR #119 upgrades S34 to required same-origin single text-PDF enrichment while retaining Direct HTTP and canonical identity. PTD section 3 is stored as `deadline_kind=TENDER_FORM_SALE_CLOSE`, meaning the tender-form sale/availability close rather than an asserted bid-submission deadline; section 6 is preserved separately as tender-opening date/time. `opportunities -> briefing -> Telegram` carries this distinction end to end, and Telegram labels it `获取标书截止` rather than generic `截止`. Full suite is `246 passed`; PR #119 verify run `34451641329` passed and squash-merged as `69ae03d47eab719152f09134f33a35cfef467e80`.

Production-copy verification then disproved PR #119's initial raw-HTML-SHA enrichment-suppression predicate: PTD ASP.NET pages can change non-business bytes, so a temporary production DB copy produced `changed=1 / signals_created=1` even though only PDF-derived semantics changed. The real production database remained clean at `45` signals and `0` S34 signals. PR #120 replaces that rule with a one-time semantic projection: only a pre-v2 PTD canonical whose non-PDF business payload is identical can suppress the initial capability-enrichment signal; once enriched, later real PDF schedule changes emit `UPDATED`. PR #120 verify run `34452719347` passed and squash-merged as final production SHA `5fc7625da9c19599ef0a1dd1e6b3fca68d90013b`.

Exact deployed-release production-copy verification on `5fc7625...` returned `SUCCESS / health_probe=true / changed=1 / signals_created=0 / signals 45->45 / S34 0->0` while correctly enriching `ptd:2026-07-31:a683b1bfdd91b4c7` to sale close `2026-08-20` and opening `2026-08-25 14:30`. Final archive SHA256 is `526efb4855bd54b44511629879749ca9d945585372cb5d3fa63de5dc912de61c`. Live Bangkok is `PASS / GREEN`, `194 canonical / 45 signals / backlog 0`, DB quick check `ok`, both timers active and Telegram dry-run pending `0`. No forced historical S34 backfill is performed because all five safely parsed sale-close dates are already expired; future new PTD tenders enter the v2 HTML+PDF path immediately. Continue existing-source semantic/missing-field audits before adding S41/S42 for source count. Evidence: `docs/verification/S34-PTD-TEXT-PDF-SEMANTIC-PRODUCTION-CLOSURE-2026-09-10.md`.

## S31 MOEA HTML Semantic v2 production closure — 2026-09-10

The next existing-source business-value audit found 28 production canonicals with `business_stage=OPPORTUNITY`, no customer signal and `deadline=null`. S29/S32/S36 are embedded-image paths, S30 historical `mofa:56952` uses a JPG attachment, and current DOMS evidence is scan-heavy, so those paths would require OCR. S31 MOEA was selected because its issuer archive already embeds actionable procurement narrative in hidden HTML comments and therefore offered a zero-new-capability improvement.

PR #122 upgrades S31 from `moea-tender-archive-card-v1 / moea-tender-normalize-v1` to v2 while retaining the same Direct HTTP archive, HTML-only production acquisition, metadata-only PDF attachments and `moea-archive-event-fingerprint-v1` identity. v2 distinguishes explicit `BID_SUBMISSION_DEADLINE` from `TENDER_APPLICATION_ACCEPTANCE_CLOSE`; a form-sale window alone or an unrelated generic `နောက်ဆုံး` date remains non-actionable. Telegram now renders the kinds as `投标截止` and `投标申请接收截止` respectively. The live issuer's 2026-05-28 record is recovered as `2026-06-10 16:00 / TENDER_APPLICATION_ACCEPTANCE_CLOSE`; 2026-02-04 remains UNKNOWN rather than adding listing-level PDF acquisition for a historical record.

A source-opt-in one-time listing semantic migration guard allows existing v1 canonicals to adopt v2 fields without customer-facing parser-only `UPDATED` noise only when all non-semantic business fields are identical. A v2 correction test proves later deadline changes still emit `UPDATED`. Targeted tests pass `22/22`; full suite `249/249`; PR #122 Actions run `34455774263` PASS and squash-merged as exact production application `038a78e195df0a8ea98f256d7bc2862e0234f6f8`. Deployment archive SHA256 is `5a8dcb0cf17c77b94d23e41976f1c8071aa964a57b3716a6ab4e34f505168ff3`; rollback is `5fc7625da9c19599ef0a1dd1e6b3fca68d90013b`.

Reviewed production `signalforge-refresh@S31.service` completed `SUCCESS / MANUAL / items=9 / tenders=9 / changed=9 / signals_created=0` with Worker correlation `signalforge-20260910T083612Z-03b7f75a`. S31 moved `semantic v2 0->9` while global signals stayed `45->45` and S31 signals `0->0`. Current customer output remains exactly `9 opportunities = 8 OPEN + 1 UNKNOWN`; Telegram dry-run pending `0`. Final Bangkok remains `PASS / GREEN`, `194 canonical / 45 signals / backlog 0`, DB quick check `ok`, both timers active. Continue existing-source semantic/signal-noise audits; do not introduce OCR merely to complete expired image-only historical records. Evidence: `docs/verification/S31-MOEA-HTML-SEMANTIC-V2-PRODUCTION-CLOSURE-2026-09-10.md`.

## S31 MOEA HTML Semantic v3 production closure — 2026-09-10

The post-v2 existing-source audit examined all silent `OPPORTUNITY + deadline=null` canonicals and found one additional HTML-only semantic gap: `moea:2023-06-09:c4536709e24937fd` already contained the explicit issuer phrase `တင်ဒါလျှောက်လွှာ တင်သွင်းရမည့်နောက်ဆုံးရက် - (၂၇ - ၆-၂၀၂၃)` but v2 recognized only the shorter tender-submission marker. PR #124 adds this explicit tender-application-submission final-date synonym, maps it to `BID_SUBMISSION_DEADLINE`, and upgrades S31 parser/normalizer to v3 without adding PDF acquisition, OCR or changing canonical identity.

The rollout guard is now a source-configured `listing_semantic_migration {from_version:2,to_version:3,suppress_signal:true}` rather than an open-ended UNKNOWN-to-known suppression. It suppresses only the configured parser transition when all non-deadline business fields are identical; once v3, a later real deadline change still emits `UPDATED`. Targeted tests are `12 passed`, full suite `249 passed`, and PR #124 Actions run `34462131786` PASS. Exact production runtime is `1e2f5b74860d0d88b7435789a8482706eddf784e`, archive SHA256 `a7a2a8c01b526df93006460f020e8dc7e0acffafde7a6cbf316c6cf581fc932a`, rollback `038a78e195df0a8ea98f256d7bc2862e0234f6f8`.

Fresh production-copy replay and the reviewed production `signalforge-refresh@S31.service` both returned `SUCCESS / changed=9 / signals_created=0`. Production Worker run `signalforge-20260910T094447Z-d486be93` moved S31 `v2 9->0 / v3 0->9`, kept global signals `45` and S31 signals `0`, and recovered the 2023 record as `deadline=2023-06-27 / BID_SUBMISSION_DEADLINE`. Current customer output remains `9 opportunities = 8 OPEN + 1 UNKNOWN`; Telegram pending `0`; Bangkok remains `PASS / GREEN`, `194 canonical / 45 signals / backlog 0`, DB quick check `ok`, both timers active. Silent deadline-unknown count is now `25` (`S26=2, S29=4, S30=1, S31=5, S32=2, S34=5, S36=6`), and a full scan of their existing HTML/business text found no second safely extractable explicit deadline. Stop optimizing historical UNKNOWN count; next audit should move to decision quality of the nine current customer opportunities. Evidence: `docs/verification/S31-MOEA-HTML-SEMANTIC-V3-PRODUCTION-CLOSURE-2026-09-10.md`.

## S39 Energy closing-context correctness closure — 2026-09-10

The current-opportunity audit found that S39 already labeled deadline evidence as `OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME` while parser v1 merely selected the last date-time anywhere in a text-native PDF. PR #126 tightens only evidence admission: `energy-html-plus-text-pdf-v2` accepts exactly one date-time whose bounded context contains tender semantics before it plus tolerant final/closing and submission semantics after it; zero or multiple candidates fail closed. Four reviewed Energy PDFs retain their existing deadlines, while new tests prove a later unrelated date-time is ignored, no-closing-context is rejected and ambiguous closing candidates fail closed. Targeted Energy tests `7 passed`; full suite `250 passed`.

Production `energy:235` evidence SHA `4d2ef1694aa6a7221b1a2d46799eadba7f8edb9ef46a2045c573e07c1760c94b` is byte-identical to the reviewed fixture. Branch and deployed-release parser v2 both produced deadline `2026-09-18 13:00` and canonical content hash `05fcbb728ea55e100291a1d0471ee1832dcdae0355ba616c48880f957f7d9cc1`, exactly equal to production. Therefore no semantic migration/backfill was required and no customer signal was created. PR #126 Actions run `34463254136` PASS, exact runtime `195515f7a8267ca79155a973d23fff29f1ea52cc`, archive SHA256 `46b4c264dc1b8e08ddeee08ef5fd6aefaf95d543eccebca792cd20732c5459ed`, rollback `1e2f5b74860d0d88b7435789a8482706eddf784e`. Reviewed S39 Worker run `signalforge-20260910T095651Z-9da87c0b` returned `SUCCESS / changed=0 / signals_created=0`; direct deployed parser verification returned `hash_equal=true`. Bangkok remains `PASS / GREEN`, `194 canonical / 45 signals / backlog 0`, Telegram pending0 and both timers active. Next audit remains customer deadline semantics: all eight OPEN opportunities currently have `deadline_kind=null`. Evidence: `docs/verification/S39-ENERGY-CLOSING-CONTEXT-PRODUCTION-CLOSURE-2026-09-10.md`.

## S30 MOFA submission-deadline correctness closure — 2026-09-10

The current-opportunity evidence audit found that S30 MOFA labeled enriched PDF deadlines as `OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME` while parser v2 selected the maximum date-time anywhere in the PDF. PR #128 replaces that with `mofa-wordpress-html-optional-text-pdf-v3`: a deadline must be on a line whose prefix contains tender + submission semantics, identical duplicate values are allowed, and zero or multiple distinct submission deadlines fail closed. Sale dates and unrelated tender event times are rejected. MOFA targeted tests `8 passed`; full suite `251 passed`. Production `mofa:59800` PDF SHA `aad5b2c3e51ffc289edb5018254f364896b01d14bee8fa3be7e362e756e130c7` is byte-identical to the reviewed fixture. Branch and deployed v3 both produce `2026-09-18 16:30` with canonical hash `e46bd2662665590426e91c64e2e3dad49e6baeb18a3ec41efe37c63266b9b262`, exactly equal to production, so no migration/backfill or parser-only signal occurred. PR #128 exact runtime `5ef49168c6f6d9f18f80d02d6b593c7b1fa77d28`, archive SHA256 `f3cf2d000c56c789051b9e0920725906d3f7b5fdbf7acc4a3993c46a5c2e1f4a`, rollback `195515f7a8267ca79155a973d23fff29f1ea52cc`. Reviewed S30 Worker run `signalforge-20260910T112656Z-4a72605b` returned `SUCCESS / changed=0 / signals_created=0`; deployed parser verification returned `hash_equal=true`. Bangkok remains `PASS/GREEN`, `194 canonical / 45 signals / backlog 0`, opportunities `8 OPEN + 1 UNKNOWN`, Telegram pending0. Next product-quality issue: all eight OPEN opportunities still expose `deadline_kind=null`; solve in the read/customer layer where evidence permits rather than rewriting canonical rows only for presentation. Evidence: `docs/verification/S30-MOFA-SUBMISSION-DEADLINE-PRODUCTION-CLOSURE-2026-09-10.md`.

## Read-layer deadline-kind production closure — 2026-09-10

PR #130 closes the customer-semantic gap where all eight current OPEN opportunities had `deadline_kind=null` despite source-reviewed evidence. `current_opportunities()` now derives `BID_SUBMISSION_DEADLINE` only for S30/S39 `OFFICIAL_TEXT_NATIVE_PDF_CLOSE_DATE_TIME` and S38 `EXPLICIT_HTML_TENDER_CLOSE_DATE_TIME`; canonical values always take precedence and no other source is inferred. No canonical rows or signals are rewritten. Targeted opportunity/briefing/Telegram tests `20 passed`; full suite `252 passed`. A production DB snapshot returned `8 OPEN -> 8 BID_SUBMISSION_DEADLINE`, `1 UNKNOWN -> null`, with identical DB SHA before/after read. PR #130 Actions run `34471797826` PASS. Exact runtime `0c310c5185f899a633f91dad0d0afd72810f1974`, archive SHA256 `393eeef9fc7cbd04a4a92838dc0f41a64e93dd6627fef63b0bf20414124810ee`, rollback `5ef49168c6f6d9f18f80d02d6b593c7b1fa77d28`. Production opportunities now expose eight bid-submission deadlines while the underlying eight canonical `deadline_kind` fields remain null; briefing propagates the kind and Telegram renders current OPEN attention as `投标截止`; no replay is generated and pending remains 0. Bangkok remains `PASS/GREEN`, `194 canonical / 45 signals / backlog 0`. Next audit: confirm whether MEDIUM watchlist items should remain summary-only or need a separate low-noise delivery policy. Evidence: `docs/verification/READ-LAYER-DEADLINE-KIND-PRODUCTION-CLOSURE-2026-09-10.md`.

### MEDIUM watchlist delivery audit — 2026-09-10

No delivery change is required. The existing `HIGH + REVIEW` Telegram policy is intentional and dynamically promotes a MEDIUM opportunity once it enters the <=72h urgency window. Production-snapshot simulation at `2026-09-12T00:00:00Z` moved `industry:1034` to `HIGH / URGENT / ACT_NOW` and Telegram dry-run produced exactly that one new pending item, while four later industrial MEDIUM items remained in watchlist and existing delivered attention items were not replayed. Keep MEDIUM summary-only; do not add individual MEDIUM pushes or a second watchlist delivery mechanism unless future evidence shows missed decisions.

## Source portfolio audit + S41 MYTEL production closure — 2026-09-10

The business-value audit separated technical health from business yield: most sources are GREEN, but customer signals are concentrated in a much smaller set; S25's twenty historical normalization `UPDATED` rows are not counted as productive yield. S40's zero canonical state was re-audited and is consistent with its current award/result-heavy page, while S15A MPA remains an intentional Manual P0 source and was not duplicated. The clearest uncovered strategic feed was MYTEL procurement via Viettel Global. PR #132 activates S41 as Bangkok `ACTIVE_PRIMARY / direct_http / listing_complete_business_records=true` using the formal strict-TLS `viettelglobal.com.vn` host and a narrowly host-bound `cloudrity_d1n_v1` cookie bootstrap; no beta-host TLS bypass, Browser Plane, pagination engine, PDF or OCR. The official category-82 feed is bounded to `limit=100` (361660 bytes live), which covered all sixteen raw 2026 MYTEL posts found in the 240-row audit. Parser folds invitation/extension by RFP serial+year, treats explicit Proposal submission deadline as `BID_SUBMISSION_DEADLINE`, extension-only bid-document collection close as `TENDER_FORM_SALE_CLOSE`, and fails closed otherwise. Live100 produced 15 canonical RFPs, with 12 latest-version 2026 records all having actionable dates and three older 2025 records UNKNOWN rather than guessed. Targeted S41+contract tests `12 passed`; full suite `260 passed`. Pre-merge Bangkok temporary-DB end-to-end gate returned baseline `changed=15/signals=0`, then `changed=0/signals=0`. PR #132 CI run `34475619689` PASS; exact runtime `c5c2327c2300e5d7a22fce3222552bf8c6de7cc9`; archive SHA256 `20d307a63c9a71ed948442e3c36fd0f52d0ee3ebb5b0ca8bd8ad0baaa270c7f1`; rollback `0c310c5185f899a633f91dad0d0afd72810f1974`. Production baseline Worker `signalforge-20260910T121631Z-e0b86f14` created 15 S41 canonical and zero signals; second Worker `signalforge-20260910T121702Z-86d64458` returned changed0/signals0. Production is `209 canonical / 45 signals / backlog0`, opportunities unchanged `8 OPEN + 1 UNKNOWN`, Telegram pending0, S41 fetch/freshness/parse/source health all GREEN and next_due is on the normal 30-minute cadence. Evidence: `docs/verification/S41-MYTEL-SOURCE-ONBOARDING-PRODUCTION-CLOSURE-2026-09-10.md`.

## S42 ATOM source audit — DEFERRED — 2026-09-10

Post-S41 telecom coverage audit checked ATOM Myanmar before adding another source. ATOM's official public web exposes supply-chain sustainability and partner/business surfaces, but bounded official-site/web searches found no public tender/RFP/RFQ archive or repeatable anonymous supplier-bidding feed. Bangkok strict-TLS `https://www.atom.com.mm/sitemap.xml` returned HTTP 200 / 131679 bytes and contained zero occurrences of `tender`, `procurement`, `supplier`, `rfp`, `rfq` or `sourcing`; `robots.txt` likewise exposed no procurement surface and `sitemap_index.xml` returned 404. This does not mean ATOM lacks procurement activity or private/invitation-only sourcing systems; it means there is currently no qualifying public acquisition surface for SignalForge. Do not create S42, credentialed portal automation, Browser/Provider flow or workaround merely to close the operator-coverage gap. Re-open only on evidence of an official public procurement surface, a real current opportunity with a stable official URL, or separately authorized credentialed supplier-portal access. Evidence: `docs/verification/S42-ATOM-SOURCE-AUDIT-DEFERRED-2026-09-10.md`.

## Source portfolio business-yield audit — PROVISIONAL TIERS / NO RUNTIME CHANGE — 2026-09-10

After S41 MYTEL activation and S42 ATOM deferral, production has `209 canonical / 45 raw signals / backlog0`. Portfolio accounting now distinguishes raw audit history from effective business yield: `45 - 20` known S25 normalization-noise UPDATED rows `- 1` known S13 parser-only historical UPDATED = **24 effective business signals**. Current effective contribution is S13=10, S38=6, S20=3, S26=2, S08A=1, S30=1, S39=1; all other active sources are currently zero. This does **not** authorize source pruning because production observation windows are only <1 to ~8 days and all active sources are baseline-complete with zero consecutive failures. Provisional analytical tiers are: Core/proven yield = S13/S20/S30/S38/S39; Strategic Watch = S16/S21/S22/S27/S34/S35/S41; Context/regulatory/selective = S05A/S07/S08A/S10/S12/S26; Observation/low-yield candidates = S25/S28/S29/S31/S32/S33/S36/S37/S40. These tiers do not modify runtime `role`, `priority`, polling or provider/direct-http topology. Default pruning/promotion re-audit gate is 30 days of production observation per source, with earlier review only on concrete health/noise/missed-opportunity/high-yield evidence. Continue optimizing signal correctness and customer decision value rather than source count. Evidence: `docs/verification/SOURCE-PORTFOLIO-BUSINESS-YIELD-AUDIT-2026-09-10.md`.

## S39 Energy multi-reference read-layer production closure — 2026-09-10

Customer decision-quality audit found that current HIGH/A/ICT `energy:235` contains eleven explicit procurement package identifiers in its already reviewed official text-native PDF scope while the read view exposed only top-level notice reference `ENERGY-27-2026-2027`. PR #136 adds a strictly source-scoped read-only derivation in `current_opportunities()`: canonical reference bundles always win; only S39 items with `HTML_ID_PUBLICATION_PLUS_TEXT_PDF_SCOPE_DEADLINE` may derive repeated exact `DMP/L-xxx(yy-yy)` references; at least two distinct values are required; other Energy reference grammars remain untouched. Targeted opportunities tests `8 passed`, full suite `262 passed`; production-copy DB SHA remained identical before/after read while `energy:235` exposed 11 refs and briefing/Telegram propagated them. PR #136 CI run `34481911436` PASS; exact production runtime `20f2a7e8cd92671e98155bf963a291cd9a5ec3ba`; archive SHA256 `7d2f8ad0e584d8bc703c5bb6d6e75428b2e13c5f13b9ffbd5878735b3e5a47b6`; rollback `c5c2327c2300e5d7a22fce3222552bf8c6de7cc9`. Post-deploy remains `PASS/GREEN / 209 canonical / 45 signals / backlog0 / 8 OPEN + 1 UNKNOWN / Telegram pending0`; direct DB payload for `energy:235` still has null `reference_numbers/reference_count`, proving no canonical migration. Evidence: `docs/verification/S39-ENERGY-MULTI-REFERENCE-READ-LAYER-PRODUCTION-CLOSURE-2026-09-10.md`.

## Multi-reference evidence-label hotfix closure — 2026-09-10

PR #138 fixes a provenance-label bug exposed by the S39 multi-reference read-layer rollout: qualification v1 previously appended `MULTI_REFERENCE_HTML_TITLE` for every `reference_count>1`, which was correct for DOMS but false for Energy references derived from official text-PDF scope. The reason is now evidence-aware: `HTML_TITLE -> MULTI_REFERENCE_HTML_TITLE`, `OFFICIAL_TEXT_NATIVE_PDF_SCOPE_* -> MULTI_REFERENCE_OFFICIAL_PDF_SCOPE`, otherwise `MULTI_REFERENCE_EVIDENCE`. Decision semantics are unchanged, so qualification policy remains v1. Targeted tests `12 passed`, full suite `263 passed`, Actions run `34482888173` PASS. Exact production runtime `3700e675327cd599797fc0eaef8ddb8d0e289005`, archive SHA256 `521424aa404b32b1af54257f50a6d0c8da42e8c65e4fcda1d4cc1af115d7da82`, rollback `20f2a7e8cd92671e98155bf963a291cd9a5ec3ba`. Live Energy retains `A/HIGH`, 11 refs and correct PDF reason; DOMS retains HTML-title reason; production remains `209 canonical / 45 signals / 8 OPEN + 1 UNKNOWN / Telegram pending0 / DB ok`. Evidence: `docs/verification/MULTI-REFERENCE-EVIDENCE-LABEL-HOTFIX-PRODUCTION-CLOSURE-2026-09-10.md`.

## Telegram time-based urgency escalation audit — PASS / NO RUNTIME CHANGE — 2026-09-10

Customer decision-quality audit verified that deadline urgency escalation already works without a new issuer signal. Qualification v1 recomputes urgency at read time; `business_briefing()` maps `URGENT` to `ACT_NOW`; Telegram delivery identity includes `attention_action`, so the same `latest_signal_id` can be delivered again when customer action changes and is then receipt-deduplicated. Bangkok Telegram timer evaluates every 5 minutes (`OnCalendar=*-*-* *:0/5:45 UTC`, `RandomizedDelaySec=10s`). A production read-only future-time dry-run moved `industry:1034` to `ACT_NOW/HIGH/URGENT` at 2026-09-11 16:01 Myanmar with unchanged signal id and receipt count `4 -> 4`. Added an end-to-end regression across real qualification/opportunities/briefing/Telegram; Telegram tests `11 passed`, full suite `264 passed`. No second scheduler, synthetic urgency signal, canonical rewrite or BKK deploy is needed. Evidence: `docs/verification/TELEGRAM-TIME-BASED-URGENCY-ESCALATION-AUDIT-2026-09-10.md`.

## S39 ICT focus-reference production closure — 2026-09-10

Customer decision-quality audit found that `energy:235` was correctly `ICT/HIGH` but its 11-package mixed scope made the relevant lots hard to identify inside a bounded Telegram excerpt. PR #141 adds a strictly read-only, S39/DMP-specific focus layer: the full 11 references remain visible, while four explicit ICT/Telecom packages are separately surfaced as `focus_reference_numbers` — `DMP/L-026`, `067`, `073`, `089` — with `focus_relevance=ICT_TELECOM`; briefing prioritizes their scope and Telegram adds `🧩 相关分包`. No generic lot NLP/classifier, parser migration, canonical write or delivery-key change. Targeted tests `26 passed`, full suite `267 passed`; production-copy DB SHA remained unchanged. PR #141 CI run `34491863462` PASS; exact production runtime `33a0aafa35ac01225d3b988be842f47245b47514`; archive SHA256 `678d8ccc32b874f7b53cbaa7006009f3892028821be2572dd7806850ab50d67d`; rollback `3700e675327cd599797fc0eaef8ddb8d0e289005`. Live remains `A/HIGH / 11 total refs / 4 ICT focus refs / 8 OPEN + 1 UNKNOWN / 209 canonical / 45 signals / Telegram pending0 / DB ok`. Evidence: `docs/verification/S39-ICT-FOCUS-REFERENCES-PRODUCTION-CLOSURE-2026-09-10.md`.
## Business Digest v1 production closure — 2026-09-10

PR #146 closes the product-observability gap where SignalForge had strong acquisition/health telemetry but did not visibly summarize business yield for the operator. The new Business Digest is separate from immediate Attention delivery: `telegram-deliver` continues to send only HIGH/REVIEW action events, while `telegram-digest` sends one compact daily Myanmar business report and makes the MEDIUM watchlist visible without turning it into alert spam. The production funnel at rollout is now explicitly observable as **27 monitored sources -> 209 canonical items -> 45 raw signals -> 9 current opportunities -> 4 immediate Attention items + 5 MEDIUM watchlist items**, with the prior portfolio audit retaining **24 effective business signals** after excluding 20 known S25 normalization-noise rows and one known S13 parser-only historical row.

Business Digest v1 reports a rolling 24-hour activity window plus the current opportunity snapshot: monitored/GREEN/degraded sources, polled/changed sources, scheduler activity, records changed, evidence fetched, items parsed, NEW/UPDATED signals, HIGH/MEDIUM/REVIEW opportunity counts, immediate-Telegram delivery counts, the current Attention shortlist, Watchlist count, Auditor result, bounded MPT/MYTEL reconciliation, ATOM surface trigger status, and cumulative canonical/signal totals. It does not change source acquisition, parser/canonical identity, qualification, or the existing immediate Alert delivery key/policy. Schema v7 adds only `digest_delivery_receipts`, giving once-per-Myanmar-calendar-day success-receipt dedup independent of per-signal delivery receipts.

PR #146 Actions run `34504021465` PASS; targeted digest/contract/db tests `11 passed`; full suite `280 passed`; `git diff --check` PASS. Exact production runtime is `40ad4f4d4e2f935e9ed77cceb044f9bf8d61240a`, archive SHA256 `b648171f22148e2bf61cff9d211d823a4099d6a46f9000d54f162a2801f834fa`, rollback `b19a775e8413181206b3c4e0adb68fd03f0be257`. The first deployed production dry-run returned 27/27 GREEN sources, 27 sources polled in 24h, 4 sources changed, 35 records changed, 1578 evidence artifacts fetched, 2807 items parsed, one 24h signal (`UPDATED`, S13), 9 current opportunities (`HIGH=3 / MEDIUM=5 / REVIEW=1`), four cumulative immediate Telegram alerts, and Auditor `PASS / findings=0`.

Because the first deployment was invoked by the previous release's deploy script, the newly introduced digest units were not yet part of that old installer and initially appeared `not-found`. The exact deployed release units were then installed manually, `systemd-analyze verify` passed, and the timer was intentionally kept disabled until the real production dry-run message was reviewed. The first real Business Digest was then sent successfully through `signalforge-telegram-digest.service`; receipt `digest_date=2026-09-10`, channel `telegram-business-digest`, Telegram provider message id `7`, sent at `2026-09-10T16:48:42.427867Z`. A same-day dry-run returned `deduplicated=true / pending_count=0`. The daily timer is now enabled/active at `02:00 UTC = 08:30 Asia/Yangon`; first scheduled next run was `2026-09-11 08:30:24 +0630`. Acquisition, immediate Alert, and daily Digest timers are all active. Final production gate: `PASS/GREEN / 209 canonical / 45 signals / backlog0 / Auditor PASS0 / alert pending0 / schema7 / digest_receipts=1 / DB quick_check=ok`. Evidence: `docs/verification/BUSINESS-DIGEST-V1-PRODUCTION-CLOSURE-2026-09-10.md`.
## Source Business Yield Scorecard v1 production closure — 2026-09-10

PR #148 adds a read-only `source-scorecard` business-yield surface so the operator/AI can inspect all active sources by actual contribution rather than health alone. The scorecard deliberately separates **Strategic Tier** from **Observed Yield** and does not mutate source role, priority, polling, parser, canonical, qualification or Telegram delivery. The live production summary is: **27 active monitored sources / 27 GREEN / 207 canonical from active sources + 2 S15A Manual P0 canonical = 209 DB total / 45 raw signals / 21 known historical noise / 24 effective signals / 9 current opportunities / 2 ICT-Telecom current opportunities / 4 Telegram alerts**. Yield-state distribution: `ACTIONABLE_PROVEN=4 / SIGNAL_PROVEN=3 / BASELINE_ONLY=18 / NOISE_ONLY_HISTORY=1 / EMPTY=1`.

The four currently actionable-proven sources are S38 Industry (`6 effective signals / 6 current opportunities / 1 TG`), S26 DOMS (`2 / 1 / 1`), S39 Energy (`1 / 1 / 1`) and S30 MOFA (`1 / 1 / 1`). Three more sources have proven effective signal generation without current opportunity/TG contribution: S13 MPT (`10 effective`), S20 MOEP (`3`) and S08A Customs Auction (`1`). S25 remains `NOISE_ONLY_HISTORY` because its twenty audited historical normalization-only UPDATED rows are accounting exclusions; S40 Labour is `EMPTY` after ~2 days and must not be pruned yet. All other zero-yield sources remain baseline-only. No pruning/promotion is authorized before the 30-day observation gate without concrete failure/noise/missed-opportunity/high-yield evidence.

Targeted scorecard+contract tests `9 passed`; full suite `285 passed`; final pre-merge production-copy returned the exact live summary above. PR #148 Actions run `34506868912` PASS. Exact production runtime `bb8ed3146c69b7727d8143f06f3467c49f16ec33`; archive SHA256 `ada3348483a78baa09b7f25196bc4e5ba88da303f04c9516288f89e4ecd72c1e`; rollback `40ad4f4d4e2f935e9ed77cceb044f9bf8d61240a`. Live `signalforge source-scorecard --window-days 30` reproduces the same summary and the manifest exposes `signalforge-source-scorecard -> source-scorecard`. Final production remains `PASS/GREEN / 209 canonical / 45 signals / backlog0 / immediate TG pending0 / daily digest deduplicated / DB quick_check ok`; acquisition, immediate Alert and daily Digest timers are all active. Evidence: `docs/verification/SOURCE-BUSINESS-YIELD-SCORECARD-V1-PRODUCTION-CLOSURE-2026-09-10.md`.
## Business Digest Source Yield Summary production closure — 2026-09-11

PR #150 makes the daily Telegram Business Digest surface the already-production-verified Source Business Yield Scorecard instead of requiring an operator/AI to query it separately. The change is read/render-only: it reuses `source_scorecard(..., window_days=30)` and does not change source execution, qualification, Telegram alert policy, digest receipt identity, timer cadence, schema, parser, canonical or signal semantics. The visible daily KPI now distinguishes proven source yield and effective business signals from raw signal rows.

The production preview after deployment returned **27 monitored / 27 GREEN / 7 of 27 proven sources / actionable 4 / signal-only 3 / baseline 18 / noise-only 1 / empty 1**, plus **209 canonical / 24 effective business signals / 45 raw signals / 9 current opportunities / 4 cumulative immediate Telegram alerts**. The next-day dry-run remained pending only because no 2026-09-11 receipt existed yet; production receipt count stayed `1`, proving no preview delivery was written. Immediate Telegram dry-run remained `pending=0`; DB `quick_check=ok`; acquisition, immediate Alert and daily Digest timers remained active. The next Digest timer remained scheduled for `2026-09-11 08:30:04 +0630`.

Targeted digest+scorecard tests `10 passed`; full suite `285 passed`; PR #150 Actions run `34510340590` PASS. Exact production runtime `bd86efcaa5699f1aa5082459cd57882b8ffe4e73`; archive SHA256 `13cb4a9592c31ac427c17d81040373c4c223c6587c14c43e5745b235ca752d05`; rollback `bb8ed3146c69b7727d8143f06f3467c49f16ec33`. The live no-network render showed the intended user-visible lines `Source产出：7/27 proven ...` and `24 effective / 45 raw signals`. Scheduled Digest execution still defaults to network-backed Auditor coverage checks; the no-network preview intentionally showed strategic-network fields as skipped/unknown. Evidence: `docs/verification/BUSINESS-DIGEST-SOURCE-YIELD-SUMMARY-PRODUCTION-CLOSURE-2026-09-11.md`.

## Production Assurance Report v1 — 2026-09-11

A fresh read-only Bangkok production audit confirms the current funnel and its limits: **27/27 GREEN / backlog0 / 209 canonical / 45 raw signals / 24 effective signals / 9 current opportunities / 4 immediate Telegram receipts**. Only **7/27** sources have proven effective business yield so far (4 actionable + 3 signal-only); the remaining observation windows are too short to justify pruning before the existing 30-day gate. Network Auditor returned `PASS / findings=0`: S13 MPT bounded recent reconciliation PASS, S41 MYTEL `15 official / 15 canonical / missing0`, ATOM official sitemap `NO_TRIGGER`; global external completeness remains explicitly `NOT_PROVEN`. The sole FAILED scheduler row in the preceding 24h was an S35 issuer read timeout that subsequently recovered to GREEN with consecutive failures 0.

The daily Business Digest was then observed at its natural 08:30 Yangon schedule without manual delivery: service started `08:30:04`, exited `0/SUCCESS` at `08:30:09`, sent exactly one 2026-09-11 digest with Telegram provider message `8`, persisted the second daily digest receipt, and a post-send dry-run returned `deduplicated=true / pending0`. Immediate Telegram dry-run also remained `pending0`. Current decision focus is Industry `industry:1022` closing 2026-09-11 16:00, Energy `energy:235` and MOFA `mofa:59800` closing 2026-09-18, plus DOMS `doms:12735` held in REVIEW with unknown deadline rather than guessed. Continue optimizing decision value, miss/noise evidence and semantic correctness rather than raw source count or new infrastructure. Evidence: `docs/verification/SIGNALFORGE-PRODUCTION-ASSURANCE-REPORT-V1-2026-09-11.md`.

## Actionable baseline + MTE commercial Signal production closure — 2026-09-11

PR #153 closes two business-value gaps exposed by the user-supplied ground-truth sample `MTE Local Marketing and Milling Department, Open Tender No (6/2026-2027)(15.9.2026)`: first, a real commercial opportunity could be intentionally filtered because S32 treated buyer-side procurement as the only Signal-worthy MTE event; second, valid future S21/S22 tenders already present in canonical state could remain invisible to the customer view because they arrived during suppressed first baseline and had no Signal. The product rule is now explicit: **Signal means a trustworthy new fact that can change a business action; it is not limited to buyer-side procurement.** Buyer procurement remains `TENDER`; the narrow MTE seller-side Local Marketing open tender is `AUCTION_NOTICE / SELLER_OPEN_TENDER_SALE / BUY_FROM_ISSUER`. Its official `15.9.2026` title date is stored as `action_date=2026-09-15 / TENDER_EVENT_DATE`, never rewritten as a bid-submission deadline.

S21 Myanma Railways and S22 IWT now opt into bounded actionable-baseline reconciliation. Date-only issuer deadlines are eligible through a conservative Myanmar-date lower bound for reconciliation only; no artificial `deadline_time` is persisted or rendered. Legacy S21/S22 TENDER rows may be read as opportunities only when the source explicitly opts into this policy. Read-layer source-scoped evidence reuses S21 project scope + tender-close date and S22 project scope + official deadline datetime without rewriting historical canonical payloads. The result is intentionally noise-bounded: four S21 rows and one S22 row appear as `A / MEDIUM` Watchlist items and do not become immediate Telegram alerts; `mte:1605` appears as `B / REVIEW / SOON` Attention because its event date is explicit but image-carried lot details are still unparsed. Existing S32 buyer-procurement payloads remain byte-equivalent to v1 so parser-v2 selection does not manufacture historical UPDATED signals.

PR #153 Actions run `34558692274` PASS; full suite `291 passed`. Exact production runtime is `cb847afc59e71ef89ba3ee57a1ca1707792ec7e0`; archive SHA256 `8e643dbd73fbad74021003fd3153aa13a8cd64d1f337d658da4233171600190f`; rollback `bd86efcaa5699f1aa5082459cd57882b8ffe4e73`. Fresh production-copy + live Bangkok network predicted exactly `209->210 canonical / 45->51 signals / 9->15 current opportunities`; formal Worker refreshes then reproduced it in production: S21 `MANUAL/SUCCESS changed=0 signals_created=4`, S22 `changed=0 signals_created=1`, S32 `changed=1 signals_created=1`. Final customer view is **15 opportunities = 14 OPEN + 1 UNKNOWN; HIGH=3 / MEDIUM=10 / REVIEW=2 / LOW=0**. Telegram dry-run exposed exactly one pending immediate alert (`mte:1605`); the systemd delivery service sent it successfully, receipt count moved `4->5`, provider message id `9`, and a repeat dry-run returned `pending_count=0`. Final status is `PASS/GREEN / 27 GREEN / 210 canonical / 51 raw signals / 30 effective signals / 15 current opportunities / backlog0`; Source Yield is now `ACTIONABLE_PROVEN=7 / SIGNAL_PROVEN=3 / BASELINE_ONLY=15 / NOISE_ONLY_HISTORY=1 / EMPTY=1`, i.e. 10/27 proven sources. Acquisition, immediate Alert, and daily Digest timers are all active. Evidence: `docs/verification/ACTIONABLE-BASELINE-MTE-COMMERCIAL-SIGNAL-PRODUCTION-CLOSURE-2026-09-11.md`.
