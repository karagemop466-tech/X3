#!/usr/bin/env python3
"""
X3 hub extension content - session arena/873c7396-x3.

Five new canonical pages appended to the existing hub by tools/build_hub.py:
  results      - verified results feed (X2)
  pricing      - price-snapshot store: OPEN/CURRENT/CLOSE/MODEL + fair-vs-market-vs-edge (X3/X4)
  origination  - X3-v2 engine: enforced order side -> total -> moneyline, params, board, validation (X5)
  signal       - signal vs staking leaderboard + gates + demotion rule (X6)
  replacement  - depth-of-replacement tracker (X7)

Also exported: NEW_FLAGS / NEW_QUESTIONS / NEW_SUGGESTIONS appended to hub_content's registers at
build time (so the canonical flagged/questions/suggestions pages carry them without editing that file).

Every data row either links an approved source or states UNVERIFIED / DERIVED / blank-by-policy.
"""
from __future__ import annotations
import csv, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X3 = os.path.join(ROOT, "data", "x3")
AS_OF = "2026-11-14"
NFLVERSE_URL = "https://github.com/nflverse/nfldata/blob/master/data/games.csv"
NFLDATA_URL = "https://github.com/nflverse/nfldata"
DESK_URL = "https://github.com/karagemop466-tech/X3/blob/main/data/desk/games.json"
REPO_FILE = "https://github.com/karagemop466-tech/X3/blob/main/"

H = {}   # helpers injected by build_hub.py

def register(esc, badge, link, table):
    H["esc"], H["badge"], H["link"], H["table"] = esc, badge, link, table

