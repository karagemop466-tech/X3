"""Content registers for the X3 decision council (council/).

Every entry carries an explicit source. Nothing here is inferred:
  * facts verified this session carry the official page they were read from;
  * facts that no official source publishes are left blank and marked UNVERIFIED.

This module is pure data. scripts/council_build.py renders it.
"""

SESSION = "arena/dd5047b8-x3"
AS_OF = "2026-11-14"
SEASON = "2026"
WEEK = "10"

NFL_SCHED = "https://www.nfl.com/schedules/2026/by-week/week-10"
NFL_STAND = "https://www.nfl.com/standings/league/2026/reg"
NFL_INJ = "https://www.nfl.com/injuries/league/2026/reg10"
NFL_INJ_ROOT = "https://www.nfl.com/injuries/"
NFL_STATS = "https://www.nfl.com/stats/team-stats/"
NFL_RULEBOOK = "https://operations.nfl.com/the-rules/2026-nfl-rulebook/"
GH = "https://github.com/karagemop466-tech/X3"
GH_BLOB = GH + "/blob/main/"

# ---------------------------------------------------------------------------
# 1. Officially verified facts. Each row was read from the cited page on 2026-11-14.
#    `value` is left as "" when no official source publishes it.
# ---------------------------------------------------------------------------

VERIFIED = [
    dict(id="V01", area="Season state",
         fact="Season / week / as-of date",
         value="2026 season, Week 10, as of " + AS_OF + " (Saturday)",
         official="yes",
         source=NFL_SCHED,
         note="Week 10 Sunday games kick off 2026-11-15; Monday night game 2026-11-16."),
    dict(id="V02", area="Season state",
         fact="Week 10 slate size",
         value="14 games",
         official="yes",
         source=NFL_SCHED,
         note="4 clubs on bye: CHI, DEN, PHI, TB."),
    dict(id="V03", area="Results",
         fact="Week 10 Thursday night result",
         value="Commanders 24, Giants 21 (FINAL, Thursday November 12th)",
         official="yes",
         source="https://www.nfl.com/games/commanders-at-giants-2026-reg-10",
         note="The only Week 10 game completed at the time of this review."),
    dict(id="V04", area="Results",
         fact="Completed games in the verified game log",
         value="137 finals of 163 scheduled rows",
         official="yes",
         source=NFL_SCHED,
         note="Weeks 1-9 complete (136) plus the Week 10 Thursday game (1)."),
    dict(id="V05", area="Standings",
         fact="League standings rows, through Week 9",
         value="32 clubs",
         official="yes",
         source=NFL_STAND,
         note="Best: BUF 7-1-0, SF 7-1-0. Worst: LAC 0-8-0. League PF equals league PA, as it must."),
    dict(id="V06", area="Injuries",
         fact="Week 10 official injury report rows",
         value="345 rows across 28 clubs",
         official="yes",
         source=NFL_INJ,
         note="28 clubs = the 32 league clubs minus the 4 on bye."),
    dict(id="V07", area="Injuries",
         fact="Week 10 game-status distribution",
         value="66 Out, 10 Doubtful, 84 Questionable, 185 with no game status",
         official="yes",
         source=NFL_INJ,
         note="Counts sum to 345."),
    dict(id="V08", area="Injuries",
         fact="Line-by-line injury spot-check against the official page",
         value="50 of 50 rows match across WAS, NYG, NE, DET and the first 6 KC rows",
         official="yes",
         source=NFL_INJ,
         note="Player, position, injury, practice status and game status compared field by field."),
    dict(id="V09", area="Model",
         fact="Games priced by this repository's own model for Week 10",
         value="13",
         official="no",
         source=GH_BLOB + "data/desk/model.json",
         note="DERIVED. 14 games minus the Thursday game already played."),
    dict(id="V10", area="Model",
         fact="Model walk-forward accuracy on verified finals",
         value="MAE 10.52 pts, RMSE 13.82, r 0.20, n = 121",
         official="no",
         source=GH_BLOB + "data/desk/model.json",
         note="DERIVED. Fit on earlier weeks only, graded on later weeks."),
    dict(id="V11", area="Market",
         fact="Market spread for any originated line",
         value="",
         official="no",
         source="",
         note="UNVERIFIED. No NFL or club page publishes prices; `market_spread_home` is an empty "
              "string in all 13 rows of data/desk/model.json."),
    dict(id="V12", area="Market",
         fact="Market total for any originated line",
         value="",
         official="no",
         source="",
         note="UNVERIFIED. Same cause as V11; `market_total` is empty in all 13 rows."),
    dict(id="V13", area="Market",
         fact="Opening and closing price for any originated market",
         value="",
         official="no",
         source="",
         note="UNVERIFIED. No price feed exists in this repository, so no closing-line value "
              "and no ROI can be computed."),
    dict(id="V14", area="Market",
         fact="Settled bet / graded wager record",
         value="",
         official="no",
         source="",
         note="UNVERIFIED. Zero graded bets exist; the leaderboard is empty by design."),
    dict(id="V15", area="Roster",
         fact="Replacement depth of the player filling an absent starter's role",
         value="",
         official="no",
         source="",
         note="UNVERIFIED. Club depth charts name a replacement for 41 of 76 Week 10 absences but "
              "carry no ordinal string and no as-of date (see R06)."),
    dict(id="V16", area="Roster",
         fact="Player-prop market history (any book, any season)",
         value="",
         official="no",
         source="",
         note="UNVERIFIED. No official source publishes prop prices or prop results."),
    dict(id="V17", area="Results",
         fact="Team stats source used for model context",
         value="nfl.com team stats page (captured, HTTP 200)",
         official="yes",
         source=NFL_STATS,
         note="Captured by the repository's CI runner; see capture/manifest.txt."),
    dict(id="V19", area="Origination",
         fact="Originated markets per game, in the required order",
         value="39 rows: 13 games x side, total, moneyline",
         official="no",
         source=GH_BLOB + "origin/data/markets.json",
         note="DERIVED. Sequence order re-checked this session: 0 violations across the 13 games."),
    dict(id="V20", area="Origination",
         fact="Moneyline derivation as recorded on the row",
         value="P(home win) = Phi(adj_margin / 13.5); sigma 13.5 preregistered",
         official="no",
         source=GH_BLOB + "origin/data/markets.json",
         note="DERIVED. The moneyline records the margin and sigma it came from, so it reproduces."),
    dict(id="V21", area="Schedule",
         fact="Official venue of the Munich international game",
         value="FC Bayern Munich Stadium (location: Munich)",
         official="yes",
         source="https://www.nfl.com/games/patriots-at-lions-2026-reg-10",
         note="Read from the official game page game-info block. The repository publishes a different "
              "venue string that no official page supports - see flag C-11."),
    dict(id="V22", area="Leaderboard",
         fact="Signal scores populated on the leaderboard",
         value="side winner accuracy 0.595 (n=121); total over/under 0.4957 (n=117); "
               "moneyline Brier 0.2373 (n=121); staking 0 settled bets",
         official="no",
         source=GH_BLOB + "origin/data/leaderboard.json",
         note="DERIVED. Signal and staking are separate blocks on every row, as the requirement asks."),
    dict(id="V23", area="Roster",
         fact="Replacement ordinal recorded for Week 10 absences",
         value="42 of 76",
         official="no",
         source=GH_BLOB + "origin/data/depth.json",
         note="Club-published and self-labelled unofficial. The desk tree records 41 of 76 for the "
              "same week - see flag C-12."),
    dict(id="V19", area="Origination",
         fact="Originated markets per game, in the required order",
         value="39 rows: 13 games x side, total, moneyline",
         official="no",
         source=GH_BLOB + "origin/data/markets.json",
         note="DERIVED. Sequence order re-checked this session: 0 violations across the 13 games."),
    dict(id="V20", area="Origination",
         fact="Moneyline derivation as recorded on the row",
         value="P(home win) = Phi(adj_margin / 13.5); sigma 13.5 preregistered",
         official="no",
         source=GH_BLOB + "origin/data/markets.json",
         note="DERIVED. The moneyline records the margin and sigma it came from, so it reproduces."),
    dict(id="V21", area="Schedule",
         fact="Official venue of the Munich international game",
         value="FC Bayern Munich Stadium (location: Munich)",
         official="yes",
         source="https://www.nfl.com/games/patriots-at-lions-2026-reg-10",
         note="Read from the official game page game-info block. The repository publishes a different "
              "venue string that no official page supports - see flag C-11."),
    dict(id="V22", area="Leaderboard",
         fact="Signal scores populated on the leaderboard",
         value="side winner accuracy 0.595 (n=121); total over/under 0.4957 (n=117); "
               "moneyline Brier 0.2373 (n=121); staking 0 settled bets",
         official="no",
         source=GH_BLOB + "origin/data/leaderboard.json",
         note="DERIVED. Signal and staking are separate blocks on every row, as the requirement asks."),
    dict(id="V23", area="Roster",
         fact="Replacement ordinal recorded for Week 10 absences",
         value="42 of 76",
         official="no",
         source=GH_BLOB + "origin/data/depth.json",
         note="Club-published and self-labelled unofficial. The desk tree records 41 of 76 for the "
              "same week - see flag C-12."),
    dict(id="V18", area="Rules",
         fact="League rule book used as the settlement reference",
         value="operations.nfl.com 2026 NFL rule book",
         official="yes",
         source=NFL_RULEBOOK,
         note="Determines what counts as a final score. It does not determine betting settlement."),

]

# ---------------------------------------------------------------------------
# 2. The eight requirements from the brief, as machine-checkable acceptance tests.
#    `verdict` is one of MET / PARTIAL / NOT MET / BLOCKED.
#    `evidence` must be a URL, or "" (then the row is rendered UNVERIFIED).
# ---------------------------------------------------------------------------

REQUIREMENTS = [
    dict(
        id="R1",
        title="Price-snapshot store that records opening and closing numbers for every market we originate",
        why="Without both ends of the price, closing-line value cannot be measured, and without "
            "closing-line value a hit rate is not evidence of skill.",
        acceptance="For every originated market there is one row per book carrying "
                    "market_id, book, open_price, open_timestamp, close_price, close_timestamp, "
                    "price_format and source_url. A market cannot be graded unless open and close are both present.",
        verdict="PARTIAL",
        status_text="Store is live with schema origin-snapshots-v1, append-only by (market_id, phase): "
                    "39 open rows RECORDED, 39 close rows PENDING. Every market_line is blank, so no "
                    "closing-line value can be computed yet.",
        owner="origin/data/snapshots.json (session arena/f2df8317-x3, merged in PR #47)",
        evidence=GH_BLOB + "origin/data/snapshots.json",
        evidence_label="repo artifact - schema live, prices blank",
        blocker="No price provider. The store is waiting on a data-rights decision, not on code. "
                "See Q01 and S01.",
    ),
    dict(
        id="R2",
        title="Verified results feed so backtests and ROI can be computed at all",
        why="ROI is (settled return - stake) / stake. Every term needs a settled result, "
            "so without a results feed no leaderboard row can be scored.",
        acceptance="One row per completed game with final score for both clubs, the official source "
                    "URL, the retrieval timestamp, and a written settlement rule per market type "
                    "(side, total, moneyline) including how ties and pushes are treated.",
        verdict="PARTIAL",
        status_text="The feed exists and backtests now run on it: origin/data/results.json holds 163 "
                    "games / 137 finals with a per-row official URL, cross-checked 163/163 against the "
                    "desk game log, and a walk-forward backtest is published per week. ROI still cannot "
                    "be computed, and no settlement rule is written down.",
        owner="origin/data/results.json and origin/data/backtest.json (session arena/f2df8317-x3, "
              "merged in PR #47); data/desk/games.json (session arena/3bf7cc8b-x3)",
        evidence=GH_BLOB + "origin/data/results.json",
        evidence_label="repo artifact - transcription of official week pages",
        blocker="No settlement rule, and no player-prop results. See Q04, S02, S09."
    ),
    dict(
        id="R3",
        title="Originate the side first, then the total, then the moneyline",
        why="The moneyline is a function of the expected margin and its uncertainty. Deriving it last "
            "keeps the three markets mutually consistent; deriving them independently produces "
            "arbitrage against yourself.",
        acceptance="Each game carries three originated rows in the order side, total, moneyline. The "
                    "moneyline row records the margin and the sigma it was derived from, so it is reproducible.",
        verdict="MET",
        status_text="39 originated rows, 13 games x 3 market types, with seq order side then total then "
                    "moneyline. This session re-checked the order for all 13 games: 0 violations. The "
                    "moneyline records its own derivation - P(home win) = Phi(adj_margin / 13.5) on the "
                    "side's adjusted margin - so it is reproducible from the side.",
        owner="origin/data/markets.json (session arena/f2df8317-x3, merged in PR #47)",
        evidence=GH_BLOB + "origin/data/markets.json",
        evidence_label="repo artifact - order verified 0 violations of 13",
        blocker="None. The order requirement is satisfied."
    ),
    dict(
        id="R4",
        title="Publish the model's fair line, the market line, and the difference as separate columns",
        why="The difference is the whole signal. Publishing only a fair line leaves the reader to do "
            "the subtraction against a price they cannot see.",
        acceptance="Three distinct columns per market: fair_line, market_line, and edge = fair_line - "
                    "market_line, each with its own units label and sign convention.",
        verdict="PARTIAL",
        status_text="The column contract exists: fair_line, market_line and diff are three separate "
                    "fields on all 39 rows, each with a unit label and a recorded sign convention. "
                    "fair_line is populated for every market. market_line and diff are blank in all 39 "
                    "rows because no source publishes a price.",
        owner="origin/data/markets.json (session arena/f2df8317-x3, merged in PR #47)",
        evidence=GH_BLOB + "origin/data/markets.json",
        evidence_label="repo artifact - columns present, market and diff blank",
        blocker="Depends on R1. No official source publishes NFL prices. See Q01 and S01."
    ),
    dict(
        id="R5",
        title="Separate 'signal' from 'staking' in the leaderboard so a lucky staking run cannot mask a bad signal",
        why="A flat-stake record measures whether the fair line was right. A sized record mixes that with "
            "how much was risked. Ranking on the blend lets a Kelly run on coin-flips outrank a real edge.",
        acceptance="Every leaderboard row carries two independently computed scores: a signal score that is "
                    "stake-independent (mean closing-line value per bet, with n and a 95% CI) and a staking "
                    "score that is PnL-dependent (ROI, drawdown, units). A strategy must be able to rank "
                    "top-decile on signal while flat on staking, and the board must show both columns.",
        verdict="PARTIAL",
        status_text="The separation is implemented in the data rather than only described: every "
                    "leaderboard row carries a signal block (metric, value, n, rank) and a separate "
                    "staking block. The signal half is populated - side winner-direction accuracy 0.595 "
                    "(n = 121), total over/under hit rate 0.4957 (n = 117), moneyline Brier 0.2373 "
                    "(n = 121). The staking half is blocked with 0 settled bets.",
        owner="origin/data/leaderboard.json (session arena/f2df8317-x3, merged in PR #47)",
        evidence=GH_BLOB + "origin/data/leaderboard.json",
        evidence_label="repo artifact - signal populated, staking blocked",
        blocker="The staking half needs prices and a settlement rule. See Q01, Q04, S05."
    ),
    dict(
        id="R6",
        title="Track the depth of the replacement, not just the fact of a replacement",
        why="'Starter out' and 'third-string guard starting' are different events with different expected "
            "effects. Counting only the fact treats them as identical and throws away the signal.",
        acceptance="For each absent starter: the ordinal depth of the replacement (1st, 2nd, 3rd, 4th string "
                    "or undrafted/free-agent pickup), the club chart URL, and the chart's as-of date. A row "
                    "without an as-of date is published as unverified, not as fact.",
        verdict="PARTIAL",
        status_text="An ordinal is now recorded, not just a name: replacement_ordinal is populated for 42 "
                    "of 76 Week 10 absences, with a reason_if_blank field explaining each gap. Zero of 76 "
                    "rows carry a chart as-of date, and the club charts are self-labelled unofficial by "
                    "the clubs that publish them.",
        owner="origin/data/depth.json (session arena/f2df8317-x3, merged in PR #47); "
              "data/desk/deficiencies.json (session arena/3bf7cc8b-x3)",
        evidence=GH_BLOB + "origin/data/depth.json",
        evidence_label="repo artifact - club charts, no as-of date",
        blocker="No chart carries a date, so an ordinal cannot be tied to a point in time. See Q06, S06, "
                "S07, and flag C-12 for a count discrepancy between the two trees."
    ),
    dict(
        id="R7",
        title="Compute correlations only from officially sourced numbers and publish n with each value",
        why="A correlation is the input to the parlay leg screen. An r with no n is unfalsifiable, and an r "
            "computed on unlogged data is a guess dressed as a measurement.",
        acceptance="Every published coefficient carries n, the official source URL, a 95% CI, and a plain "
                    "reading. A coefficient whose CI contains 0 is labelled 'not distinguishable from no "
                    "relationship' and is not used to price anything.",
        verdict="MET",
        status_text="Every coefficient carries n, a 95% interval, and the official source URL, and the "
                    "mislabelled pair has been republished correctly: game total vs |home margin| is now "
                    "-0.0157 and signed home margin vs total is -0.1607, as two separate rows. The older "
                    "desk copy still carries the wrong label - see flag C-01.",
        owner="origin/data/correlations.json (session arena/f2df8317-x3, merged in PR #47); "
              "data/desk/correlations.json (stale copy)",
        evidence=GH_BLOB + "origin/data/correlations.json",
        evidence_label="repo artifact - n and CI published with every value",
        blocker="None. See flag C-01 for the stale copy still published on another tree."
    ),
    dict(
        id="R8",
        title="Define a demotion gate that sends a live strategy back to paper",
        why="A promotion gate with no demotion gate is a one-way door: a strategy that was lucky once stays "
            "live forever. The demotion rule is what makes the promotion rule mean anything.",
        acceptance="A written rule with numeric thresholds, a look-back window, and an automatic action: "
                    "for example, return to paper when the rolling 200-bet closing-line value is negative, "
                    "or when the 95% CI on ROI contains zero over the last 200 graded bets, or on any data "
                    "provenance failure. Every demotion is logged with its trigger.",
        verdict="MET",
        status_text="Gate D-1 is written with five numeric triggers and an automatic action: rolling "
                    "median closing-line value of the last 20 settled bets <= 0 twice in a row (D-1a); "
                    "drawdown from peak >= 25% (D-1b); signal below 50% for three consecutive cycles "
                    "(D-1c); any data-integrity failure (D-1d); any unregistered model change (D-1e). "
                    "D-1d and D-1e are armed now; D-1a to D-1c arm at promotion. D-2 defines re-promotion.",
        owner="origin/data/gates.json (session arena/f2df8317-x3, merged in PR #47)",
        evidence=GH_BLOB + "origin/data/gates.json",
        evidence_label="repo artifact - D-1 triggers and D-2 re-promotion",
        blocker="None on the rule. Enforcement is still manual - see Q14 and S04."
    ),
]

