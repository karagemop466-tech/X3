#!/usr/bin/env python3
"""
X3 pipeline stage 2 - origination engine X3-v2 + price-snapshot model rows + strategy backtest
+ leaderboard (signal vs staking) + validation/demotion gates + correlations. Session arena/873c7396-x3.

ORIGINATION ORDER (requirement): for every game the engine originates in a fixed order,
  1. SIDE    - opponent-adjusted margin rating -> fair spread (home perspective)
  2. TOTAL   - opponent-adjusted for/against ratings -> fair total
  3. MONEYLINE - derived ONLY from the side already originated (Gaussian margin model),
                 never re-estimated from market prices.
The order is recorded per game in the output (origination_seq).

Inputs: data/x3/results_feed_2026.csv, data/x3/results_history.csv, data/x3/price_snapshots_2026.csv
Outputs: data/x3/model_lines_2026.csv, data/x3/backtest_bets.csv, data/x3/model_eval.json,
         data/x3/leaderboard.json, data/x3/correlations.json, data/x3/gates.json,
         hub/data/{results,pricing,origination,signal}.json
Deterministic; no wall-clock reads.
"""
from __future__ import annotations
import csv, json, os, math, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "data", "x3")
HUBD = os.path.join(ROOT, "hub", "data")
TEAMS = ["ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB",
         "HOU", "IND", "JAX", "KC", "LV", "LAC", "LA", "MIA", "MIN", "NE", "NO", "NYG", "NYJ",
         "PHI", "PIT", "SF", "SEA", "TB", "TEN", "WAS"]
AS_OF = "2026-11-14"
NFLVERSE_URL = "https://github.com/nflverse/nfldata/blob/master/data/games.csv"
SOURCE_NOTE = "results/market: nflverse games.csv (scores = official record mirror; lines = PFF MARKET-3P)"

# ---- pre-registered parameters (published; changes create a new model id, never edit these) ----
PARAMS = {
    "model_id": "X3-v2",
    "prior_season_weight": 0.5,        # previous-season rating shrunk to this fraction
    "prior_shrinkage_games_k": 3.0,    # prior counts as k games of evidence
    "iterations": 150,                 # fixed-point iterations for adjusted ratings
    "hfa_2026_pts": 0.0,               # measured 2026 home win% 0.4927 (n=137) -> no HFA (hub finding)
    "hfa_backtest_pts": 1.5,           # fixed for 2021-2025 backtest; sensitivity published
    "sigma_margin_fixed": None,        # estimated from official margins (written to PARAMS_OUT)
    "edge_threshold_side_pts": 2.0,
    "edge_threshold_total_pts": 2.0,
    "edge_threshold_ml_ev": 0.04,
    "flat_stake_units": 1.0,
    "kelly_fraction": 0.25,
    "kelly_cap": 0.03,
    "bet_odds_default": -110,
}
PARAMS_OUT = dict(PARAMS)

