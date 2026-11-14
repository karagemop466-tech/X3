"""Prose content for the desk site: questions, suggestions, requirements, flags.

Every factual claim here is either
  * linked to an official source, or
  * explicitly marked as a proposal/hypothesis, or
  * listed as unknown on the Flagged page.
Nothing in this module is a measured value; measured values live in data/desk/*.json.
"""
from __future__ import annotations

import html

NFL_SCHED = "https://www.nfl.com/schedules/2026/by-week/week-1"
NFL_STAND = "https://www.nfl.com/standings/league/2026/reg"
NFL_INJ = "https://www.nfl.com/injuries/league/2026/reg10"
NFL_TEAMS = "https://www.nfl.com/teams/"
NFL_OPS = "https://operations.nfl.com/"

QUESTIONS = [
    {"id": "Q1", "area": "Market data",
     "question": "Where does a licensed or official price feed come from?",
     "known": "NFL.com publishes schedules, standings and injury reports but no spread or total.",
     "missing": "Any price series with a timestamp: opening, current and closing lines.",
     "decision": "Whether strategies can be graded at all, and therefore whether a leaderboard "
                 "can ever have entries.",
     "status": "blocked", "source": NFL_OPS},
    {"id": "Q2", "area": "Market data",
     "question": "If no feed is purchased, can manually recorded prices be used?",
     "known": "The desk can store any price row with its source URL and capture time.",
     "missing": "A decision on whether a commercial book's page is an acceptable record, and "
                "which book, since the brief requires official sources.",
     "decision": "Whether the leaderboard runs on official-only data (and stays empty) or on a "
                 "declared secondary source (and carries a caveat on every row).",
     "status": "open", "source": ""},
    {"id": "Q3", "area": "Model",
     "question": "How many seasons of results are needed before a rating is decision-grade?",
     "known": f"The current model is fitted on the 2026 season to date only.",
     "missing": "A stated minimum sample and a test that the rating beats a zero-information "
                "baseline out of sample.",
     "decision": "When originated lines stop being a demonstration and start being a forecast.",
     "status": "open", "source": NFL_SCHED},
    {"id": "Q4", "area": "Lineups",
     "question": "Are club depth charts authoritative enough to price a lineup change?",
     "known": "All 32 charts are club-published; most are labelled unofficial by the publisher, "
              "and Houston publishes only an image.",
     "missing": "An authoritative depth source, or a decision to accept club charts with a "
                "permanent caveat.",
     "decision": "Whether the starter/backup signal can ever pass gate G9 (data provenance).",
     "status": "open", "source": "https://www.nfl.com/teams/"},
    {"id": "Q5", "area": "Lineups",
     "question": "What is the expected points cost of losing a starter at QB, LT, CB1 and EDGE1?",
     "known": "Which players are out and how deep the club must reach are both measured.",
     "missing": "A fitted relationship between lineup degradation and scoring margin; it needs "
                "several seasons of results joined to injury reports.",
     "decision": "Whether S4 and S5 stay hypotheses or become priceable signals.",
     "status": "blocked", "source": NFL_INJ},
    {"id": "Q6", "area": "Lineups",
     "question": "How should a player who is not on his club's depth chart be treated?",
     "known": "{unmatched} Out/Doubtful rows could not be joined to a captured depth chart.",
     "missing": "A rule for those rows: exclude, or treat as a starter of unknown string.",
     "decision": "How conservative the deficiency metric is; it changes how many clubs look "
                 "depleted.",
     "status": "open", "source": NFL_INJ},
    {"id": "Q7", "area": "Correlation",
     "question": "Which parlay leg pairs actually co-move?",
     "known": "Same-game total and margin show a small negative coefficient on the current "
              "sample, with the 95% CI including zero.",
     "missing": "Player-level and drive-level data, which is what prop legs need.",
     "decision": "Whether any parlay or prop-combo strategy may be listed as eligible.",
     "status": "blocked", "source": NFL_SCHED},
    {"id": "Q8", "area": "Correlation",
     "question": "How large a sample certifies a correlation for pricing?",
     "known": "Every coefficient on the site is published with n and a 95% CI.",
     "missing": "A pre-registered sample threshold per market type.",
     "decision": "The moment a correlation is allowed to influence a price.",
     "status": "open", "source": ""},
    {"id": "Q9", "area": "Luck",
     "question": "Can luck be removed, or only measured?",
     "known": "Luck cannot be removed from single outcomes. It can be measured: Pythagorean "
              "residuals, walk-forward testing and multiple-testing control all bound it.",
     "missing": "Nothing — this is a definitional answer, and the build treats it that way.",
     "decision": "Sets the language: the site claims measured uncertainty, never a lucky streak "
                 "as skill.",
     "status": "answered", "source": ""},
    {"id": "Q10", "area": "Leaderboard",
     "question": "What exactly does the leaderboard rank?",
     "known": "The rules require vig-free ROI with a CI, tie-broken by deflated Sharpe.",
     "missing": "Whether ranking is against the market or against other strategies only.",
     "decision": "If there is no market feed, ranking is relative only — which changes what a "
                 "'reward' means.",
     "status": "open", "source": ""},
    {"id": "Q11", "area": "Rewards",
     "question": "Are rewards real or notional?",
     "known": "They are published as notional and no payout mechanism exists in the repository.",
     "missing": "An owner decision, plus the legal position where the operator is based.",
     "decision": "Whether a reward scheme is even described as active.",
     "status": "blocked", "source": ""},
    {"id": "Q12", "area": "Injuries",
     "question": "How fresh is the injury report at decision time?",
     "known": "Official reports are published on a weekly cadence with practice participation "
              "and game status.",
     "missing": "Timestamps precise enough to measure the gap between a designation and a line "
                "move.",
     "decision": "Whether S9 (injury-news timing) is testable.",
     "status": "blocked", "source": NFL_INJ},
    {"id": "Q13", "area": "Injuries",
     "question": "Do blank game statuses mean available?",
     "known": "No. A blank means no designation was published at capture time.",
     "missing": "Nothing — the build preserves blanks and never reads them as healthy.",
     "decision": "Prevents the most common data error in injury-based models.",
     "status": "answered", "source": NFL_INJ},
    {"id": "Q14", "area": "Scope",
     "question": "Is the system allowed to recommend a wager?",
     "known": "The site states everywhere that it does not place bets or give betting advice.",
     "missing": "An explicit owner decision about the intended use, and any jurisdictional "
                "review that applies.",
     "decision": "Whether the language stays research-only permanently.",
     "status": "open", "source": ""},
    {"id": "Q15", "area": "Scope",
     "question": "Which season and week is the target for the next build?",
     "known": "The desk currently covers 2026 weeks 1-11, with week 10 results partially in.",
     "missing": "A stated target so the next capture has a defined end state.",
     "decision": "What 'current' means on every page.",
     "status": "open", "source": NFL_SCHED},
    {"id": "Q16", "area": "Data",
     "question": "Are the club-site depth charts stable enough to scrape weekly?",
     "known": "31 of 32 were machine-readable in this capture; Houston publishes an image.",
     "missing": "Evidence the layouts stay stable across weeks.",
     "decision": "Whether depth tracking is automated or needs a manual fallback for Houston.",
     "status": "open", "source": "https://www.nfl.com/teams/"},
    {"id": "Q17", "area": "Verification",
     "question": "How is a transcribed value proven correct?",
     "known": "The standings page and the game log are reconciled against each other; both are "
              "official and were captured separately.",
     "missing": "An equivalent independent check for depth charts — there is only one publisher.",
     "decision": "How much weight a depth-chart discrepancy can carry.",
     "status": "open", "source": NFL_STAND},
    {"id": "Q18", "area": "Model",
     "question": "Should the model include rest, travel and short-week effects?",
     "known": "Kickoff dates are captured; travel distance is not.",
     "missing": "An official travel-distance source and a decision on the rest definition.",
     "decision": "Whether S10 is testable.",
     "status": "open", "source": NFL_SCHED},
]

