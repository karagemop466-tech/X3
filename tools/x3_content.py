#!/usr/bin/env python3
"""
X3 / content register for the eight market-structure requirements (session
arena/f0880a0b-x3).

This module is APPEND-ONLY relative to tools/hub_content.py: it adds registers, it does
not edit the older ones, so a parallel session holding hub_content.py cannot collide
with it. build_hub.py renders C.X + M.X for each register.

Conventions identical to hub_content.py:
  VERIFIED   read from an official page, URL given
  DERIVED    computed by a repo script from verified inputs
  UNVERIFIED no official source; blank, never inferred
  BLOCKED    cannot proceed until a named input exists
"""

AS_OF = "2026-11-14"

S = {
    "results": "https://www.nfl.com/schedules/2026/by-week/week-10",
    "standings": "https://www.nfl.com/standings/league/2026/REG",
    "injuries": "https://www.nfl.com/injuries/league/2026/reg10",
    "game_lac_bal": "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10",
    "odds_probe": "https://www.nfl.com/odds/",
    "stats": "https://www.nfl.com/stats/",
    "nfl_injuries_index": "https://www.nfl.com/injuries/",
    "players": "https://www.nfl.com/players/",
}

# ---------------------------------------------------------------------------
# Requirements added by this work (R-26..R-36), one per brief line
# ---------------------------------------------------------------------------
# id, area, requirement, acceptance criterion, status, evidence
REQ2 = [
    ("R-26", "Markets", "Price-snapshot store with an opening and a closing number for every "
     "market we originate",
     "Every originated market has an open and a close row; a close that does not exist yet is "
     "PENDING, never imputed", "VERIFIED",
     "data/x3/price_store.csv - counts are interpolated from the file at build time, never typed"),
    ("R-27", "Markets", "Verified results feed so backtests and ROI can be computed at all",
     "Results reconcile to an independent official source with zero mismatches, or the build fails",
     "VERIFIED",
     "data/x3/results_2026.csv - every club's results aggregate to the official standings with 0 "
     "mismatches, and the 16 Week-1 box scores match an independent live read"),
    ("R-28", "Markets", "Originate the side first, then the total, then the moneyline",
     "The origination order is explicit in the data and the moneyline is derived from the side "
     "model, not priced independently", "VERIFIED",
     "data/x3/markets.json origination_order; hub/markets.html prints the order per row and the "
     "moneyline is computed from the same margin model"),
    ("R-29", "Markets", "Publish fair line, market line and difference as separate columns",
     "Three distinct columns; a blank market cell carries a status and a reason", "VERIFIED",
     "hub/markets.html - one row per originated market per game, market columns blank and "
     "flagged (F-18)"),
    ("R-30", "Leaderboard", "Separate signal from staking so a lucky staking run cannot mask a bad "
     "signal", "Two columns, two data sources, and a promotion rule that requires both",
     "VERIFIED", "hub/leaderboard.html + data/x3/strategies.json scoring_contract"),
    ("R-31", "Depth", "Track the depth of the replacement, not just the fact of a replacement",
     "Each absence names the replacement and his chart tier, or is published UNVERIFIED",
     "VERIFIED", "hub/replacements.html - each absence either names a replacement with his chart "
     "tier or is published UNVERIFIED with the reason"),
    ("R-32", "Analytics", "Compute correlations only from officially sourced numbers and publish n "
     "with each value", "Every computed row names its source URL and its n; unsourced rows blank",
     "VERIFIED", "hub/correlation.html - 7 computed rows, each with n and a source; 5 blank rows"),
    ("R-33", "Governance", "Define a demotion gate that sends a live strategy back to paper",
     "Four named clauses, evaluated on every build, with the current verdict published",
     "VERIFIED", "hub/gates.html G-10 - D-4 currently fires; every strategy is on paper"),
    ("R-34", "Site", "A reviewable Suggestions section so a path can be chosen before any change",
     "Each suggestion carries impact, effort, risk, dependency and a blank decision column",
     "VERIFIED", "hub/suggestions.html - every proposal carries impact, effort, risk and a blank "
     "decision column"),
    ("R-35", "Site", "A clear list of questions, information and answers needed before a decision",
     "Known / missing / discovery path / owner / default for every open question",
     "VERIFIED", "hub/questions.html - known / missing / discovery path / owner / default per row"),
    ("R-36", "Reporting", "Executive summary of the important details",
     "One page that states what is verified, what is derived, what is blocked and what is not "
     "claimed", "VERIFIED", "hub/executive-summary.html"),
]

