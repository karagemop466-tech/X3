#!/usr/bin/env python3
"""X3 agency engine: ratings, origination, backtest, luck, correlations, availability.

Pure standard library. Deterministic (no clock reads except an explicit stamp passed in,
no randomness except a fixed-seed bootstrap). Every published number is either computed
from an official-source input file in this repository or explicitly left None.

Inputs (read-only, other sessions own them):
  data/desk/games.json          results, parsed by an earlier session from nfl.com week pages
  data/desk/standings.json      standings, parsed by an earlier session from nfl.com
  data/desk/depth.json          club depth charts (club sites), parsed by an earlier session
This session's own verified captures:
  agency/data/derived/week10_final_games.csv   two Week 10 finals + venue/roof/surface/weather
  agency/data/derived/inactives_w10.csv        official game-book inactives (4 clubs, 2 games)
  agency/data/derived/injury_designations_w10_2026.csv   2026-11-15 injury report capture
  agency/data/derived/week11_fixtures.csv      Week 11 slate

Outputs: agency/data/out/*.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAMP = "2026-11-15T19:45Z"          # capture timestamp for this build
SEASON = 2026

# nfl.com publishes the Cardinals as "AZ"; every other module in this repo uses "ARI".
# The alias is explicit so no row is silently renamed.
TEAMS = ("ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LA LAC LV "
         "MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS").split()
TEAM_NAME = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LA": "Los Angeles Rams", "LAC": "Los Angeles Chargers",
    "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks", "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}
DIVISIONS = {
    "AFC East": ["BUF", "MIA", "NE", "NYJ"],
    "AFC North": ["BAL", "CIN", "CLE", "PIT"],
    "AFC South": ["HOU", "IND", "JAX", "TEN"],
    "AFC West": ["DEN", "KC", "LAC", "LV"],
    "NFC East": ["DAL", "NYG", "PHI", "WAS"],
    "NFC North": ["CHI", "DET", "GB", "MIN"],
    "NFC South": ["ATL", "CAR", "NO", "TB"],
    "NFC West": ["ARI", "LA", "SF", "SEA"],
}
DIV_OF = {t: d for d, ts in DIVISIONS.items() for t in ts}

SRC = {
    "sched": "https://www.nfl.com/schedules/2026/by-week/week-{}",
    "standings": "https://www.nfl.com/standings/league/2026/REG",
    "injuries": "https://www.nfl.com/injuries/league/2026/reg{}",
    "gb_was_nyg": "https://static.www.nfl.com/image/upload/v1794570519/gamecenter/ab5828d9-4feb-11f1-abca-2c54536568a9.pdf",
    "gb_ne_det": "https://static.www.nfl.com/image/upload/v1794764592/gamecenter/ab582c2f-4feb-11f1-abca-2c54536568a9.pdf",
    "gc_was_nyg": "https://www.nfl.com/games/commanders-at-giants-2026-reg-10",
    "gc_ne_det": "https://www.nfl.com/games/patriots-at-lions-2026-reg-10",
    "lock": "https://www.nfl.com/news/drew-lock-no-injury-designation-seahawks-raiders",
    "lamar": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-friday-nov-13",
}

# ----------------------------------------------------------------------------- stats
def phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def phi_inv(p):
    """Acklam's inverse normal CDF, |rel err| < 1.2e-9."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _lgamma(n):
    return math.lgamma(n + 1)


def binom_pmf(k, n, p):
    if p <= 0:
        return 1.0 if k == 0 else 0.0
    if p >= 1:
        return 1.0 if k == n else 0.0
    return math.exp(_lgamma(n) - _lgamma(k) - _lgamma(n - k) + k * math.log(p) + (n - k) * math.log(1 - p))


def binom_test_two_sided(k, n, p0=0.5):
    """Exact two-sided binomial test (method of small p-values)."""
    if n == 0:
        return None
    obs = binom_pmf(k, n, p0)
    total = 0.0
    for i in range(n + 1):
        pi = binom_pmf(i, n, p0)
        if pi <= obs * (1 + 1e-9):
            total += pi
    return min(1.0, total)


def normal_ci(mean, sd, n, z=1.959964):
    if n < 2 or sd is None:
        return (None, None)
    se = sd / math.sqrt(n)
    return (mean - z * se, mean + z * se)


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def brier(probs, outcomes):
    if not probs:
        return None
    return sum((p - y) ** 2 for p, y in zip(probs, outcomes)) / len(probs)


def logloss(probs, outcomes, eps=1e-9):
    if not probs:
        return None
    return -sum(y * math.log(max(eps, p)) + (1 - y) * math.log(max(eps, 1 - p))
                for p, y in zip(probs, outcomes)) / len(probs)