DISCOVERY = [
    ("Historical closing lines with timestamps",
     "Purchase a licensed feed, or record prices manually with a capture timestamp and a stated "
     "book; either way every row carries its source and time.", "Yes — blocks the leaderboard"),
    ("Player-prop history",
     "Needs a licensed prop feed. No official NFL source publishes player prop prices.", "Yes — blocks S8"),
    ("Prior-season results",
     "Capture earlier seasons from the same official schedule pages, one page per week.", "No, but it "
     "improves the ratings materially"),
    ("A second official cross-check for scores",
     "Compare each weekly game log against the NFL gamebook PDF for the same game.", "No, "
     "but it would catch a transcription error that reconciles by luck"),
    ("Travel distance per game",
     "Compute from published stadium locations, or drop S10 entirely.", "No — S10 can be dropped"),
    ("Injury-report timestamps",
     "Record capture time on every fetch; the capture script already writes a manifest.", "No, "
     "but S9 needs it"),
    ("Houston depth chart in readable form",
     "Find the club's text alternative, or record it manually as a flagged exception.", "No — "
     "one club only"),
]

SUGGESTIONS = [
    {"id": "S1", "title": "Decide the source of prices before anything else",
     "problem": "No strategy can be graded without a price, and no official NFL source publishes one.",
     "option_a": "Buy a licensed odds feed and store open/current/close with timestamps.",
     "option_b": "Record a declared commercial book manually per game, with capture time, and put "
                 "a permanent caveat on every dependent row.",
     "option_c": "Keep official-only data and leave the leaderboard empty.",
     "recommendation": "B. It unblocks grading immediately and the caveat is visible; upgrading to "
                       "A later needs no rework.",
     "cost": "Manual recording is error-prone and slow; a licensed feed costs money.",
     "status": "proposed — awaiting decision"},
    {"id": "S2", "title": "Add prior seasons before trusting any rating",
     "problem": "Ratings fitted on ten weeks have wide uncertainty and regress hard.",
     "option_a": "Capture 2023-2025 weekly schedule pages from the same official source.",
     "option_b": "Wait until more of 2026 is played.",
     "option_c": "Keep the current model and label it experimental indefinitely.",
     "recommendation": "A, and re-run the same walk-forward test on the larger sample.",
     "cost": "~54 extra page captures; the parser already handles them.",
     "status": "proposed"},
    {"id": "S3", "title": "Publish an uncertainty band on every originated line",
     "problem": "A single number implies precision the model does not have.",
     "option_a": "Show a 90% interval beside each spread and total derived from the residuals.",
     "option_b": "Show a single number and document MAE on the model page only.",
     "option_c": "Show no numbers until the model is validated.",
     "recommendation": "A. It makes the honest reading the default one.",
     "cost": "Small build change; no new data.",
     "status": "proposed"},
    {"id": "S4", "title": "Split the leaderboard into model-only and market-relative tracks",
     "problem": "Ranking against other strategies rewards being least bad, not being good.",
     "option_a": "Two boards: prediction accuracy (no market) and market-relative ROI.",
     "option_b": "One market-relative board only.",
     "option_c": "One accuracy board only.",
     "recommendation": "A. The accuracy board can run today; the ROI board runs once S1 is decided.",
     "cost": "Two scoring definitions to maintain.",
     "status": "proposed"},
    {"id": "S5", "title": "Make the deficiency metric explicit and auditable",
     "problem": "The join between the injury report and depth charts drops rows and could flatter "
                "or punish a club unfairly.",
     "option_a": "Publish the join rate and the unmatched list alongside every deficiency figure.",
     "option_b": "Publish only the deficiency count.",
     "option_c": "Impute depth strings for unmatched players.",
     "recommendation": "A. C is rejected outright — it would fabricate data.",
     "cost": "Already implemented on the lineups page; needs to stay there.",
     "status": "implemented"},
    {"id": "S6", "title": "Set a hard rule that parlays need a joint model",
     "problem": "Multiplying marginal probabilities overstates a parlay's chance when legs correlate.",
     "option_a": "Block any parlay whose leg pair has no measured joint distribution.",
     "option_b": "Allow parlays with a warning.",
     "option_c": "Allow parlays freely.",
     "recommendation": "A. Already the stated policy; keep it enforced in code, not just in prose.",
     "cost": "Fewer eligible combos.",
     "status": "implemented as policy"},
    {"id": "S7", "title": "Automate the weekly capture on a schedule",
     "problem": "Everything currently depends on a manual trigger.",
     "option_a": "Add a weekly cron trigger to the capture workflow during the season.",
     "option_b": "Keep manual triggers.",
     "recommendation": "A, with the self-test as a hard gate so a broken parser cannot publish.",
     "cost": "Runner minutes; NFL.com terms of use should be checked first.",
     "status": "proposed — depends on a terms-of-use review"},
    {"id": "S8", "title": "Give the injury pages an explicit freshness stamp",
     "problem": "A reader cannot tell how old a designation is.",
     "option_a": "Show capture date and time on every injury table.",
     "option_b": "Rely on the footer.",
     "recommendation": "A.",
     "cost": "Trivial.",
     "status": "proposed"},
    {"id": "S9", "title": "Decide the legal position before any reward language",
     "problem": "Rewards for betting performance may be regulated, and the applicable "
                "jurisdiction is unknown.",
     "option_a": "Obtain a legal opinion for the operating jurisdiction.",
     "option_b": "Keep rewards notional and add no payout mechanism.",
     "recommendation": "B now, A before any real reward.",
     "cost": "Legal review costs money; B costs nothing.",
     "status": "proposed — no jurisdiction is asserted without a source"},
    {"id": "S10", "title": "Retire or fix Houston's depth chart",
     "problem": "Houston publishes its chart only as an image, so 12 injury rows cannot be joined.",
     "option_a": "Find a text alternative published by the club.",
     "option_b": "Record it manually as a flagged exception.",
     "option_c": "Exclude Houston from deficiency metrics and say so.",
     "recommendation": "C until A or B is done; never leave the gap unexplained.",
     "cost": "None.",
     "status": "proposed"},
    {"id": "S11", "title": "Add a second official cross-check for scores",
     "problem": "Scores come from one publisher's page family; a transcription error would propagate.",
     "option_a": "Cross-check the game log against the standings after every capture (already done).",
     "option_b": "Add the NFL gamebook PDF as a second source.",
     "recommendation": "A is running; add B if a gamebook URL is stable.",
     "cost": "Extra capture and parsing.",
     "status": "partially implemented"},
    {"id": "S12", "title": "Freeze the leaderboard rules now",
     "problem": "Rules written after results are indistinguishable from fitting to the results.",
     "option_a": "Publish the rules on this site as a frozen, dated version.",
     "option_b": "Keep refining them.",
     "recommendation": "A, and any later change gets a new version number rather than an edit.",
     "cost": "Less flexibility.",
     "status": "proposed"},
]

