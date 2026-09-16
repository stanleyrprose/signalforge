# S01 Myanmar National Portal — Assurance Discovery Activation

Date: 2026-09-16 (Asia/Yangon)

## Decision

S01 remains **DEFERRED as a canonical source**. The 2026-09-04 finding remains valid: Myanmar National Portal is an official government aggregator, but its `Closing Date` metadata has previously contradicted issuer-original evidence and therefore cannot override issuer truth.

This change activates S01 only as an **Assurance discovery aggregator**. It does not enter the production scheduler source set, does not create canonical items, and does not create Signals.

Contract:

- role: `DISCOVERY_AGGREGATOR_ONLY`
- current page only
- high-value current lead filter
- `Closing Date` is `HINT_ONLY_NOT_CANONICAL`
- exact canonical/source truth remains issuer-oriented
- unresolved Portal leads remain Assurance evidence only
- a reviewed Portal-hosted official document may prove a coverage gap and open a miss against the issuer-oriented source

## New business evidence that triggered activation

On 2026-09-16 the live National Portal tender page exposed a current tender from the Ministry of Digital Development and Communications / Myanma Posts and Telecommunications that was absent from SignalForge S13 and absent from the live MPT tender page.

Portal-hosted official PDF identity:

`aa3cebae-2f59-5c3c-e840-640c99f0cb92`

Reviewed document SHA-256:

`3dd5dd18a2395ba1bb18bdc31c9fa9850a98aced98fb05b7453c4380d24c9eea`

The text-native official PDF proves an MPT tender for repair of the earthquake-damaged Pobbathiri Exchange Office in Nay Pyi Taw. Reviewed business scope:

- repair RC column/wall cracking and settlement damage;
- replace/repair roof and ceiling;
- tender form sale starts 2026-09-11;
- tender form sale closes 2026-09-24 16:30;
- site survey 2026-09-25;
- tender submission window 2026-09-29 09:30–14:00.

The reviewed deadline is taken from the official PDF, not from the Portal card metadata.

## Live first-page verification

Bangkok/direct-compatible HTTPS fetch of `https://myanmar.gov.mm/tenders` returned HTTP 200 and approximately 223 KB.

The new current high-value lead parser selected exactly one record from the live first page on 2026-09-16:

- National Portal lead: MPT / MDDC tender above;
- target source hint: S13;
- evidence kind: `NATIONAL_PORTAL_HOSTED_DOCUMENT`;
- canonical truth: false.

Current Industry rows and unusable `href="#"` rows were not promoted into the lead set.

## Coverage-gap semantics

The reviewed MPT opportunity is recorded outside canonical state in `Reviewed-Coverage-Gaps-v1.json` and appears in the Business Digest under the reviewed/manual-verification section. It does **not** increment formal current-opportunity count.

S01 Assurance resolution behaves as follows:

1. exact Portal lead URL already represented in canonical state -> covered;
2. exact lead URL represented by a reviewed National-Portal-hosted coverage gap -> confirmed gap;
3. otherwise -> unresolved lead, retained in supplemental Assurance only;
4. unresolved leads do not directly create misses;
5. confirmed reviewed gaps create a RED miss against the target issuer source;
6. aggregator-derived misses automatically resolve to history after the reviewed opportunity deadline expires.

## Product-output boundary

Exact reviewed document URLs remain in the registry/evidence trail. Telegram uses shorter official landing links to preserve message budget. Low-value GREEN/Assurance diagnostic footer text was removed from the Business Digest; those metrics remain available through Assurance/status surfaces.

## Verification gate

Before PR/deploy:

- live National Portal first page: exactly one current high-value lead selected;
- production-DB copy: S01 = GAP, official 1, covered 0, confirmed 1, unresolved 0;
- formal current opportunities remain 17;
- reviewed coverage gaps become 3;
- rendered Business Digest stays below Telegram 4096-character limit;
- full test suite: 373 passed;
- changed-files Ruff: PASS;
- `git diff --check`: PASS.

## Expected production metric effect

After activation, the reviewed MPT gap should create an OPEN RED miss against S13 via `AGGREGATOR_COVERAGE_AUDIT`. Therefore Assurance may correctly report `FAIL` while this current gap remains unresolved. That is an intended business-quality signal, not a runtime regression.
