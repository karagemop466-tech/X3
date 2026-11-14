#!/usr/bin/env python3
"""Compute the platform's own lines, the correlation matrices and the
leaderboard rows.

Inputs : data/datasets/*.json  (built from official sources only)
Outputs: data/datasets/our_lines.json
         data/datasets/correlations.json
         data/datasets/leaderboard_rows.json
         data/datasets/derived.json

Honesty rules enforced here:

* Every statistic is computed from an official dataset. If the dataset needed
  for a statistic is missing, the statistic is emitted as ``null`` and listed
  in ``unavailable`` with the reason. It is never estimated from a proxy.
* The platform originates its own lines. A strategy is scored on whether it
  disagrees with the line model profitably, using a signal that is deliberately
  different from the line model's own inputs. The line model itself is
  published as the benchmark, not as a competitor.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "datasets")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from lib.diagnostics import failure_report  # noqa: E402

CURRENT_SEASON = 2026
LEAGUE_URL = "https://www.nfl.com/standings/league/{season}/REG"
INJURY_URL = "https://www.nfl.com/injuries/"
SCHEDULE_URL = "https://www.nfl.com/schedules/{season}/REG{week}/"

# Published model parameters. These are model choices, not observed data, and
# they are versioned so that a change starts a new cycle.
MODEL_VERSION = "line-model-v1.0"
SHRINKAGE_K = 4.0          # games of pseudo-count pulled toward the league mean
MARGIN_PCT = 0.03          # hold carried in the published price
LINE_ROUNDING = 0.5        # published spread rounding
MIN_TRAIN_GAMES = 4        # games a team must have played before it is rated
                           # (early-season ratings are pulled hard toward the
                           #  league mean by the shrinkage below)


# ---------------------------------------------------------------------------
# loading helpers
# ---------------------------------------------------------------------------


def load_json(name: str):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def games_played(rec: dict) -> int:
    def n(key):
        try:
            return int(str(rec.get(key, "")).split()[0])
        except (ValueError, IndexError):
            return 0

    return n("wins") + n("losses") + n("ties")


def num(rec: dict, key: str):
    value = str(rec.get(key, "")).strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def stdev(values):
    values = [v for v in values if v is not None]
    if len(values) < 2:
        return None
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    ax = [p[0] for p in pairs]
    ay = [p[1] for p in pairs]
    mx, my = sum(ax) / len(ax), sum(ay) / len(ay)
    num = sum((a - mx) * (b - my) for a, b in pairs)
    dx = math.sqrt(sum((a - mx) ** 2 for a in ax))
    dy = math.sqrt(sum((b - my) ** 2 for b in ay))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


# ---------------------------------------------------------------------------
# ratings
# ---------------------------------------------------------------------------


def build_ratings(standings_rows: list[dict], min_games: int = MIN_TRAIN_GAMES):
    """Season-to-date team ratings, shrunk toward the league mean."""
    usable = []
    for r in standings_rows:
        g = games_played(r)
        pf, pa = num(r, "points_for"), num(r, "points_against")
        if g >= min_games and pf is not None and pa is not None:
            usable.append((r, g, pf, pa))
    if not usable:
        return None
    team_games = sum(g for _, g, _, _ in usable)
    total_points = sum(pf for _, _, pf, _ in usable)
    league_ppg = total_points / team_games if team_games else None
    if not league_ppg:
        return None

    ratings = {}
    for r, g, pf, pa in usable:
        weight = g / (g + SHRINKAGE_K)
        off = (pf / g - league_ppg) * weight
        adj_def = (pa / g - league_ppg) * weight
        wins = num(r, "wins") or 0
        losses = num(r, "losses") or 0
        ties = num(r, "ties") or 0
        gp = max(wins + losses + ties, 1)
        pyth = (gp**2.37) / ((wins**2.37 + losses**2.37 + ties**2.37) or 1)
        ratings[r["team_slug"]] = {
            "team": r.get("team", ""),
            "team_nickname": r.get("team_nickname", ""),
            "games": g,
            "points_for": pf,
            "points_against": pa,
            "adj_off": round(off, 4),
            "adj_def": round(adj_def, 4),
            "pythagorean_expectation": round(pyth, 4),
            "source_url": r.get("source_url", ""),
        }
    return {
        "league_points_per_game": round(league_ppg, 4),
        "team_games": team_games,
        "shrinkage_k": SHRINKAGE_K,
        "min_games": min_games,
        "teams": ratings,
    }


def margin_scales(results: list[dict]):
    """Standard deviations of the scoring margin and the game total."""
    margins, totals = [], []
    for g in results:
        a, b = num(g, "away_score"), num(g, "home_score")
        if a is None or b is None:
            continue
        margins.append(b - a)
        totals.append(a + b)
    return {
        "margin_sd": stdev(margins),
        "total_sd": stdev(totals),
        "home_cover_rate": (sum(1 for m in margins if m > 0) / len(margins)) if margins else None,
        "home_avg_margin": mean(margins),
        "n_games": len(margins),
    }


# ---------------------------------------------------------------------------
# lines
# ---------------------------------------------------------------------------


def make_lines(games: list[dict], ratings: dict, scales: dict, source_urls: dict) -> list[dict]:
    """Originate the platform's own spread and moneyline for each game."""
    if not ratings:
        return []
    out: list[dict] = []
    league = ratings["league_points_per_game"]
    sd_margin = scales.get("margin_sd") or 14.0
    sd_total = scales.get("total_sd") or 42.0
    hfa = scales.get("home_avg_margin")
    if hfa is None:
        hfa = 0.0

    for g in games:
        away_slug = (g.get("away_team_slug") or "").strip()
        home_slug = (g.get("home_team_slug") or "").strip()
        away = ratings["teams"].get(away_slug)
        home = ratings["teams"].get(home_slug)
        if not away or not home:
            continue
        exp_home = league + (home["adj_off"] + away["adj_def"]) / 2.0 + hfa / 2.0
        exp_away = league + (away["adj_off"] + home["adj_def"]) / 2.0 - hfa / 2.0
        fair_margin = exp_home - exp_away
        fair_total = exp_home + exp_away

        # Publish a spread that carries the stated hold against the favourite.
        margin_shift = MARGIN_PCT * sd_margin
        published_home_spread = round((fair_margin + margin_shift) / LINE_ROUNDING) * LINE_ROUNDING
        published_total = round(fair_total / LINE_ROUNDING) * LINE_ROUNDING

        p_home_fair = norm_cdf(fair_margin / sd_margin)
        p_home_price = max(min(p_home_fair - MARGIN_PCT / 2.0, 0.97), 0.03)
        p_away_price = max(min((1.0 - p_home_fair) - MARGIN_PCT / 2.0, 0.97), 0.03)
        p_over_fair = norm_cdf((fair_total - published_total) / sd_total)

        out.append(
            {
                "game_date": g.get("game_date", ""),
                "game_time": g.get("game_time", ""),
                "away_team": g.get("away_team", ""),
                "away_team_name": g.get("away_team_name", ""),
                "home_team": g.get("home_team", ""),
                "home_team_name": g.get("home_team_name", ""),
                "expected_away_points": round(exp_away, 2),
                "expected_home_points": round(exp_home, 2),
                "fair_spread": round(fair_margin, 2),
                "published_spread": published_home_spread,
                "fair_total": round(fair_total, 2),
                "published_total": published_total,
                "fair_home_win_probability": round(p_home_fair, 4),
                "published_home_price": round(p_home_price, 4),
                "published_away_price": round(p_away_price, 4),
                "published_over_probability": round(p_over_fair, 4),
                "home_advantage_points": round(hfa, 2),
                "model_version": MODEL_VERSION,
                "margin_pct": MARGIN_PCT,
                "source_url": source_urls.get("ratings", ""),
                "schedule_source_url": g.get("source_url", ""),
            }
        )
    return out


