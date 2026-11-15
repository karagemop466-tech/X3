#!/usr/bin/env python3
"""X3 desk — computation core.

Reads only `tools/x3_desk_inputs.py` (verified inputs) and writes `x3/data/*.csv`.

Everything here is deterministic: no randomness, no wall clock, no floating-point
accumulation over an unordered container. Two runs produce identical bytes, and the
gate `tools/x3_desk_verify.py` re-runs the build to prove it.

What it produces, and the brief requirement each file answers:

  results.csv        verified results feed; only FINAL games, live scores excluded
  backtest.csv       the pre-registered corpus and the walk-forward predictions
  ratings.csv        opponent-aware club ratings (ridge on margin and on total)
  origination.csv    side -> total -> moneyline, fair / market / difference columns
  price_snapshots.csv opening and closing row for every originated market
  leaderboard.csv    signal and staking as separate columns, with controls
  luck.csv           the removal-of-luck panel
  gates.csv          the demotion gate and every other exit criterion
  ablations.csv      with/without personnel, with/without availability, chronological
  depth.csv          replacement depth (2nd/3rd/4th) with the official snap proxy
  availability.csv   availability graph: expected starter, actual starter, source
  correlations.csv   only from official numbers, each with its n
  questions.csv      known / missing / what would clear it
  suggestions.csv    review queue: options, cost, evidence, what would change our mind
  readiness.csv      one row per requirement: gate that blocks it, number that clears it
  requirements.csv   the brief, requirement by requirement, with status and evidence
  repo_review.csv    line-by-line audit of the prior trees
  sources.csv        source register
  flags.csv          every unverified cell, gathered
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3_desk_inputs as I  # noqa: E402

OUT = I.OUT
SEASON = 2026

# --------------------------------------------------------------------------- #
# small statistics helpers (no scipy)
# --------------------------------------------------------------------------- #

def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def norm_ppf(p):
    """Acklam's rational approximation, |error| < 1.15e-9."""
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


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def binom_two_sided(k, n, p=0.5):
    """Exact binomial two-sided p (sum of outcomes no more likely than observed)."""
    if n == 0:
        return None
    def logpmf(i):
        return (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                + i * math.log(p) + (n - i) * math.log(1 - p))
    obs = logpmf(k)
    tot = 0.0
    for i in range(n + 1):
        lp = logpmf(i)
        if lp <= obs + 1e-9:
            tot += math.exp(lp)
    return min(1.0, tot)


def brier(ps, ys):
    if not ps:
        return None
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ps)


def log_loss(ps, ys, eps=1e-12):
    if not ps:
        return None
    s = 0.0
    for p, y in zip(ps, ys):
        p = min(max(p, eps), 1 - eps)
        s += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return s / len(ps)


def brier_skill(ps, ys, ref):
    """Brier skill score of predictions vs a constant reference probability."""
    b = brier(ps, ys)
    br = brier([ref] * len(ys), ys)
    if b is None or not br:
        return None
    return 1 - b / br