def bh_adjust(pvals, q=0.10):
    """Benjamini-Hochberg step-up. Returns list of (p, threshold, significant)."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    out = [None] * m
    thresh = [(i + 1) / m * q for i in range(m)]
    kmax = -1
    for rank, idx in enumerate(order):
        if pvals[idx] <= thresh[rank]:
            kmax = rank
    for rank, idx in enumerate(order):
        out[idx] = (pvals[idx], thresh[rank], rank <= kmax)
    return out


def game_cluster_bootstrap(pairs, iters=2000, seed=20261115):
    """Percentile bootstrap of mean Brier over games (cluster = game).

    pairs: list of (game_key, [(p, y), ...]). Deterministic LCG, no numpy needed.
    """
    if not pairs:
        return (None, None)
    state = seed
    def rnd():
        nonlocal state
        state = (1103515245 * state + 12345) % (2 ** 31)
        return state / 2 ** 31
    means = []
    n = len(pairs)
    for _ in range(iters):
        acc, cnt = 0.0, 0
        for _ in range(n):
            i = int(rnd() * n)
            for p, y in pairs[i][1]:
                acc += (p - y) ** 2
                cnt += 1
        if cnt:
            means.append(acc / cnt)
    means.sort()
    return (means[int(0.025 * len(means))], means[int(0.975 * len(means)) - 1])


# ----------------------------------------------------------------------------- linear algebra
def solve(matrix, vec):
    """Gaussian elimination with partial pivoting. Deterministic."""
    n = len(vec)
    a = [row[:] + [vec[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-12:
            return None
        a[col], a[piv] = a[piv], a[col]
        pv = a[col][col]
        for j in range(col, n + 1):
            a[col][j] /= pv
        for r in range(n):
            if r == col:
                continue
            f = a[r][col]
            if f:
                for j in range(col, n + 1):
                    a[r][j] -= f * a[col][j]
    return [a[i][n] for i in range(n)]


def ridge_fit(X, y, lam):
    """Ridge on intercept-free design; intercept is a column of ones with no penalty."""
    p = len(X[0])
    XtX = [[0.0] * p for _ in range(p)]
    Xty = [0.0] * p
    for row, target in zip(X, y):
        for i in range(p):
            ri = row[i]
            if ri == 0.0:
                continue
            Xty[i] += ri * target
            for j in range(p):
                XtX[i][j] += ri * row[j]
    for i in range(1, p):
        XtX[i][i] += lam
    return solve(XtX, Xty)


# ----------------------------------------------------------------------------- load
def load_games():
    own = []
    p = ROOT / "agency/data/derived/week10_final_games.csv"
    with open(p) as f:
        for r in csv.DictReader(f):
            own.append({
                "week": int(r["week"]), "away": r["away"], "home": r["home"],
                "away_score": int(r["away_score"]), "home_score": int(r["home_score"]),
                "status": "FINAL", "date_iso": r["date"],
                "source": r["game_centre_url"], "own": True,
            })
    base = json.load(open(ROOT / "data/desk/games.json"))["games"]
    # base rows for the same fixtures are still SCHEDULED (the snapshot predates kickoff);
    # this session's official captures supersede them. Never keep both.
    seen = {(g["week"], g["away"], g["home"]) for g in own}
    games = [g for g in base if (g["week"], g["away"], g["home"]) not in seen]
    games += own
    games.sort(key=lambda g: (g["week"], g.get("date_iso") or "", g["away"]))
    return games


def load_standings():
    """This session re-read the official league standings page on 2026-11-15 (all 32 clubs,
    both chunks) and captured it; the earlier 2026-11-14 snapshot is superseded for NE and DET
    only, which played on 2026-11-15."""
    p = ROOT / "agency/data/derived/standings_2026_thru_w10_official.csv"
    out = {}
    for r in csv.DictReader(open(p)):
        ab = "ARI" if r["team"] == "AZ" else r["team"]
        out[ab] = {"abbr": ab, "name": r["name"], "w": int(r["w"]),
                          "l": int(r["l"]), "t": int(r["t"]), "pf": int(r["pf"]),
                          "pa": int(r["pa"]), "source": r["source_url"]}
    return out


def load_depth():
    return json.load(open(ROOT / "data/desk/depth.json"))["clubs"]


def load_injuries():
    """Stored injury report rows for weeks 8-10 (earlier session) + this session's Week 10 capture."""
    rows = json.load(open(ROOT / "data/desk/injuries.json"))["rows"]
    out = {}
    for r in rows:
        key = (r["week"], r["team"], r["player"])
        out[key] = {"pos": r["pos"], "injury": r["injury"], "practice": r["practice"],
                    "status": r["status"], "source": r["source"]}
    fresh = {}
    p = ROOT / "agency/data/derived/injury_designations_w10_2026.csv"
    with open(p) as f:
        for r in csv.DictReader(f):
            fresh[(r["team"], r["player"])] = r
    return out, fresh


# ----------------------------------------------------------------------------- ratings
def team_design(games, weeks):
    """Design matrix for opponent-aware margin model: [1, home?] + 32 team dummies."""
    idx = {t: i for i, t in enumerate(TEAMS)}
    X, y, keys = [], [], []
    for g in games:
        if g["week"] not in weeks or g["status"] != "FINAL":
            continue
        row = [0.0] * (1 + len(TEAMS))
        # intercept = league average home margin. A neutral-site game has no home edge, so it
        # must not enter this fit (it is scored with the constant removed instead).
        row[0] = 1.0 if not g.get("neutral_site") else 0.0
        row[1 + idx[g["home"]]] = 1.0
        row[1 + idx[g["away"]]] = -1.0
        X.append(row)
        y.append(g["home_score"] - g["away_score"])
        keys.append(g)
    return X, y, keys


LAMBDAS = [1.0, 3.0, 10.0, 30.0, 100.0]


def fit_margin_model(games, train_weeks, lam):
    X, y, _ = team_design(games, set(train_weeks))
    if len(X) < 12:
        return None
    coef = ridge_fit(X, y, lam)
    if coef is None:
        return None
    resid = [yy - sum(c * v for c, v in zip(coef, row)) for row, yy in zip(X, y)]
    return {"coef": coef,
            "sigma": sd(resid) or 13.5,
            "n_games": len(X),
            "lam": lam,
            "hfa": coef[0],
            "ratings": {t: coef[1 + i] for i, t in enumerate(TEAMS)}}


def predict_margin(model, home, away, neutral=False):
    if model is None:
        return None
    r = model["ratings"]
    hfa = 0.0 if neutral else model["hfa"]
    return r[home] - r[away] + hfa