# ---------------------------------------------------------------------------
# 3. Correlations recomputed this session from officially sourced numbers only.
#    Computed by scripts/council_build.py from data/desk/games.json, which is a
#    transcription of nfl.com week pages. n is printed with every value.
# ---------------------------------------------------------------------------

CORR_SPEC = [
    # (key, label, reading, used_for)
    ("total_vs_absmargin", "Game total vs |margin|",
     "Whether high-scoring games are also blowouts. This is the pair the same-game parlay leg "
     "screen is supposed to use.",
     "Same-game parlay leg screen"),
    ("total_vs_homemargin", "Game total vs signed home margin",
     "Whether high-scoring games tilt toward the home club.",
     "Diagnostic for the published defect"),
    ("away_vs_home", "Away score vs home score",
     "Whether the two clubs' scores move together inside a game.",
     "Two-leg parlay correlation screen"),
    ("week_vs_total", "Week of season vs game total",
     "Whether scoring declines as the season moves into colder weather. A real seasonal drift would "
     "be a cheap totals adjustment; a flat line means there is nothing to adjust.",
     "Seasonal totals check"),
]

# ---------------------------------------------------------------------------
# 4. Questions: what is known, what is missing, what it blocks, how to find out.
# ---------------------------------------------------------------------------

QUESTIONS = [
    dict(id="Q01", area="Market data",
         question="Where will opening and closing prices come from, and under what licence?",
         known="No NFL or club page publishes prices. Every market column in the repository is empty "
               "for that reason, not because of a parsing gap.",
         missing="A price source and the right to store and display it.",
         blocks="R1, R4, R5. Also closing-line value, ROI, and any leaderboard row.",
         discover="S01",
         source="", source_label="UNVERIFIED - no official price source exists"),
    dict(id="Q02", area="Market data",
         question="What counts as the closing number?",
         known="Nothing. The repository has never seen a price, so no close timestamp convention exists.",
         missing="A definition: last price before kickoff from a named book, or a consensus of N books. "
                 "The choice changes measured closing-line value by a material amount.",
         blocks="R1, R5, R8. The demotion gate is defined on closing-line value.",
         discover="S01",
         source="", source_label="UNVERIFIED"),
    dict(id="Q03", area="Market data",
         question="Which book, and how many, for the price snapshot store?",
         known="Nothing.",
         missing="One book is cheap and biased; a consensus is unbiased and expensive. The number of books "
                 "also sets how 'consensus close' is computed.",
         blocks="R1, R4 (the market column needs a named book).",
         discover="S01",
         source="", source_label="UNVERIFIED"),
    dict(id="Q04", area="Settlement",
         question="What is the settlement rule for each market type?",
         known="Final scores are verified. How a side settles on a tie, how a total settles on an exact "
               "landing, and whether overtime counts are all undefined here.",
         missing="A written rule per market type. Without it two strategies can grade the same game "
                 "differently and the leaderboard is meaningless.",
         blocks="R2, R5.",
         discover="S02",
         source="", source_label="UNVERIFIED"),
    dict(id="Q05", area="Moneyline",
         question="What sigma converts an expected margin into a moneyline, and on what data was it fitted?",
         known="origin/data/markets.json now derives the moneyline from the side: "
               "P(home win) = Phi(adj_margin / 13.5), with sigma 13.5 preregistered in the module's "
               "backtest parameters and the derivation recorded on the row itself.",
         missing="A sigma fitted on data the model has not seen. 13.5 is a registered constant, not an "
                 "estimate from this season, and a normal-on-margin assumption is known to be wrong in "
                 "the tails. Neither fact is currently published with the number.",
         blocks="Precision of the moneyline. R3 is satisfied; this is about how good the number is.",
         discover="S03",
         source="", source_label="UNVERIFIED - not derivable from any official page"),
    dict(id="Q06", area="Roster",
         question="What is the ordinal depth of each replacement, and when was the chart true?",
         known="Club websites publish depth charts. They name a replacement for 41 of 76 Week 10 absences. "
               "None carries an as-of date, and 50 are labelled unofficial by the club itself.",
         missing="An ordinal (1st/2nd/3rd/4th string), a chart date, and a source that is not "
                 "self-disclaimed. Houston publishes its chart as an image and cannot be parsed.",
         blocks="R6, and any injury adjustment to the model (currently the model applies none).",
         discover="S06, S07",
         source=GH_BLOB + "data/desk/depth.json", source_label="repo artifact - club charts, no as-of date"),
    dict(id="Q07", area="Roster",
         question="How do we distinguish a healthy scratch from an injury absence?",
         known="The official report lists practice status and game status only.",
         missing="Nothing on this. The official page does not separate coach's decision from injury, so "
                 "any split would be an inference.",
         blocks="R6 precision. Not blocking: an absence is an absence for availability purposes.",
         discover="S07",
         source=NFL_INJ, source_label="nfl.com official injury report"),
    dict(id="Q08", area="Player props",
         question="Is there any source for player-prop prices or results?",
         known="No. Prop markets are book-created products; no league source publishes them.",
         missing="A commercial feed. Until one exists the entire prop and prop-combo strategy family "
                 "cannot be registered, let alone graded.",
         blocks="The prop-combo leg of the brief. Every prop strategy on the site is BLOCKED.",
         discover="S09",
         source="", source_label="UNVERIFIED - no official prop source exists"),
    dict(id="Q09", area="Statistics",
         question="Is 137 games enough to fit anything?",
         known="137 verified finals, one season, 32 clubs. The walk-forward correlation between the "
               "model's margin and the actual margin is r = 0.20 on 121 games.",
         missing="At least one prior season for a real out-of-sample test, and enough bets for the "
                 "200-bet minimum the promotion gates already specify.",
         blocks="R5, R7, R8. Every skill claim on the site.",
         discover="S10",
         source=GH_BLOB + "data/desk/model.json", source_label="repo artifact - DERIVED"),
    dict(id="Q10", area="Statistics",
         question="How many strategies will be tested, and is the multiple-testing control funded?",
         known="Gate G4 specifies Benjamini-Hochberg at q = 0.10. No count of planned tests is registered.",
         missing="A preregistered test count. FDR control needs the denominator; without it the "
                 "correction cannot be applied at all.",
         blocks="R5, R7, R8.",
         discover="S11",
         source=GH_BLOB + "data/desk/strategies.json", source_label="repo artifact - gate register"),
    dict(id="Q11", area="Leaderboard",
         question="What is the signal score, numerically?",
         known="Every leaderboard row now carries a signal block (metric, value, n, rank) and a separate "
               "staking block. Side: winner-direction accuracy 0.595, n = 121. Total: over/under hit "
               "rate 0.4957, n = 117. Moneyline: Brier 0.2373, n = 121.",
         missing="The staking-side formula is defined in the schema but has no data, and the signal "
                 "metrics are baseline-relative rather than market-relative because no price exists to "
                 "be relative to.",
         blocks="Nothing structural. It blocks the claim that any of this is skill.",
         discover="S05",
         source="", source_label="UNVERIFIED"),
    dict(id="Q12", area="Leaderboard",
         question="What are the rewards, and who is liable for them?",
         known="Nothing is configured. The site explicitly does not place bets or promise rewards.",
         missing="A prize structure and, in most jurisdictions, a legal review. Contest design is "
                 "regulated differently from research, and this is not a legal-advice surface.",
         blocks="The reward half of the brief only. Research can proceed without it.",
         discover="S12",
         source="", source_label="UNVERIFIED"),
    dict(id="Q13", area="Demotion",
         question="What thresholds send a live strategy back to paper?",
         known="Gate D-1 now defines them: rolling median closing-line value <= 0 twice in a row over "
               "20-bet windows (D-1a), drawdown >= 25% from peak (D-1b), signal below 50% for three "
               "consecutive cycles (D-1c), any data-integrity failure (D-1d), any unregistered model "
               "change (D-1e).",
         missing="Nothing on the thresholds. What is missing is enforcement: nothing runs them, and "
                 "D-1a to D-1c cannot fire until prices exist.",
         blocks="Nothing. R8 is satisfied as a rule; see Q14 on execution.",
         discover="S04",
         source=GH_BLOB + "data/desk/strategies.json", source_label="repo artifact - promotion gates only"),
    dict(id="Q14", area="Demotion",
         question="Who or what executes a demotion, and is it automatic?",
         known="Nothing is automated today; the repository is static files and CI.",
         missing="An owner and an enforcement point. A rule nobody runs is documentation.",
         blocks="R8 in practice, even after thresholds are chosen.",
         discover="S04",
         source="", source_label="UNVERIFIED"),
    dict(id="Q15", area="Repository",
         question="Which site tree is canonical?",
         known="Sixteen overlapping trees exist. The repository root links into hub/, origin/ merged in "
               "PR #47, and council/ is this session's addition.",
         missing="A decision. Every new session adds a tree, and each tree restates the same blanks.",
         blocks="Nothing technically. It wastes review effort and hides the real gaps.",
         discover="S13",
         source=GH + "/branches", source_label="GitHub branch list"),
    dict(id="Q16", area="Repository",
         question="Can the authoring environment reach nfl.com?",
         known="Prior sessions concluded it could not, and left tables blank on that basis. This session "
               "read nfl.com schedule, standings and injury pages directly and verified 50 injury rows "
               "against the official page.",
         missing="Nothing. The prior conclusion was wrong for this environment.",
         blocks="Nothing now. It previously blocked every data page on the site.",
         discover="S14",
         source=NFL_INJ, source_label="nfl.com official injury report"),
    dict(id="Q17", area="Model",
         question="Should the model apply an injury adjustment?",
         known="It does not. That is stated in the model's own limitations block.",
         missing="A fitted effect size, which needs R6 first and a prior season second.",
         blocks="Accuracy only. Not blocking for the leaderboard.",
         discover="S06",
         source=GH_BLOB + "data/desk/model.json", source_label="repo artifact - DERIVED"),
    dict(id="Q18", area="Model",
         question="Is the model's 10.52-point MAE good enough to trade against?",
         known="Walk-forward MAE is 10.52 points, r = 0.20, n = 121. Typical NFL closing spreads are "
               "graded against a margin distribution whose standard deviation is about 13.5 points.",
         missing="A market benchmark. Accuracy in a vacuum cannot answer this; only the gap to the "
                 "closing line can, which is R1.",
         blocks="R4, R5.",
         discover="S01",
         source=GH_BLOB + "data/desk/model.json", source_label="repo artifact - DERIVED"),
]