# ---------------------------------------------------------------------------
# Questions this work added (Q-17..Q-24)
# ---------------------------------------------------------------------------
# id, blocking, decision it gates, what we already know, what is missing,
# how to discover it, who answers, default if unanswered
Q2 = [
    ("Q-17", "YES", "Whether the difference column can ever be filled",
     "NFL.com publishes no odds: the LAC@BAL Week-10 game centre shows participation, team stats "
     "and standings, and /odds/ returns a 404 (both checked 2026-11-14, both linked on the "
     "sources page).",
     "A price publication we may legally use. No official one exists, so the choice is a licensed "
     "feed or a recorded manual snapshot.",
     "Compare a licensed feed's cost and terms against one recorded weekly snapshot with a "
     "timestamp and a screenshot hash.",
     "Owner (commercial decision)",
     "Market columns stay blank; fair line and difference stay empty and flagged (F-18)."),
    ("Q-18", "NO", "Whether two models may coexist on the site",
     "X3-v1 prices the Week-10 board from injury-cost priors with HFA set to 0; X3-v2 prices it "
     "from walk-forward results with a fitted HFA of 0.08 points. They disagree by up to 10.9 "
     "points on the same game (F-19).",
     "A decision on which is canonical after three weeks of v2.",
     "Compare both against outcomes for three weeks; the one with the lower walk-forward MAE wins "
     "by the rule already published on the gates page.",
     "Owner", "Both stay published and labelled; v1 is not deleted."),
    ("Q-19", "YES", "Whether to buy prior-season results",
     "One season of finals exists (137 games). Gate G-2 needs three seasons and gate G-3 needs a "
     "chronological walk-forward across them.",
     "Seven prior seasons of scores, venue and rest days from an official publication.",
     "NFL.com publishes historical schedules and scores by season; a bulk transcription of "
     "2018-2025 is mechanical work, not a purchase.",
     "Owner (whether the effort is funded)", "Gates G-2 and G-3 stay FAIL/BLOCKED forever."),
    ("Q-20", "YES", "What a reward may legally be",
     "The site places no bets and pays nothing; reward amounts are blank (F-06).",
     "The jurisdiction, and whether a skill contest with prizes is permitted there.",
     "Written advice from a qualified lawyer in the owner's jurisdiction.",
     "Owner", "Rewards stay notional; the leaderboard shows a paper tier only."),
    ("Q-21", "YES", "Whether to keep a total model that loses to a constant",
     "The total model's walk-forward MAE is 12.50 points against 11.14 for a constant 45.0 "
     "(n=105). It is published as-is and not tuned (F-21).",
     "A better total model, or a decision to publish the constant instead.",
     "Either fit a pace model with prior-season data, or state the constant and stop modelling "
     "the total.",
     "Owner", "The total stays published with its loss attached, or is replaced by the constant."),
    ("Q-22", "NO", "Whether club depth charts are acceptable evidence",
     "All 32 club charts are self-labelled unofficial and only 5 print an as-of date; 36 of 76 "
     "Week-10 absences can be resolved to a named replacement through them (F-22).",
     "An official, dated participation record.",
     "NFL.com publishes game-day participation and snap counts under /stats/; a weekly capture of "
     "those would replace the charts.",
     "Owner (effort)", "The 40 unresolved absences stay UNVERIFIED."),
    ("Q-23", "NO", "How a staking score is funded once prices exist",
     "No staking score exists. The staking column is BLOCKED for all 12 strategies, and the "
     "demotion gate's D-4 fires because of it.",
     "A bankroll definition, a unit size and a settlement convention.",
     "Write the staking contract before any price arrives, so the first price cannot define it "
     "after the fact.",
     "Owner", "Staking stays BLOCKED; the leaderboard stays a signal board."),
    ("Q-24", "NO", "Whether a prop or parlay strategy may be published as UNTESTED indefinitely",
     "Prop prices and prop settlement history do not exist in the repo, so 5 of 12 strategies "
     "cannot be tested at all (F-23).",
     "A decision on whether to keep them registered or archive them.",
     "Keep them registered: a dead hypothesis with a reason is cheaper than a deleted one that "
     "returns.",
     "Owner", "They stay UNTESTED, listed, and never ranked."),
]