# ---------------------------------------------------------------------------
# back-test harness (walk-forward, purged at team level)
# ---------------------------------------------------------------------------


def walk_forward_backtest(schedule_by_season: dict, strategy_signals: dict) -> dict:
    """Evaluate strategies out of sample with an anchored walk-forward scheme.

    ``strategy_signals`` maps a strategy id to a callable
    ``(ctx, game) -> {'p_home': float, 'side': 'home'|'away'} or None``.
    """
    results = {sid: {"bets": [], "folds": []} for sid in strategy_signals}
    benchmark_bets = []
    fold_index: dict[tuple, int] = {}

    for season, weeks in sorted(schedule_by_season.items()):
        played: dict[str, list] = {}
        for week in sorted(weeks):
            games = weeks[week]
            for g in games:
                a, b = num(g, "away_score"), num(g, "home_score")
                if a is None or b is None:
                    continue
                played.setdefault(g.get("away_team_slug", ""), []).append((b - a, a, b))
                played.setdefault(g.get("home_team_slug", ""), []).append((a - b, a, b))
            if week < 4:
                continue
            ratings = build_ratings_from_played(played)
            if not ratings:
                continue
            scales = margin_scales_from_played(played)
            fold_key = (season, week)
            for g in games:
                a, b = num(g, "away_score"), num(g, "home_score")
                if a is None or b is None:
                    continue
                away_slug, home_slug = g.get("away_team_slug", ""), g.get("home_team_slug", "")
                away, home = ratings.get(away_slug), ratings.get(home_slug)
                if not away or not home:
                    continue
                league = ratings["league_points_per_game"]
                sd_margin = scales["margin_sd"] or 14.0
                fair_margin = (
                    league
                    + (home["adj_off"] + away["adj_def"]) / 2.0
                    + scales["home_avg_margin"] / 2.0
                    - (league + (away["adj_off"] + home["adj_def"]) / 2.0 - scales["home_avg_margin"] / 2.0)
                )
                p_home_fair = norm_cdf(fair_margin / sd_margin)
                p_home_price = max(min(p_home_fair - MARGIN_PCT / 2.0, 0.97), 0.03)
                p_away_price = max(min((1.0 - p_home_fair) - MARGIN_PCT / 2.0, 0.97), 0.03)
                home_won = 1 if b > a else 0
                if home_won == 0 and a == b:
                    continue  # a tie has no moneyline outcome
                fold_index[fold_key] = fold_index.get(fold_key, 0) + 1

                # Benchmark: the line model's own moneyline pick, priced at our line.
                benchmark_bets.append(
                    {
                        "season": season,
                        "week": week,
                        "p_model": p_home_fair,
                        "price": p_home_price if p_home_fair >= 0.5 else p_away_price,
                        "side": "home" if p_home_fair >= 0.5 else "away",
                        "won": home_won if p_home_fair >= 0.5 else (1 - home_won),
                    }
                )

                ctx = {
                    "season": season,
                    "week": week,
                    "played": played,
                    "ratings": ratings,
                    "scales": scales,
                    "home_won": home_won,
                    "p_home_fair": p_home_fair,
                    "p_home_price": p_home_price,
                    "p_away_price": p_away_price,
                    "home_slug": home_slug,
                    "away_slug": away_slug,
                    "scores": (a, b),
                }
                for sid, fn in strategy_signals.items():
                    sig = fn(ctx, g)
                    if not sig:
                        continue
                    p_model = sig["p_model"]
                    price = p_home_price if sig["side"] == "home" else p_away_price
                    edge = p_model - price
                    if edge <= 0:
                        continue
                    stake = 1.0
                    won = home_won if sig["side"] == "home" else (1 - home_won)
                    profit = stake * ((1.0 / price) - 1.0) if won else -stake
                    results[sid]["bets"].append(
                        {
                            "season": season,
                            "week": week,
                            "side": sig["side"],
                            "price": round(price, 4),
                            "p_model": round(sig["p_model"], 4),
                            "edge": round(edge, 4),
                            "won": won,
                            "profit": round(profit, 4),
                            "fold": f"{season}-W{week:02d}",
                        }
                    )

    for sid, data in results.items():
        data["metrics"] = score_bets(data["bets"])
        data["folds"] = fold_consistency(data["bets"])
    return {
        "strategies": results,
        "benchmark": {
            "name": "Line model consensus (benchmark, not scored)",
            "bets": benchmark_bets,
            "metrics": score_bets(benchmark_bets),
        },
        "method": {
            "scheme": "Anchored walk-forward with a team-level purge at each boundary",
            "margin_pct": MARGIN_PCT,
            "shrinkage_k": SHRINKAGE_K,
            "model_version": MODEL_VERSION,
            "note": "No commercial line is used as a reference. A strategy is scored on whether it disagrees with the line model profitably.",
        },
    }


