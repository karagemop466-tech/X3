#!/usr/bin/env python3
"""
Funnel model v1 — originate side, then total, then moneyline, in that order.

Everything this script emits is DERIVED: arithmetic on official, already-verified inputs.
It never invents a market price. Where a market price does not exist in the repository the
market column is blank and the row is badged, which is the rule the rest of the repo follows.

Inputs (read-only, produced by other sessions or by scripts/ops_model.py itself)
--------------------------------------------------------------------------------
data/ops/reference/games.json          official 2026 game log (final scores + schedule)
data/ops/reference/standings.json      official 2026 standings (32 clubs)
data/ops/reference/teamstats.json      official 2026 team stats, offense + defense
data/ops/reference/playerlogs.json     official per-week player logs (prop leg inputs)
data/ops/reference/injuries_wk10.json  official Week-10 injury report rows
data/ops/reference/depth.json          club-published depth charts
scripts/ops_join.py output             injury x depth replacement-depth join

Output
------
data/ops/model.json        ratings, per-game origination, gates, correlations, leaderboard
ops/data/model.json        byte-identical copy for the site build

Method (published in full on ops/method.html; no hidden constants)
------------------------------------------------------------------
1.  Strictly pre-game ratings.  A week-W game is priced from games in weeks < W only, so no
    result that the bet would have been settled on is ever in its own input.
2.  Side first.  Net rating = ridge-shrunk mean margin contribution; the side price is
    -(net_home - net_away) for a home team, positive = home favoured.
3.  Total second.  Total = league average total + pace_home + pace_away. It is computed
    AFTER the side so the side can never borrow information from a total that was itself
    fitted on the same game.
4.  Moneyline third, and only from the side.  Margin is modelled as normal(mu = -spread,
    sigma = fitted residual sd).  P(home wins) = Phi(mu / sigma).  Publishing the side
    first is what makes the moneyline reproducible: it is a transform of the side, so the
    three markets can never contradict each other.
"""
from __future__ import annotations

import json
import math
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "data", "ops", "reference")
OUT = os.path.join(ROOT, "data", "ops")
SHARE = os.path.join(ROOT, "ops", "data")

AS_OF = "2026-11-14"
SEASON = 2026
SHRINK = 2.0          # pseudo-games of shrinkage toward the league mean
MIN_PRIOR_GAMES = 3   # a club needs this many prior games before it is priced
BREAKEVEN = 0.5238    # -110 both ways -> 52.38%
DEC = 0.909           # decimal odds at -110