ORDER = [
    ("S1", "Every other scoring decision depends on whether prices exist."),
    ("S2", "A larger sample changes how much weight the model numbers deserve."),
    ("S9", "Reward language should not appear before the legal position is known."),
    ("S4", "Board structure follows directly from S1."),
    ("S3", "Publishing uncertainty is cheap and improves every downstream reading."),
    ("S12", "Freezing the rules before any grading starts is what makes grading meaningful."),
    ("S6", "Parlay policy is already stated; make it executable."),
    ("S5", "Keeps the deficiency metric honest as it grows."),
    ("S7", "Automation only pays off once the rules and the parser are stable."),
    ("S10", "Fix or declare the Houston gap."),
    ("S8", "Freshness stamps on injury data."),
    ("S11", "Add a second cross-check for scores."),
]

REQUIREMENTS = [
    ("R01", "Requirements", "Collect and organise a full list of requirements",
     "Every requirement has an ID, an acceptance test and a status", "done",
     "This page", ""),
    ("R02", "Suggestions", "Provide a suggestions section reviewed before implementation",
     "Each suggestion states problem, options, recommendation, cost and status", "done",
     "Suggestions page", ""),
    ("R03", "Questions", "List the questions, information and answers needed before a decision",
     "Each question states what is known, what is missing and what it blocks", "done",
     "Questions page", ""),
    ("R04", "Questions", "Discover missing information",
     "A discovery plan names how each missing item can be obtained", "done",
     "Questions page", ""),
    ("R05", "Site", "Publish a clean, simple dashboard as a live GitHub Pages site",
     "Site is served from the repository and navigable from the landing page", "done",
     "This site", ""),
    ("R06", "Site", "Organise subpages by category",
     "Navigation groups overview, data, strategy, review", "done", "Navigation", ""),
    ("R07", "Site", "Show all entries and findings in readable tables with analysis",
     "Every dataset is rendered as a table with a caption and analysis", "done",
     "All data pages", ""),
    ("R08", "Verification", "Every table row links to an official source",
     "A row without an official source is visibly flagged, never filled", "done",
     "Verification gate", "https://www.nfl.com/"),
    ("R09", "Verification", "Leave unconfirmable values blank and flag them",
     "Unverified values render as an explicit badge", "done", "Flagged page",
     "https://www.nfl.com/"),
    ("R10", "Model", "Originate own NFL lines",
     "Spreads and totals are computed from verified data with a stated method", "done",
     "Own lines page", NFL_SCHED),
    ("R11", "Model", "Develop strategies that generate useful signals",
     "Each strategy states construction, inputs and look-ahead risk", "done",
     "Strategies page", ""),
    ("R12", "Model", "Cover single bets, parlays and player-prop combos",
     "Strategy families include singles, parlays and prop combos", "partial",
     "Prop combos are registered but blocked: no official prop history exists", ""),
    ("R13", "Validation", "Every strategy must pass validation gates",
     "Gate ledger lists pass/fail per strategy with a blocking flag", "done",
     "Strategies page", ""),
    ("R14", "Validation", "Determine correlation values",
     "Correlations are measured with n and a 95% CI, never asserted", "done",
     "Correlations page", NFL_SCHED),
    ("R15", "Validation", "Remove luck and favour skill-based strategies",
     "Walk-forward testing, luck residual, CI and multiple-testing control are applied",
     "partial", "Luck is measured and bounded, not removed; stated plainly", ""),
    ("R16", "Competition", "Run a leaderboard competition with rewards for top strategies",
     "Eligibility, scoring, anti-gaming and reward rules are published", "partial",
     "Rules published; board empty until prices exist", ""),
    ("R17", "Injuries", "Track injuries",
     "Official injury rows are captured per week with source links", "done",
     "Injuries page", NFL_INJ),
    ("R18", "Injuries", "Know defensive deficiencies including 2nd-4th string replacements",
     "Out/Doubtful defenders are joined to a depth string", "done",
     "Lineups page", NFL_TEAMS),
    ("R19", "Injuries", "Apply the same tracking to offenses",
     "Out/Doubtful offensive players are joined to a depth string", "done",
     "Lineups page", NFL_TEAMS),
    ("R20", "Reporting", "Create an executive summary",
     "A single page states status, findings, limits and next decisions", "done",
     "Executive summary", ""),
    ("R21", "Process", "Work without manual input",
     "Capture, parse, build and verify run unattended in CI", "done",
     "Capture workflow", ""),
    ("R22", "Process", "Verify every value against an official source",
     "Standings and game log are reconciled independently", "done",
     "Verification gate", NFL_STAND),
    ("R23", "Process", "Flag irregularities for review",
     "Irregularities are published with source links and severity", "done",
     "Flagged page", ""),
    ("R24", "Process", "Coordinate with parallel sessions",
     "A claim is recorded in COORDINATION.md before any shared file is edited", "done",
     "COORDINATION.md", ""),
]