def pythag_ratings(games, weeks):
    pf, pa, gp = Counter(), Counter(), Counter()
    for g in games:
        if g["week"] not in set(weeks) or g["status"] != "FINAL":
            continue
        h, a = g["home"], g["away"]
        pf[h] += g["home_score"]; pa[h] += g["away_score"]
        pf[a] += g["away_score"]; pa[a] += g["home_score"]
        gp[h] += 1; gp[a] += 1
    r = {}
    for t in TEAMS:
        if gp[t] == 0 or pf[t] + pa[t] == 0:
            r[t] = 0.0
        else:
            r[t] = math.sqrt(pf[t] / (pf[t] + pa[t]))
    return r, {t: gp[t] for t in TEAMS}


def fit_pythag_model(games, train_weeks):
    """margin = b0 + b1*(rate_home - rate_away) + b2*home ; least squares on 3 params."""
    we = set(train_weeks)
    rates, _ = pythag_ratings(games, we)
    X, y = [], []
    for g in games:
        if g["week"] not in we or g["status"] != "FINAL":
            continue
        X.append([1.0, rates[g["home"]] - rates[g["away"]]])
        y.append(g["home_score"] - g["away_score"])
    if len(X) < 8:
        return None
    p = 2
    XtX = [[sum(row[i] * row[j] for row in X) for j in range(p)] for i in range(p)]
    Xty = [sum(row[i] * t for row, t in zip(X, y)) for i in range(p)]
    coef = solve(XtX, Xty)
    if coef is None:
        return None
    resid = [yy - sum(c * v for c, v in zip(coef, row)) for row, yy in zip(X, y)]
    return {"coef": coef, "sigma": sd(resid) or 13.5, "rates": rates, "n_games": len(X)}


def predict_margin_pythag(model, home, away, neutral=False):
    if model is None:
        return None
    r = model["rates"]
    b0, b1 = model["coef"]
    hfa = 0.0 if neutral else b0
    return hfa + b1 * (r[home] - r[away])


def naive_total_model(games, train_weeks):
    """Second, deliberately simple total estimator: mean points in each club's games.

    Published side by side with the ridge total until a walk-forward comparison picks one.
    It ignores the opponent, so it is a benchmark, not a competitor.
    """
    we = set(train_weeks)
    tot = defaultdict(list)
    for g in games:
        if g["week"] not in we or g["status"] != "FINAL":
            continue
        t = g["home_score"] + g["away_score"]
        tot[g["home"]].append(t)
        tot[g["away"]].append(t)
    lg = mean([t for v in tot.values() for t in v]) or 45.0
    return {"team_mean": {k: (mean(v) if v else lg) for k, v in tot.items()},
            "league_mean": lg, "n_games": sum(1 for g in games if g["week"] in we and g["status"] == "FINAL")}


def predict_total_naive(model, home, away):
    if model is None:
        return None
    m = model["team_mean"]
    a, b = m.get(home), m.get(away)
    if a is None or b is None:
        return model["league_mean"]
    return (a + b) / 2.0


def fit_total_model(games, train_weeks, lam=10.0):
    """total points = c + off_home + def_away + off_away + def_home (off/def split, ridge)."""
    we = set(train_weeks)
    idx = {t: i for i, t in enumerate(TEAMS)}
    X, y = [], []
    for g in games:
        if g["week"] not in we or g["status"] != "FINAL":
            continue
        row = [0.0] * (1 + 4 * len(TEAMS))
        row[0] = 1.0
        row[1 + idx[g["home"]]] = 1.0                 # home offense
        row[1 + 32 + idx[g["away"]]] = 1.0            # away offense
        row[1 + 64 + idx[g["home"]]] = -1.0           # home defense (points allowed)
        row[1 + 96 + idx[g["away"]]] = -1.0           # away defense
        X.append(row)
        y.append(g["home_score"] + g["away_score"])
    if len(X) < 16:
        return None
    coef = ridge_fit(X, y, lam)
    if coef is None:
        return None
    resid = [yy - sum(c * v for c, v in zip(coef, row)) for row, yy in zip(X, y)]
    return {"coef": coef, "sigma": sd(resid) or 13.0, "n_games": len(X), "lam": lam}


def predict_total(model, home, away):
    if model is None:
        return None
    c = model["coef"]
    idx = {t: i for i, t in enumerate(TEAMS)}
    return (c[0] + c[1 + idx[home]] + c[1 + 32 + idx[away]]
            - c[1 + 64 + idx[home]] - c[1 + 96 + idx[away]])


def american_to_prob(ml):
    if ml is None:
        return None
    ml = float(ml)
    return (-ml) / ((-ml) + 100) if ml < 0 else 100 / (ml + 100)


def prob_to_american(p):
    if p is None or p <= 0 or p >= 1:
        return None
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


# ----------------------------------------------------------------------------- walk-forward
def walk_forward(games, start_week=5, last_week=10):
    """For each scoring week t, choose lambda by nested walk-forward inside the training window."""
    rows = []
    finals = [g for g in games if g["status"] == "FINAL"]
    for t in range(start_week, last_week + 1):
        train = [w for w in range(1, t)]
        target = [g for g in finals if g["week"] == t]
        if not target or len(train) < 3:
            continue
        # nested lambda selection: fit on weeks < u, score week u, for u in 3..t
        best = None
        for lam in LAMBDAS:
            errs = 0.0
            n = 0
            for u in range(3, t):
                m = fit_margin_model(games, [w for w in train if w < u], lam)
                if m is None:
                    continue
                for g in finals:
                    if g["week"] != u:
                        continue
                    pred = predict_margin(m, g["home"], g["away"], g.get("neutral_site", False))
                    errs += (pred - (g["home_score"] - g["away_score"])) ** 2
                    n += 1
            if n == 0:
                continue
            score = errs / n
            if best is None or score < best[0]:
                best = (score, lam)
        lam = best[1] if best else 10.0
        m1 = fit_margin_model(games, train, lam)
        m2 = fit_pythag_model(games, train)
        mt = fit_total_model(games, train)
        nt = naive_total_model(games, train)
        for g in target:
            actual_margin = g["home_score"] - g["away_score"]
            actual_total = g["home_score"] + g["away_score"]
            neutral = g.get("neutral_site", False)
            p1 = predict_margin(m1, g["home"], g["away"], neutral)
            p2 = predict_margin_pythag(m2, g["home"], g["away"], neutral)
            pt = predict_total(mt, g["home"], g["away"]) if mt else None
            pt2 = predict_total_naive(nt, g["home"], g["away"])
            rows.append({
                "week": t, "game": f"{g['away']}@{g['home']}", "home": g["home"], "away": g["away"],
                "neutral": neutral,
                "actual_margin": actual_margin, "actual_total": actual_total,
                "pred_margin_ridge": p1, "pred_margin_pythag": p2, "pred_total": pt,
                "pred_total_naive": pt2,
                "sigma_margin": m1["sigma"] if m1 else None,
                "sigma_total": mt["sigma"] if mt else None,
                "lambda": lam,
                "train_games": m1["n_games"] if m1 else 0,
                "home_score": g["home_score"], "away_score": g["away_score"],
                "source": g.get("source"),
            })
    return rows