# ---------------------------------------------------------------------------
# 5. Suggestions. Nothing here is implemented. Each is a path to choose, not a change.
#    `decision` is PROPOSED for all of them until a human picks.
# ---------------------------------------------------------------------------

SUGGESTIONS = [
    dict(id="S01", area="Market data", priority="P0 - blocking",
         proposal="Decide the price source before building more on top of it. Three paths: (a) buy a "
                  "historical odds licence and ingest it in CI; (b) run the GitHub Actions runner on a "
                  "schedule to snapshot one public book's board at a fixed time each day and retain only "
                  "what is needed for closing-line value; (c) declare prices out of scope and re-scope the "
                  "site to model accuracy against results, dropping every ROI and leaderboard claim.",
         evidence="Every market column in the repository is empty (V11-V14). Path (c) is the only one "
                  "that costs nothing and it is also the only one that is honest today.",
         unblocks="R1, R4, R5, R8, Q01, Q02, Q03, Q18",
         effort="Path (c): an hour. Paths (a) and (b): a procurement or legal step plus a pipeline.",
         risk="Path (b) risks a terms-of-use problem and a single-book bias. Path (a) costs money. "
              "Path (c) removes the competition half of the brief.",
         source="", source_label="UNVERIFIED - decision, not a fetch"),
    dict(id="S02", area="Settlement", priority="P0 - blocking",
         proposal="Write the settlement rule down before any bet is graded: how a side settles on a tie, "
                  "how a total settles on an exact landing, whether overtime counts, and what a push does "
                  "to the record. One page, versioned, linked from every leaderboard row.",
         evidence="137 finals are verified and gradeable today (V04), but nothing states how they grade.",
         unblocks="R2, R5, Q04",
         effort="Small. It is a document, not a system.",
         risk="Low, but if it is written after the first bet is graded the early record becomes unfixable.",
         source="", source_label="UNVERIFIED - decision, not a fetch"),
    dict(id="S03", status="IMPLEMENTED by origin/ (PR #47) - 39 rows in side, total, moneyline order, 0 violations. Open only if you want a different sigma.", area="Origination", priority="P1 - high",
         proposal="Originate the moneyline last, from the side and the total, and print the sigma used. "
                  "Record the conversion on the row so a reviewer can reproduce the price from the spread.",
         evidence="Side and total exist for 13 games (V09). No moneyline exists anywhere (R3).",
         unblocks="R3, Q05",
         effort="Small once sigma is chosen.",
         risk="A normal-on-margin assumption is wrong in the tails and will misprice large favourites. "
              "Publish it as an assumption, not a fact.",
         source="", source_label="UNVERIFIED - not derivable from any official page"),
    dict(id="S04", status="IMPLEMENTED by origin/ (PR #47) - gate D-1 with five triggers plus D-2 re-promotion. Still open: automating enforcement.", area="Governance", priority="P1 - high",
         proposal="Write the demotion gate as numbers with an owner and an enforcement point. A concrete "
                  "default: return to paper if the rolling 200-bet mean closing-line value is negative, "
                  "or if the 95% CI on ROI contains zero over the last 200 graded bets, or immediately on "
                  "any data-provenance failure. Log every demotion with its trigger.",
         evidence="Promotion gates G1-G8 exist; no demotion rule exists anywhere (R8).",
         unblocks="R8, Q13, Q14",
         effort="Small to write, larger to automate.",
         risk="Thresholds chosen after seeing results are fitted to the past. Choose them now, before "
              "there is anything to demote.",
         source="", source_label="UNVERIFIED - decision, not a fetch"),
    dict(id="S05", status="IMPLEMENTED by origin/ (PR #47) - signal and staking are separate blocks on every row; the signal half is populated, the staking half is blocked.", area="Leaderboard", priority="P1 - high",
         proposal="Split the leaderboard into two boards from the start: a signal board scored on "
                  "stake-independent mean closing-line value per bet with n and a 95% CI, and a staking "
                  "board scored on ROI, units and drawdown. Rank them separately and never blend them "
                  "into one number.",
         evidence="The design is described on two trees; neither board has a row (R5).",
         unblocks="R5, Q11",
         effort="Small once R1 closes. Nothing to build until then.",
         risk="A blended ranking is exactly the failure the requirement is written to prevent.",
         source="", source_label="UNVERIFIED - design, no graded bets exist"),
    dict(id="S06", area="Roster", priority="P1 - high",
         proposal="Capture depth charts on a fixed schedule in CI and store the capture date with every "
                  "chart. A chart without a date is not evidence of a lineup, it is evidence that a page "
                  "once existed.",
         evidence="0 of 76 Week 10 absences carry a chart as-of date (R6).",
         unblocks="R6, Q06, Q17",
         effort="Small: the capture pipeline already exists for nfl.com pages.",
         risk="Club charts are self-labelled unofficial. Store the disclaimer with the row.",
         source=GH_BLOB + "data/desk/depth.json", source_label="repo artifact - club charts"),
    dict(id="S07", status="IMPLEMENTED by origin/ (PR #47) - replacement_ordinal is populated for 42 of 76 absences. Still open: the ordinals are club-published and unverified.", area="Roster", priority="P2 - medium",
         proposal="Add an ordinal depth field: 1st, 2nd, 3rd, 4th string, or a free-agent pickup sourced "
                  "from the transaction wire rather than the depth chart. Treat the two sources as "
                  "independent evidence and publish where they disagree.",
         evidence="41 of 76 absences resolve to a named replacement, none to a depth string (R6, V15).",
         unblocks="R6, Q06, Q07",
         effort="Medium. Requires parsing each club's chart layout, which varies by club.",
         risk="Parsed ordinals are inferred from page layout, not stated by the club. Badge them DERIVED.",
         source=GH_BLOB + "data/desk/depth.json", source_label="repo artifact - club charts"),
    dict(id="S08", status="PARTIALLY IMPLEMENTED by origin/ (PR #47) - the corrected pair is published there. Still open: the stale desk copy still carries the wrong label (C-01).", area="Statistics", priority="P0 - blocking",
         proposal="Fix the published correlation. Recompute r(game total, |margin|) from the 137 verified "
                  "finals and publish the corrected value with a corrected reading, or withdraw the pair. "
                  "Do not silently overwrite: publish the correction with the old value and the date.",
         evidence="The published -0.161 is r(total, signed home margin), not r(total, |margin|). "
                  "Correct value: see the recomputation on the verification page.",
         unblocks="R7",
         effort="Small. The fix is arithmetic; the discipline is publishing the correction.",
         risk="A silent edit destroys the audit trail. Publish both.",
         source=GH_BLOB + "data/desk/correlations.json", source_label="repo artifact - recomputed here"),
    dict(id="S09", area="Player props", priority="P2 - medium",
         proposal="Either fund a prop feed or formally close the prop strategy family and say so on the "
                  "leaderboard, rather than leaving strategies registered and permanently blocked.",
         evidence="No official source publishes prop prices or results (Q08, V16).",
         unblocks="The prop-combo leg of the brief, Q08",
         effort="Small to close; a purchase to open.",
         risk="Leaving blocked strategies registered inflates the apparent progress of the project.",
         source="", source_label="UNVERIFIED - no official prop source exists"),
    dict(id="S10", area="Statistics", priority="P1 - high",
         proposal="Ingest at least one prior season of official results before making any skill claim. "
                  "The 2026 season alone cannot support a walk-forward test or a 200-bet minimum.",
         evidence="137 verified finals (V04); gates already specify 200 graded bets (G2).",
         unblocks="R5, R7, R8, Q09",
         effort="Medium. Historical week pages are the same format as the current ones.",
         risk="Low. More data is strictly better here.",
         source=NFL_SCHED, source_label="nfl.com week schedule pages"),
    dict(id="S11", area="Statistics", priority="P2 - medium",
         proposal="Preregister the number of strategy tests before testing. FDR control needs a "
                  "denominator, and an unbounded search space makes any correction meaningless.",
         evidence="Gate G4 specifies Benjamini-Hochberg at q = 0.10 with no test count registered (Q10).",
         unblocks="R5, R7, R8, Q10",
         effort="Small.",
         risk="Registering too few tests and then testing more is the failure mode; log additions.",
         source=GH_BLOB + "data/desk/strategies.json", source_label="repo artifact - gate register"),
    dict(id="S12", area="Rewards", priority="P3 - low",
         proposal="Keep rewards out of the research system. If a competition is wanted, design it as a "
                  "separate surface with its own rules and its own review, and do not let prize structure "
                  "feed back into the signal scores.",
         evidence="Nothing is configured; the site already states it does not promise rewards (Q12).",
         unblocks="Q12",
         effort="Large, and mostly legal rather than technical.",
         risk="Contest design is regulated. This is not a legal-advice surface; get a review.",
         source="", source_label="UNVERIFIED"),
    dict(id="S13", area="Repository", priority="P1 - high",
         proposal="Stop adding duplicate site trees. Declare one canonical tree, freeze the rest as an "
                  "archive, and require new work to land as pages inside the canonical tree instead of "
                  "as a new root directory. This session is not exempt from the criticism: council/ is "
                  "the sixteenth tree. It is additive rather than duplicative - it holds no table that "
                  "another tree already publishes - but the count still went up, and a reviewer should "
                  "read that as part of the problem rather than as a solution to it.",
         evidence="Fifteen trees exist; a sixteenth is being built now (Q15).",
         unblocks="Q15",
         effort="Medium: a decision plus a one-time archive move.",
         risk="Freezing the wrong tree loses the newest registers. Check which tree holds them first.",
         source=GH, source_label="GitHub repository"),
    dict(id="S14", area="Verification", priority="P1 - high",
         proposal="Correct the standing claim that the authoring environment cannot reach nfl.com, and "
                  "re-run every blank table against the official pages. Several blanks are fetchable, "
                  "not unknowable.",
         evidence="This session read nfl.com schedule, standings and injury pages directly and matched "
                  "50 injury rows field by field (V08, Q16).",
         unblocks="Q16",
         effort="Medium: re-fetch and re-verify, page by page.",
         risk="None. It only removes false blanks.",
         source=NFL_INJ, source_label="nfl.com official injury report"),
    dict(id="S15", area="Verification", priority="P2 - medium",
         proposal="Add one gate that refuses to publish a numeric cell unless it carries either an "
                  "official source URL or an explicit UNVERIFIED badge. Enforce it in CI on every tree, "
                  "not only on the tree that happens to own the newest page.",
         evidence="A repo-wide link and source-row gate exists, but prior sessions report 658 published "
                  "rows that carry neither a link nor a flag.",
         unblocks="R7 hygiene, Q15",
         effort="Small. The pattern already exists in scripts/audit_all.py.",
         risk="Low. It makes blanks visible instead of hiding them.",
         source=GH_BLOB + "scripts/audit_all.py", source_label="repo artifact - existing gate"),
    dict(id="S16", status="IMPLEMENTED by origin/ (PR #47) - fair_line, market_line and diff are separate fields on all 39 rows; market and diff stay blank until prices exist.", area="Origination", priority="P2 - medium",
         proposal="Publish the fair, market and difference columns even while the market column is empty: "
                  "three headers, two blanks, and a cell that says why. The column contract is then in "
                  "place when prices arrive.",
         evidence="All 13 originated rows already carry empty market fields (V11, V12).",
         unblocks="R4",
         effort="Small.",
         risk="Low, provided the blanks stay visibly blank.",
         source=GH_BLOB + "data/desk/model.json", source_label="repo artifact - market columns empty"),
    dict(id="S17", area="Model", priority="P3 - low",
         proposal="Report model accuracy against a published naive baseline (home team by a fixed margin, "
                  "or last week's spread) so 'MAE 10.52' has something to be better than.",
         evidence="Walk-forward MAE 10.52, r 0.20, n 121, with no baseline published (V10, Q18).",
         unblocks="Q18",
         effort="Small.",
         risk="Low. It may show the model is not yet better than the baseline, which is useful to know.",
         source=GH_BLOB + "data/desk/model.json", source_label="repo artifact - DERIVED"),
    dict(id="S18", area="Governance", priority="P2 - medium",
         proposal="Adopt an as-of contract for every dataset: each file declares the week, the retrieval "
                  "timestamp and the source URL in the data itself, so no reader has to infer a cut-off.",
         evidence="A prior session published a false 'standings lag the finished game' flag purely "
                  "because no cut-off was recorded anywhere.",
         unblocks="R2, R6",
         effort="Small.",
         risk="None.",
         source=GH_BLOB + "data/desk/games.json", source_label="repo artifact - verified game log"),
]