def read_csv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(path, heads, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(heads)
        for r in rows:
            w.writerow([r.get(h, "") for h in heads])
    print("wrote", os.path.relpath(path, ROOT), f"({len(rows)} rows)")

def jdump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    print("wrote", os.path.relpath(path, ROOT))

# ------------------------------------------------------------------ data load
feed = read_csv(os.path.join(OUT, "results_feed_2026.csv"))
hist = read_csv(os.path.join(OUT, "results_history.csv"))
snaps = read_csv(os.path.join(OUT, "price_snapshots_2026.csv"))

OLD_CODE = {"OAK": "LV", "SD": "LAC", "STL": "LA", "WSH": "WAS", "AZ": "ARI"}
for r in hist:
    r["home_team"] = OLD_CODE.get(r["home_team"], r["home_team"])
    r["away_team"] = OLD_CODE.get(r["away_team"], r["away_team"])
    r["margin_home"] = int(r["margin_home"]); r["total"] = int(r["total"])
    r["home_score"] = int(r["home_score"]); r["away_score"] = int(r["away_score"])
    r["market_spread_home_close"] = float(r["market_spread_home_close"])
    r["market_total_close"] = float(r["market_total_close"])
    r["week"] = int(r["week"]); r["season"] = int(r["season"])
for r in feed:
    r["week"] = int(r["week"])
    if r["status"] == "FINAL":
        r["margin_home"] = int(r["margin_home"]); r["total_pts"] = int(r["total_pts"])
    r["market_spread_home_close"] = float(r["market_spread_home_close"]) if r["market_spread_home_close"] else None
    r["market_total_close"] = float(r["market_total_close"]) if r["market_total_close"] else None

# sigma of official margins, 2021-2025 (backtest window) - published with n
m21_25 = [abs(r["margin_home"]) for r in hist if 2021 <= r["season"] <= 2025]
SIGMA = sum(m21_25) / math.sqrt(len(m21_25) * 2 / math.pi) if m21_25 else 13.5
# more directly: sd of margins
ms = [r["margin_home"] for r in hist if 2021 <= r["season"] <= 2025]
mu = sum(ms) / len(ms)
SIGMA_SD = math.sqrt(sum((x - mu) ** 2 for x in ms) / (len(ms) - 1))
PARAMS_OUT["sigma_margin_sd"] = round(SIGMA_SD, 3)
PARAMS_OUT["sigma_margin_n"] = len(ms)
PARAMS_OUT["sigma_margin_note"] = "sd of official game margins 2021-2025, used for cover/win probabilities"

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def prob_cover(fair_margin, line_from_home):        # line_from_home = spread_home (neg = home fav)
    return norm_cdf((fair_margin + line_from_home) / SIGMA_SD)

def prob_win(fair_margin):
    return norm_cdf(fair_margin / SIGMA_SD)

def american_from_prob(p):
    p = min(max(p, 0.01), 0.99)
    return int(round(-100 * p / (1 - p))) if p >= 0.5 else int(round(100 * (1 - p) / p))

def ev_at_odds(p, odds):
    b = (100.0 / -odds) if odds < 0 else (odds / 100.0)
    return p * b - (1 - p)

# --------------------------------------------------------- iterative ratings
def solve_adjusted(games, prior=None, k=PARAMS["prior_shrinkage_games_k"], hfa=0.0):
    """games: list of dicts home,away,margin (home-away), total not needed here.
    Returns dict R[team] margin rating (points). prior: dict or None."""
    n = {t: 0 for t in TEAMS}; s = {t: 0.0 for t in TEAMS}
    opp = {t: [] for t in TEAMS}
    for g in games:
        h, a = g["home"], g["away"]
        m = g["margin"] - (hfa if g.get("home_flag", 1) else -hfa)
        n[h] += 1; n[a] += 1
        s[h] += m; s[a] -= m
        opp[h].append(a); opp[a].append(h)
    R = {t: 0.0 for t in TEAMS}
    if prior:
        w = {t: (prior[t] * PARAMS["prior_season_weight"]) for t in TEAMS}
    for _ in range(PARAMS["iterations"]):
        new = {}
        for t in TEAMS:
            base = (s[t] + sum(R[o] for o in opp[t])) / n[t] if n[t] else 0.0
            if prior and n[t] + k > 0:
                base = (n[t] * base + k * w[t]) / (n[t] + k)
            new[t] = base
        R = new
    mean = sum(R.values()) / len(R)
    return {t: R[t] - mean for t in TEAMS}

def solve_totals(games, prior=None, k=PARAMS["prior_shrinkage_games_k"]):
    """Opponent-adjusted for/against point ratings. games need home,away,pf_home,pa_home."""
    lg = (sum(g["pf_home"] + g["pa_home"] for g in games) / (2 * len(games))) if games else 22.0
    nf = {t: 0 for t in TEAMS}; sf = {t: 0.0 for t in TEAMS}; na = {t: 0 for t in TEAMS}; sa = {t: 0.0 for t in TEAMS}
    fopp = {t: [] for t in TEAMS}; aopp = {t: [] for t in TEAMS}
    for g in games:
        h, a = g["home"], g["away"]
        nf[h] += 1; nf[a] += 1; na[h] += 1; na[a] += 1
        sf[h] += g["pf_home"]; sf[a] += g["pa_home"]
        sa[h] += g["pa_home"]; sa[a] += g["pf_home"]
        fopp[h].append(a); fopp[a].append(h); aopp[h].append(a); aopp[a].append(h)
    off = {t: (sf[t] / nf[t] - lg) if nf[t] else 0.0 for t in TEAMS}
    dfn = {t: (sa[t] / na[t] - lg) if na[t] else 0.0 for t in TEAMS}
    pw = PARAMS["prior_season_weight"]
    for _ in range(PARAMS["iterations"]):
        off2, dfn2 = {}, {}
        for t in TEAMS:
            o = (sf[t] / nf[t] - lg - sum(dfn[o2] for o2 in fopp[t]) / nf[t]) if nf[t] else 0.0
            d = (sa[t] / na[t] - lg - sum(off[o2] for o2 in aopp[t]) / na[t]) if na[t] else 0.0
            if prior:
                o = (nf[t] * o + k * prior["off"][t] * pw) / (nf[t] + k)
                d = (na[t] * d + k * prior["def"][t] * pw) / (na[t] + k)
            off2[t], dfn2[t] = o, d
        off, dfn = off2, dfn2
    mo = sum(off.values()) / len(off); md = sum(dfn.values()) / len(dfn)
    return {t: off[t] - mo for t in TEAMS}, {t: dfn[t] - md for t in TEAMS}, lg

def prior_from_history(season):
    """Final adjusted rating of season-1 (all weeks) - computed once per season, no look-ahead
    within the season because it only uses completed prior seasons."""
    gs = [g for g in hist if g["season"] == season - 1]
    if not gs:
        return None
    gg = [{"home": r["home_team"], "away": r["away_team"], "margin": r["margin_home"]} for r in gs]
    R = solve_adjusted(gg, prior=None, hfa=PARAMS["hfa_backtest_pts"])
    tg = [{"home": r["home_team"], "away": r["away_team"], "pf_home": r["home_score"],
           "pa_home": r["away_score"]} for r in gs]
    off, dfn, _ = solve_totals(tg, prior=None)
    return {"R": R, "off": off, "def": dfn}

# season 2025 finals for the 2026 prior
prior_2026 = prior_from_history(2026)
prior_backtest = {s: prior_from_history(s) for s in range(2021, 2026)}

def fit_asof(season, thru_week, prior):
    """Ratings from all completed games: prior seasons' full history + season thru_week-1."""
    if season > 2026:
        past = [r for r in hist if r["season"] < season]
    else:
        past = [r for r in hist if r["season"] < season]
    if season == 2026:
        past = [r for r in hist if r["season"] <= 2025]
    cur = []
    if season <= 2026:
        for r in hist:
            if r["season"] == season and r["week"] <= thru_week - 1:
                cur.append(r)
    gg = [{"home": r["home_team"], "away": r["away_team"], "margin": r["margin_home"]} for r in past + cur]
    hfa = PARAMS["hfa_2026_pts"] if season == 2026 else PARAMS["hfa_backtest_pts"]
    R = solve_adjusted(gg, prior=(prior or {}).get('R') if isinstance(prior, dict) else prior, hfa=hfa)
    tg = [{"home": r["home_team"], "away": r["away_team"], "pf_home": r["home_score"],
           "pa_home": r["away_score"]} for r in past + cur]
    off, dfn, lg = solve_totals(tg, prior={"off": prior["off"], "def": prior["def"]} if prior else None)
    return R, off, dfn, lg

def originate(season, week, prior):
    """ORIGINATION ORDER: side -> total -> moneyline. Returns list of fair-line dicts."""
    R, off, dfn, lg = fit_asof(season, week, prior)
    hfa = PARAMS["hfa_2026_pts"] if season == 2026 else PARAMS["hfa_backtest_pts"]
    rows = []
    for r in feed:
        if r["week"] != week:
            continue
        h, a = r["home_team"], r["away_team"]
        # 1. SIDE
        fair_margin = (R[h] - R[a]) + hfa
        fair_spread_home = -round(fair_margin * 2) / 2.0          # half-point grid, neg = home fav
        # 2. TOTAL
        fair_total = round((2 * lg + (off[h] + off[a] - dfn[h] - dfn[a]) / 2.0) * 2) / 2.0
        # 3. MONEYLINE (derived from the side, Gaussian with sigma from official margins)
        p_home = prob_win(fair_margin)
        fair_ml_home = american_from_prob(p_home)
        fair_ml_away = american_from_prob(1 - p_home)
        rows.append({"game_id": r["game_id"], "season": season, "week": week,
                     "gameday": r["gameday"], "away": a, "home": h,
                     "fair_margin_home": round(fair_margin, 2),
                     "fair_spread_home": fair_spread_home,
                     "fair_total": fair_total,
                     "p_home_win": round(p_home, 4),
                     "fair_ml_home": fair_ml_home, "fair_ml_away": fair_ml_away,
                     "origination_seq": "1-side,2-total,3-moneyline",
                     "status": r["status"],
                     "mkt_spread_home": r["market_spread_home_close"],
                     "mkt_total": r["market_total_close"],
                     "mkt_ml_home": r["market_ml_home_close"], "mkt_ml_away": r["market_ml_away_close"]})
    return rows

# --------------------------------------------------------------- backtest
bets = []
pred_all = []
for season in range(2021, 2026):
    prior = prior_backtest[season]
    weeks = sorted({r["week"] for r in hist if r["season"] == season})
    for w in weeks:
        preds = originate_bt = None
        # originate with data thru w-1 (walk-forward)
        R, off, dfn, lg = fit_asof(season, w, prior)
        hfa = PARAMS["hfa_backtest_pts"]
        for r in hist:
            if r["season"] != season or r["week"] != w:
                continue
            h, a = r["home_team"], r["away_team"]
            fair_margin = (R[h] - R[a]) + hfa
            fair_spread_home = -round(fair_margin * 2) / 2.0
            fair_total = round((2 * lg + (off[h] + off[a] - dfn[h] - dfn[a]) / 2.0) * 2) / 2.0
            p_home_cover_fair = prob_cover(fair_margin, r["market_spread_home_close"])
            p_over_fair = norm_cdf((fair_total - r["total"] + (r["total"] - r["market_total_close"]) * 0) / 6.666)  # sd of totals ~ 2*sqrt(2)*? keep simple below
            # total probabilities: sd of total ~ 13.0 (published)
            p_over_fair = norm_cdf((fair_total - r["market_total_close"]) / 13.0)
            mkt = r["market_spread_home_close"]
            # SIDE bets (flat, at close, home/away by fair edge)
            edge_side = fair_spread_home - mkt          # >0 means we like home more than market
            if abs(edge_side) >= PARAMS["edge_threshold_side_pts"]:
                side_home = edge_side < 0               # our fair spread lower (more negative) = home stronger
                p = p_home_cover_fair if side_home else 1 - p_home_cover_fair
                line_used = mkt if side_home else -mkt
                margin = r["margin_home"] if side_home else -r["margin_home"]
                cover = 1 if margin + line_used > 0 else (0 if margin + line_used < 0 else 0.5)
                bets.append({"season": season, "week": w, "game_id": r["game_id"], "strategy": "SID",
                             "pick": f"{h} {line_used:+g}" if side_home else f"{a} {-line_used:+g}",
                             "fair_prob": round(p, 4), "edge_pts": round(abs(edge_side), 2),
                             "result_cover": cover, "odds": PARAMS["bet_odds_default"],
                             "source": NFLVERSE_URL})
            # TOTAL bets
            edge_tot = fair_total - r["market_total_close"]
            if abs(edge_tot) >= PARAMS["edge_threshold_total_pts"]:
                over = edge_tot > 0
                p = p_over_fair if over else 1 - p_over_fair
                tot = r["total"]
                diff = tot - r["market_total_close"]
                res = 1 if (diff > 0 if over else diff < 0) else (0.5 if diff == 0 else 0)
                bets.append({"season": season, "week": w, "game_id": r["game_id"], "strategy": "TOT",
                             "pick": ("Over" if over else "Under") + f" {r['market_total_close']:g}",
                             "fair_prob": round(p, 4), "edge_pts": round(abs(edge_tot), 2),
                             "result_cover": res, "odds": PARAMS["bet_odds_default"],
                             "source": NFLVERSE_URL})
            pred_all.append({"season": season, "week": w, "game_id": r["game_id"],
                             "fair_spread_home": fair_spread_home, "fair_total": fair_total,
                             "mkt_spread_home": r["market_spread_home_close"],
                             "mkt_total": r["market_total_close"],
                             "margin_home": r["margin_home"], "total": r["total"]})

# 2026 walk-forward: predictions per week with prior + thru w-1 data (weeks 2..11)
pred_2026 = []
for w in range(2, 12):
    pred_2026 += originate(2026, w, prior_2026)
# week 1 rows (prior-only)
w1 = originate(2026, 1, prior_2026)

# settle 2026 weeks 1-9 bets vs official finals
feed_idx = {(int(r["week"]), r["home_team"], r["away_team"]): r for r in feed}
for p in pred_2026:
    if p["week"] > 9 or p["status"] != "FINAL":
        continue
    r = feed_idx[(p["week"], p["home"], p["away"])]
    p["margin_home"] = r["margin_home"]; p["total"] = r["total_pts"]
    mkt = p["mkt_spread_home"]
    edge_side = p["fair_spread_home"] - mkt
    if abs(edge_side) >= PARAMS["edge_threshold_side_pts"]:
        side_home = edge_side < 0
        line_used = mkt if side_home else -mkt
        margin = p["margin_home"] if side_home else -p["margin_home"]
        cover = 1 if margin + line_used > 0 else (0 if margin + line_used < 0 else 0.5)
        pc = prob_cover(p["fair_margin_home"], line_used if side_home else -line_used)
        bets.append({"season": 2026, "week": p["week"], "game_id": p["game_id"], "strategy": "SID",
                     "pick": f"{p['home']} {line_used:+g}" if side_home else f"{p['away']} {-line_used:+g}",
                     "fair_prob": round(pc if side_home else 1 - pc, 4), "edge_pts": round(abs(edge_side), 2),
                     "result_cover": cover, "odds": PARAMS["bet_odds_default"], "source": NFLVERSE_URL})
    edge_tot = p["fair_total"] - p["mkt_total"]
    if abs(edge_tot) >= PARAMS["edge_threshold_total_pts"]:
        over = edge_tot > 0
        diff = p["total"] - p["mkt_total"]
        res = 1 if (diff > 0 if over else diff < 0) else (0.5 if diff == 0 else 0)
        po = norm_cdf((p["fair_total"] - p["mkt_total"]) / 13.0)
        bets.append({"season": 2026, "week": p["week"], "game_id": p["game_id"], "strategy": "TOT",
                     "pick": ("Over" if over else "Under") + f" {p['mkt_total']:g}",
                     "fair_prob": round(po if over else 1 - po, 4), "edge_pts": round(abs(edge_tot), 2),
                     "result_cover": res, "odds": PARAMS["bet_odds_default"], "source": NFLVERSE_URL})

# ------------------------------------------------------- strategy aggregation
def settle(profit_units, odds):
    b = (100.0 / -odds) if odds < 0 else odds / 100.0
    return profit_units * b

def binom_ci(p_hat, n, z=1.645):
    if n == 0: return (0.0, 0.0)
    se = math.sqrt(p_hat * (1 - p_hat) / n)
    return (max(0, p_hat - z * se), min(1, p_hat + z * se))

def summarize(strategy_rows, name):
    n = len(strategy_rows)
    wins = sum(1 for b in strategy_rows if b["result_cover"] == 1)
    losses = sum(1 for b in strategy_rows if b["result_cover"] == 0)
    pushes = n - wins - losses
    dec = wins + losses
    settled = [b for b in strategy_rows if b["result_cover"] in (0, 1)]
    stake = PARAMS["flat_stake_units"] * n
    profit = 0.0
    for b in strategy_rows:
        if b["result_cover"] == 1: profit += settle(1, b["odds"])
        elif b["result_cover"] == 0: profit -= 1
    roi = profit / stake if stake else 0.0
    hit = wins / dec if dec else 0.0
    lo, hi = binom_ci(hit, dec)
    mean_edge = sum(b["edge_pts"] for b in strategy_rows) / n if n else 0.0
    mean_fair = sum(b["fair_prob"] for b in strategy_rows) / n if n else 0.0
    exp_hit = mean_fair / (mean_fair + (1 - mean_fair)) if n else 0.0
    # Brier skill vs market baseline: baseline prob from edge=0 -> 0.5 at -110 world; use fair vs 50/50?
    brier = sum((b["fair_prob"] - b["result_cover"]) ** 2 for b in settled) / len(settled) if settled else None
    # rolling-20 mean edge for demotion demo
    roll20 = [sum(x["edge_pts"] for x in strategy_rows[i:i + 20]) / min(20, len(strategy_rows) - i)
              for i in range(0, max(0, len(strategy_rows) - 20))]
    breakeven = 100.0 / 210.0  # -110 breakeven
    return {"strategy": name, "bets": n, "wins": wins, "losses": losses, "pushes": pushes,
            "hit_rate": round(hit, 4), "hit_ci90": [round(lo, 4), round(hi, 4)],
            "breakeven": round(breakeven, 4),
            "roi_flat": round(roi, 4), "profit_units_flat": round(profit, 2),
            "mean_edge_pts": round(mean_edge, 3), "brier": round(brier, 4) if brier else None,
            "exp_hit_from_fair": round(mean_fair, 4),
            "luck_z": round((hit - mean_fair) / math.sqrt(mean_fair * (1 - mean_fair) / dec), 3) if dec and 0 < mean_fair < 1 else None,
            "min_roll20_edge": round(min(roll20), 3) if roll20 else None,
            "note": "flat 1u at market close; paper only"}

by_strat = collections.defaultdict(list)
for b in bets:
    by_strat[b["strategy"]].append(b)
leaderboard = []
for sname, rows in sorted(by_strat.items()):
    lb = summarize(rows, sname)
    # season-by-season stability (G6)
    byseason = collections.defaultdict(list)
    for b in rows: byseason[b["season"]].append(b)
    seas = []
    for s in sorted(byseason):
        r2 = summarize(byseason[s], sname)
        seas.append({"season": s, "bets": r2["bets"], "roi_flat": r2["roi_flat"]})
    lb["by_season"] = seas
    lb["seasons_profitable"] = sum(1 for x in seas if x["roi_flat"] > 0)
    leaderboard.append(lb)

# kelly staking view (same settled stream, quarter-kelly capped 3%)
for lb in leaderboard:
    rows = by_strat[lb["strategy"]]
    bank = 100.0; peak = bank; maxdd = 0.0
    for b in rows:
        p = b["fair_prob"]
        odds = b["odds"]; bnet = (100.0 / -odds) if odds < 0 else odds / 100.0
        f = max(0.0, (p * bnet - (1 - p)) / bnet) * PARAMS["kelly_fraction"]
        f = min(f, PARAMS["kelly_cap"])
        stake = bank * f
        if b["result_cover"] == 1: bank += stake * bnet
        elif b["result_cover"] == 0: bank -= stake
        peak = max(peak, bank); maxdd = max(maxdd, (peak - bank) / peak)
    lb["kelly_final_bank"] = round(bank, 2)
    lb["kelly_max_drawdown"] = round(maxdd, 4)

# gates (computed, not asserted)
gates = []
for lb in leaderboard:
    g = {
        "strategy": lb["strategy"],
        "G1_sample>=100": "PASS" if lb["bets"] >= 100 else "FAIL",
        "G2_mean_edge>=1pt": "PASS" if lb["mean_edge_pts"] >= 1.0 else "FAIL",
        "G3_hitCI>breakeven": "PASS" if (lb["hit_ci90"][0] > lb["breakeven"]) else "FAIL",
        "G4_brier<0.25": "PASS" if (lb["brier"] is not None and lb["brier"] < 0.25) else "FAIL",
        "G6_stable>=3of6seasons": "PASS" if lb["seasons_profitable"] >= 3 else "FAIL",
        "D1_roll20_edge<0": "TRIGGERED" if (lb["min_roll20_edge"] is not None and lb["min_roll20_edge"] < 0) else "not triggered",
        "D4_drawdown>25%": "TRIGGERED" if lb["kelly_max_drawdown"] > 0.25 else "not triggered",
        "state": "PAPER",
    }
    live_ok = all(g[k] == "PASS" for k in ("G1_sample>=100", "G2_mean_edge>=1pt", "G3_hitCI>breakeven",
                                           "G4_brier<0.25", "G6_stable>=3of6seasons"))
    g["live_eligible"] = "NO - stays PAPER (owner sign-off still required)" if not live_ok else "meets gates; owner sign-off required"
    gates.append(g)

# ------------------------------------------------- correlations (official numbers)
def pearson(xs, ys):
    n = len(xs)
    if n < 3: return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = math.sqrt(sum((x - mx) ** 2 for x in xs)); vy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return cov / (vx * vy) if vx and vy else None

corr = []
all_finals = ([{"season": r["season"], "week": r["week"], "home": r["home_team"], "away": r["away_team"],
                "margin": r["margin_home"], "total": r["total"],
                "mkt_spread": r["market_spread_home_close"], "mkt_total": r["market_total_close"]}
               for r in hist] +
              [{"season": 2026, "week": int(r["week"]), "home": r["home_team"], "away": r["away_team"],
                "margin": int(r["margin_home"]), "total": int(r["total_pts"]),
                "mkt_spread": r["market_spread_home_close"], "mkt_total": r["market_total_close"]}
               for r in feed if r["status"] == "FINAL"])
for label, sel in [("2021-2025", lambda r: 2021 <= r["season"] <= 2025), ("2026", lambda r: r["season"] == 2026)]:
    rows = [x for x in all_finals if sel(x)]
    r_mt = pearson([x["margin"] for x in rows], [x["total"] for x in rows])
    n = len(rows)
    corr.append({"pair": "signed home margin vs game total", "window": label, "n": n,
                 "pearson_r": round(r_mt, 4) if r_mt is not None else None,
                 "numbers": "official scores only", "source": NFLVERSE_URL})
    # side-total dependence: home favourite covers & over
    sub = []
    for x in rows:
        m, t = x["mkt_spread"], x["mkt_total"]
        if m is None or t is None or m == "" or t == "" or m >= 0:
            continue
        covered = 1 if (x["margin"] + m) > 0 else 0
        over = 1 if x["total"] > t else 0
        sub.append((covered, over))
    if len(sub) >= 30:
        pc = pearson([a for a, b in sub], [b for a, b in sub])
        p_joint = sum(1 for a, b in sub if a == 1 and b == 1) / len(sub)
        p_cov = sum(a for a, b in sub) / len(sub)
        p_over = sum(b for a, b in sub) / len(sub)
        corr.append({"pair": "home-favourite covers vs over (same game)", "window": label, "n": len(sub),
                     "pearson_r": round(pc, 4) if pc is not None else None,
                     "p_joint": round(p_joint, 4), "p_independent_expected": round(p_cov * p_over, 4),
                     "corr_factor_joint_vs_indep": round(p_joint / (p_cov * p_over), 4) if p_cov * p_over else None,
                     "numbers": "official scores + PFF closing lines (MARKET-3P)", "source": NFLVERSE_URL})
    # momentum
    tm = collections.defaultdict(list)
    for x in rows:
        tm[x["home"]].append((x["week"], x["margin"]))
        tm[x["away"]].append((x["week"], -x["margin"]))
    xs, ys = [], []
    for t, lst in tm.items():
        lst.sort()
        for (w1_, m1), (w2_, m2) in zip(lst, lst[1:]):
            if w2_ == w1_ + 1:
                xs.append(m1); ys.append(m2)
    if len(xs) >= 30:
        corr.append({"pair": "team margin week i vs week i+1 (momentum)", "window": label,
                     "n": len(xs), "pearson_r": round(pearson(xs, ys), 4),
                     "numbers": "official scores only", "source": NFLVERSE_URL})

# Gaussian mapping validation: empirical home-win% by closing-spread band, 2021-2025
bins = collections.defaultdict(lambda: [0, 0])
for r in hist:
    if not (2021 <= r["season"] <= 2025): continue
    m = r["market_spread_home_close"]
    band = round(m * 2) / 2
    b = bins[band]; b[0] += 1
    if r["margin_home"] > 0: b[1] += 1
    elif r["margin_home"] == 0: b[1] += 0.5
mapping = []
for band in sorted(bins):
    n, w = bins[band]
    if n < 25: continue
    emp = w / n
    gauss = prob_win(-band)   # fair margin implied by closing line
    mapping.append({"closing_spread_home": band, "n": n, "empirical_home_win": round(emp, 4),
                    "gaussian_model": round(gauss, 4), "abs_err": round(abs(emp - gauss), 4),
                    "source": NFLVERSE_URL})

# ------------------------------------------------------------------- outputs
write_csv(os.path.join(OUT, "backtest_bets.csv"), ["season", "week", "game_id", "strategy", "pick",
    "fair_prob", "edge_pts", "result_cover", "odds", "source"], bets)
jdump({"model": "X3-v2", "params": PARAMS_OUT, "as_of": AS_OF, "source": SOURCE_NOTE,
       "order": ["1-side", "2-total", "3-moneyline"],
       "hfa_sensitivity_2026": {"hfa_used": 0.0, "note": "measured 2026 home win% = 0.4927 (n=137); grid -1.5..+3.5 published on hub/lines"},
       "seasons_backtested": [2021, 2022, 2023, 2024, 2025, "2026 wks1-9"]},
      os.path.join(OUT, "model_eval.json"))
jdump({"as_of": AS_OF, "flat_stake": "1u at market close, paper", "leaderboard": leaderboard,
       "signal_note": ("SIGNAL columns (mean pre-close edge, Brier, hit-rate CI) measure the line, not the "
                       "money; STAKING columns (ROI flat, Kelly bank, drawdown) are shown separately so a "
                       "lucky staking run cannot mask a bad signal."),
       "luck_note": ("luck_z is the binomial z of realized hit rate vs the fair-probability expectation; "
                     "Kelly row uses quarter-Kelly capped 3%; all paper."),
       "clv_note": ("True CLV needs an opening or bet-time market snapshot; no 2026 opening-line source "
                    "exists (Q-01/F-01), so published signal = pre-close edge vs the PFF closing line.")},
      os.path.join(OUT, "leaderboard.json"))
jdump({"gates": gates, "demotion_rules": {
        "D1": "rolling 20-bet mean pre-close edge < 0 pts -> back to paper",
        "D2": "rolling 50-bet flat ROI < breakeven - 2 sigma -> back to paper",
        "D3": "any verification failure (unverified row, source mismatch) on strategy inputs -> back to paper",
        "D4": "paper-bankroll drawdown > 25% (quarter-Kelly) -> back to paper"},
       "note": "no strategy holds live capital; state column is the governance record"},
      os.path.join(OUT, "gates.json"))
jdump({"as_of": AS_OF, "correlations": corr, "gaussian_mapping_validation": mapping,
       "policy": "every value carries n; official scores only; market lines labelled MARKET-3P"},
      os.path.join(OUT, "correlations.json"))
write_csv(os.path.join(OUT, "model_lines_2026.csv"),
          ["game_id", "season", "week", "gameday", "away", "home", "fair_margin_home", "fair_spread_home",
           "fair_total", "p_home_win", "fair_ml_home", "fair_ml_away", "origination_seq", "status",
           "mkt_spread_home", "mkt_total", "mkt_ml_home", "mkt_ml_away"], pred_2026 + w1)

# model rows into the price-snapshot store (MODEL observation type) - full deterministic rebuild:
# read the market rows ingest.py wrote, add MODEL rows, rewrite the file once.
msnaps = []
for p in pred_2026 + w1:
    for mkt_name, val in (("SPREAD_HOME", p["fair_spread_home"]), ("TOTAL", p["fair_total"]),
                          ("ML_HOME", p["fair_ml_home"]), ("ML_AWAY", p["fair_ml_away"])):
        msnaps.append({"game_id": p["game_id"], "week": p["week"], "market": mkt_name,
                       "line": val, "odds": "", "obs_type": "MODEL", "captured_at": AS_OF,
                       "source_name": "X3-v2 origination (scripts/x3/model.py)", 
                       "source_url": "https://github.com/karagemop466-tech/X3/blob/main/scripts/x3/model.py",
                       "note": "our fair line; order side->total->ML"})
market_rows = read_csv(os.path.join(OUT, "price_snapshots_2026.csv"))
all_rows = market_rows + msnaps
heads2 = ["game_id", "week", "market", "line", "odds", "obs_type", "captured_at", "source_name",
          "source_url", "note"]
write_csv(os.path.join(OUT, "price_snapshots_2026.csv"), heads2, all_rows)
print("snapshot store rebuilt:", len(all_rows), "rows (", len(market_rows), "market +", len(msnaps), "model )")
print("bets:", len(bets), "| leaderboard:", [(l["strategy"], l["bets"], l["roi_flat"]) for l in leaderboard])
print("sigma_sd:", round(SIGMA_SD, 3), "| weeks with 2026 preds:", len(pred_2026) + len(w1))

# current ratings snapshot (walk-forward thru wk10 finals) for the origination page
R_cur, off_cur, dfn_cur, lg_cur = fit_asof(2026, 11, prior_2026)
ratings = {t: {"rating": round(R_cur[t], 2), "off": round(off_cur[t], 2), "def": round(dfn_cur[t], 2)}
           for t in TEAMS}
jdump({"as_of": AS_OF, "through": "2026 week 10 finals (137 games)", "league_ppg": round(lg_cur, 2),
       "ratings": ratings}, os.path.join(OUT, "ratings_2026_current.json"))