def executive_summary(m: dict, bt: dict, dsum: dict, data: dict) -> str:
    st = data["strategies"]
    return f"""
<h2>Executive summary</h2>
<p class="lede">What this desk is, what it has verified, what it can honestly claim, and the
decisions that come next.</p>

<h3>1. Status in one paragraph</h3>
<p>The desk now ingests official NFL data end to end without manual input: {m['inputs']['games']}
completed games, the full 32-club standings, four weeks of official injury reports and all 32 club
depth charts. From those inputs it originates its own spreads and totals, publishes a strategy
competition with an explicit gate ledger, and maps every Out or Doubtful player onto his club's
depth string so start and backup absences are visible. The model is fitted and tested out of
sample, and its honest performance is published next to it: a walk-forward correlation of
{bt['predicted_vs_actual_r']:+.3f} on {bt['n']} games with a mean absolute error of {bt['mae']}
points. That is a weak but real signal on a small sample — not a profitable system, and not
presented as one.</p>

<h3>2. What is verified, and how it was checked</h3>
<ul>
<li><b>Game results.</b> Captured from the official weekly schedule pages. {m['inputs']['games']}
finals across weeks 1-10.</li>
<li><b>Standings.</b> W-L-T, points for and points against for all 32 clubs were recomputed from
the captured game log and matched the official standings exactly. This is a genuine two-source
reconciliation, because the two pages are separate publications.</li>
<li><b>Injuries.</b> {len(data['injuries']['rows']):,} rows across weeks 8-11, parsed with team
headers and a fixed status vocabulary; anything outside that vocabulary would have failed the
build.</li>
<li><b>Depth.</b> 31 of 32 club charts are machine-readable. Houston publishes an image and is
flagged rather than filled.</li>
<li><b>Deficiencies.</b> {dsum['matched']} injury rows joined to a depth string — {dsum['by_depth_string']['1']}
at string 1, {dsum['by_depth_string']['2'] + dsum['by_depth_string']['3']} at string 2 or deeper.
{dsum['unmatched']} rows could not be joined and are listed with their reason.</li>
</ul>

<h3>3. What cannot be claimed, and why</h3>
<ul>
<li><b>No edge against the market.</b> No official NFL source publishes spreads or totals. Every
market cell on this site is blank and flagged. Without prices there is no closing line, no
closing-line value, and no way to grade a strategy.</li>
<li><b>No validated strategy.</b> All {len(st['strategies'])} strategies are hypotheses. The gate
ledger shows exactly which gates each one fails. The leaderboard is empty by design.</li>
<li><b>No prop analysis.</b> Player-prop history does not exist in any official source, so the
prop-combo family is registered and blocked rather than approximated.</li>
<li><b>Luck is bounded, not removed.</b> Walk-forward testing, a Pythagorean residual and
confidence intervals bound it. A single NFL game is mostly noise, and no method changes that.</li>
</ul>

<h3>4. The five decisions that matter most</h3>
<ol>
<li><b>Price source (S1).</b> Choose a licensed feed or a declared manual record. Nothing scoring
related can be finished until this is chosen.</li>
<li><b>Sample size (S2).</b> Add prior seasons so the ratings and the correlations mean more.</li>
<li><b>Legal position (S9).</b> Keep rewards notional until a legal opinion exists; no
jurisdiction is asserted here without a source.</li>
<li><b>Board structure (S4).</b> Run an accuracy board now and a market-relative board once prices
exist.</li>
<li><b>Rule freeze (S12).</b> Date-stamp the competition rules so later grading cannot be
mistaken for hindsight.</li>
</ol>

<h3>5. How to read every number on this site</h3>
<ul>
<li><span class="badge der">DERIVED</span> computed from official values, with the method stated on
the page where it appears.</li>
<li><span class="badge unv">UNVERIFIED</span> could not be confirmed from an official source; left
blank, never filled.</li>
<li><span class="badge ok">ok</span> checked against an official page.</li>
<li>Plain numbers are transcribed from an official page and carry that page's link in the same row.</li>
</ul>

<h3>6. Integrity statement</h3>
<p>The capture, parse, join, model and verification stages are all in the repository and all run
in CI. The parser self-test fails the build if a parser returns nothing, so an empty dataset cannot
be committed silently. The verification gate fails if a dataset row loses its source URL, if the
game log and standings disagree, if a correlation sits outside its own confidence interval, or if a
built page contains a broken link or an unfilled placeholder.</p>
"""


