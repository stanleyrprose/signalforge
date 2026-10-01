# Tender Radar External Pilot Intake

Use this for each manually onboarded design partner.

## 1. Company

- Company name:
- Country/ownership:
- Myanmar operating entity:
- Website:
- Main contact:
- Role:
- Preferred contact channel:

## 2. What the company sells

List concrete products/services, not generic industries.

Products/services:
1.
2.
3.
4.
5.

## 3. Target buyers

List ministries, SOEs, utilities, municipalities, telecom operators or other public buyers that matter.
1.
2.
3.
4.
5.

## 4. Positive Tender keywords

Use 10–30 concrete terms likely to appear in a procurement notice.
1.
2.
3.
4.
5.
6.
7.
8.
9.
10.

## 5. Explicit exclusions

What should never trigger a notification even if a broad category matches?
1.
2.
3.
4.
5.

## 6. Current discovery workflow

- Where do you currently find Myanmar Tender information?
- Who checks it?
- How often?
- Which languages are difficult?
- What is the most recent Tender you discovered too late?
- What irrelevant information wastes the most time?

## 7. Action threshold

What information makes you take immediate action: buyer, product match, value/budget, quantity, deadline, geography, local-partner requirement, bid bond, manufacturer authorization, or something else?

## 8. Pilot delivery

Operator-only fields. Do not commit customer secrets or Telegram identifiers into public Git.

- profile_id:
- Business Profile file location:
- Telegram chat ID storage location:
- commercial owner:
- feedback owner:
- start date:
- planned review date:

## 9. Preflight

- [ ] Business Profile JSON validates
- [ ] MATCHED_ONLY used unless customer explicitly asks for all tenders
- [ ] dry-run executed
- [ ] translation preview reviewed
- [ ] no obvious false positives
- [ ] official source/evidence present
- [ ] Telegram destination independently confirmed
- [ ] no customer secret committed to Git

Example command:

    signalforge telegram-deliver --dry-run --translate-preview --profile /srv/signalforge/state/pilots/<profile-id>.json

## 10. Weekly evidence

- delivered:
- relevant:
- not relevant:
- clicked:
- took action:
- bid/quote initiated:
- explicit willingness to pay:
- false positives:
- missed Tender reported:
- notes:

## Decision

- CONTINUE
- ADJUST PROFILE
- ADJUST ICP
- STOP

Reason:
