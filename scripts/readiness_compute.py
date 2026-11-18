#!/usr/bin/env python3
"""Readiness-module computations (session arena/6259c7b0-x3).

Deterministic, offline, fixed seed. Produces:

  readiness/data/control_baselines.json   RD-04 control baselines (random picks; favourites only)
  readiness/data/what_changed.json        RD-05 weekly what-changed diff (rank / rating / availability)
  readiness/data/history/2026/week-XX/*   RD-05 stored weekly snapshots (CSV, one dir per week)
  readiness/data/ablations.json           RD-07 injury/personnel ablation with uncertainty

The control baselines reuse scripts/x3_signals.py's own pipeline and grading rule
(`score_contest`), so every control is evaluated on the identical graded game set with
the identical no-knowledge baseline that the signals leaderboard uses. Nothing here is
tuned on graded outcomes: thresholds are fixed constants written before the run.

Official inputs (all captured from NFL.com pages, stored in data/desk/):
  games.json  (163 rows, https://www.nfl.com/schedules/2026/by-week/week-N)
  injuries.json (1,027 rows, https://www.nfl.com/injuries/league/2026/regN)
  standings.json (32 clubs, https://www.nfl.com/standings/league/2026/reg)
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import x3_signals as X  # noqa: E402  (reuses the published engine, unchanged)

OUT = ROOT / "readiness" / "data"
HIST = OUT / "history" / "2026"
SEED = 20261115          # fixed seed, written before the run; never tuned
BOOTSTRAP_N = 10_000
CONTROLS_SOURCE = "https://www.nfl.com/schedules/2026/by-week/week-N"
STANDINGS_SOURCE = "https://www.nfl.com/standings/league/2026/reg"


# --------------------------------------------------------------------------
# pipeline (identical to the signals engine)
# --------------------------------------------------------------------------
def run_engine():
    inp = X.load_inputs()
    results = X.build_results(inp["games"])
    _depth_rows, avail_roll = X.build_depth_tables(inp["deficiencies"], inp["depth"])
    _snaps, lines, _stage = X.build_snapshots(results, avail_roll)
    graded = [g for g in lines
              if g["verified"] == "yes" and g.get("close_originated") == "yes"]
    graded.sort(key=lambda x: (x["week"], x["date_iso"], x["away"]))
    return inp, results, graded


# --------------------------------------------------------------------------
# RD-04: control baselines
# --------------------------------------------------------------------------
def wilson(k, n):
    if not n:
        return None, None
    return X.wilson(k, n)


def contest_rows(graded, key_pred):
    """Score the control with the engine's own contest rule."""
    games = []
    for g in graded:
        gg = dict(g)
        gg["_pred"] = gg[key_pred]
        gg["_base"] = gg["close_base_margin"]
        gg["_act"] = gg["actual_margin_home"]
        games.append(gg)
    return X.score_contest(games, "_pred", "_base", "_act")


def build_controls(results, graded):
    rng = random.Random(SEED)

    # --- C1: coin flip -----------------------------------------------------
    # Registered before the run: a coin flip carries no margin information, so its
    # margin number is 0 for every game; the side is a seeded 50/50 draw.
    c1_su, c1_brier, c1_keys = 0, 0.0, []
    for g in graded:
        pick_home = rng.random() < 0.5
        o = g.get("actual_home_win")
        if o in (X.BLANK, None):
            continue
        win = (o == 1) if pick_home else (o == 0)
        c1_su += 1 if win else 0
        c1_brier += (0.5 - o) ** 2
        c1_keys.append(0.0)  # the registered coin-flip number (home-margin perspective)
    for g, k in zip(graded, c1_keys):
        g["c1_pred"] = k
    c1 = contest_rows(graded, "c1_pred")
    n_b = len(c1_keys)
    c1_out = {
        "id": "C1",
        "name": "Coin flip (random picks)",
        "rule": ("Seeded 50/50 side draw (random.Random, seed 20261115). Margin number = 0 "
                 "every game: a coin flip expresses no margin information. Never ranked; "
                 "published beside the leaderboard as the luck control."),
        "graded_n": len(graded),
        "su_wins": c1_su,
        "su_n": n_b,
        "su_rate": round(c1_su / n_b, 4) if n_b else X.BLANK,
        "su_ci95": list(wilson(c1_su, n_b)) if n_b else [X.BLANK, X.BLANK],
        "su_p_exact": X.binom_two_sided(c1_su, n_b) if n_b else X.BLANK,
        "brier": round(c1_brier / n_b, 5) if n_b else X.BLANK,
        "contest": {k: c1[k] for k in ("n_decisive", "wins", "losses", "win_rate",
                                       "ci95_low", "ci95_high", "p_exact_binomial",
                                       "mae_model", "mae_baseline")},
    }

    # --- C2: favourites only ------------------------------------------------
    # Registered before the run: favourite = higher verified win pct in the results
    # feed strictly before the game's week; equal pct -> home by default. The
    # control's margin number is +/-1 (direction only, no magnitude); its Brier
    # probability is p_home = pct_home / (pct_home + pct_away).
    by_week = {}
    for r in results:
        if r["verified"] == "yes":
            by_week.setdefault(r["week"], []).append(r)
    pct = {}  # (week, abbr) -> win pct entering that week
    cum = {}  # abbr -> [w, l]
    max_week = max(g["week"] for g in graded)
    for w in range(1, max_week + 1):
        for abbr, wl in cum.items():
            tot = wl[0] + wl[1]
            pct[(w, abbr)] = wl[0] / tot if tot else 0.0
        for r in by_week.get(w, []):
            if r["margin_home"] == X.BLANK:
                continue
            h, a = r["home"], r["away"]
            ch, ca = cum.setdefault(h, [0, 0]), cum.setdefault(a, [0, 0])
            m = r["margin_home"]
            if m > 0:
                ch[0] += 1; ca[1] += 1
            elif m < 0:
                ca[0] += 1; ch[1] += 1
    c2_su = c2_n = 0
    c2_brier = 0.0
    preds = []
    for g in graded:
        w, h, a = g["week"], g["home"], g["away"]
        ph = pct.get((w, h), 0.0)
        pa = pct.get((w, a), 0.0)
        if ph > pa:
            fav_home, number = True, 1.0
        elif pa > ph:
            fav_home, number = False, -1.0
        else:
            fav_home, number = True, 1.0          # registered tie rule: home by default
        o = g.get("actual_home_win")
        if o in (X.BLANK, None):
            preds.append(X.BLANK)
            continue
        c2_n += 1
        win = (o == 1) if fav_home else (o == 0)
        c2_su += 1 if win else 0
        den = ph + pa
        p_home = (ph / den) if den else 0.5
        c2_brier += (p_home - o) ** 2
        preds.append(number)
    for g, k in zip(graded, preds):
        g["c2_pred"] = k
    c2 = contest_rows([g for g, k in zip(graded, preds) if k != X.BLANK], "c2_pred")
    c2_out = {
        "id": "C2",
        "name": "Favourites only",
        "rule": ("Pick the club with the higher verified win pct entering the week (results "
                 "feed only; equal pct -> home). Margin number = +/-1: direction without "
                 "magnitude. Brier probability = pct_home / (pct_home + pct_away). "
                 "Never ranked; published beside the leaderboard as the control."),
        "graded_n": len(graded),
        "su_wins": c2_su,
        "su_n": c2_n,
        "su_rate": round(c2_su / c2_n, 4) if c2_n else X.BLANK,
        "su_ci95": list(wilson(c2_su, c2_n)) if c2_n else [X.BLANK, X.BLANK],
        "su_p_exact": X.binom_two_sided(c2_su, c2_n) if c2_n else X.BLANK,
        "brier": round(c2_brier / c2_n, 5) if c2_n else X.BLANK,
        "contest": {k: c2[k] for k in ("n_decisive", "wins", "losses", "win_rate",
                                       "ci95_low", "ci95_high", "p_exact_binomial",
                                       "mae_model", "mae_baseline")},
    }

    # the engine's own graded numbers, for side-by-side reading (read-only copy)
    side = X.score_contest(graded, "close_pred_margin", "close_base_margin",
                           "actual_margin_home")
    model_row = {
        "id": "S1 (signals)",
        "name": "Model side (published signals engine)",
        "rule": "scripts/x3_signals.py S1 - contest vs the same no-knowledge baseline.",
        "graded_n": len(graded),
        "contest": {k: side[k] for k in ("n_decisive", "wins", "losses", "win_rate",
                                         "ci95_low", "ci95_high", "p_exact_binomial",
                                         "mae_model", "mae_baseline")},
        "su_wins": X.BLANK, "su_n": X.BLANK, "su_rate": X.BLANK,
        "su_ci95": [X.BLANK, X.BLANK], "su_p_exact": X.BLANK, "brier": X.BLANK,
    }
    return {
        "as_of": X.AS_OF,
        "seed": SEED,
        "graded_n": len(graded),
        "graded_weeks": sorted({g["week"] for g in graded}),
        "metric": ("contest win rate = share of graded games where the control's number is "
                   "closer to the actual margin than the no-knowledge baseline "
                   "(mean home margin fitted on the same training weeks) - identical rule, "
                   "identical set as signals strategy S1"),
        "controls": [c1_out, c2_out],
        "model_side_published": model_row,
        "source": CONTROLS_SOURCE,
        "note": ("Controls are never ranked. Coordination request logged to the signals owner "
                 "to join these rows into signals/leaderboard.html on its next rebuild."),
    }