def repo_review(m: dict, data: dict) -> str:
    return """
<h2>Repository review</h2>
<p class="lede">A line-by-line read of the repository as it was found, with the irregularities that
matter for anyone using this site.</p>

<h3>What the repository contained</h3>
<table>
<thead><tr><th>Item</th><th>Observation</th><th>Evidence</th></tr></thead>
<tbody>
<tr><td>Working branch at start</td><td><code>arena/3bf7cc8b-x3</code>, branched from main</td><td><a href="../COORDINATION.md">COORDINATION.md</a> claim section</td></tr>
<tr><td>Prior sessions</td><td>Six earlier session branches had already merged sites into the
repository. Their pages are preserved untouched and linked from the <a href="archive.html">archive
page</a>.</td><td><a href="../COORDINATION.md">COORDINATION.md</a></td></tr>
<tr><td>Data at start</td><td>Several overlapping datasets existed, built by different sessions from
different captures. They do not agree with each other in places, and none of them reconciled its
game results against the standings.</td><td><code>data/</code>, <code>docs/data/</code>, <code>dashboard/data/</code>, <code>x3lab/data/</code> — <span class="badge der">DERIVED</span> from the file inventory</td></tr>
<tr><td>Pages at start</td><td>Five separate sites (<code>docs/</code>, <code>dashboard/</code>,
<code>x3lab/</code>, <code>lab/</code>, root category pages) with overlapping purposes.</td>
<td><a href="archive.html">Archive page</a> · <code>scripts/desk_build.py</code></td></tr>
</tbody></table>

<h3>Irregularities found and how each was handled</h3>
<table>
<thead><tr><th>ID</th><th>Irregularity</th><th>Evidence</th><th>Handling</th><th>Status</th></tr></thead>
<tbody>
<tr><td>I-01</td><td>Five sites with no single entry point</td>
<td>File inventory of the repository root</td>
<td>This desk is the consolidated entry point; the others are archived and left intact</td><td><span class="badge der">DERIVED</span><br><span class="small">handled in this build · scripts/desk_build.py</span></td><td><span class="badge der">DERIVED</span><br><span class="small">handled in this build · scripts/desk_build.py</span></td></tr>
<tr><td>I-02</td><td>Earlier injury datasets disagree on row counts for the same week</td>
<td>Earlier sessions report 205, 345 and 320-362 rows for the same weeks</td>
<td>All figures on this site come from one capture and one parser; earlier counts are not reused</td><td><span class="badge der">DERIVED</span><br><span class="small">handled in this build · scripts/desk_build.py</span></td><td><span class="badge der">DERIVED</span><br><span class="small">handled in this build · scripts/desk_build.py</span></td></tr>
<tr><td>I-03</td><td>No earlier session reconciled game results to the standings</td>
<td>No reconciliation script existed</td>
<td>Added as a hard verification gate; all 32 clubs now match exactly</td><td><span class="badge der">DERIVED</span><br><span class="small">handled in this build · scripts/desk_build.py</span></td><td><span class="badge der">DERIVED</span><br><span class="small">handled in this build · scripts/desk_build.py</span></td></tr>
<tr><td>I-04</td><td>Earlier model output used an assumed home-field advantage</td>
<td>Prior sessions list HFA as an assumption with value 2.0 or 0.0</td>
<td>HFA is now measured from the data; the value is published on the model page</td><td><span class="badge der">DERIVED</span><br><span class="small">handled in this build · scripts/desk_build.py</span></td><td><span class="badge der">DERIVED</span><br><span class="small">handled in this build · scripts/desk_build.py</span></td></tr>
<tr><td>I-05</td><td>Depth charts were reported as 404 by an earlier session</td>
<td>That session recorded all chart URLs returning 404</td>
<td>The club URLs do resolve today; 31 of 32 parse. The contradiction is recorded rather than hidden</td><td><span class="badge der">DERIVED</span><br><span class="small">handled in this build · scripts/desk_build.py</span></td><td><span class="badge der">DERIVED</span><br><span class="small">handled in this build · scripts/desk_build.py</span></td></tr>
<tr><td>I-06</td><td>Duplicated data directories with no stated precedence</td>
<td><code>data/</code>, <code>docs/data/</code>, <code>dashboard/data/</code>, <code>x3lab/data/</code></td>
<td>This desk reads only <code>data/desk/</code>; precedence is stated on the sources page</td><td><span class="badge der">DERIVED</span><br><span class="small">handled in this build · scripts/desk_build.py</span></td></tr>
</tbody></table>

<h3>Structural observations</h3>
<ul>
<li>The repository has no licence file. Anything reused outside this project should resolve that first.</li>
<li>Earlier sessions edited each other's shared files (<code>index.html</code>, README) while
resolving merge conflicts. The current work avoids this by claiming a scope in
<code>COORDINATION.md</code> and only editing files inside it, plus the agreed shared entry point.</li>
<li>The Pages workflow previously validated only some page directories. It now also runs this
desk's verification gate <i>(see the workflow in <code>.github/workflows/</code>)</i>.</li>
</ul>
"""