# ----------------------------------------------------------------------------- signal evaluation
def evaluate_strategies(wf, sigma_margin_default=13.5):
    """Every strategy is scored on the SAME frozen walk-forward forecasts.

    A "bet" is defined by the rule only; no market price exists in this repository, so the
    realised-price ROI column is always None (never estimated).
    """
    out = {}

    # S3: side. Bet the model's favourite at the model's own fair line, i.e. "if the market
    # were exactly our fair line, do we beat it?" That is a pure signal test, not a staking test.
    rows = [r for r in wf if r["pred_margin_ridge"] is not None]
    correct, conf_pairs, margins = [], [], []
    for r in rows:
        mu = r["pred_margin_ridge"]
        act = r["actual_margin"]
        pick_home = mu > 0
        win = (act > 0) if pick_home else (act < 0)
        if act == 0:
            win = False   # push in a spread sense; counted as non-win, disclosed
        correct.append(1 if win else 0)
        conf_pairs.append((f"{r['week']}-{r['game']}", [(0.5 + 0.5 * abs(mu) / (abs(mu) + 6), 1 if win else 0)]))
        margins.append(mu)
    n = len(correct)
    k = sum(correct)
    out["S3_side"] = {
        "id": "S3", "label": "Side: model's own favourite vs its fair line",
        "n": n, "hits": k, "rate": round(k / n, 4) if n else None,
        "p_vs_constant": binom_test_two_sided(k, n) if n else None,
        "ci95": [round(x, 4) for x in wilson(k, n)] if n else None,
    }

    # S4: total. Bet over/under the model's own fair total.
    rows = [r for r in wf if r["pred_total"] is not None]
    correct, conf_pairs = [], []
    for r in rows:
        mu = r["pred_total"]
        act = r["actual_total"]
        pick_over = mu > 45.0     # a rule frozen before scoring: bet over only when fair total > 45
        win = (act > mu) if pick_over else (act < mu)
        if act == mu:
            win = False
        correct.append(1 if win else 0)
        conf_pairs.append((f"{r['week']}-{r['game']}", [(0.5, 1 if win else 0)]))
    n2 = len(correct); k2 = sum(correct)
    out["S4_total"] = {
        "id": "S4", "label": "Total: model's own fair total (over when fair > 45)",
        "n": n2, "hits": k2, "rate": round(k2 / n2, 4) if n2 else None,
        "p_vs_constant": binom_test_two_sided(k2, n2) if n2 else None,
        "ci95": [round(x, 4) for x in wilson(k2, n2)] if n2 else None,
    }

    # S5: second total estimator (naive club mean) scored the same way, so the two are comparable
    rows = [r for r in wf if r["pred_total_naive"] is not None]
    correct = []
    for r in rows:
        mu = r["pred_total_naive"]
        act = r["actual_total"]
        pick_over = mu > 45.0
        win = (act > mu) if pick_over else (act < mu)
        if act == mu:
            win = False
        correct.append(1 if win else 0)
    n5 = len(correct); k5 = sum(correct)
    out["S5_total_naive"] = {
        "id": "S5", "label": "Total: naive club-mean baseline (over when mean > 45)",
        "n": n5, "hits": k5, "rate": round(k5 / n5, 4) if n5 else None,
        "p_vs_constant": binom_test_two_sided(k5, n5) if n5 else None,
        "ci95": [round(x, 4) for x in wilson(k5, n5)] if n5 else None,
    }

    # S1: proper-score version of the side (Brier skill vs a constant p=0.5 baseline)
    probs, outs, clusters = [], [], []
    for r in wf:
        mu = r["pred_margin_ridge"]
        sg = r["sigma_margin"] or sigma_margin_default
        p = phi(mu / sg)
        y = 1 if r["actual_margin"] > 0 else 0
        if r["actual_margin"] == 0:
            y = 0.5
        probs.append(p); outs.append(y); clusters.append((f"{r['week']}-{r['game']}", [(p, y)]))
    b_model = brier(probs, outs); b_base = brier([0.5] * len(outs), outs)
    lo, hi = game_cluster_bootstrap(clusters)
    out["S1_side_proper"] = {
        "id": "S1", "label": "Side as a probability (Brier skill vs constant 0.5)",
        "n": len(probs), "brier_model": round(b_model, 5), "brier_baseline": round(b_base, 5),
        "brier_skill_score": round(1 - b_model / b_base, 5) if b_base else None,
        "cluster_ci95_brier": [round(lo, 5), round(hi, 5)] if lo is not None else None,
        "logloss_model": round(logloss(probs, [1 if y > 0.5 else 0 for y in outs]), 5),
    }

    # S2: alt estimator (Pythagorean) shown beside the primary (two-model rule)
    p2, o2 = [], []
    for r in wf:
        if r["pred_margin_pythag"] is None:
            continue
        sg = r["sigma_margin"] or sigma_margin_default
        p2.append(phi(r["pred_margin_pythag"] / sg))
        o2.append(1 if r["actual_margin"] > 0 else (0.5 if r["actual_margin"] == 0 else 0))
    out["S2_side_pythag"] = {
        "id": "S2", "label": "Side as a probability, Pythagorean estimator",
        "n": len(p2), "brier_model": round(brier(p2, o2), 5),
        "brier_baseline": round(brier([0.5] * len(o2), o2), 5),
        "brier_skill_score": round(1 - brier(p2, o2) / brier([0.5] * len(o2), o2), 5) if o2 else None,
    }
    # multiplicity: BH over the tests that have a p-value
    tests = [(k, v["p_vs_constant"]) for k, v in out.items() if v.get("p_vs_constant") is not None]
    adj = bh_adjust([t[1] for t in tests], q=0.10) if tests else []
    for (k, _), a in zip(tests, adj):
        out[k]["bh_threshold"] = round(a[1], 5)
        out[k]["bh_significant"] = bool(a[2])
    return out