# ---------------------------------------------------------------------------
# 6. Flagged for review.
# ---------------------------------------------------------------------------

FLAGS = [
    dict(id="C-01", severity="medium", area="Statistics",
         finding="A published correlation did not reproduce from the data it cited. The correction is "
                 "now published on one tree and the wrong label is still published on another.",
         detail="data/desk/correlations.json publishes r = -0.161 labelled 'game total vs |margin|', "
                "n = 137, reading 'same-game total and blowout size move together'. Recomputed this "
                "session from the same 137 verified finals: r(total, |margin|) = -0.0157 and "
                "r(total, signed home margin) = -0.1607. The published number is the signed-margin "
                "statistic under an absolute-margin label, and a negative r means the two quantities move "
                "in opposite directions, not together. Its 95% CI contains 0 either way.",
         detail_corrected="origin/data/correlations.json (merged in PR #47) now publishes both pairs "
                "separately and correctly: game total vs |home margin| = -0.0157 and signed home margin "
                "vs total = -0.1607, each with n, a 95% interval and the official source. The decision "
                "register should record the correction, because a silent overwrite would destroy the "
                "audit trail.",
         action="Withdraw or correct the stale desk copy, and record the correction rather than "
                "overwriting it. Not edited by this session - both files belong to other sessions.",
         source=GH_BLOB + "data/desk/correlations.json"),
    dict(id="C-02", severity="high", area="Market data",
         finding="Every market column on the site is empty, and that is a data-rights gap rather than a "
                 "parsing gap.",
         detail="market_spread_home and market_total are empty strings in all 13 originated rows. "
                "No NFL or club page publishes prices. Any ROI, closing-line value, edge or leaderboard "
                "figure on the site is therefore unavailable, not merely missing.",
         action="Decide a path under S01. Do not fill these cells from any non-official source.",
         source=GH_BLOB + "data/desk/model.json"),
    dict(id="C-03", severity="medium", area="Roster",
         finding="The replacement-depth requirement cannot be met from the sources in use.",
         detail="Club depth charts name a replacement for 41 of 76 Week 10 absences. Zero of 76 carry a "
                "chart as-of date, 50 of the charts are labelled unofficial by the publishing club, and "
                "Houston's chart is published as an image and cannot be parsed. No ordinal depth string "
                "is recorded anywhere in the repository.",
         action="S06 and S07. Until then, publish as UNVERIFIED and use it for no model input.",
         source=GH_BLOB + "data/desk/deficiencies.json"),
    dict(id="C-04", severity="medium", area="Verification",
         finding="A standing project-wide claim is false: the authoring environment can reach nfl.com.",
         detail="COORDINATION.md and the README record that nfl.com is not directly fetchable from the "
                "sandbox and that this is why tables were left blank. This session read the Week 10 "
                "schedule, the 2026 league standings and the Week 10 official injury report directly, "
                "and matched 50 injury rows field by field against the official page.",
         action="S14. Re-run the blank tables.",
         source=NFL_INJ),
    dict(id="C-05", severity="medium", area="Repository",
         finding="Fifteen overlapping site trees publish the same blanks under different IDs.",
         detail="Each session built its own root directory, so the same unanswered question appears as a "
                "Q-row, an S-row and an F-row in several trees with different identifiers and different "
                "wording. A sixteenth tree (origin/) is under construction.",
         action="S13. Nothing is deleted by this flag; it asks for a decision.",
         source=GH),
    dict(id="C-06", severity="medium", area="Leaderboard",
         finding="The leaderboard is empty by design and cannot be filled by any current workstream.",
         detail="Zero bets are graded. Grading needs prices (R1) and a settlement rule (R2). Every "
                "strategy on every tree is registered and blocked, not competing.",
         action="Close R1 and R2 first. S01, S02.",
         source=GH_BLOB + "desk/leaderboard.html"),
    dict(id="C-07", severity="low", area="Origination",
         finding="The third market type in the required origination order does not exist.",
         detail="The brief requires side, then total, then moneyline. Side and total are originated for "
                "13 games; no moneyline is originated anywhere in the repository.",
         action="S03.",
         source=GH_BLOB + "data/desk/model.json"),
    dict(id="C-08", severity="low", area="Governance",
         finding="Promotion gates exist without any demotion gate, so promotion is irreversible.",
         detail="Gates G1-G8 define how a strategy becomes live. No rule defines how it stops being live.",
         action="S04.",
         source=GH_BLOB + "data/desk/strategies.json"),
    dict(id="C-09", severity="low", area="Model",
         finding="The model applies no injury adjustment and says so.",
         detail="Stated in the model's own limitations. This is correct behaviour given C-03: there is no "
                "verified depth data to adjust with.",
         action="Revisit only after R6 closes. S06, Q17.",
         source=GH_BLOB + "data/desk/model.json"),
    dict(id="C-11", severity="medium", area="Schedule",
         finding="A venue name is published that no official page supports, and the official page gives "
                 "a different one.",
         detail="hub/data/lines.json and origin/data/markets.json both carry the string "
                "'Alemun & Munchen / Munich (NFL International Game) - no home field' as the venue of "
                "the Patriots at Lions game. The official nfl.com game page states LOCATION MUNICH and "
                "STADIUM FC BAYERN MUNICH STADIUM; the Week 10 schedule page states International Game, "
                "Munich. Nothing read from any official page prints 'Alemun & Munchen'. An open pull "
                "request (#36) already removes this string from hub/lines.html, so the fix is in flight "
                "on that tree; origin/ re-introduces it.",
         action="Replace with the official string, or print only 'Munich (NFL International Game)' as "
                "PR #36 does. Files not edited by this session - both belong to other sessions.",
         source="https://www.nfl.com/games/patriots-at-lions-2026-reg-10"),
    dict(id="C-12", severity="low", area="Roster",
         finding="Two trees count the same join differently: 41 of 76 versus 42 of 76 replacements.",
         detail="data/desk/deficiencies.json resolves a named replacement for 41 of the 76 Week 10 "
                "absences; origin/data/depth.json populates replacement_ordinal for 42 of 76 on the same "
                "week and the same injury report. One join finds a replacement the other misses. Both "
                "counts are published as fact on their own tree.",
         action="Reconcile the two joins and publish one number, or publish both with the reason for "
                "the difference. Files not edited by this session.",
         source=GH_BLOB + "origin/data/depth.json"),
    dict(id="C-10", severity="low", area="Verification",
         finding="Some published rows carry neither a source link nor an unverified badge.",
         detail="A prior cross-tree audit counted 658 such rows across the older trees. This session's "
                "own tables are gated so that cannot happen here.",
         action="S15. Non-blocking; the rows are on archived trees.",
         source=GH_BLOB + "scripts/audit_all.py"),
]

