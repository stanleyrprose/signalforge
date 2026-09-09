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
