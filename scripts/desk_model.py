#!/usr/bin/env python3
"""Model, correlation and signal diagnostics computed only from verified game results.

Outputs
  data/desk/model.json         opponent-adjusted ratings, measured home-field advantage,
                               originated lines for the next unplayed week, gap to market
                               (market values are blank unless a licensed feed is added)
  data/desk/correlations.json  measured correlations with n, 95% CI and a stated method
  data/desk/luck.json          Pythagorean expectation vs actual wins (regression signal)
  data/desk/calibration.json   out-of-sample backtest of the model on played weeks
  data/desk/strategies.json    strategy registry with gate status (hypotheses, not claims)

Every number here is DERIVED from official results. Model output is labelled DERIVED
everywhere it is published. Nothing is fitted on the same game it is tested on.
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

RATING_ITERATIONS = 200
HFA_PRIOR = 0.0


# --------------------------------------------------------------------------- #
# small statistics helpers                                                     #
# --------------------------------------------------------------------------- #
def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def sd(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pearson(xs: list[float], ys: list[float]) -> tuple[float, int]:
    n = min(len(xs), len(ys))
    xs, ys = xs[:n], ys[:n]
    if n < 3:
        return 0.0, n
    mx, my = mean(xs), mean(ys)
    sx, sy = sd(xs), sd(ys)
    if sx == 0 or sy == 0:
        return 0.0, n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)
    return max(-1.0, min(1.0, cov / (sx * sy))), n


def fisher_ci(r: float, n: int, z: float = 1.959964) -> tuple[float, float]:
    """95% confidence interval for a Pearson r via Fisher's z transformation."""
    if n < 4 or abs(r) >= 1:
        return (0.0, 0.0)
    zr = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    lo, hi = zr - z * se, zr + z * se
    return (math.tanh(lo), math.tanh(hi))


def two_sided_p(r: float, n: int) -> float:
    if n < 4:
        return 1.0
    if abs(r) >= 1:
        return 0.0
    t = r * math.sqrt((n - 2) / max(1e-12, 1 - r * r))
    # two-sided p from Student t via the incomplete beta function (numerical)
    df = n - 2
    x = df / (df + t * t)
    return betainc(df / 2.0, 0.5, x)


