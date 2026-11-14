#!/usr/bin/env python3
"""
X3 / model library shared by the market, backtest and correlation engines.

Two linear models, fitted by coordinate descent (no third-party dependency, so the
same arithmetic runs in CI):

    home_margin = hfa + net[home] - net[away]      (neutral-site games: hfa = 0)
    game_total  = base + pace[home] + pace[away]

Everything here is fitted on FINAL scores only, and callers are expected to fit on a
chronologically earlier subset than the games they score (walk-forward). Nothing in this
module reads a price, a market or a prior-season number.

The margin model identifies the DIFFERENCE net[home]-net[away]; the split of that
difference into offence and defence is not identified by this fit and is not published
from it anywhere.
"""
from __future__ import annotations

import math


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def sd(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pearson(xs, ys):
    n = min(len(xs), len(ys))
    if n < 3:
        return None, n
    xs, ys = xs[:n], ys[:n]
    mx, my = mean(xs), mean(ys)
    sx, sy = sd(xs), sd(ys)
    if sx == 0 or sy == 0:
        return None, n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)
    return max(-1.0, min(1.0, cov / (sx * sy))), n


def fisher_ci(r, n, z=1.959964):
    """95% CI for a Pearson r (Fisher z). Returns (None, None) when undefined."""
    if r is None or n < 4 or abs(r) >= 1:
        return None, None
    zr = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    return math.tanh(zr - z * se), math.tanh(zr + z * se)


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p):
    """Inverse standard normal (Acklam's rational approximation, |error| < 1.2e-9)."""
    if not 0 < p < 1:
        raise ValueError("p must be in (0,1)")
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


def fit(games, iterations=200, ridge=1.0):
    """Ridge fit of margin/pace ratings. `games` must be dicts with home/away scores.

    Neutral-site games contribute no home-field term, so the HFA is estimated only from
    games that had a home team.
    """
    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    net = {t: 0.0 for t in teams}
    pace = {t: 0.0 for t in teams}
    hfa = 0.0
    base = mean([g["home_score"] + g["away_score"] for g in games]) if games else 0.0

    def hfa_of(g):
        return 0.0 if g.get("neutral_site") else hfa

    for _ in range(iterations):
        resid = [((g["home_score"] - g["away_score"]) - (net[g["home"]] - net[g["away"]]))
                 for g in games if not g.get("neutral_site")]
        hfa = mean(resid) if resid else 0.0
        for t in teams:
            num, den = 0.0, ridge
            for g in games:
                if g["home"] == t:
                    num += (g["home_score"] - g["away_score"]) - hfa_of(g) + net[g["away"]]
                    den += 1.0
                elif g["away"] == t:
                    num += (g["away_score"] - g["home_score"]) + hfa_of(g) + net[g["home"]]
                    den += 1.0
            net[t] = num / den if den else 0.0
        m = mean(list(net.values()))
        net = {t: v - m for t, v in net.items()}
        for t in teams:
            num, den = 0.0, ridge
            for g in games:
                if g["home"] == t:
                    num += (g["home_score"] + g["away_score"]) - base - pace[g["away"]]
                    den += 1.0
                elif g["away"] == t:
                    num += (g["home_score"] + g["away_score"]) - base - pace[g["home"]]
                    den += 1.0
            pace[t] = num / den if den else 0.0
        m = mean(list(pace.values()))
        pace = {t: v - m for t, v in pace.items()}
        base = mean([g["home_score"] + g["away_score"] - pace[g["home"]] - pace[g["away"]]
                     for g in games]) if games else 0.0

    return {"net": net, "pace": pace, "hfa": hfa, "base_total": base,
            "teams": teams, "n_games": len(games)}


def predict(ratings, home, away, neutral=False):
    """(home margin, game total) implied by the fitted ratings."""
    hfa = 0.0 if neutral else ratings["hfa"]
    return (hfa + ratings["net"][home] - ratings["net"][away],
            ratings["base_total"] + ratings["pace"][home] + ratings["pace"][away])


def fair_probability(margin, sigma):
    """P(home wins) for a normal margin model: Phi(margin / sigma), tie excluded."""
    if sigma <= 0:
        return None
    return norm_cdf(margin / sigma)


def fair_price_decimal(prob):
    """Fair (zero-hold) decimal price for a probability. None when the probability is 0/1."""
    if prob is None or not 0 < prob < 1:
        return None
    return 1.0 / prob


def american_from_decimal(dec):
    if dec is None:
        return None
    if dec >= 2.0:
        return round((dec - 1) * 100)
    return -round(100 / (dec - 1))


def decimal_from_american(am):
    if am is None or am == 0:
        return None
    return 1 + (am / 100 if am > 0 else 100 / abs(am))


def devig_pair(p_home_dec, p_away_dec):
    """Multiplicative de-vig of a two-way market. Returns (p_home, p_away) or (None, None)."""
    if not p_home_dec or not p_away_dec:
        return None, None
    ih, ia = 1 / p_home_dec, 1 / p_away_dec
    s = ih + ia
    return ih / s, ia / s