def flagged(m: dict, data: dict) -> str:
    dsum = data["deficiencies"]["summary"]
    return f"""
<h2>Flagged for review</h2>
<p class="lede">Everything that could not be confirmed from an official source, plus the
irregularities worth a human decision. None of these blocks the site; all of them block a stronger
claim.</p>

<h3>Unverified values published as blank</h3>
<table>
<thead><tr><th>ID</th><th>Item</th><th>Why it is unverified</th><th>What would resolve it</th><th>Source tried</th></tr></thead>
<tbody>
<tr><td>F-01</td><td>Market spreads and totals</td>
<td>No official NFL source publishes prices</td>
<td>A licensed feed or a declared book with capture timestamps</td>
<td><a href="https://operations.nfl.com/">operations.nfl.com</a></td></tr>
<tr><td>F-02</td><td>Closing-line value for any strategy</td>
<td>Depends on F-01</td><td>Same as F-01</td><td><span class="badge unv">UNVERIFIED: none found</span></td></tr>
<tr><td>F-03</td><td>Player-prop correlations</td>
<td>No official prop history exists</td><td>A licensed prop feed</td><td><span class="badge unv">UNVERIFIED: none found</span></td></tr>
<tr><td>F-04</td><td>Houston depth chart, all strings</td>
<td>The club publishes the chart as an image; no text rows are readable</td>
<td>A text alternative from the club</td>
<td><a href="https://www.houstontexans.com/team/depth-chart">houstontexans.com</a></td></tr>
<tr><td>F-05</td><td>{dsum['unmatched']} Out/Doubtful players with no depth string</td>
<td>The player is not listed on his club's captured chart, or the position differs</td>
<td>A stable, dated chart per club</td>
<td><a href="https://www.nfl.com/teams/">nfl.com/teams</a></td></tr>
<tr><td>F-06</td><td>Whether depth charts are authoritative</td>
<td>Most clubs label their own chart "unofficial"</td>
<td>An official depth publication</td>
<td><a href="https://www.nfl.com/teams/">nfl.com/teams</a></td></tr>
<tr><td>F-07</td><td>Payout or reward mechanics</td>
<td>No reward mechanism exists and the legal position is unknown</td>
<td>An owner decision plus a legal opinion</td><td><span class="badge unv">UNVERIFIED: none found</span></td></tr>
<tr><td>F-08</td><td>Whether a strategy is profitable</td>
<td>Cannot be tested without F-01</td><td>Graded results against prices</td><td><span class="badge unv">UNVERIFIED: none found</span></td></tr>
<tr><td>F-09</td><td>Points cost of a lineup change</td>
<td>Needs several seasons of results joined to injury reports</td>
<td>Historical capture plus a fitted model</td><td><span class="badge unv">UNVERIFIED: none found</span></td></tr>
<tr><td>F-10</td><td>Injury designations with no game status</td>
<td>The club had not published a designation at capture time</td>
<td>Recapture after the club posts its final report</td>
<td><a href="https://www.nfl.com/injuries/league/2026/reg10">nfl.com/injuries</a></td></tr>
</tbody></table>

<h3>Model caveats that must not be quoted without context</h3>
<ul>
<li>The model is fitted on {m['inputs']['games']} games from a single season. Ratings regress
heavily and the early weeks were fitted on very few games.</li>
<li>Home-field advantage is measured as {m['home_field_points']:+.2f} points on this sample. That is
smaller than the long-run convention, which is itself a finding worth review rather than a
correction to be applied.</li>
<li>No injury adjustment is applied to the model. The deficiency page is diagnostic, not an input.</li>
<li>No neutral-site adjustment is applied. If a game is played outside a club's home stadium the
home-field term is still applied unchanged.</li>
</ul>

<h3>Data irregularities observed during capture</h3>
<ul>
<li>NFL.com renders schedule scores client-side; the captured HTML shows "Hidden Score" in the
score widgets. The visible score lines in the page text were used, and they reconcile exactly to
the standings, which is the evidence they were read correctly.</li>
<li>An earlier session reported every club depth-chart URL as 404. On the capture date used here,
31 of 32 returned a parsable chart. Both observations are recorded; neither is deleted.</li>
<li>Injury-report row counts differ between sessions because they captured at different times.
Only this build's single capture is used on this site.</li>
</ul>
"""