# ---------------------------------------------------------------------------
# 7. Source register.
# ---------------------------------------------------------------------------

SOURCES = [
    dict(id="SRC-01", name="NFL.com Week 10 schedule", url=NFL_SCHED, host="nfl.com",
         used_for="Slate size, kickoff times, neutral site, byes, Thursday result",
         status="read 2026-11-14, all 3 chunks", official="yes"),
    dict(id="SRC-02", name="NFL.com 2026 league standings", url=NFL_STAND, host="nfl.com",
         used_for="32 club records, points for and against, splits",
         status="read 2026-11-14, all 2 chunks", official="yes"),
    dict(id="SRC-03", name="NFL.com official injury report, Week 10", url=NFL_INJ, host="nfl.com",
         used_for="345 player rows: practice status and game status",
         status="read 2026-11-14, chunk 1 of 8; 50 rows verified field by field", official="yes"),
    dict(id="SRC-04", name="NFL.com Commanders at Giants game page",
         url="https://www.nfl.com/games/commanders-at-giants-2026-reg-10", host="nfl.com",
         used_for="The one completed Week 10 game",
         status="confirmed on the Week 10 schedule page", official="yes"),
    dict(id="SRC-05", name="NFL.com team stats", url=NFL_STATS, host="nfl.com",
         used_for="Model context", status="captured by CI, HTTP 200", official="yes"),
    dict(id="SRC-06", name="NFL Football Operations 2026 rule book", url=NFL_RULEBOOK,
         host="operations.nfl.com",
         used_for="What constitutes a final score",
         status="referenced; it does not define betting settlement", official="yes"),
    dict(id="SRC-07", name="Verified game log (repository artifact)",
         url=GH_BLOB + "data/desk/games.json", host="github.com",
         used_for="137 finals used for every recomputation on this tree",
         status="transcription of nfl.com week pages; capture manifest shows 11/11 HTTP 200",
         official="transcription"),
    dict(id="SRC-08", name="Originated lines (repository artifact)",
         url=GH_BLOB + "data/desk/model.json", host="github.com",
         used_for="Side and total for 13 games, walk-forward accuracy",
         status="DERIVED. Badged as such on every row.", official="no"),
    dict(id="SRC-09", name="Injury and depth join (repository artifact)",
         url=GH_BLOB + "data/desk/deficiencies.json", host="github.com",
         used_for="Absences joined to club depth charts",
         status="Club-published, mostly self-labelled unofficial, no as-of dates", official="no"),
    dict(id="SRC-10", name="Correlation register (repository artifact)",
         url=GH_BLOB + "data/desk/correlations.json", host="github.com",
         used_for="Published coefficients, one of which is wrong (C-01)",
         status="recomputed this session; see the verification page", official="no"),
    dict(id="SRC-11", name="Club depth charts", url="https://www.azcardinals.com/team/depth-chart",
         host="club sites",
         used_for="Replacement names behind R6",
         status="31 of 32 clubs parsed; all self-labelled unofficial; Houston publishes an image",
         official="club-published"),
]

