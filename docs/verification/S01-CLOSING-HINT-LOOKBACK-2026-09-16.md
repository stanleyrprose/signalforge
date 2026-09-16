# S01 National Portal Closing-Hint Lookback

Date: 2026-09-16

## Problem

S01 treats Myanmar National Portal as an official discovery aggregator, not canonical truth. Its `Closing Date` field is explicitly hint-only because live audits have shown mixed semantics:

- some cards carry the real tender deadline;
- some cards carry a publication/listing date while the issuer document has a later submission deadline.

The previous parser nevertheless discarded every card whose Portal `Closing Date` was before the current Myanmar date. That made a hint-only field a hard freshness gate and could create false negatives for issuers not already covered elsewhere.

A concrete audit example is the Ministry of Foreign Affairs Technology-topic card: Portal metadata shows 2026-09-04 while issuer evidence already captured by S30 proves the tender remained open until 2026-09-18.

## Decision

Only the S01 Assurance policy opts into a **14-day closing-hint lookback**.

Default parser behavior remains `0` days for existing callers.

The lookback:

- preserves recent mission leads for coverage resolution;
- does not change Portal hint into a canonical deadline;
- does not create canonical items or Signals;
- does not make an unresolved lead a RED miss;
- remains bounded to a maximum accepted configuration of 45 days;
- keeps S01 at max 6 pages / stop after 3 consecutive pages with no mission leads.

## Why 14 days

A live 2026-09-16 audit compared possible windows on the all-tender first six pages.

- 0-day window: 3 mission leads;
- 7-day window: 8 raw mission-title/agency matches before URL validation;
- 14-day window: 10 raw matches before URL validation;
- 30-day window: 21 raw matches;
- 45-day window: 22 raw matches.

After requiring a usable official URL, the 14-day window produced 7 S01 leads on a production database copy.

Production-copy resolution result:

- candidates: 7
- covered: 7
- strict canonical equivalents: 6
- verified external official opportunities: 1
- confirmed gaps: 0
- unresolved leads: 0
- S01 status: PASS

The seven covered leads were the existing MPT verified-external opportunity, S22 IWT canonical-equivalent opportunity, and five S38 Industry records. The widened discovery window therefore increased recall without creating a current business false positive.

## Topic-surface audit

National Portal official topic pages were also checked before changing production scope:

- Communication: 14 pages / about 68 records, no current lead after 2026-09-16; the latest IT/Cyber Security tender on that surface closed 2026-07-17.
- Technology: a 2026-09-07 Office of the Auditor General official JPG was reviewed. OCR confirmed Backup Power for Mini Data Center (640 units), Synology NAS Storage with HDD (1 lot), and air conditioners, but the issuer document closed on 2026-09-07 16:30 and opened on 2026-09-08, so it is expired.
- Power & Energy: recent Portal cards exist but current cards are already represented by issuer-oriented energy coverage or have non-actionable Portal-only metadata.
- Construction / Transportation: current useful cards were the already recovered MPT opportunity and the already covered IWT vessel tender.

No topic surface is therefore added to production polling in this change.

## Verification expectation

Production must remain:

- no new business opportunity solely from this lookback;
- no new Telegram pending delivery;
- no new RED miss;
- S01 remains PASS when all recent hints resolve to canonical/equivalent/verified official coverage.