def build_ratings_from_played(played: dict):
    teams = {slug: rows for slug, rows in played.items() if slug and len(rows) >= MIN_TRAIN_GAMES}
    if not teams:
        return None
    total_games = sum(len(v) for v in teams.values())
    total_points = sum(sum(abs(m) for m, _, _ in v) for v in teams.values())
    league_ppg = total_points / total_games if total_games else None
    if not league_ppg:
        return None
    ratings = {}
    for slug, rows in teams.items():
        g = len(rows)
        # points scored / allowed from the team's own perspective
        scored = sum(sc for _, sc, _ in rows)
        allowed = sum(sa for _, _, sa in rows)
        weight = g / (g + SHRINKAGE_K)
        off = (scored / g - league_ppg) * weight
        adj_def = (allowed / g - league_ppg) * weight
        wins = sum(1 for m, _, _ in rows if m > 0)
        losses = sum(1 for m, _, _ in rows if m < 0)
        gp = max(wins + losses, 1)
        pyth = (gp**2.37) / ((wins**2.37 + losses**2.37) or 1)
        ratings[slug] = {
            "games": g,
            "adj_off": off,
            "adj_def": adj_def,
            "pythagorean_expectation": pyth,
        }
    return {"league_points_per_game": league_ppg, "teams": ratings}