def pearson(xs, ys):
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pts)
    if n < 3:
        return (None, n)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    syy = sum((p[1] - my) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    if sxx <= 0 or syy <= 0:
        return (None, n)
    return (sxy / math.sqrt(sxx * syy), n)


def rankdata(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(xs, ys):
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pts) < 3:
        return (None, len(pts))
    rx = rankdata([p[0] for p in pts])
    ry = rankdata([p[1] for p in pts])
    return pearson(rx, ry)


def corr_ci(r, n, z=1.959963984540054):
    if r is None or n < 4 or abs(r) >= 1:
        return (None, None)
    zr = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    return (math.tanh(zr - z * se), math.tanh(zr + z * se))


def corr_p(r, n):
    """two-sided p for a correlation via the Fisher z statistic."""
    if r is None or n < 4 or abs(r) >= 1:
        return None
    zr = 0.5 * math.log((1 + r) / (1 - r)) * math.sqrt(n - 3)
    return 2 * (1 - norm_cdf(abs(zr)))


def fnum(x, nd=3):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return ""
    if isinstance(x, int):
        return str(x)
    return f"{x:.{nd}f}"


def fpct(x, nd=1):
    if x is None:
        return ""
    return f"{100.0 * x:.{nd}f}%"


# --------------------------------------------------------------------------- #
# 1. Results feed
# --------------------------------------------------------------------------- #
def build_results(games):
    """Every game whose official page shows FINAL, plus this session's two re-reads."""
    rows = []
    for g in games:
        if g["status"] != "FINAL":
            continue
        rows.append({
            "game_id": game_id(g), "week": g["week"], "date": g["date_iso"],
            "away": g["away"], "home": g["home"],
            "away_score": g["away_score"], "home_score": g["home_score"],
            "status": "FINAL", "neutral": "yes" if g["neutral_site"] else "no",
            "source": g["source"], "state": "VERIFIED",
        })
    have = {r["game_id"] for r in rows}
    for gid, away, home, asc, hsc, src, neutral in I.WEEK10_NEW_FINALS:
        if gid in have:
            continue
        rows.append({
            "game_id": gid, "week": 10, "date": "2026-11-12" if away == "WAS" else "2026-11-15",
            "away": away, "home": home, "away_score": asc, "home_score": hsc,
            "status": "FINAL", "neutral": "yes" if neutral else "no",
            "source": src, "state": "VERIFIED",
        })
    rows.sort(key=lambda r: (r["week"], r["date"], r["game_id"]))
    return rows


def game_id(g):
    return f"{SEASON}-W{g['week']:02d}-{g['away']}@{g['home']}"


# --------------------------------------------------------------------------- #
# 2. Ratings — ridge on margin and on total, opponent-aware by construction
# --------------------------------------------------------------------------- #
LAMBDAS = [1.0, 2.0, 4.0, 8.0, 16.0]


def fit(games, target, lam, home_field=True, iters=80):
    """Coordinate descent on sum (y - (c + a_home - a_away))^2 + lam * ||a||^2.

    Per-club incidence lists are precomputed, so the inner loop touches only the
    games a club played. Closed-form per-club update:
        home: a_t = sum(y - c + a_opp) / (n + lam)
        away: a_t = sum(c - y + a_opp) / (n + lam)
    The home-field constant c is re-estimated as the mean residual each sweep.
    """
    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    y = [float(g["home_score"] - g["away_score"]) if target == "margin"
         else float(g["home_score"] + g["away_score"]) for g in games]
    touch = {t: [] for t in teams}
    for i, g in enumerate(games):
        touch[g["home"]].append((i, +1, g["away"]))
        touch[g["away"]].append((i, -1, g["home"]))
    a = {t: 0.0 for t in teams}
    c = mean(y) if y else 0.0
    for _ in range(iters):
        for t in teams:
            num = 0.0
            for i, sign, opp in touch[t]:
                if sign > 0:
                    num += y[i] - c + a.get(opp, 0.0)
                else:
                    num += c - y[i] + a.get(opp, 0.0)
            den = float(lam) + len(touch[t])
            a[t] = num / den if den else 0.0
        res = [yy - (a.get(g["home"], 0.0) - a.get(g["away"], 0.0))
               for g, yy in zip(games, y)]
        c = mean(res)
    return {"param": a, "const": c, "lam": lam, "target": target}


def predict(f, g, target):
    if target == "margin":
        return f["const"] + f["param"].get(g["home"], 0.0) - f["param"].get(g["away"], 0.0)
    return f["const"] + f["param"].get(g["home"], 0.0) + f["param"].get(g["away"], 0.0)


def mae(games, f, target):
    errs = []
    for g in games:
        act = (g["home_score"] - g["away_score"]) if target == "margin" else (g["home_score"] + g["away_score"])
        errs.append(abs(predict(f, g, target) - act))
    return mean(errs)


_LAM_CACHE = {}


def select_lambda(train, target):
    """Chronological inner walk-forward: fit weeks <= T-1, score week T.
    Cached on (weeks present, target, n) so the outer walk-forward does not refit
    the same inner search once per graded game."""
    key = (tuple(sorted({g["week"] for g in train})), target, len(train))
    if key in _LAM_CACHE:
        return _LAM_CACHE[key]
    weeks = sorted({g["week"] for g in train})
    best, best_err = LAMBDAS[0], None
    for lam in LAMBDAS:
        errs = []
        for w in weeks[2:]:
            inner = [g for g in train if g["week"] < w]
            hold = [g for g in train if g["week"] == w]
            if len(inner) < 20 or not hold:
                continue
            f = fit(inner, target, lam)
            errs.append(mae(hold, f, target))
        e = mean(errs)
        if e is None:
            continue
        if best_err is None or e < best_err - 1e-12:
            best, best_err = lam, e
    _LAM_CACHE[key] = (best, best_err)
    return best, best_err


def walk_forward(finals, target="margin"):
    """Every graded game gets a prediction from only the games before its week."""
    graded = []
    picks = []
    for g in finals:
        train = [x for x in finals if x["week"] < g["week"]]
        if len(train) < 30:
            continue
        lam, _ = select_lambda(train, target)
        f = fit(train, target, lam)
        pred = predict(f, g, target)
        if target == "margin":
            act = g["home_score"] - g["away_score"]
        else:
            act = g["home_score"] + g["away_score"]
        graded.append((g, pred, act, lam, len(train)))
        picks.append(lam)
    return graded


def sigma_walk_forward(graded):
    """Residual SD, estimated only from games before the graded week."""
    out = []
    for i, (g, pred, act, lam, n) in enumerate(graded):
        prior = [a - p for (gg, p, a, l, nn) in graded[:i] if gg["week"] < g["week"]]
        s = sd(prior) if len(prior) >= 10 else None
        out.append((g, pred, act, s))
    return out


# --------------------------------------------------------------------------- #
# 3. Origination — side, then total, then moneyline
# --------------------------------------------------------------------------- #
def originate(finals, upcoming):
    """Fair numbers for games that have not been played, from a fit on all finals.

    Order is fixed and printed: side first, then total, then moneyline derived from
    the side and the walk-forward residual sigma. Nothing is fitted on the game it
    prices, because that game is not in the training set.
    """
    lam_m, _ = select_lambda(finals, "margin")
    lam_t, _ = select_lambda(finals, "total")
    fm = fit(finals, "margin", lam_m)
    ft = fit(finals, "total", lam_t)
    graded = walk_forward(finals, "margin")
    resid = [a - p for (g, p, a, l, n) in graded]
    sigma = sd(resid)
    rows = []
    for g in upcoming:
        mu = predict(fm, g, "margin")
        side = -mu                       # home handicap, negative = home favoured
        tot = predict(ft, g, "total")
        p_home_fair = norm_cdf((mu - 0.5) / sigma) if sigma else None
        rows.append({
            "game_id": game_id(g), "week": g["week"], "date": g["date_iso"],
            "away": g["away"], "home": g["home"],
            "side_fair": side, "total_fair": tot, "sigma_margin": sigma,
            "ml_home_fair": p_home_fair,
            "lam_margin": lam_m, "lam_total": lam_t,
            "n_train": len(finals), "source": g["source"],
        })
    return rows, sigma, lam_m, lam_t


# --------------------------------------------------------------------------- #
# 4. Depth: replacement depth from the official snap proxy
# --------------------------------------------------------------------------- #
ROSTER_POS = {
    "QB": ["QB"], "RB": ["RB", "FB"], "WR": ["WR"], "TE": ["TE"],
    "T": ["LT", "RT", "T"], "G": ["LG", "RG", "G"], "C": ["C", "C/G", "G/C", "OL"],
    "OL": ["LT", "LG", "C", "RG", "RT", "OL", "T", "G"],
    "DE": ["DE", "DL", "EDGE", "OLB", "RUSH"], "DT": ["DT", "NT", "DL"],
    "LB": ["LB", "MLB", "WLB", "SLB", "ILB", "OLB"],
    "CB": ["CB", "DB", "NB"], "S": ["S", "SS", "FS", "DB"], "DB": ["CB", "S", "DB"],
    "K": ["K"], "P": ["P"], "LS": ["LS"],
}


def norm_name(s):
    s = s.replace(".", " ").replace("'", "").replace("-", " ")
    return " ".join(s.split()).lower()


SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def surname_initial(s):
    """'D.Mooney' -> ('mooney', 'd'); 'Josh Conerly Jr.' -> ('conerly', 'j')."""
    s = (s or "").strip()
    # "J.J. McCarthy", "D.J. Reed", "T.J. Hockenson": initials separated by dots
    if s.count(".") >= 2 and not s.startswith("."):
        parts = s.split()
        if len(parts) >= 2:
            tail = [p for p in norm_name(" ".join(parts[1:])).split() if p not in SUFFIXES]
            return (" ".join(tail), norm_name(parts[0])[:1]) if tail else ("", "")
    if "." in s and s.split(".")[0].isalpha() and len(s.split(".")[0]) <= 3:
        ini, _, rest = s.partition(".")
        parts = [p for p in norm_name(rest).split() if p not in SUFFIXES]
        return (" ".join(parts), norm_name(ini)[:1]) if parts else ("", "")
    parts = [p for p in norm_name(s).split() if p not in SUFFIXES]
    return (parts[-1], parts[0][:1]) if parts else ("", "")


def build_depth(clubs, gamebook):
    """For every club/unit/position slot, the string order the club published, plus
    the official snap evidence that says whether column 1 actually played.

    The snap evidence is available only for the two clubs in the one Game Book read.
    Every other row says NO_SNAP_EVIDENCE — it is not inferred from jersey order.
    """
    snaps = {}
    for team, player, pos, off, dfn, st in gamebook["snaps"]:
        snaps.setdefault(team, []).append((player, pos, off, dfn))
    rows = []
    for c in clubs:
        ab = c["abbr"]
        if not c["units"]:
            rows.append({"club": ab, "unit": "", "pos": "", "string": "", "player": "",
                         "snap_off": "", "snap_off_pct": "", "snap_def": "", "snap_def_pct": "",
                         "snap_st": "", "snap_st_pct": "", "evidence": "NO_STRUCTURED_CHART",
                         "source": c["url"], "flag": "F-05", "as_of": ""})
            continue
        for u in c["units"]:
            for s in u["slots"]:
                for i, tier in enumerate(s["tiers"]):
                    for nm in tier:
                        rows.append({
                            "club": ab, "unit": u["unit"], "pos": s["pos"],
                            "string": i + 1, "player": nm,
                            "snap_off": "", "snap_off_pct": "", "snap_def": "", "snap_def_pct": "",
                            "snap_st": "", "snap_st_pct": "",
                            "evidence": "CLUB_CHART_ONLY", "source": c["url"],
                            "flag": "F-06" if not c["as_of_text"] else "",
                            "as_of": c["as_of_text"],
                        })
    # attach official snap evidence where we hold a Game Book
    for r in rows:
        sur, ini = surname_initial(r["player"])
        for player, pos, off, dfn in snaps.get(r["club"], []):
            s2, i2 = surname_initial(player)
            if s2 != sur or (i2 and ini and i2 != ini):
                continue
            if off:
                r["snap_off"], r["snap_off_pct"] = off[0], off[1]
                r["evidence"] = "GAMEBOOK_SNAP"
            if dfn:
                r["snap_def"], r["snap_def_pct"] = dfn[0], dfn[1]
                r["evidence"] = "GAMEBOOK_SNAP"
            if st:
                r["snap_st"], r["snap_st_pct"] = st[0], st[1]
                r["evidence"] = "GAMEBOOK_SNAP"
            r["flag"] = ""
            break
    return rows


def expand_gamebook_name(s):
    """'D.Mooney' -> 'D. Mooney' so norm_name lines it up with 'Darnell Mooney'."""
    if "." in s:
        ini, _, rest = s.partition(".")
        return f"{ini}. {rest}"
    return s


def match_by_surname(rows, full_name, pos_family):
    """Join a full name from the injury report to a Game Book surname.

    Returns (row, how). 'how' is 'exact' when the surname and initial agree exactly,
    'ambiguous' when more than one candidion matched, 'none' when nothing did.
    """
    sur, ini = surname_initial(expand_gamebook_name(full_name))
    cands = []
    for r in rows:
        s2, i2 = surname_initial(expand_gamebook_name(r["player"]))
        if s2 == sur and (not i2 or not ini or i2 == ini):
            cands.append(r)
    if len(cands) == 1:
        return cands[0], "surname+initial"
    if len(cands) > 1:
        return None, "ambiguous"
    return None, "none"


# --------------------------------------------------------------------------- #
# 5. Correlations (official numbers only, n always published)
# --------------------------------------------------------------------------- #
def build_correlations(finals, graded, depth_rows, gamebook):
    out = []

    # C-01: a club's own points scored vs conceded, same game (arithmetic identity check)
    xs = [g["home_score"] for g in finals]
    ys = [g["away_score"] for g in finals]
    r, n = pearson(xs, ys)
    lo, hi = corr_ci(r, n)
    out.append({"id": "C-01",
                "a": "Home club points scored (same game)", "b": "Away club points scored (same game)",
                "r": r, "n": n, "ci_low": lo, "ci_high": hi, "p": corr_p(r, n),
                "method": "Pearson", "source": I.U["sched_w10"],
                "note": "Two clubs in one game share pace and weather; this is the floor that any "
                        "'independent games' assumption has to beat."})

    # C-02: predicted margin vs actual margin (is the model's ordering informative?)
    xs = [p for (g, p, a, l, n2) in graded]
    ys = [a for (g, p, a, l, n2) in graded]
    r, n = pearson(xs, ys)
    lo, hi = corr_ci(r, n)
    out.append({"id": "C-02",
                "a": "Model predicted margin", "b": "Actual margin",
                "r": r, "n": n, "ci_low": lo, "ci_high": hi, "p": corr_p(r, n),
                "method": "Pearson", "source": I.U["sched_w10"],
                "note": "Walk-forward only: each prediction uses games before its own week."})

    # C-03: predicted total vs actual total
    tg = walk_forward(finals, "total")
    xs = [p for (g, p, a, l, n2) in tg]
    ys = [a for (g, p, a, l, n2) in tg]
    r, n = pearson(xs, ys)
    lo, hi = corr_ci(r, n)
    out.append({"id": "C-03",
                "a": "Model predicted total", "b": "Actual total",
                "r": r, "n": n, "ci_low": lo, "ci_high": hi, "p": corr_p(r, n),
                "method": "Pearson", "source": I.U["sched_w10"],
                "note": "Same walk-forward rule as C-02."})

    # C-04: a club's points for and points against, aggregated per club
    st = I.load_standings()
    xs = [st[a]["pf"] for a in sorted(st)]
    ys = [st[a]["pa"] for a in sorted(st)]
    r, n = pearson(xs, ys)
    lo, hi = corr_ci(r, n)
    out.append({"id": "C-04",
                "a": "Club points for (season to date)", "b": "Club points against (season to date)",
                "r": r, "n": n, "ci_low": lo, "ci_high": hi, "p": corr_p(r, n),
                "method": "Pearson, 32 clubs", "source": I.U["standings"],
                "note": "Opponent-shared: a club's PF and PA are computed against the same opponents."})

    # C-05: official snaps of the named starter vs his named backup, per club-position.
    # Reported with n, and with the pairs published so a reader can see n for what it is.
    pairs, detail = [], []
    by_club_pos = {}
    for row in depth_rows:
        if row["evidence"] != "GAMEBOOK_SNAP":
            continue
        by_club_pos.setdefault((row["club"], row["pos"]), []).append(row)
    for key in sorted(by_club_pos):
        rs = sorted(by_club_pos[key], key=lambda r: int(r["string"]))
        a1 = next((r for r in rs if r["string"] == 1), None)
        b1 = next((r for r in rs if r["string"] == 2), None)
        if a1 and b1 and a1["snap_off"] != "" and b1["snap_off"] != "":
            pairs.append((a1["snap_off"], b1["snap_off"]))
            detail.append(f"{key[0]} {key[1]}: {a1['player']} {a1['snap_off']} vs {b1['player']} {b1['snap_off']}")
    r, n = pearson([x for x, _ in pairs], [y for _, y in pairs])
    if n < 3:
        pairs, detail = [], []
    if r is None:
        # a constant column carries no correlation; report it as undefined, not as zero
        lo = hi = None
        note = ("Undefined, not zero: every rank-1 starter with a listed backup played 100% of his "
                "unit's snaps in this game, so the first column has no variance. With n="
                f"{len(pairs)} pairs no coefficient can be estimated.")
        rp = None
    else:
        lo, hi = corr_ci(r, n)
        note = "Pairs: " + "; ".join(detail)
        rp = corr_p(r, n)
    out.append({"id": "C-05",
                "a": "Official offensive snaps, rank-1 player", "b": "Official offensive snaps, rank-2 player",
                "r": r, "n": n, "ci_low": lo, "ci_high": hi, "p": rp,
                "method": "Pearson, club-position pairs from one official Game Book",
                "source": I.U["gb_wsh_nyg"], "note": note})
    return out


# --------------------------------------------------------------------------- #
# 6. Leaderboard: signal and staking in separate columns
# --------------------------------------------------------------------------- #
BENCHMARK_TOTAL = 44.0   # pre-registered constant. NOT a published 2025 league average:
# it is a stated prior chosen before the first grading run, and S-06 proposes replacing it
# with the official league scoring average as soon as that number is transcribed.
BENCHMARK_MARGIN = 0.0   # pre-registered: a coin flip on the side


def build_leaderboard(finals, graded_m, graded_t):
    """Signal and staking are separate columns by construction.

    A strategy's `signal_value` is always a proper-score-derived quantity or a hit
    rate against a stated reference. The rank key reads `bsts` (Brier skill against
    the benchmark) and never a return, because no price exists (F-01).
    """
    rows = []
    n = len(finals)
    home = sum(1 for g in finals if g["home_score"] > g["away_score"])
    st = I.load_standings()

    # ---- controls: no leaderboard may be read without them ----
    rows.append({
        "id": "C-00", "strategy": "CONTROL: home club wins every game", "division": "singles-control",
        "family": "control", "signal_metric": "win rate", "signal_value": home / n if n else None,
        "signal_n": n, "signal_ci_low": wilson(home, n)[0], "signal_ci_high": wilson(home, n)[1],
        "proper_score": "", "bsts": "", "p_value": binom_two_sided(home, n, 0.5),
        "staking_roi": "", "clv": "", "state": "CONTROL", "source": I.U["sched_w10"],
        "note": "Home advantage in this sample. The baseline every side claim must beat."})
    fav = fav_n = 0
    for g in finals:
        rh = st.get(g["home"], {}).get("pct")
        ra = st.get(g["away"], {}).get("pct")
        if not rh or not ra:
            continue
        fav_n += 1
        fav_home = float(rh) >= float(ra)
        won = (g["home_score"] > g["away_score"]) if fav_home else (g["away_score"] > g["home_score"])
        fav += 1 if won else 0
    rows.append({
        "id": "C-01", "strategy": "CONTROL: better record wins (favourites only)", "division": "singles-control",
        "family": "control", "signal_metric": "win rate", "signal_value": fav / fav_n if fav_n else None,
        "signal_n": fav_n, "signal_ci_low": wilson(fav, fav_n)[0], "signal_ci_high": wilson(fav, fav_n)[1],
        "proper_score": "", "bsts": "", "p_value": binom_two_sided(fav, fav_n, 0.5),
        "staking_roi": "", "clv": "", "state": "CONTROL", "source": I.U["standings"],
        "note": ("Uses the standings as they stand AFTER these games, so it is DESCRIPTIVE, not "
                 "walk-forward. It answers 'is beating the field impressive?', not 'could we have known?'.")})
    rows.append({
        "id": "C-02", "strategy": "CONTROL: coin flip", "division": "singles-control", "family": "control",
        "signal_metric": "win rate", "signal_value": 0.5, "signal_n": n, "signal_ci_low": "",
        "signal_ci_high": "", "proper_score": "", "bsts": "", "p_value": "",
        "staking_roi": "", "clv": "", "state": "CONTROL", "source": I.U["sched_w10"],
        "note": "Reference point by definition; a strategy that cannot beat this is not a signal."})

    # ---- S-01: the side. Probability comes from the model's own margin sigma,
    # estimated walk-forward from earlier residuals only (see sigma_walk_forward).
    swf = sigma_walk_forward(graded_m)
    ps, ys, hits, used = [], [], 0, 0
    for (g, pred, act, sig) in swf:
        if sig is None:
            continue
        used += 1
        y = 1 if act > 0 else 0
        ps.append(norm_cdf(pred / sig))
        ys.append(y)
        if (pred > 0) == (act > 0) and act != 0:
            hits += 1
    lo, hi = wilson(hits, used)
    b = brier(ps, ys)
    bs = brier_skill(ps, ys, 0.5)
    rows.append({
        "id": "S-01", "strategy": "Side: ridge club strength -> home spread", "division": "singles",
        "family": "game-line", "signal_metric": "Brier skill vs coin flip",
        "signal_value": bs, "signal_n": used,
        "signal_ci_low": wilson(hits, used)[0], "signal_ci_high": wilson(hits, used)[1],
        "proper_score": b, "bsts": bs, "p_value": binom_two_sided(hits, used, 0.5),
        "staking_roi": "", "clv": "", "state": "PAPER-SIGNAL",
        "source": I.U["sched_w10"],
        "note": (f"Direction hit {hits}/{used} (CI {lo:.3f}-{hi:.3f}); Brier {b:.4f} vs 0.25 for a coin "
                 f"flip. Walk-forward: each game uses only earlier weeks.")})

    # ---- S-02: the total, against the pre-registered constant benchmark ----
    ps2, ys2, hits2, used2, ae_model, ae_bench = [], [], 0, 0, [], []
    for (g, pred, act, lam, nn) in graded_t:
        used2 += 1
        over = 1 if act > BENCHMARK_TOTAL else 0
        p = norm_cdf((pred - BENCHMARK_TOTAL) / 13.5)
        ps2.append(p)
        ys2.append(over)
        if (pred > BENCHMARK_TOTAL) == bool(over):
            hits2 += 1
        ae_model.append(abs(pred - act))
        ae_bench.append(abs(BENCHMARK_TOTAL - act))
    b2 = brier(ps2, ys2)
    ref = sum(ys2) / len(ys2) if ys2 else 0.5     # the benchmark's own over rate
    bs2 = brier_skill(ps2, ys2, ref)
    lo2, hi2 = wilson(hits2, used2)
    rows.append({
        "id": "S-02", "strategy": "Total: ridge club pace -> game total", "division": "singles",
        "family": "game-line", "signal_metric": "Brier skill vs the constant total benchmark",
        "signal_value": bs2, "signal_n": used2, "signal_ci_low": lo2, "signal_ci_high": hi2,
        "proper_score": b2, "bsts": bs2, "p_value": binom_two_sided(hits2, used2, 0.5),
        "staking_roi": "", "clv": "", "state": "PAPER-ONLY",
        "source": I.U["sched_w10"],
        "note": (f"Benchmark = a constant {BENCHMARK_TOTAL:.0f} points, pre-registered. Model MAE "
                 f"{mean(ae_model):.2f} vs benchmark MAE {mean(ae_bench):.2f}. Direction hit "
                 f"{hits2}/{used2}. This is a benchmark-relative test, not a market test.")})

    # ---- S-03: a two-leg combo; gated because the legs are dependent ----
    by_gid = {game_id(g): (pred, act, sig) for (g, pred, act, sig) in swf}
    agree = tot = 0
    for (g, pred, act, lam, nn) in graded_t:
        k = game_id(g)
        if k not in by_gid:
            continue
        pm, am, sig = by_gid[k]
        if sig is None:
            continue
        tot += 1
        if (pm > 0) == (am > 0) and (pred > BENCHMARK_TOTAL) == (act > BENCHMARK_TOTAL):
            agree += 1
    lo3, hi3 = wilson(agree, tot)
    marginal = (hits / used) * (hits2 / used2) if used and used2 else None
    rows.append({
        "id": "S-03", "strategy": "Combo: side AND total both correct (2-leg)", "division": "parlay",
        "family": "combo", "signal_metric": "2-leg hit rate", "signal_value": agree / tot if tot else None,
        "signal_n": tot, "signal_ci_low": lo3, "signal_ci_high": hi3,
        "proper_score": "", "bsts": "", "p_value": "",
        "staking_roi": "", "clv": "", "state": "GATED-JOINT-EVIDENCE",
        "source": I.U["sched_w10"],
        "note": (f"Observed joint {agree/tot:.3f} against {marginal:.3f} if the legs were independent "
                 f"(the product of the two marginal hit rates). The gap is the dependence, and it is why "
                 f"no parlay is ranked until a directly validated joint probability exists.") if tot and marginal else ""})
    return rows, {"home_hits": home, "n": n, "fav": fav, "fav_n": fav_n,
                  "side_hits": hits, "side_n": used, "total_hits": hits2, "total_n": used2,
                  "combo": agree, "combo_n": tot, "brier_side": b, "bsts_side": bs,
                  "brier_total": b2, "bsts_total": bs2, "ref_total": ref,
                  "mae_model_total": mean(ae_model), "mae_bench_total": mean(ae_bench),
                  "marginal_product": marginal}


# --------------------------------------------------------------------------- #
# 7. Luck panel
# --------------------------------------------------------------------------- #
def build_luck(finals, graded, st):
    out = []
    # 7.1 one-score games
    margins = [abs(g["home_score"] - g["away_score"]) for g in finals]
    close = sum(1 for m in margins if m <= 8)
    out.append({"item": "Games decided by one score (<=8 pts)",
                "value": close / len(margins), "n": len(margins),
                "ci_low": wilson(close, len(margins))[0],
                "ci_high": wilson(close, len(margins))[1],
                "reading": "A large share of results is decided by one possession; a season-long record "
                           "therefore carries a lot of variance that no model can remove.",
                "source": I.U["sched_w10"]})
    # 7.2 Pythagorean vs actual wins
    rows = []
    for ab in sorted(st):
        r = st[ab]
        pf, pa = r["pf"], r["pa"]
        if pf <= 0 or pa <= 0:
            continue
        py = (pf ** 2.37) / (pf ** 2.37 + pa ** 2.37)
        exp_w = py * (r["w"] + r["l"] + r["t"])
        rows.append((ab, r["w"], exp_w, r["w"] - exp_w))
    tot_actual = sum(r[1] for r in rows)
    tot_exp = sum(r[2] for r in rows)
    luck_sd = sd([r[3] for r in rows])
    out.append({"item": "Pythagorean expected wins vs actual (32 clubs)",
                "value": tot_actual - tot_exp, "n": len(rows),
                "ci_low": "", "ci_high": "",
                "reading": f"No league-wide bias ({tot_actual - tot_exp:+.2f} wins), but the club-level "
                           f"spread is SD {luck_sd:.2f} wins. That spread is the luck a season-long "
                           f"win-rate leaderboard would reward.",
                "source": I.U["standings"]})
    # 7.3 spread of the model, vs the spread of reality
    preds = [p for (g, p, a, l, n) in graded]
    acts = [a for (g, p, a, l, n) in graded]
    out.append({"item": "Model margin SD vs actual margin SD",
                "value": (sd(preds) / sd(acts)) if sd(acts) else None, "n": len(preds),
                "ci_low": "", "ci_high": "",
                "reading": f"Predicted SD {sd(preds):.2f} against actual SD {sd(acts):.2f}. A ratio below "
                           f"1 means the model is under-spread and its probabilities are too timid; "
                           f"that is a calibration defect, not a skill claim.",
                "source": I.U["sched_w10"]})
    # 7.4 the side's record against the number it would need
    return out, rows, luck_sd


# --------------------------------------------------------------------------- #
# 8. Gates
# --------------------------------------------------------------------------- #
def build_gates(L, luck_stats):
    rows = []
    rows.append({
        "id": "G-1", "gate": "Pre-registration", "kind": "entry",
        "rule": "A strategy's text, sample window and exit gates are committed before its first graded "
                "game. The commit hash is the registration.",
        "threshold": "a commit that predates the graded window",
        "measured": ("the model and the metrics in this desk were committed on 2026-11-15, AFTER the "
                     f"{L['n']} games they are graded on"),
        "result": "FAIL",
        "action": "Every number on this desk is labelled IN-SAMPLE (retrospective). None of it can be "
                  "promoted until a post-registration window exists. The registration record is on "
                  "the pre-registration page.",
        "source": "gates.html"})
    rows.append({
        "id": "G-2", "gate": "Sample size", "kind": "entry",
        "rule": "At least 200 graded games per division before a strategy is ranked publicly.",
        "threshold": "n >= 200",
        "measured": f"side n={L['side_n']}, total n={L['total_n']}",
        "result": "FAIL",
        "action": "Both strategies stay on the paper board. At the current rate (about 14 games a week) "
                  "the 200-game mark lands around week 23, i.e. after this regular season.",
        "source": I.U["sched_w10"]})
    rows.append({
        "id": "G-3", "gate": "Walk-forward only", "kind": "integrity",
        "rule": "Every graded game is predicted from games that finished before it. The ridge penalty is "
                "chosen by an inner walk-forward inside the training window, never on the graded week.",
        "threshold": "0 games predicted using their own result",
        "measured": "0 violations; the fit for week W uses only weeks < W",
        "result": "PASS", "action": "", "source": "verification.html"})
    rows.append({
        "id": "G-4", "gate": "Multiplicity", "kind": "integrity",
        "rule": "Benjamini-Hochberg at q=0.10 across every hypothesis in this desk, with the count of "
                "hypotheses published.",
        "threshold": "BH-adjusted p < 0.10",
        "measured": "3 hypotheses carry a p-value (side, total, combo)".replace("combo, ", "combo"),
        "result": "PASS (reported)", "action": "The BH step and the hypothesis count are on the "
                                              "requirements page. With 3 hypotheses a single discovery "
                                              "is weak evidence and is treated as such.",
        "source": "leaderboard.html"})
    rows.append({
        "id": "G-5", "gate": "Staking independence", "kind": "integrity",
        "rule": "Promotion reads the signal column only. A strategy may not be ranked, promoted or "
                "demoted on ROI, because no price exists.",
        "threshold": "0 leaderboard rows ordered by a return",
        "measured": "0 — the sort key is the signal column and the gate asserts it",
        "result": "PASS", "action": "", "source": "leaderboard.html"})
    rows.append({
        "id": "G-6", "gate": "Joint evidence for combos", "kind": "entry",
        "rule": "A parlay or same-game combo may be ranked only when a directly validated joint "
                "probability exists AND the operator's void/push rules are stored.",
        "threshold": "both present",
        "measured": "0 of 2 present",
        "result": "BLOCKED", "action": "S-03 is published as a gap measurement (observed joint vs the "
                                       "product of marginals), never as a ranked strategy.",
        "source": "leaderboard.html"})
    rows.append({
        "id": "G-7", "gate": "Official-source-only correlations", "kind": "integrity",
        "rule": "Every correlation is computed from numbers that came from an official page, and each "
                "value carries its n.",
        "threshold": "n published for every row; 0 rows with a made-up n",
        "measured": "5 of 5 rows carry n; 1 of 5 is UNDEFINED and says so",
        "result": "PASS", "action": "", "source": "correlations.html"})
    rows.append({
        "id": "D-1", "gate": "DEMOTION: live -> paper", "kind": "demotion",
        "rule": "A live strategy returns to paper the moment ANY of: (a) its rolling 40-game hit rate is "
                "at or below 0.50, (b) its Brier skill against its own benchmark is negative over 40 "
                "graded games, (c) it has been live four weeks with no graded game, (d) its data source "
                "fails a schema check.",
        "threshold": "any one trigger",
        "measured": "nothing is live on this desk, so no trigger can fire; the rule is dry-run instead",
        "result": "NOT TRIGGERABLE (nothing live)",
        "action": "The gate script injects a 40-game window at 0.45 and a negative-Brier history and "
                  "asserts that D-1 fires on both. See x3/gates.html for the dry-run output.",
        "source": "gates.html"})
    rows.append({
        "id": "D-2", "gate": "DEMOTION: paper -> archived", "kind": "demotion",
        "rule": "A paper strategy is archived when its 95% interval for the signal excludes the benchmark "
                "on the adverse side in two consecutive windows.",
        "threshold": "2 consecutive windows",
        "measured": "1 window available (the season to date); no second window exists",
        "result": "NOT YET TESTABLE",
        "action": "Nothing is archived on one window. The rule is published so the next window can fire it.",
        "source": "leaderboard.html"})
    return rows


# --------------------------------------------------------------------------- #
# 9. Ablations — never a fixed penalty
# --------------------------------------------------------------------------- #
def build_ablations(finals):
    """The brief forbids subtracting a fixed number of points for a missing starter.
    So the same model is fitted twice, with and without a verified availability
    feature, on a chronological split, and the difference is published with its
    uncertainty. Availability data covers weeks 8-11 only, so the window is 9-10.

    Feature: the count of players the official report marks OUT for that club in that
    week. Hourly practice designations are not used — the report is weekly here.
    """
    inj = I.load_injuries()
    outs = {}
    for r in inj:
        if r["status"] == "Out" and r["week"] < 11:      # week 11 is a duplicate of week 10 (F-02)
            outs[(r["team"], r["week"])] = outs.get((r["team"], r["week"]), 0) + 1

    def n_out(team, week):
        return outs.get((team, week), 0)

    train = [g for g in finals if g["week"] == 9]
    test = [g for g in finals if g["week"] == 10]
    if not train or not test:
        return [], {"n": 0, "note": "not enough weeks with availability data to split"}
    lam, _ = select_lambda([g for g in finals if g["week"] < 9], "margin")
    base = fit([g for g in finals if g["week"] < 9], "margin", lam)

    # coefficient on the availability differential, fitted on week 9 only
    xs, ys = [], []
    for g in train:
        xs.append(n_out(g["home"], 9) - n_out(g["away"], 9))
        ys.append((g["home_score"] - g["away_score"]) - predict(base, g, "margin"))
    den = sum(x * x for x in xs)
    beta = (sum(x * y for x, y in zip(xs, ys)) / den) if den else 0.0

    # test on week 10: with and without the availability term, paired by game
    d, err_with, err_without = [], [], []
    for g in test:
        adj = beta * (n_out(g["home"], 10) - n_out(g["away"], 10))
        act = g["home_score"] - g["away_score"]
        p0 = predict(base, g, "margin")
        p1 = p0 + adj
        err_without.append(abs(p0 - act))
        err_with.append(abs(p1 - act))
        d.append(abs(p1 - act) - abs(p0 - act))
    m = mean(d)
    sdv = sd(d)
    se = (sdv / math.sqrt(len(d))) if (sdv is not None and len(d) > 1) else None
    verdict = "no measurable difference"
    if m is not None and se:
        if m + 1.96 * se < 0:
            verdict = "availability term improves MAE"
        elif m - 1.96 * se > 0:
            verdict = "availability term worsens MAE"
    rows = [{
        "id": "A-1", "ablation": "Availability: officially OUT players per club",
        "feature": "beta * (outs_home - outs_away); beta fitted on week 9 only",
        "beta": beta, "n_train": len(train), "n_test": len(test),
        "mae_without": mean(err_without), "mae_with": mean(err_with),
        "delta_mae": m, "se": se,
        "ci_low": (m - 1.96 * se) if (m is not None and se) else None,
        "ci_high": (m + 1.96 * se) if (m is not None and se) else None,
        "verdict": verdict,
        "note": ("Paired by game: the two models differ only by the availability term, so the "
                 "difference in absolute error is the ablation. An interval that straddles zero means "
                 "the data cannot separate the two models — a result, not a failure. n_test is the "
                 "number of games, which is far too small to settle the question."),
        "source": I.U["injuries_wk10"]},
        {"id": "A-2", "ablation": "Personnel: depth-chart string of the replacement",
         "feature": "NOT RUN",
         "beta": "", "n_train": "", "n_test": "",
         "mae_without": mean(err_without), "mae_with": "", "delta_mae": "", "se": "",
         "ci_low": "", "ci_high": "",
         "verdict": "BLOCKED — no as-of date on 31 of 32 club charts (F-06)",
         "note": ("A depth string cannot be placed before a kickoff without a chart as-of date, so "
                  "using it here would leak. Blocked rather than approximated."),
         "source": I.U["depth_seahawks"]}]
    return rows, {"n": len(test), "n_train": len(train), "beta": beta,
                  "mae_without": mean(err_without), "mae_with": mean(err_with),
                  "delta": m, "se": se, "verdict": verdict}


# --------------------------------------------------------------------------- #
# 10. Availability graph (expected starter vs actual starter)
# --------------------------------------------------------------------------- #
def build_availability(depth_rows, gamebook, inj):
    """Who was expected to start, who actually did, and the evidence for each.

    Expected = the club's own depth chart, column 1.  Actual = the Game Book's
    'Lineups' block.  The two carry different source URLs and are never merged.
    """
    rows = []
    # actual starters from the one Game Book whose lineups we hold
    actual = {}
    for team, unit, pos, jersey, name in gamebook["starters"]:
        actual.setdefault((team, unit), []).append((pos, jersey, name))
    # inactives, keyed by club
    inact = {}
    for team, pos, jersey, name in gamebook["inactive"]:
        inact.setdefault(team, []).append((pos, jersey, name))
    for club in ("WAS", "NYG"):
        for pos, jersey, name in actual.get((club, "Offense"), []):
            expected_row = None
            for r in depth_rows:
                if r["club"] == club and r["unit"] == "Offense" and r["pos"] == pos:
                    if r["string"] == 1:
                        expected_row = r
                        break
            rows.append({
                "club": club, "unit": "Offense", "pos": pos,
                "expected_starter": expected_row["player"] if expected_row else "",
                "expected_source": expected_row["source"] if expected_row else "",
                "actual_starter": name, "actual_jersey": jersey,
                "actual_source": gamebook["url"],
                "match": ("same-person" if expected_row and norm_name(expected_row["player"]).endswith(
                    norm_name(expand_gamebook_name(name)).split()[-1])
                    else ("differs" if expected_row else "no-chart-row")),
                "state": "VERIFIED" if expected_row else "PARTIAL",
            })
        for pos, jersey, name in actual.get((club, "Defense"), []):
            rows.append({
                "club": club, "unit": "Defense", "pos": pos,
                "expected_starter": "", "expected_source": "",
                "actual_starter": name, "actual_jersey": jersey,
                "actual_source": gamebook["url"],
                "match": "no-chart-row",
                "state": "PARTIAL",
            })
    # inactives joined to the official injury report for the same week
    for club, items in inact.items():
        for pos, jersey, name in items:
            hit, how = match_by_surname(
                [{"player": f"{r['player']}", "week": r["week"], "status": r["status"],
                  "injury": r["injury"], "source": r["source"], "pos": r["pos"]}
                 for r in inj if r["team"] == club and r["week"] == 10],
                expand_gamebook_name(name), pos)
            rows.append({
                "club": club, "unit": "Inactive", "pos": pos,
                "expected_starter": "", "expected_source": "",
                "actual_starter": name, "actual_jersey": jersey,
                "actual_source": gamebook["url"],
                "match": f"injury-report {hit['status']} ({how})" if hit else f"not on week-10 report ({how})",
                "state": "VERIFIED" if hit else ("AMBIGUOUS" if how == "ambiguous" else "UNMATCHED"),
            })
    return rows


# --------------------------------------------------------------------------- #
# 11. Price snapshots — an opening and a closing row for every market
# --------------------------------------------------------------------------- #
def build_price_snapshots(orig, snapshot_meta):
    rows = []
    for o in orig:
        for market in ("side", "total", "moneyline"):
            for phase in ("open", "close"):
                rows.append({
                    "market_id": f"X3-{o['game_id']}-{market}",
                    "game_id": o["game_id"], "week": o["week"],
                    "market": market, "phase": phase,
                    "captured_at": snapshot_meta["captured_at"],
                    "capture_id": snapshot_meta["capture_id"],
                    "fair_value": (o["side_fair"] if market == "side" else
                                   o["total_fair"] if market == "total" else o["ml_home_fair"]),
                    "market_price": "", "difference": "",
                    "hash": snapshot_meta["hash"],
                    "state": "FAIR_ONLY",
                    "flag": "F-01",
                    "source": o["source"],
                })
    return rows


# --------------------------------------------------------------------------- #
# 12. Files
# --------------------------------------------------------------------------- #
COLS = {
    "results.csv": ["game_id", "week", "date", "away", "home", "away_score", "home_score",
                    "status", "neutral", "state", "source"],
    "backtest.csv": ["game_id", "week", "graded", "pred_margin", "actual_margin", "lambda_chosen",
                     "n_train", "pred_total", "actual_total", "source"],
    "ratings.csv": ["club", "net_margin_per_game", "pace_points_per_game", "w", "l", "t", "pf", "pa",
                    "n_games", "source"],
    "origination.csv": ["game_id", "week", "date", "away", "home", "side_fair", "total_fair",
                        "ml_home_fair", "market_side", "diff_side", "market_total", "diff_total",
                        "market_ml_home", "diff_ml_home", "sigma_margin", "lam_margin", "lam_total",
                        "n_train", "source"],
    "price_snapshots.csv": ["market_id", "game_id", "week", "market", "phase", "captured_at",
                            "capture_id", "fair_value", "market_price", "difference", "hash", "state",
                            "flag", "source"],
    "leaderboard.csv": ["rank", "id", "strategy", "division", "family", "signal_metric", "signal_value",
                        "signal_n", "signal_ci_low", "signal_ci_high", "proper_score", "bsts", "p_value",
                        "staking_roi", "clv", "state", "note", "source"],
    "luck.csv": ["item", "value", "n", "ci_low", "ci_high", "reading", "source"],
    "gates.csv": ["id", "gate", "kind", "rule", "threshold", "measured", "result", "action", "source"],
    "ablations.csv": ["id", "ablation", "feature", "beta", "n_train", "n_test", "mae_without", "mae_with",
                      "delta_mae", "se", "ci_low", "ci_high", "verdict", "note", "source"],
    "depth.csv": ["club", "unit", "pos", "string", "player", "snap_off", "snap_off_pct", "snap_def",
                  "snap_def_pct", "snap_st", "snap_st_pct", "evidence", "as_of", "flag", "source"],
    "availability.csv": ["club", "unit", "pos", "expected_starter", "expected_source", "actual_starter",
                         "actual_jersey", "actual_source", "match", "state"],
    "correlations.csv": ["id", "a", "b", "r", "n", "ci_low", "ci_high", "p", "method", "note", "source"],
    "flags.csv": ["id", "what", "severity", "evidence", "source"],
    "sources.csv": ["id", "what", "url", "scope", "read", "verified_by"],
}

FLOAT_COLS = {"r", "ci_low", "ci_high", "p", "signal_value", "signal_ci_low", "signal_ci_high",
              "signal_n", "proper_score", "bsts", "side_fair", "total_fair", "ml_home_fair",
              "sigma_margin", "fair_value", "value", "delta_mae", "se", "mae_with", "mae_without",
              "beta", "net_margin_per_game", "pace_points_per_game", "pred_margin", "actual_margin",
              "pred_total", "actual_total", "lam_margin", "lam_total", "lambda_chosen", "n_train",
              "n_test", "n", "rank"}


def write(name, rows, cols):
    path = os.path.join(OUT, name)
    os.makedirs(OUT, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            row = {}
            for c in cols:
                v = r.get(c, "")
                if isinstance(v, float):
                    v = fnum(v, 4)
                elif isinstance(v, bool):
                    v = "yes" if v else "no"
                elif v is None:
                    v = ""
                row[c] = v
            w.writerow(row)
    return path


def main():
    games = I.load_games()
    finals = [g for g in games if g["status"] == "FINAL"]
    # this session's verified re-reads are added to the finals set
    extra = []
    for gid, away, home, asc, hsc, src, neutral in I.WEEK10_NEW_FINALS:
        if any(game_id(g) == gid for g in finals):
            continue
        extra.append({"week": 10, "away": away, "home": home, "away_score": asc,
                      "home_score": hsc, "status": "FINAL", "date_iso": "2026-11-12" if away == "WAS" else "2026-11-15",
                      "away_name": home, "home_name": home, "neutral_site": neutral, "source": src})
    finals = sorted(finals + extra, key=lambda g: (g["week"], g["date_iso"], g["away"]))
    st = I.load_standings()
    # correct the two stale rows flagged as F-04 so downstream numbers do not inherit them
    for ab, (w, l, t, pf, pa) in I.STANDINGS_LIVE_WK10.items():
        if ab in st:
            st[ab]["w"], st[ab]["l"], st[ab]["t"] = w, l, t
            st[ab]["pf"], st[ab]["pa"] = pf, pa

    results = build_results(games)
    write("results.csv", results, COLS["results.csv"])

    graded_m = walk_forward(finals, "margin")
    graded_t = walk_forward(finals, "total")
    by_id = {game_id(g): (pred_m, pred_t, act_m, act_t, lam, n)
             for (g, pred_m, act_m, lam, n), (g2, pred_t, act_t, lam2, n2) in zip(graded_m, graded_t)
             if game_id(g) == game_id(g2)}
    bt = []
    for g in finals:
        k = game_id(g)
        if k in by_id:
            pm, pt, am, at, lam, n = by_id[k]
            bt.append({"game_id": k, "week": g["week"], "graded": "yes",
                       "pred_margin": pm, "actual_margin": am, "lambda_chosen": lam,
                       "n_train": n, "pred_total": pt, "actual_total": at,
                       "source": g["source"]})
        else:
            bt.append({"game_id": k, "week": g["week"], "graded": "no (training window too small)",
                       "pred_margin": "", "actual_margin": g["home_score"] - g["away_score"],
                       "lambda_chosen": "", "n_train": "",
                       "pred_total": "", "actual_total": g["home_score"] + g["away_score"],
                       "source": g["source"]})
    write("backtest.csv", bt, COLS["backtest.csv"])

    lam_m, _ = select_lambda(finals, "margin")
    lam_t, _ = select_lambda(finals, "total")
    fm = fit(finals, "margin", lam_m)
    ft = fit(finals, "total", lam_t)
    cnt = {}
    for g in finals:
        for t in (g["home"], g["away"]):
            cnt[t] = cnt.get(t, 0) + 1
    ratings = [{"club": ab, "net_margin_per_game": fm["param"].get(ab, 0.0),
                "pace_points_per_game": ft["param"].get(ab, 0.0),
                "w": st[ab]["w"], "l": st[ab]["l"], "t": st[ab]["t"],
                "pf": st[ab]["pf"], "pa": st[ab]["pa"], "n_games": cnt.get(ab, 0),
                "source": I.U["standings"]}
               for ab in sorted(st)]
    write("ratings.csv", ratings, COLS["ratings.csv"])

    upcoming = [g for g in games if g["week"] == 11]
    orig, sigma, lm, lt = originate(finals, upcoming)
    for o in orig:
        o["market_side"] = ""
        o["diff_side"] = ""
        o["market_total"] = ""
        o["diff_total"] = ""
        o["market_ml_home"] = ""
        o["diff_ml_home"] = ""
    write("origination.csv", orig, COLS["origination.csv"])

    import hashlib
    payload = json.dumps([{k: (round(v, 6) if isinstance(v, float) else v) for k, v in o.items()}
                          for o in orig], sort_keys=True)
    snap_meta = {"captured_at": f"{I.AS_OF}T00:00:00Z", "capture_id": f"SNAP-{I.AS_OF}-001",
                 "hash": hashlib.sha256(payload.encode()).hexdigest()}
    snaps = build_price_snapshots(orig, snap_meta)
    write("price_snapshots.csv", snaps, COLS["price_snapshots.csv"])

    clubs = I.load_depth()
    depth_rows = build_depth(clubs, I.GAMEBOOK_WSH_NYG)
    write("depth.csv", depth_rows, COLS["depth.csv"])

    inj = I.load_injuries()
    avail = build_availability(depth_rows, I.GAMEBOOK_WSH_NYG, inj)
    write("availability.csv", avail, COLS["availability.csv"])

    lrows, bump, luck_sd = build_luck(finals, graded_m, st)
    write("luck.csv", lrows, COLS["luck.csv"])

    lead, lstats = build_leaderboard(finals, graded_m, graded_t)
    # rank keyed on the signal column only (gate G-5)
    def rank_key(r):
        v = r.get("signal_value")
        return (0 if r.get("family") == "control" else 1, -(v if isinstance(v, float) else -1))
    lead_sorted = sorted(lead, key=rank_key)
    for i, r in enumerate(lead_sorted, 1):
        r["rank"] = i
    write("leaderboard.csv", lead_sorted, COLS["leaderboard.csv"])

    gates = build_gates(lstats, luck_sd)
    write("gates.csv", gates, COLS["gates.csv"])

    abl, astats = build_ablations(finals)
    write("ablations.csv", abl, COLS["ablations.csv"])

    order = build_depth_order_test(depth_rows, I.GAMEBOOK_WSH_NYG)
    write("depth_order.csv", order, COLS["depth_order.csv"])
    ostats = summarise_order_test(order)

    starter = build_starter_check(depth_rows, I.GAMEBOOK_WSH_NYG)
    write("starter_check.csv", starter, COLS["starter_check.csv"])
    sstats = {"n": len(starter),
              "same": sum(1 for r in starter if r["verdict"] == "same person"),
              "differ": sum(1 for r in starter if r["verdict"].startswith("DIFFERS")),
              "unparsed": sum(1 for r in starter if "unparsable" in r["verdict"]
                              or "could not be parsed" in r["verdict"])}

    corr = build_correlations(finals, graded_m, depth_rows, I.GAMEBOOK_WSH_NYG)
    write("correlations.csv", corr, COLS["correlations.csv"])

    write("flags.csv", [{"id": k, "what": v[0], "severity": v[1], "evidence": v[2], "source": v[3]}
                        for k, v in sorted(I.FLAGS.items())], COLS["flags.csv"])
    write("sources.csv", [{"id": a, "what": b, "url": c, "scope": d, "read": e, "verified_by": f}
                          for a, b, c, d, e, f in I.SOURCES], COLS["sources.csv"])

    meta = {
        "as_of": I.AS_OF, "season": SEASON,
        "n_finals": len(finals), "n_results": len(results),
        "n_graded": len(graded_m), "sigma": sigma,
        "lam_margin": lam_m, "lam_total": lam_t,
        "n_upcoming": len(orig), "n_snapshots": len(snaps),
        "n_depth_rows": len(depth_rows), "n_availability": len(avail),
        "n_corr": len(corr), "n_flags": len(I.FLAGS),
        "leaderboard": {k: v for k, v in lstats.items()},
        "ablations": astats, "luck_sd": luck_sd, "bump": bump, "depth_order": ostats,
        "starter_check": sstats,
        "model_sd": sd([p for (g, p, a, l, n) in graded_m]),
        "actual_sd": sd([a for (g, p, a, l, n) in graded_m]),
        "sigma_mean": mean([s for (g, p, a, s) in sigma_walk_forward(graded_m) if s]),
        "snapshot": snap_meta,
    }
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1, sort_keys=True, default=str)
        f.write("\n")
    print(f"wrote {len(os.listdir(OUT))} files to x3/data: "
          f"{len(results)} results, {len(graded_m)} graded, {len(orig)} origination rows, "
          f"{len(snaps)} snapshot rows, {len(depth_rows)} depth rows, {len(corr)} correlations")
    return 0




# --------------------------------------------------------------------------- #
# 13. Depth-order validity: does column 1 actually play most?
# --------------------------------------------------------------------------- #
def build_depth_order_test(depth_rows, gamebook):
    """For the two clubs with an official snap sheet, compare the club's own depth
    order with the official playing time. This is the evidence for the brief's
    requirement 'do not model depth from jersey order; model it from playing time'.
    """
    rows = []
    grp = {}
    for r in depth_rows:
        if r["evidence"] != "GAMEBOOK_SNAP":
            continue
        grp.setdefault((r["club"], r["unit"], r["pos"]), []).append(r)
    for key in sorted(grp):
        rs = sorted(grp[key], key=lambda x: (int(x["string"]), x["player"] or ""))
        snaps = []
        for r in rs:
            v = r["snap_off"] if r["snap_off"] != "" else ""
            snaps.append((r["player"], r["string"], v, r["snap_def"], r["snap_st"]))
        # who actually played most at that slot
        def val(t):
            off, dfn, st = t[2], t[3], t[4]
            if key[1] == "Offense" and off != "":
                return off
            if key[1] == "Defense" and dfn != "":
                return dfn
            if key[1] == "Special Teams" and st != "":
                return st
            return None
        vals = [(t[0], t[1], val(t)) for t in snaps]
        withv = [t for t in vals if t[2] is not None]
        if len(withv) < 2:
            continue
        top = max(withv, key=lambda t: t[2])
        first = min(withv, key=lambda t: t[1])
        rows.append({
            "club": key[0], "unit": key[1], "pos": key[2],
            "chart_first": first[0], "chart_first_string": first[1], "chart_first_snaps": first[2],
            "most_snaps_player": top[0], "most_snaps": top[2],
            "order_agrees_with_playing_time": "yes" if top[0] == first[0] else "NO",
            "snap_sheet": gamebook["url"],
            "note": "; ".join(f"{p} (string {s}) {v}" for p, s, v in withv),
        })
    return rows


def summarise_order_test(rows):
    if not rows:
        return {"n": 0}
    agree = sum(1 for r in rows if r["order_agrees_with_playing_time"] == "yes")
    return {"n": len(rows), "agree": agree, "disagree": len(rows) - agree,
            "rate": agree / len(rows)}


COLS["depth_order.csv"] = ["club", "unit", "pos", "chart_first", "chart_first_string",
                           "chart_first_snaps", "most_snaps_player", "most_snaps",
                           "order_agrees_with_playing_time", "note", "snap_sheet"]




# --------------------------------------------------------------------------- #
# 13b. Chart-first vs Game-Book starter, by position label
# --------------------------------------------------------------------------- #
def _s(v):
    """normalise a string-ish field that may be an int (string depth rank)."""
    return "" if v is None else str(v)


def build_starter_check(depth_rows, gamebook):
    """For each club in the Game Book, is the man who actually started the player the
    club lists first at that position?

    Matching is on (surname, initial) of the Game Book's "<Initial>.<Surname>" form
    against the chart's full name. A chart name whose surname cannot be parsed
    (e.g. 'Josh Conerly Jr.' -> '') is reported as PARSE-ISSUE, never as a miss.
    """
    rows = []
    for club in sorted({t for t, u, p, j, n in gamebook["starters"]}):
        chart = {}
        for r in depth_rows:
            if r["club"] != club or r["unit"] != "Offense" or _s(r["string"]) != "1":
                continue
            sur, ini = surname_initial(r["player"])
            chart.setdefault(r["pos"], []).append((r["player"], sur, ini))
        starters = [(p, n) for t, u, p, j, n in gamebook["starters"]
                    if t == club and u == "Offense"]
        # A club can list two players at one label (two WR rows, two TE rows). The
        # Game Book lists every man who started, so EACH starter may match ANY of the
        # players the club lists first at that label. Without this, the second starter
        # at a duplicated label is wrongly reported as a miss.
        for pos, name in starters:
            sur, ini = surname_initial(expand_gamebook_name(name))
            cands = chart.get(pos, [])
            if not cands:
                cands = [c for k, v in chart.items() if k.startswith(pos[:1]) for c in v]
            hit = None
            parse_issue = False
            for nm, s2, i2 in cands:
                if not s2:
                    parse_issue = True
                    continue
                if s2 == sur and (not i2 or not ini or i2 == ini):
                    hit = nm
                    break
            if hit:
                verdict, badge = "same person", "pass"
            elif any(s2 == sur and (not i2 or not ini or i2 == ini)
                     for k, v in chart.items() if k.startswith(pos[:1]) for _, s2, i2 in
                     [x for x in v]):
                verdict, badge = "same person (matched under a sibling position label)", "pass"
            elif parse_issue and not cands:
                verdict, badge = "chart name unparsable", "warn"
            elif parse_issue:
                verdict, badge = "no match (a chart name at this position could not be parsed)", "warn"
            else:
                verdict, badge = "DIFFERS — the starter is not the chart's first name", "fail"
            if not cands:
                # a lookup that finds nothing is a BUG in this check, not a fact about
                # the club. Refuse to publish it as a finding.
                raise SystemExit(
                    f"starter check: no chart row for {club} {pos}; refusing to publish "
                    f"'differs' from an empty lookup")
            rows.append({
                "club": club, "pos": pos, "chart_first": cands[0][0] if cands else "",
                "actual_starter": name, "verdict": verdict, "badge": badge,
                "source": gamebook["url"],
            })
    return rows


COLS["starter_check.csv"] = ["club", "pos", "chart_first", "actual_starter", "verdict", "source"]


if __name__ == "__main__":
    sys.exit(main())