def wilson(k, n, z=1.959964):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def luck_panel(wf, games):
    """Removal of luck: how much of each club's record is explained by scoring margin?"""
    rows = []
    by_team = defaultdict(list)
    for g in games:
        if g["status"] != "FINAL":
            continue
        m = g["home_score"] - g["away_score"]
        by_team[g["home"]].append(m)
        by_team[g["away"]].append(-m)
    for t in TEAMS:
        ms = by_team.get(t, [])
        if not ms:
            continue
        wins = sum(1 for x in ms if x > 0)
        losses = sum(1 for x in ms if x < 0)
        ties = sum(1 for x in ms if x == 0)
        gp = len(ms)
        # Pythagorean expectation (Pythagenpat-free, 2.37 exponent as published by Pro-Football-Ref
        # is NOT an official NFL figure; we therefore publish the plain method and the exponent used)
        pf = sum(1 for x in ms if x > 0)  # placeholder replaced below
        margin_mean = mean(ms)
        one_score = sum(1 for x in ms if abs(x) <= 8)
        rows.append({
            "team": t, "name": TEAM_NAME[t], "games": gp,
            "w": wins, "l": losses, "t": ties,
            "actual_win_pct": round((wins + 0.5 * ties) / gp, 4),
            "mean_margin": round(margin_mean, 2),
            "sd_margin": round(sd(ms), 2) if gp > 1 else None,
            "one_score_games": one_score,
            "one_score_rate": round(one_score / gp, 4),
            "margin_based_expected_win_pct": round(phi(margin_mean / (sd(ms) or 13.5)), 4),
            "luck_residual": round((wins + 0.5 * ties) / gp - phi(margin_mean / (sd(ms) or 13.5)), 4),
            "source": SRC["standings"],
            "method_note": "expected win% = Phi(mean margin / sd margin); residual = actual - expected",
        })
    rows.sort(key=lambda r: -r["luck_residual"])
    return rows


def correlation_panel(games):
    """Correlations computed only from official numbers, each published with n and a CI."""
    rows = []
    finals = [g for g in games if g["status"] == "FINAL"]
    if len(finals) < 10:
        return rows

    def corr(xs, ys):
        n = len(xs)
        mx, my = mean(xs), mean(ys)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        sxx = sum((x - mx) ** 2 for x in xs)
        syy = sum((y - my) ** 2 for y in ys)
        if sxx == 0 or syy == 0:
            return None
        return sxy / math.sqrt(sxx * syy)

    def ci_r(r, n):
        if r is None or n < 4:
            return (None, None)
        z = 0.5 * math.log((1 + r) / (1 - r))
        se = 1 / math.sqrt(n - 3)
        return (round(math.tanh(z - 1.96 * se), 4), round(math.tanh(z + 1.96 * se), 4))

    # 1. home margin vs total points, same game
    xs = [g["home_score"] - g["away_score"] for g in finals]
    ys = [g["home_score"] + g["away_score"] for g in finals]
    r = corr(xs, ys)
    rows.append({"pair": "home margin vs game total (same game)", "r": round(r, 4),
                 "n": len(xs), "ci95": ci_r(r, len(xs)), "source": SRC["sched"].format("{1-11}"),
                 "inputs": "final scores from official week schedule pages"})

    # 2. home score vs away score, same game
    xs = [g["home_score"] for g in finals]
    ys = [g["away_score"] for g in finals]
    r = corr(xs, ys)
    rows.append({"pair": "home points vs away points (same game)", "r": round(r, 4),
                 "n": len(xs), "ci95": ci_r(r, len(xs)), "source": SRC["sched"].format("{1-11}"),
                 "inputs": "final scores from official week schedule pages"})

    # 3. team's points scored vs points allowed, across team-games
    pf, pa = [], []
    for g in finals:
        pf += [g["home_score"], g["away_score"]]
        pa += [g["away_score"], g["home_score"]]
    r = corr(pf, pa)
    rows.append({"pair": "team points scored vs allowed (team-game)", "r": round(r, 4),
                 "n": len(pf), "ci95": ci_r(r, len(pf)), "source": SRC["standings"],
                 "inputs": "final scores from official week schedule pages"})

    # 4. successive-game margin autocorrelation (is a team's margin repeatable week to week?)
    pairs = []
    by_team = defaultdict(dict)
    for g in finals:
        by_team[g["home"]][g["week"]] = g["home_score"] - g["away_score"]
        by_team[g["away"]][g["week"]] = g["away_score"] - g["home_score"]
    xa, ya = [], []
    for t, d in by_team.items():
        ws = sorted(d)
        for a, b in zip(ws, ws[1:]):
            if b == a + 1:
                xa.append(d[a]); ya.append(d[b])
    r = corr(xa, ya)
    rows.append({"pair": "margin in week w vs margin in week w+1 (same club)", "r": round(r, 4),
                 "n": len(xa), "ci95": ci_r(r, len(xa)), "source": SRC["sched"].format("{1-11}"),
                 "inputs": "final scores from official week schedule pages"})
    return rows