# ---------------------------------------------------------------------------
# Suggestions this work added (S-15..S-26) - proposals, nothing implemented silently
# ---------------------------------------------------------------------------
# id, title, what and why, impact, effort, risk, depends on, status
SUG2 = [
    ("S-15", "Record one weekly price snapshot by hand, with a timestamp and a hash, and label it "
     "as such",
     "A licensed feed is the clean answer but it is a purchase. A single recorded snapshot per "
     "week (one book, one time, screenshot plus the numbers typed into data/x3/snapshots/) costs "
     "minutes and immediately makes the difference column meaningful. It must be labelled "
     "MANUAL-RECORDED, not official.",
     "Critical", "Low (one file a week)", "Medium - a hand-entered price is an unverified input "
     "and must never be shown as official", "Q-17", "PROPOSED", ""),
    ("S-16", "Treat a market price as a three-class object: OFFICIAL, RECORDED, BLANK",
     "The brief's rule is that an unconfirmable value is blank. A price has a middle state: "
     "recorded from a named book at a named time. Publishing the class next to the number keeps "
     "the rule honest without throwing away the only price we have.",
     "High", "Low", "Low", "S-15", "PROPOSED", ""),
    ("S-17", "Run the market engine weekly in CI so opening numbers are captured before kickoff",
     "The capture workflow already proves the pattern (a runner with full internet commits data "
     "back). Running markets_engine.py on a Tuesday and again on Sunday morning builds the "
     "open/close pair automatically instead of by memory.",
     "High", "Medium", "Low", "none", "PROPOSED", ""),
    ("S-18", "Add prior-season scores (2018-2025) so gates G-2 and G-3 can ever pass",
     "Every strategy is stuck behind a three-season requirement. NFL.com publishes historical "
     "schedules by season, so this is transcription work rather than a purchase.",
     "Critical", "High (8 seasons x 18 weeks)", "Low", "Q-19", "PROPOSED", ""),
    ("S-19", "Retire X3-v1 from the main navigation once X3-v2 has three weeks of walk-forward",
     "Two models on one site is the drift problem this repository keeps re-learning. Keep v1 "
     "reachable as an archive with its parameters, but navigate to one board.",
     "Medium", "Low", "Low", "Q-18", "PROPOSED", ""),
    ("S-20", "Price parlay legs from one joint simulation rather than a product of marginals",
     "The engine already produces a margin distribution and a total distribution per game. "
     "Drawing them jointly (with the measured r(margin,total) of -0.16 and r(home,away) of +0.08) "
     "is the honest way to price a same-game parlay, and the dependence is then visible.",
     "High", "Medium", "Low", "S-18", "PROPOSED", ""),
    ("S-21", "Replace club depth charts with game-day participation once captured",
     "Charts are unofficial and undated; participation is official and dated. The join is the "
     "same one replacements.html already does.",
     "High", "Medium", "Low", "Q-22", "PROPOSED", ""),
    ("S-22", "Publish a weekly movement digest from the price store",
     "Once a price source exists, the open-to-close movement is the cheapest visible signal of "
     "where information entered. The store already records the pair; only the digest is missing.",
     "Medium", "Low", "Low", "S-15", "PROPOSED", ""),
    ("S-23", "Keep the leaderboard paper-only until a staking contract and a legal answer exist",
     "A leaderboard with a prize is a contest. The signal board is useful today; the prize is "
     "not. Paper tiers cost nothing and cannot be mistaken for a payout.",
     "Medium", "Low", "Low", "Q-20, Q-23", "PROPOSED", ""),
    ("S-24", "Make snapshot files write-once and verify them by hash in CI",
     "The store is append-only today by convention. Hashing each snapshot and checking the hash "
     "in CI turns the convention into a guarantee, which is what makes a backtest auditable.",
     "Medium", "Low", "Low", "S-17", "PROPOSED", ""),
    ("S-25", "Show the model's own error bar on every published number",
     "sigma (13.03 points) is already computed. Printing +/-1 sigma next to each fair line stops "
     "a reader treating a half-point as precision.",
     "Medium", "Low", "Low", "none", "PROPOSED", ""),
    ("S-26", "Archive the prop and parlay strategies, or label them UNTESTABLE rather than "
     "UNTESTED",
     "Five strategies need an input that does not exist. UNTESTED implies it could be tested "
     "tomorrow; UNTESTABLE is the truth until a prop archive exists.",
     "Low", "Low", "Low", "Q-24", "PROPOSED", ""),
]

