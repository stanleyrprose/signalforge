# SignalForge Mission-Focused Output — 2026-09-16

## Business goal frozen

SignalForge primary customer output is now explicitly defined as:

> High-quality Myanmar government / state-owned-enterprise tender and procurement intelligence for engineering, construction/infrastructure, telecommunications/ICT infrastructure, and energy/power/oil-and-gas infrastructure.

Source count, GREEN health, raw canonical volume and raw Signal volume are diagnostics, not the business goal.

## Selection contract

Mission filtering is presentation/business-yield only. It does not delete or rewrite canonical state and does not change source acquisition.

Primary briefing / Telegram / Business Digest include only high-confidence target tenders:

- ENERGY / power / oil-and-gas infrastructure;
- TELECOM;
- CONSTRUCTION / civil / infrastructure;
- ICT infrastructure proven by scope such as Server, Network, Data Center, SCADA/EMS, VMware, Red Hat, etc.;
- engineering procurement proven by scope such as Electrical/Mechanical spares, transformers, substations, conductors, pumps, generators, vessels, bridges, roads and civil works.

Explicitly off-mission examples remain stored but are removed from primary output unless separately reviewed/promoted:

- medical procurement;
- Customs auctions;
- yarn / ordinary commodity procurement;
- Chemical Reagent / Sample Gas;
- refractory/raw-material procurement;
- general logistics/transport services;
- private-operator items such as ATOM/Ooredoo when they are not government/SOE procurement.

## Production-data preview before deployment

Using a copy of the Bangkok production DB on 2026-09-16:

- tracked current opportunities: 17;
- mission-fit current opportunities: 8;
- mission-excluded current opportunities: 9;
- mission sectors: ENERGY 5, ENGINEERING 2, TELECOM_ICT_INFRA 1;
- attention: 6;
- MEDIUM watchlist: 2.

The mission-fit formal opportunities are represented by:

- S39 Energy / ICT procurement;
- S30 MOFA Data Server + Windows Server + SQL Server;
- four current S20 MOEP electricity-system tenders;
- S38 Electrical/Mechanical spare-parts tender (presentation focuses only on engineering sub-scope);
- S22 Coastal Cargo Vessel procurement.

Reviewed non-canonical coverage gaps remain separately visible because they are mission-fit:

- S23 Ayeyarwady bridge works;
- S23 Yangon–Mandalay Expressway maintenance/materials;
- S13 MPT Pobbathiri Exchange Office earthquake repair.

## Scorecard semantics

Source Scorecard v3 now distinguishes tracked activity from mission business value:

- `tracked_current_opportunities` = every current stored opportunity;
- `current_opportunities` = mission-fit current opportunities;
- `tracked_telegram_alerts_total` = historical raw Telegram deliveries;
- `telegram_alerts_total` = deliveries whose canonical business scope is mission-fit.

Observed business yield/recommendation uses mission-fit opportunities and mission-fit Telegram deliveries. This prevents medical/auction/commodity sources from being incorrectly rewarded as actionable business yield.

## Output preview

Production DB copy renders a materially shorter primary digest while retaining all target opportunities and reviewed target gaps. The Business Digest title is now explicitly:

`SignalForge Myanmar 重点招投标`

with scope line:

`政府/国企 · 工程/建设/通讯/能源 · 当前+24h变化`

## Verification gate

- mission/briefing/digest/telegram/scorecard/assurance targeted tests: PASS;
- full suite: 380 passed;
- changed-files Ruff: PASS;
- `git diff --check`: PASS;
- canonical/source acquisition semantics unchanged.