# --------------------------------------------------------------------------
# RD-05: what changed (weekly diff)
# --------------------------------------------------------------------------
def cumulative_standings(results, thru_week):
    tab = {}
    for r in results:
        if r["verified"] != "yes" or r["week"] > thru_week:
            continue
        if r["margin_home"] == X.BLANK:
            continue
        for ab in (r["home"], r["away"]):
            tab.setdefault(ab, {"abbr": ab, "w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0})
    for r in results:
        if r["verified"] != "yes" or r["week"] > thru_week or r["margin_home"] == X.BLANK:
            continue
        h, a = tab[r["home"]], tab[r["away"]]
        m, tot = r["margin_home"], r["total"]
        h["pf"] += (tot + m) // 2
        h["pa"] += (tot - m) // 2
        a["pf"] += (tot - m) // 2
        a["pa"] += (tot + m) // 2
        if m > 0:
            h["w"] += 1; a["l"] += 1
        elif m < 0:
            a["w"] += 1; h["l"] += 1
        else:
            h["t"] += 1; a["t"] += 1
    return tab


def rank_table(tab):
    def key(c):
        games = c["w"] + c["l"] + c["t"]
        pct = (c["w"] + 0.5 * c["t"]) / games if games else 0.0
        return (-pct, -(c["pf"] - c["pa"]), c["abbr"])
    ordered = sorted(tab.values(), key=key)
    return {c["abbr"]: i + 1 for i, c in enumerate(ordered)}


def availability_by_week(injuries):
    """injuries.json rows -> per week per club designation counts + newly-out names."""
    weeks = sorted(iw["week"] for iw in injuries["weeks"])
    per = {}
    for row in injuries["rows"]:
        wk = per.setdefault(row["week"], {})
        cl = wk.setdefault(row["team"], {"out": [], "doubtful": [], "questionable": [],
                                         "rows": 0})
        cl["rows"] += 1
        st = (row.get("status") or "").strip().lower()
        if st == "out":
            cl["out"].append(row["player"])
        elif st == "doubtful":
            cl["doubtful"].append(row["player"])
        elif st == "questionable":
            cl["questionable"].append(row["player"])
    return weeks, per


def build_what_changed(results, inp):
    weeks = sorted({r["week"] for r in results if r["verified"] == "yes"})
    inj_weeks, inj_per = availability_by_week(inp["injuries"])
    rank_hist, rating_hist = {}, {}
    for w in weeks:
        tab = cumulative_standings(results, w)
        rank_hist[w] = rank_table(tab)
        train = [r for r in results if r["verified"] == "yes" and r["week"] <= w]
        mf, _tf = X.fit_all(train, lam_net=X.LAMBDA_NET, lam_pace=X.LAMBDA_PACE)
        rating_hist[w] = {t: round(v, 3) for t, v in mf["param"].items()}

    # store the weekly snapshots (the diff is rendered FROM these, never hand-written)
    for w in weeks:
        wd = HIST / f"week-{w:02d}"
        wd.mkdir(parents=True, exist_ok=True)
        tab = cumulative_standings(results, w)
        with open(wd / "standings_thru.csv", "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["abbr", "w", "l", "t", "pf", "pa", "rank", "source"])
            for c in sorted(tab.values(), key=lambda x: rank_hist[w][x["abbr"]]):
                wr.writerow([c["abbr"], c["w"], c["l"], c["t"], c["pf"], c["pa"],
                             rank_hist[w][c["abbr"]], STANDINGS_SOURCE])
        with open(wd / "ratings_thru.csv", "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["abbr", "rating", "source"])
            for ab in sorted(rating_hist[w]):
                wr.writerow([ab, rating_hist[w][ab], CONTROLS_SOURCE])
        if w in inj_per:
            with open(wd / "availability.csv", "w", newline="") as f:
                wr = csv.writer(f)
                wr.writerow(["team", "out_n", "doubtful_n", "questionable_n", "rows",
                             "source"])
                for ab in sorted(inj_per[w]):
                    cl = inj_per[w][ab]
                    wr.writerow([ab, len(cl["out"]), len(cl["doubtful"]),
                                 len(cl["questionable"]), cl["rows"],
                                 X.INJURY_URL.format(w=w)])

    club_rows = []
    diff_weeks = [w for w in weeks if (w - 1) in rank_hist and (w - 1) in rating_hist]
    for w in weeks:
        if w not in diff_weeks:
            continue
        prev_r, cur_r = rank_hist[w - 1], rank_hist[w]
        prev_e, cur_e = rating_hist[w - 1], rating_hist[w]
        for ab in sorted(cur_r):
            prev_avail = inj_per.get(w - 1, {}).get(ab)
            cur_avail = inj_per.get(w, {}).get(ab)
            newly_out, returned = [], []
            if prev_avail and cur_avail:
                p_out = set(prev_avail["out"])
                c_out = set(cur_avail["out"])
                newly_out = sorted(c_out - p_out)
                returned = sorted(p_out - c_out)
            club_rows.append({
                "week": w, "abbr": ab,
                "rank_prev": prev_r[ab], "rank_now": cur_r[ab],
                "rank_change": prev_r[ab] - cur_r[ab],
                "rating_prev": prev_e.get(ab, X.BLANK), "rating_now": cur_e.get(ab, X.BLANK),
                "rating_change": (round(cur_e[ab] - prev_e[ab], 3)
                                  if ab in prev_e and ab in cur_e else X.BLANK),
                "out_prev": len(prev_avail["out"]) if prev_avail else X.BLANK,
                "out_now": len(cur_avail["out"]) if cur_avail else X.BLANK,
                "out_change": (len(cur_avail["out"]) - len(prev_avail["out"])
                               if prev_avail and cur_avail else X.BLANK),
                "newly_out": ", ".join(newly_out) if newly_out else X.BLANK,
                "returned": ", ".join(returned) if returned else X.BLANK,
                "availability_captured": "yes" if (prev_avail and cur_avail) else "no",
                "source": X.INJURY_URL.format(w=w),
            })
    latest = max(diff_weeks) if diff_weeks else X.BLANK
    avail_weeks_note = ("Availability change is computable only where consecutive weekly "
                        "injury-report snapshots exist in the repository (weeks 8-10). "
                        "Weeks 1-7 have no stored snapshot, so those cells are blank and "
                        "flagged rather than inferred.")
    return {
        "as_of": X.AS_OF,
        "weeks": weeks,
        "snapshots_stored": [str(HIST.relative_to(ROOT) / f"week-{w:02d}") for w in weeks],
        "ranking_rule": ("rank by win pct (ties: point differential, then abbr) from the "
                         "verified results feed; deterministic and pre-registered"),
        "rating_rule": (f"margin-model club effect refit on verified finals through each week "
                        f"(scripts/x3_signals.py fit_all, default lambda {X.LAMBDA_NET}, "
                        f"the published fallback when nested selection is unavailable)"),
        "availability_note": avail_weeks_note,
        "latest_diff_week": latest,
        "rows": club_rows,
        "source": CONTROLS_SOURCE,
    }


# --------------------------------------------------------------------------
# RD-07: injury/personnel ablation (with vs without availability features)
# --------------------------------------------------------------------------
def ridge_solve(rows, lam):
    """Closed-form ridge with unpenalised intercept. Pure python, deterministic.

    rows: list of (feature_index_list, value, y). Features: 0 = intercept slot handled
    separately; here we build the full matrix explicitly.
    """
    # build matrix
    n_feat = max(i for feats, _v, _y in rows for i in feats) + 1
    Xmat, y = [], []
    for feats, _v, yi in rows:
        x = [0.0] * (n_feat + 1)
        x[0] = 1.0
        for i in feats:
            x[i + 1] = 1.0 * _v.get(i, 1.0)
        Xmat.append(x)
        y.append(float(yi))
    k = n_feat + 1
    ata = [[0.0] * k for _ in range(k)]
    aty = [0.0] * k
    for x, yi in zip(Xmat, y):
        for a in range(k):
            aty[a] += x[a] * yi
            for b in range(k):
                ata[a][b] += x[a] * x[b]
    for a in range(1, k):
        ata[a][a] += lam
    # gaussian elimination with partial pivoting
    m = [row[:] + [aty[i]] for i, row in enumerate(ata)]
    for col in range(k):
        piv = max(range(col, k), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            m[col][col] = m[col][col] or 1e-12
            piv = col
        m[col], m[piv] = m[piv], m[col]
        pv = m[col][col]
        for r in range(k):
            if r == col:
                continue
            fac = m[r][col] / pv
            if fac:
                for c in range(col, k + 1):
                    m[r][c] -= fac * m[col][c]
    beta = [m[i][k] / m[i][i] for i in range(k)]
    return beta


def predict_ab(rows_all, beta, game, with_avail):
    teams = rows_all["teams"]
    pred = beta[0]
    pred += beta[1 + teams.index(game["home"])]
    pred -= beta[1 + teams.index(game["away"])]
    if with_avail:
        pred += beta[-2] * game["avail_home"] + beta[-1] * game["avail_away"]
    return pred


def build_ablation(results, avail_rows):
    load = {(a["week"], a["team"]): a["load_total"] for a in avail_rows}
    weeks_with_avail = sorted({r["week"] for r in avail_rows})

    def attach(games):
        out = []
        for g in games:
            if g["verified"] != "yes" or g["margin_home"] == X.BLANK:
                continue
            ah = load.get((g["week"], g["home"]))
            aa = load.get((g["week"], g["away"]))
            if ah is None or aa is None:
                continue
            gg = dict(g)
            gg["avail_home"], gg["avail_away"] = ah, aa
            out.append(gg)
        return out

    avail_weeks = sorted({g["week"] for g in attach(results)})
    if len(avail_weeks) < 2:
        return {"status": "not computable", "weeks_with_availability": avail_weeks}

    teams = sorted({r["home"] for r in results} | {r["away"] for r in results})

    def build_rows(games):
        rows = []
        for g in games:
            v = {teams.index(g["home"]): 1.0, teams.index(g["away"]): -1.0}
            v[len(teams)] = g["avail_home"]
            v[len(teams) + 1] = g["avail_away"]
            rows.append((list(v.keys()), v, g["margin_home"]))
        return rows

    rng = random.Random(SEED)
    arms = []
    pooled_test = []
    for w in avail_weeks[1:]:
        train = [g for g in attach(results) if g["week"] < w]
        test = [g for g in attach(results) if g["week"] == w]
        if not train or not test:
            continue
        # Arm A: ratings only (same form and lambda as the published engine)
        fA = X._fit(train, "margin", X.LAMBDA_NET)
        # Arm B: identical ratings plus the two availability features
        betaB = ridge_solve(build_rows(train), X.LAMBDA_NET)
        eA, eB = [], []
        for g in test:
            pA = fA["const"] + fA["param"].get(g["home"], 0.0) - fA["param"].get(g["away"], 0.0)
            pB = predict_ab({"teams": teams}, betaB, g, True)
            eA.append(abs(g["margin_home"] - pA))
            eB.append(abs(g["margin_home"] - pB))
        n = len(eA)
        diffs = [a - b for a, b in zip(eA, eB)]     # positive = availability arm better
        boots = []
        for _ in range(BOOTSTRAP_N):
            s = [diffs[rng.randrange(n)] for _ in range(n)]
            boots.append(sum(s) / n)
        boots.sort()
        contest = sum(1 for a, b in zip(eA, eB) if b < a)
        arms.append({
            "test_week": w,
            "train_weeks": sorted({g["week"] for g in train}),
            "train_n": len(train), "test_n": n,
            "mae_A": round(sum(eA) / n, 3), "mae_B": round(sum(eB) / n, 3),
            "mae_delta": round((sum(eA) - sum(eB)) / n, 3),
            "delta_ci95": [round(boots[int(0.025 * (BOOTSTRAP_N - 1))], 3),
                           round(boots[int(0.975 * (BOOTSTRAP_N - 1))], 3)],
            "contest_B_wins": contest,
            "contest_rate": round(contest / n, 4) if n else X.BLANK,
            "lambda": X.LAMBDA_NET,
        })
        pooled_test.extend(diffs)
    if pooled_test:
        n = len(pooled_test)
        boots = []
        for _ in range(BOOTSTRAP_N):
            s = [pooled_test[rng.randrange(n)] for _ in range(n)]
            boots.append(sum(s) / n)
        boots.sort()
        pooled = {
            "test_n": n,
            "mae_delta_mean": round(sum(pooled_test) / n, 3),
            "delta_ci95": [round(boots[int(0.025 * (BOOTSTRAP_N - 1))], 3),
                           round(boots[int(0.975 * (BOOTSTRAP_N - 1))], 3)],
            "verdict": ("inconclusive at this sample size" if
                        boots[int(0.025 * (BOOTSTRAP_N - 1))] <= 0 <=
                        boots[int(0.975 * (BOOTSTRAP_N - 1))] else
                        ("availability features reduce MAE" if sum(pooled_test) > 0
                         else "availability features increase MAE")),
        }
    else:
        pooled = {"test_n": 0}
    return {
        "as_of": X.AS_OF,
        "registered_rule": ("Same model form (home constant + 32 club margin effects, ridge "
                            f"lambda {X.LAMBDA_NET}), identical training windows. Arm A = "
                            "published ratings only; Arm B = identical ratings plus the two "
                            "official availability-load features (0-4 scale, derived from the "
                            "official injury report joined to club depth charts). MAE delta "
                            f"> 0 means the availability arm is closer to the truth. Paired "
                            f"bootstrap, {BOOTSTRAP_N} resamples, seed {SEED}."),
        "weeks_with_availability": avail_weeks,
        "arms": arms,
        "pooled": pooled,
        "caveat": ("Availability snapshots exist only for weeks 8-10, so the ablation trains "
                   "on very few weeks and its confidence intervals are wide. The interval - "
                   "not a point estimate - is the published result; the panel becomes "
                   "decisive only when the snapshot history spans more weeks (RD-06)."),
        "source": X.INJURY_URL.format(w=10),
    }


# --------------------------------------------------------------------------
# RD-10: publish every model total twice (estimator A vs estimator B)
# --------------------------------------------------------------------------
def build_two_totals(results, graded):
    """Estimator A = the published engine total (close_fair_total).
    Estimator B = registered alternative: lagged team scoring means through W-1.

    Both are published with a gap column; neither is collapsed until a
    pre-registered walk-forward comparison favours one (below).
    """
    # team scoring means, lagged (train = finals strictly before the game's week)
    pts = {}
    def lagged_mean(team, w):
        vals = pts.get(team, [])
        prior = [v for (tw, v) in vals if tw < w]
        return sum(prior) / len(prior) if prior else None

    for r in results:
        if r["verified"] != "yes" or r["total"] == X.BLANK:
            continue
        w = r["week"]
        pts.setdefault(r["home"], []).append((w, (r["total"] + r["margin_home"]) / 2))
        pts.setdefault(r["away"], []).append((w, (r["total"] - r["margin_home"]) / 2))

    rows = []
    eA, eB = [], []
    for g in graded:
        tA = g.get("close_fair_total")
        mh = lagged_mean(g["home"], g["week"])
        ma = lagged_mean(g["away"], g["week"])
        if tA in (X.BLANK, None) or mh is None or ma is None:
            continue
        tB = round(mh + ma, 2)
        act = g["actual_total"]
        eA.append(abs(act - tA))
        eB.append(abs(act - tB))
        rows.append({
            "game_id": g["game_id"], "week": g["week"], "home": g["home"],
            "away": g["away"], "estimator_A": tA, "estimator_B": tB,
            "gap": round(tA - tB, 2), "actual_total": act,
            "err_A": round(abs(act - tA), 2), "err_B": round(abs(act - tB), 2),
        })
    rng = random.Random(SEED)
    n = len(eA)
    if n:
        diffs = [a - b for a, b in zip(eA, eB)]   # positive = A closer
        boots = []
        for _ in range(BOOTSTRAP_N):
            s = [diffs[rng.randrange(n)] for _ in range(n)]
            boots.append(sum(s) / n)
        boots.sort()
        lo, hi = boots[int(0.025 * (BOOTSTRAP_N - 1))], boots[int(0.975 * (BOOTSTRAP_N - 1))]
        maeA = sum(eA) / n
        maeB = sum(eB) / n
        if lo <= 0 <= hi:
            verdict = ("keep both - the walk-forward comparison cannot separate them "
                       "(CI spans zero), so neither may be collapsed")
        elif sum(diffs) > 0:
            verdict = "estimator A closer on this window; collapse decision deferred until the CI excludes zero on a later, untouched window"
        else:
            verdict = "estimator B closer on this window; collapse decision deferred until the CI excludes zero on a later, untouched window"
    else:
        lo = hi = X.BLANK
        maeA = maeB = X.BLANK
        verdict = "no graded totals with both estimators available"
    return {
        "as_of": X.AS_OF,
        "registered_rule": ("Estimator A = the published signals-engine total "
                            "(ridge pace model, scripts/x3_signals.py). Estimator B = sum of "
                            "each team's lagged mean scored points through week W-1 (verified "
                            "finals only). Both stay visible per game with a gap column; a "
                            "collapse to one estimator requires the pre-registered "
                            f"walk-forward comparison to separate them (paired bootstrap "
                            f"{BOOTSTRAP_N} resamples, seed {SEED}, CI excluding zero)."),
        "n": n,
        "mae_A": round(maeA, 3) if n else X.BLANK,
        "mae_B": round(maeB, 3) if n else X.BLANK,
        "mae_gap": round(maeA - maeB, 3) if n else X.BLANK,
        "delta_ci95": [round(lo, 3), round(hi, 3)] if n else [X.BLANK, X.BLANK],
        "verdict": verdict,
        "rows": rows,
        "source": CONTROLS_SOURCE,
    }


# --------------------------------------------------------------------------
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inp, results, graded = run_engine()

    controls = build_controls(results, graded)
    (OUT / "control_baselines.json").write_text(json.dumps(controls, indent=1) + "\n")

    changed = build_what_changed(results, inp)
    (OUT / "what_changed.json").write_text(json.dumps(changed, indent=1) + "\n")

    avail_rows = json.loads((ROOT / "signals" / "data" / "club_availability.json")
                            .read_text())
    abl = build_ablation(results, avail_rows)
    (OUT / "ablations.json").write_text(json.dumps(abl, indent=1) + "\n")

    totals = build_two_totals(results, graded)
    (OUT / "two_totals.json").write_text(json.dumps(totals, indent=1) + "\n")

    print(f"controls: C1 SU {controls['controls'][0]['su_rate']} "
          f"(n={controls['controls'][0]['su_n']}), "
          f"C2 SU {controls['controls'][1]['su_rate']} "
          f"(n={controls['controls'][1]['su_n']}); "
          f"contest C1 {controls['controls'][0]['contest']['win_rate']} "
          f"C2 {controls['controls'][1]['contest']['win_rate']} "
          f"model {controls['model_side_published']['contest']['win_rate']}")
    print(f"what-changed: {len(changed['rows'])} club-week diff rows, "
          f"snapshots in {len(changed['snapshots_stored'])} week dirs")
    print(f"ablation: pooled {abl['pooled']}")
    print(f"two-totals: n={totals['n']} MAE A {totals['mae_A']} B {totals['mae_B']} "
          f"CI {totals['delta_ci95']} -> {totals['verdict'][:60]}")


if __name__ == "__main__":
    main()