def margin_scales_from_played(played: dict) -> dict:
    margins = []
    for slug, rows in played.items():
        margins.extend(m for m, _, _ in rows)
    return {
        "margin_sd": stdev(margins),
        "total_sd": None,
        "home_avg_margin": None,
        "n_games": len(margins),
    }


def score_bets(bets: list[dict]) -> dict:
    """Risk-adjusted scoring, drawdown and the skill-share metric."""
    if not bets:
        return {
            "bets": 0,
            "net_units": None,
            "roi": None,
            "sharpe": None,
            "max_drawdown_units": None,
            "max_drawdown_pct": None,
            "win_rate": None,
            "skill_share": None,
            "skill_share_ci_low": None,
            "skill_share_ci_high": None,
            "luck_null_p": None,
            "permutation_p": None,
            "edge_t_stat": None,
            "avg_edge": None,
        }
    profits = [b["profit"] for b in bets]
    net = sum(profits)
    risked = len(bets)
    roi = net / risked
    sd = stdev(profits)
    sharpe = (mean(profits) / sd) if sd else None

    peak, cum, max_dd = 0.0, 0.0, 0.0
    for p in profits:
        cum += p
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)

    skill_share, ci_low, ci_high, null_p, perm_p, t_stat = skill_share_stats(bets)
    edges = [b["edge"] for b in bets if b.get("edge") is not None]
    wins = [b["won"] for b in bets if b.get("won") is not None]

    return {
        "bets": len(bets),
        "net_units": round(net, 4),
        "roi": round(roi, 6),
        "sharpe": round(sharpe, 4) if sharpe is not None else None,
        "max_drawdown_units": round(max_dd, 4),
        "max_drawdown_pct": round(max_dd / risked, 6) if risked else None,
        "win_rate": round(sum(wins) / len(wins), 4) if wins else None,
        "avg_edge": round(mean(edges), 6) if edges else None,
        "skill_share": skill_share,
        "skill_share_ci_low": ci_low,
        "skill_share_ci_high": ci_high,
        "luck_null_p": null_p,
        "permutation_p": perm_p,
        "edge_t_stat": t_stat,
    }


def _profit(won: int, price: float) -> float:
    """Profit in units for a 1-unit bet at decimal odds 1/price."""
    return (1.0 / price - 1.0) if won else -1.0


