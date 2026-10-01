# Myanmar Official Media Signal Sources — 2026-10-01

Status: IMPLEMENTED / PRODUCTION DEPLOYMENT PENDING

## Purpose

Add official Myanmar government/media surfaces as a bounded early-signal layer for Digital Government, ICT, telecom, cloud/data-center, cybersecurity, shared platforms, PPP, planning/budget and pre-procurement formation.

This is not generic news ingestion and does not replace canonical tender sources.

## Source roles

| Source | Registry | State | Role |
| --- | --- | --- | --- |
| Ministry of Information news | S48 | ACTIVE_SELECTIVE | Official policy/project precursor; reactivated after explicit user goal change |
| Myanmar International TV | S52 | ACTIVE_SELECTIVE | English official Digital/ICT early signals |
| Myanmar Digital News | S53 | ACTIVE_SELECTIVE | Burmese official Digital/ICT early signals |
| Global New Light of Myanmar | S54 | ACTIVE_SELECTIVE | English official newspaper; daily HTML issue + required native-text PDF |
| Myawady Web Portal | S55 | ACTIVE_SELECTIVE_TLS_IGNORED | User-approved HTTPS read-only collection with certificate verification disabled only for Myawady |
| Myanma Alinn / 缅甸之光 | S56 | ACTIVE_SELECTIVE | Daily MOI issue HTML + one reviewed official PDF + Mac DOCUMENT_OCR |
| Kyemon / The Mirror / 镜报 | S57 | ACTIVE_SELECTIVE | Daily MOI issue HTML + one reviewed native-text official PDF |

S37 remains the separate MOI tender/department-announcement source and is unchanged.

## Selection boundary

A candidate must contain at least one reviewed Digital/ICT category and forward-action evidence.

Categories include:

- Digital Government / e-Government / Digital Governance;
- Single Window / One-Stop Digital Services / EDMS / open government data;
- cybersecurity / information security;
- ICT or digital infrastructure;
- cloud / data center;
- telecom / network / fiber / 5G / shared platforms.

Forward-action evidence includes implementation, transition, plan/strategy/law/framework, PPP formation, establishment/development/upgrade/build, budget/funding, procurement-plan or tender-preparation, rollout/platform/service/system language.

Open procurement phrases such as open tender, invitation to tender/bid, RFP/RFQ, and Burmese tender-call phrases are excluded from this early-signal layer so canonical tender sources remain authoritative for actual procurement.

All emitted items are:

- item_kind = REGULATORY_NOTICE
- business_stage = PROJECT_PRECURSOR_CANDIDATE
- precursor_review_required = true

The Telegram customer channel remains canonical-Tender-only; REGULATORY_NOTICE precursor items do not bypass that quality gate.

## e-Government meeting acceptance case

The 29 September 2026 e-Government Steering Committee coordination meeting is a positive acceptance case because the official reports contain multiple forward business signals:

- transition from e-Government to Digital Government;
- Public-Private Partnership (PPP) frameworks;
- Single Window and One-Stop Digital Services platforms;
- information security / cybersecurity;
- National Digital Development Strategy 2030;
- Digital Development Law.

The MITV and MDN detail parsers recognize the article as DIGITAL_GOVERNMENT + CYBERSECURITY + ICT_INFRASTRUCTURE with PPP_FORMATION stage.

GNLM 30 September 2026 native-text PDF is parsed article-locally rather than as one whole newspaper. This prevents an unrelated tender on another page from vetoing or contaminating the Digital Government article. The issue yields “Push to Transition from E-Government to Digital Governance” as a qualifying precursor.

## GNLM attachment contract

S54 discovers daily issue pages from https://www.moi.gov.mm/nlm/.

Each selected issue requires exactly one same-origin PDF attachment. HTTP attachment links are canonicalized to HTTPS only for the reviewed MOI/GNLM origin. PDF text is extracted natively with pypdf; OCR is not invoked when the text layer is usable.

The parser searches bounded article-local windows around reviewed Digital/ICT terms and stores only a bounded relevant scope excerpt rather than the full newspaper.

## Myawady TLS exception

Strict-TLS checks from both Bangkok and Mac failed on 1 October 2026 with a certificate-chain verification error. The user explicitly approved ignoring this issuer-side TLS verification problem for the public read-only Myawady source.