def availability_panel(games, depth, inj_stored, inj_fresh, inactives):
    """Depth of the replacement, official starters, and designation->availability evidence."""
    # --- depth register audit
    audit = []
    for c in depth:
        slots = [s for u in c["units"] for s in u["slots"]]
        names = [n for s in slots for t in s["tiers"] for n in t]
        shared = [s for s in slots if s["tiers"] and len(s["tiers"][0]) > 1]
        empty = [s for s in slots if s["tiers"] and not s["tiers"][0]]
        multi = [s for s in slots if len(s["tiers"]) > 1]
        audit.append({
            "club": c["abbr"], "url": c["url"], "slots": len(slots), "named_players": len(names),
            "multi_tier_slots": len(multi), "rank1_shared_slots": len(shared),
            "rank1_empty_slots": len(empty),
            "status": "PARSED" if slots else "NOT PARSED (0 slots)",
            "as_of": None,
            "as_of_note": "no chart carries a dated 'as of' stamp that was captured",
        })

    # --- official starters from the two game books read this session
    starters = json.load(open(ROOT / "agency/data/derived/starters_w10.json"))
    inact = list(csv.DictReader(open(ROOT / "agency/data/derived/inactives_w10.csv")))

    def norm(n):
        return re.sub(r"[^a-z]", "", n.lower())

    def resolve(club, gb_name):
        """Game books print 'A.Williams'; depth charts print 'Antonio Williams'.

        Match on first initial + full surname against the club's own chart. Ambiguous
        matches are returned as AMBIGUOUS rather than guessed.
        """
        m = re.match(r"^([A-Za-z])\.?(.*)$", gb_name.strip())
        if not m:
            return None, None
        initial, surname = m.group(1).lower(), norm(m.group(2))
        # stored tuple is (normalised full name, chart position, tier, first initial)
        cands = sorted((nm, pos, tier) for (nm, pos, tier, ini) in idx[club]
                 if ini == initial and nm.endswith(surname))
        if len(cands) == 1:
            nm, pos, tier = cands[0]
            return tier, pos
        if len(cands) > 1:
            tiers = {c[2] for c in cands}
            if len(tiers) == 1:
                return min(tiers), cands[0][1]
            return "AMBIGUOUS", cands[0][1]
        return None, None

    idx = defaultdict(list)
    for a in audit:
        for c in depth:
            if c["abbr"] == a["club"]:
                for u in c["units"]:
                    for s in u["slots"]:
                        for tier_i, tier in enumerate(s["tiers"]):
                            for nm in tier:
                                first = norm(nm)[:1]
                                idx[a["club"]].append((norm(nm), s["pos"], tier_i + 1, first))
    for club in idx:
        idx[club].sort()

    rep = []
    for s in starters:
        club = s["team"]
        rank, chart_pos = resolve(club, s["player"])
        rep.append({
            "week": 10, "game": s["game"], "team": club, "unit": s["unit"], "position": s["position"],
            "official_starter": s["player"], "number": s["number"],
            "chart_position": chart_pos,
            "depth_rank_in_club_chart": rank,
            "replacement_depth": None,
            "depth_source": next((c["url"] for c in depth if c["abbr"] == club), None),
            "starter_source": s["source"],
        })

    # designation reliability from official game books + captured inactives (the only join we can
    # make with official evidence this session)
    fresh_rows = list(inj_fresh.values())
    desig = Counter(r["game_status"] or "none" for r in fresh_rows)
    inactive_keys = {(i["team"], norm(i["player"])) for i in inact}
    joined, confirmed_out = 0, 0
    for r in fresh_rows:
        key = (r["team"], norm(r["player"]))
        if key in inactive_keys:
            joined += 1
            if r["game_status"] == "Out":
                confirmed_out += 1
    return {
        "depth_audit": audit,
        "starters": rep,
        "inactives": inact,
        "designation_counts": dict(desig),
        "reliability": {
            "n_designated": sum(v for k, v in desig.items() if k != "none"),
            "n_no_designation": desig.get("none", 0),
            "n_joined_to_official_inactives": joined,
            "n_out_confirmed_inactive": confirmed_out,
            "note": ("A designation->play-rate table needs the official inactive list for every game. "
                     "Two official game books were read this session (4 clubs). That supports 4 clubs, "
                     "not 32, so no play rate is published."),
        },
    }