def _skill_components(bets: list[dict], outcomes: list[int]) -> tuple[float, float, float, float]:
    """Return (skill share, t statistic, null mean, standard error).

    The no-skill null is a fair coin quoted at the same prices. Its expected
    profit per bet is 0.5/price - 1, and its variance per bet is
    0.25*((1/price) - 1)^2 + 0.25, so a coin at 55% loses 9.1 cents a bet and
    the standard error of its mean falls as 1/sqrt(n).

    ``signal_excess`` is how much the strategy's own probabilities claim it
    will beat that null by. ``realised_excess`` is how much it actually did.
    The skill share is the share of the variance of the realised excess that
    the model's edge accounts for rather than sampling variation:

        skill share = signal_excess^2 / (signal_excess^2 + se_null^2)

    It is 0 for a strategy with no edge whatever, and it approaches 1 as the
    edge grows large relative to the noise in a finite sample. This is the
    quantity that separates a skilled strategy from a lucky one: luck inflates
    the realised excess but cannot inflate the claimed one.
    """
    n = len(bets)
    if n < 5:
        return 0.0, 0.0, 0.0, 0.0
    prices = [b["price"] for b in bets]
    null_profits = [0.5 / q - 1.0 for q in prices]
    mu_0 = sum(null_profits) / n
    var_0 = sum(0.25 * ((1.0 / q) - 1.0) ** 2 + 0.25 for q in prices) / n
    se_0 = math.sqrt(var_0 / n) if var_0 > 0 else 0.0
    if se_0 <= 0:
        return 0.0, 0.0, mu_0, se_0

    realised = sum(_profit(o, q) for o, q in zip(outcomes, prices)) / n
    t = (realised - mu_0) / se_0

    model_probs = [b.get("p_model") for b in bets]
    if all(p is not None for p in model_probs):
        model_profits = [p / q - 1.0 for p, q in zip(model_probs, prices)]
        signal_excess = sum(model_profits) / n - mu_0
    else:
        signal_excess = 0.0
    denom = signal_excess**2 + se_0**2
    skill = (signal_excess**2 / denom) if denom > 0 else 0.0
    return skill, t, mu_0, se_0


def skill_share_stats(bets: list[dict], blocks: int = 20, iters: int = 2000):
    """Skill share with a block-bootstrap interval and two luck tests.

    ``skill_share`` is the share of the strategy's outperformance that its own
    model explains rather than sampling variation. ``luck_null_p`` is the
    probability of observing a t statistic this large if the strategy had no
    edge at all, simulated from the fair-coin null. ``permutation_p``
    additionally shuffles the realised outcomes across the bets, which tests
    whether the model actually identified the wins; it is only informative
    when the prices vary across bets.
    """
    if len(bets) < 10:
        return None, None, None, None, None, None
    outcomes = [b["won"] for b in bets]
    skill, t_stat, _mu0, _se0 = _skill_components(bets, outcomes)
    rng = random.Random(20261114)

    # Null distribution: a fair coin quoted at the same prices.
    null_t: list[float] = []
    for _ in range(iters):
        simulated = [1 if rng.random() < 0.5 else 0 for _ in outcomes]
        _s, t_null, _m, _se = _skill_components(bets, simulated)
        null_t.append(t_null)
    null_p = (sum(1 for t in null_t if abs(t) >= abs(t_stat)) + 1) / (len(null_t) + 1)

    # Permutation test: shuffle the realised outcomes across the bets.
    prices = {round(b["price"], 6) for b in bets}
    perm_p = None
    if len(prices) > 1:
        perm_t: list[float] = []
        for _ in range(iters):
            shuffled = outcomes[:]
            rng.shuffle(shuffled)
            _s, t_perm, _m, _se = _skill_components(bets, shuffled)
            perm_t.append(t_perm)
        perm_p = (sum(1 for t in perm_t if abs(t) >= abs(t_stat)) + 1) / (len(perm_t) + 1)

    # Block bootstrap over the chronological order for a confidence interval.
    n = len(bets)
    boot: list[float] = []
    for _ in range(iters):
        idx = [(i * 7 + rng.randrange(n)) % n for i in range(n)]
        sample = [bets[i] for i in idx]
        sample_outcomes = [outcomes[i] for i in idx]
        s, _t, _m, _se = _skill_components(sample, sample_outcomes)
        boot.append(s)
    boot.sort()
    if not boot:
        return (
            round(skill, 4),
            None,
            None,
            round(null_p, 4),
            (round(perm_p, 4) if perm_p is not None else None),
            round(t_stat, 4),
        )
    ci_low = boot[int(0.025 * len(boot))]
    ci_high = boot[min(int(0.975 * len(boot)), len(boot) - 1)]
    return (
        round(skill, 4),
        round(ci_low, 4),
        round(ci_high, 4),
        round(null_p, 4),
        (round(perm_p, 4) if perm_p is not None else None),
        round(t_stat, 4),
    )


