# S50 MOEE Project Precursor Production Closure — 2026-09-27

## Objective

Extend SignalForge upstream of Tender publication in the electricity/energy domain while preserving honest project-to-procurement lead-time measurement.

S50 is not another Tender source. It observes MOEE latest-news articles for named electricity/energy assets that are still in a future, approval, financing or planning stage.

## Production identity

- PR: #257 `feat: add MOEE project precursor source`
- Active release: `d28b2184d4930369ec93d5e73b14f3ebe23ef6ab`
- Previous release: `fde7f078e23146dddb11208e914aed725f2b7dd3`
- Archive SHA256: `27b4a326559a8bb503144f502ad6bcbd167f70d32f5ed4eef5aa2ebbb385e4df`
- Standard deployment path: `deploy/deploy-signalforge-release.sh`

## Source and parser contract

Discovery URL:

`https://moep.gov.mm/mm/ignite/page/12`

The listing parser:

- captures only the main `content-data-list` latest-news cards;
- excludes the right-hand Tender list structurally;
- does not require project keywords in card titles, because useful project evidence may exist only in the article body.

The detail parser:

- reads the official article title, body and publication date;
- splits body text into project clauses;
- may emit more than one independent reviewed precursor candidate from one article;
- requires a concrete electricity/energy asset plus explicit future / approval / finance / planning evidence;
- rejects operating, underway, completed and open-procurement evidence at the affected clause level;
- uses `MOEE content id + stable normalized project-clause hash` as candidate identity;
- marks every candidate `PROJECT_PRECURSOR_CANDIDATE` and `precursor_review_required=true`.

Human review remains mandatory before lifecycle promotion. Project-to-procurement linking remains explicit/reviewed; fuzzy automatic linking is prohibited.

## Real-site verification before merge

Bangkok read-only parsing against the official MOEE site produced:

- five current main-news discovery entries;
- five of five current detail pages parsed successfully;
- zero current false precursor candidates.

Historical article 7133 was used only as a parser fixture. It contains, in the same paragraph:

1. a Pinpet steel-factory coal-fired steam power plant explicitly described as to be constructed; and
2. a Taunggyi main-substation 230/132kV 150MVA Switchbay explicitly described as already under construction.

The parser emitted exactly one candidate: the future Pinpet plant. The underway Switchbay was rejected.

This demonstrates the required project-clause isolation behavior.

## Historical-boundary rule

`baseline_lookback_days=0`.

Historical articles may prove parser behavior but are never inserted as production detection evidence. S50 detection time begins only for records retained after activation.

## Verification before merge

- focused S50 / contract / scorecard tests: 24 PASS;
- full unit suite: 526 PASS;
- Python compileall: PASS;
- `git diff --check`: PASS;
- GitHub `verify`: PASS.

## Live production acceptance

First production run:

`systemctl start signalforge-refresh@S50.service`

Result:

- `Result=success`;
- `ExecMainStatus=0`.

Latest scheduler run:

- status SUCCESS;
- changed 0;
- signals created 0;
- detail attempts 0;
- detail successes 0;
- items parsed 0;
- error null.

Discovery processing:

- parser `moee-latest-news-project-precursor-list-v1`;
- status SUCCESS;
- items found: 5;
- canonical items: 0;
- signals created: 0.

Source state:

- baseline complete: 1;
- consecutive failures: 0;
- last error: null;
- SQLite `PRAGMA quick_check = ok`.

This is the intended activation state: five current news records establish the baseline without being treated as newly discovered precursor evidence.

## Business and KPI boundary

After activation:

- S50 procurement opportunities: 0;
- project precursor candidates: 0;
- pending review: 0;
- tracked projects: 0;
- linked projects: 0;
- project-to-procurement lead-time remains unmeasured.

Current opportunity output quality remains:

- 8 current business opportunities;
- 6 canonical opportunities;
- 2 verified external opportunities;
- 5/6 canonical opportunities HIGH or VERY_HIGH;
- official-evidence rate 100%.

No S50 precursor is counted as a procurement opportunity.

## Runtime health

Post-refresh:

- SignalForge status: PASS;
- SignalForge health: GREEN;
- monitored sources: 34;
- green sources: 34;
- non-green sources: 0;
- S50 source health: GREEN;
- S50 fetch health: GREEN;
- S50 freshness health: GREEN;
- S50 parse health: UNKNOWN only because no post-activation BUSINESS_PROCESSING detail sample exists yet;
- all four production timers enabled and active/waiting.

## Next final-goal bottleneck

The acquisition side now has three explicit upstream precursor surfaces:

- S48 MOI general official project news;
- S49 Ministry of Construction planned capital works;
- S50 MOEE energy project formation news.

The next bottleneck is no longer simply source count. Once a precursor is reviewed and promoted, SignalForge must make the eventual procurement easy to identify for **human-reviewed explicit linking** so the lead-time sample is actually realized.

The next tranche should inspect the existing lifecycle/linking workflow and add a review-only procurement-link suggestion queue if the current implementation relies on manual discovery. Suggestions may rank evidence for review, but they must never create fuzzy or automatic authoritative links.