def archive(data: dict) -> str:
    return """
<h2>Archive of earlier sessions</h2>
<p class="lede">Earlier sessions built separate sites in this repository. Nothing here was deleted
or rewritten. These links are kept so the history stays reviewable — but each site uses its own
capture, its own assumptions and its own counts, so they will not agree with this desk in places.</p>
<table>
<thead><tr><th>Site</th><th>Path</th><th>What it contains</th><th>Status</th></tr></thead>
<tbody>
<tr><td>Verified-data dashboard</td><td><a href="../dashboard/index.html">/dashboard/</a></td>
<td>18 pages: standings, injuries, depth, own lines, gates, correlations</td>
<td>Archived — differs from this desk in capture time and counts</td></tr>
<tr><td>Lines and strategy lab</td><td><a href="../x3lab/index.html">/x3lab/</a></td>
<td>Model v0.1 lines, luck analysis, validation gates G-0…G-8</td>
<td>Archived — its model used assumed parameters</td></tr>
<tr><td>Extended research tree</td><td><a href="../docs/pages/executive-summary.html">/docs/pages/</a></td>
<td>Research notes, requirements, correlation research, leaderboard design</td>
<td>Archived</td></tr>
<tr><td>Source-first research site</td><td><a href="../lab/index.html">/lab/</a></td>
<td>Hypotheses, gate definitions, open questions, suggestions</td>
<td>Archived</td></tr>
<tr><td>Root category pages</td><td><a href="../executive-summary.html">/executive-summary.html</a></td>
<td>Standalone pages from an earlier session: lines, leaderboard, injuries, flagged</td>
<td>Archived</td></tr>
<tr><td>Legacy data site</td><td><a href="../docs/index.html">/docs/</a></td>
<td>Generated dashboard with archived CSVs</td><td>Archived</td></tr>
</tbody></table>
<div class="notice"><b>Which one to use.</b> This desk. It is the only site whose data is
reconciled against a second official page and whose build fails when verification fails.</div>
"""