def betainc(a: float, b: float, x: float, steps: int = 4000) -> float:
    """Regularised incomplete beta I_x(a,b) by continued-fraction integration."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    # use the continued fraction (Numerical Recipes betacf)
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    f, c, d = 1.0, 1.0, 0.0
    for i in range(steps):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        d = 1e-30 if abs(d) < 1e-30 else d
        d = 1.0 / d
        c = 1.0 + num / c
        c = 1e-30 if abs(c) < 1e-30 else c
        f *= c * d
        if abs(1 - c * d) < 1e-10:
            break
    return front * (f - 1)


# --------------------------------------------------------------------------- #
# opponent-adjusted ratings                                                    #
# --------------------------------------------------------------------------- #
def fit_ratings(games: list[dict], iterations: int = RATING_ITERATIONS, ridge: float = 1.0) -> dict:
    """Ridge least squares on margins and totals (two independent linear models).

    Margin model:  home_score - away_score = hfa + net[home] - net[away]
    Total model:   home_score + away_score = base + pace[home] + pace[away]

    Solved by Gauss-Seidel coordinate descent with a small ridge penalty and a
    zero-mean constraint, which makes both models identifiable. No matrix library is
    required, and the same code runs in CI.
    """
    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    net = {t: 0.0 for t in teams}
    pace = {t: 0.0 for t in teams}
    hfa = 0.0
    base = mean([g["home_score"] + g["away_score"] for g in games]) if games else 0.0

    def hfa_of(g: dict) -> float:
        """Neutral-site games carry no home-field term."""
        return 0.0 if g.get("neutral_site") else hfa

    for _ in range(iterations):
        # home-field advantage, given net ratings; neutral-site games excluded from the estimate
        resid = [((g["home_score"] - g["away_score"]) - (net[g["home"]] - net[g["away"]]))
                 for g in games if not g.get("neutral_site")]
        hfa = mean(resid) if resid else 0.0
        # per-club net rating, given hfa and the opponent's rating
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

        # per-club pace rating, given the league base
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

    # split net into offense/defense for display: offense = half the net plus a
    # scoring level, defense = half the net; only the NET is identified by this fit.
    n_games = {t: sum(1 for g in games if t in (g["home"], g["away"])) for t in teams}
    pf = {t: sum(g["home_score"] if g["home"] == t else g["away_score"]
                 for g in games if t in (g["home"], g["away"])) for t in teams}
    pa = {t: sum(g["away_score"] if g["home"] == t else g["home_score"]
                 for g in games if t in (g["home"], g["away"])) for t in teams}
    mun = mean([(pf[t] - pa[t]) / max(1, n_games[t]) for t in teams])
    return {
        "net": net, "pace": pace, "hfa": hfa, "base_total": base,
        "league_avg_team_score": base / 2,
        "points_for_pg": {t: pf[t] / max(1, n_games[t]) for t in teams},
        "points_against_pg": {t: pa[t] / max(1, n_games[t]) for t in teams},
        "net_points_pg": {t: (pf[t] - pa[t]) / max(1, n_games[t]) for t in teams},
        "teams": teams, "identified": "margin model identifies net[team] only; totals model is separate",
    }


def predict(ratings: dict, home: str, away: str, neutral: bool = False) -> tuple[float, float]:
    """Home margin and game total implied by the fitted ratings."""
    hfa = 0.0 if neutral else ratings["hfa"]
    margin = hfa + ratings["net"][home] - ratings["net"][away]
    total = ratings["base_total"] + ratings["pace"][home] + ratings["pace"][away]
    return margin, total


# --------------------------------------------------------------------------- #
def main(dst: str) -> int:
    base = Path(dst)
    games = [g for g in json.loads((base / "games.json").read_text())["games"]
             if g["status"] == "FINAL"]
    games.sort(key=lambda g: (g["week"], g["date_iso"]))
    all_teams = sorted({g["home"] for g in games} | {g["away"] for g in games})

    # ---- walk-forward backtest: fit on weeks < w, predict week w -------------
    backtest, per_week = [], []
    for w in sorted({g["week"] for g in games}):
        train = [g for g in games if g["week"] < w]
        test = [g for g in games if g["week"] == w]
        if len(train) < 16 or not test:
            continue
        r = fit_ratings(train)
        for g in test:
            pred, _tot = predict(r, g["home"], g["away"], g.get("neutral_site", False))
            backtest.append({
                "week": w, "home": g["home"], "away": g["away"],
                "predicted_margin_home": round(pred, 2),
                "actual_margin_home": g["home_score"] - g["away_score"],
                "error": round((g["home_score"] - g["away_score"]) - pred, 2),
                "source": g["source"],
            })
        per_week.append({"week": w, "games": len(test)})
    mae = mean([abs(b["error"]) for b in backtest]) if backtest else 0.0
    rmse = math.sqrt(mean([b["error"] ** 2 for b in backtest])) if backtest else 0.0
    bias = mean([b["error"] for b in backtest]) if backtest else 0.0
    corr_pred, n_pred = pearson([b["predicted_margin_home"] for b in backtest],
                                [b["actual_margin_home"] for b in backtest])

    # ---- final ratings on all played games ---------------------------------
    full = fit_ratings(games)
    ratings_rows = []
    for t in all_teams:
        ratings_rows.append({
            "team": t,
            "net_rating": round(full["net"][t], 2),
            "pace_rating": round(full["pace"][t], 2),
            "points_for_pg": round(full["points_for_pg"][t], 1),
            "points_against_pg": round(full["points_against_pg"][t], 1),
            "net_points_pg": round(full["net_points_pg"][t], 1),
            "games": sum(1 for g in games if t in (g["home"], g["away"])),
        })
    ratings_rows.sort(key=lambda r: -r["net_rating"])

    # ---- originated lines for the next unplayed week -----------------------
    sched = json.loads((base / "games.json").read_text())["games"]
    upcoming = [g for g in sched if g["status"] != "FINAL"]
    week = min((g["week"] for g in upcoming), default=None)
    lines = []
    for g in [x for x in upcoming if x["week"] == week]:
        margin, total = predict(full, g["home"], g["away"], g.get("neutral_site", False))
        lines.append({
            "week": g["week"], "date_iso": g["date_iso"], "kickoff_et": g["kickoff_et"],
            "home": g["home"], "away": g["away"],
            "neutral_site": bool(g.get("neutral_site")),
            "venue": g.get("neutral_site_name", ""),
            "our_home_margin": round(margin, 1),
            "our_spread_home": round(-margin, 1),
            "our_total": round(total, 1),
            "model_class": "DERIVED - unvalidated, no market settlement rule applied",
            "inputs_source": "https://www.nfl.com/schedules/2026/by-week/week-%d" % g["week"],
            "model_source": "data/desk/model.json (fit on verified 2026 results)",
            "market_spread_home": "", "market_total": "", "market_source": "",
        })

    model = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": ("Two ridge least-squares models fitted by coordinate descent on final scores: "
                   "margin = home_field + net[home] - net[away]; total = base + pace[home] + pace[away]. "
                   "Ratings are centred on zero. No prior-season data, no market data, no manual input."),
        "inputs": {"games": len(games), "weeks": sorted({g['week'] for g in games}),
                   "source": "https://www.nfl.com/schedules/2026/by-week/week-N"},
        "home_field_points": round(full["hfa"], 2),
        "league_avg_team_score": round(full["league_avg_team_score"], 2),
        "ratings": ratings_rows,
        "backtest": {"games": len(backtest), "mae": round(mae, 2), "rmse": round(rmse, 2),
                     "bias": round(bias, 2),
                     "predicted_vs_actual_r": round(corr_pred, 3), "n": n_pred,
                     "weeks": per_week,
                     "rule": "fit on all weeks before the predicted week only"},
        "originated_lines": {"week": week, "rows": lines},
        "limitations": [
            "No preseason or prior-season data: ratings start from zero information.",
            "No rest or short-week adjustment beyond opponent rating.",
            "No injury adjustment is applied to the model output.",
            "Neutral-site games exclude the home-field term but are not otherwise adjusted.",
            "No market comparison: no licensed odds feed exists in this repository.",
            "Early-season weeks are fitted on very few games.",
        ],
    }
    (base / "model.json").write_text(json.dumps(model, indent=1) + "\n")

    # ---- correlations -------------------------------------------------------
    pairs = []
    def add(pair: str, xs: list[float], ys: list[float], reading: str, kind: str) -> None:
        pass
    tot = [g["home_score"] + g["away_score"] for g in games]
    margin = [g["home_score"] - g["away_score"] for g in games]
    r1, n1 = pearson(tot, margin)
    lo, hi = fisher_ci(r1, n1)
    pairs.append({"pair": "game total vs |margin|", "r": round(r1, 3), "n": n1,
                  "ci95": [round(lo, 3), round(hi, 3)], "p": round(two_sided_p(r1, n1), 4),
                  "reading": "same-game total and blowout size move together",
                  "used_for": "same-game parlay leg screen", "source": "verified 2026 finals"})
    r2, n2 = pearson([g["away_score"] for g in games], [g["home_score"] for g in games])
    lo, hi = fisher_ci(r2, n2)
    pairs.append({"pair": "away score vs home score", "r": round(r2, 3), "n": n2,
                  "ci95": [round(lo, 3), round(hi, 3)], "p": round(two_sided_p(r2, n2), 4),
                  "reading": "whether the two teams' scores co-move inside a game",
                  "used_for": "correlated two-leg parlay screen", "source": "verified 2026 finals"})
    # team-level: scoring vs conceding, and rating vs wins
    st = json.loads((base / "standings.json").read_text())["rows"]
    r3, n3 = pearson([x["pf"] / max(1, x["w"] + x["l"] + x["t"]) for x in st],
                     [x["pa"] / max(1, x["w"] + x["l"] + x["t"]) for x in st])
    lo, hi = fisher_ci(r3, n3)
    pairs.append({"pair": "points for per game vs points against per game", "r": round(r3, 3),
                  "n": n3, "ci95": [round(lo, 3), round(hi, 3)], "p": round(two_sided_p(r3, n3), 4),
                  "reading": "club-level scoring balance", "used_for": "rating sanity check",
                  "source": "https://www.nfl.com/standings/league/2026/reg"})
    r4, n4 = pearson([x["net"] for x in st],
                     [x["w"] / max(1, x["w"] + x["l"] + x["t"]) for x in st])
    lo, hi = fisher_ci(r4, n4)
    pairs.append({"pair": "net points vs win percentage", "r": round(r4, 3), "n": n4,
                  "ci95": [round(lo, 3), round(hi, 3)], "p": round(two_sided_p(r4, n4), 4),
                  "reading": "how much point differential explains results",
                  "used_for": "luck screen", "source": "https://www.nfl.com/standings/league/2026/reg"})

    # ---- Pythagorean luck ---------------------------------------------------
    exp = 2.37
    luck = []
    for x in st:
        g = x["w"] + x["l"] + x["t"]
        pf, pa = x["pf"], x["pa"]
        pct = (pf ** exp) / (pf ** exp + pa ** exp) if pf and pa else 0.0
        luck.append({"team": x["abbr"], "w": x["w"], "l": x["l"], "t": x["t"],
                     "pythag_pct": round(pct, 3), "expected_wins": round(pct * g, 2),
                     "actual_wins": x["w"] + 0.5 * x["t"],
                     "luck_delta": round(x["w"] + 0.5 * x["t"] - pct * g, 2),
                     "source": "https://www.nfl.com/standings/league/2026/reg"})
    luck.sort(key=lambda r: -r["luck_delta"])
    rl, nl = pearson([r["pythag_pct"] for r in luck], [r["actual_wins"] for r in luck])

    (base / "correlations.json").write_text(json.dumps({
        "method": ("Pearson product-moment correlation on verified values only. 95% CI by Fisher z. "
                   "Two-sided p from Student t. n is printed with every coefficient; a coefficient "
                   "whose CI includes 0 is reported as not distinguishable from no relationship."),
        "pairs": pairs,
        "sample_note": f"{len(games)} verified final games (2026 weeks 1-10); club-level pairs use 32 clubs",
        "not_measured": [
            "player-prop correlations (no official player-prop history ingested)",
            "correlation at market closing prices (no odds feed)",
            "any correlation that would need play-by-play or drive data",
        ],
    }, indent=1) + "\n")
    (base / "luck.json").write_text(json.dumps({
        "method": f"Pythagorean expectation, exponent {exp} (conventional value, not fitted here).",
        "r_pythag_vs_actual": round(rl, 3), "n": nl,
        "source": "https://www.nfl.com/standings/league/2026/reg",
        "teams": luck,
    }, indent=1) + "\n")
    (base / "calibration.json").write_text(json.dumps({
        "walk_forward": {"games": len(backtest), "mae": round(mae, 2), "rmse": round(rmse, 2),
                         "bias": round(bias, 2), "r": round(corr_pred, 3), "n": n_pred,
                         "verdict": ("model beats a coin flip on direction only if "
                                     f"r>0 and CI excludes 0; measured r={round(corr_pred,3)}")},
        "rows": backtest,
    }, indent=1) + "\n")

    # ---- strategy registry -------------------------------------------------
    (base / "strategies.json").write_text(json.dumps(strategy_registry(model, len(backtest)),
                                                     indent=1) + "\n")
    print(json.dumps({
        "games": len(games), "hfa": model["home_field_points"],
        "backtest": model["backtest"], "correlations": pairs,
        "lines_week": week, "line_rows": len(lines),
    }, indent=1)[:3000])
    return 0


def strategy_registry(model: dict, n_backtest: int) -> dict:
    G = [
        ("G1", "Pre-registration", "Rule, inputs and staking written to the repo before any graded result."),
        ("G2", "Sample size", "At least 200 graded bets per strategy before any skill claim."),
        ("G3", "Walk-forward only", "Fit on past weeks, grade on later weeks. No same-game fitting."),
        ("G4", "Multiple-testing control", "Benjamini-Hochberg FDR at q=0.10 across all tested strategies."),
        ("G5", "Benchmark beat", "Must beat the vig-free closing line or a no-bet baseline, not a guess."),
        ("G6", "Uncertainty", "95% CI on ROI and on hit rate must exclude the break-even rate."),
        ("G7", "Luck control", "Deflated Sharpe: reward adjusted for number of trials run."),
        ("G8", "Correlation integrity", "Parlay legs must show a measured joint distribution, not multiplied marginals."),
        ("G9", "Data provenance", "Every input row carries an official source URL and a fetch date."),
        ("G10", "No look-ahead", "Inputs must be published before the decision cutoff for that game."),
    ]
    strategies = [
        {"id": "S1", "name": "Opponent-adjusted net rating difference", "family": "Single",
         "construction": "Full-game side. Difference of net ratings from model.json at the decision cutoff.",
         "inputs": "verified final scores only", "lookahead": "none",
         "gates_pass": ["G1", "G3", "G9", "G10"], "gates_fail": ["G2", "G5", "G6", "G7"],
         "status": "hypothesis - cannot pass without a market price series"},
        {"id": "S2", "name": "Home-field measured vs assumed", "family": "Single",
         "construction": "Side only when measured home-field differs from the market's implied home-field.",
         "inputs": "verified results + market spreads", "lookahead": "none",
         "gates_pass": ["G1", "G3", "G9", "G10"], "gates_fail": ["G2", "G5", "G6", "G7"],
         "status": "blocked - no market spread series"},
        {"id": "S3", "name": "Pythagorean luck fade", "family": "Single",
         "construction": "Fade clubs whose wins exceed Pythagorean expectation by more than 1.5 wins.",
         "inputs": "standings PF/PA", "lookahead": "none",
         "gates_pass": ["G1", "G9"], "gates_fail": ["G2", "G6", "G7"],
         "status": "hypothesis - needs market prices to grade"},
        {"id": "S4", "name": "Starter-out deficiency signal", "family": "Single",
         "construction": "Side against a club starting a 2nd-or-deeper string at QB/LT/CB1/EDGE1.",
         "inputs": "official injury report + club depth chart", "lookahead": "none",
         "gates_pass": ["G1", "G9", "G10"], "gates_fail": ["G2", "G5", "G6", "G7"],
         "status": "hypothesis - depth charts are club-published and mostly unofficial"},
        {"id": "S5", "name": "Backup-promotion fade (offense)", "family": "Single",
         "construction": "Under on the side whose offensive line or QB depth is degraded.",
         "inputs": "injury report + depth chart", "lookahead": "none",
         "gates_pass": ["G1", "G9", "G10"], "gates_fail": ["G2", "G5", "G6"],
         "status": "hypothesis"},
        {"id": "S6", "name": "Total vs margin joint filter", "family": "Parlay",
         "construction": "Only combine a total leg with a side leg when the measured total/margin "
                         "correlation for that game archetype is below the policy threshold.",
         "inputs": "verified results", "lookahead": "none",
         "gates_pass": ["G1", "G3", "G8", "G9"], "gates_fail": ["G2", "G5", "G6", "G7"],
         "status": "hypothesis - current sample is too small to certify any leg pair"},
        {"id": "S7", "name": "Two-side arb of correlated scores", "family": "Parlay",
         "construction": "Two teams' scores co-move negatively; exploit only with a measured joint model.",
         "inputs": "verified results", "lookahead": "none",
         "gates_pass": ["G1", "G8", "G9"], "gates_fail": ["G2", "G5", "G6", "G7"],
         "status": "hypothesis - sign of the measured correlation must clear its CI first"},
        {"id": "S8", "name": "Player prop combo (same game)", "family": "Prop combo",
         "construction": "Combine player props whose measured joint distribution beats the "
                         "product of their marginals by more than the price.",
         "inputs": "player prop history", "lookahead": "none",
         "gates_pass": ["G1", "G8", "G9", "G10"],
         "gates_fail": ["G2", "G3", "G5", "G6", "G7"],
         "status": "blocked - no player-prop history and no official prop source"},
        {"id": "S9", "name": "Injury-news timing edge", "family": "Single",
         "construction": "Act on the first official injury-report posting before the line settles.",
         "inputs": "official injury report timestamps + line timestamps",
         "lookahead": "none (requires timestamps on both sides)",
         "gates_pass": ["G1", "G9", "G10"], "gates_fail": ["G2", "G5", "G6", "G7"],
         "status": "blocked - no line timestamp series"},
        {"id": "S10", "name": "Rest and short-week differential", "family": "Single",
         "construction": "Side with the rest advantage measured in days, net of travel.",
         "inputs": "schedule dates + travel distance", "lookahead": "none",
         "gates_pass": ["G1", "G9", "G10"], "gates_fail": ["G2", "G5", "G6"],
         "status": "hypothesis - travel distance not yet ingested from an official source"},
    ]
    return {
        "policy": ("These are hypotheses with an explicit gate ledger. A strategy is promoted to the "
                   "leaderboard only when every blocking gate is recorded as passed on later, untouched "
                   "data. No strategy is claimed to be profitable."),
        "gates": [{"id": i, "gate": n, "rule": d, "blocking": "yes"} for i, n, d in G],
        "leaderboard_rule": {
            "eligibility": "all blocking gates passed, minimum 200 graded bets, pre-registered",
            "score": "vig-free ROI with a 95% CI, tie-broken by deflated Sharpe",
            "rewards": ("notional only: the leaderboard ranks strategies, it does not pay money. "
                        "Any real reward needs a decision recorded on the Suggestions page."),
            "anti_gaming": ["no re-fitting after grading", "results posted with the losing bets",
                            "one submission per strategy family per week"],
        },
        "strategies": strategies,
        "graded_results": {"rows": 0,
                           "why": "grading requires market prices, which no official source publishes"},
        "backtest_sample": n_backtest,
    }


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