# ---------------------------------------------------------------------------
# Irregularities this work found (F-18..F-26)
# ---------------------------------------------------------------------------
# id, severity, area, finding, source to check, action
FLAGS2 = [
    ("F-18", "HIGH", "Market data",
     "NFL.com publishes no odds at all. The LAC@BAL Week-10 game centre (checked 2026-11-14) "
     "carries participation, team stats and standings and no spread, total or moneyline, and "
     "nfl.com/odds/ returns a 404. The official-source class for a market price therefore does "
     "not exist, which is why the difference column is structurally blank rather than merely "
     "unfilled.",
     S["game_lac_bal"] + " and " + S["odds_probe"],
     "Choose a price class (Q-17). The column stays blank and badged until then."),
    ("F-19", "MEDIUM", "Model drift",
     "Two models price the same Week-10 games and disagree. X3-v1 (hub/lines.html) uses "
     "injury-cost priors with home-field advantage set to 0.0; X3-v2 (hub/markets.html) fits on "
     "137 verified finals and measures a home-field term of 0.08 points. The largest gap between "
     "the two boards is 10.9 points on one game.",
     "https://github.com/karagemop466-tech/X3/blob/main/hub/lines.html vs hub/markets.html",
     "Q-18: retire one after three weeks of walk-forward. Both stay labelled meanwhile."),
    ("F-20", "MEDIUM", "Retraction",
     "Old F-02 ('no game log; one final score known') is RETRACTED. A 163-game capture with 137 "
     "finals exists in data/desk/games.json, captured by this repository's own CI runner "
     "(212/212 pages HTTP 200). The new results feed reconciles it to the official standings with "
     "0 mismatches on 32 clubs, so the data was there and the flag was wrong.",
     S["standings"],
     "No action. Recorded so the flagged list does not keep asserting a gap that is closed."),
    ("F-21", "MEDIUM", "Model performance",
     "The total model loses to a constant. Walk-forward MAE is 12.50 points against 11.14 for a "
     "constant 45.0 on n=105 games. It is published with the loss attached rather than tuned "
     "until it looks better.",
     S["results"],
     "Q-21: keep with the loss, or publish the constant until a pace model is fitted."),
    ("F-22", "MEDIUM", "Depth charts",
     "Only 5 of 32 club depth charts print an as-of date, and all 32 are self-labelled unofficial "
     "by the club. 40 of 76 Week-10 absences therefore cannot be resolved to a named replacement "
     "from an official source and are published UNVERIFIED instead of guessed.",
     S["nfl_injuries_index"],
     "Q-22 / S-21: replace charts with dated participation."),
    ("F-23", "LOW", "Cross-role name match",
     "16 player names matched a club depth chart only inside a different position group (a tight "
     "end matched to a running-back slot, a tackle to a guard slot). The engine refuses a "
     "cross-role match rather than using it to name a replacement, so those rows are UNVERIFIED "
     "by design.",
     "https://github.com/karagemop466-tech/X3/blob/main/tools/depth_engine.py",
     "No action. Refusing is the correct behaviour; the refusal is counted and published."),
    ("F-24", "LOW", "Strategy catalogue",
     "5 of 12 registered strategies (both prop-combo and parlay families, plus the prop single) "
     "cannot be tested at all: no prop price and no prop settlement history exists, and no "
     "official source publishes either.",
     S["stats"],
     "Q-24 / S-26: label them UNTESTABLE until a prop archive exists."),
    ("F-25", "LOW", "Scoring convention",
     "The signal score for the side model is +0.205 points of absolute-error improvement over the "
     "naive baseline, with a bootstrap 95% CI of [-1.047, +1.478]. The interval contains zero, so "
     "the honest label is INCONCLUSIVE, not 'beats the baseline'. The direction hit rate (62.9%, "
     "CI [53.3%, 71.5%]) is a different and weaker claim, and is published next to its own "
     "baseline.",
     S["results"],
     "No action. This is the label the leaderboard uses; do not upgrade it without a wider CI."),
    ("F-26", "LOW", "Price store",
     "The store has one snapshot milestone. Every close in it is a reconstructed close (our own "
     "number refitted on finals before kickoff), not a captured one, and every open for the live "
     "slate is a single fit rather than a before-kickoff capture. The distinction is printed in "
     "every row's note column, because a reconstructed close and a captured close are not the "
     "same evidence.",
     "https://github.com/karagemop466-tech/X3/blob/main/data/x3/price_store.csv",
     "S-17 / S-24: schedule the capture and hash the files."),
    ("F-27", "MEDIUM", "Repository duplication",
     "A parallel session independently implemented the same eight market-structure requirements in a "
     "second tree (ledger/ with data/ledger/*.csv and its own builder and verifier), and both trees now "
     "ship. This is the eighth time this repository has grown a parallel site for the same facts, which "
     "is the single largest usability and audit problem here.",
     "https://github.com/karagemop466-tech/X3/blob/main/hub/archive.html",
     "hub/ stays canonical because it is the only tree the Pages workflow rebuilds and diffs, and the "
     "only one whose navigation carries every page. Reconcile or archive ledger/ in a later session; "
     "nothing is deleted."),
]
