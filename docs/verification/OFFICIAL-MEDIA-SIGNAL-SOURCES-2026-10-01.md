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
| Myawady Web Portal | S55 | BLOCKED_TLS_CERTIFICATE | Registered source inventory only; no collection until strict TLS succeeds |

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

## Myawady boundary

Strict-TLS checks from both Bangkok and Mac failed on 1 October 2026 with a certificate-chain verification error.

S55 is therefore registered but disabled:

- role = BLOCKED_TLS_CERTIFICATE;
- acquisition_policy.enabled = false;
- insecure TLS bypass is explicitly forbidden;
- curl -k / certificate verification disablement is not permitted;
- reactivation requires strict TLS to become valid or a separately verified official alternate surface followed by re-audit.

The user-supplied e-Government article URL is retained as a reviewed bootstrap reference for future reactivation.

## Polling / baseline

- S48 MOI: 30 minutes.
- S52 MITV: 30 minutes.
- S53 MDN: 30 minutes.
- S54 GNLM: 60 minutes.
- S55 Myawady: not scheduled while blocked.

First baseline customer signals are disabled. Initial runs populate canonical/history state without generating a customer Tender Telegram message.

## Parser versions

- MOI precursor selection policy: v3.
- MITV official media adapter: v1.
- MDN official media adapter: v1.
- GNLM official media adapter: v1.