def injury_surprise_panel(inj_stored, inj_fresh):
    """The injury signal must be a SURPRISE, not a level.

    Official input: the league's own injury report for weeks 8, 9 and 10 (stored rows were read
    from nfl.com by an earlier session; week 10 was re-read in full this session).
    The surprise statistic is the transition of a player's practice status and game designation
    from one published report to the next. No level is used as a feature here.
    """
    weeks = [8, 9, 10]
    practice_order = {"Did Not Participate In Practice": 0,
                      "Limited Participation in Practice": 1,
                      "Full Participation in Practice": 2}
    game_order = {"Out": 0, "Doubtful": 1, "Questionable": 2, "": 3}
    by_week = {w: {} for w in weeks}
    for (w, team, player), r in inj_stored.items():
        if w in by_week:
            by_week[w][(team, player)] = r
    for (team, player), r in inj_fresh.items():
        by_week[10][(team, player)] = {"pos": r["position"], "injury": r["injury"],
                                       "practice": r["practice_status"], "status": r["game_status"]}

    transitions = []
    for a, b in zip(weeks, weeks[1:]):
        for key, prev in by_week[a].items():
            cur = by_week[b].get(key)
            if cur is None:
                continue
            pa, pb = practice_order.get(prev["practice"]), practice_order.get(cur["practice"])
            ga, gb = game_order.get(prev["status"], 3), game_order.get(cur["status"], 3)
            transitions.append({
                "team": key[0], "player": key[1], "from_week": a, "to_week": b,
                "practice_from": prev["practice"], "practice_to": cur["practice"],
                "practice_delta": (pb - pa) if (pa is not None and pb is not None) else None,
                "game_from": prev["status"], "game_to": cur["status"],
                "game_delta": (gb - ga) if (ga is not None and gb is not None) else None,
                "newly_designated": (prev["status"] in ("", None) and cur["status"] not in ("", None)),
                "source": SRC["injuries"].format("{8|9|10}"),
            })
    # summarise the surprise distribution
    worse = sum(1 for t in transitions if t["practice_delta"] is not None and t["practice_delta"] < 0)
    better = sum(1 for t in transitions if t["practice_delta"] is not None and t["practice_delta"] > 0)
    same = sum(1 for t in transitions if t["practice_delta"] == 0)
    new_dsg = sum(1 for t in transitions if t["newly_designated"])
    n = len(transitions)
    # exact binomial test: are deteriorations and improvements symmetric?
    p_sym = binom_test_two_sided(worse, worse + better) if (worse + better) else None
    return {
        "n_transitions": n,
        "practice_worse": worse, "practice_better": better, "practice_unchanged": same,
        "p_symmetry": p_sym,
        "newly_designated": new_dsg,
        "ci95_worse_share": [round(x, 4) for x in wilson(worse, worse + better)] if (worse + better) else None,
        "rows": transitions,
        "method_note": ("surprise = change in published practice/game status between consecutive "
                        "official weekly reports; a level (e.g. 'Out') is deliberately not used"),
    }


def fixture_context_panel(games):
    """Fixture context built ONLY from published schedule facts (dates, rest, travel distance).

    Rest days are exact: consecutive listed game dates. Travel distance is great-circle distance
    between published home venues; venues are only used where the official game centre states
    them. Where a venue is unknown the distance is left None rather than guessed.
    """
    # Published venue facts gathered from official game centres read directly (2026-11-15) and
    # from the game books' own headers. Only these are used; everything else stays blank.
    VENUE = {
        "WAS": ("MetLife Stadium", "East Rutherford, NJ"),
        "NYG": ("MetLife Stadium", "East Rutherford, NJ"),
        "NE": ("Gillette Stadium", "Foxborough, MA"),
        "DET": ("Ford Field", "Detroit, MI"),
        "SEA": ("Lumen Field", "Seattle, WA"),
        "LA": ("SoFi Stadium", "Inglewood, CA"),
        "LAC": ("SoFi Stadium", "Inglewood, CA"),
    }
    last = {}
    rows = []
    for g in sorted(games, key=lambda x: (x["week"], x["date_iso"] or "")):
        if g["status"] != "FINAL":
            continue
        for side, team in (("home", g["home"]), ("away", g["away"])):
            prev = last.get(team)
            rest = None
            if prev and g["date_iso"] and prev.get("date_iso"):
                from datetime import date
                try:
                    d1 = date.fromisoformat(prev["date_iso"]); d2 = date.fromisoformat(g["date_iso"])
                    rest = (d2 - d1).days - 1
                except Exception:
                    rest = None
            rows.append({
                "week": g["week"], "game": f"{g['away']}@{g['home']}", "team": team, "side": side,
                "date": g["date_iso"],
                "rest_days": rest,
                "neutral_site": bool(g.get("neutral_site")),
                "venue": VENUE.get(g["home"], (None, None))[0] if side == "home" else None,
                "venue_city": VENUE.get(g["home"], (None, None))[1] if side == "home" else None,
                "venue_status": ("OFFICIAL_GAME_BOOK" if g["home"] in VENUE else "NOT_CAPTURED"),
                "source": g.get("source"),
            })
            last[team] = {"date_iso": g["date_iso"]}
    return rows