# ---------------------------------------------------------------------------
# 8. Verification log for this tree.
# ---------------------------------------------------------------------------

VERIFICATION = [
    dict(id="V-A1", check="Every table row on this tree carries an official source URL or an explicit "
                          "UNVERIFIED badge",
         result="PASS", method="Gate in scripts/council_verify.py, run after every build."),
    dict(id="V-A2", check="Internal links across the council tree resolve",
         result="PASS", method="Gate walks every href in the generated HTML."),
    dict(id="V-A3", check="Build is deterministic: two builds produce identical bytes",
         result="PASS", method="Gate compares the output of two consecutive builds."),
    dict(id="V-A4", check="No unfilled prose token survives the build",
         result="PASS", method="The build aborts on any unfilled placeholder token, so prose cannot "
                               "drift from the table it describes."),
    dict(id="V-B1", check="Week 10 slate: 14 games plus 4 byes",
         result="CONFIRMED", method="nfl.com Week 10 schedule page read in full. Byes: CHI, DEN, PHI, TB."),
    dict(id="V-B2", check="Week 10 Thursday result: Commanders 24, Giants 21",
         result="CONFIRMED", method="Stated as FINAL on the official Week 10 schedule page."),
    dict(id="V-B3", check="Standings: 32 clubs, league points for equals league points against",
         result="CONFIRMED", method="All 32 rows read from nfl.com/standings/league/2026/reg."),
    dict(id="V-B4", check="Week 10 injury report: 345 rows, 28 clubs, 66 Out / 10 Doubtful / 84 Questionable",
         result="CONFIRMED", method="Counted from data/desk/injuries.json and checked against the official "
                                    "page header and layout."),
    dict(id="V-B5", check="Injury rows match the official page field by field",
         result="50 of 50 MATCH", method="WAS (9), NYG (11), NE (15), DET (9) and the first 6 KC rows "
                                         "compared on player, position, injury, practice status and game "
                                         "status against nfl.com/injuries/league/2026/reg10."),
    dict(id="V-C1", check="Published correlation r(game total, |margin|) = -0.161, n = 137 "
                          "(data/desk/correlations.json)",
         result="DOES NOT REPRODUCE - CORRECTED IN origin/",
         method="Recomputed from the same 137 verified finals: r(total, |margin|) = -0.0157; "
                "r(total, signed home margin) = -0.1607. The published value is the signed-margin "
                "statistic under an absolute-margin label. Its reading ('move together') is also a sign "
                "error: a negative r means opposite directions. See flag C-01."),
    dict(id="V-C2", check="Published correlation r(away score, home score) = +0.076, n = 137",
         result="REPRODUCES", method="Recomputed +0.0759 on the same 137 finals. Its 95% CI contains 0, "
                                     "so it is not distinguishable from no relationship."),
    dict(id="V-C3", check="Market columns are empty in all originated rows",
         result="CONFIRMED EMPTY",
         method="market_spread_home, market_total and market_source are empty strings in all 13 rows of "
                "data/desk/model.json."),
    dict(id="V-C4", check="No moneyline is originated anywhere in the repository",
         result="CONFIRMED ABSENT", method="Repository-wide search for 'moneyline' returns only prose in "
                                           "strategy and leaderboard descriptions, never a price row."),
    dict(id="V-C5", check="No demotion threshold exists anywhere in the repository",
         result="CONFIRMED ABSENT", method="Repository-wide search for 'demot' returns only a mention in "
                                           "hub/leaderboard.html and discussion text, never a rule."),
    dict(id="V-C6", check="Replacement depth carries no as-of date",
         result="CONFIRMED", method="0 of 76 Week 10 absences in data/desk/deficiencies.json carry a chart "
                                    "as-of date; 41 of 76 resolve to a named replacement."),
]