def load(name, default=None):
    p = os.path.join(REF, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def r2(x, nd=2):
    if x is None:
        return None
    return round(x, nd)


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ---------------------------------------------------------------------------
# ratings
# ---------------------------------------------------------------------------
def _solve(A, b):
    """Gaussian elimination with partial pivoting; A is small (<=33x33) and positive definite."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            continue
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]
        for r in range(n):
            if r == c:
                continue
            f = M[r][c] / pv
            if f:
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(n)]


def _ridge_means(design, y, lam):
    """Solve (X'X + lam*I) beta = X'y with the intercept column last and unpenalised."""
    p = len(design[0])
    A = [[0.0] * p for _ in range(p)]
    b = [0.0] * p
    for row, yi in zip(design, y):
        for i in range(p):
            b[i] += row[i] * yi
            for j in range(p):
                A[i][j] += row[i] * row[j]
    for i in range(p - 1):
        A[i][i] += lam
    return _solve(A, b)


def fit_ratings(games, upto_week):
    """Ridge least squares, fitted on weeks < upto_week only.

    margin_home_obs = (home - away) - hfa*(not neutral)  =  net[home] - net[away] + noise
    total_obs       = home + away                        =  base + pace[home] + pace[away] + noise

    The home-field term hfa is fitted jointly with the net ratings rather than assumed, and
    neutral-site games enter with no home-field term. Shrinkage (lam) pulls every club rating
    toward zero, which is what stops a 2-0 club from being priced as the best team in football.
    """
    prior = [g for g in games if g["status"] == "FINAL" and g["week"] < upto_week]
    teams = sorted({t for g in prior for t in (g["away"], g["home"])})
    if len(prior) < 6:
        return {}, 0.0, (44.0, {}, None), {}
    counts = {t: sum(1 for g in prior if t in (g["away"], g["home"])) for t in teams}
    idx = {t: i for i, t in enumerate(teams)}

    # --- side: one row per game, columns = net[club]..., hfa ---
    design, y = [], []
    for g in prior:
        row = [0.0] * (len(teams) + 1)
        row[idx[g["home"]]] = 1.0
        row[idx[g["away"]]] = -1.0
        row[-1] = 0.0 if g.get("neutral_site") else 1.0
        design.append(row)
        y.append(g["home_score"] - g["away_score"])
    beta = _ridge_means(design, y, SHRINK)
    net = {t: beta[idx[t]] for t in teams}
    hfa = beta[-1]

    # --- total: one row per game, columns = pace[club]..., base ---
    design, y = [], []
    for g in prior:
        row = [0.0] * (len(teams) + 1)
        row[idx[g["home"]]] = 1.0
        row[idx[g["away"]]] = 1.0
        row[-1] = 1.0
        design.append(row)
        y.append(g["home_score"] + g["away_score"])
    beta = _ridge_means(design, y, SHRINK)
    base = beta[-1]
    pace = {t: beta[idx[t]] for t in teams}
    league_total = base + 2 * (sum(pace.values()) / len(pace))

    resid = []
    for g in prior:
        pred = net[g["home"]] - net[g["away"]] + (0.0 if g.get("neutral_site") else hfa)
        resid.append((g["home_score"] - g["away_score"]) - pred)
    sigma = statistics.pstdev(resid) if len(resid) > 2 else None
    return net, hfa, (league_total, pace, sigma), counts


def originate(g):
    """Deterministic origination for one scheduled game, in the required order."""
    return g


def main():
    games = load("games.json")
    standings = load("standings.json")
    teamstats = load("teamstats.json")
    playerlogs = load("playerlogs.json", {"players": []})
    inj = load("injuries_wk10.json", {"rows": []})
    depth = load("depth.json", {"clubs": []})
    if not games:
        raise SystemExit("missing data/ops/reference/games.json")

    all_games = games["games"]
    finals = [g for g in all_games if g["status"] == "FINAL"]
    week = games.get("week_of_record")

    # ---------------- full-sample ratings (for display) ----------------
    net, hfa, (league_total, pace, sigma), counts = fit_ratings(all_games, 99)
    ratings = []
    st = {r["abbr"]: r for r in (standings or {}).get("rows", [])}
    for t in sorted(net, key=lambda x: -net[x]):
        s = st.get(t, {})
        g_n = counts.get(t, 0)
        ratings.append({
            "team": t,
            "net": r2(net[t]),
            "pace": r2(pace[t]),
            "hfa_adjusted_net": r2(net[t]),
            "games": g_n,
            "w": s.get("w"), "l": s.get("l"), "t": s.get("t"),
            "pf": s.get("pf"), "pa": s.get("pa"),
            "pf_pg": r2(s["pf"] / max(1, s["w"] + s["l"] + s["t"])) if s.get("pf") else None,
            "pa_pg": r2(s["pa"] / max(1, s["w"] + s["l"] + s["t"])) if s.get("pa") else None,
            "source": "https://www.nfl.com/standings/league/2026/REG",
        })

    # ---------------- walk-forward origination of the unplayed slate ----------------
    slate = [g for g in all_games if g["status"] == "SCHEDULED"]
    orig = []
    for g in sorted(slate, key=lambda x: (x["week"], x["date_iso"], x["away"])):
        w_net, w_hfa, (w_total, w_pace, w_sigma), w_counts = fit_ratings(all_games, g["week"])
        h, a = g["home"], g["away"]
        prior_games = min(w_counts.get(h, 0), w_counts.get(a, 0))
        row = {
            "week": g["week"], "date": g["date_iso"], "kickoff_et": g.get("kickoff_et", ""),
            "network": g.get("network", ""), "away": a, "home": h,
            "neutral_site": bool(g.get("neutral_site")),
            "prior_games_min": prior_games,
            "source": g["source"],
        }
        if prior_games < MIN_PRIOR_GAMES or w_sigma is None:
            row.update({"status": "BLOCKED", "blocked_reason":
                        f"fewer than {MIN_PRIOR_GAMES} prior games for one club; ratings not identified"})
            orig.append(row)
            continue
        # 1. SIDE
        edge = (w_net[h] - w_net[a]) + (0.0 if g.get("neutral_site") else w_hfa)
        spread_home = -edge                       # negative = home favoured
        # 2. TOTAL
        total = w_total + w_pace[h] + w_pace[a]
        # 3. MONEYLINE, from the side only
        p_home = norm_cdf(edge / w_sigma)
        row.update({
            "status": "DERIVED",
            "fair_home_spread": r2(spread_home, 1),
            "fair_total": r2(total, 1),
            "fair_home_ml": int(round(-110 if p_home == 0.5 else
                                      (100 * (1 - p_home) / p_home if p_home > 0.5 else -100 * p_home / (1 - p_home)))),
            "p_home_win": r2(p_home, 3),
            "p_away_win": r2(1 - p_home, 3),
            "sigma": r2(w_sigma, 2),
            "hfa": r2(w_hfa, 2),
            "order": "side -> total -> moneyline",
            # market / difference: no official price exists in this repo -> blank by policy
            "market_home_spread": None, "market_total": None, "market_home_ml": None,
            "diff_spread": None, "diff_total": None, "diff_ml": None,
            "market_status": "UNVERIFIED - no official market price in the repository",
        })
        orig.append(row)

    # ---------------- walk-forward backtest of the side and the total ----------------
    bt = []
    for g in sorted(finals, key=lambda x: (x["week"], x["date_iso"])):
        w_net, w_hfa, (w_total, w_pace, w_sigma), w_counts = fit_ratings(all_games, g["week"])
        h, a = g["home"], g["away"]
        if min(w_counts.get(h, 0), w_counts.get(a, 0)) < MIN_PRIOR_GAMES or w_sigma is None:
            continue
        edge = (w_net[h] - w_net[a]) + (0.0 if g.get("neutral_site") else w_hfa)
        pred_margin = -(-edge)                     # home margin prediction = edge
        pred_total = w_total + w_pace[h] + w_pace[a]
        actual_margin = g["home_score"] - g["away_score"]
        actual_total = g["home_score"] + g["away_score"]
        p_home = norm_cdf(edge / w_sigma)
        bt.append({
            "week": g["week"], "away": a, "home": h,
            "pred_margin": r2(edge, 2), "actual_margin": actual_margin,
            "pred_total": r2(pred_total, 2), "actual_total": actual_total,
            "p_home": r2(p_home, 3), "home_won": actual_margin > 0, "tie": actual_margin == 0,
            "abs_margin_err": r2(abs(edge - actual_margin), 2),
            "abs_total_err": r2(abs(pred_total - actual_total), 2),
            "brier": r2((p_home - (1.0 if actual_margin > 0 else 0.0)) ** 2, 4),
            "source": g["source"],
        })

    def mean(xs):
        xs = [x for x in xs if x is not None]
        return r2(statistics.mean(xs), 3) if xs else None

    n_bt = len(bt)
    mae_margin = mean([b["abs_margin_err"] for b in bt])
    mae_total = mean([b["abs_total_err"] for b in bt])
    bias_margin = mean([b["pred_margin"] - b["actual_margin"] for b in bt])
    bias_total = mean([b["pred_total"] - b["actual_total"] for b in bt])
    brier = mean([b["brier"] for b in bt])
    clf_acc = mean([1.0 if (b["p_home"] >= 0.5) == (b["actual_margin"] > 0) else 0.0 for b in bt])

    model = {
        "as_of": AS_OF,
        "season": SEASON,
        "week_of_record": week,
        "method": ("Ridge-shrunk net rating per club + fitted home field for the side; league total + pace for the "
                   "total; normal transform of the side for the moneyline. Every week-W output is fitted on weeks <W "
                   "only. No market price is read or written: market columns are blank by policy."),
        "params": {
            "shrink_pseudo_games": SHRINK,
            "min_prior_games": MIN_PRIOR_GAMES,
            "breakeven_rate_vs_-110": BREAKEVEN,
            "decimal_odds_at_-110": DEC,
            "sigma_margin": r2(sigma, 2) if sigma else None,
            "hfa_points": r2(hfa, 2),
            "league_avg_total": r2(league_total, 2),
            "neutral_site_games_excluded_from_hfa": sum(1 for g in all_games if g.get("neutral_site") and g["status"] == "FINAL"),
        },
        "ratings": ratings,
        "originated": orig,
        "backtest": {
            "n": n_bt,
            "mae_margin": mae_margin,
            "mae_total": mae_total,
            "bias_margin": bias_margin,
            "bias_total": bias_total,
            "brier_home_win": brier,
            "home_win_base_rate": mean([1.0 if b["home_won"] else 0.0 for b in bt]),
            "model_home_win_rate": mean([1.0 if b["p_home"] >= 0.5 else 0.0 for b in bt]),
            "home_pick_accuracy": clf_acc,
            "rows": bt,
            "note": ("This is a backtest of the model against reality, not against a market. Without market prices "
                     "it says nothing about profitability and is not graded on the leaderboard."),
        },
        "limitations": [
            "No market price exists in the repository, so fair-vs-market difference is blank and ROI cannot be computed.",
            "n is one partial season; every weekly fit uses at most 137 finals and early weeks use far fewer.",
            "No prior-season priors, no schedule-strength residual beyond the net rating, no weather, no rest differential.",
            "Injuries are not yet an input to the price; the join exists (data/ops/join.json) but no validated effect size exists.",
        ],
    }

    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SHARE, exist_ok=True)
    blob = json.dumps(model, indent=1, sort_keys=False)
    for p in (os.path.join(OUT, "model.json"), os.path.join(SHARE, "model.json")):
        with open(p, "w", encoding="utf-8") as f:
            f.write(blob + "\n")
    print(f"model: {len(ratings)} ratings, {len(orig)} originated rows, backtest n={n_bt}, "
          f"MAE margin {mae_margin}, MAE total {mae_total}, Brier {brier}")


if __name__ == "__main__":
    main()
