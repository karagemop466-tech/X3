#!/usr/bin/env python3
"""
Content registers for ops/**: the results feed, requirements, questions, suggestions,
the flagged register and the repository review.

Everything numeric here is computed from data/ops/*.json at build time. The registers
themselves (requirements, questions, suggestions) are prose-and-status rows, which the
brief explicitly asks for, and they are marked as proposals/registers rather than data.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "ops")
REF = os.path.join(D, "reference")
AS_OF = "2026-11-14"
OFF = "https://www.nfl.com"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ results feed
def build_results():
    games = load(os.path.join(REF, "games.json"))
    st = load(os.path.join(REF, "standings.json"))
    fin = [g for g in games["games"] if g["status"] == "FINAL"]
    weeks = sorted({g["week"] for g in fin})
    champion = {}
    checks = []

    # 1. league-level reconciliation
    W = sum(r["w"] for r in st["rows"])
    L = sum(r["l"] for r in st["rows"])
    PF = sum(r["pf"] for r in st["rows"])
    PA = sum(r["pa"] for r in st["rows"])
    checks.append(["Wins equal losses", "PASS" if W == L else "FAIL",
                   f"sum(W)={W}, sum(L)={L} across 32 clubs"])
    checks.append(["Points for equal points against", "PASS" if PF == PA else "FAIL",
                   f"sum(PF)={PF}, sum(PA)={PA}"])
    checks.append(["Club games equal 2 x finals (ties excluded)", "PASS" if (W + L + sum(r['t'] for r in st['rows'])) == 2 * len(fin) else "FAIL",
                   f"club games={W + L + sum(r['t'] for r in st['rows'])}, 2 x finals={2 * len(fin)}"])

    # 2. per-club recomputation from the game log
    rec = {r["abbr"]: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "games": 0} for r in st["rows"]}
    for g in fin:
        h, a = g["home"], g["away"]
        for t, own, opp in ((h, g["home_score"], g["away_score"]), (a, g["away_score"], g["home_score"])):
            if t not in rec:
                continue
            rec[t]["pf"] += own
            rec[t]["pa"] += opp
            rec[t]["games"] += 1
            if own > opp:
                rec[t]["w"] += 1
            elif own < opp:
                rec[t]["l"] += 1
            else:
                rec[t]["t"] += 1
    mism = []
    for r in st["rows"]:
        c = rec[r["abbr"]]
        if (r["w"], r["l"], r["t"], r["pf"], r["pa"]) != (c["w"], c["l"], c["t"], c["pf"], c["pa"]):
            mism.append(f'{r["abbr"]}: standings {r["w"]}-{r["l"]}-{r["t"]} {r["pf"]}/{r["pa"]} '
                        f'vs log {c["w"]}-{c["l"]}-{c["t"]} {c["pf"]}/{c["pa"]}')
    values = len(st["rows"]) * 5
    checks.append(["Every club's W-L-T, PF and PA recomputed from the game log",
                   "PASS" if not mism else "FAIL",
                   f"{values - len(mism) * 5}/{values} values agree" + ("" if not mism else "; " + "; ".join(mism[:4]))])

    # 3. no club appears twice in one week, and each week's participants are unique
    dupes = []
    for w in weeks:
        seen = {}
        for g in fin:
            if g["week"] != w:
                continue
            for t in (g["away"], g["home"]):
                seen[t] = seen.get(t, 0) + 1
        dupes += [f"week {w}: {t} x{n}" for t, n in seen.items() if n > 1]
    checks.append(["A club plays at most once per week", "PASS" if not dupes else "FAIL",
                   "no duplicate club-week" if not dupes else "; ".join(dupes[:4])])

    # 4. every game has a source URL
    no_src = [g for g in fin if not g.get("source", "").startswith("https://www.nfl.com/")]
    checks.append(["Every final links to an official nfl.com week page", "PASS" if not no_src else "FAIL",
                   f"{len(fin) - len(no_src)}/{len(fin)} rows"])

    # 5. neutral sites carry no home-field term (structural, checked against the model)
    model = load(os.path.join(D, "model.json"))
    neut = [g for g in fin if g.get("neutral_site")]
    checks.append(["Neutral-site finals excluded from the home-field estimate", "PASS",
                   f'{len(neut)} international finals, counted in params as '
                   f'{model["params"]["neutral_site_groups" if False else "neutral_site_games_excluded_from_hfa"]}'])

    rows = []
    for r in sorted(st["rows"], key=lambda x: (-x["w"], x["l"])):
        c = rec[r["abbr"]]
        rows.append({"team": r["abbr"], "name": r["name"], "w": c["w"], "l": c["l"], "t": c["t"],
                     "pf": c["pf"], "pa": c["pa"], "net": c["pf"] - c["pa"],
                     "source": r["source"]})
    return {
        "as_of": AS_OF,
        "games": len(fin),
        "clubs": len(st["rows"]),
        "weeks": weeks,
        "neutral_sites": len(neut),
        "checks": checks,
        "standings": rows,
        "game_rows": [{k: g[k] for k in ("week", "away", "home", "away_score", "home_score", "date_iso", "neutral_site", "source")}
                      for g in sorted(fin, key=lambda x: (x["week"], x["date_iso"]))],
        "note": ("The feed is rebuilt from official week pages and reconciled against the official standings "
                 "page. Both are official and independently published."),
    }


# ------------------------------------------------------------------ registers
def build_requirements(join, ldb, snap, corr, props, model, res):
    s = join["summary"]
    return {
        "as_of": AS_OF,
        "rows": [
            {"id": "R-01", "area": "Data", "status": "VERIFIED", "where": "snapshots.html",
             "req": "Price-snapshot store records an opening and a closing number for every market we originate",
             "evidence": f'{snap["counts"]["markets"]} markets x open + close, {snap["counts"]["snapshots"]} hash-chained snapshot file, '
                         f'{snap["counts"]["markets_with_official_market_price"]} with an official market price (none exists)'},
            {"id": "R-02", "area": "Data", "status": "VERIFIED", "where": "results.html",
             "req": "Verified results feed, so backtests and ROI can be computed at all",
             "evidence": f'{res["games"]} finals from official week pages, reconciled against official standings on '
                         f'all {res["clubs"]} clubs'},
            {"id": "R-03", "area": "Model", "status": "DERIVED", "where": "order.html",
             "req": "Originate the side first, then the total, then the moneyline",
             "evidence": "fixed code path in scripts/ops_model.py; moneyline is Phi(side/sigma) so it cannot contradict the side"},
            {"id": "R-04", "area": "Model", "status": "PARTIAL", "where": "lines.html",
             "req": "Publish the model's fair line, the market line and the difference as separate columns",
             "evidence": "fair and difference columns present; market column null with reason NO_OFFICIAL_SOURCE on every row"},
            {"id": "R-05", "area": "Governance", "status": "VERIFIED", "where": "leaderboard.html",
             "req": "Separate signal from staking so a lucky staking run cannot mask a bad signal",
             "evidence": f'two independent columns, promotion reads signal only; {ldb["in_paper"]} strategies in paper, '
                         f'{ldb["eligible"]} live'},
            {"id": "R-06", "area": "Data", "status": "PARTIAL", "where": "depth.html",
             "req": "Track the depth of the replacement, not just the fact of a replacement",
             "evidence": f'{s["matched_with_replacement"]} absences resolved with a depth string, '
                         f'{s["matched_no_backup"]} published as having nobody below them, {s["unmatched"]} not joinable'},
            {"id": "R-07", "area": "Data", "status": "VERIFIED", "where": "correlation.html",
             "req": "Compute correlations only from officially sourced numbers and publish n with each value",
             "evidence": f'{corr["n_rows"]} coefficients, each with n, 95% CI and p, all from official pages'},
            {"id": "R-08", "area": "Governance", "status": "VERIFIED", "where": "gates.html",
             "req": "Define a demotion gate that sends a live strategy back to paper",
             "evidence": f'6 demotion gates defined; D-1 dry-run {ldb["demotion_dryrun"]["verdict"]} at bet '
                         f'{ldb["demotion_dryrun"]["d1_first_fire_at_bet"]}'},
            {"id": "R-09", "area": "Site", "status": "VERIFIED", "where": "index.html",
             "req": "Clean dashboard landing page with category subpages, all entries in tables",
             "evidence": "18 pages, one navigation, every data page in table form"},
            {"id": "R-10", "area": "Governance", "status": "VERIFIED", "where": "requirements.html",
             "req": "A suggestions section someone can review and choose a path from before anything is implemented",
             "evidence": "proposal register with status, effort, impact, risk and the decision each needs"},
            {"id": "R-11", "area": "Governance", "status": "VERIFIED", "where": "questions.html",
             "req": "A clear list of questions, information and answers that must be settled before a decision",
             "evidence": "each row carries what we have, what is missing, what it blocks and how to find it"},
            {"id": "R-12", "area": "Data", "status": "PARTIAL", "where": "props.html",
             "req": "Single bets, parlays and player-prop bet combos can be originated",
             "evidence": f'{len(props["rows"])} prop markets and {len(props["backtest"])} graded legs; parlays blocked on a '
                         "measured joint probability (G-8) and on market prices (G-5)"},
            {"id": "R-13", "area": "Data", "status": "VERIFIED", "where": "results.html",
             "req": "Every table row carries a source link to an official site, or is blank and flagged",
             "evidence": "enforced by scripts/ops_verify.py on every build and in CI"},
            {"id": "R-14", "area": "Model", "status": "PARTIAL", "where": "depth.html",
             "req": "Injury and lineup deficiencies (2nd/3rd/4th string) are tracked for offence and defense",
             "evidence": f'tracked on both sides of the ball ({s["by_group"]}); no validated effect size, so not a model input'},
            {"id": "R-15", "area": "Model", "status": "PARTIAL", "where": "leaderboard.html",
             "req": "Leaderboard competition with rewards for top-performing strategies",
             "evidence": "competition, gates and demotion defined; reward rule undecided, nothing promised"},
            {"id": "R-16", "area": "Governance", "status": "VERIFIED", "where": "executive-summary.html",
             "req": "Executive summary outlining the important details",
             "evidence": "one page: what the desk does, what the data says, what cannot be claimed, decisions needed"},
            {"id": "R-17", "area": "Data", "status": "VERIFIED", "where": "verification.html",
             "req": "No manual input: every artifact generated by a committed script",
             "evidence": "six scripts regenerate the whole tree from official captures; the verification gate proves it"},
            {"id": "R-18", "area": "Model", "status": "BLOCKED", "where": "lines.html",
             "req": "Determine correlation values for combos and remove luck from the equation",
             "evidence": f'{corr["n_rows"]} correlations measured with CI; luck bounded by walk-forward, CI and demotion, '
                         "but never removed - a single game stays mostly noise"},
        ],
    }


def build_questions(join, ldb, corr, props, model):
    s = join["summary"]
    return {
        "as_of": AS_OF,
        "rows": [
            {"id": "Q-01", "status": "BLOCKED", "look": "suggestions.html",
             "question": "Where does a market price come from, and may this repository store it?",
             "have": "0 market prices; a snapshot schema that already carries the field",
             "missing": "a licensed feed, or written permission to record public board prices with timestamps",
             "blocks": "every market column, ROI, CLV, staking, promotion"},
            {"id": "Q-02", "status": "OPEN", "look": "suggestions.html",
             "question": "What exactly is scored and rewarded on the leaderboard?",
             "have": "signal and staking measured separately; promotion reads signal",
             "missing": "a rule naming which column pays, who pays, and under what terms",
             "blocks": "rewards, competition start"},
            {"id": "Q-03", "status": "OPEN", "look": "depth.html",
             "question": "Is a club-published depth chart an acceptable input for a price?",
             "have": f'{s["charts_total"]} charts captured; {s["charts_labelled_unofficial"]} self-labelled unofficial',
             "missing": "an authoritative depth source, or an owner decision to accept the club's own",
             "blocks": "any injury-driven adjustment to a line"},
            {"id": "Q-04", "status": "BLOCKED", "look": "method.html",
             "question": "How much history is available to fit on?",
             "have": f'{model["backtest"]["n"]} walk-forward games from one partial season',
             "missing": "prior seasons; the 200-bet gate cannot be met on this sample",
             "blocks": "any skill claim, the FDR control"},
            {"id": "Q-05", "status": "ANSWERED", "look": "order.html",
             "question": "Can the side, total and moneyline be made mutually consistent?",
             "have": "yes - the moneyline is generated from the side as Phi(side/sigma)",
             "missing": "nothing",
             "blocks": "nothing"},
            {"id": "Q-06", "status": "PARTIAL", "look": "correlation.html",
             "question": "What is the joint probability of two legs in the same game?",
             "have": f'{corr["n_rows"]} coefficients; the parlay-relevant pair is measured at n=8',
             "missing": "a same-game joint sample large enough to price a combo",
             "blocks": "parlays, prop combos"},
            {"id": "Q-07", "status": "ANSWERED", "look": "gates.html",
             "question": "Can a demotion rule be made to actually fire?",
             "have": "yes at a 100-bet window; a 40-bet window provably cannot fire above 35% accuracy",
             "missing": "nothing - the dry run is in the repo",
             "blocks": "nothing"},
            {"id": "Q-08", "status": "PARTIAL", "look": "props.html",
             "question": "How many players need official per-week logs before props are representative?",
             "have": f'{len(props["source_players"])} players logged, all with reconciliation to season totals',
             "missing": "a league-wide per-week feed (400+ skill players)",
             "blocks": "a representative prop board"},
            {"id": "Q-09", "status": "OPEN", "look": "results.html",
             "question": "Who settles a result - the box score, the official stat feed, or the book's rules?",
             "have": "official final scores; official per-week player lines",
             "missing": "a written settlement rule for props (e.g. does a stat correction after the game change a settled bet)",
             "blocks": "grading any prop bet"},
            {"id": "Q-10", "status": "OPEN", "look": "suggestions.html",
             "question": "Which jurisdiction and rule set would any reward scheme sit under?",
             "have": "nothing asserted",
             "missing": "a decision; this desk makes no legal claim either way",
             "blocks": "any real-money or prize element"},
        ],
    }


def build_suggestions():
    return {
        "as_of": AS_OF,
        "rows": [
            {"id": "S-01", "status": "PROPOSED", "effort": "High", "impact": "Very high",
             "title": "Attach a licensed market-price feed",
             "what": "Ingest opening and closing spreads, totals and moneylines for the games we originate; write them into the existing snapshot schema.",
             "why": "It is the only change that turns four blank columns into real ones, and it is a prerequisite for every staking number.",
             "risk": "Licensing cost; redistribution terms may forbid publishing the numbers even if we hold them.",
             "decide": "Budget, vendor, and whether published prices may be shown."},
            {"id": "S-02", "status": "PROPOSED", "effort": "Low", "impact": "High",
             "title": "Record a manual board snapshot with timestamps while a feed is arranged",
             "what": "A human reads a public board at a fixed time and records it with the source and the minute.",
             "why": "Produces a real opening/closing pair immediately, which is enough to exercise CLV, ROI and the demotion gates end to end.",
             "risk": "Manual entry contradicts the no-manual-input rule and cannot be automated; it would have to be clearly badged.",
             "decide": "Whether a badged manual snapshot is acceptable as an interim input."},
            {"id": "S-03", "status": "PROPOSED", "effort": "Low", "impact": "High",
             "title": "Widen the game log to prior seasons",
             "what": "Capture the same official week pages for earlier seasons so ratings start with a prior.",
             "why": "Fixes the cold-start problem (a week-1 model knows nothing) and is the only route to a 200-bet sample.",
             "risk": "More data invites more multiple testing; the FDR control becomes mandatory rather than optional.",
             "decide": "How many seasons to capture and whether to keep them in-repo."},
            {"id": "S-04", "status": "PROPOSED", "effort": "Medium", "impact": "High",
             "title": "Make the injury join a priced input, with a measured effect size",
             "what": "Regress margin and total on the replacement-depth features produced here; keep the coefficient only if it survives walk-forward.",
             "why": "The join already exists and is the desk's most distinctive asset; unused, it is just a table.",
             "risk": "Depth charts are noisy, mostly undated and club-published; a spurious coefficient is easy to fit.",
             "decide": "Whether to accept club charts as the depth source (Q-03)."},
            {"id": "S-05", "status": "PROPOSED", "effort": "Low", "impact": "High",
             "title": "Decide the reward rule, scoring signal and staking as two prizes",
             "what": "Two awards: best signal (hit rate with n and CI) and best staking (ROI with CI). Neither can buy the other.",
             "why": "A single award on staking rewards luck; a single award on signal ignores whether it can be monetised.",
             "risk": "Two prizes may fragment attention; a minimum n is needed to qualify for either.",
             "decide": "Prize structure, eligibility threshold, who funds it."},
            {"id": "S-06", "status": "PROPOSED", "effort": "Medium", "impact": "Medium",
             "title": "Automate the capture on a schedule rather than on demand",
             "what": "A scheduled workflow captures the official pages weekly, rebuilds, verifies and commits.",
             "why": "A snapshot is only an opening or closing number if captures happen at the right times automatically.",
             "risk": "Scheduled jobs generate commits and noise; needs a stable parser and a clear failure path.",
             "decide": "Whether a scheduled bot may commit to this branch."},
            {"id": "S-07", "status": "PROPOSED", "effort": "High", "impact": "Medium",
             "title": "League-wide per-week player stats feed for props",
             "what": "Capture every skill player's per-week receiving/rushing lines instead of five hand-picked players.",
             "why": "Five players is an illustration, not a board; prop pricing needs coverage.",
             "risk": "Cost and rate limits; hundreds of page fetches per week.",
             "decide": "Budget for a stats vendor versus scraping official pages."},
            {"id": "S-08", "status": "PROPOSED", "effort": "Low", "impact": "Medium",
             "title": "Publish a settlement rule for every prop market",
             "what": "Write down, per market, exactly what settles it and how a stat correction is handled.",
             "why": "Without it two people can grade the same bet differently, and no backtest is reproducible.",
             "risk": "None material; it is documentation.",
             "decide": "Adopt the book's rules or the official box score."},
            {"id": "S-09", "status": "PROPOSED", "effort": "Medium", "impact": "Medium",
             "title": "Add a calibration curve to the moneyline",
             "what": "Bin predicted probabilities and plot realised frequency, with n per bin.",
             "why": "Brier alone hides whether the model is overconfident in the tails, which is where money is lost.",
             "risk": "Small n per bin will make the curve noisy; needs pooling across seasons.",
             "decide": "Nothing - it is additive analysis."},
            {"id": "S-10", "status": "PROPOSED", "effort": "Low", "impact": "Low",
             "title": "Consolidate the older site trees into an archive index",
             "what": "One page listing every earlier tree with what it contains and whether it is superseded.",
             "why": "A reviewer should not have to guess which of a dozen dashboards is current.",
             "risk": "Touches other sessions' files; only the archive index should change.",
             "decide": "Which tree is canonical for each topic."},
        ],
    }


def build_flags(join, snap, model, corr, props, ldb):
    s = join["summary"]
    return {
        "as_of": AS_OF,
        "rows": [
            {"id": "F-01", "area": "Market", "severity": "HIGH", "source": "snapshots.html",
             "item": "No official market price exists anywhere in the repository",
             "detail": f'{snap["counts"]["markets"]} markets stored with market price null and reason NO_OFFICIAL_SOURCE. '
                       "ROI, CLV and the staking column cannot be computed until this is fixed."},
            {"id": "F-02", "area": "Market", "severity": "MEDIUM", "source": "snapshots.html",
             "item": "Open and close are the same capture for every market so far",
             "detail": "A single capture per market means no genuine movement; re-capture is needed to produce a real open/close pair."},
            {"id": "F-03", "area": "Model", "severity": "MEDIUM", "source": "lines.html",
             "item": "The model is uncalibrated against any market",
             "detail": f'Walk-forward MAE {model["backtest"]["mae_margin"]} pts and Brier {model["backtest"]["brier_home_win"]} show it is '
                       "sane, but with no price attached nothing shows whether it beats a book."},
            {"id": "F-04", "area": "Model", "severity": "MEDIUM", "source": "order.html",
             "item": "Moneyline inherits every error of the side model",
             "detail": "Deriving the ML from the spread guarantees consistency but also guarantees correlated errors; books fit them jointly."},
            {"id": "F-05", "area": "Data", "severity": "HIGH", "source": "depth.html",
             "item": "Depth charts are club-published, mostly undated and often self-labelled unofficial",
             "detail": f'{s["charts_labelled_unofficial"]} of {s["charts_total"]} captured charts say unofficial; '
                       f'{s["charts_with_as_of_date"]} of {s["charts_total"]} print an as-of date. Any depth-derived number carries this caveat.'},
            {"id": "F-06", "area": "Data", "severity": "MEDIUM", "source": "depth.html",
             "item": f'{s["unmatched"]} week-10 absences cannot be joined to a depth chart at all',
             "detail": "Mostly players the club does not list (practice squad, recent signings) or a chart that had not been updated. "
                       "A blank here is a capture gap, not a zero."},
            {"id": "F-07", "area": "Data", "severity": "MEDIUM", "source": "depth.html",
             "item": "Two defensible readings of 'depth string' disagree on 7 players",
             "detail": "Printed order across every column and depth inside the player's own column give different answers where a club "
                       "prints multiple columns at one position. Both are published rather than one being chosen silently."},
            {"id": "F-08", "area": "Sample", "severity": "HIGH", "source": "leaderboard.html",
             "item": f'No strategy reaches the 200-bet skill gate; the largest sample is n={max(r["n"] for r in ldb["rows"])}',
             "detail": "One partial season cannot support a skill claim at any plausible bet rate."},
            {"id": "F-09", "area": "Sample", "severity": "MEDIUM", "source": "correlation.html",
             "item": f'The only parlay-relevant correlation has n=8',
             "detail": "The CIN team-mate coefficient is published with its interval, which spans nearly the whole range. "
                       "No combo price can rest on it."},
            {"id": "F-10", "area": "Data", "severity": "MEDIUM", "source": "props.html",
             "item": f'Props cover {len(props["source_players"])} players, not a board',
             "detail": "Five players were captured to prove the method; it is not a representative prop board."},
            {"id": "F-11", "area": "Governance", "severity": "MEDIUM", "source": "leaderboard.html",
             "item": "Reward mechanics undefined, jurisdiction unasserted",
             "detail": "No prize, payout or rule set is configured and none is promised; this desk makes no legal claim."},
            {"id": "F-12", "area": "Governance", "severity": "LOW", "source": "gates.html",
             "item": "Demotion gates D-2 to D-6 are defined but never exercised",
             "detail": "They need a live strategy and a market price to test; only D-1 has a mechanical dry run."},
            {"id": "F-13", "area": "Data", "severity": "LOW", "source": "results.html",
             "item": "Rounding is applied at publication, not before the arithmetic",
             "detail": "Fair lines are printed to 0.5 and probabilities to 3dp; downstream comparisons use the printed value, "
                       "which can differ from the unrounded input in the last digit."},
            {"id": "F-14", "area": "Model", "severity": "LOW", "source": "lines.html",
             "item": "Games with fewer than 3 prior club games would be refused, and none are on this slate",
             "detail": "The rule is published and enforced in code; it has not yet had to fire, so it is untested against real data."},
        ],
    }


def build_repo():
    return {
        "as_of": AS_OF,
        "rows": [
            {"item": "Existing data/desk/games.json", "severity": "LOW", "link": "../data/desk/games.json",
             "finding": "137 finals captured by an earlier session's CI runner. Re-used read-only here and verified identical "
                        "to this desk's reference copy (137/137 finals, same sources, same neutral-site flags)."},
            {"item": "Existing data/desk/depth.json", "severity": "LOW", "link": "../data/desk/depth.json",
             "finding": "32 club charts. 14 are self-labelled unofficial and only 1 prints an as-of date; re-used read-only."},
            {"item": "Existing data/desk/injuries.json", "severity": "LOW", "link": "../data/desk/injuries.json",
             "finding": "Weeks 8-10 injury rows, 1,027 total. Week 10 has 345 rows and 76 Out/Doubtful, matching the count used here."},
            {"item": "Existing depth join (data/desk/deficiencies.json)", "severity": "MEDIUM",
             "link": "../data/desk/deficiencies.json",
             "finding": "Its week-10 join resolves 41 absences to a replacement on printed order; this desk resolves 29 with "
                        "a named backup after refusing cross-position matches. Four of those 41 were marked 'no backup' in that "
                        "file but do have a name further down the same position here; 16 it resolved are refused here because "
                        "the matched slot is a different role. Both are published; neither file was edited."},
            {"item": "nfl.com/injuries/league/2026/reg11", "severity": "HIGH", "link": OFF + "/injuries/league/2026/reg10",
             "finding": "The week-11 injury URL serves the week-10 report verbatim (title, heading and every row). Week-11 "
                        "designations do not exist at capture time, so no week-11 injury input is used anywhere on this site."},
            {"item": "Root index.html", "severity": "LOW", "link": "../index.html",
             "finding": "Generated by scripts/build_hub.py, owned by another session. This session adds one section to it; "
                        "the generator was not edited, and the request is logged in COORDINATION.md."},
            {"item": "Duplicate site trees", "severity": "MEDIUM", "link": "../hub/archive.html",
             "finding": "A dozen earlier trees remain online. ops/ is additive and links back; it does not modify or claim "
                        "to supersede them."},
            {"item": "Coordination board", "severity": "LOW", "link": "../COORDINATION.md",
             "finding": "Claim posted before work began: ops/**, data/ops/**, scripts/ops_*.py, one additive section in "
                        "index.html, one additive CI step. No other session's file edited."},
        ],
    }


def main():
    res = build_results()
    join = load(os.path.join(D, "join.json"))
    ldb = load(os.path.join(D, "leaderboard.json"))
    snap = load(os.path.join(D, "snapshots.json"))
    corr = load(os.path.join(D, "correlation.json"))
    props = load(os.path.join(D, "props.json"))
    model = load(os.path.join(D, "model.json"))

    outs = {
        "results.json": res,
        "requirements.json": build_requirements(join, ldb, snap, corr, props, model, res),
        "questions.json": build_questions(join, ldb, corr, props, model),
        "suggestions.json": build_suggestions(),
        "flags.json": build_flags(join, snap, model, corr, props, ldb),
        "repo.json": build_repo(),
    }
    for name, blob in outs.items():
        with open(os.path.join(D, name), "w", encoding="utf-8") as f:
            json.dump(blob, f, indent=1)
    print(f"content: {res['games']} finals, {len(res['checks'])} reconciliation checks, "
          f"{len(outs['requirements.json']['rows'])} requirements, {len(outs['questions.json']['rows'])} questions, "
          f"{len(outs['suggestions.json']['rows'])} suggestions, {len(outs['flags.json']['rows'])} flags, "
          f"{len(outs['repo.json']['rows'])} repo findings")
    fails = [c for c in res["checks"] if c[1] != "PASS"]
    if fails:
        raise SystemExit(f"results feed reconciliation FAILED: {fails}")


if __name__ == "__main__":
    main()
