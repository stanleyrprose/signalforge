# SignalForge 28-source historical production evidence audit

> Historical evidence scope — added 2026-10-24: the original observations, PASS/FAIL results, deployment SHAs, source roles, cadence, model choices and next-step recommendations below apply to the recorded date/release/subsystem. They do not establish current authorization, deployment or delivery health. Current product requirements follow [GOAL](../../GOAL.md) and the [S01/S52/S53 news contract](../S01-S52-S53-NEWS-DELIVERY-CONTRACT.md); surviving technical controls require confirmation against current code. This scope note does not change the historical results.

Read-only Bangkok production SQLite snapshot: 2026-10-12T11:38:33.555710+00:00

**Scope:** Historical stored canonical TENDER rows and most recent scheduler execution. This is NOT a live re-fetch, original PDF semantic verification, or new S01 production validation. A SUCCESS scheduler status does not prove item+quantity+deadline.

| ID | Source | Last scheduler | Stored tenders | Complete (item+qty+deadline) | Missing item / qty / deadline | Evidence |
|---|---|---|---:|---:|---|---|
| S01 | Myanmar National Portal Official Tender Documents | NOT_RUN  | 0 | 0 | N/A | https://myanmar.gov.mm/tenders |
| S13 | MPT Tender Information | SUCCESS 2026-10-12 | 16 | 12 | 0/3/2 | https://mpt.com.mm/en/pstn-and-ftth-last-mile-maintenance-at-yangon-and-naypyitaw-2/ |
| S21 | Myanma Railways Tenders | SUCCESS 2026-10-12 | 85 | 0 | 0/85/4 | https://www.railways.gov.mm/posts?category=tender |
| S22 | Inland Water Transport Tenders | SUCCESS 2026-10-12 | 5 | 0 | 0/5/0 | https://iwt.gov.mm/tenders |
| S20 | MOEP Main Tender Hub | SUCCESS 2026-10-12 | 12 | 0 | 0/12/12 | https://moep.gov.mm/mm/ignite/page/62 |
| S25 | MONPIFER Ministry Tenders | SUCCESS 2026-10-12 | 10 | 0 | 10/10/0 | https://www.monpifer.gov.mm/my/ministry-tenders |
| S26 | DOMS Medical Procurement Opportunities | SUCCESS 2026-10-12 | 3 | 0 | 0/3/3 | https://www.doms.gov.mm/category/tender/ |
| S28 | Department of Fisheries Open Tenders | SUCCESS 2026-10-12 | 9 | 0 | 9/9/0 | https://www.dof.gov.mm/index.php/my/tender |
| S29 | DWIR Waterway and River Works Tenders | FAILED 2026-10-12 | 5 | 0 | 0/5/5 | https://www.dwir.gov.mm/ |
| S30 | Ministry of Foreign Affairs Procurement Invitations | SUCCESS 2026-10-12 | 2 | 0 | 0/2/1 | https://www.mofa.gov.mm/category/announcement/ |
| S31 | Ministry of Ethnic Affairs Procurement Invitations | SUCCESS 2026-10-12 | 9 | 0 | 1/9/5 | https://portal.moea.gov.mm/index.php?page=ORwuBwpT |
| S32 | Myanma Timber Enterprise Procurement + Local Tender Sales | SUCCESS 2026-10-12 | 2 | 0 | 0/2/2 | https://mte.gov.mm/index.php/en/annoucements |
| S33 | Ministry of Cooperatives and Rural Development Tenders | SUCCESS 2026-10-12 | 5 | 0 | 5/5/0 | https://www.mcrd.gov.mm/index.php?page=dGluZGEmbW8%3D |
| S16 | YCDC Engineering Department (Building) Tender Opportunities | SUCCESS 2026-10-12 | 5 | 0 | 0/5/0 | https://www.ycdc.gov.mm/frontend_engineering_building_detail/1 |
| S34 | Posts and Telecommunications Department Open Tenders | SUCCESS 2026-10-12 | 6 | 0 | 0/6/5 | https://www.ptd.gov.mm/CatAnnouncements.aspx |
| S35 | Department of Advanced Science and Technology Tenders | SUCCESS 2026-10-12 | 9 | 0 | 0/9/0 | https://www.dast.gov.mm/category/tender/ |
| S36 | Department of Agriculture Procurement Announcements | SUCCESS 2026-10-12 | 6 | 0 | 0/6/6 | https://www.doa.gov.mm/doa/index.php?route=cms/category&path=22 |
| S37 | Ministry of Information Ministerial Office Procurement Announcements | SUCCESS 2026-10-12 | 1 | 0 | 0/1/0 | https://www.moi.gov.mm/department-announcement |
| S38 | Ministry of Industry Procurement Announcements | SUCCESS 2026-10-12 | 30 | 6 | 0/24/0 | https://www.industrymsme.gov.mm/announcements/1049 |
| S27 | Ministry of Border Affairs Tender Opportunities | SUCCESS 2026-10-12 | 7 | 0 | 0/7/0 | https://moba.gov.mm/my/tender |
| S39 | Ministry of Energy Collective Tenders | SUCCESS 2026-10-12 | 5 | 0 | 0/5/0 | https://energy.gov.mm/tenders |
| S40 | Ministry of Labour Procurement Invitations | SUCCESS 2026-10-12 | 1 | 0 | 0/1/0 | https://www.mol.gov.mm/tender/ |
| S41 | MYTEL Procurement Invitations via Viettel Global | FAILED 2026-10-12 | 15 | 0 | 0/15/3 | https://viettelglobal.com.vn/en/tender-offer |
| S43 | Yangon Region Ministry of Construction Tenders | SUCCESS 2026-10-12 | 2 | 0 | 0/2/0 | https://www.yangon.gov.mm/category/ministry-of-construction/ |
| S47 | Yangon Region Government — YCDC Mission Tenders | SUCCESS 2026-10-12 | 5 | 0 | 0/5/0 | https://www.yangon.gov.mm/category/tenders/ |
| S15A | Myanma Port Authority Tenders | SUCCESS 2026-10-12 | 1 | 0 | 0/1/0 | https://www.mpa.gov.mm/tenders-and-announcement/ |
| S51 | Digital Development Department Shared ICT Hardware Tenders | FAILED 2026-10-12 | 1 | 1 | 0/0/0 | https://myanmar.gov.mm/documents/20143/0/newspaper+%287%29.pdf/bbf2a100-02b1-4024-716f-e1763c2556d1 |
| S23 | Ministry of Construction National Tenders | SUCCESS 2026-10-12 | 3 | 2 | 0/1/0 | https://construction.gov.mm/letter-download/e2ebde10-b89b-11f1-bcd1-1fcc285ca8bf |

## Interpretation

- A complete row is only field presence in the same stored canonical tender, **not** independent validation that the values are semantically correct or extracted from issuer-authored material.
- Zero stored tenders = **NO_OBSERVED_TENDERS**, not proof of source failure.
- Scheduler FAILED requires separate network/parse diagnostics; SUCCESS with zero tenders may reflect no tenders or selection/parser misses.
- S01 has no deployed production canonical source yet: **NOT_DEPLOYED / UNVERIFIED**. The source adapter is development code only.
- Follow-up live source-by-source re-fetch, evidence PDF/OCR review and false-negative sampling remain required before declaring any source meaningful and healthy.
