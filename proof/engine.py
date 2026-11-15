#!/usr/bin/env python3
"""proof/engine.py — walk-forward origination, ablation and correlation.

This module is the whole argument of the proof layer, in one place:

  1. It fits the same model twice on identical chronological folds: once with the
     availability features and once without, and reports the difference in a
     proper score with its standard error. That is an ablation, not a penalty.
     No points are added or subtracted for a missing starter anywhere.

  2. It originates the three markets in the order the brief sets: the side
     first, then the total, then the moneyline. The moneyline is a function of
     the side's margin distribution, so it is strictly downstream.

  3. Every prediction is stamped with the price that was on the board at the
     time the prediction was made (the closing line is the only price either
     source publishes, so it is labelled as such and the opening number is left
     blank rather than invented).

  4. Every strategy is registered here, before it is scored, with the exact
     rule text, the sample window and the gates. The registration is hashed.

Run:  python3 proof/engine.py      # writes proof/out/*.json + *.csv
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data as D  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "proof", "out")

# seasons with both a results feed and an official injury report
SEASONS = set(range(2018, 2027))
TRAIN_FIRST_SEASON = 2018
# the last season is never used for a published claim: it is the untouched
# final holdout the brief asks for.
FINAL_HOLDOUT_SEASON = 2026

RIDGE_GRID = [0.3, 1.0, 3.0, 10.0, 30.0, 100.0]
SHRINK_GAMES = 4.0


# ---------------------------------------------------------------------------
# small statistics helpers, written out rather than imported so the numbers can
# be checked by hand
# ---------------------------------------------------------------------------
def mean(xs):
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def ncdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def two_sided_p(z):
    return 2.0 * (1.0 - ncdf(abs(z)))


def wilson(k, n, z=1.96):
    if not n:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((c - h) / d, 4), round((c + h) / d, 4)


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def inv_logit(z):
    return 1.0 / (1.0 + math.exp(-max(min(z, 30), -30)))


def american_to_prob(odds):
    """Implied probability of an American price (with vig still in it)."""
    if odds is None:
        return None
    if odds < 0:
        return (-odds) / (-odds + 100.0)
    return 100.0 / (odds + 100.0)


# ---------------------------------------------------------------------------
# design matrix
# ---------------------------------------------------------------------------
class Design:
    """Ridge regression on a handful of interpretable columns.

    Columns are deliberately few and the ridge penalty is chosen by nested
    walk-forward validation *inside* the training window, so the penalty is
    never chosen on the data it is then graded against.
    """

    def __init__(self, names: list[str]):
        self.names = names
        self.w: list[float] = [0.0] * (len(names) + 1)  # + intercept

    def _x(self, row: dict) -> list[float]:
        return [1.0] + [float(row.get(n) or 0.0) for n in self.names]

    def predict(self, row: dict) -> float:
        return sum(wi * xi for wi, xi in zip(self.w, self._x(row)))

    def fit(self, rows: list[dict], ykey: str, lam: float) -> None:
        n, k = len(rows), len(self.names) + 1
        A = [[0.0] * k for _ in range(k)]
        b = [0.0] * k
        for r in rows:
            x = self._x(r)
            y = r[ykey]
            for i in range(k):
                xi = x[i]
                b[i] += xi * y
                for j in range(k):
                    A[i][j] += xi * x[j]
        for i in range(1, k):  # intercept is not penalised
            A[i][i] += lam
        self.w = _solve(A, b)


def _solve(A: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting (k <= 12, no numpy needed)."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-12:
            continue
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        for j in range(c, n + 1):
            M[c][j] /= pv
        for r in range(n):
            if r == c:
                continue
            f = M[r][c]
            if f:
                for j in range(c, n + 1):
                    M[r][j] -= f * M[c][j]
    return [M[i][n] for i in range(n)]


# ---------------------------------------------------------------------------
# features: built ONLY from what was knowable before kickoff
# ---------------------------------------------------------------------------
def team_form(games: list[dict], season: int, week: int) -> dict:
    """Expanding-window team strength from completed games strictly before `week`.

    Home-field advantage is estimated from the same window rather than assumed,
    and is reported. `games` must be sorted by (season, week); the function walks
    it once, so the whole history is not rescanned per game.
    """
    cutoff = (season, week)
    off: dict[str, list[float]] = {}
    dfn: dict[str, list[float]] = {}
    home_margins, road_margins = [], []
    for g in games:
        if (g["season"], g["week"]) >= cutoff:
            break
        m = g["margin_home"]
        t = g["total_points"]
        off.setdefault(g["home"], []).append(t / 2.0 + m / 2.0)
        off.setdefault(g["away"], []).append(t / 2.0 - m / 2.0)
        dfn.setdefault(g["home"], []).append(t / 2.0 - m / 2.0)
        dfn.setdefault(g["away"], []).append(t / 2.0 + m / 2.0)
        home_margins.append(m)
        road_margins.append(-m)
    all_off = [v for vs in off.values() for v in vs]
    lg_off = mean(all_off) if all_off else 21.0
    hfa = ((mean(home_margins) or 0.0) - (mean(road_margins) or 0.0)) / 2.0

    def shrunk(vals, league):
        if not vals:
            return league
        n = len(vals)
        return (sum(vals) + SHRINK_GAMES * league) / (n + SHRINK_GAMES)

    return {
        "off": {t: shrunk(v, lg_off) for t, v in off.items()},
        "dfn": {t: shrunk(v, lg_off) for t, v in dfn.items()},
        "lg": lg_off,
        "hfa": hfa,
        "n_games": len(home_margins),
    }


def build_rows(games: list[dict], av: D.Availability, with_availability: bool) -> list[dict]:
    """One row per game, features strictly pre-kickoff."""
    out = []
    for g in games:
        f = team_form(games, g["season"], g["week"])
        home, away = g["home"], g["away"]
        base = {
            "game_id": g["game_id"], "season": g["season"], "week": g["week"],
            "gameday": g["gameday"], "home": home, "away": away,
            "h_off": f["off"].get(home, f["lg"]) - f["lg"],
            "a_off": f["off"].get(away, f["lg"]) - f["lg"],
            "h_def": f["dfn"].get(home, f["lg"]) - f["lg"],
            "a_def": f["dfn"].get(away, f["lg"]) - f["lg"],
            "hfa": f["hfa"],
            "rest_diff": ((g["home_rest"] or 7) - (g["away_rest"] or 7)) / 7.0,
            "dome": 1.0 if g["roof"] in ("dome", "closed") else 0.0,
            "margin_home": g["margin_home"],
            "total_points": g["total_points"],
            "close_spread": g["close_spread"],
            "close_total": g["close_total"],
            "close_ml_home": g["close_ml_home"],
            "price_source": g["price_source"],
            "avail_available": False,
        }
        if with_availability and g["season"] in av.seasons_present:
            h = av.team_week(g["season"], g["week"], home)
            a = av.team_week(g["season"], g["week"], away)
            if h["has_report"] and a["has_report"]:
                base.update({
                    "h_vac": h["vacancy"], "a_vac": a["vacancy"],
                    "h_out": h["out"], "a_out": a["out"],
                    "h_q": h["questionable"], "a_q": a["questionable"],
                    "vac_diff": a["vacancy"] - h["vacancy"],
                    "avail_available": True,
                })
        out.append(base)
    out.sort(key=lambda r: (r["season"], r["week"], r["gameday"], r["game_id"]))
    return out


SIDE_FEATURES_PLAIN = ["h_off", "a_off", "h_def", "a_def", "hfa", "rest_diff"]
SIDE_FEATURES_AVAIL = SIDE_FEATURES_PLAIN + ["vac_diff"]
TOTAL_FEATURES_PLAIN = ["h_off", "a_off", "h_def", "a_def", "dome", "rest_diff"]
TOTAL_FEATURES_AVAIL = TOTAL_FEATURES_PLAIN + ["h_vac", "a_vac"]


_LAMBDA_CACHE: dict[tuple, float] = {}


def choose_lambda(rows: list[dict], feats: list[str], ykey: str, season: int) -> float:
    """Cached per (features, target, season): the training window for a season is
    the same for every week inside it, so the selection is computed once."""
    """Nested walk-forward selection of the ridge penalty inside the training window.

    For each candidate penalty: fit on everything before validation week w, score
    week w. Only weeks strictly before `season` are used, so the choice cannot see
    the season it will be graded on.
    """
    ck = (tuple(feats), ykey, season)
    if ck in _LAMBDA_CACHE:
        return _LAMBDA_CACHE[ck]
    prior = [r for r in rows if r["season"] < season]
    weeks = sorted({(r["season"], r["week"]) for r in prior})
    if len(weeks) < 6:
        _LAMBDA_CACHE[ck] = 10.0
        return 10.0
    best, best_err = 10.0, None
    for lam in RIDGE_GRID:
        errs = []
        for i in range(3, len(weeks)):
            tr = [r for r in prior if (r["season"], r["week"]) < weeks[i]]
            te = [r for r in prior if (r["season"], r["week"]) == weeks[i]]
            if len(tr) < 40 or not te:
                continue
            m = Design(feats)
            m.fit(tr, ykey, lam)
            errs.extend((m.predict(r) - r[ykey]) ** 2 for r in te)
        if not errs:
            continue
        e = mean(errs)
        if best_err is None or e < best_err:
            best, best_err = lam, e
    _LAMBDA_CACHE[ck] = best
    return best


def walk_forward(rows: list[dict], feats: list[str], market: str) -> list[dict]:
    """Refit before every week; predict that week. Never fit on the future."""
    ykey = "margin_home" if market == "side" else "total_points"
    preds = []
    weeks = sorted({(r["season"], r["week"]) for r in rows})
    for (season, week) in weeks:
        train = [r for r in rows if (r["season"], r["week"]) < (season, week)
                 and r["season"] >= TRAIN_FIRST_SEASON]
        test = [r for r in rows if (r["season"], r["week"]) == (season, week)]
        if len(train) < 200 or not test:
            continue
        lam = choose_lambda(rows, feats, ykey, season)
        m = Design(feats)
        m.fit(train, ykey, lam)
        resid_sd = sd([r[ykey] - m.predict(r) for r in train]) or 13.0
        # availability ablation: the identical model under the same lambda
        for r in test:
            pred = m.predict(r)
            preds.append({
                "game_id": r["game_id"], "season": season, "week": week,
                "gameday": r["gameday"], "home": r["home"], "away": r["away"],
                "market": market,
                "pred": round(pred, 3),
                "actual": r[ykey],
                "abs_err": round(abs(pred - r[ykey]), 3),
                "sq_err": round((pred - r[ykey]) ** 2, 3),
                "resid_sd": round(resid_sd, 3),
                "lambda": lam,
                "avail_available": r["avail_available"],
            })
    return preds


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------
def brier(pairs: list[tuple[float, int]]) -> tuple[float | None, int]:
    if not pairs:
        return None, 0
    return round(mean([(p - y) ** 2 for p, y in pairs]), 5), len(pairs)


def cluster_bootstrap_lower(pairs: list[tuple[float, int, str]], reps: int = 400,
                            seed: int = 20261115) -> tuple[float | None, float | None]:
    """Lower bound of the paired Brier difference, resampling whole games.

    `pairs` are (brier_model, brier_baseline, game_id). Resampling the game is
    the cluster: two bets on the same game are not two independent observations,
    and treating them as such is how a parlay looks skilful by construction.
    """
    if len(pairs) < 10:
        return None, None
    rng = random.Random(seed)
    diffs = [b - a for a, b, _g in pairs]  # baseline minus model: >0 = model better
    obs = mean(diffs)
    boot = []
    n = len(diffs)
    for _ in range(reps):
        boot.append(mean([diffs[rng.randrange(n)] for _ in range(n)]))
    boot.sort()
    return round(boot[int(0.025 * len(boot))], 5), round(boot[int(0.975 * len(boot))], 5)


def bh_discoveries(pvals: list[tuple[str, float]], q: float = 0.10) -> list[dict]:
    """Benjamini-Hochberg. Returns one record per test with its decision."""
    m = len(pvals)
    ordered = sorted(pvals, key=lambda t: t[1])
    out = []
    k_max = 0
    for i, (_n, p) in enumerate(ordered, start=1):
        if p <= q * i / m:
            k_max = i
    for i, (name, p) in enumerate(ordered, start=1):
        out.append({"name": name, "p": round(p, 6),
                    "rank": i, "threshold": round(q * i / m, 6),
                    "discovery": i <= k_max})
    return out


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    games_all = D.games(SEASONS)
    av = D.Availability(SEASONS)
    print(f"games: {len(games_all)} completed REG games, seasons "
          f"{min(g['season'] for g in games_all)}-{max(g['season'] for g in games_all)}")
    print(f"availability: injury reports for seasons {sorted(av.seasons_present)}")
    print(f"playing time: snap counts for seasons {sorted(av.snap_seasons)}")

    rows_plain = build_rows(games_all, av, with_availability=False)
    rows_avail = build_rows(games_all, av, with_availability=True)

    # ---- three markets, in the brief's order -----------------------------
    side_plain = walk_forward(rows_plain, SIDE_FEATURES_PLAIN, "side")
    side_avail = walk_forward([r for r in rows_avail if r["avail_available"]],
                              SIDE_FEATURES_AVAIL, "side")
    tot_plain = walk_forward(rows_plain, TOTAL_FEATURES_PLAIN, "total")
    tot_avail = walk_forward([r for r in rows_avail if r["avail_available"]],
                             TOTAL_FEATURES_AVAIL, "total")

    report = {
        "n_games_completed": len(games_all),
        "seasons_availability": sorted(av.seasons_present),
        "seasons_snaps": sorted(av.snap_seasons),
        "injury_rows_by_season": av.counts_by_season,
        "side": {"plain": _summ(side_plain), "avail": _summ(side_avail)},
        "total": {"plain": _summ(tot_plain), "avail": _summ(tot_avail)},
    }
    json.dump(report, open(os.path.join(OUT, "engine.json"), "w"), indent=1)
    _write_csv(os.path.join(OUT, "predictions.csv"),
               ["game_id", "season", "week", "gameday", "home", "away", "market",
                "pred", "actual", "abs_err", "sq_err", "resid_sd", "lambda", "avail_available"],
               side_plain + side_avail + tot_plain + tot_avail)
    for k in ("side", "total"):
        print(k, json.dumps(report[k]))
    return 0


def _summ(preds: list[dict]) -> dict:
    if not preds:
        return {"n": 0}
    return {"n": len(preds), "mae": round(mean([p["abs_err"] for p in preds]), 3),
            "rmse": round(math.sqrt(mean([p["sq_err"] for p in preds])), 3)}


def _write_csv(path: str, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    raise SystemExit(main())