S55 therefore uses a source-scoped TLS-ignore profile rather than a global TLS downgrade:

- certificate verification is disabled from the first request for S55; there is no deliberate strict-TLS failure attempt first;
- the profile is restricted to https://myawady.net.mm and https://www.myawady.net.mm;
- method is GET-only/read-only with no credentials or cookies;
- redirects must remain HTTPS and on the reviewed Myawady hosts;
- all other sources retain the global TLS fail-closed policy;
- acquisition evidence is labeled DIRECT_HTTP_TLS_INSECURE_READONLY.

Live validation on 1 October 2026 successfully read the 80,050-byte English News listing and the 59,410-byte e-Government detail page under this profile. The reviewed e-Government article remains a silent bootstrap acceptance case.

## Myanma Alinn and Kyemon newspaper contracts

S56 discovers daily Myanma Alinn issue pages from https://www.moi.gov.mm/mal/. The 1 October 2026 issue and its reviewed official PDF are reachable over strict TLS, but the PDF's embedded font mapping makes native extraction unusable: pypdf yields large volumes of /gNNN glyph placeholders rather than reliable Burmese text. S56 therefore sends exactly one reviewed MOI PDF URL through the existing Mac DOCUMENT_OCR capability with fixed Burmese+English OCR. The provider boundary is pinned to www.moi.gov.mm and /mal/sites/default/files/newspaper-pdf/; Bangkok does not duplicate-download the PDF. Current production-provider processing is bounded to the first 12 pages per issue.

A real Mac OCR smoke on the 1 October 2026 Myanma Alinn PDF recovered readable Burmese from page 1 (4,058 OCR text characters; mya+eng profile) where native extraction was unusable. The 12-page bounded OCR path also completed.

S57 discovers daily Kyemon issue pages from https://www.moi.gov.mm/km/. Its official PDF has a usable Burmese/English text layer, so the source uses native pypdf extraction rather than OCR. A real 1 October 2026 32-page PDF was fetched and parsed successfully; it yielded zero qualifying Digital/ICT precursor items under the current conservative filter, which is a valid no-signal result rather than a collection failure.

Both sources emit only REGULATORY_NOTICE / PROJECT_PRECURSOR_CANDIDATE, use the same conservative official-media selection boundary as GNLM, and never bypass the canonical Tender Telegram gate.

## Polling / baseline

- S48 MOI: 30 minutes.
- S52 MITV: 30 minutes.
- S53 MDN: 30 minutes.
- S54 GNLM: 60 minutes.
- S55 Myawady: 30 minutes; source-scoped read-only TLS verification disabled.
- S56 Myanma Alinn: 60 minutes; one issue per baseline/delta cycle; reviewed PDF through bounded Mac DOCUMENT_OCR.
- S57 Kyemon: 60 minutes; one issue per baseline/delta cycle; native-text official PDF.

First baseline customer signals are disabled. Initial runs populate canonical/history state without generating a customer Tender Telegram message.

## Parser versions

- MOI precursor selection policy: v3.
- MITV official media adapter: v2.
- MDN official media adapter: v2.
- GNLM official media adapter: v2.
- Myawady transport profile: insecure-readonly v2; source policy v3.
- Myanma Alinn official newspaper adapter: v1 (DOCUMENT_OCR).
- Kyemon official newspaper adapter: v1 (native PDF text).

## Production baseline noise gate

The first S54 production baseline was intentionally silent and exposed over-broad newspaper matching before customer delivery was enabled. Six canonical baseline candidates were created, but zero Signals and zero Telegram messages were emitted.

Review found:
- 30 September e-Government article: true positive;
- 1 October telecom-fraud enforcement article: false positive;
- 28 September tourism digital-platform article: false positive;
- 27 September neighboring tender-page contamination: false positive;
- other weak generic matches: rejected under v2.

v2 therefore adds ASCII token boundaries, narrower article-local windows, high-specificity ICT-infrastructure anchors, and explicit fraud/crime/law-enforcement negative context. Production timers remain gated until v2 replay passes.

## GNLM large-PDF production gate

The 26 September 2026 GNLM issue PDF is 21,553,662 bytes. The initial 6 MB acquisition ceiling therefore failed closed before parsing and caused the bounded backlog item to retry. S54 now uses a 30 MB request ceiling and 60-second timeout, still limited to exactly one reviewed same-origin PDF per issue.
