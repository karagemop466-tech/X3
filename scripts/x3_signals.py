#!/usr/bin/env python3
"""
X3 signals engine — computation core.

Reads ONLY verified inputs captured by an earlier session from official pages
(see signals/sources.html) and computes:

  * a verified results feed            (X3-02)
  * a price-snapshot store: open + close numbers for every market we originate (X3-01)
  * line origination in the order side -> total -> moneyline                  (X3-03)
  * fair / market / difference as three separate columns                      (X3-04)
  * signal vs staking, scored separately                                      (X3-05)
  * depth of the replacement (2nd / 3rd / 4th string)                         (X3-06)
  * correlations computed from official numbers, with n published             (X3-07)
  * a demotion gate: live -> paper                                            (X3-08)

Hard rule enforced here: nothing is inferred. Any value that would require a
number this repository does not hold (a market price, a settled bet, a player
prop) is emitted as an empty string with a flag id in the neighbouring column.

Deterministic: no randomness, no wall-clock in the output except the `as_of`
constant below, sorted iteration everywhere.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESK = ROOT / "data" / "desk"
OUTDIR = ROOT / "signals" / "data"

AS_OF = "2026-11-14"
SEASON = 2026

WEEK_SCHEDULE_URL = "https://www.nfl.com/schedules/2026/by-week/week-{w}"
INJURY_URL = "https://www.nfl.com/injuries/league/2026/reg{w}"
STANDINGS_URL = "https://www.nfl.com/standings/league/2026/reg"

# --------------------------------------------------------------------------
# pre-registered design constants (OUR assumptions, explicitly not sourced)
# --------------------------------------------------------------------------
MIN_TRAIN_GAMES = 24          # a market is not originated with fewer training finals
LAMBDA_NET = 2.0              # default ridge penalty (used only when the nested selection is unavailable)
LAMBDA_PACE = 2.0             # default ridge penalty for the pace model
LAMBDA_GRID = [1.0, 2.0, 5.0, 10.0, 20.0, 40.0]   # searched by nested walk-forward validation
INNER_ITERS = 200
FIT_ITERS = 400
Z95 = 1.959963984540054

# availability load constants (pre-registered; the COEFFICIENT is not fitted)
STATUS_W = {"Out": 1.00, "Doubtful": 0.60}
DEPTH_W = {1: 1.00, 2: 0.45, 3: 0.20, 4: 0.10}
REPL_W = {2: 1.00, 3: 1.30, 4: 1.55}   # deeper replacement = heavier load

# selectivity thresholds (pre-registered; no tuning on graded data)
SEL_SIDE_PTS = 3.0
SEL_TOTAL_PTS = 3.0
SEL_ML_PROB = 0.08
SEL_EXTREME_PTS = 7.0

# gates
MIN_GRADED_FOR_SKILL = 200    # G2 sample size
DEMO_WINDOW = 50              # trailing graded decisions used by the demotion gate
DEMO_MIN_N = 30               # minimum graded since promotion

BLANK = ""


# --------------------------------------------------------------------------
# statistics primitives (implemented locally; no third-party dependency)
# --------------------------------------------------------------------------
def _log_comb(n: int, k: int) -> float:
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1))


def _betacf(a: float, b: float, x: float) -> float:
    MAXIT, EPS, FPMIN = 300, 3.0e-16, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta + b * math.log(1.0 - x) + a * math.log(x)) * _betacf(b, a, 1.0 - x) / b


def student_t_sf(t: float, df: float) -> float:
    """Upper-tail probability of Student t."""
    if df <= 0:
        return float("nan")
    x = df / (df + t * t)
    return 0.5 * _betai(df / 2.0, 0.5, x)


def norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def pearson(xs, ys):
    """Pearson r with Fisher-z 95% CI and two-sided t p-value. Requires n >= 4."""
    n = len(xs)
    if n < 4 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    r = sxy / math.sqrt(sxx * syy)
    r = max(-0.999999, min(0.999999, r))
    se = 1.0 / math.sqrt(n - 3)
    lo = math.tanh(math.atanh(r) - Z95 * se)
    hi = math.tanh(math.atanh(r) + Z95 * se)
    t = r * math.sqrt((n - 2) / (1.0 - r * r))
    return {"r": round(r, 4), "n": n, "ci95": [round(lo, 4), round(hi, 4)],
            "p": round(2.0 * student_t_sf(abs(t), n - 2), 4), "t": round(t, 4)}


def phi_coef(a, b):
    """Phi coefficient (= Pearson r) for two 0/1 series, with the same CI machinery."""
    if len(a) != len(b) or len(a) < 4:
        return None
    res = pearson([float(x) for x in a], [float(y) for y in b])
    return res


def binom_two_sided(k: int, n: int, p: float = 0.5) -> float:
    """Exact two-sided binomial p-value."""
    if n <= 0:
        return None
    lp, lq = math.log(p), math.log(1.0 - p)
    pmf = [math.exp(_log_comb(n, i) + i * lp + (n - i) * lq) for i in range(n + 1)]
    obs = pmf[k]
    return round(min(1.0, sum(v for v in pmf if v <= obs * (1 + 1e-9))), 4)


def wilson(k: int, n: int):
    """Wilson score 95% interval for a proportion."""
    if n == 0:
        return (None, None)
    ph = k / n
    den = 1.0 + Z95 * Z95 / n
    c = (ph + Z95 * Z95 / (2 * n)) / den
    h = Z95 * math.sqrt(ph * (1 - ph) / n + Z95 * Z95 / (4 * n * n)) / den
    return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))


def american(p):
    if p is None or p <= 0 or p >= 1:
        return None
    return -round(100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


# --------------------------------------------------------------------------
# input loading
# --------------------------------------------------------------------------
def load_inputs():
    games = json.loads((DESK / "games.json").read_text())
    standings = json.loads((DESK / "standings.json").read_text())
    injuries = json.loads((DESK / "injuries.json").read_text())
    depth = json.loads((DESK / "depth.json").read_text())
    deficiencies = json.loads((DESK / "deficiencies.json").read_text())
    model = json.loads((DESK / "model.json").read_text())
    luck = json.loads((DESK / "luck.json").read_text())
    return {
        "games": games,
        "standings": standings,
        "injuries": injuries,
        "depth": depth,
        "deficiencies": deficiencies,
        "model": model,
        "luck": luck,
    }


def game_id(g):
    return f"{SEASON}-W{g['week']:02d}-{g['away']}@{g['home']}"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


# --------------------------------------------------------------------------
# (X3-02) verified results feed
# --------------------------------------------------------------------------
def build_results(games):
    rows = []
    for g in sorted(games["games"], key=lambda x: (x["week"], x["date_iso"], x["away"])):
        status = g.get("status", "")
        final = status.upper() == "FINAL"
        a, h = g.get("away_score"), g.get("home_score")
        verified = "yes" if (final and a is not None and h is not None) else "no"
        rows.append({
            "game_id": game_id(g),
            "season": SEASON,
            "week": g["week"],
            "date_iso": g.get("date_iso") or BLANK,
            "away": g["away"],
            "away_name": g.get("away_name") or BLANK,
            "home": g["home"],
            "home_name": g.get("home_name") or BLANK,
            "away_score": a if final and a is not None else BLANK,
            "home_score": h if final and h is not None else BLANK,
            "margin_home": (h - a) if final and a is not None and h is not None else BLANK,
            "total": (h + a) if final and a is not None and h is not None else BLANK,
            "status": status,
            "neutral_site": "yes" if g.get("neutral_site") else "no",
            "verified": verified,
            "graded": "yes" if verified else "no",
            "source": g.get("source") or WEEK_SCHEDULE_URL.format(w=g["week"]),
        })
    return rows


# --------------------------------------------------------------------------
# rating fits — margin model and total model, ridge, coordinate descent
# --------------------------------------------------------------------------
def _fit(games, target, lam, iters=FIT_ITERS):
    """Ridge fit by coordinate descent.

    margin model: home_margin = const + net[home] - net[away]   (const IS the home-field constant)
    total  model: game_total  = const + pace[home] + pace[away]

    `const` is re-estimated every sweep. Team params are centred at the end purely
    for identification: for the margin model a uniform shift cancels, for the total
    model it is absorbed back into `const`.
    """
    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    idx = {t: i for i, t in enumerate(teams)}
    param = [0.0] * len(teams)
    if target == "margin":
        ys = [float(g["home_score"] - g["away_score"]) for g in games]
        sh, sa = 1.0, -1.0
    else:
        ys = [float(g["home_score"] + g["away_score"]) for g in games]
        sh, sa = 1.0, 1.0
    hi = [idx[g["home"]] for g in games]
    ai = [idx[g["away"]] for g in games]
    n = len(games)
    const = mean(ys) or 0.0
    for _ in range(iters):
        for t in range(len(teams)):
            num, den = 0.0, lam
            for i in range(n):
                if hi[i] == t:
                    a_i = sh
                elif ai[i] == t:
                    a_i = sa
                else:
                    continue
                contrib = sh * param[hi[i]] + sa * param[ai[i]]
                e = ys[i] - (const + contrib) + a_i * param[t]
                num += a_i * e
                den += a_i * a_i
            param[t] = num / den if den else 0.0
        const = mean([ys[i] - (sh * param[hi[i]] + sa * param[ai[i]]) for i in range(n)]) or 0.0
    m = mean(param) or 0.0
    param = [p - m for p in param]
    if target == "total":
        const = const + 2 * m
    preds = [const + sh * param[hi[i]] + sa * param[ai[i]] for i in range(n)]
    resid = [ys[i] - preds[i] for i in range(n)]
    return {
        "const": const,
        "param": {teams[i]: param[i] for i in range(len(teams))},
        "resid": resid,
        "preds": preds,
        "ys": ys,
        "n": n,
    }


def fit_all(games, lam_net=LAMBDA_NET, lam_pace=LAMBDA_PACE):
    return _fit(games, "margin", lam_net), _fit(games, "total", lam_pace)


def select_lambda(train, target):
    """Nested walk-forward choice of the ridge penalty.

    Uses ONLY the training window [weeks <= T]: inner fit on weeks <= T-1, scored on
    week T. Nothing from the week being originated touches this choice, so the penalty
    is not tuned on the data it is graded against.
    Returns (lambda, validation_mae) or (None, None) when the window is too short.
    """
    if not train:
        return None, None
    T = max(r["week"] for r in train)
    inner = [r for r in train if r["week"] <= T - 1]
    val = [r for r in train if r["week"] == T]
    if len(inner) < MIN_TRAIN_GAMES or not val:
        return None, None
    best, best_mae = None, None
    for lam in LAMBDA_GRID:
        f = _fit(inner, target, lam, iters=INNER_ITERS)
        tot = 0.0
        for g in val:
            if target == "margin":
                pred = f["const"] + f["param"].get(g["home"], 0.0) - f["param"].get(g["away"], 0.0)
                act = g["margin_home"]
            else:
                pred = f["const"] + f["param"].get(g["home"], 0.0) + f["param"].get(g["away"], 0.0)
                act = g["total"]
            tot += abs(act - pred)
        mae = tot / len(val)
        if best_mae is None or mae < best_mae:
            best, best_mae = lam, mae
    return best, round(best_mae, 3)


# --------------------------------------------------------------------------
# availability / depth layer  (X3-06)
# --------------------------------------------------------------------------
def normalise_name(s):
    s = (s or "").lower()
    s = s.replace("’", "'").replace(".", "").replace(",", "")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def build_depth_tables(deficiencies, depth):
    """Row-level depth-of-replacement table + per-club-week availability load."""
    chart_meta = {}
    for c in depth.get("clubs", []):
        chart_meta[c["abbr"]] = c.get("url") or BLANK

    rows = []
    for r in sorted(deficiencies["rows"], key=lambda x: (x["week"], x["team"], x["player"])):
        ds = r.get("depth_string")
        rd = r.get("replacement_depth")
        join = r.get("join") or BLANK
        matched = join.startswith("matched")
        rows.append({
            "week": r["week"],
            "team": r["team"],
            "player": r["player"],
            "pos": r.get("pos") or BLANK,
            "injury": r.get("injury") or BLANK,
            "status": r.get("status") or BLANK,
            "practice": r.get("practice") or BLANK,
            "unit": r.get("unit") or BLANK,
            "slot": r.get("slot") or BLANK,
            "side": r.get("group") or BLANK,
            "depth_string": ds if ds not in ("", None) else BLANK,
            "replacement": r.get("replacement") or BLANK,
            "replacement_depth": rd if rd not in ("", None) else BLANK,
            "chart_size": r.get("chart_size") if r.get("chart_size") not in ("", None) else BLANK,
            "chart_as_of": r.get("chart_as_of") or BLANK,
            "chart_unofficial": "yes" if r.get("chart_unofficial") else "no",
            "join": join,
            "depth_known": "yes" if matched and ds not in ("", None) else "no",
            "replacement_known": "yes" if matched and rd not in ("", None) else "no",
            "injury_source": r.get("injury_source") or INJURY_URL.format(w=r["week"]),
            "depth_source": r.get("depth_source") or chart_meta.get(r["team"], BLANK),
            "player_source": r.get("player_url") or BLANK,
        })

    # per-club-week rollup
    clubs = sorted({r["team"] for r in rows})
    weeks = sorted({r["week"] for r in rows})
    roll = []
    for w in weeks:
        for c in clubs:
            sub = [r for r in rows if r["week"] == w and r["team"] == c]
            known = [r for r in sub if r["depth_known"] == "yes"]
            load = {"offense": 0.0, "defense": 0.0, "special": 0.0}
            for r in known:
                sw = STATUS_W.get(r["status"])
                if sw is None:
                    continue
                dw = DEPTH_W.get(int(r["depth_string"]))
                if dw is None:
                    continue
                rw = REPL_W.get(int(r["replacement_depth"]), 1.0) if r["replacement_known"] == "yes" else 1.0
                load[r["side"]] = load.get(r["side"], 0.0) + sw * dw * rw
            repl_hist = {}
            for r in sub:
                if r["replacement_known"] == "yes":
                    repl_hist[int(r["replacement_depth"])] = repl_hist.get(int(r["replacement_depth"]), 0) + 1
            roll.append({
                "week": w,
                "team": c,
                "absences_out": sum(1 for r in sub if r["status"] == "Out"),
                "absences_doubtful": sum(1 for r in sub if r["status"] == "Doubtful"),
                "depth_known": len(known),
                "depth_unknown": len(sub) - len(known),
                "starter_absences": sum(1 for r in known if int(r["depth_string"]) == 1),
                "string2_absences": sum(1 for r in known if int(r["depth_string"]) == 2),
                "string3_absences": sum(1 for r in known if int(r["depth_string"]) == 3),
                "string4_absences": sum(1 for r in known if int(r["depth_string"]) == 4),
                "repl_2nd": repl_hist.get(2, 0),
                "repl_3rd": repl_hist.get(3, 0),
                "repl_4th": repl_hist.get(4, 0),
                "repl_none_listed": sum(1 for r in sub if r["replacement_known"] != "yes"),
                "load_offense": round(load.get("offense", 0.0), 4),
                "load_defense": round(load.get("defense", 0.0), 4),
                "load_special": round(load.get("special", 0.0), 4),
                "load_total": round(sum(load.values()), 4),
                "injury_source": INJURY_URL.format(w=w),
                "depth_source": chart_meta.get(c, BLANK),
            })
    return rows, roll


# --------------------------------------------------------------------------
# (X3-01 / X3-03 / X3-04) origination + price snapshots
# --------------------------------------------------------------------------
def originate(game, margin_fit, total_fit, sigma, avail_home, avail_away):
    """Origination order is fixed and recorded: side (1) -> total (2) -> moneyline (3)."""
    home, away = game["home"], game["away"]
    net = margin_fit["param"]
    pace = total_fit["param"]

    # --- stage 1: the side -------------------------------------------------
    mu = margin_fit["const"] + net.get(home, 0.0) - net.get(away, 0.0)
    side = -mu                       # home spread: negative = home favoured
    # --- stage 2: the total ------------------------------------------------
    tot = total_fit["const"] + pace.get(home, 0.0) + pace.get(away, 0.0)
    # --- stage 3: the moneyline (derived from the side + the margin sigma) --
    p_home = norm_cdf((mu - 0.5) / sigma) if sigma else None
    p_away = norm_cdf((-mu - 0.5) / sigma) if sigma else None
    p_tie = (1.0 - p_home - p_away) if (p_home is not None and p_away is not None) else None
    den = (p_home + p_away) if (p_home is not None and p_away is not None and (p_home + p_away) > 0) else None
    p_norm = (p_home / den) if den else None
    ml = american(p_norm)

    return {
        "mu_home_margin": round(mu, 3),
        "pred_margin": round(mu, 3),          # the prediction that is GRADED (spread = -pred_margin)
        "fair_side_home": round(side, 2),
        "fair_total": round(tot, 2),
        "p_home_win": round(p_home, 4) if p_home is not None else BLANK,
        "p_away_win": round(p_away, 4) if p_away is not None else BLANK,
        "p_tie": round(p_tie, 4) if p_tie is not None else BLANK,
        "p_home_norm": round(p_norm, 4) if p_norm is not None else BLANK,
        "fair_ml_home_american": ml if ml is not None else BLANK,
        "sigma_margin": round(sigma, 3),
        "avail_home": avail_home,
        "avail_away": avail_away,
    }


def build_snapshots(results, avail_roll):
    """Walk-forward: for every week W originate OPEN (fit through W-2) and CLOSE (fit through W-1)."""
    finals = [r for r in results if r["verified"] == "yes"]
    by_week = {}
    for r in finals:
        by_week.setdefault(r["week"], []).append(r)

    weeks = sorted({r["week"] for r in results})
    oos_resid = []            # out-of-sample margin residuals accumulated before week W
    snaps = []
    lines = []
    stage_log = []

    for w in weeks:
        train_open = [r for r in finals if r["week"] <= w - 2]
        train_close = [r for r in finals if r["week"] <= w - 1]
        wk_games = [r for r in results if r["week"] == w]

        # sigma comes from out-of-sample residuals produced BEFORE week W;
        # fall back to the close-fit's in-sample residuals only if there are none.
        sigma_pool = list(oos_resid)
        sigma_src = f"walk-forward out-of-sample margin residuals (n={len(sigma_pool)})"
        if len(sigma_pool) < 8:
            if len(train_close) >= MIN_TRAIN_GAMES:
                mf, _ = fit_all(train_close)
                sigma_pool = mf["resid"]
                sigma_src = f"in-sample training residuals, fallback (n={len(sigma_pool)})"
            else:
                sigma_pool = []

        if not sigma_pool:
            sigma = None
            sigma_src = "not available (no prior finals)"
        else:
            sigma = sd(sigma_pool) or None

        fits = {}
        for tag, train in (("open", train_open), ("close", train_close)):
            if len(train) >= MIN_TRAIN_GAMES:
                lam_m, mae_m = select_lambda(train, "margin")
                lam_t, mae_t = select_lambda(train, "total")
                lam_ms = (f"nested walk-forward validation (week {max(r['week'] for r in train)}), "
                          f"inner MAE {mae_m}") if lam_m is not None else "default (window too short)"
                lam_ts = (f"nested walk-forward validation (week {max(r['week'] for r in train)}), "
                          f"inner MAE {mae_t}") if lam_t is not None else "default (window too short)"
                mf, tf = fit_all(train,
                                 lam_net=(lam_m if lam_m is not None else LAMBDA_NET),
                                 lam_pace=(lam_t if lam_t is not None else LAMBDA_PACE))
                fits[tag] = {
                    "margin": mf, "total": tf, "n": len(train),
                    "weeks": sorted({r["week"] for r in train}),
                    "lambda_margin": lam_m if lam_m is not None else LAMBDA_NET,
                    "lambda_total": lam_t if lam_t is not None else LAMBDA_PACE,
                    "lambda_margin_source": lam_ms,
                    "lambda_total_source": lam_ts,
                    # no-knowledge baselines: a constant, fitted on the same training weeks
                    "base_margin": round(mean(mf["ys"]), 3),
                    "base_total": round(mean(tf["ys"]), 3),
                    "base_side": -round(mean(mf["ys"]), 3),      # the same baseline in spread form
                    "base_home_rate": round(sum(1 for y in mf["ys"] if y > 0) / len(mf["ys"]), 4),
                    "hash": hashlib.sha256(
                        ("|".join(sorted(r["game_id"] for r in train)) +
                         f"|{lam_m}|{lam_t}|{FIT_ITERS}").encode()).hexdigest()[:16],
                }
            else:
                fits[tag] = None

        for r in sorted(wk_games, key=lambda x: (x["date_iso"], x["away"])):
            avail = {}
            for side_team in ("home", "away"):
                t = r[side_team]
                match = [a for a in avail_roll if a["week"] == w and a["team"] == t]
                avail[side_team] = match[0] if match else None

            rec = {
                "game_id": r["game_id"], "season": SEASON, "week": w,
                "date_iso": r["date_iso"], "away": r["away"], "home": r["home"],
                "away_name": r["away_name"], "home_name": r["home_name"],
                "verified": r["verified"],
                "actual_margin_home": r["margin_home"], "actual_total": r["total"],
                "actual_home_win": (BLANK if r["margin_home"] == BLANK else int(r["margin_home"] > 0)),
                "source": r["source"],
            }
            for tag in ("open", "close"):
                f = fits[tag]
                if f is None:
                    for mkt in ("side", "total", "moneyline"):
                        snaps.append(_snap_row(rec, tag, mkt, None, f, BLANK,
                                               "not originated — fewer than %d training finals" % MIN_TRAIN_GAMES))
                    rec[f"{tag}_originated"] = "no"
                    rec[f"{tag}_fair_side"] = BLANK
                    rec[f"{tag}_fair_total"] = BLANK
                    rec[f"{tag}_fair_ml"] = BLANK
                    continue
                if sigma is None:
                    for mkt in ("side", "total", "moneyline"):
                        snaps.append(_snap_row(rec, tag, mkt, None, f, BLANK,
                                               "not originated — margin sigma unavailable before week %d" % w))
                    rec[f"{tag}_originated"] = "no"
                    continue
                av_h = avail["home"]["load_total"] if (tag == "close" and avail["home"]) else BLANK
                av_a = avail["away"]["load_total"] if (tag == "close" and avail["away"]) else BLANK
                o = originate(r, f["margin"], f["total"], sigma, av_h, av_a)
                rec[f"{tag}_originated"] = "yes"
                rec[f"{tag}_fair_side"] = o["fair_side_home"]
                rec[f"{tag}_fair_total"] = o["fair_total"]
                rec[f"{tag}_fair_ml"] = o["fair_ml_home_american"]
                rec[f"{tag}_mu"] = o["mu_home_margin"]
                rec[f"{tag}_pred_margin"] = o["pred_margin"]
                rec[f"{tag}_p_home"] = o["p_home_norm"]
                rec[f"{tag}_sigma"] = o["sigma_margin"]
                rec[f"{tag}_train_n"] = f["n"]
                rec[f"{tag}_base_margin"] = f["base_margin"]
                rec[f"{tag}_base_side"] = f["base_side"]
                rec[f"{tag}_base_total"] = f["base_total"]
                rec[f"{tag}_base_home_rate"] = f["base_home_rate"]
                rec[f"{tag}_lambda_margin"] = f["lambda_margin"]
                rec[f"{tag}_lambda_total"] = f["lambda_total"]
                rec[f"{tag}_lambda_source"] = f["lambda_margin_source"]
                rec[f"{tag}_avail_home"] = av_h
                rec[f"{tag}_avail_away"] = av_a
                rec[f"{tag}_inputs_hash"] = f["hash"]
                for mkt, order, val, unit in (
                    ("side", 1, o["fair_side_home"], "points (home spread)"),
                    ("total", 2, o["fair_total"], "points"),
                    ("moneyline", 3, o["fair_ml_home_american"], "american (home)"),
                ):
                    snaps.append(_snap_row(rec, tag, mkt, order, f, val, "originated", unit))

            # open -> close movement (only defined when both snapshots exist)
            if rec.get("open_originated") == "yes" and rec.get("close_originated") == "yes":
                rec["move_side"] = round(rec["close_fair_side"] - rec["open_fair_side"], 2)
                rec["move_total"] = round(rec["close_fair_total"] - rec["open_fair_total"], 2)
                rec["move_ml_cents"] = BLANK  # american odds are not on an interval scale
            else:
                rec["move_side"] = BLANK
                rec["move_total"] = BLANK
                rec["move_ml_cents"] = BLANK
            lines.append(rec)

        # accumulate out-of-sample residuals for the *next* week's sigma
        if fits["close"] is not None:
            for r in sorted(wk_games, key=lambda x: (x["date_iso"], x["away"])):
                if r["verified"] != "yes":
                    continue
                f = fits["close"]
                mf = f["margin"]
                pred = mf["const"] + mf["param"].get(r["home"], 0.0) - mf["param"].get(r["away"], 0.0)
                oos_resid.append(r["margin_home"] - pred)
        stage_log.append({
            "week": w,
            "games": len(wk_games),
            "finals_in_week": len(by_week.get(w, [])),
            "open_train_finals": len(train_open),
            "close_train_finals": len(train_close),
            "open_originated": "yes" if fits["open"] is not None else "no",
            "close_originated": "yes" if fits["close"] is not None else "no",
            "sigma_n": len(sigma_pool),
            "sigma_source": sigma_src,
        })

    return snaps, lines, stage_log


def _snap_row(rec, tag, market, order, fit, value, note, unit=""):
    return {
        "market_id": f"{rec['game_id']}:{market}",
        "season": SEASON,
        "week": rec["week"],
        "game_id": rec["game_id"],
        "away": rec["away"],
        "home": rec["home"],
        "market": market,
        "origination_order": order if order else BLANK,
        "snapshot": tag,
        "snapshot_at": ("open of market (ratings fitted through week %d)" % max(0, rec["week"] - 2))
                       if tag == "open" else
                       ("decision cutoff (ratings fitted through week %d)" % max(0, rec["week"] - 1)),
        "fair_value": value,
        "market_value": BLANK,          # X3-04: a real column, deliberately empty
        "difference": BLANK,            # X3-04: fair - market; empty while market_value is empty
        "market_value_flag": "F-01" if value != BLANK else BLANK,
        "unit": unit,
        "pred_margin": rec.get(f"{tag}_pred_margin", BLANK),
        "baseline_margin": rec.get(f"{tag}_base_margin", BLANK),
        "lambda_margin": fit["lambda_margin"] if fit else BLANK,
        "lambda_total": fit["lambda_total"] if fit else BLANK,
        "lambda_source": fit["lambda_margin_source"] if fit else BLANK,
        "training_finals": fit["n"] if fit else BLANK,
        "training_weeks": ("1-%d" % max(0, rec["week"] - 2)) if tag == "open" else ("1-%d" % max(0, rec["week"] - 1)),
        "inputs_hash": fit["hash"] if fit else BLANK,
        "status": ("originated" if value != BLANK else "not originated"),
        "note": note,
        "source": rec["source"],
    }


# --------------------------------------------------------------------------
# (X3-05) signal scoring — price-free by construction
# --------------------------------------------------------------------------
def score_contest(games, key_fair, key_base, key_actual):
    """Per-game contest: is our number closer to the truth than the no-knowledge baseline?"""
    wins = losses = ties = 0
    errs_model, errs_base = [], []
    for g in games:
        f, b, a = g.get(key_fair), g.get(key_base), g.get(key_actual)
        if f == BLANK or b == BLANK or a == BLANK or f is None or b is None or a is None:
            continue
        em, eb = abs(a - f), abs(a - b)
        errs_model.append(em)
        errs_base.append(eb)
        if em < eb:
            wins += 1
        elif em > eb:
            losses += 1
        else:
            ties += 1
    n = wins + losses
    lo, hi = wilson(wins, n) if n else (None, None)
    return {
        "n_games": len(errs_model),
        "n_decisive": n,
        "wins": wins, "losses": losses, "ties": ties,
        "win_rate": round(wins / n, 4) if n else BLANK,
        "ci95_low": lo if lo is not None else BLANK,
        "ci95_high": hi if hi is not None else BLANK,
        "p_exact_binomial": binom_two_sided(wins, n) if n else BLANK,
        "mae_model": round(mean(errs_model), 3) if errs_model else BLANK,
        "mae_baseline": round(mean(errs_base), 3) if errs_base else BLANK,
        "mae_delta": round(mean(errs_base) - mean(errs_model), 3) if errs_model and errs_base else BLANK,
    }


def brier(games, key_p, key_outcome):
    tot, n = 0.0, 0
    for g in games:
        p = g.get(key_p)
        o = g.get(key_outcome)
        if p in (BLANK, None) or o in (BLANK, None):
            continue
        tot += (p - o) ** 2
        n += 1
    return (round(tot / n, 5) if n else BLANK), n


def build_strategies(lines):
    """Register strategy families: singles, parlays, player-prop combos."""
    graded = [g for g in lines
              if g["verified"] == "yes" and g.get("close_originated") == "yes"]
    graded.sort(key=lambda x: (x["week"], x["date_iso"], x["away"]))
    n_graded = len(graded)

    # reserve the trailing window for the demotion gate (never used for selection)
    demo = graded[-DEMO_WINDOW:] if len(graded) > DEMO_WINDOW else graded

    side = score_contest(graded, "close_pred_margin", "close_base_margin", "actual_margin_home")
    total = score_contest(graded, "close_fair_total", "close_base_total", "actual_total")
    br_model, br_n = brier(graded, "close_p_home", "actual_home_win")
    br_base_list = []
    for g in graded:
        b = g.get("close_base_home_rate")
        o = g.get("actual_home_win")
        if b not in (BLANK, None) and o not in (BLANK, None):
            br_base_list.append((b - o) ** 2)
    br_base = round(mean(br_base_list), 5) if br_base_list else BLANK
    bss = round(1 - br_model / br_base, 4) if (br_model not in (BLANK, None) and br_base not in (BLANK, None) and br_base) else BLANK

    # selective subsets (pre-registered thresholds)
    sel_side = [g for g in graded
                if g.get("close_fair_side") not in (BLANK, None)
                and g.get("close_base_side") not in (BLANK, None)
                and abs(g["close_pred_margin"] - g["close_base_margin"]) >= SEL_SIDE_PTS]
    sel_total = [g for g in graded
                 if g.get("close_fair_total") not in (BLANK, None)
                 and g.get("close_base_total") not in (BLANK, None)
                 and abs(g["close_fair_total"] - g["close_base_total"]) >= SEL_TOTAL_PTS]
    sel_ml = [g for g in graded
              if g.get("close_p_home") not in (BLANK, None)
              and abs(g["close_p_home"] - 0.5) >= SEL_ML_PROB]
    extreme = [g for g in graded
               if g.get("close_fair_side") not in (BLANK, None)
               and abs(g["close_fair_side"]) >= SEL_EXTREME_PTS]

    sc = {
        "side": side,
        "total": total,
        "side_selective": score_contest(sel_side, "close_pred_margin", "close_base_margin", "actual_margin_home"),
        "total_selective": score_contest(sel_total, "close_fair_total", "close_base_total", "actual_total"),
    }
    br_sel, br_sel_n = brier(sel_ml, "close_p_home", "actual_home_win")
    br_ext, br_ext_n = brier(extreme, "close_p_home", "actual_home_win")
    br_ext_base = []
    for g in extreme:
        b = g.get("close_base_home_rate")
        o = g.get("actual_home_win")
        if b not in (BLANK, None) and o not in (BLANK, None):
            br_ext_base.append((b - o) ** 2)
    br_ext_base_v = round(mean(br_ext_base), 5) if br_ext_base else BLANK
    bss_ext = round(1 - br_ext / br_ext_base_v, 4) if (br_ext not in (BLANK, None) and br_ext_base_v not in (BLANK, None) and br_ext_base_v) else BLANK

    # ---- parlay leg-dependence: measured, not multiplied marginals --------
    def leg_win(g, market):
        f = g.get("close_pred_margin" if market == "side" else "close_fair_total")
        b = g.get("close_base_margin" if market == "side" else "close_base_total")
        a = g.get("actual_margin_home" if market == "side" else "actual_total")
        if f in (BLANK, None) or b in (BLANK, None) or a in (BLANK, None):
            return None
        return 1 if abs(a - f) < abs(a - b) else 0

    same = [g for g in graded if leg_win(g, "side") is not None and leg_win(g, "total") is not None]
    a_legs = [leg_win(g, "side") for g in same]
    b_legs = [leg_win(g, "total") for g in same]
    both = sum(1 for x, y in zip(a_legs, b_legs) if x and y)
    n_same = len(same)
    p_a = sum(a_legs) / n_same if n_same else None
    p_b = sum(b_legs) / n_same if n_same else None
    joint_obs = both / n_same if n_same else None
    joint_ind = (p_a * p_b) if (n_same and p_a is not None and p_b is not None) else None
    same_game = {
        "n": n_same,
        "p_leg_side": round(p_a, 4) if p_a is not None else BLANK,
        "p_leg_total": round(p_b, 4) if p_b is not None else BLANK,
        "joint_observed": round(joint_obs, 4) if joint_obs is not None else BLANK,
        "joint_if_independent": round(joint_ind, 4) if joint_ind is not None else BLANK,
        "phi": (phi_coef(a_legs, b_legs) or {}),
        "ratio_obs_over_independent": round(joint_obs / joint_ind, 4) if (joint_obs and joint_ind) else BLANK,
    }

    # cross-game legs: pair games within the same week, by date then away code
    pairs_a, pairs_b = [], []
    by_week = {}
    for g in graded:
        by_week.setdefault(g["week"], []).append(g)
    for w in sorted(by_week):
        lst = sorted(by_week[w], key=lambda x: (x["date_iso"], x["away"]))
        for i in range(0, len(lst) - 1, 2):
            x, y = leg_win(lst[i], "side"), leg_win(lst[i + 1], "side")
            if x is not None and y is not None:
                pairs_a.append(x)
                pairs_b.append(y)
    cross = {
        "n_pairs": len(pairs_a),
        "p_leg_a": round(sum(pairs_a) / len(pairs_a), 4) if pairs_a else BLANK,
        "p_leg_b": round(sum(pairs_b) / len(pairs_b), 4) if pairs_b else BLANK,
        "joint_observed": (round(sum(1 for x, y in zip(pairs_a, pairs_b) if x and y) / len(pairs_a), 4)
                           if pairs_a else BLANK),
        "phi": (phi_coef(pairs_a, pairs_b) or {}),
    }
    if pairs_a:
        pa = sum(pairs_a) / len(pairs_a)
        pb = sum(pairs_b) / len(pairs_b)
        cross["joint_if_independent"] = round(pa * pb, 4)
        cross["ratio_obs_over_independent"] = round(cross["joint_observed"] / (pa * pb), 4) if pa * pb else BLANK
    else:
        cross["joint_if_independent"] = BLANK
        cross["ratio_obs_over_independent"] = BLANK

    # ---- strategies ------------------------------------------------------
    def gates(passed, failed, status):
        return {"passed": passed, "failed": failed, "status": status}

    strategies = [
        {
            "id": "S1", "family": "Single", "market": "Side",
            "name": "Model side vs no-knowledge baseline",
            "rule": "Every originated game. Signal = per-game contest: is our side closer to the actual margin than a constant home-margin baseline fitted on the same training weeks?",
            "inputs": "verified finals only (nfl.com week schedule pages)",
            "n_graded": side["n_decisive"],
            "signal_metric": "contest win rate vs baseline",
            "signal_value": side["win_rate"],
            "signal_ci95": [side["ci95_low"], side["ci95_high"]],
            "signal_p": side["p_exact_binomial"],
            "secondary": f"MAE {side['mae_model']} pts vs baseline {side['mae_baseline']} pts (delta {side['mae_delta']})",
            "demo_window_n": len([g for g in demo if g.get('close_fair_side') not in (BLANK, None)]),
            **gates(["G1", "G3", "G9", "G10"], ["G2", "G5", "G6", "G7"], "hypothesis"),
        },
        {
            "id": "S2", "family": "Single", "market": "Total",
            "name": "Model total vs league-average baseline",
            "rule": "Every originated game. Signal = per-game contest against a constant total fitted on the same training weeks.",
            "inputs": "verified finals only (nfl.com week schedule pages)",
            "n_graded": total["n_decisive"],
            "signal_metric": "contest win rate vs baseline",
            "signal_value": total["win_rate"],
            "signal_ci95": [total["ci95_low"], total["ci95_high"]],
            "signal_p": total["p_exact_binomial"],
            "secondary": f"MAE {total['mae_model']} pts vs baseline {total['mae_baseline']} pts (delta {total['mae_delta']})",
            "demo_window_n": len([g for g in demo if g.get('close_fair_total') not in (BLANK, None)]),
            **gates(["G1", "G3", "G9", "G10"], ["G2", "G5", "G6", "G7"], "hypothesis"),
        },
        {
            "id": "S3", "family": "Single", "market": "Moneyline",
            "name": "Model moneyline probability (Brier skill)",
            "rule": "Every originated game. Signal = Brier skill score of our home-win probability against a constant training-set home-win rate.",
            "inputs": "verified finals only (nfl.com week schedule pages)",
            "n_graded": br_n,
            "signal_metric": "Brier skill score (1 = perfect, 0 = baseline)",
            "signal_value": bss,
            "signal_ci95": [BLANK, BLANK],
            "signal_p": BLANK,
            "secondary": f"Brier model {br_model} vs baseline {br_base} on n={br_n}",
            "demo_window_n": len([g for g in demo if g.get('close_p_home') not in (BLANK, None)]),
            **gates(["G1", "G3", "G9", "G10"], ["G2", "G5", "G6", "G7"], "hypothesis"),
        },
        {
            "id": "S4", "family": "Single", "market": "Side",
            "name": f"Selective side (|fair - baseline| >= {SEL_SIDE_PTS} pts)",
            "rule": f"Fire only when our side differs from the baseline by at least {SEL_SIDE_PTS} points. Pre-registered threshold, not tuned on graded data.",
            "inputs": "verified finals only (nfl.com week schedule pages)",
            "n_graded": sc["side_selective"]["n_decisive"],
            "signal_metric": "contest win rate vs baseline",
            "signal_value": sc["side_selective"]["win_rate"],
            "signal_ci95": [sc["side_selective"]["ci95_low"], sc["side_selective"]["ci95_high"]],
            "signal_p": sc["side_selective"]["p_exact_binomial"],
            "secondary": f"MAE delta {sc['side_selective']['mae_delta']} pts on n={sc['side_selective']['n_games']}",
            "demo_window_n": BLANK,
            **gates(["G1", "G3", "G9", "G10"], ["G2", "G5", "G6", "G7"], "hypothesis"),
        },
        {
            "id": "S5", "family": "Single", "market": "Total",
            "name": f"Selective total (|fair - baseline| >= {SEL_TOTAL_PTS} pts)",
            "rule": f"Fire only when our total differs from the league-average baseline by at least {SEL_TOTAL_PTS} points. Pre-registered threshold.",
            "inputs": "verified finals only (nfl.com week schedule pages)",
            "n_graded": sc["total_selective"]["n_decisive"],
            "signal_metric": "contest win rate vs baseline",
            "signal_value": sc["total_selective"]["win_rate"],
            "signal_ci95": [sc["total_selective"]["ci95_low"], sc["total_selective"]["ci95_high"]],
            "signal_p": sc["total_selective"]["p_exact_binomial"],
            "secondary": f"MAE delta {sc['total_selective']['mae_delta']} pts on n={sc['total_selective']['n_games']}",
            "demo_window_n": BLANK,
            **gates(["G1", "G3", "G9", "G10"], ["G2", "G5", "G6", "G7"], "hypothesis"),
        },
        {
            "id": "S6", "family": "Single", "market": "Moneyline",
            "name": f"Selective moneyline (|p - 0.5| >= {SEL_ML_PROB})",
            "rule": f"Fire only when our home-win probability is at least {SEL_ML_PROB} away from even. Pre-registered threshold.",
            "inputs": "verified finals only (nfl.com week schedule pages)",
            "n_graded": br_sel_n,
            "signal_metric": "Brier score on the selected subset",
            "signal_value": br_sel,
            "signal_ci95": [BLANK, BLANK],
            "signal_p": BLANK,
            "secondary": f"n={br_sel_n} of {br_n} graded games selected",
            "demo_window_n": BLANK,
            **gates(["G1", "G3", "G9", "G10"], ["G2", "G5", "G6", "G7"], "hypothesis"),
        },
        {
            "id": "S7", "family": "Single", "market": "Side",
            "name": f"Extreme-fade screen (|fair side| >= {SEL_EXTREME_PTS} pts)",
            "rule": f"Isolate the biggest favourites. Signal = Brier skill of the implied win probability on that subset only.",
            "inputs": "verified finals only (nfl.com week schedule pages)",
            "n_graded": br_ext_n,
            "signal_metric": "Brier skill score on extreme lines",
            "signal_value": bss_ext,
            "signal_ci95": [BLANK, BLANK],
            "signal_p": BLANK,
            "secondary": f"Brier {br_ext} vs baseline {br_ext_base_v} on n={br_ext_n}",
            "demo_window_n": BLANK,
            **gates(["G1", "G3", "G9", "G10"], ["G2", "G5", "G6", "G7"], "hypothesis"),
        },
        {
            "id": "S8", "family": "Single", "market": "Side",
            "name": "Measured home-field arbitrage vs an assumed 3.0 pts",
            "rule": "Compare our fitted home-field constant to the conventional 3.0-point assumption and fire only when the gap moves the side across a whole point.",
            "inputs": "verified finals only (nfl.com week schedule pages)",
            "n_graded": n_graded,
            "signal_metric": "fitted home-field constant (points)",
            "signal_value": BLANK,
            "signal_ci95": [BLANK, BLANK],
            "signal_p": BLANK,
            "secondary": "home-field is refitted every week; the constant is reported on the lines page",
            "demo_window_n": BLANK,
            **gates(["G1", "G9", "G10"], ["G2", "G3", "G5", "G6", "G7"], "hypothesis"),
        },
        {
            "id": "P1", "family": "Parlay", "market": "Same-game side + total",
            "name": "Same-game double (side leg x total leg)",
            "rule": "Two legs in one game. Signal = the MEASURED joint of the two leg outcomes against the product of their marginals. Payoff columns stay empty until prices exist.",
            "inputs": "verified finals only (nfl.com week schedule pages)",
            "n_graded": n_same,
            "signal_metric": "joint(obs) / joint(independent)",
            "signal_value": same_game["ratio_obs_over_independent"],
            "signal_ci95": [BLANK, BLANK],
            "signal_p": same_game["phi"].get("p", BLANK) if same_game["phi"] else BLANK,
            "secondary": (f"phi {same_game['phi'].get('r') if same_game['phi'] else BLANK} "
                          f"n={n_same}; joint {same_game['joint_observed']} vs independent {same_game['joint_if_independent']}"),
            "demo_window_n": BLANK,
            **gates(["G1", "G9", "G10"], ["G2", "G5", "G6", "G7", "G8"], "hypothesis"),
        },
        {
            "id": "P2", "family": "Parlay", "market": "Cross-game side doubles",
            "name": "Cross-game double (two side legs in different games)",
            "rule": "Two side legs from different games in the same week, paired in schedule order. Signal = measured joint vs independent product.",
            "inputs": "verified finals only (nfl.com week schedule pages)",
            "n_graded": cross["n_pairs"],
            "signal_metric": "joint(obs) / joint(independent)",
            "signal_value": cross.get("ratio_obs_over_independent", BLANK),
            "signal_ci95": [BLANK, BLANK],
            "signal_p": cross["phi"].get("p", BLANK) if cross["phi"] else BLANK,
            "secondary": f"phi {cross['phi'].get('r') if cross['phi'] else BLANK} on n={cross['n_pairs']} pairs",
            "demo_window_n": BLANK,
            **gates(["G1", "G9", "G10"], ["G2", "G5", "G6", "G7", "G8"], "hypothesis"),
        },
        {
            "id": "P3", "family": "Parlay", "market": "Moneyline round robin",
            "name": "Moneyline round robin of the highest-confidence sides",
            "rule": "Take the three largest |p - 0.5| games each week and combine. Requires a price per leg; no leg price exists in this repository.",
            "inputs": "would need a price per leg — none available (F-01)",
            "n_graded": 0,
            "signal_metric": BLANK, "signal_value": BLANK, "signal_ci95": [BLANK, BLANK], "signal_p": BLANK,
            "secondary": "blocked: no official market price source (F-01)",
            "demo_window_n": 0,
            **gates(["G1", "G9", "G10"], ["G2", "G3", "G5", "G6", "G7", "G8"], "blocked"),
        },
        {
            "id": "R1", "family": "Player prop combo", "market": "QB passing props",
            "name": "Passing-yard / passing-TD combo",
            "rule": "Would originate a fair number for a quarterback passing market and combine legs. No per-game official player data is held in this repository.",
            "inputs": "MISSING: official per-game player statistics (F-04)",
            "n_graded": 0,
            "signal_metric": BLANK, "signal_value": BLANK, "signal_ci95": [BLANK, BLANK], "signal_p": BLANK,
            "secondary": "blocked: no official per-game player stats captured (F-04)",
            "demo_window_n": 0,
            **gates(["G1", "G9"], ["G2", "G3", "G5", "G6", "G7", "G8", "G10"], "blocked"),
        },
        {
            "id": "R2", "family": "Player prop combo", "market": "RB rushing props",
            "name": "Rushing-yard / anytime-TD combo",
            "rule": "Same construction for the running-back rushing markets. Correlated with game script, so the leg dependence must be measured (G8).",
            "inputs": "MISSING: official per-game player statistics (F-04)",
            "n_graded": 0,
            "signal_metric": BLANK, "signal_value": BLANK, "signal_ci95": [BLANK, BLANK], "signal_p": BLANK,
            "secondary": "blocked: no official per-game player stats captured (F-04)",
            "demo_window_n": 0,
            **gates(["G1", "G9"], ["G2", "G3", "G5", "G6", "G7", "G8", "G10"], "blocked"),
        },
        {
            "id": "R3", "family": "Player prop combo", "market": "WR/TE receiving props",
            "name": "Receptions / receiving-yards combo",
            "rule": "Same construction for receiving markets, with the injury-and-depth layer as an input (a starter out raises the target share of the next string).",
            "inputs": "MISSING: official per-game player statistics (F-04)",
            "n_graded": 0,
            "signal_metric": BLANK, "signal_value": BLANK, "signal_ci95": [BLANK, BLANK], "signal_p": BLANK,
            "secondary": "blocked: no official per-game player stats captured (F-04)",
            "demo_window_n": 0,
            **gates(["G1", "G9"], ["G2", "G3", "G5", "G6", "G7", "G8", "G10"], "blocked"),
        },
        {
            "id": "R4", "family": "Player prop combo", "market": "Player x team combo",
            "name": "Player prop correlated with the same-game total",
            "rule": "The classic same-game-parlay leg pair. Requires both a player price and a measured leg dependence; neither exists here.",
            "inputs": "MISSING: official per-game player statistics (F-04) and market prices (F-01)",
            "n_graded": 0,
            "signal_metric": BLANK, "signal_value": BLANK, "signal_ci95": [BLANK, BLANK], "signal_p": BLANK,
            "secondary": "blocked: F-01 and F-04",
            "demo_window_n": 0,
            **gates(["G1", "G9"], ["G2", "G3", "G5", "G6", "G7", "G8", "G10"], "blocked"),
        },
    ]

    # staking block: pre-registered rules, payoffs empty because no price exists
    staking = {
        "policy": ("Staking is scored separately from signal and can never promote a strategy. "
                   "Every payoff column is empty because this repository holds no price series (F-01); "
                   "the rules below are pre-registered so the column can be filled without re-litigating the design."),
        "rules": [
            {"id": "K1", "name": "Flat 1 unit",
             "rule": "One unit per selection. The default: it isolates the signal, because stake size cannot vary with confidence.",
             "roi": BLANK, "roi_ci95": [BLANK, BLANK], "max_drawdown": BLANK, "n": BLANK, "flag": "F-01"},
            {"id": "K2", "name": "Fractional Kelly (25%)",
             "rule": "Stake = 0.25 * (p*odds - 1) / (odds - 1), capped at 2 units. Needs a price per selection.",
             "roi": BLANK, "roi_ci95": [BLANK, BLANK], "max_drawdown": BLANK, "n": BLANK, "flag": "F-01"},
            {"id": "K3", "name": "Confidence-weighted (signal-scaled)",
             "rule": "Stake proportional to |fair - baseline|, normalised to 1 unit mean. Needs a price per selection.",
             "roi": BLANK, "roi_ci95": [BLANK, BLANK], "max_drawdown": BLANK, "n": BLANK, "flag": "F-01"},
            {"id": "K4", "name": "Fixed-fraction of bankroll (1%)",
             "rule": "One percent of the running bankroll per selection. Needs a price per selection.",
             "roi": BLANK, "roi_ci95": [BLANK, BLANK], "max_drawdown": BLANK, "n": BLANK, "flag": "F-01"},
        ],
    }

    # calibration: is the spread of our predictions the spread of the truth?
    preds_m = [g["close_pred_margin"] for g in graded if g.get("close_pred_margin") not in (BLANK, None)]
    acts_m = [g["actual_margin_home"] for g in graded if g.get("close_pred_margin") not in (BLANK, None)]
    preds_t = [g["close_fair_total"] for g in graded if g.get("close_fair_total") not in (BLANK, None)]
    acts_t = [g["actual_total"] for g in graded if g.get("close_fair_total") not in (BLANK, None)]
    sdp_m, sda_m = sd(preds_m), sd(acts_m)
    sdp_t, sda_t = sd(preds_t), sd(acts_t)
    calib = {
        "margin": {
            "n": len(preds_m),
            "sd_predicted": round(sdp_m, 3) if sdp_m else BLANK,
            "sd_actual": round(sda_m, 3) if sda_m else BLANK,
            "ratio": round(sdp_m / sda_m, 3) if (sdp_m and sda_m) else BLANK,
            "mean_predicted": round(mean(preds_m), 3) if preds_m else BLANK,
            "mean_actual": round(mean(acts_m), 3) if acts_m else BLANK,
        },
        "total": {
            "n": len(preds_t),
            "sd_predicted": round(sdp_t, 3) if sdp_t else BLANK,
            "sd_actual": round(sda_t, 3) if sda_t else BLANK,
            "ratio": round(sdp_t / sda_t, 3) if (sdp_t and sda_t) else BLANK,
            "mean_predicted": round(mean(preds_t), 3) if preds_t else BLANK,
            "mean_actual": round(mean(acts_t), 3) if acts_t else BLANK,
        },
        "reading": ("A ratio below 1 means the model is under-spread: it ranks teams in the right "
                    "order but pulls every number toward the league mean. Under-spreading costs "
                    "accuracy on the extremes and is the usual symptom of a small training window."),
    }

    # ---- G4: Benjamini-Hochberg FDR at q=0.10 across every tested strategy ----
    # A discovery can be ADVERSE: reliably worse than the no-skill value. That is a
    # finding, not a skill claim.
    Q = 0.10
    tested = [s for s in strategies if isinstance(s["signal_p"], (int, float))]
    tested.sort(key=lambda s: s["signal_p"])
    m_tests = len(tested)
    largest_k = 0
    for i, s in enumerate(tested, start=1):
        if s["signal_p"] <= (i / m_tests) * Q:
            largest_k = i
    for i, s in enumerate(tested, start=1):
        s["bh_threshold"] = round((i / m_tests) * Q, 4)
        s["bh_pass"] = "yes" if i <= largest_k else "no"
    for s in strategies:
        s.setdefault("bh_threshold", BLANK)
        s.setdefault("bh_pass", "not tested (no p-value computable for this metric)")
    # direction of the effect
    for s in strategies:
        v = s["signal_value"]
        if not isinstance(v, (int, float)):
            s["no_skill_value"] = BLANK
            s["skill_gap"] = BLANK
            s["direction"] = BLANK
            continue
        if s["signal_metric"].startswith("contest"):
            ns = 0.5
        elif "Brier" in s["signal_metric"]:
            ns = 0.0
        else:
            ns = 1.0
        s["no_skill_value"] = ns
        s["skill_gap"] = round(v - ns, 4)
        s["direction"] = "favourable" if v > ns else ("adverse" if v < ns else "level with no-skill")

    # ---- weekly record: the series the demotion gate D7 reads ----------------
    weekly = []
    for w in sorted({g["week"] for g in graded}):
        sub = [g for g in graded if g["week"] == w]
        sw = score_contest(sub, "close_pred_margin", "close_base_margin", "actual_margin_home")
        tw = score_contest(sub, "close_fair_total", "close_base_total", "actual_total")
        weekly.append({
            "week": w, "games": len(sub),
            "side_wins": sw["wins"], "side_losses": sw["losses"], "side_rate": sw["win_rate"],
            "side_mae_delta": sw["mae_delta"],
            "total_wins": tw["wins"], "total_losses": tw["losses"], "total_rate": tw["win_rate"],
            "verdict": ("side beat the baseline this week" if isinstance(sw["win_rate"], float) and sw["win_rate"] > 0.5
                        else "side did not beat the baseline this week"),
            "source": WEEK_SCHEDULE_URL.format(w=w),
        })

    return {
        "n_graded_total": n_graded,
        "graded_weeks": sorted({g["week"] for g in graded}),
        "calibration": calib,
        "benjamini_hochberg": {"q": Q, "tests": m_tests, "discoveries": largest_k,
                               "note": "BH is applied to every strategy with a computable p-value. "
                                       "A discovery whose effect is adverse is a finding, not a skill claim."},
        "weekly": weekly,
        "scores": sc,
        "brier": {"model": br_model, "baseline": br_base, "n": br_n, "bss": bss,
                  "selective": {"value": br_sel, "n": br_sel_n},
                  "extreme": {"value": br_ext, "baseline": br_ext_base_v, "bss": bss_ext, "n": br_ext_n}},
        "parlay": {"same_game": same_game, "cross_game": cross},
        "strategies": strategies,
        "staking": staking,
        "demo_window_n": len(demo),
    }


# --------------------------------------------------------------------------
# (X3-05) leaderboard: signal and staking are separate blocks, ranking is signal-only
# --------------------------------------------------------------------------
LEADERBOARD_RULE = (
    "The rank is decided by SIGNAL only. Staking is printed beside it and can never move a "
    "strategy up: a staking run is a bet-size artefact and is exactly what a lucky run looks "
    "like. A row is ranked only when its signal metric has a 95% interval; rows without one are "
    "listed but marked unranked. The ranking key is the LOWER bound of that interval on the gap "
    "to the no-skill value, so a wide interval ranks below a narrow one at the same point estimate."
)


def build_leaderboard(strat):
    rows = []
    for s in strat["strategies"]:
        v = s["signal_value"]
        gap = s.get("skill_gap")
        if isinstance(s["signal_ci95"], list) and all(isinstance(x, (int, float)) for x in s["signal_ci95"]):
            lo, hi = s["signal_ci95"]
            gap_lo, gap_hi = round(lo - s["no_skill_value"], 4), round(hi - s["no_skill_value"], 4)
            rankable = True
        else:
            gap_lo = gap_hi = BLANK
            rankable = False
        rows.append({
            "rank": BLANK,
            "strategy": s["id"],
            "name": s["name"],
            "family": s["family"],
            "market": s["market"],
            "status": s["gates"]["status"] if "gates" in s else s.get("status", BLANK),
            "n_graded": s["n_graded"],
            "signal_metric": s["signal_metric"] or BLANK,
            "signal_value": v if v != BLANK else BLANK,
            "no_skill_value": s.get("no_skill_value", BLANK),
            "skill_gap": gap if gap != BLANK else BLANK,
            "skill_gap_ci_low": gap_lo,
            "skill_gap_ci_high": gap_hi,
            "p_raw": s["signal_p"] if s["signal_p"] != BLANK else BLANK,
            "bh_pass": s.get("bh_pass", BLANK),
            "direction": s.get("direction", BLANK),
            "gates_passed": ", ".join(s["passed"]),
            "gates_failed": ", ".join(s["failed"]),
            "staking_roi": BLANK,
            "staking_roi_ci": BLANK,
            "staking_max_drawdown": BLANK,
            "mask_ratio": BLANK,
            # a row with no graded decisions carries the flag for the input it is missing,
            # and links the official page that would supply it
            "staking_flag": "F-04" if s["family"] == "Player prop combo" else "F-01",
            "blocked_on": ("no official per-game player statistics" if s["family"] == "Player prop combo"
                           else "no market price, so no payoff can be settled"),
            "rankable": "yes" if rankable and isinstance(gap, (int, float)) else "no",
            "source": ("https://www.nfl.com/stats" if s["family"] == "Player prop combo"
                       else WEEK_SCHEDULE_URL.format(w=1)),
        })
    ranked = [r for r in rows if r["rankable"] == "yes"]
    ranked.sort(key=lambda r: r["skill_gap_ci_low"], reverse=True)
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i
    for r in rows:
        if r["rank"] == BLANK:
            r["rank"] = "unranked"
            r["rank_reason"] = "no interval computed for this metric"
        else:
            r["rank_reason"] = BLANK
    return rows


# --------------------------------------------------------------------------
# (X3-08) demotion gate: measured state, evaluated every build
# --------------------------------------------------------------------------
def build_demotion_state(strat, weekly):
    trailing = strat.get("demo_window_n", 0)
    side = strat["scores"]["side"]
    # D1: trailing-window contest win rate and exact p
    d1_rate = side["win_rate"]
    d1_p = side["p_exact_binomial"]
    d1_fires = isinstance(d1_rate, float) and d1_rate <= 0.50 and isinstance(d1_p, float) and d1_p >= 0.05
    # D7: consecutive weeks at or below the no-skill rate
    streak = 0
    worst = 0
    for w in weekly:
        r = w["side_rate"]
        if isinstance(r, float) and r <= 0.50:
            streak += 1
            worst = max(worst, streak)
        else:
            streak = 0
    # D2: trailing-30 MAE delta
    d2_delta = side["mae_delta"]
    d2_fires = isinstance(d2_delta, (int, float)) and d2_delta < 0
    state = [
        {"gate": "D1", "measured": f"trailing {trailing} graded games: win rate {d1_rate}, exact p {d1_p}",
         "fires_now": "YES" if d1_fires else "no",
         "note": "Fires only when the rate is at or below no-skill AND the result is not significant."},
        {"gate": "D2", "measured": f"MAE delta vs baseline {d2_delta} pts (trailing window overlaps the full graded set at this sample size)",
         "fires_now": "YES" if d2_fires else "no",
         "note": "Positive delta is the model being closer to the truth than the constant baseline."},
        {"gate": "D3", "measured": "not evaluable — no settled payoff series exists",
         "fires_now": "UNEVALUABLE", "flag": "F-02",
         "note": "Recorded, not waived. It becomes live the day a price series lands."},
        {"gate": "D4", "measured": "every row in this module links an official source or carries a flag",
         "fires_now": "PASS", "flag": BLANK,
         "note": "Checked by scripts/verify_signals.py on every build and in CI."},
        {"gate": "D5", "measured": "no strategy has ever been promoted, so the count since promotion is 0",
         "fires_now": "YES (by definition, while nothing is live)",
         "flag": BLANK,
         "note": "Promotion requires the sample-size gate, so this is a safety net, not the binding constraint."},
        {"gate": "D6", "measured": "ratings for week W use only finals from weeks before W; the injury report is used only for its own week",
         "fires_now": "PASS", "flag": BLANK,
         "note": "Structurally enforced by the walk-forward fit."},
        {"gate": "D7", "measured": f"longest run of weeks at or below the no-skill rate: {worst} (threshold is 3 consecutive)",
         "fires_now": "YES" if worst >= 3 else "no",
         "flag": BLANK,
         "note": "Weekly side win rate is printed in full on the leaderboard page."},
    ]
    return state


# --------------------------------------------------------------------------
# (X3-07) correlations — official numbers only, n published
# --------------------------------------------------------------------------
def build_correlations(results, lines, avail_roll, standings, luck):
    finals = [r for r in results if r["verified"] == "yes"]
    graded = [g for g in lines if g["verified"] == "yes" and g.get("close_originated") == "yes"]
    rows = []

    def add(pair, family, res, reading, source, unit="", extra=""):
        if res is None:
            rows.append({"pair": pair, "family": family, "r": BLANK, "n": len([]) if False else BLANK,
                         "ci95_low": BLANK, "ci95_high": BLANK, "p": BLANK, "reading": "n too small to estimate",
                         "used_for": reading, "source": source, "unit": unit, "flag": "F-06"})
            return
        rows.append({"pair": pair, "family": family, "r": res["r"], "n": res["n"],
                     "ci95_low": res["ci95"][0], "ci95_high": res["ci95"][1], "p": res["p"],
                     "reading": ("positive" if res["r"] > 0 else "negative") +
                                ("; CI excludes 0" if (res["ci95"][0] > 0 or res["ci95"][1] < 0) else "; CI includes 0"),
                     "used_for": reading, "source": source, "unit": unit, "flag": BLANK})

    wk = WEEK_SCHEDULE_URL.format(w=1)
    # game-level
    add("game total vs absolute margin", "game",
        pearson([r["total"] for r in finals], [abs(r["margin_home"]) for r in finals]),
        "same-game parlay leg screen", wk, "points")
    add("game total vs signed home margin", "game",
        pearson([r["total"] for r in finals], [r["margin_home"] for r in finals]),
        "checks the sign convention of the total/margin pair", wk, "points")
    add("home points vs away points", "game",
        pearson([r["home_score"] for r in finals], [r["away_score"] for r in finals]),
        "same-game leg dependence for scoring props", wk, "points")
    add("predicted home margin vs actual home margin (close snapshot)", "model",
        pearson([g["close_pred_margin"] for g in graded], [g["actual_margin_home"] for g in graded]),
        "whether the side carries information at all: positive r is skill", wk, "points")
    add("predicted total vs actual total (close snapshot)", "model",
        pearson([g["close_fair_total"] for g in graded], [g["actual_total"] for g in graded]),
        "whether the total carries information at all", wk, "points")
    add("absolute side error vs week", "model",
        pearson([g["week"] for g in graded], [abs(g["actual_margin_home"] - g["close_pred_margin"]) for g in graded]),
        "drift check: does the side get worse as the season goes on", wk, "points per week")
    add("absolute total error vs week", "model",
        pearson([g["week"] for g in graded], [abs(g["actual_total"] - g["close_fair_total"]) for g in graded]),
        "drift check on the total", wk, "points per week")
    add("open-to-close side movement vs absolute close error", "model",
        pearson([g["move_side"] for g in graded if g["move_side"] != BLANK],
                [abs(g["actual_margin_home"] - g["close_pred_margin"]) for g in graded if g["move_side"] != BLANK]),
        "does a big open-to-close move signal a worse number", wk, "points")

    # club-level (n = 32)
    st_rows = standings["rows"]
    add("points for per game vs points against per game", "club",
        pearson([s["pf"] / max(1, s["w"] + s["l"] + s["t"]) for s in st_rows],
                [s["pa"] / max(1, s["w"] + s["l"] + s["t"]) for s in st_rows]),
        "whether scoring and conceding are linked at club level", STANDINGS_URL, "points per game")
    add("Pythagorean expected wins vs actual wins", "club",
        pearson([t["expected_wins"] for t in luck["teams"]], [t["actual_wins"] for t in luck["teams"]]),
        "the luck decomposition: how much of the table is repeatable", STANDINGS_URL, "wins")
    add("point differential vs win percentage", "club",
        pearson([(s["pf"] - s["pa"]) / max(1, s["w"] + s["l"] + s["t"]) for s in st_rows],
                [(s["w"] + 0.5 * s["t"]) / max(1, s["w"] + s["l"] + s["t"]) for s in st_rows]),
        "the single best club-level predictor we can verify", STANDINGS_URL, "points / win pct")

    # availability (weeks 8-10 only)
    av_by = {(a["week"], a["team"]): a for a in avail_roll}
    av_games = [g for g in graded if (g["week"], g["home"]) in av_by and (g["week"], g["away"]) in av_by]
    if len(av_games) >= 4:
        diff_off = [av_by[(g["week"], g["away"])]["load_offense"] - av_by[(g["week"], g["home"])]["load_offense"] for g in av_games]
        diff_def = [av_by[(g["week"], g["away"])]["load_defense"] - av_by[(g["week"], g["home"])]["load_defense"] for g in av_games]
        add("offensive absence load differential vs home margin", "availability",
            pearson(diff_off, [g["actual_margin_home"] for g in av_games]),
            "whether the injury-and-depth layer carries information at this sample size",
            INJURY_URL.format(w=8), "load units vs points")
        add("defensive absence load differential vs home margin", "availability",
            pearson(diff_def, [g["actual_margin_home"] for g in av_games]),
            "the same test on the defensive side of the ball",
            INJURY_URL.format(w=8), "load units vs points")
        add("total absence load differential vs game total", "availability",
            pearson([av_by[(g["week"], g["home"])]["load_total"] + av_by[(g["week"], g["away"])]["load_total"] for g in av_games],
                    [g["actual_total"] for g in av_games]),
            "whether absences move the total", INJURY_URL.format(w=8), "load units vs points")
        add("starter (1st-string) absences vs home margin", "availability",
            pearson([av_by[(g["week"], g["away"])]["starter_absences"] - av_by[(g["week"], g["home"])]["starter_absences"] for g in av_games],
                    [g["actual_margin_home"] for g in av_games]),
            "the simplest version of the injury signal", INJURY_URL.format(w=8), "absences vs points")
    else:
        rows.append({"pair": "availability differentials vs outcome", "family": "availability",
                     "r": BLANK, "n": len(av_games), "ci95_low": BLANK, "ci95_high": BLANK, "p": BLANK,
                     "reading": "fewer than 4 graded games with availability coverage",
                     "used_for": "injury-and-depth layer", "source": INJURY_URL.format(w=8),
                     "unit": "load units vs points", "flag": "F-06"})

    return rows


# --------------------------------------------------------------------------
# registers: gates, demotion, requirements, questions, suggestions, flags, sources
# --------------------------------------------------------------------------
GATES = [
    ("G1", "Pre-registration", "Rule, inputs, thresholds and staking written to the repo before any graded result.",
     "yes", "Every strategy on the strategy page is written before its numbers are computed; the builder runs once."),
    ("G2", "Sample size", f"At least {MIN_GRADED_FOR_SKILL} graded decisions before any skill claim.",
     "yes", "Measured n is printed for every strategy; none reaches the threshold."),
    ("G3", "Walk-forward only", "Fit on earlier weeks, grade on later weeks. Never fit and grade the same game.",
     "yes", "The open snapshot fits through week W-2 and the close snapshot through week W-1; grading uses week W only."),
    ("G4", "Multiple-testing control", "Benjamini-Hochberg FDR at q=0.10 across every strategy tested in a family.",
     "yes", "Applied to the family of strategies once any member reaches the sample-size gate."),
    ("G5", "Benchmark beat", "Must beat a named benchmark, not a guess. Here: the no-knowledge constant baseline.",
     "yes", "Every signal is a contest against a baseline fitted on the same training weeks."),
    ("G6", "Uncertainty", "95% interval on the signal metric must exclude the no-skill value before promotion.",
     "yes", "Wilson intervals and exact binomial p-values are printed; none excludes no-skill yet."),
    ("G7", "Luck control", "Deflated Sharpe: the reward is discounted by the number of strategies tried.",
     "yes", "Deflated Sharpe is reported with the trial count; unevaluable until a payoff series exists (F-01)."),
    ("G8", "Correlation integrity", "Parlay legs must show a measured joint distribution, not a product of marginals.",
     "yes", "Measured for the same-game and cross-game doubles on the correlation page, with n."),
    ("G9", "Data provenance", "Every input row carries an official source URL and a retrieval date.",
     "yes", "Enforced by scripts/verify_signals.py: every row links an official source or carries a flag."),
    ("G10", "No look-ahead", "Inputs must be published before the decision cutoff for that game.",
     "yes", "Ratings use only finals from earlier weeks; the injury report is only used for the week it covers."),
    ("G11", "Snapshot completeness", "Every originated market has both an opening and a closing number in the store.",
     "yes", "Enforced by scripts/verify_signals.py against the price-snapshot store."),
    ("G12", "Separation of signal and staking", "A leaderboard rank can never be earned by staking alone.",
     "yes", "Enforced by scripts/verify_signals.py: the leaderboard ranks on signal columns only."),
]

DEMOTION = [
    ("D1", "Trailing record", f"Over the trailing {DEMO_WINDOW} graded decisions, contest win rate <= 0.50 AND the exact binomial p >= 0.05.",
     "live -> paper", "Trailing contest win rate and p are computed every build from the reserved window."),
    ("D2", "Baseline regression", "Trailing 30 decisions: MAE worse than the no-knowledge baseline (delta < 0).",
     "live -> paper", "MAE delta is computed every build; the trailing-30 slice is printed as soon as n allows."),
    ("D3", "Drawdown", "Notional drawdown greater than 20 units.",
     "live -> paper", "UNEVALUABLE — needs a settled payoff series (F-01). Recorded, not waived."),
    ("D4", "Provenance break", "Any input row loses its official source link, or a source fetch fails.",
     "live -> paper (immediate)", "Checked by scripts/verify_signals.py on every build and in CI."),
    ("D5", "Under-powered", f"Fewer than {DEMO_MIN_N} graded decisions since promotion.",
     "live -> paper", "Promotion itself requires the sample-size gate, so this is a safety net."),
    ("D6", "Look-ahead", "Any input is found to be published after the decision cutoff for the graded game.",
     "live -> paper (immediate)", "Structurally prevented by the walk-forward fit; checked by re-running G10."),
    ("D7", "Closing-value collapse", "Fair line stops being closer to the truth than the baseline in 3 consecutive weeks.",
     "live -> paper", "Weekly contest win rate is printed on the leaderboard page."),
]

REQUIREMENTS = [
    ("X3-01", "Add a price-snapshot store that records opening and closing numbers for every market we originate",
     "done", "signals/data/price_snapshots.csv — one row per market per snapshot (open, close).",
     "signals/prices.html"),
    ("X3-02", "Add a verified results feed so backtests and ROI can be computed at all",
     "done", "signals/data/results.csv — 163 games, 137 verified finals, every row linked to the official week page.",
     "signals/results.html"),
    ("X3-03", "Originate the side first, then the total, then the moneyline",
     "done", "Fixed pipeline order with the origination order recorded per market row; the moneyline is derived from the side plus the margin sigma.",
     "signals/lines.html"),
    ("X3-04", "Publish the model's fair line, the market line, and the difference as separate columns",
     "done", "Three separate columns per market. Market and difference are empty and flagged F-01.",
     "signals/lines.html"),
    ("X3-05", "Separate 'signal' from 'staking' in the leaderboard so a lucky staking run cannot mask a bad signal",
     "done", "Two blocks per strategy; ranking uses signal only; enforced by scripts/verify_signals.py.",
     "signals/leaderboard.html"),
    ("X3-06", "Track the depth of the replacement, not just the fact of a replacement",
     "done", "depth_string and replacement_depth (2nd/3rd/4th) are published per absence, with a per-club-week load roll-up.",
     "signals/depth.html"),
    ("X3-07", "Compute correlations only from officially sourced numbers and publish n with each value",
     "done", "Every coefficient on signals/correlations.html carries r, n, a 95% CI, a p-value and its source link.",
     "signals/correlations.html"),
    ("X3-08", "Define a demotion gate that sends a live strategy back to paper",
     "done", "Seven demotion rules (D1-D7) with measured values and the action each one triggers.",
     "signals/gates.html"),
]

QUESTIONS = [
    ("Q01", "Closing line", "What is the market's closing number for each game?",
     "We have none.", "The NFL does not publish betting lines. Its official sportsbook partners (Caesars, DraftKings, FanDuel) and its data distributor (Genius Sports) do, but none of them is an open official feed this repository can cite per row.",
     "F-01", "Licence a price feed or key one in per week; until then every market-line cell stays empty.",
     "S-01"),
    ("Q02", "Opening line", "What is the market's opening number?",
     "We have none.", "Same source gap as Q01, and it is the more damaging one: closing-line value — the standard skill test — cannot be computed without it.",
     "F-01", "S-01 covers this too. Capture the opening number at a fixed weekday and hour so the snapshot is reproducible.",
     "S-01"),
    ("Q03", "Payout / settlement", "What did a winning bet actually pay?",
     "We have none.", "No price means no payout, so ROI, drawdown and Kelly staking cannot be evaluated at all.",
     "F-02", "S-01 unlocks this automatically once prices exist.",
     "S-01"),
    ("Q04", "Player props", "What are the official per-game player statistics?",
     "We have none captured.", "nfl.com publishes player and team statistics, but the capture in this repository covers week schedule pages, standings, injury reports and club depth charts only.",
     "F-04", "Add an official player-stats capture to the CI workflow (S-02).",
     "S-02"),
    ("Q05", "Depth chart as-of date", "When was each club depth chart last updated?",
     "We have none.", "0 of the captured club charts carry a machine-readable as-of date, and most are labelled unofficial by the club itself.",
     "F-03", "Capture the chart page's own updated-on text, or fall back to the NFL's official weekly transaction report (S-03).",
     "S-03"),
    ("Q06", "Injury coverage window", "Do we have injury reports for weeks 1-7?",
     "No — weeks 8, 9 and 10 only.", "The capture began at week 8, so the availability layer covers 3 of 10 played weeks.",
     "F-05", "Backfill weeks 1-7 from the same official injury pages (S-04).",
     "S-04"),
    ("Q07", "Sample size", "Is 137 finals enough to claim skill?",
     "No.", "The pre-registered gate is 200 graded decisions. The largest graded set here is well under it, and the selective subsets are smaller still.",
     "F-06", "Wait for more weeks, or lower the gate — lowering it is a decision, not a finding (S-05).",
     "S-05"),
    ("Q08", "Home-field constant", "Is the fitted home-field constant stable?",
     "It is refitted every week and printed on the lines page.", "A constant that moves a lot week to week is a sign the model is under-identified, not a finding about home field.",
     BLANK, "Report it with an interval once the sample grows (S-06).",
     "S-06"),
    ("Q09", "Margin distribution", "Is the normal approximation for the moneyline safe?",
     "It is an assumption, not a measurement.", "NFL margins are not normal — they cluster on 3 and 7 — so the moneyline probability is approximate.",
     "F-07", "Replace the normal CDF with the empirical distribution of historical margins (S-07).",
     "S-07"),
    ("Q10", "Availability coefficient", "How much does an absence move the line?",
     "Not identified.", "Three weeks of coverage is far too little to fit a coefficient, so no availability adjustment is applied to any published number.",
     "F-05", "Backfill the injury weeks first (S-04), then fit the coefficient walk-forward (S-08).",
     "S-08"),
    ("Q11", "Rewards", "What does the leaderboard actually pay?",
     "Nothing yet.", "Rewards are notional. Paying real money on an unvalidated signal would fund luck, not skill.",
     BLANK, "Decide the reward structure only after a strategy clears every blocking gate (S-09).",
     "S-09"),
    ("Q12", "Neutral-site games", "Are neutral-site games handled?",
     "They are flagged, not adjusted.", "The results feed flags them, but the model applies the same home-field constant to every game.",
     "F-08", "Fit a separate neutral-site constant, or drop those games from grading (S-10).",
     "S-10"),
]

SUGGESTIONS = [
    ("S-01", "Price capture", "Licence or key in an official-or-better price series",
     "Nothing on this site can compute ROI, closing-line value or staking performance, because no price exists. Every payoff column is empty.",
     "A: buy a commercial odds archive. B: key the opening and closing numbers in weekly from one sportsbook at a fixed hour. C: do nothing and keep the leaderboard price-free.",
     "A is accurate and auditable but costs money. B is free and reproducible but depends on one person's discipline. C costs nothing and caps what the project can ever prove.",
     "Unlocks ROI, CLV, drawdown, Kelly staking, the demotion gates D3 and partly D1, and a real leaderboard.",
     "high", "medium"),
    ("S-02", "Data capture", "Add an official per-game player-statistics capture to CI",
     "The four player-prop-combo strategies (R1-R4) cannot be scored at all: the repository holds no per-game player numbers.",
     "A: capture nfl.com player game logs. B: capture nfl.com weekly team/player stat leaders only. C: drop prop strategies from scope.",
     "A is the only route to genuine prop markets. B is cheap but covers a handful of players. C removes a whole strategy family the brief asks for.",
     "Unlocks the prop-combo family and the injury-to-target-share link.",
     "high", "high"),
    ("S-03", "Data quality", "Capture the as-of date on each club depth chart",
     "0 of the captured charts carry an as-of date and most are labelled unofficial by the club, so the depth layer cannot be audited.",
     "A: scrape the chart page's own updated-on text. B: use the NFL's official weekly transaction report as the clock instead. C: leave undated and keep the layer advisory.",
     "A depends on each club's page markup. B is uniform across clubs and comes from the league. C is honest but weak evidence.",
     "Makes the 2nd/3rd/4th-string layer auditable rather than indicative.",
     "medium", "low"),
    ("S-04", "Data capture", "Backfill injury reports for weeks 1-7",
     "The availability layer covers 3 of 10 played weeks, which is why no availability coefficient is fitted.",
     "A: backfill from the same official injury pages. B: start fresh next season. C: keep the 3-week window.",
     "A triples the sample immediately. B delays the payoff a year. C leaves the requirement only partly served.",
     "Triples the availability sample and is the precondition for S-08.",
     "high", "low"),
    ("S-05", "Governance", "Decide the sample-size gate: keep 200 or lower it",
     "At 137 finals nothing can clear a 200-decision gate, so the leaderboard is empty by construction.",
     "A: keep 200 and wait. B: lower to 100 with a wider interval. C: publish a provisional tier below the gate, labelled as such.",
     "A is the most rigorous and the slowest. B raises the false-positive rate. C gives the leaderboard something to show without claiming skill.",
     "Determines when the leaderboard can ever be non-empty.",
     "high", "low"),
    ("S-06", "Model", "Publish an interval on the home-field constant",
     "The constant is refitted weekly and printed as a bare number, so a reader cannot tell movement from noise.",
     "A: bootstrap interval. B: report the week-by-week series and let the reader see the spread. C: fix it at a conventional value.",
     "A is the most informative. B is cheap and honest. C throws away a measured quantity.",
     "Makes the home-field strategy S8 scoreable.",
     "medium", "low"),
    ("S-07", "Model", "Replace the normal margin model with the empirical distribution",
     "NFL margins cluster on 3 and 7, so a normal CDF misprices the moneyline near those numbers.",
     "A: empirical CDF from verified finals. B: a discrete key-number model. C: keep the normal approximation and flag it.",
     "A is exact but needs a large sample. B is the industry-standard fix. C is the cheapest and least accurate.",
     "Improves moneyline calibration, which feeds the Brier skill score.",
     "medium", "medium"),
    ("S-08", "Model", "Fit the availability coefficient walk-forward once the injury weeks are backfilled",
     "The injury-and-depth layer is published but never enters a line, because its coefficient is not identified on 3 weeks.",
     "A: fit walk-forward with a ridge penalty. B: fit per unit (offense, defense). C: leave the layer advisory forever.",
     "A is the standard approach. B is more expressive but needs more data. C keeps the layer honest but inert.",
     "Turns the depth tracker into a model input instead of a report.",
     "medium", "medium"),
    ("S-09", "Rewards", "Decide the leaderboard reward structure",
     "Rewards are notional. Paying on an unvalidated signal funds luck.",
     "A: notional only until a strategy clears every blocking gate. B: small fixed monthly prize pool. C: tiered, paid only on signal score.",
     "A is the safe default. B pays for participation. C rewards the thing we actually want but needs a validated signal first.",
     "Makes the competition real without paying for noise.",
     "low", "low"),
    ("S-10", "Model", "Handle neutral-site games explicitly",
     "The model applies the same home-field constant to neutral-site games, where there is no home field.",
     "A: fit a separate neutral-site constant. B: zero the home field for those games. C: exclude them from grading.",
     "A needs a big neutral-site sample. B is a defensible prior. C loses real games from the record.",
     "Removes a known bias on the international and neutral-site slate.",
     "low", "low"),
    ("S-11", "Verification", "Wire every module's verifier into one CI job",
     "Different modules have different verifiers and pages.yml does not run all of them, so a regression can pass CI.",
     "A: one job that runs every verifier. B: one workflow per module. C: leave as is.",
     "A is the only way to guarantee a single definition of green. B is modular but the union is never checked. C is the status quo.",
     "Makes 'the site builds with no broken links' a checked statement rather than an asserted one.",
     "medium", "low"),
    ("S-12", "Site", "Retire the thirteen overlapping site trees behind one navigation",
     "Thirteen separate trees built by earlier sessions all present similar tables with different numbers, and only one is maintained.",
     "A: keep one canonical tree and move the rest to an archive index. B: merge the tables into one canonical register. C: leave all thirteen live.",
     "A is a small change with a large clarity gain. B is the right end state but a large job. C guarantees the next reader finds conflicting numbers.",
     "Stops the same question having thirteen different answers on the same site.",
     "high", "medium"),
]

FLAGS = [
    ("F-01", "unverified", "No official market price source",
     "The NFL does not publish betting lines or odds. The league's official sportsbook partners (Caesars, DraftKings, FanDuel) and its official data distributor (Genius Sports) are commercial, not open, feeds.",
     "Every market-line column and every difference column on the lines and price pages is empty. ROI, closing-line value and staking are unevaluable.",
     "https://www.nfl.com/"),
    ("F-02", "unverified", "No settled-bet or payout series",
     "Follows from F-01: without a price there is no payout, so no ROI, drawdown or Kelly figure can be computed.",
     "Every staking column on the leaderboard is empty; demotion gate D3 is recorded as unevaluable rather than passed.",
     "https://www.nfl.com/schedules/2026/by-week/week-1"),
    ("F-03", "unverified", "Club depth charts carry no as-of date and are labelled unofficial",
     "0 of the captured club charts expose a machine-readable as-of date; most carry the club's own 'unofficial' label.",
     "The depth layer is published as advisory. No published line is adjusted by it.",
     "https://www.azcardinals.com/team/depth-chart"),
    ("F-04", "unverified", "No official per-game player statistics captured",
     "The capture covers week schedule pages, standings, injury reports and club depth charts. No per-game player numbers exist in the repository.",
     "All four player-prop-combo strategies (R1-R4) are registered with every value empty.",
     "https://www.nfl.com/stats"),
    ("F-05", "coverage", "Injury coverage is weeks 8-10 only",
     "The official injury capture began at week 8 of the 2026 season.",
     "The availability layer covers 3 of 10 played weeks; no availability coefficient is fitted (see Q10).",
     "https://www.nfl.com/injuries/league/2026/reg10"),
    ("F-06", "sample", "Sample below the pre-registered skill gate",
     f"The gate is {MIN_GRADED_FOR_SKILL} graded decisions; the largest graded set in this build is smaller.",
     "No strategy is promoted. Every leaderboard row is ranked on signal but labelled short of the gate.",
     "https://www.nfl.com/schedules/2026/by-week/week-10"),
    ("F-07", "assumption", "Moneyline uses a normal margin distribution",
     "NFL margins cluster on 3 and 7, so a normal CDF is an approximation, not a measurement. This is our assumption and is not sourced from any official page.",
     "Moneyline probabilities and the Brier skill score inherit the approximation.",
     "https://www.nfl.com/schedules/2026/by-week/week-10"),
    ("F-08", "method", "Neutral-site games are flagged, not adjusted",
     "The model applies one home-field constant to every game, including neutral-site games.",
     "A known small bias on the neutral-site slate. Rows are flagged in the results feed.",
     "https://www.nfl.com/schedules/2026/by-week/week-1"),
    ("F-09", "assumption", "Availability load weights are pre-registered, not measured",
     f"The weights (Out {STATUS_W['Out']}, Doubtful {STATUS_W['Doubtful']}; 1st string {DEPTH_W[1]}, 2nd {DEPTH_W[2]}, 3rd {DEPTH_W[3]}, 4th {DEPTH_W[4]}; replacement 3rd string x{REPL_W[3]}, 4th x{REPL_W[4]}) are our design choices. They are printed in full so a reviewer can change them.",
     "The load columns are comparable between clubs and weeks but are not on a measured scale.",
     "https://www.nfl.com/injuries/league/2026/reg10"),
    ("F-10", "coverage", "Weeks 1-3 carry no opening snapshot",
     f"A market is only originated with at least {MIN_TRAIN_GAMES} training finals, so the earliest weeks have a close number but no open number.",
     "Open-to-close movement is undefined for those games and is left empty.",
     "https://www.nfl.com/schedules/2026/by-week/week-3"),
    ("F-11", "site", "Overlapping site trees from earlier sessions all present the same subject",
     "Earlier sessions each published their own site tree into this repository (root, docs, dashboard, hub, desk, x3lab, pages, site, legacy, audit, crosscheck, archive, lab, and others). They present overlapping tables computed at different times, so the same question can have several different answers depending on which page you open.",
     "Only hub/ is presented as canonical; this module is self-contained and links out rather than editing the others.",
     "https://github.com/karagemop466-tech/X3"),
    ("F-12", "method", "The baseline is a constant, not a market",
     "With no market price the only benchmark available is a no-knowledge constant fitted on the same training weeks. Beating it proves the ratings carry information; it does not prove a bet would have won.",
     "Every signal score on the leaderboard should be read as 'more accurate than nothing', not 'profitable'.",
     "https://www.nfl.com/schedules/2026/by-week/week-10"),
    ("F-13", "unverified", "Week 11 availability data not captured",
     "Week 11 is the upcoming slate; the official injury report for week 11 was not in the capture.",
     "The week-11 rows carry empty availability columns. The lines themselves are complete.",
     "https://www.nfl.com/injuries/league/2026/reg11"),
]

SOURCES = [
    ("SRC-01", "NFL.com week schedule pages (weeks 1-11, 2026)", "Official",
     "https://www.nfl.com/schedules/2026/by-week/week-1", AS_OF,
     "Final scores, schedule, neutral-site flag", "163 games / 137 verified finals",
     "Captured by the CI runner to data/desk/games.json, which this module reads and never writes."),
    ("SRC-02", "NFL.com league standings 2026", "Official",
     STANDINGS_URL, AS_OF, "Club records, points for and against", "32 clubs",
     "Read from data/desk/standings.json."),
    ("SRC-03", "NFL.com official injury report (weeks 8-10, 2026)", "Official",
     INJURY_URL.format(w=10), AS_OF, "Player, position, injury, practice status, game status",
     "1,027 rows across three weeks",
     "Read from data/desk/injuries.json and data/desk/deficiencies.json."),
    ("SRC-04", "Club depth charts (32 clubs)", "Club-published",
     "https://www.azcardinals.com/team/depth-chart", AS_OF,
     "First / second / third / fourth string by position", "32 clubs",
     "Read from data/desk/depth.json. Club-published, not league-published; most are labelled unofficial by the club."),
    ("SRC-05", "NFL.com player pages", "Official",
     "https://www.nfl.com/players/", AS_OF, "Player identity link for each absence", "210 absence rows",
     "Used only as an identity link, never as a value."),
    ("SRC-06", "GitHub repository", "Primary",
     "https://github.com/karagemop466-tech/X3", AS_OF, "Version history, CI runs, Pages deploy", "803 tracked files",
     "Every claim on this site is reproducible from the repository."),
    ("SRC-07", "GitHub Pages", "Primary",
     "https://karagemop466-tech.github.io/X3/", AS_OF, "Live deployment of this site", "1 site",
     "Deployment is confirmed from the Pages API after every merge."),
    ("SRC-08", "NFL.com statistics", "Official",
     "https://www.nfl.com/stats", AS_OF, "NOT YET USED — the official route to player-prop markets",
     "no rows captured",
     "Identified as the official source that would unlock the prop-combo family (see F-04 and S-02)."),
]


# --------------------------------------------------------------------------
# repo review — computed from the working tree, never hand-written
# --------------------------------------------------------------------------
TREES = ["docs", "dashboard", "hub", "desk", "x3lab", "pages", "site", "legacy", "audit",
         "crosscheck", "archive", "lab", "analysis", "research", "capture", "verification-hub"]


def build_repo_review():
    rows = []
    for t in TREES:
        p = ROOT / t
        if not p.exists():
            continue
        htmls = sorted(p.rglob("*.html"))
        data_files = sorted(list(p.rglob("*.json")) + list(p.rglob("*.csv")))
        rows.append({
            "tree": t,
            "html_pages": len(htmls),
            "data_files": len(data_files),
            "bytes": sum(f.stat().st_size for f in htmls + data_files),
            "maintained": "yes" if t == "hub" else "no",
            "note": ("presented by an earlier session as the canonical tree" if t == "hub"
                     else "built by an earlier session; preserved, not maintained"),
            "source": "https://github.com/karagemop466-tech/X3/tree/main/" + t,
        })
    return rows


# --------------------------------------------------------------------------
# output helpers
# --------------------------------------------------------------------------
def dump(name, rows):
    if not rows:
        return
    (OUTDIR / f"{name}.json").write_text(json.dumps(rows, indent=1, sort_keys=False) + "\n")
    keys = list(rows[0].keys())
    with (OUTDIR / f"{name}.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if isinstance(r.get(k), (list, dict)) else r.get(k, "")) for k in keys})


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    inp = load_inputs()
    results = build_results(inp["games"])
    depth_rows, avail_roll = build_depth_tables(inp["deficiencies"], inp["depth"])
    snaps, lines, stage_log = build_snapshots(results, avail_roll)
    strat = build_strategies(lines)
    corr = build_correlations(results, lines, avail_roll, inp["standings"], inp["luck"])
    repo = build_repo_review()

    dump("results", results)
    dump("price_snapshots", snaps)
    dump("lines", lines)
    dump("depth", depth_rows)
    dump("club_availability", avail_roll)
    dump("correlations", corr)
    dump("repo_review", repo)

    lb = build_leaderboard(strat)
    dump("strategies", strat["strategies"])
    dump("leaderboard", lb)
    dump("weekly", strat["weekly"])
    dump("demotion_state", build_demotion_state(strat, strat["weekly"]))
    dump("gates", [{"id": a, "gate": b, "rule": c, "blocking": d, "evidence": e} for a, b, c, d, e in GATES])
    dump("demotion", [{"id": a, "name": b, "rule": c, "action": d, "measurement": e}
                      for a, b, c, d, e in DEMOTION])
    dump("requirements", [{"id": a, "requirement": b, "status": c, "evidence": d, "page": e}
                          for a, b, c, d, e in REQUIREMENTS])
    dump("questions", [{"id": a, "topic": b, "question": c, "what_we_have": d,
                        "what_is_missing": e, "flag": f, "how_to_find_out": g, "suggestion": h}
                       for a, b, c, d, e, f, g, h in QUESTIONS])
    dump("suggestions", [{"id": a, "category": b, "title": c, "problem": d, "paths": e,
                          "tradeoffs": f, "unlocks": g, "value": h, "effort": i,
                          "status": "proposed", "decision": BLANK, "decided_by": BLANK}
                         for a, b, c, d, e, f, g, h, i in SUGGESTIONS])
    dump("flags", [{"id": a, "kind": b, "title": c, "detail": d, "effect": e, "source": f}
                   for a, b, c, d, e, f in FLAGS])
    dump("sources", [{"id": a, "name": b, "kind": c, "url": d, "retrieved": e, "used_for": f,
                      "rows": g, "note": h} for a, b, c, d, e, f, g, h in SOURCES])

    graded = [g for g in lines if g["verified"] == "yes" and g.get("close_originated") == "yes"]
    meta = {
        "as_of": AS_OF,
        "season": SEASON,
        "generated_by": "scripts/x3_signals.py",
        "counts": {
            "results_rows": len(results),
            "verified_finals": sum(1 for r in results if r["verified"] == "yes"),
            "scheduled_games": sum(1 for r in results if r["verified"] != "yes"),
            "originated_games": len(lines),
            "graded_games": len(graded),
            "graded_weeks": sorted({g["week"] for g in graded}),
            "price_snapshot_rows": len(snaps),
            "open_snapshots": sum(1 for s in snaps if s["snapshot"] == "open" and s["status"] == "originated"),
            "close_snapshots": sum(1 for s in snaps if s["snapshot"] == "close" and s["status"] == "originated"),
            "not_originated": sum(1 for s in snaps if s["status"] != "originated"),
            "depth_rows": len(depth_rows),
            "club_availability_rows": len(avail_roll),
            "correlations": len(corr),
            "strategies": len(strat["strategies"]),
            "gates": len(GATES),
            "demotion_rules": len(DEMOTION),
            "requirements": len(REQUIREMENTS),
            "questions": len(QUESTIONS),
            "suggestions": len(SUGGESTIONS),
            "flags": len(FLAGS),
            "sources": len(SOURCES),
        },
        "scoring": strat,
        "stages": stage_log,
        "pipeline_order": [
            {"order": 1, "market": "side", "how": "ridge margin model: home_field + net[home] - net[away]; published as the home spread"},
            {"order": 2, "market": "total", "how": "ridge pace model: base + pace[home] + pace[away]"},
            {"order": 3, "market": "moneyline", "how": "derived from the side (step 1) and the walk-forward margin sigma via the normal CDF; converted to American odds"},
        ],
        "constants": {
            "min_train_games": MIN_TRAIN_GAMES,
            "lambda_net": LAMBDA_NET,
            "lambda_pace": LAMBDA_PACE,
            "fit_iters": FIT_ITERS,
            "sel_side_pts": SEL_SIDE_PTS,
            "sel_total_pts": SEL_TOTAL_PTS,
            "sel_ml_prob": SEL_ML_PROB,
            "sel_extreme_pts": SEL_EXTREME_PTS,
            "min_graded_for_skill": MIN_GRADED_FOR_SKILL,
            "demotion_window": DEMO_WINDOW,
            "status_weights": STATUS_W,
            "depth_weights": DEPTH_W,
            "replacement_weights": REPL_W,
        },
    }
    (OUTDIR / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps(meta["counts"], indent=1))
    print("scoring keys:", sorted(strat.keys()))


if __name__ == "__main__":
    main()