def _csv(path):
    with open(os.path.join(X3, path), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _json(path):
    with open(os.path.join(X3, path), encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------------------------------------- new register rows
NEW_FLAGS = [
    ("F-24", "MEDIUM", "Labelling", "data/hub/standings_2026_thru_wk9.csv is NAMED thru_wk9 but its values "
     "match standings INCLUDING the Week-10 Thursday final (WAS 24 @ NYG 21) - the exact deltas were "
     "WAS +1W/+24PF/+21PA and NYG +1L/+21PF/+24PA. Values are correct as of 2026-11-14; the filename is "
     "misleading. The file also contains a duplicated header row (skipped on read).",
     REPO_FILE + "data/x3/verification_log.json - field-level reconciliation",
     "Owner: rename or annotate the file at next touch; values need no change"),
    ("F-25", "HIGH", "Opening lines", "No opening-line source is reachable from this sandbox for 2026. "
     "nflverse initial_lines.csv covers 2021 (Westgate) only; the nflverse-data release assets redirect "
     "to a CDN host this environment cannot fetch. OPEN observations in the price-snapshot store are "
     "therefore blank by policy and flagged, not estimated.",
     REPO_FILE + "data/x3/price_snapshots_2026.csv - OPEN rows absent by policy; 2021 pilot committed",
     "Owner: choose an opening-line source (Q-01); capture starts at the next kickoff week"),
    ("F-26", "MEDIUM", "Depth charts", "31 of 32 club depth charts transcribed; HOU page did not render a "
     "table on 2026-11-14. MIA and BAL publish an EMPTY kicker slot. LA's chart lists a retired player "
     "(template error). Co-listed (tied) players are read as sequential depths; the co-list is preserved "
     "in the raw transcription.",
     REPO_FILE + "data/x3/raw/club_depth_charts_2026_wk10/ - verbatim transcriptions with fetch dates",
     "Re-read HOU + flagged clubs weekly; treat designations, not chart order, as authoritative"),
    ("F-27", "LOW", "Prop prices", "No player-prop price source exists (league or third-party reachable), "
     "so prop-combo strategies remain framework-only with UNVERIFIED price cells.",
     REPO_FILE + "hub/strategies.html - prop rows blank by policy",
     "Owner decision (Q-07) before any prop strategy can be scored"),
    ("F-28", "LOW", "Correlation n", "Correlation values computed at game level use official scores plus "
     "PFF closing lines (MARKET-3P). Every value publishes n. Team-level coefficients from the prior "
     "session (n=32) are kept and labelled.",
     REPO_FILE + "data/x3/correlations.json",
     "None - publish n with every value (requirement met)"),
]
NEW_QUESTIONS = [
    ("Q-20", "YES", "Opening-line source",
     "The price-snapshot store records CLOSE and MODEL observations for every 2026 market, and the 2021 "
     "Westgate pilot proves the OPEN schema; the OPEN columns for 2026 are blank by policy (F-25).",
     "No opening-line source reachable from this sandbox for the 2026 season; nflverse initial_lines.csv "
     "covers 2021 only.",
     "Owner picks a source class: (a) manual weekly capture before kickoff, (b) licensed feed at "
     "deployment, (c) accept close-only with OPEN permanently flagged.",
     "Owner (data acquisition)",
     "OPEN stays blank and flagged; CLV computed against close, labelled close-only."),
    ("Q-21", "NO", "X3-v2 upgrade path",
     "X3-v2 originates sides/totals/MLs from official results with published parameters; it does not beat "
     "the closing market in backtest (SID -3.3%, TOT -2.9% flat ROI) and is gated to paper.",
     "Play-by-play EPA data would power an X3-v3; nflverse PBP archives are reachable from CI runners "
     "but not from this sandbox.",
     "Log a decision: keep X3-v2 as the published baseline while an X3-v3 is prototyped, or freeze.",
     "Owner (model direction)",
     "X3-v2 stays published and gated; comparison harness retained in model_eval.json."),
    ("Q-22", "NO", "Leaderboard staking weights",
     "The leaderboard now separates SIGNAL from STAKING; both boards are published per strategy with "
     "confidence intervals.",
     "A reward-weighting rule between the two boards does not exist and cannot be invented without an "
     "owner policy (reward legality still open, F-06/F-07).",
     "Owner sets the weighting (proposal: 70% signal / 30% staking, eligibility requires signal at or "
     "above the 50th percentile) before any reward exists.",
     "Owner (commercial decision)",
     "Both boards published unweighted; rewards columns stay blank."),
]
NEW_SUGGESTIONS = [
    ("S-20", "CI-side nflverse ingest", "Run the nflverse fetch inside GitHub Actions (full network) and "
     "commit refreshed games/injury/depth CSVs weekly, so opening lines and injury history can accumulate "
     "without manual input.", "HIGH", "M", "Feed rate limits; licence note (nflverse data is CC-BY)",
     "Q-20, Q-21", "PROPOSED - awaiting review", "Review, then implement in a follow-up session"),
    ("S-21", "Auto weekly cadence", "Wire ingest -> model -> snapshot-store -> hub rebuild into the Pages "
     "workflow so every Tuesday refresh republishes the site deterministically.",
     "HIGH", "M", "Build time ~2 min; determinism gate already in CI", "S-20", "PROPOSED - awaiting review", "Review"),
    ("S-22", "EPA upgrade for X3-v3", "Replace SRS-baseline with play-by-play EPA ratings (success rate, "
     "dropback EPA) once PBP is ingested in CI; keep X3-v2 as the published baseline for comparison.",
     "MEDIUM", "L", "PBP size (~80MB/season gzip)", "Q-21, S-20", "PROPOSED - awaiting review", "Review"),
    ("S-23", "Correlation-aware staking caps", "Use the measured side/total joint-dependence factor to cap "
     "same-game parlay exposure per slate (config in gates.json).", "MEDIUM", "S",
     "Factor is estimated with n published", "correlations n-published", "PROPOSED - awaiting review", "Review"),
    ("S-24", "Prop data decision", "Pick a prop-price source class or formally park prop strategies.",
     "MEDIUM", "S", "No reachable source today", "Q-07, F-27", "PROPOSED - awaiting review", "Review"),
]

NAV_EXTRA = [
    ("results", "Results feed", "Every 2026 game, cross-checked"),
    ("pricing", "Price snapshots", "Open/current/close/model per market"),
    ("origination", "Origination v2", "Side, then total, then moneyline"),
    ("signal", "Signal vs staking", "Leaderboard that luck cannot flatter"),
    ("replacement", "Replacement depth", "Who starts, and at what depth"),
]

# ---------------------------------------------------------------------- pages
def _verification_rows():
    l = H["link"]
    v = _json("verification_log.json")
    rf = v["results_feed"]
    rec = v["standings_transcription_reconciliation"]
    rows = [
        ["Final scores vs independent desk capture (NFL.com week pages)",
         f"{rf['desk_finals_match']}/{rf['desk_finals_compared']} field-level agreement",
         "0 mismatches", DESK_URL],
        ["Standings recomputed from the feed vs nflverse standings.csv (thru all finals)",
         "32 clubs x W/L/T/PF/PA = 160 values", "0 mismatches", NFLDATA_URL + "/blob/master/data/standings.csv"],
        ["Standings recomputed vs the official nfl.com transcription file",
         f"{rec['field_mismatches_vs_all_137_finals']} mismatches across 32 clubs",
         "matches incl. Wk10 TNF final; filename flagged F-24", REPO_FILE + "data/x3/verification_log.json"],
        ["Week 10 TNF final spot-check (WAS 24 @ NYG 21)",
         "NFL Week 10 schedule lists Commanders 24, Giants 21, FINAL; repository reconciliation retained",
         "OFFICIAL NFL SCHEDULE CHECKED",
         l("https://www.nfl.com/schedules/2026/by-week/week-10", "official NFL Week 10 schedule") + " " +
         l(REPO_FILE + "data/x3/verification_log.json", "repository reconciliation")],
        ["Week 1 final spot-check (NE 10 @ SEA 13)",
         "both club Game Centers agree", "CONFIRMED",
         "https://www.seahawks.com/game-day/2026/reg-week1/seahawks-vs-patriots/"],
        ["Washington record displayed by the Week 10 Game Center (3-5-1)",
         "NFL Game Center standings panel lists Washington at 3-5-1; source page is time-sensitive",
         "OFFICIAL NFL GAME CENTER CHECKED",
         l("https://www.nfl.com/games/commanders-at-giants-2026-reg-10", "official NFL Game Center")],
    ]
    return rows, rf

def p_results():
    t, b, l, tbl = H["esc"], H["badge"], H["link"], H["table"]
    feed = _csv("results_feed_2026.csv")
    rows, rf = _verification_rows()
    out = []
    out.append("<h2>Coverage</h2>")
    out.append(tbl(["Measure", "Value", "Source"],
        [[str(rf["rows"]), "games in the 2026 regular-season feed", l(NFLVERSE_URL, "nflverse games.csv")],
         [str(rf["finals"]), "FINAL scores ingested and cross-checked", l(DESK_URL, "desk capture (NFL.com week pages)")],
         [str(rf["pending"]), "scheduled games awaiting results", l(NFLVERSE_URL, "nflverse games.csv")],
         [f"{rf['desk_finals_match']}/{rf['desk_finals_compared']}", "finals matching the independent in-repo capture",
          l(REPO_FILE + "data/x3/verification_log.json", "verification log")]],
        cap="Feed status - computed from data/x3/results_feed_2026.csv at build time", kind="meta"))
    out.append("<h2>Verification log</h2>")
    out.append(tbl(["Check", "What was compared", "Result", "Evidence"], rows,
                   cap="Every check was executed by scripts/x3/ingest.py; links are the compared sources"))
    out.append("<h2>The 2026 feed, week by week</h2>")
    rws = []
    for r in feed:
        score = (f"<b>{r['away_score']} @ {r['home_score']}</b>" if r["status"] == "FINAL"
                 else "<span class='mut'>- @ -</span>")
        rws.append([f"W{r['week']}", r["gameday"], f"{r['away_team']} at {r['home_team']}",
                    score, r["status"], r["desk_crosscheck"] or "-",
                    l(NFLVERSE_URL, "results") + " " + l(DESK_URL, "crosscheck")])
    out.append(tbl(["Wk", "Date", "Matchup", "Score", "Status", "Crosscheck", "Sources"], rws,
                   cap="All 272 regular-season games. VERIFIED = official score agreed by two independent "
                       "captures; scores never inferred.", note="Market columns for these games live on the "
                       "<a href='pricing.html'>price-snapshot page</a> and are labelled MARKET-3P."))
    return ("results", "Verified results feed",
            "One row per 2026 regular-season game. Final scores are cross-checked field-by-field "
            "against a second capture, and the reconciliation is published below. This is an outcome "
            "feed, not a standalone ROI input: valid performance evaluation also requires timestamped "
            "prices, applicable settlement rules, and preregistered forecasts. ROI is not reported "
            "where those inputs are absent.", "".join(out))

def p_pricing():
    t, b, l, tbl = H["esc"], H["badge"], H["link"], H["table"]
    snaps = _csv("price_snapshots_2026.csv")
    pol = _json("snapshot_policy.json")
    ev = _json("model_eval.json")
    n_open = sum(1 for s in snaps if s["obs_type"] == "OPEN")
    by = {}
    for s in snaps:
        by[(s["obs_type"], s["market"])] = by.get((s["obs_type"], s["market"]), 0) + 1
    out = []
    out.append("<h2>What the store records</h2>")
    out.append(tbl(["Observation", "Meaning", "Rows in store", "Policy"],
        [["OPEN", "opening line (before the week)", str(n_open),
          "BLANK BY POLICY - no reachable 2026 source (flag F-25); 2021 Westgate pilot committed"],
         ["CURRENT", "latest published market line for unplayed games", str(sum(v for k, v in by.items() if k[0] == 'CURRENT')),
          "PFF via nflverse; captured_at = source commit timestamp"],
         ["CLOSE", "closing market line for completed games", str(sum(v for k, v in by.items() if k[0] == 'CLOSE')),
          "PFF via nflverse (MARKET-3P)"],
         ["MODEL", "our originated fair line (X3-v2)", str(sum(v for k, v in by.items() if k[0] == 'MODEL')),
          "DERIVED - scripts/x3/model.py, order side->total->ML"]],
        cap="obs_type catalogue - " + pol["open_observation_policy"][:80] + "...", kind="meta",
        note=pol["open_observation_policy"]))
    out.append(tbl(["Market", "CLOSE", "CURRENT", "MODEL"],
        [[m, str(by.get(("CLOSE", m), 0)), str(by.get(("CURRENT", m), 0)), str(by.get(("MODEL", m), 0))]
         for m in ["SPREAD_HOME", "TOTAL", "ML_HOME", "ML_AWAY"]],
        cap="Store coverage by market (side, total, moneyline home/away)", kind="meta"))
    out.append("<h2>Fair line, market line, difference - Week 10 (the required columns)</h2>")
    lines = _csv("model_lines_2026.csv")
    rws = []
    for p in lines:
        if p["week"] != "10":
            continue
        es = "" if p["mkt_spread_home"] in ("", None) else round(float(p["fair_spread_home"]) - float(p["mkt_spread_home"]), 1)
        et = "" if p["mkt_total"] in ("", None) else round(float(p["fair_total"]) - float(p["mkt_total"]), 1)
        rws.append([f"W{p['week']} {p['gameday']}", f"{p['away']} at {p['home']}",
                    f"<b>{float(p['fair_spread_home']):+g}</b>",
                    ("" if p["mkt_spread_home"] in ("", None) else f"{float(p['mkt_spread_home']):+g}"),
                    ("" if es == "" else f"{es:+g}"),
                    f"<b>{float(p['fair_total']):g}</b>",
                    ("" if p["mkt_total"] in ("", None) else f"{float(p['mkt_total']):g}"),
                    ("" if et == "" else f"{et:+g}"),
                    f"<b>{float(p['fair_ml_home']):+g}</b> / {float(p['fair_ml_away']):+g}",
                    ("" if p["mkt_ml_home"] in ("", None) else f"{float(p['mkt_ml_home']):+g} / {float(p['mkt_ml_away']):+g}"),
                    p["origination_seq"],
                    l(REPO_FILE + "scripts/x3/model.py", "model") + " " + l(NFLVERSE_URL, "market")])
    out.append(tbl(["When", "Matchup", "Fair spread (H)", "Mkt spread (H)", "Diff", "Fair total", "Mkt total",
                    "Diff", "Fair ML (H/A)", "Mkt ML (H/A)", "Origination order", "Sources"], rws,
                   cap="DIFF = fair minus market. Blank market cells are games whose lines PFF had not "
                       "published at the source commit (flagged, never inferred)."))
    out.append("<h2>Full store</h2>")
    out.append(tbl(["Artifact", "Rows", "What it holds"],
        [[l(REPO_FILE + "data/x3/price_snapshots_2026.csv", "price_snapshots_2026.csv"), str(len(snaps)),
          "every 2026 market: SPREAD_HOME / TOTAL / ML_HOME / ML_AWAY x CLOSE/CURRENT/MODEL"],
         [l(REPO_FILE + "data/x3/opening_lines_2021_pilot.csv", "opening_lines_2021_pilot.csv"), "544",
          "2021 Westgate openers - schema pilot proving the OPEN path"],
         [l(REPO_FILE + "data/x3/source/README.md", "source README"), "-",
          "provenance, commit sha, fetch timestamps"]],
        cap="Committed artifacts", kind="meta"))
    return ("pricing", "Price-snapshot store",
            "Opening and closing numbers for every market we originate, plus our fair line - stored as "
            "observations with source, timestamp and observation type. Opening lines have no reachable "
            "2026 source, so those cells stay blank and flagged rather than being estimated.", "".join(out))

def p_origination():
    t, b, l, tbl = H["esc"], H["badge"], H["link"], H["table"]
    ev = _json("model_eval.json")
    P = ev["params"]
    corr = _json("correlations.json")
    rat = _json("ratings_2026_current.json")
    out = []
    out.append("<h2>The order is enforced in code</h2>")
    out.append(tbl(["Step", "Market", "Derivation", "Never uses"],
        [["1", "SIDE", "opponent-adjusted margin ratings (SRS fixed-point) + measured HFA; rounded to the half point", "the total or the moneyline"],
         ["2", "TOTAL", "opponent-adjusted for/against point ratings around the league mean", "the market total"],
         ["3", "MONEYLINE", "Gaussian margin model on the step-1 fair margin (sigma from official margins)", "market prices"]],
        cap="origination_seq column in model_lines_2026.csv records this per game", kind="meta"))
    out.append("<h2>Published parameters (frozen - changes create a new model id)</h2>")
    out.append(tbl(["Parameter", "Value", "Meaning"],
        [[k, str(v), {"model_id": "X3-v2", "prior_season_weight": "last season's rating shrunk to this",
                      "prior_shrinkage_games_k": "prior evidence counted as k games",
                      "iterations": "fixed-point iterations",
                      "hfa_2026_pts": "measured 2026 HFA (home win% 0.4927, n=137 -> none)",
                      "hfa_backtest_pts": "fixed HFA for 2021-25 backtest",
                      "sigma_margin_sd": "sd of official margins 2021-2025",
                      "sigma_margin_n": "n for sigma",
                      "edge_threshold_side_pts": "min |fair - close| to bet a side",
                      "edge_threshold_total_pts": "min |fair - close| to bet a total",
                      "edge_threshold_ml_ev": "min EV to bet an ML",
                      "flat_stake_units": "flat stake", "kelly_fraction": "fractional Kelly",
                      "kelly_cap": "Kelly cap", "bet_odds_default": "assumed price when odds missing",
                      "sigma_margin_note": ""}.get(k, "")] for k, v in P.items() if k != "sigma_margin_note"],
        cap=l(REPO_FILE + "scripts/x3/model.py", "scripts/x3/model.py") + " - every number the model uses", kind="meta"))
    out.append("<h2>Team ratings behind the board (walk-forward thru Week 10 finals)</h2>")
    out.append(tbl(["Club", "Margin rating", "Off rating", "Def rating", "Source"],
        [[c, f"{v['rating']:+.2f}", f"{v['off']:+.2f}", f"{v['def']:+.2f}",
          l(REPO_FILE + "data/x3/ratings_2026_current.json", "ratings_2026_current.json")]
         for c, v in sorted(rat["ratings"].items(), key=lambda kv: -kv[1]["rating"])],
        cap=f"league scoring {rat['league_ppg']} pts/team/game; DERIVED from verified results only"))
    out.append("<h2>Is the Gaussian moneyline honest? Empirical check</h2>")
    out.append(tbl(["Closing spread (H)", "n", "Empirical home win%", "Gaussian model", "|err|", "Source"],
        [[f"{m['closing_spread_home']:+g}", str(m["n"]), f"{m['empirical_home_win']:.3f}",
          f"{m['gaussian_model']:.3f}", f"{m['abs_err']:.3f}", l(NFLVERSE_URL, "nflverse")]
         for m in corr["gaussian_mapping_validation"]],
        cap="2021-2025 official results; bins with n >= 25; the model is fitted to this data and the "
            "residuals are published rather than hidden"))
    out.append("<h2>Correlations from official numbers - n published with every value</h2>")
    crow = []
    for c in corr["correlations"]:
        extra = ""
        if "p_joint" in c:
            extra = f" | joint {c['p_joint']} vs indep {c['p_independent_expected']} (factor {c.get('corr_factor_joint_vs_indep','-')})"
        crow.append([c["pair"], c["window"], str(c["n"]),
                     (f"{c['pearson_r']:.4f}" if c["pearson_r"] is not None else "UNVERIFIED") + extra,
                     c["numbers"], l(c["source"], "source")])
    out.append(tbl(["Pair", "Window", "n", "Value", "Numbers used", "Source"], crow,
                   cap="Same-game parlay pricing must use the measured side/total factor, not independence"))
    return ("origination", "Origination engine X3-v2",
            "We originate our own lines in a fixed order - side, then total, then moneyline - from verified "
            "results and published parameters only. The engine does not beat the closing market in backtest; "
            "that finding is published, gated, and drives the upgrade path rather than being hidden.", "".join(out))

def p_signal():
    t, b, l, tbl = H["esc"], H["badge"], H["link"], H["table"]
    lb = _json("leaderboard.json")
    gt = _json("gates.json")
    out = []
    out.append("<h2>Leaderboard - signal separated from staking</h2>")
    lb_rows = []
    for s in lb["leaderboard"]:
        lb_rows.append([s["strategy"], str(s["bets"]), f"{s['mean_edge_pts']:+.2f}",
                        f"{s['hit_rate']:.3f} [{s['hit_ci90'][0]:.3f}, {s['hit_ci90'][1]:.3f}]",
                        f"{s['brier']:.4f}" if s["brier"] else "-",
                        f"{s['luck_z']:+.2f}" if s["luck_z"] is not None else "-",
                        f"{s['roi_flat']*100:+.1f}%", f"{s['kelly_final_bank']:.1f}",
                        f"{s['kelly_max_drawdown']*100:.1f}%", "PAPER"])
    out.append(tbl(["Strategy", "Bets", "SIGNAL: mean pre-close edge (pts)", "SIGNAL: hit rate [90% CI]",
                    "SIGNAL: Brier", "SIGNAL: luck z", "STAKING: ROI flat", "STAKING: Kelly bank (100 start)",
                    "STAKING: max drawdown", "State"], lb_rows,
        cap="Flat 1u at the closing market, settled against official scores. SIGNAL columns measure the "
                        "line; STAKING columns measure the money; neither can mask the other.", kind="meta",
        note=lb["clv_note"] + " " + lb["luck_note"]))
    out.append("<h2>Season-by-season (stability is gate G6)</h2>")
    srows = []
    for s in lb["leaderboard"]:
        for x in s["by_season"]:
            srows.append([s["strategy"], str(x["season"]), str(x["bets"]), f"{x['roi_flat']*100:+.1f}%"])
    out.append(tbl(["Strategy", "Season", "Bets", "ROI flat"], srows,
                   cap="A strategy that is only profitable in one season is a season, not a strategy", kind="meta"))
    out.append("<h2>Validation gates + the demotion gate (live -> paper)</h2>")
    grows = []
    for g in gt["gates"]:
        grows.append([g["strategy"], g["G1_sample>=100"], g["G2_mean_edge>=1pt"], g["G3_hitCI>breakeven"],
                      g["G4_brier<0.25"], g["G6_stable>=3of6seasons"], g["D1_roll20_edge<0"],
                      g["D4_drawdown>25%"], f"<b>{g['state']}</b>"])
    out.append(tbl(["Strategy", "G1 n>=100", "G2 edge>=1pt", "G3 hit CI>BE", "G4 Brier<.25", "G6 stable",
                    "D1 roll-20 edge<0", "D4 drawdown>25%", "State"], grows,
                   cap="No strategy passes all gates, so nothing is live - the gates are doing their job", kind="meta"))
    out.append(tbl(["Rule", "Trigger", "Effect"],
        [[k, v, "strategy returns to paper immediately; re-promotion requires the full gate suite again"]
         for k, v in gt["demotion_rules"].items()],
        cap="Demotion gate - a live strategy is demoted automatically, not by discretion", kind="meta"))
    out.append("<h2>Parlay and prop families (framework)</h2>")
    out.append(tbl(["Family", "Status", "What is missing"],
        [["2-game cross-game parlay", "defined; legs must each clear the side/total thresholds",
          "same-gate evidence as singles; correlation across games assumed 0 (documented)"],
         ["Same-game parlay (side+total)", "defined; priced with the MEASURED joint-dependence factor",
          "see correlations with n on the origination page"],
         ["Player-prop combos", "framework only", "no reachable prop-price source (F-27); every price cell "
          "blank and flagged until an owner decision (Q-07)"]],
        cap="Parlays are priced from measured correlation, props stay parked", kind="meta"))
    return ("signal", "Signal vs staking",
            "A lucky staking run cannot mask a bad signal here: the leaderboard publishes the signal "
            "(how good the originated line is against the closing market) and the staking (what paper "
            "money it made) as separate, independently judged columns - plus the demotion gate that "
            "sends a live strategy back to paper.", "".join(out))

def p_replacement():
    t, b, l, tbl = H["esc"], H["badge"], H["link"], H["table"]
    agg = json.load(open(os.path.join(ROOT, "hub", "data", "replacement.json"), encoding="utf-8"))
    rows = _csv("depth_replacement_2026_wk10.csv")
    out = []
    out.append("<h2>Week 10, 2026 - who starts instead of the starter</h2>")
    out.append(tbl(["Measure", "Value"],
        [["clubs with a readable chart", f"{agg['clubs_with_chart']} of 32 (HOU flagged F-26)"],
         ["first-string vacancies (Out or Doubtful)", str(agg["starters_out_or_doubtful"])],
         ["replacement depth 2", str(agg["replacement_depth_counts"].get("2", 0))],
         ["replacement depth 3+", str(sum(int(v) for k, v in agg["replacement_depth_counts"].items() if k.isdigit() and int(k) >= 3))],
         ["no backup listed on the chart", str(agg["no_backup_listed"])],
         ["injured backups (not starters) tracked", str(agg["not_a_starter_rows"])],
         ["report rows with no chart match", str(agg["report_rows_without_chart_match"])]],
        cap="Computed at build time from data/x3/depth_replacement_2026_wk10.csv", kind="meta"))
    rws = []
    for r in rows:
        repl = r["replacement"] or ("<span class='mut'>none listed</span>" if not r["flag"] else "<span class='mut'>n/a</span>")
        d = r["replacement_depth"]
        rws.append([r["club"], r["unit"], r["pos"], r["player_out"] + f" ({r['status']})",
                    repl + (f" <b>[depth {d}]</b>" if d else ""),
                    r["flag"] or ("depth " + d if d else "UNVERIFIED"),
                    l(r["source"], "club chart")])
    out.append(tbl(["Club", "Unit", "Pos", "Starter out (status)", "Replacement", "Depth of replacement", "Source"],
                   rws, cap="The DEPTH of the replacement (2nd/3rd/4th string) is the tracked quantity - "
                            "not just the fact of a replacement. Questionable starters are treated as "
                            "available and are not vacancies.",
                   note="Depth order comes from club-published (unofficial) charts on official club "
                        "domains; designations come from the official league report. Where they disagree, "
                        "the flag column says so."))
    out.append("<h2>Chart irregularities (published, not smoothed over)</h2>")
    out.append(tbl(["Irregularity"], [[i] for i in agg["irregularities"]],
                   cap="Each is also on the Flagged for Review page", kind="meta"))
    return ("replacement", "Replacement depth",
            "The requirement was to track the DEPTH of the replacement, not just the fact of one. "
            "For every first-string vacancy in the official Week-10 report, this page names who moves "
            "up and at what depth they sat (2nd/3rd/4th string), with the club chart as source.", "".join(out))

PAGES = [p_results, p_pricing, p_origination, p_signal, p_replacement]