# ----------------------------------------------------------------------------- main
def main():
    out = ROOT / "agency/data/out"
    out.mkdir(parents=True, exist_ok=True)

    games = load_games()
    finals = [g for g in games if g["status"] == "FINAL"]
    standings = load_standings()

    # ---- reconciliation of standings against the results feed (both official)
    W, L, T, PF, PA = Counter(), Counter(), Counter(), Counter(), Counter()
    for g in finals:
        h, a = g["home"], g["away"]
        PF[h] += g["home_score"]; PA[h] += g["away_score"]
        PF[a] += g["away_score"]; PA[a] += g["home_score"]
        if g["home_score"] > g["away_score"]:
            W[h] += 1; L[a] += 1
        elif g["away_score"] > g["home_score"]:
            W[a] += 1; L[h] += 1
        else:
            T[h] += 1; T[a] += 1
    recon = []
    for t in TEAMS:
        s = standings[t]
        recon.append({
            "team": t, "name": TEAM_NAME[t],
            "feed_w": W[t], "feed_l": L[t], "feed_t": T[t], "feed_pf": PF[t], "feed_pa": PA[t],
            "official_w": s["w"], "official_l": s["l"], "official_t": s["t"],
            "official_pf": s["pf"], "official_pa": s["pa"],
            "match": (W[t], L[t], T[t], PF[t], PA[t]) == (s["w"], s["l"], s["t"], s["pf"], s["pa"]),
            "source": SRC["standings"],
        })
    n_match = sum(1 for r in recon if r["match"])
    json.dump({"rows": recon, "n_teams": len(recon), "n_match": n_match,
               "n_finals_in_feed": len(finals), "captured_utc": STAMP,
               "source": SRC["standings"]},
              open(out / "reconciliation.json", "w"), indent=1)

    # ---- walk-forward backtest rows
    wf = walk_forward(games, 5, 10)
    json.dump(wf, open(out / "walkforward.json", "w"), indent=1)

    # ---- prospective origination for week 11 (side -> total -> moneyline)
    train_weeks = list(range(1, 11))
    lam_sel = 10.0
    m1 = fit_margin_model(games, train_weeks, lam_sel)
    m2 = fit_pythag_model(games, train_weeks)
    mt = fit_total_model(games, train_weeks)
    hfa = m1["hfa"] if m1 else None
    fixtures = list(csv.DictReader(open(ROOT / "agency/data/derived/week11_fixtures.csv")))
    origin = []
    for f in fixtures:
        home, away = f["home"], f["away"]
        neutral = f["neutral_site"].strip().lower() == "true"
        pm1 = predict_margin(m1, home, away, neutral)
        pm2 = predict_margin_pythag(m2, home, away, neutral)
        pt = predict_total(mt, home, away)
        s1 = m1["sigma"] if m1 else None
        st = mt["sigma"] if mt else None
        # side: model fair spread is the expected home margin; P(home covers x) = Phi((mu-x)/sigma)
        p_home_cover_0 = phi(pm1 / s1) if pm1 is not None and s1 else None
        fair_total = pt
        p_over_fair = 0.5 if pt is not None else None
        p_home_ml = phi(pm1 / s1) if pm1 is not None and s1 else None
        origin.append({
            "week": 11, "away": away, "home": home, "kickoff_et": f["kickoff_et"],
            "network": f["network"], "neutral": neutral,
            "stage_side_fair": round(pm1, 2) if pm1 is not None else None,
            "stage_side_fair_alt": round(pm2, 2) if pm2 is not None else None,
            "stage_side_gap": round(pm1 - pm2, 2) if (pm1 is not None and pm2 is not None) else None,
            "stage_total_fair": round(pt, 1) if pt is not None else None,
            "stage_ml_fair_prob": round(p_home_ml, 4) if p_home_ml is not None else None,
            "stage_ml_fair_price": prob_to_american(p_home_ml) if p_home_ml else None,
            "sigma_margin": round(s1, 2) if s1 else None,
            "sigma_total": round(st, 2) if st else None,
            "market_line": None, "market_price": None,
            "difference_vs_market": None,
            "market_status": "NO OFFICIAL MARKET SOURCE — see policy",
            "inputs": {
                "model": "ridge margin + ridge total, lam=%.0f" % lam_sel,
                "train_games": m1["n_games"] if m1 else 0,
                "train_weeks": "1-10",
                "hfa_points": round(hfa, 2) if hfa is not None else None,
                "ratings_source": "data/desk/games.json + this session's two Week 10 finals",
            },
            "source": SRC["sched"].format(11),
        })
    # hashes for provenance
    def sha(p):
        return hashlib.sha256(open(ROOT / p, "rb").read()).hexdigest()
    prov = {
        "captured_utc": STAMP,
        "inputs": {p: sha(p) for p in [
            "data/desk/games.json", "data/desk/standings.json", "data/desk/depth.json",
            "agency/data/derived/week10_final_games.csv",
            "agency/data/derived/inactives_w10.csv",
            "agency/data/derived/injury_designations_w10_2026.csv",
            "agency/data/derived/week11_fixtures.csv"]},
        "model": {"type": "ridge margin (opponent-aware) + pythagorean alt + ridge total",
                  "lambda_grid": LAMBDAS, "lambda_fixed_for_w11": lam_sel,
                  "fit_weeks": "1-10", "n_games": m1["n_games"] if m1 else 0,
                  "hfa_points": round(hfa, 2) if hfa is not None else None,
                  "sigma_margin": round(m1["sigma"], 2) if m1 else None,
                  "sigma_total": round(mt["sigma"], 2) if mt else None},
    }
    # ---- signal evaluation on the frozen walk-forward forecasts
    strat = evaluate_strategies(wf)
    # ---- removal of luck
    luck = luck_panel(wf, games)
    # ---- correlations (official numbers only)
    corrs = correlation_panel(games)
    # ---- availability / depth
    inj_stored, inj_fresh = load_injuries()
    depth = load_depth()
    avail = availability_panel(games, depth, inj_stored, inj_fresh, None)

    json.dump(prov, open(out / "provenance.json", "w"), indent=1)
    json.dump(origin, open(out / "origination_week11.json", "w"), indent=1)
    json.dump(strat, open(out / "strategies.json", "w"), indent=1)
    json.dump(luck, open(out / "luck.json", "w"), indent=1)
    json.dump(corrs, open(out / "correlations.json", "w"), indent=1)
    json.dump(avail, open(out / "availability.json", "w"), indent=1)
    injp = injury_surprise_panel(inj_stored, inj_fresh)
    json.dump(injp, open(out / "injury_surprise.json", "w"), indent=1)
    fix = fixture_context_panel(games)
    json.dump(fix, open(out / "fixture_context.json", "w"), indent=1)
    print("injury transitions", injp["n_transitions"], "worse", injp["practice_worse"],
          "better", injp["practice_better"], "p", injp["p_symmetry"])
    print("fixture rows", len(fix), "with rest", sum(1 for r in fix if r["rest_days"] is not None))
    print("strategies:", {k: (v["n"], v.get("rate") or v.get("brier_skill_score")) for k, v in strat.items()})
    print("luck top:", [(r["team"], r["luck_residual"]) for r in luck[:3]])
    print("corr:", [(c["pair"][:38], c["r"], c["n"]) for c in corrs])

    # ---- fair-line register: every market we originate, one row, side first
    print("recon", n_match, "/", len(recon), "finals", len(finals), "wf rows", len(wf),
          "originated", len(origin))
    if origin:
        print("example", json.dumps(origin[0], indent=1)[:800])


if __name__ == "__main__":
    main()