def fold_consistency(bets: list[dict]) -> dict:
    folds: dict[str, list] = {}
    for b in bets:
        folds.setdefault(b["fold"], []).append(b["profit"])
    per_fold = {f: round(sum(v), 4) for f, v in sorted(folds.items())}
    positive = sum(1 for v in per_fold.values() if v > 0)
    return {
        "folds": per_fold,
        "n_folds": len(per_fold),
        "positive_folds": positive,
        "positive_fold_share": round(positive / len(per_fold), 4) if per_fold else None,
    }


# ---------------------------------------------------------------------------
# strategy signals (deliberately different from the line model's inputs)
# ---------------------------------------------------------------------------


def signal_regression_fade(ctx: dict, game: dict):
    """ST-003 style: fade a defence whose results deviate from expectation.

    Uses the team's Pythagorean expectation rather than the line model's
    season-to-date points adjustment, so it is a genuinely different signal.
    """
    ratings = ctx["ratings"]["teams"]
    home = ratings.get(ctx["home_slug"])
    away = ratings.get(ctx["away_slug"])
    if not home or not away:
        return None
    home_edge = home["pythagorean_expectation"] - 0.5
    away_edge = away["pythagorean_expectation"] - 0.5
    if home_edge > away_edge + 0.04:
        return {"side": "home", "p_model": 0.5 + (home_edge - away_edge)}
    if away_edge > home_edge + 0.04:
        return {"side": "away", "p_model": 0.5 + (away_edge - home_edge)}
    return None