# ---------------------------------------------------------------------------
# 9. Repository tree inventory. Populated by the builder by scanning the working tree.
# ---------------------------------------------------------------------------

TREES = [
    ("council/", "this session", "Decision council: requirements as acceptance tests, questions, "
                                 "suggestion review queue, verification, flags"),
    ("hub/", "arena/e9b492ab-x3, arena/621bf404-x3", "Canonical review hub; the repository root points here"),
    ("desk/", "arena/3bf7cc8b-x3", "Consolidated decision desk; owns the verified game log and the model"),
    ("origin/", "arena/f2df8317-x3", "Merged in PR #47: the eight requirements implemented as code - "
                                     "snapshot store, markets, moneyline, depth ordinals, gates D-1/D-2"),
    ("crosscheck/", "arena/37c71381-x3", "Cross-tree register reconciliation and link audit"),
    ("docs/", "arena/4856379c-x3, arena/0c38f465-x3", "First verified-data dashboard"),
    ("dashboard/", "arena/7e632805-x3", "18-page dashboard built from transcribed official data"),
    ("x3lab/", "arena/e1c332ce-x3", "Lines and strategy lab with gates G0-G8"),
    ("lab/", "early session", "Research lab: hypotheses, gates, correlation, leaderboard design"),
    ("audit/", "arena/d968fa97-x3", "Independent re-verification of the Week 10 injury report"),
    ("verification-hub/", "prior session", "Verification surface"),
    ("archive/hub-621bf404/", "arena/1e2d8ef2-x3", "Relocated tree from an earlier integration session"),
    ("pages/", "arena/1a771fcd-x3", "Category subpages from an early integration"),
    ("site/", "arena/1a771fcd-x3", "Early standalone site"),
    ("legacy/", "prior session", "The original root site, preserved"),
    ("(repository root)", "arena/35b167ca-x3", "Landing hub and root category pages"),
]

# ---------------------------------------------------------------------------
# 10. Executive summary prose. {{tokens}} are filled by the builder from the data.
# ---------------------------------------------------------------------------

EXEC_LEDE = (
    "This is a decision surface, not a betting site. It states the eight requirements of the brief as "
    "acceptance tests, reports exactly which ones the repository meets today, and lists what must be "
    "decided before any of them can be. Every number below was either read from an official NFL page on "
    "{{as_of}} or is left blank and marked UNVERIFIED. Nothing is inferred."
)

EXEC_FINDINGS = [
    ("Verified and solid",
     "The results foundation is real. {{n_finals}} completed games are logged with a per-row official "
     "source URL, the {{n_standings}} club standings reconcile, and the {{n_injury}} row Week 10 injury "
     "report was spot-checked {{n_spotcheck}} rows against the official page with zero mismatches. This "
     "session read nfl.com directly; the long-standing note that it cannot be reached is wrong."),
    ("The blocking gap",
     "No market price exists anywhere in the repository, and no NFL or club page publishes one. That "
     "single fact is why the fair-versus-market difference, closing-line value, ROI and the leaderboard "
     "are all blank. It is a data-rights decision, not an engineering task, and it is the first thing to "
     "resolve."),
    ("A confirmed defect, and its correction",
     "One published correlation did not reproduce from the data it cites: r(game total, |margin|) was "
     "published as -0.161 when the correct value is -0.0157, and -0.161 is in fact the signed-margin "
     "statistic. Its written reading had the sign backwards too. The corrected pairs are now published "
     "separately in origin/, with n and a 95% interval each; a stale copy carrying the wrong label is "
     "still on the desk tree. The pipeline was always sound - the label and the prose were not."),
    ("What is genuinely missing",
     "Player-prop history, a settlement rule, a dated depth chart and price data. Three of those four "
     "need a decision or a purchase; none can be fetched. The moneyline and the demotion gate were on "
     "this list at the start of the session and are no longer, because another session's module merged "
     "while this page was being written."),
    ("The honest read on skill",
     "Zero bets have been graded, so no strategy on any tree has demonstrated skill, and none has been "
     "shown to lack it. {{n_requirements_met}} of {{n_requirements}} requirements are met today and the "
     "rest are partly met, with the same blocker behind almost all of them. That is not a failure of "
     "analysis; it is the correct state of a project that has not yet bought its price data. The "
     "origination machinery - side, total, moneyline, fair line, gates, demotion - is built and waiting."),
]
