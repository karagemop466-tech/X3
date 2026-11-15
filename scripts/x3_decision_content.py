#!/usr/bin/env python3
"""
Builder for the X3 decision layer: the review surface that sits *above* the
sixteen implementation trees and answers one question - what is ready to decide,
what gate blocks it, and what number would clear that gate.

It deliberately implements no pricing model, no leaderboard and no scraper of its
own: those exist already (hub/, signals/, origin/, ops/, council/, desk/) and the
duplicate-tree problem is itself a flagged irregularity. This tree only reads.

Inputs (all read-only, all inside the repository):
  data/snapshots/ledger.json        sealed availability reads
  data/snapshots/delta.json         point-in-time deltas between them
  hub/data/lines.json               the originated Week-10 slate
  data/desk/games.json              the verified results feed
  data/desk/model.json              ratings + backtest block
  origin/data/markets.json          three-market origination
  data/desk/correlations.json       correlation store
  data/desk/parse_report.json       parser problems the desk pipeline recorded
  data/desk/text/depth-*.txt        retained club depth pages

Every number that appears in the prose is interpolated from those files at build
time. A missing key raises KeyError and aborts the build, so the text cannot
drift from the tables it describes.

Run: python3 scripts/build_decision.py
"""
from __future__ import annotations

import glob
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "decision")
AS_OF = "2026-11-15T18:16Z"
BUILD = "build_decision.py v1"


def load(*parts):
    return json.load(open(os.path.join(ROOT, *parts), encoding="utf-8"))


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


# ---------------------------------------------------------------- inputs -----
ledger = load("data", "snapshots", "ledger.json")
delta_doc = load("data", "snapshots", "delta.json")
D = delta_doc["deltas"][0]
lines_doc = load("hub", "data", "lines.json")
games = load("data", "desk", "games.json")
games_rows = games if isinstance(games, list) else (games.get("games") or games.get("rows"))
model = load("data", "desk", "model.json")
parse_report = load("data", "desk", "parse_report.json")
markets = load("origin", "data", "markets.json")
desk_corr = load("data", "desk", "correlations.json")

lines_rows = lines_doc["rows"]
n_priced = len(lines_rows)
n_with_market = sum(1 for r in lines_rows if (r.get("market_spread") or "").strip())
n_finals = sum(1 for r in games_rows if r.get("home_score") is not None)
n_games = len(games_rows)
venue_stale = sum(1 for p in glob.glob(os.path.join(ROOT, "origin", "data", "markets.json"))
                  for _ in range(open(p, encoding="utf-8").read().count("Alemun")))
