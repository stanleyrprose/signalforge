# Current Opportunity Business Quality Audit — 2026-09-21

## Scope

Read-only audit of the 12 current SignalForge mission opportunities on production `f87d52e5bfc78af1a1b57caa34540b39869679e6`.

Goal: test customer-facing business usefulness, not source count or health metrics.

Production read model at audit time:

- current opportunities: 12;
- canonical: 9;
- verified external: 3;
- sectors: Construction 4 / Energy 3 / Engineering 5;
- current status: 11 OPEN / 1 UNKNOWN;
- YESC `moep:7150` remains `DETAIL_PARTIAL` after bounded official-source recovery was exhausted.

## Audit result

### ACTION_NOW — 4

1. `moep:7151:2026-09-08` — EPGE — ENERGY
   - industrial/electrical spare parts for hydro plants;
   - deadline `2026-09-22 13:00`;
   - Trust A / quality 97 / FULL;
   - purchase tender document by 9/21, submit Technical/Financial proposals in separate sealed envelopes by 9/22 13:00 at Office No.27, Nay Pyi Taw.

2. `industry:1037` — Ministry of Industry — ENGINEERING
   - environmental-control laboratory apparatus, 5 types, Pang Pet steel plant;
   - deadline `2026-09-22 16:00`;
   - Trust A / quality 93 / FULL;
   - operationally actionable but more tactical/specialized than core infrastructure.

3. `S23:18be5b60-accb-11f1-b41f-3517e3a380a0` — Ministry of Construction — CONSTRUCTION
   - Yangon–Mandalay Expressway maintenance/repair/supervision road-material procurement;
   - deadline `2026-09-23 16:00`;
   - verified issuer PDF / Trust A / FULL;
   - business defect found: current verified-external attention logic does not surface this <=72h final bid deadline.

4. `S23:bed02200-b01f-11f1-b666-953fc0cbe05c` — Ministry of Construction / DUHD — CONSTRUCTION
   - urban/housing Phase (2)/(3) works;
   - tender-form sale ends `2026-09-22`; final bid deadline `2026-10-01 11:00`;
   - verified issuer scan / Trust A / FULL;
   - correctly surfaced as external ACT_NOW after Digest v9.

### ACTION_SOON — 4

5. `industry:1039` — Ministry of Industry — ENGINEERING
   - lubricants plus 23 electrical and 43 mechanical spare-item types for Myingyan steel plant;
   - deadline `2026-09-25 16:00`;
   - Trust A / quality 91 / FULL;
   - actionable but tactical industrial procurement.

6. `S13:aa3cebae-2f59-5c3c-e840-640c99f0cb92` — MPT / MDDC — CONSTRUCTION
   - Pobbathiri Exchange Office earthquake repair;
   - tender-form sale closes `2026-09-24 16:30`; site survey `2026-09-25`; bid deadline `2026-09-29 14:00`;
   - verified National Portal-hosted official MPT PDF / Trust A / FULL;
   - business defect found: reviewed field is `tender_form_sale_close`, while current attention helper only understands `tender_form_sale_end`.

7. `yangon-ycdc-mission:3755` — YCDC — CONSTRUCTION
   - municipal materials including sand/cement/HDPE pipe, chemicals, steel bar, aggregates and fogging machines;
   - deadline `2026-09-29 12:00`;
   - Trust A / quality 90 / FULL;
   - meaningful municipal infrastructure supply opportunity.

8. `industry:1044` — Ministry of Industry — ENGINEERING/CONSTRUCTION
   - reinforced-concrete water tank construction at No.8 Textile Factory, Pyawbwe;
   - deadline `2026-09-29 16:00`;
   - Trust A / quality 79 / FULL;
   - tactical construction project; quantity/lot detail not separately structured but scope is sufficient.

### WATCH — 3

9. `moep:7157:2026-09-11` — DPTSC — ENERGY
   - 230 kV Kamanat–Hlawga 38.4-mile line: replace ACSR with ACCC conductor and procure required materials;
   - deadline `2026-10-01 14:00`;
   - Trust A / quality 83 / FULL;
   - high strategic infrastructure value; not yet urgency-window constrained.

10. `iwt:1039:2026-09-19` — IWT — ENGINEERING
    - replace steel plates on 21 ageing vessels/barges with ASTM A-36 plates;
    - deadline `2026-10-09 10:00`;
    - Trust A / quality 83 / FULL;
    - location/participation detail remains weaker than other A-grade items.

11. `iwt:1038:2026-08-25` — IWT — ENGINEERING
    - procurement of one vessel;
    - deadline `2026-11-03 10:00`;
    - Trust A / quality 93 / FULL;
    - complete contact/submission information; long enough runway to remain WATCH.

### DETAIL_PARTIAL — 1

12. `moep:7150:2026-09-08` — YESC — ENERGY
    - tender event itself is covered by official MOEP HTML;
    - attachment `YESC-4778.pdf` is HTTP 404;
    - deadline and participation details remain unproven;
    - Trust B / quality 49 / PARTIAL / REVIEW;
    - bounded recovery exhausted: exact MOEP page exposes one attachment only; all reasonable URL variants remain 404; National Portal, Kyemon 9/8–9/10, Yangon Region Government and indexed YESC tender surface do not provide exact second official evidence.
    - stop condition: keep `DETAIL_PARTIAL`; do not continue recovery unless new official evidence appears.

## Findings

1. No confirmed false positive or duplicate was found among the 12 current mission opportunities.
2. Evidence quality is now strong for 11/12 opportunities; YESC is the only detail-partial item.
3. Source count is no longer the highest-value optimization target.
4. The highest-value current defect is verified-external urgency handling:
   - final bid deadline can be <=72h without entering top attention;
   - reviewed sources use both `tender_form_sale_end` and `tender_form_sale_close` field names.
5. Attention should be derived from the earliest upcoming actionable milestone, while keeping verified-external items outside canonical Signal semantics.

## Decision

Implement one bounded output-layer fix:

- candidate milestones: tender-form sale end/close, then final bid deadline;
- choose earliest upcoming milestone;
- if it enters <=72h, derive `ACT_NOW` for Business Digest only;
- preserve non-canonical/non-Signal semantics;
- do not add sources or expand OCR/Harness scope as part of this fix.