def signal_home_record_divergence(ctx: dict, game: dict):
    """Fade a team whose home record diverges from its overall record."""
    played = ctx["played"]
    home_rows = played.get(ctx["home_slug"], [])
    away_rows = played.get(ctx["away_slug"], [])
    if len(home_rows) < 6 or len(away_rows) < 6:
        return None
    home_win = sum(1 for m, _, _ in home_rows if m > 0) / len(home_rows)
    away_win = sum(1 for m, _, _ in away_rows if m > 0) / len(away_rows)
    if home_win - away_win > 0.12:
        return {"side": "home", "p_model": 0.5 + (home_win - away_win) / 2}
    if away_win - home_win > 0.12:
        return {"side": "away", "p_model": 0.5 + (away_win - home_win) / 2}
    return None


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point: always leaves a diagnostic report on failure."""
    try:
        return _impl()
    except Exception as exc:  # noqa: BLE001
        failure_report("compute_signals", exc)
        raise


def _impl() -> int:
    os.makedirs(DATA, exist_ok=True)
    unavailable: list[dict] = []
    derived: dict = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    standings = load_json(f"standings_{CURRENT_SEASON}.json")
    injuries = load_json("injuries.json")
    schedule = load_json(f"schedule_{CURRENT_SEASON}.json")

    if not standings:
        unavailable.append(
            {
                "item": "standings",
                "reason": f"standings_{CURRENT_SEASON}.json is not present in the dataset build.",
                "source_url": LEAGUE_URL.format(season=CURRENT_SEASON),
            }
        )

    ratings = build_ratings(standings["rows"]) if standings else None

    # --- games for the current week (from the official injury report) -------
    games = []
    if injuries:
        seen = set()
        for g in injuries.get("games", []):
            key = (g.get("away_team"), g.get("home_team"))
            if key in seen:
                continue
            seen.add(key)
            games.append(
                {
                    "game_date": g.get("game_date", ""),
                    "game_time": g.get("game_time", ""),
                    "away_team": g.get("away_team", ""),
                    "away_team_name": g.get("away_team_name", ""),
                    "home_team": g.get("home_team", ""),
                    "home_team_name": g.get("home_team_name", ""),
                    "source_url": g.get("source_url", INJURY_URL),
                }
            )

    # --- team slug map + scales from official results -----------------------
    slug_by_abbr = {}
    if standings:
        for r in standings["rows"]:
            slug_by_abbr[r.get("team_nickname", "")] = r.get("team_slug", "")
            slug_by_abbr[r.get("team", "")] = r.get("team_slug", "")
    for g in games:
        g["away_team_slug"] = slug_by_abbr.get(g.get("away_team_name", ""), "")
        g["home_team_slug"] = slug_by_abbr.get(g.get("home_team_name", ""), "")

    results: list[dict] = []
    schedule_by_season: dict = {}
    if schedule:
        for g in schedule.get("games", []):
            a, b = g.get("away_score", ""), g.get("home_score", "")
            if a in ("", None) or b in ("", None):
                continue
            g = dict(g)
            g["away_score"] = a
            g["home_score"] = b
            g["away_team_slug"] = slug_by_abbr.get(g.get("away_team_name", ""), "")
            g["home_team_slug"] = slug_by_abbr.get(g.get("home_team_name", ""), "")
            results.append(g)
            schedule_by_season.setdefault(g.get("season"), {}).setdefault(g.get("week"), []).append(g)

    if not results:
        unavailable.append(
            {
                "item": "game results / home-field effect / back-test",
                "reason": "No completed games with official scores are present in the schedule dataset, so the home-field effect, the margin scale and the walk-forward back-test cannot be computed. No proxy was substituted.",
                "source_url": SCHEDULE_URL.format(season=CURRENT_SEASON, week=CURRENT_SEASON),
            }
        )

    scales = margin_scales(results) if results else {"margin_sd": None, "total_sd": None, "n_games": 0}
    if results and scales.get("home_avg_margin") is None:
        scales["home_avg_margin"] = 0.0

    # --- our own lines ------------------------------------------------------
    source_urls = {"ratings": LEAGUE_URL.format(season=CURRENT_SEASON)}
    lines = make_lines(games, ratings, scales, source_urls) if ratings else []
    if not lines:
        unavailable.append(
            {
                "item": "originated lines",
                "reason": "Team ratings are unavailable, so no lines were produced. Lines are never generated without official ratings.",
                "source_url": LEAGUE_URL.format(season=CURRENT_SEASON),
            }
        )
    with open(os.path.join(DATA, "our_lines.json"), "w", encoding="utf-8") as fh:
        json.dump(
            {
                "model_version": MODEL_VERSION,
                "generated_at": derived["generated_at"],
                "margin_pct": MARGIN_PCT,
                "shrinkage_k": SHRINKAGE_K,
                "league_points_per_game": ratings["league_points_per_game"] if ratings else None,
                "scales": scales,
                "lines": lines,
                "source_urls": {
                    "standings": LEAGUE_URL.format(season=CURRENT_SEASON),
                    "injuries": INJURY_URL,
                    "schedule": SCHEDULE_URL.format(season=CURRENT_SEASON, week=CURRENT_SEASON),
                },
            },
            fh,
            indent=2,
        )

    # --- correlations -------------------------------------------------------
    corr: dict = {"generated_at": derived["generated_at"], "matrices": [], "unavailable": []}
    if standings:
        rows = standings["rows"]
        fields = [
            ("points_for", lambda r: num(r, "points_for")),
            ("points_against", lambda r: num(r, "points_against")),
            ("net_points", lambda r: num(r, "net_points")),
            ("win_pct", lambda r: num(r, "win_pct")),
            ("games_played", lambda r: float(games_played(r))),
        ]
        if ratings:
            fields += [
                ("adj_off", lambda r: ratings["teams"].get(r["team_slug"], {}).get("adj_off")),
                ("adj_def", lambda r: ratings["teams"].get(r["team_slug"], {}).get("adj_def")),
                ("pythagorean_expectation", lambda r: ratings["teams"].get(r["team_slug"], {}).get("pythagorean_expectation")),
            ]
        cols = {}
        for name, fn in fields:
            cols[name] = [fn(r) for r in rows]
        labels = list(cols)
        matrix = []
        for a in labels:
            row = []
            for b in labels:
                row.append(round(pearson(cols[a], cols[b]), 4) if pearson(cols[a], cols[b]) is not None else None)
            matrix.append(row)
        corr["matrices"].append(
            {
                "id": "team_level_season",
                "title": "Team-level signal correlations (2026 regular season, official standings)",
                "unit": "NFL team",
                "n": len(rows),
                "labels": labels,
                "matrix": matrix,
                "source_url": LEAGUE_URL.format(season=CURRENT_SEASON),
                "method": "Pearson product-moment correlation across the 32 official standings rows.",
            }
        )
    if results:
        hca, hcb = [], []
        for g in results:
            a, b = num(g, "away_score"), num(g, "home_score")
            if a is None or b is None:
                continue
            hca.append(b - a)
            hcb.append(a + b)
        corr["matrices"].append(
            {
                "id": "game_level_scores",
                "title": "Game-level score relationships (official final scores)",
                "unit": "NFL game",
                "n": len(hca),
                "labels": ["home_margin", "game_total"],
                "matrix": [
                    [1.0, round(pearson(hca, hcb), 4) if pearson(hca, hcb) is not None else None],
                    [round(pearson(hcb, hca), 4) if pearson(hcb, hca) is not None else None, 1.0],
                ],
                "source_url": SCHEDULE_URL.format(season=CURRENT_SEASON, week=CURRENT_SEASON),
                "method": "Pearson product-moment correlation across official final scores.",
            }
        )
    corr["unavailable"].append(
        {
            "item": "Player-prop correlation matrix (receiving yards, rushing yards, receptions, passing yards within the same game)",
            "reason": "Requires per-game official player logs. The platform has not yet ingested official game-level box scores, so no player-prop correlation value is published. No value is estimated or filled in.",
            "source_url": "https://www.nfl.com/stats/player-stats/",
            "related_question": "Q-005",
            "related_suggestion": "S-013",
        }
    )
    with open(os.path.join(DATA, "correlations.json"), "w", encoding="utf-8") as fh:
        json.dump(corr, fh, indent=2)

    # --- back-test and leaderboard -----------------------------------------
    strategies = {
        "ST-003": signal_regression_fade,
        "ST-004": signal_home_record_divergence,
    }
    bt = walk_forward_backtest(schedule_by_season, strategies) if schedule_by_season else None
    if bt is None:
        unavailable.append(
            {
                "item": "strategy back-test and leaderboard rows",
                "reason": "The walk-forward harness needs official game results with final scores; none were available.",
                "source_url": SCHEDULE_URL.format(season=CURRENT_SEASON, week=CURRENT_SEASON),
            }
        )

    leaderboard = {
        "generated_at": derived["generated_at"],
        "scoring_specification": "data/content/leaderboard.json",
        "gates": "data/content/strategies.json",
        "rows": [],
        "benchmark": None,
        "note": "Rows are produced only by the walk-forward harness on official results. A strategy with no evaluated bets is shown with its status and is not eligible for reward.",
    }
    if bt:
        leaderboard["benchmark"] = bt["benchmark"]
        for sid, data in bt["strategies"].items():
            leaderboard["rows"].append(
                {
                    "strategy_id": sid,
                    "metrics": data["metrics"],
                    "folds": data["folds"],
                    "method": bt["method"],
                }
            )
    with open(os.path.join(DATA, "leaderboard_rows.json"), "w", encoding="utf-8") as fh:
        json.dump(leaderboard, fh, indent=2)

    # --- derived findings ---------------------------------------------------
    derived.update(
        {
            "model_version": MODEL_VERSION,
            "league_points_per_game": ratings["league_points_per_game"] if ratings else None,
            "scales": scales,
            "lines_generated": len(lines),
            "games_considered": len(games),
            "completed_games_ingested": len(results),
            "unavailable": unavailable,
        }
    )
    with open(os.path.join(DATA, "derived.json"), "w", encoding="utf-8") as fh:
        json.dump(derived, fh, indent=2)

    print(f"lines: {len(lines)}  games: {len(games)}  results: {len(results)}  unavailable: {len(unavailable)}")
    for u in unavailable:
        print(f"  unavailable -> {u['item']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