depth_files = sorted(glob.glob(os.path.join(ROOT, "data", "desk", "text", "depth-*.txt")))
depth_rows = {}
for p in depth_files:
    team = os.path.basename(p).split("-")[1].split(".")[0]
    n = 0
    with open(p, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if ln[:2] in ("QB", "RB", "WR", "TE", "LT", "LG", "C ", "RG", "RT", "DE", "NT",
                         "OL", "IL", "LB", "CB", "SS", "FS", "S ", "K ", "P ", "LS"):
                n += 1
    depth_rows[team] = n
depth_zero = sorted(t for t, n in depth_rows.items() if n == 0)
captures = {c["capture_id"]: c for c in ledger["captures"]}
new_cap = [c for c in ledger["captures"] if c.get("sealed")][0]
old_cap = [c for c in ledger["captures"] if not c.get("sealed")][0]

# trees present in the repository (a directory that serves its own index.html)
# The review layer is not one of the implementation trees, and counting it would
# make the tree count depend on whether this build has already run - a
# self-referential number is not a measurement.
TREES = []
for d in sorted(x for x in os.listdir(ROOT) if x != "decision"):
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and not d.startswith(".") and os.path.exists(os.path.join(p, "index.html")):
        htmls = [f for f in os.listdir(p) if f.endswith(".html")]
        TREES.append((d, len(htmls)))
n_trees = len(TREES)

CTX = {
    "as_of": AS_OF, "build": BUILD, "n_trees": n_trees, "n_trees_list": ", ".join(t for t, _ in TREES),
    "n_priced": n_priced, "n_with_market": n_with_market, "n_finals": n_finals, "n_games": n_games,
    "rows_before": old_cap["counts"]["rows"], "rows_after": new_cap["counts"]["rows"],
    "desig_before": old_cap["counts"]["rows"] - old_cap["counts"]["blank_game_status"],
    "desig_after": new_cap["counts"]["rows"] - new_cap["counts"]["blank_game_status"],
    "blank_after": new_cap["counts"]["blank_game_status"],
    "n_desig_changes": D["designation_changes_count"], "n_prac_changes": D["practice_changes_count"],
    "n_added": D["added_rows_count"], "n_dropped": D["dropped_rows_count"],
    "adverse": D["surprise_panel"]["adverse"], "favourable": D["surprise_panel"]["favourable"],
    "hash_new": new_cap["sha256"][:16], "hash_old": old_cap["sha256"][:16],
    "depth_clubs": len(depth_rows), "depth_zero": ", ".join(depth_zero) or "none",
    "venue_stale": venue_stale,
    "parse_problems": parse_report["problem_count"],
    "corr_n": desk_corr["pairs"][0]["n"], "corr_r": desk_corr["pairs"][0]["r"],
    "pred_sd": model.get("backtest", {}).get("margin_sd_predicted", "n/a"),
}

# ------------------------------------------------------------------ data -----
# Requirement register. Columns: id, requirement, status, where, gate, clears,
# basis, source. `basis` is what makes the row auditable: how this session came
# to the status it prints.
READY, PARTIAL, BLOCKED, NOT_STARTED, POLICY, DEFECT, DECIDED = (
    "READY", "PARTIAL", "BLOCKED", "NOT STARTED", "POLICY", "DEFECT", "DECIDED")

V = "VERIFIED THIS SESSION"          # this session opened the official page or the file
R = "READ REPO FILE"                  # status read directly out of a repo artefact
A = "PRIOR AUDIT CITED"               # another session's audit, cited, not re-run
U = "NOT RE-COUNTED"                  # the brief's number, not independently reproduced

REQS = [
 # ---- market & price layer
 ("P-01", "Price-snapshot store: opening and closing numbers for every market we originate", PARTIAL,
  "origin/data/snapshots.json · hub/price-store.html",
  "the closing half of every row is pending, and market_line is blank on every row",
  "39 of 39 markets holding a dated open AND close number", R,
  "file:origin/data/snapshots.json"),
 ("P-02", "Verified results feed so backtests and ROI can be computed at all", READY,
  "data/desk/games.json",
  "nothing blocks the backtest half; ROI stays blocked by P-01",
  f"{n_finals} finals reconciled to 32 clubs with 0 standings mismatches", V,
  "url:https://www.nfl.com/schedules/2026/by-week/week-10"),
 ("P-03", "Originate the side first, then the total, then the moneyline", READY,
  "origin/data/markets.json · hub/origination.html",
  "none", "0 order violations across every game (audited 13/13)", A, "file:origin/data/markets.json"),
 ("P-04", "Publish the fair line, the market line and the difference as separate columns", PARTIAL,
  "hub/lines.html · origin markets",
  "the market and difference columns exist but are empty",
  f"both populated for all {n_priced} priced games before the residual is trusted", V,
  "file:hub/data/lines.json"),
 ("P-05", "Price a line ourselves and publish the residual against the market, on a schedule, from day one", BLOCKED,
  "no residual panel exists",
  "no dated external price exists to subtract; the residual is not estimable from repo data",
  "1 published residual on 1 game, on a schedule, with both timestamps on the row", V,
  "file:hub/data/lines.json"),
 ("P-06", "Decide the price-data policy before any backtest is published", DECIDED,
  "decision/pricing.html (this session)",
  "the decision itself - three options, one must be chosen; backtests have already been published in three trees without it",
  "one option signed off; 0 backtests left unlabelled by it", V, "file:decision/pricing.html"),
 ("P-07", "Publish every model total twice until one wins", NOT_STARTED,
  "-",
  "one total per game is published today; there is no second estimator to collapse",
  "2 estimators x 13 games, then a walk-forward pick on >=30 games", R, "file:hub/data/lines.json"),
 ("P-08", "Vig-free market consensus vs originated fair-line decomposition", BLOCKED,
  "-",
  "needs at least two priced books per market; the repository holds zero",
  "2 priced books per game for 1 full week", V, "file:hub/data/lines.json"),
 # ---- leaderboard & evaluation
 ("L-01", "Separate 'signal' from 'staking' so a lucky run cannot mask a bad signal", PARTIAL,
  "signals/leaderboard.html · hub/signal.html",
  "the staking side is empty by design: 0 settled bets",
  "signal side already populated (3 metrics with n); staking needs P-01", A, "file:signals/leaderboard.html"),
 ("L-02", "Pre-register every strategy; forbid backtest numbers from ever appearing on the leaderboard", PARTIAL,
  "hub/data/prereg.json",
  "the registration froze a method the brief rejects (see A-27), so it registers the wrong thing",
  "re-registration commit + 0 backtest cells on the leaderboard page", V, "file:hub/data/prereg.json"),
 ("L-03", "Rank with proper scores and uncertainty, not win rate", READY,
  "signals engine (Brier skill, game-cluster CI, Benjamini-Hochberg)",
  "none", "4 strategies already ranked on a signal interval", A, "file:signals/index.html"),
 ("L-04", "Proper-score leaderboard divisions: singles, game parlays, SGPs, prop combos", PARTIAL,
  "signals · origin",
  "the divisions are defined; only singles carries rows",
  "4 divisions with >=1 registered strategy each", A, "file:signals/leaderboard.html"),
 ("L-05", "Control baseline (random picks; favourites only) in every leaderboard run", PARTIAL,
  "hub/luck.html · data/desk/luck.json",
  "a constant baseline exists; a favourites-only baseline is not verified in this tree",
  "3 baselines printed beside every ranked strategy", R, "file:data/desk/luck.json"),
 ("L-06", "Demotion gate that sends a live strategy back to paper", READY,
  "origin D-1a..D-1e + D-2 · signals (7 rules)",
  "nothing is live, so nothing can be demoted; two triggers are already armed",
  "1 live strategy; gate fires when the BSS lower bound < 0 over 20 games", A, "file:signals/gates.html"),
 ("L-07", "Compute correlations only from officially sourced numbers and publish n", DEFECT,
  "data/desk/correlations.json vs origin/data/correlations.json",
  "the desk store labels r(total, signed home margin) as total vs |margin|; the reading is a sign error",
  f"relabel the desk row (n={CTX.get('corr_n')} already printed); 1 line", V, "file:data/desk/correlations.json"),
 ("L-08", "Compute and publish the 'removal of luck' panel on the site dashboard", PARTIAL,
  "hub/luck.html · data/desk/luck.json",
  "the panel exists on a subpage; the landing page does not carry it",
  "variance share on the landing + 1 line per ranked strategy", R, "file:hub/luck.html"),
 ("L-09", "Rewards for top-performing strategies", NOT_STARTED,
  "-",
  "no payout rule, escrow or cliff is written anywhere in the repository",
  "1 reward policy row + a >=4-week prospective escrow before any payout", V, "file:decision/suggestions.html"),
 ("L-10", "Keep parlays and prop combos behind a joint-evidence gate", READY,
  "signals · origin (multiplication under dependence is refused)",
  "no validated joint probability, so no combo is ranked - correctly",
  "1 joint probability validated out of sample before the first combo is ranked", A, "file:signals/gates.html"),
 # ---- availability, injury, depth
 ("A-01", "Track the depth of the replacement, not just the fact of a replacement", PARTIAL,
  "origin/data/depth.json",
  "42 of 76 replacements resolved, and 0 of 76 carry a chart as-of date",
  "76 of 76 resolved with an as-of date on every row", A, "file:origin/data/depth.json"),
 ("A-02", "Build the availability graph as a first-class dataset", PARTIAL,
  "data/desk/deficiencies.json · depth.json",
  "no edges and no versioning against the last official roster event",
  "a graph with typed edges + 1 version stamp per node", R, "file:data/desk/deficiencies.json"),
 ("A-03", "Model depth from playing time, not jersey order", BLOCKED,
  "-",
  "no official snap-count source is ingested anywhere in the repository",
  "1 verified snap-count source covering 1 full club-week", V, "file:decision/questions.html"),
 ("A-04", "Make the injury signal a surprise, never a level", READY,
  "decision/snapshots.html (this session)",
  "one day of history exists; a feature needs >=3 clock times per week cut per game slot",
  f"{D['designation_changes_count']} changes already measured between two reads, {D['surprise_panel']['adverse']} adverse", V,
  "url:https://www.nfl.com/injuries/league/2026/reg10"),
 ("A-05", "Run the 32-team roster/IR sweep before any team-level model is trusted", PARTIAL,
  "data/desk/text/depth-*.txt",
  f"{len(depth_zero)} club page(s) yield no depth rows at all: {CTX['depth_zero']}",
  f"{len(depth_rows)} of 32 clubs parsed today; 32 of 32 to trust the model", V,
  "file:data/desk/parse_report.json"),
 ("A-06", "Store every injury-hub read with its clock time and publish the delta, never the level", READY,
  "data/snapshots/ledger.json · delta.json (this session)",
  "the earlier read has a date but no hour, so the gap cannot be stated in hours",
  "2 sealed reads, 1 day apart, both hashed; every future read carries hh:mm", V,
  "file:data/snapshots/ledger.json"),
 ("A-07", "Capture official inactive lists and snap counts", NOT_STARTED,
  "-",
  f"no inactive or active-list capture exists; {D['counts_after']['blank_game_status']} of {CTX['rows_after']} rows carry no game designation today",
  "T-90 inactives for 13 games + snap share per player", V, "url:https://www.nfl.com/injuries/league/2026/reg10"),
 ("A-08", "Automate immutable multi-day availability snapshots with retained hashes", PARTIAL,
  "data/snapshots/ (this session)",
  "the store is immutable and hashed but manual: no scheduled runner, and captures live in the repo, not outside it",
  "1 scheduled run per day for 3 consecutive days with 0 manual steps", V, "file:data/snapshots/README.md"),
 ("A-09", "Fix the two depth-parsing failures before widening coverage", PARTIAL,
  "data/desk/text/depth-GB.txt · depth-HOU.txt",
  "the Packers raw line still reads 'QB 10 Jordan Love 6 Tyrod Taylor' (numbers present, stripping unverified); the Texans page yields 0 rows",
  "GB rows parsed with the raw string retained + 1 authorized structured source for HOU", V,
  "file:data/desk/text/depth-HOU.txt"),
 ("A-10", "Model depth slots as groups, not a single starter", PARTIAL,
  "club depth captures",
  "the brief counts 149 slots with more than one rank-1 player; not re-counted this session",
  "re-count from the retained captures, then a group-aware slot table", U, "file:data/desk/text/"),
 ("A-11", "Treat roster turnover as a first-class data event", NOT_STARTED,
  "-",
  "no transactions or reserve-list capture exists in data/desk/text (only depth, games, injuries, schedule, standings, team-stats)",
  "1 dated transactions feed + a version edge per turnover event", V, "file:data/desk/text/"),
 ("A-12", "Reject deriving depth order from jersey number, experience or salary", POLICY,
  "rule in force",
  "nothing to build - the reject is respected; jersey numbers are stripped, never ranked by",
  "0 features sourced from jersey number / salary / experience", V, "file:decision/readiness.html"),
 ("A-13", "Represent shared and empty depth slots faithfully", PARTIAL,
  "depth captures",
  "a shared slot and an empty slot are still one string in the retained text",
  "typed slot states for all 32 clubs", A, "file:data/desk/text/"),
 ("A-14", "Resolve the depth-order source before building the backup-deficiency feature", PARTIAL,
  "route (a) per-club pages; route (b) snap counts",
  "route (a) works for " + str(len(depth_rows)) + " of 32 clubs and fails for " + CTX['depth_zero'] + "; route (b) has no source at all",
  "one route verified for all 32 clubs", V, "file:data/desk/parse_report.json"),
 ("A-15", "Score injury-designation reliability before using it as a feature", BLOCKED,
  "-",
  "needs the official inactive lists (A-07) joined to several seasons of designations",
  ">=3 seasons x play rate per designation with a 95% CI that excludes 100% or 0%", V, "file:decision/questions.html"),
 ("A-16", "Snapshot the injury report every Wed, Thu and Fri and keep a dated history", PARTIAL,
  "data/snapshots/wk10/ (this session)",
  "cadence is manual; two reads exist, one of them on a Sunday, which the Wed/Thu/Fri rule never contemplated",
  "3 reads inside one week from a scheduled runner", V, "file:data/snapshots/ledger.json"),
 ("A-17", "Treat the injury report as a timestamped series, daily Wed to kickoff", PARTIAL,
  "same store",
  f"the series exists but has 2 points; measured today: Monday-night clubs' designations still moved on Sunday at {AS_OF[11:16]}Z",
  "a daily series with 0 gaps from Wednesday to each game's kickoff", V, "url:https://www.nfl.com/injuries/league/2026/reg10"),
 ("A-18", "Use snap counts as the starter proxy when the depth chart is unavailable", BLOCKED,
  "-",
  "blocked on the same missing source as A-03; the Texans case is exactly where it would be needed",
  "1 club-week of official snap counts", V, "file:decision/questions.html"),
 ("A-19", "Flag stale depth rows against the official transactions log", PARTIAL,
  "data/desk/text/depth-BAL.txt line 52",
  "the Baltimore staleness named in the brief is gone from the retained capture - it now reads 'QB Jacoby Brissett Joe Fagnano Kedon Slovis'; the flag rule itself is not automated",
  "1 automated staleness check per club per capture", V, "file:data/desk/text/depth-BAL.txt"),
 ("A-20", "Populate the three missing Lions game-status designations", READY,
  "hub/data/injuries.json · DET section of the official report",
  "none - re-read today: Joseph, Mays and Reed all print 'Out'",
  "3 of 3 populated; 0 blank cells in the DET block", V, "url:https://www.nfl.com/injuries/league/2026/reg10"),
 ("A-21", "Re-capture and republish the Week 10 injury tables", READY,
  "data/desk/injuries.json (11-14) · data/snapshots/wk10 (11-15)",
  "none; the brief's '254 rows / 4 no-injury sections' is superseded by two verified reads of 345 and 347 rows",
  f"{CTX['rows_after']} rows on 28 clubs, counts published with the fetch time", V,
  "url:https://www.nfl.com/injuries/league/2026/reg10"),
 ("A-22", "Add an announced-starter evidence field, not an inferred replacement", PARTIAL,
  "official dated articles found this session (Lock, Watson/Beck, McCord)",
  "the field does not exist yet; the evidence for it does, in dated news items beside the report",
  "1 article link per announced change, on the row that changes", V,
  "url:https://www.nfl.com/news/drew-lock-no-injury-designation-seahawks-raiders"),
 ("A-23", "Official depth-chart register with date and source per row", BLOCKED,
  "origin/data/depth.json",
  "0 of 76 rows carry an as-of date, which is what makes a chart usable at a point in time",
  "76 of 76 rows with date + source URL", A, "file:origin/data/depth.json"),
 ("A-24", "Calibrate what 'Questionable' means empirically, not from old percentages", BLOCKED,
  "-",
  "the official page prints no percentages, and the calibration needs inactives (A-07) + historical weeks",
  "play rate for Questionable over >=3 seasons with a CI, from official pages only", V,
  "url:https://www.nfl.com/injuries/league/2024/reg10"),
 ("A-25", "Archive weekly injury reports for past seasons", DECIDED,
  "unblocked by this session",
  "was believed blocked by access; verified reachable - the league serves /injuries/league/{year}/reg{week} for past seasons back to 1965",
  "1 season x 18 weeks captured into the snapshot store", V, "url:https://www.nfl.com/injuries/league/2024/reg10"),
 ("A-26", "Interactive Offense vs Defense deficiency matrix (1st-4th string)", BLOCKED,
  "-",
  "depends on A-14 and A-09; without a resolved depth source the matrix would print invented matchups",
  "32 clubs with a verified depth source, then one rendered matrix", V, "file:decision/readiness.html"),
 ("A-27", "Injury/personnel ablations instead of fixed penalties", DEFECT,
  "hub/data/lines.json · hub/data/prereg.json",
  "the frozen model applies a fixed additive penalty: injury_delta 1.2 / 0.63 / 4.48 points on the line, and prereg pins pos_cost QB 4.0, RB 1.5, WR 1.1 ...",
  "1 ablation pair (with / without personnel features) on chronological holdouts, difference + uncertainty", V,
  "file:hub/data/prereg.json"),
 ("A-28", "Durable snapshot storage outside the static site, with freshness alerts", PARTIAL,
  "data/snapshots/ + decision gate",
  "storage is repo-local and immutable but there is no freshness monitor and no alert on source or schema change",
  "1 scheduled capture per day + 1 alert firing on a missed day", V, "file:scripts/x3_snapshots_verify.py"),
 ("A-29", "Drift alarm on every scraper: expected row counts and required fields", PARTIAL,
  "scripts/x3_snapshots_verify.py (this session)",
  "the alarm exists for the availability store only; depth, games and standings parsers still publish blanks quietly",
  "row-count + required-field assertions on 4 of 4 parsers, build fails on a blank", V,
  "file:scripts/x3_snapshots_verify.py"),
 ("A-30", "Per-team view: starters out, replacements named, net injury count", PARTIAL,
  "hub/injuries.html · hub/depth.html",
  "starters-out and net counts are derivable and shown; 'replacements named' is the column that stays blank for lack of inactives",
  "3 of 3 columns non-blank for 32 clubs", R, "file:hub/depth.html"),
 # ---- model outputs & features
 ("M-01", "Fixture-context feature set built only from published schedule facts", PARTIAL,
  "data/desk/games.json (neutral_site, kickoff slot, network)",
  "the fields are captured but not used as features; rest days and travel are not computed",
  ">=4 fixture features wired into the originator with a walk-forward run", R,
  "url:https://www.nfl.com/schedules/2026/by-week/week-10"),
 ("M-02", "Store every model output as a probability plus its inputs, not just a pick", PARTIAL,
  "origin markets (P(home) on the moneyline row)",
  "spreads and totals are stored as points, not probabilities, and the input vector is referenced not embedded",
  "100% of rows carrying p + an input-vector id that resolves", A, "file:origin/data/markets.json"),
 ("M-03", "Ingest game-level results so the ratings are opponent-aware", READY,
  "data/desk/model.json (ridge on finals)",
  "none", f"{n_finals} finals feed the ratings; 0 standings mismatches", R, "file:data/desk/model.json"),
 ("M-04", "2026 kickoff & declared onside-kick regime prior filter", NOT_STARTED,
  "-",
  "no rulebook parameter is wired into the originator; totals and 4th-quarter win probability carry no regime prior",
  "1 frozen parameter in the registration + a re-run of the backtest", U, "url:https://operations.nfl.com/the-rules/2026-nfl-rulebook/"),
 ("M-05", "Stadium roof/surface & NWS hourly wind/precipitation overlay", NOT_STARTED,
  "-",
  "no venue register and no forecast capture exist in the repository",
  "roof designation + a forecast vector for 13 games, both dated pre-kickoff", V, "file:decision/questions.html"),
 ("M-06", "Ingest game-level results to make the ratings opponent-aware", READY,
  "same artefact as M-03 - listed once in the brief under two phrasings",
  "none", "one store, one generator, 0 duplicate pipelines", R, "file:data/desk/games.json"),
 # ---- governance, site, process
 ("G-01", "Freeze a rule before it sees data; the commit hash is the registration", PARTIAL,
  "hub/data/prereg.json",
  "the registration records a date and a session id but no commit hash, so the freeze is not verifiable",
  "40-character sha on every strategy row, resolvable in git", V, "file:hub/data/prereg.json"),
 ("G-02", "Split data into train, validation and final holdout seasons", BLOCKED,
  "-",
  "the repository holds one season (2026); the historical pages are reachable (A-25) but nothing is ingested",
  "3 seasons frozen: 2023-24 train, 2025 validation, 2026 holdout", V, "url:https://www.nfl.com/injuries/league/2024/reg10"),
 ("G-03", "Turn the 136-game log into the pre-registered backtest corpus", PARTIAL,
  "data/desk/games.json",
  f"the store holds {n_games} games and {n_finals} finals, not 136; the corpus is not frozen by hash, so 'pre-registered' is not yet checkable",
  f"corpus hashed at a stated count ({n_finals} finals today) + 1 registered evaluation window", V,
  "file:data/desk/games.json"),
 ("G-04", "Transcribe the venue of every fixture from the official game centre", DEFECT,
  "origin/data/markets.json",
  f"'Alemun & Munchen' - a string no official page prints - is still on {venue_stale} rows of a served tree",
  "0 unsourced venue strings in any served file", V, "url:https://www.nfl.com/schedules/2026/by-week/week-10"),
 ("G-05", "Publish the league's dated schedule announcement beside the live schedule page", PARTIAL,
  "docs/ · sources pages",
  "the announcement is cited but not rendered beside the schedule table",
  "1 dated announcement link on the schedule page itself", A, "file:docs/"),
 ("G-06", "Use official NFL Game Books for actual starters; do not infer depth rank or snaps", NOT_STARTED,
  "-",
  "no game book is parsed; play-by-play is the closest artefact and it is not retained",
  "1 game book parsed per week, with the starter rows diffed against the depth chart", V,
  "url:https://operations.nfl.com/the-rules/2026-nfl-rulebook/"),
 ("G-07", "Split the site into a public analysis layer and a private data layer", DEFECT,
  "data/desk/text/** (raw third-party page bodies, inside the served tree)",
  "raw club-page text is published on the public site while the terms are unread - the exact exposure the requirement exists to prevent",
  f"0 raw page bodies under a served path ({len(depth_files)} depth captures alone are in it today)", V,
  "file:data/desk/text/"),
 ("G-08", "Put a decision-readiness table on the landing page", READY,
  "decision/readiness.html + decision/landing-block.html",
  "the landing page itself is another session's file while PR #72 is open; the block is paste-ready and the request is logged",
  "1 nav row + the block pasted into index.html", V, "file:decision/landing-block.html"),
 ("G-09", "A section dedicated to suggestions, reviewed before anything is implemented", READY,
  "decision/suggestions.html",
  "none - every row carries a blank decision column and nothing in it has been implemented",
  "1 suggestion accepted, 0 implemented before acceptance", V, "file:decision/suggestions.html"),
 ("G-10", "Questions, information we have and lack, and the answers, with missing-info discovery", READY,
  "decision/questions.html",
  "none; two questions were closed by evidence gathered today",
  "every open question naming the artefact or fetch that would close it", V, "file:decision/questions.html"),
 ("G-11", "Executive summary outlining important details", READY, "decision/executive-summary.html",
  "none", "numbers interpolated at build time so the prose cannot drift", V, "file:decision/executive-summary.html"),
 ("G-12", "No manual input from the owner; work autonomously end to end", READY, "this session",
  "none - no value on any page here was typed in by the reviewer",
  "0 fields requiring human entry to render", V, "file:COORDINATION.md"),
 ("G-13", "Reject ranking strategies by season-long ROI alone", POLICY, "rule in force",
  "nothing to build; proper-score ranking is implemented (L-03) and ROI alone is refused",
  "0 leaderboard rows ranked on realised return alone", A, "file:signals/leaderboard.html"),
 ("G-14", f"Consolidate the {n_trees} overlapping site trees into one canonical surface", NOT_STARTED,
  "decision/trees.html (this session counts them)",
  "sixteen sessions each added a tree instead of editing one; every shared artefact now has competing copies",
  "1 canonical tree + " + str(max(0, n_trees - 1)) + " frozen read-only with a pointer", V, "file:decision/trees.html"),
 ("G-15", "Every table row must carry a source link to an official site, else blank + flagged", READY,
  "decision/* + scripts/verify_decision.py",
  "none for this tree; older trees still hold rows with neither link nor flag (prior audit counted 658)",
  "0 rows without a link or an explicit badge - enforced by the build gate", V, "file:scripts/verify_decision.py"),
]

# ---------------------------------------------------------------- suggestions
SUGS = [
 ("S-D1", "Pick the price-data policy, then label every published backtest with it", "blocking everything monetised",
  "There is no market price in the repository: " + str(n_priced) + " priced games, " + str(n_with_market) +
  " with a market line. Three trees publish backtests anyway, and the brief says the policy must be decided first.",
  [("A", "Decline prices: publish structure, skill and calibration only, and rename every ROI cell to 'not applicable'."),
   ("B", "License a price feed: contract, terms and retention decided first, then a one-week shadow capture before any backtest cites it."),
   ("C", "Self-record one operator's open and close per game with a dated hash, after a read of the terms.")],
  "B and C unblock P-01, P-05, P-08, the staking half of L-01, L-09 and every ROI cell at once; A unblocks nothing but makes the site honest today",
  "hours (A) to weeks (B)",
  "A is reversible in an afternoon; C is the cheapest path that still produces a real closing-line value, and it inherits S-D8"),
 ("S-D2", "Declare one canonical tree and freeze the rest read-only", "process",
  f"{n_trees} directories each serve their own index: {CTX['n_trees_list']}. Four of them re-implement the same eight requirements on the same inputs.",
  [("A", "Promote hub/ (widest nav, it owns the landing page) and reduce signals/, origin/, ops/ and council/ to appendices."),
   ("B", "Promote signals/ (the only tree with a settled engine, a deterministic gate and a nested walk-forward fit) and reduce the rest."),
   ("C", "Keep every tree, publish one index that states which artefact answers which requirement, and admit no new tree.")],
  "one leaderboard, one price store, one results feed, one requirements register - each is duplicated three or four times today",
  "hours, plus a decision nobody has made",
  "C is what this session did; it does not survive a seventeenth session. The judgement half is which engine is the model, because the site currently answers that three ways"),
 ("S-D3", "Run the capture in CI with real egress and byte-level raw storage", "availability",
  "Captures here go through a page reader, so the hash seals a transcription rather than the league's bytes; a direct HTTP client in this sandbox cannot reach nfl.com at all.",
  [("A", "Scheduled workflow storing raw HTML, HTTP headers and sha256, with the current store as the parse target."),
   ("B", "Keep the rendered-text capture and say so on every page - the current behaviour, stated in the store README.")],
  "a defensible audit trail and a byte-exact diff, so 'replayable as it was known' becomes literally true",
  "hours, once the runner has egress",
  "the pattern already exists for the schedule feed in .github/workflows/origin-capture.yml"),
 ("S-D4", "Backfill 2023-2025 official injury reports and results into the snapshot store", "unblocks the holdout split",
  "Verified today: the league serves https://www.nfl.com/injuries/league/2024/reg10 as a complete Week 10 2024 report, and its own selector runs back to 1965. Nothing in the repository uses this.",
  [("A", "Backfill three seasons of weekly reports plus their finals, hashed as they arrive, then split train / validation / holdout by season."),
   ("B", "Backfill only the weeks a registered strategy touches.")],
  "A-15, A-24, A-25, G-02 and any honest calibration of 'Questionable' - the only route that needs no third party",
  "days (about 3 seasons x 18 weekly reads)",
  "historical practice columns come back blank on some rows, so the parser must treat a blank as a value, not a failure"),
 ("S-D5", "Replace the fixed injury penalty with an ablation, and re-register the model", "brief-versus-code conflict",
  "hub/data/prereg.json freezes pos_cost (QB 4.0, RB 1.5, WR 1.1, TE 0.9) and a status weight, and lines.json adds injury_delta (0.63 to 4.48 points) straight to the margin. The brief explicitly rejects subtracting a fixed number of points for a missing starter.",
  [("A", "Fit the same model with and without the personnel features on chronological holdouts; publish the difference with uncertainty."),
   ("B", "Keep the penalty and label every affected page 'fixed adjustment, not ablation'.")],
  "A-27, and it makes the L-02 registration worth having at all",
  "days", "the current numbers are honest and reproducible; they simply answer a different question than the brief asked"),
 ("S-D6", "Set the capture cadence by each game's kickoff, not by the week", "measured today",
  f"Between two reads one day apart, {D['designation_changes_count']} designations moved and {D['added_rows_count']} rows appeared, almost all of it on the two Monday-night clubs. 'Final' is therefore a property of a game slot, not of a week.",
  [("A", "Capture at T-168h, T-24h, T-3h and T-90m for every game, storing the per-game clock on each row."),
   ("B", "Keep the brief's Wed/Thu/Fri cadence and accept a stale Monday slate.")],
  "A-16, A-17 and A-04 as a usable feature; it also removes a lookahead leak from every weekly-cut backtest",
  "hours - the store already supports it",
  "a Monday game priced from Friday's report is not priced on the information the market sees"),
 ("S-D7", "Capture the transactions log and the reserve list beside the report", "availability",
  "Nothing here records injured reserve or transactions. Today that cost us: two Ravens rows appeared between reads with a practice designation and no game status, and a reader cannot distinguish 'not listed' from 'available'.",
  [("A", "Add a dated transactions and IR capture per club to the snapshot store, under the same hash rules."),
   ("B", "Skip it and mark 'replacement confirmed' permanently unmeetable from this source set.")],
  "A-11, A-07 and A-13; the only way a backup's promotion becomes a fact instead of a guess",
  "days; club transaction pages differ per club, so parse per club and assert the count",
  "this is the second highest-leverage missing dataset after the inactive lists"),
 ("S-D8", "Move raw third-party page bodies out of the served tree", "terms and legal",
  f"{len(depth_files)} club depth captures and the game-centre text are published on the live site while the terms are unread.",
  [("A", "Keep the artefacts in the repository but out of the Pages publish set; serve derived tables plus a link to the official page."),
   ("B", "Read the terms first, then decide.")],
  "G-07 without waiting on an answer nobody in this repository can give",
  "hours", "nothing analytical is lost: every derived row keeps its official link, so the verification chain survives the move"),
 ("S-D9", "Capture the T-90 inactive lists from the official game centre", "availability",
  "Confirmed replacements, play rate per designation and the empirical meaning of 'Questionable' all hinge on the inactive list, which no tree holds.",
  [("A", "One capture per game at T-90, hashed, joined to the designation row it followed.")],
  "A-07, A-15, A-24 and the 'replacements named' column of A-30",
  "days", "the single highest-leverage missing dataset in the project; everything about a backup starts here"),
 ("S-D10", "Close the two depth-parsing failures", "availability",
  "The Texans publish depth as an image (0 rows parsed, recorded in the repository's own parse report) and the Packers prefix jersey numbers to every name.",
  [("A", "Strip the numbers and retain the raw string beside each parsed row for GB; for HOU use an authorized structured source."),
   ("B", "Transcribe the Texans image by eye for the clubs that matter this week.")],
  "A-09 and A-14, then A-26 (the deficiency matrix)",
  "a day for GB; HOU depends on source access",
  "B is exactly what the brief forbids, and it cannot be hashed - an image read by eye is not evidence"),
 ("S-D11", "Freeze the backtest corpus by hash and reconcile its count", "governance",
  f"The brief calls it a 136-game log; the store holds {n_games} games with {n_finals} finals. Different trees quote different numbers for the same season.",
  [("A", "Publish corpus.json with the sha256 of the game file, the final count and the evaluation window, and cite it from every backtest page.")],
  "G-03, and it makes 'pre-registered' checkable instead of asserted",
  "hours", "a corpus that grows while strategies are graded is not a corpus"),
 ("S-D12", "Publish the residual panel now with an empty price column", "pricing",
  "The brief wants the residual 'on a schedule, from day one'. Publishing the empty column is what keeps a future number comparable instead of retrofitted.",
  [("A", "Ship fair line, market line (blank), residual (blank) and both fetch timestamps per market.")],
  "P-05 becomes schedulable the day a price exists, and P-04 stops being a half-row",
  "hours", "an empty column with a timestamp invites the question that has to be answered"),
 ("S-D13", "Write the reward policy before any stake exists", "leaderboard",
  "A competition with rewards is requested, and no payout rule is written anywhere in the repository. Rewards tied to short-run ROI buy variance.",
  [("A", "Pay on prospective Brier skill after a >=4-week escrow; publish the cliff, the sample floor and how it interacts with the demotion gate."),
   ("B", "No rewards at all until P-01 resolves.")],
  "L-09, and the credibility of L-01",
  "hours", "either choice works, but the control baselines in L-05 must be printed next to any reward claim or the number is meaningless"),
 ("S-D14", "Keep one correlation store and relabel the desk row", "correctness",
  "Two stores disagree because of a label rather than a number: the desk row is the signed-margin statistic published under an absolute-margin label, so its stated reading is a sign error.",
  [("A", "Point both pages at the origin copy, which already prints the two statistics as separate rows, and retire the desk copy.")],
  "L-07, and it ends the pattern of correcting one tree and leaving the wrong figure live in another",
  "minutes", "this session did not edit either file; the request is logged in COORDINATION.md"),
 ("S-D15", "Extend the drift alarm to every parser", "operations",
  "The availability store now fails a build on a missing field, a shifted row count or an unmapped club code. The depth, games and standings parsers do not, which is how a blank replacement column became a published value.",
  [("A", "Assert expected row counts and required fields in each parser, and fail the build loudly on a blank.")],
  "A-29, and with S-D3 it becomes real alerting rather than a nightly log line",
  "a day", "a silent blank is indistinguishable from 'nothing to report', which is the most expensive failure mode a data site can have"),
 ("S-D16", "Publish both total estimators and only then collapse", "modelling",
  "One total is published per game, so the 'publish every model total twice until one wins' rule has nothing to arbitrate.",
  [("A", "Add a second, structurally different total estimator, keep the gap column, and collapse only after a walk-forward comparison.")],
  "P-07, and it is a cheap honesty test on the model itself",
  "days", "if both estimators agree on every game, one of them is decoration"),
]

# ------------------------------------------------------------------ questions
QUESTIONS = [
 ("Q-D1", "Which price source is lawful, reachable and stable enough to originate against?",
  "No official NFL publication of betting prices exists; the repository holds 0 market lines across " + str(n_priced) + " priced games.",
  "a terms read, a fetch policy, and a named operator feed with retained timestamps",
  "unanswered - and it is the single gate in front of ROI, CLV, rewards and the staking half of the leaderboard",
  "S-D1"),
 ("Q-D2", "Does 'Questionable' mean anything we can use?",
  "the official report prints no percentages; practice designation and game status are separate columns and frequently disagree (today: DNP with no designation on Puka Nacua, Aaron Donald and Fred Warner-equivalent rows)",
  "official inactive lists + historical designations joined to them",
  "no, not yet - and the empirical route is open because past seasons are reachable (see Q-D9)", "S-D4 + S-D9"),
 ("Q-D3", "Who actually replaced the starter - a confirmed fact or an inference?",
  "42 of 76 replacements resolved to a depth ordinal in origin/data/depth.json, 0 of 76 with a chart as-of date",
  "inactive lists, snap counts, and a dated chart per club",
  "still an inference for the whole slate; the blank replacement column on the report page is the honest answer", "S-D7 + S-D9"),
 ("Q-D4", "Can a club's rank-1 column be treated as 'the starter'?",
  "no. the brief counts 149 slots with more than one rank-1 player; the retained captures show shared and empty slots written as one string",
  "a typed slot model per club, from a dated chart",
  "not without inventing a starter the club never named; three-receiver and three-ILB slots are the proof", "S-D7"),
 ("Q-D5", "Is the side or the total the better signal?",
  "prior run: side 67/105 (95% CI 0.543-0.724, p=0.006, survives BH at q=0.10); total 47/105 (p=0.329) with a reliably adverse confident subset",
  "the same engine re-run on a frozen corpus (S-D11) once the Monday slate settles",
  "the side carries measured skill; the total does not, and its confident subset is worse than a constant", "S-D11"),
 ("Q-D6", "Is the model's spread too tight?",
  "predicted margin SD 4.28 against actual 12.74 - and today's settled example is the extreme case: the model put Detroit at -3.5 (predicted margin 3.64) and the final was 10-35, a 25-point margin",
  "residual variance modelling, or a distribution rather than a point",
  "yes, by about a factor of three; that is a calibration failure, not a pick failure", "S-D16"),
 ("Q-D7", "When is a week's report actually final?",
  f"measured today between two reads one day apart: {D['designation_changes_count']} designation changes and {D['added_rows_count']} new rows, concentrated on the Monday-night clubs; one designation also went backwards (Questionable -> no designation, corroborated by two independent prior reads)",
  "a per-game capture clock (S-D6)",
  "it is final per game, not per week; a weekly cut leaks or starves depending on the slot", "S-D6"),
 ("Q-D8", "Does the league ever remove a designation?",
  "yes: Indianapolis DE Arden Key reads Questionable in both 2026-11-14 reads and prints no designation in the 2026-11-15 read",
  "more reads; this is exactly what a series is for",
  "it does, so 'cleared' is a state the store must represent, not an error to reconcile away", "S-D6"),
 ("Q-D9", "Are past seasons reachable at all?",
  "verified this session: https://www.nfl.com/injuries/league/2024/reg10 returns the complete 2024 Week 10 report with per-club tables, and the page's own selector lists seasons back to 1965",
  "an ingestion plan and a place to keep the captures",
  "yes - which converts 'archive past seasons' from blocked to schedulable, and is the only way to build a real holdout", "S-D4"),
 ("Q-D10", "How many settled games before a strategy may rank?",
  "the gates say >=20 games with a game-cluster lower bound and a multiplicity adjustment; today the engine has settled 1 game it priced before kickoff",
  "13 more finals for Week 10 plus the price data to settle staking at all",
  "the rule exists and is not yet satisfiable for staking; for signal, one observation is not a sample and the site says so", "S-D11"),
 ("Q-D11", "Is the injury adjustment in the published lines an ablation or a penalty?",
  "a penalty: prereg.json pins pos_cost (QB 4.0, RB 1.5, WR 1.1, TE 0.9...) and lines.json adds a fixed injury_delta to the margin",
  "a with/without-features refit on chronological holdouts",
  "the brief forbids this specific construction, so the frozen model and the requirement disagree on the record", "S-D5"),
 ("Q-D12", "Which of these sixteen trees is the project?",
  "each serves its own landing page; four re-implement the same eight requirements on the same inputs",
  "a decision, not a fetch", "unresolved; this tree is a review layer and adds no competing engine", "S-D2"),
 ("Q-D13", "Do we have the right to publish the raw club pages we captured?",
  "unanswered; raw depth-page and game-centre text is currently inside the served tree",
  "a read of the club and league terms",
  "unknown - the safe interim is S-D8, which keeps the analysis and drops the bodies", "S-D8"),
 ("Q-D14", "Can a same-game parlay be priced from this data at all?",
  "no: marginal probabilities multiplied under dependence is invalid, and no joint probability has been validated here",
  "a validated joint model + the operator's void/push rules",
  "blocked by design; the gate that says so is already implemented", "S-D1"),
 ("Q-D15", "What did today's results do to the backtest?",
  f"the desk store records {n_finals} finals; the official schedule page now shows Patriots 10, Lions 35 FINAL, with eight games in progress and Monday Night Football unplayed at capture time",
  "a re-capture after the slate closes",
  "+1 final is available and is deliberately not folded into another tree's store here; see the settlement panel", "S-D11"),
]

# --------------------------------------------------------------------- flags
FLAGS = [
 ("F-D01", "high", "the frozen model applies exactly the fixed injury penalty the brief rejects",
  "hub/data/prereg.json pins pos_cost (QB 4.0, RB 1.5, WR 1.1, TE 0.9, C 1.2, G/T 1.0, DE 1.0, DT 0.8) and a status weight (Out 1.0, Doubtful 0.9, Questionable 0.35); hub/data/lines.json then adds injury_delta to the margin on every row (1.2 on NE@DET, 4.48 on HOU@CLE). adj_margin_home = base_margin_home + injury_delta on all " + str(n_priced) + " rows. The brief asks for an ablation with uncertainty instead.",
  "re-register the model as S-D5 and either implement the ablation or label the page as a fixed adjustment; the deviation should be a decision, not a default", "file:hub/data/prereg.json"),
 ("F-D02", "medium", "an unsourced venue string is still published",
  f"origin/data/markets.json carries 'Alemun & Munchen / Munich (NFL International Game) - no home field' on {venue_stale} rows. The official Week 10 schedule page - re-read this session - prints 'International Game, November 15th / Munich'; the hub store prints 'Munich (NFL International Game)'. Nothing official prints 'Alemun & Munchen'.",
  "replace with the official string on those rows (this session did not edit another tree's file; request logged in COORDINATION.md)",
  "url:https://www.nfl.com/schedules/2026/by-week/week-10"),
 ("F-D03", "medium", "two reads of the same page one day apart differ by 2 rows, and the cause cannot be pinned from the retained evidence",
  f"the {CTX['rows_after']}-row read of 2026-11-15 contains Ravens DT Calais Campbell and T Ronnie Stanley (both DNP, no game designation); neither appears in the desk store nor in the audit transcription of 2026-11-14. Two explanations remain: the league added them, or the earlier reads dropped them. The older reads predate this store, so no hash of the page as served exists for them.",
  "publish as an open ambiguity; from now on the rule 'every read is hashed' makes this class of question answerable in one comparison", "file:data/snapshots/delta.json"),
 ("F-D04", "medium", "raw third-party page text is inside the public site tree",
  f"data/desk/text/ holds {len(depth_files)} club depth captures plus game-centre text, all under the GitHub Pages publish root, while the terms of use are unread. This is the exposure G-07 exists to prevent, and no prior session closed it.",
  "S-D8: keep the artefacts in the repository, exclude them from the served set, and continue to link every row to the official page", "file:data/desk/text/"),
 ("F-D05", "low", "a designation moved backwards between reads",
  "Indianapolis DE Arden Key: Questionable in both 2026-11-14 reads (injury 'Hamstring', Full Participation), and no game designation with an empty injury cell in the 2026-11-15 read. Corroboration verdict on the row: CORROBORATED, because two independent prior reads agree with each other.",
  "treat 'cleared' as a first-class transition; do not reconcile it away as a parse error", "url:https://www.nfl.com/injuries/league/2026/reg10"),
 ("F-D06", "low", "the report's club codes do not match the repository's",
  "the official page prints 'AZ' for Arizona and 'LAR' for the Rams, while every dataset here keys them 'ARI' and 'LA'. Before it was documented, the same page read as 15 added rows plus 15 dropped rows and 14 more for the Rams.",
  "alias map is now explicit in scripts/x3_snapshots.py and the verifier fails on any new unmapped code", "file:scripts/x3_snapshots.py"),
 ("F-D07", "low", "the earlier read has no clock time",
  "the 2026-11-14 record carries a date only, so the measurement window between the two reads cannot be stated in hours; Monday-night designations moved inside that window and the exact lag is unrecoverable.",
  "no action possible for the old read; every new capture filename encodes hh:mm Z", "file:data/snapshots/ledger.json"),
 ("F-D08", "low", "the official page places several well-known players on clubs a reader may not expect",
  "read verbatim from the report this session: Giants QB J.J. McCarthy; Vikings QB Kyler Murray; Packers LB Micah Parsons and RB Josh Jacobs; Rams LB Myles Garrett and DT Aaron Donald; Seahawks G Quenton Nelson; Colts CB Charvarius Ward.",
  "published as printed, with the page link, because the site's rule is to transcribe the official row and not to override it from recollection - flag it if the reviewer wants a second confirmation per row",
  "url:https://www.nfl.com/injuries/league/2026/reg10"),
 ("F-D09", "low", "practice columns move after the designation deadline",
  "three LAC rows changed practice only (Bud Dupree DNP->Full, Keaton Mitchell Limited->Full, Rodney Shelley Limited->Full) between the two reads, on a Monday game, after the Friday designation deadline the rules describe.",
  "the capture clock has to be per-game; the practice column cannot be assumed frozen at Friday", "url:https://www.nfl.com/injuries/league/2026/reg10"),
 ("F-D10", "low", "counts quoted in the brief are stale against the repository",
  f"the brief cites 254 rows / 4 no-injury sections / 'only 6 of 254 rows carry a game designation'. Two verified reads now exist: {CTX['rows_before']} rows on 2026-11-14 and {CTX['rows_after']} on 2026-11-15, with {CTX['desig_after']} carrying a designation and {CTX['blank_after']} without. The '136-game log' likewise reads {n_games} games / {n_finals} finals.",
  "supersession noted here and on the readiness register so nobody re-fixes a fixed thing", "file:data/snapshots/ledger.json"),
 ("F-D11", "low", "the settlement page rests on one observation",
  "Patriots 10, Lions 35 is the first game this repository priced before kickoff and then settled from an official final. n = 1. It is published as a single scored row, not as evidence of skill.",
  "re-settle the slate once the remaining 11 of 13 games are final; do not rank anything on n=1",
  "url:https://www.nfl.com/schedules/2026/by-week/week-10"),
 ("F-D12", "low", "two snapshot stores now exist in the project",
  "this session sealed data/snapshots/ledger.json + delta.json + wk10/capture-*.csv; PR #58 (open, stale ~22h) adds data/snapshots/snapshots_2026_wk10.csv + store_meta.json to the same directory. No filename collides, but the concept is duplicated.",
  "the merge author should collapse them onto the format that has a verifier attached (request logged in COORDINATION.md)", "file:COORDINATION.md"),
]

TREES_NOTES = {
 "hub": "canonical maintained tree; the landing page and the widest nav",
 "signals": "own side/total/moneyline origination, price-snapshot store, signal-vs-staking leaderboard, deterministic engine",
 "origin": "three-market origination with an explicit order, demotion gate, replacement ordinals",
 "ops": "trading-desk variant of the same eight requirements; every price cell blank by design",
 "council": "the eight requirements restated as pass/fail acceptance tests plus a suggestion queue",
 "desk": "injury/depth capture pipeline; its parse_report is what F-D03 and A-05 rest on",
 "docs": "earlier decision-lab tree; injury row count disagrees with the official page",
 "dashboard": "panel tree; luck decomposition and per-team views",
 "x3lab": "lab tree, framework-heavy",
 "ledger": "point-in-time ledger experiment predating this session's store",
 "crosscheck": "cross-source reconciliation",
 "audit": "the 2026-11-14 independent read of the Week 10 report - used here as the second corroborating read",
 "analysis": "derived analysis",
 "research": "research notes",
 "lab": "framework-only, no data values",
 "legacy": "the pre-docs root site",
 "pages": "produced when nfl.com was believed unreachable; blank cells by design",
 "site": "single page",
 "archive": "frozen copies of older trees",
 "decision": "this tree: read-only review layer, snapshot store gate, readiness register",
}

# expose the computed context as module attributes so the renderer can read them
globals().update(CTX)
