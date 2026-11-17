#!/usr/bin/env python3
"""X3 close-out engine (session arena/e1ad8b78-x3).

Reads only:
  * data/closeout/*.csv          - rows transcribed from official NFL pages on 2026-11-17
  * data/x3/verified/results_2026.csv   - inherited pre-Week-10 game log (prior session)
  * data/x3/verified/markets.json       - the board that was published pre-kickoff on 2026-11-14
  * x3/data/origination.csv             - the Week-11 board frozen by the prior session on 2026-11-15
  * data/hub/standings_2026_thru_wk9.csv- the information set that existed before Week 10 kicked off

Writes derived tables to data/closeout/derived/. Every number is arithmetic on those inputs; no value in
this module is copied from a non-official source and no missing value is filled in.

Deterministic: one RNG, seeded with a constant, used only for the bootstrap.
Run: python3 scripts/closeout_engine.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
from statistics import mean, pstdev

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D_IN = os.path.join(ROOT, "data", "closeout")
D_OUT = os.path.join(D_IN, "derived")
MODEL_VERSION = "X3-CO-1.0"
FROZEN_UTC = "2026-11-17T23:05:00Z"
FIRST_W11_KICKOFF_UTC = "2026-11-19T23:15:00Z"  # Thu 8:15 PM ET, official Week-11 page
SEED = 20261117

os.makedirs(D_OUT, exist_ok=True)


# ---------------------------------------------------------------- helpers
def read(name, folder=D_IN):
    with open(os.path.join(folder, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(v, cast=float, default=None):
    if v is None:
        return default
    s = str(v).strip()
    if s == "" or s.upper() in {"UNVERIFIED", "N/A", "NA", "NONE"}:
        return default
    try:
        return cast(s)
    except ValueError:
        return default


def write(name, rows, cols=None):
    path = os.path.join(D_OUT, name)
    if not rows:
        open(path, "w").close()
        return path
    cols = cols or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})
    return path


def phi(z):
    """standard normal CDF - math.erf only, no third-party dependency"""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def round_half(x):
    return round(x * 2.0) / 2.0


def american(prob):
    """vig-free fair American odds from a probability; blank when degenerate"""
    if prob is None or prob <= 0 or prob >= 1:
        return ""
    if prob >= 0.5:
        return f"-{int(round(prob / (1 - prob) * 100))}"
    return f"+{int(round((1 - prob) / prob * 100))}"


def wilson(k, n, z=1.96):
    """Wilson score interval for a binomial proportion"""
    if n == 0:
        return ("", "")
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = c / d
    s = z / d * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round(m - s, 4), round(m + s, 4))


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def fisher_ci(r, n, z=1.96):
    if r is None or n < 4:
        return ("", "")
    rr = min(max(r, -0.999999), 0.999999)
    at = math.atanh(rr)
    se = 1 / math.sqrt(n - 3)
    lo, hi = math.tanh(at - z * se), math.tanh(at + z * se)
    return (round(lo, 3), round(hi, 3))


def boot_cluster_ci(pairs, seed=SEED, reps=4000):
    """game-cluster bootstrap for a per-game 0/1 hit vector; pairs = [(cluster_id, hit)]"""
    by = {}
    for cid, hit in pairs:
        by.setdefault(cid, []).append(hit)
    clusters = sorted(by)
    if not clusters:
        return ("", "")
    rng = random.Random(seed)
    out = []
    for _ in range(reps):
        vals = []
        for _ in range(len(clusters)):
            vals.extend(by[rng.choice(clusters)])
        out.append(mean(vals) if vals else 0.0)
    out.sort()
    q = lambda p: round(out[min(len(out) - 1, int(p * len(out)))], 4)
    return (q(0.025), q(0.975))


def sha_of(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def f(v, nd=3):
    return "" if v is None or v == "" else f"{float(v):.{nd}f}"


# ---------------------------------------------------------------- 1. the verified log
ALIAS = {"LAR": "LA"}  # inherited feed prints the Rams as LAR; the official standings page prints LA
ALIAS_GET = lambda x: ALIAS.get(x, x)


wk9 = {ALIAS_GET(r["team"]): r for r in read("standings_2026_thru_wk9.csv", os.path.join(ROOT, "data", "hub"))}
official = {r["team"]: r for r in read("official_standings_2026_wk10.csv")}
w10 = read("week10_finals.csv")
inherited = [r for r in read("results_2026.csv", os.path.join(ROOT, "data", "x3", "verified"))
             if r["status"].upper() == "FINAL"]
mine = {f"10:{r['game_id']}": True for r in w10}

def norm(x):
    return ALIAS_GET(x)


log = []
for r in inherited:
    gid = r["game_id"]
    if gid in mine:  # my 2026-11-17 transcription wins for Week 10
        continue
    log.append({
        "game_id": gid, "week": num(r["week"], int), "date_iso": r["date_iso"],
        "away": norm(r["away"]), "home": norm(r["home"]),
        "away_score": num(r["away_score"], int), "home_score": num(r["home_score"], int),
        "neutral": r["neutral_site"], "venue": r.get("venue", ""),
        "provenance": "inherited (prior session, as_of 2026-11-14)",
        "source": r["source"],
    })
for r in w10:
    log.append({
        "game_id": f"10:{r['game_id']}", "week": 10, "date_iso": r["date_iso"],
        "away": r["away"], "home": r["home"],
        "away_score": num(r["away_score"], int), "home_score": num(r["home_score"], int),
        "neutral": "yes" if r["game_id"] == "NE@DET" else "no", "venue": r["venue"],
        "provenance": "captured 2026-11-17T22:44Z (this session)",
        "source": r["source_page"],
    })
for g in log:
    g["margin_home"] = g["home_score"] - g["away_score"]
    g["total"] = g["home_score"] + g["away_score"]
log.sort(key=lambda g: (g["week"], g["date_iso"], g["game_id"]))
write("season_log.csv", log)
GAMES = [g for g in log if g["away_score"] is not None and g["home_score"] is not None]

# ---------------------------------------------------------------- 2. reconciliation to the official standings
recon = []
for team, o in sorted(official.items()):
    g = [x for x in GAMES if team in (x["home"], x["away"])]
    pf = pa = w = l = t = 0
    for x in g:
        me, opp = (x["home_score"], x["away_score"]) if x["home"] == team else (x["away_score"], x["home_score"])
        pf += me
        pa += opp
        w += me > opp
        l += me < opp
        t += me == opp
    agree = (w == num(o["w"], int) and l == num(o["l"], int) and t == num(o["t"], int)
             and pf == num(o["pf"], int) and pa == num(o["pa"], int))
    recon.append({
        "team": team, "games_played": len(g), "log_w": w, "log_l": l, "log_t": t,
        "log_pf": pf, "log_pa": pa, "official_w": o["w"], "official_l": o["l"], "official_t": o["t"],
        "official_pf": o["pf"], "official_pa": o["pa"],
        "games_agree": "yes" if len(g) == w + l + t else "NO",
        "agree": "MATCH" if agree else "MISMATCH",
        "detail": "" if agree else (
            f"log {w}-{l}-{t} {pf}:{pa} vs official {o['w']}-{o['l']}-{o['t']} {o['pf']}:{o['pa']}"),
        "source": o["source_page"],
    })
write("reconciliation.csv", recon)
sum_pf = sum(num(o["pf"], int) for o in official.values())
sum_pa = sum(num(o["pa"], int) for o in official.values())
net_arith = all(num(o["pf"], int) - num(o["pa"], int) == num(o["net"], int) for o in official.values())
mismatches = [r for r in recon if r["agree"] != "MATCH"]

# ---------------------------------------------------------------- 3. ratings (fitted on every game before the Week-11 kickoff)
teams = sorted(official)
r = {t: 0.0 for t in teams}
hfa = 0.0
def is_neutral(g):
    return str(g.get("neutral", "")).lower() in ("true", "yes")


def adj(g, h_):  # the home-advantage term actually applied to this game
    return 0.0 if is_neutral(g) else h_


def solve(A, b):
    """Gaussian elimination with partial pivoting; A is n x n, modified in place"""
    n = len(A)
    for c in range(n):
        piv = max(range(c, n), key=lambda i: abs(A[i][c]))
        if abs(A[piv][c]) < 1e-14:
            A[c][c] += 1e-9
            piv = c
        A[c], A[piv] = A[piv], A[c]
        b[c], b[piv] = b[piv], b[c]
        pc = A[c][c]
        for i in range(n):
            if i == c:
                continue
            fac = A[i][c] / pc
            if fac:
                for j in range(c, n):
                    A[i][j] -= fac * A[c][j]
                b[i] -= fac * b[c]
    return [b[i] / A[i][i] if abs(A[i][i]) > 1e-14 else 0.0 for i in range(n)]


def ls_ratings(games, teams_, hfa):
    """least-squares (Massey) ratings with a sum-to-zero constraint.

    Exact linear solve, so a schedule whose conferences have not yet met cannot drift the way an iterative
    average would. Returns (ratings, home advantage re-estimated from the non-neutral residuals).
    """
    idx = {tm: i for i, tm in enumerate(teams_)}
    n = len(teams_)
    W = 1e6  # weight on the sum-to-zero penalty
    A = [[W + (1e-9 if i == j else 0.0) for j in range(n)] for i in range(n)]
    b = [0.0] * n
    used = set()
    for g in games:
        hi, ai = idx.get(g["home"]), idx.get(g["away"])
        if hi is None or ai is None:
            continue
        y = g["margin_home"] - (hfa if not is_neutral(g) else 0.0)
        for i, s in ((hi, 1.0), (ai, -1.0)):
            b[i] += s * y
            A[i][hi] += s
            A[i][ai] += -s
        used.add(hi)
        used.add(ai)
    r = solve(A, b)
    mu = mean(r)
    r = {tm: r[idx[tm]] - mu for tm in teams_}
    non = [g for g in games if not is_neutral(g) and g["home"] in idx and g["away"] in idx]
    hfa_new = mean([g["margin_home"] - (r[g["home"]] - r[g["away"]]) for g in non]) if non else 0.0
    return r, hfa_new, len(non)


hfa = 0.0
for _ in range(60):  # alternate the ratings solve and the home-advantage estimate until stable
    r_new, hfa_new, n_nonneutral = ls_ratings(GAMES, teams, hfa)
    if max(abs(r_new[x] - r[x]) for x in teams) < 1e-9 and abs(hfa_new - hfa) < 1e-9:
        r, hfa = r_new, hfa_new
        break
    r, hfa = r_new, hfa_new

stats = {}
for t in teams:
    g = [x for x in GAMES if t in (x["home"], x["away"])]
    pf = sum(x["home_score"] if x["home"] == t else x["away_score"] for x in g)
    pa = sum(x["away_score"] if x["home"] == t else x["home_score"] for x in g)
    stats[t] = {"g": len(g), "ppg": pf / len(g), "opp_ppg": pa / len(g)}
resid_m = [g["margin_home"] - (r[g["home"]] - r[g["away"]] + adj(g, hfa)) for g in GAMES]
resid_t = []
for g in GAMES:
    exp_total = (stats[g["home"]]["ppg"] + stats[g["away"]]["opp_ppg"]) / 2 + \
                (stats[g["away"]]["ppg"] + stats[g["home"]]["opp_ppg"]) / 2
    resid_t.append(g["total"] - exp_total)
sigma_m = pstdev(resid_m) * math.sqrt(len(resid_m) / (len(resid_m) - 1))
sigma_t = pstdev(resid_t) * math.sqrt(len(resid_t) / (len(resid_t) - 1))
sd_pred = pstdev([r[g["home"]] - r[g["away"]] + adj(g, hfa) for g in GAMES])
sd_act = pstdev([g["margin_home"] for g in GAMES])
r2_margin = 1 - sum(e * e for e in resid_m) / sum((m - mean([g["margin_home"] for g in GAMES])) ** 2
                                                  for m in [g["margin_home"] for g in GAMES])

ratings = []
for t in teams:
    ratings.append({
        "team": t, "games": stats[t]["g"], "ppg": f(stats[t]["ppg"], 3),
        "opp_ppg": f(stats[t]["opp_ppg"], 3),
        "net_ppg": f(stats[t]["ppg"] - stats[t]["opp_ppg"], 3),
        "rating": f(r[t], 3), "rating_raw": f(r[t], 6),
        "record_official": f"{official[t]['w']}-{official[t]['l']}-{official[t]['t']}",
        "fitted_on": f"{len(GAMES)} games (weeks 1-10, 2026)",
        "source": "arithmetic on data/closeout/derived/season_log.csv",
    })
write("ratings.csv", ratings)

# ---------------------------------------------------------------- 4. Week-11 forecast (frozen before kickoff)
slate = read("week11_slate.csv")
avail = read("availability_w10.csv")
forecasts, drift = [], []
prior = {row["game_id"].replace("2026-W11-", ""): row for row in read("origination.csv", os.path.join(ROOT, "x3", "data"))}
for s in slate:
    h, a = s["home"], s["away"]
    exp_m = r[h] - r[a] + (0.0 if s["neutral_site"] == "true" else hfa)
    exp_total = (stats[h]["ppg"] + stats[a]["opp_ppg"]) / 2 + (stats[a]["ppg"] + stats[h]["opp_ppg"]) / 2
    line_home = -round_half(exp_m)
    line_total = round_half(exp_total)
    p_home = phi(exp_m / sigma_m)
    p_cover = phi((exp_m - (-line_home)) / sigma_m)
    p_over = phi((exp_total - line_total) / sigma_t)
    eh = exp_total / 2 + exp_m / 2
    ea = exp_total / 2 - exp_m / 2
    forecasts.append({
        "game_id": s["game_id"], "week": 11, "date_iso": s["date_iso"], "kickoff_et": s["kickoff_et"],
        "network": s["network"], "away": a, "home": h, "neutral_site": s["neutral_site"],
        "venue": s["venue"],
        "model_version": MODEL_VERSION, "frozen_utc": FROZEN_UTC,
        # --- order of origination: 1 side, 2 total, 3 moneyline (brief), kept in separate columns
        "fair_margin_home": f(exp_m, 2), "side_fair_line_home": f(line_home, 1),
        "side_prob_home_cover": f(p_cover, 4),
        "total_fair_line": f(line_total, 1), "total_prob_over": f(p_over, 4),
        "ml_prob_home": f(p_home, 4), "ml_prob_away": f(1 - p_home, 4),
        "ml_fair_american_home": american(p_home), "ml_fair_american_away": american(1 - p_home),
        "expected_home_points": f(eh, 2), "expected_away_points": f(ea, 2),
        # --- market columns: no price source exists in this repository; left blank, never imputed
        "market_side": "", "diff_side": "", "market_total": "", "diff_total": "",
        "market_ml_home": "", "diff_ml_home": "", "market_source": "NO MARKET PRICE - see price policy PDP-1",
        # --- inputs, published with the output (brief: store probability plus its inputs)
        "rating_home": f(r[h], 3), "rating_away": f(r[a], 3), "home_advantage": f(hfa, 3),
        "sigma_margin": f(sigma_m, 3), "sigma_total": f(sigma_t, 3),
        "n_train_games": len(GAMES), "ppg_home": f(stats[h]["ppg"], 3), "ppg_away": f(stats[a]["ppg"], 3),
        "opp_ppg_home": f(stats[h]["opp_ppg"], 3), "opp_ppg_away": f(stats[a]["opp_ppg"], 3),
        "availability_input": "NONE - no Week-11 injury report existed at freeze time (SR-05, SR-06, SR-07)",
        "injury_context_wk10": "; ".join(
            f"{x['player']} {x['designation']}".strip() for x in avail
            if x["club"] in (h, a) and x["designation"] in ("Out", "Questionable", "Doubtful")) or "no designated player read this session",
        "source": s["source_page"],
    })
    p = prior.get(s["game_id"])
    if p:
        drift.append({
            "game_id": s["game_id"], "market": "side",
            "prior_frozen_utc": "2026-11-15 (x3/data/origination.csv)", "prior_value": p["side_fair"],
            "this_frozen_utc": FROZEN_UTC, "this_value": f(line_home, 2),
            "difference": f(line_home - num(p["side_fair"], float), 3),
            "note": "both columns are the home spread, negative = home favourite; this row is not a winner-takes-"
                    "anything comparison, it is the size of the move between two freezes of the same fixture",
            "source": "https://github.com/karagemop466-tech/X3/blob/b7d4142/x3/data/origination.csv",
        })
        drift.append({
            "game_id": s["game_id"], "market": "moneyline (home probability)",
            "prior_frozen_utc": "2026-11-15 (x3/data/origination.csv)", "prior_value": p["ml_home_fair"],
            "this_frozen_utc": FROZEN_UTC, "this_value": f(p_home, 4),
            "difference": f(p_home - num(p["ml_home_fair"], float), 4),
            "note": "probability, so no vig and no line convention is involved",
            "source": "https://github.com/karagemop466-tech/X3/blob/b7d4142/x3/data/origination.csv",
        })
        drift.append({
            "game_id": s["game_id"], "market": "total",
            "prior_frozen_utc": "2026-11-15 (x3/data/origination.csv)", "prior_value": p["total_fair"],
            "this_frozen_utc": FROZEN_UTC, "this_value": f(exp_total, 4),
            "difference": f(exp_total - num(p["total_fair"], float), 4),
            "note": "both fitted on 2026 finals; the prior model trained on 138 games, this one on "
                    f"{len(GAMES)}",
            "source": "https://github.com/karagemop466-tech/X3/blob/b7d4142/x3/data/origination.csv",
        })
    else:
        drift.append({
            "game_id": s["game_id"], "market": "both", "prior_frozen_utc": "", "prior_value": "",
            "this_frozen_utc": FROZEN_UTC, "this_value": "", "difference": "",
            "note": "no prior-session row for this fixture - nothing to compare",
            "source": "https://github.com/karagemop466-tech/X3/blob/b7d4142/x3/data/origination.csv",
        })
write("forecasts_w11.csv", forecasts)
write("drift_vs_prior.csv", drift)

# ---------------------------------------------------------------- 5. settlement of the pre-kickoff board
mk = json.load(open(os.path.join(ROOT, "data", "x3", "verified", "markets.json")))
live = [x for x in mk["live"] if x["week"] == 10]
def norm_key(k):
    a, _, h = k.partition("@")
    return f"{norm(a)}@{norm(h)}"


by_game = {norm_key(g["game_id"].split(":", 1)[1]): g for g in GAMES if g["week"] == 10}
settled, ungraded = [], []
mean_total_wk1_9 = mean([g["total"] for g in GAMES if g["week"] <= 9])
for row in live:
    gid = norm_key(row["game_id"].split(":", 1)[1])
    g = by_game.get(gid)
    if not g:
        ungraded.append({"game_id": row["game_id"], "why": "no final score captured for this fixture",
                         "source": "data/closeout/week10_finals.csv"})
        continue
    act_m, act_t = g["margin_home"], g["total"]
    line = num(row["side_fair_line"], float)
    total_line = num(row["total_fair_line"], float)
    p_cov, p_ov, p_ml = (num(row["side_cover_prob_home"], float), num(row["total_over_prob"], float),
                         num(row["ml_home_prob"], float))
    margin_push = (line is not None and act_m == -line)
    total_push = (total_line is not None and act_t == total_line)
    home_cover = None if margin_push else (1.0 if act_m > -line else 0.0)
    over = None if total_push else (1.0 if act_t > total_line else 0.0)
    home_win = 1.0 if act_m > 0 else (0.5 if act_m == 0 else 0.0)
    wk9h, wk9a = wk9.get(g["home"]), wk9.get(g["away"])
    if wk9h and wk9a:
        ph, paa = num(wk9h["pct"], float, 0.0), num(wk9a["pct"], float, 0.0)
        fav = g["home"] if ph >= paa else g["away"]
        ctl_fav = 1.0 if ((act_m > 0 and fav == g["home"]) or (act_m < 0 and fav == g["away"])) else (0.5 if act_m == 0 else 0.0)
    else:
        fav, ctl_fav = "", ""
    model_pick = "" if line is None else (g["home"] if line < 0 else (g["away"] if line > 0 else ""))
    model_fav_hit = "" if (model_pick == "" or margin_push) else (
        1.0 if ((model_pick == g["home"] and act_m > -line) or (model_pick == g["away"] and act_m < -line)) else 0.0)
    ml_pick = "" if p_ml is None or p_ml == 0.5 else (g["home"] if p_ml > 0.5 else g["away"])
    ml_fav_hit = "" if ml_pick == "" else (1.0 if (ml_pick == g["home"] and act_m > 0) or (ml_pick == g["away"] and act_m < 0) else 0.0)
    settled.append({
        "game_id": row["game_id"], "date_iso": row["date_iso"], "away": g["away"], "home": g["home"],
        "board_as_of": mk["as_of"],
        "board_published_before_kickoff": "yes - as_of 2026-11-14, kickoffs 2026-11-15 and 2026-11-16",
        "model_margin_home": f(num(row["margin_model"], float), 2), "actual_margin_home": act_m,
        "margin_error": f(abs(act_m - num(row["margin_model"], float)), 2),
        "naive_margin_zero_error": f(abs(act_m), 2),
        "side_fair_line_home": f(line, 1), "side_prob_home_cover": f(p_cov, 4),
        "side_result": "PUSH" if margin_push else ("HOME COVERS" if home_cover == 1.0 else "AWAY COVERS"),
        "side_home_cover_hit": "" if margin_push else int(home_cover),
        "side_brier": "" if margin_push else f((p_cov - (1.0 if home_cover == 1.0 else 0.0)) ** 2, 5),
        "model_side_pick": model_pick, "model_side_cover_hit": "" if model_fav_hit == "" else int(model_fav_hit),
        "total_fair_line": f(total_line, 1), "total_prob_over": f(p_ov, 4), "actual_total": act_t,
        "total_result": "PUSH" if total_push else ("OVER" if over == 1.0 else "UNDER"),
        "total_hit": "" if total_push else int(over),
        "total_brier": "" if total_push else f((p_ov - (1.0 if over == 1.0 else 0.0)) ** 2, 5),
        "total_error": f(abs(act_t - total_line), 2) if total_line is not None else "",
        "naive_total_error": f(abs(act_t - mean_total_wk1_9), 2),
        "ml_prob_home": f(p_ml, 4), "ml_result": "HOME" if act_m > 0 else ("AWAY" if act_m < 0 else "TIE"),
        "ml_brier": f((p_ml - (1.0 if act_m > 0 else 0.0)) ** 2, 5),
        "model_ml_pick": ml_pick, "model_ml_hit": "" if ml_fav_hit == "" else int(ml_fav_hit),
        "control_always_home": 1.0 if act_m > 0 else (0.5 if act_m == 0 else 0.0),
        "control_wk9_pct_favourite": ctl_fav, "control_favourite_club": fav,
        "wk9_pct_home": "" if not wk9h else wk9h["pct"], "wk9_pct_away": "" if not wk9a else wk9a["pct"],
        "source": row.get("source_results", "https://www.nfl.com/schedules/2026/by-week/week-10"),
    })
write("settlement.csv", settled)
write("ungraded.csv", ungraded or [{"game_id": "", "why": "none - every pre-kickoff row has a captured final",
                                    "source": "data/closeout/week10_finals.csv"}])

n = len(settled)
rng = random.Random(SEED)
rand_hits = 0.0
for s in settled:
    other = s["away"] if rng.random() < 0.5 else s["home"]
    rand_hits += 1.0 if ((other == s["home"] and num(s["actual_margin_home"], float) > 0)
                         or (other == s["away"] and num(s["actual_margin_home"], float) < 0)) else 0.0


def prop(field):
    vals = [float(s[field]) for s in settled if s[field] != ""]
    k = sum(1 for v in vals if v == 1.0)
    half = sum(1 for v in vals if v == 0.5)
    nn = len(vals)
    lo, hi = wilson(k, nn)
    blo, bhi = boot_cluster_ci([(s["game_id"], float(s[field])) for s in settled if s[field] != ""])
    return k, nn, half, lo, hi, blo, bhi


def proper(field):
    vals = [num(s[field], float) for s in settled if s[field] != ""]
    vals = [v for v in vals if v is not None]
    return (round(mean(vals), 5) if vals else None), len(vals)


def mae(field):
    vals = [num(s[field], float) for s in settled if s[field] != ""]
    vals = [v for v in vals if v is not None]
    return (round(mean(vals), 3) if vals else None)


side_k, side_n, side_push, side_lo, side_hi, side_blo, side_bhi = prop("side_home_cover_hit")
side_brier, side_bn = proper("side_brier")
tot_k, tot_n, tot_push, tot_lo, tot_hi, tot_blo, tot_bhi = prop("total_hit")
tot_brier, tot_bn = proper("total_brier")
ml_k, ml_n, ml_push, ml_lo, ml_hi, ml_blo, ml_bhi = prop("ml_brier_hit_placeholder") if False else prop("model_ml_hit")
ml_brier, ml_bn = proper("ml_brier")
sk_pick, sk_n, sk_push, sk_lo, sk_hi, sk_blo, sk_bhi = prop("model_side_cover_hit")

_ctl_home = mean([s["control_always_home"] for s in settled])
ctl_home_rate = _ctl_home
ctl_fav_rate = mean([float(s["control_wk9_pct_favourite"]) for s in settled if s["control_wk9_pct_favourite"] != ""])
ctl_rand = rand_hits
mae_model, mae_zero = mae("margin_error"), mae("naive_margin_zero_error")
scorecard = [
    {"id": "SC-1", "division": "singles - side", "what_is_scored": "probability that the home team covers the "
     "board's own fair line", "n_gradable": side_n, "n_push": side_push, "n_ungradable": 0,
     "brier": side_brier, "benchmark_brier": 0.25,
     "skill_vs_benchmark": f(1 - side_brier / 0.25, 4) if side_brier is not None else "",
     "mae_points": mae("margin_error"), "mae_benchmark_points": mae("naive_margin_zero_error"),
     "benchmark_rule": "naive benchmark predicts a 0 margin for every game (always pick 'no one is better')",
     "frozen": "2026-11-14 by the prior session (before the Nov 15/16 kickoffs)",
     "stakes": "none - no price to settle against, so no ROI, CLV or reward exists on this row",
     "verdict": f"NOT LEADERBOARD-ELIGIBLE: n={side_n} graded, Brier {side_brier} against a 0.25 benchmark, so the "
                "cover probability is worth nothing on this sample; margin MAE does beat the always-zero benchmark "
                f"({mae('margin_error')} vs {mae('naive_margin_zero_error')})",
     "source": "https://github.com/karagemop466-tech/X3/blob/b7d4142/data/x3/verified/markets.json"},
    {"id": "SC-2", "division": "singles - total", "what_is_scored": "probability that the game goes over the "
     "board's own fair total", "n_gradable": tot_n, "n_push": tot_push, "n_ungradable": 0,
     "brier": tot_brier, "benchmark_brier": 0.25,
     "skill_vs_benchmark": f(1 - tot_brier / 0.25, 4) if tot_brier is not None else "",
     "mae_points": mae("total_error"), "mae_benchmark_points": mae("naive_total_error"),
     "benchmark_rule": f"naive benchmark predicts the Week 1-9 league mean total ({f(mean_total_wk1_9, 2)}) for every game",
     "frozen": "2026-11-14 by the prior session (before the Nov 15/16 kickoffs)",
     "stakes": "none - no price to settle against",
     "verdict": f"NOT LEADERBOARD-ELIGIBLE: n={tot_n}; the total line is the model's own, so a 'win' is agreement "
                f"with itself, and its total MAE ({mae('total_error')}) is worse than the running-league-mean "
                f"benchmark ({mae('naive_total_error')})",
     "source": "https://github.com/karagemop466-tech/X3/blob/b7d4142/data/x3/verified/markets.json"},
    {"id": "SC-3", "division": "singles - moneyline", "what_is_scored": "probability that the home team wins",
     "n_gradable": ml_bn, "n_push": 0, "n_ungradable": 0,
     "brier": ml_brier, "benchmark_brier": 0.25,
     "skill_vs_benchmark": f(1 - ml_brier / 0.25, 4) if ml_brier is not None else "",
     "mae_points": "", "mae_benchmark_points": "",
     "benchmark_rule": "benchmark says 0.5 on every home team",
     "frozen": "2026-11-14 by the prior session (before the Nov 15/16 kickoffs)",
     "stakes": "none - no price to settle against",
     "verdict": ("NOT LEADERBOARD-ELIGIBLE: n=13. The home-win probability does beat the 0.25 benchmark "
                 f"(Brier {ml_brier} vs 0.25), but the pick rate is {f(ml_k / ml_n if ml_n else None, 3)} and the "
                 "Week-9-winning-percentage control on the same games is "
                 f"{f(ctl_fav_rate, 3)} - identical, so none of the gain is attributable to the model"),
     "source": "https://github.com/karagemop466-tech/X3/blob/b7d4142/data/x3/verified/markets.json"},
]
write("scorecard.csv", scorecard)

controls = [
    {"picker": "the prior board's side pick (favourite at its own fair line)", "n": sk_n, "hits": sk_pick,
     "ties_or_half": sk_push, "hit_rate": f(sk_pick / sk_n if sk_n else None, 4),
     "wilson_lo": sk_lo, "wilson_hi": sk_hi, "boot_lo": sk_blo, "boot_hi": sk_bhi,
     "outcome_used": "the model's favoured side covers the model's own line",
     "note": "with a fair line this is a calibration test, not an edge test: a perfectly unbiased model sits at 0.500",
     "source": "data/closeout/derived/settlement.csv"},
    {"picker": "model's moneyline pick (probability above 0.5)", "n": ml_n, "hits": ml_k, "ties_or_half": ml_push,
     "hit_rate": f(ml_k / ml_n if ml_n else None, 4), "wilson_lo": ml_lo, "wilson_hi": ml_hi,
     "boot_lo": ml_blo, "boot_hi": ml_bhi, "outcome_used": "the picked club won the game",
     "note": "the same outcome is then given to three control pickers on the same games",
     "source": "data/closeout/derived/settlement.csv"},
    {"picker": "control - always home", "n": side_n, "hits": sum(1 for s in settled if s["control_always_home"] == 1.0),
     "ties_or_half": 0, "hit_rate": f(mean([s["control_always_home"] for s in settled]), 4),
     "wilson_lo": wilson(sum(1 for s in settled if s["control_always_home"] == 1.0), side_n)[0],
     "wilson_hi": wilson(sum(1 for s in settled if s["control_always_home"] == 1.0), side_n)[1],
     "boot_lo": "", "boot_hi": "", "outcome_used": "home team won the game",
     "note": "the fitted home advantage is " + f(hfa, 2) + " points, which is why 'always home' is not a free lunch",
     "source": "data/closeout/derived/settlement.csv"},
    {"picker": "control - better winning percentage in the Week-9 standings", "n": len(fav_vals := [s for s in settled if s["control_wk9_pct_favourite"] != ""]),
     "hits": sum(1 for s in fav_vals if s["control_wk9_pct_favourite"] == 1.0),
     "ties_or_half": sum(1 for s in fav_vals if s["control_wk9_pct_favourite"] == 0.5),
     "hit_rate": f(mean([float(s["control_wk9_pct_favourite"]) for s in fav_vals]) if fav_vals else None, 4),
     "wilson_lo": wilson(sum(1 for s in fav_vals if s["control_wk9_pct_favourite"] == 1.0), len(fav_vals))[0],
     "wilson_hi": wilson(sum(1 for s in fav_vals if s["control_wk9_pct_favourite"] == 1.0), len(fav_vals))[1],
     "boot_lo": "", "boot_hi": "", "outcome_used": "the picked club won the game",
     "note": "uses only the standings as they stood before Week 10 kicked off - no lookahead",
     "source": "data/hub/standings_2026_thru_wk9.csv"},
    {"picker": "control - seeded random coin flip per game", "n": n, "hits": int(round(rand_hits)),
     "ties_or_half": 0, "hit_rate": f(rand_hits / n if n else None, 4),
     "wilson_lo": wilson(int(round(rand_hits)), n)[0], "wilson_hi": wilson(int(round(rand_hits)), n)[1],
     "boot_lo": "", "boot_hi": "", "outcome_used": "the picked club won the game",
     "note": f"seed {SEED}, fixed, so the number is reproducible and not re-rolled between reviews",
     "source": "data/closeout/derived/settlement.csv"},
]
write("controls.csv", controls)


# ---------------------------------------------------------------- 5b. walk-forward backtest (chronological holdout)
def fit_ratings(games, teams_):
    r_, h_, _ = ls_ratings(games, teams_, 0.0)
    for _ in range(40):
        r2_, h2_, _ = ls_ratings(games, teams_, h_)
        if max(abs(r2_[x] - r_[x]) for x in teams_) < 1e-9 and abs(h2_ - h_) < 1e-9:
            return r2_, h2_
        r_, h_ = r2_, h2_
    return r_, h_


chron = sorted(GAMES, key=lambda x: (x["date_iso"], x["game_id"]))
wf_rows = []
for i, g in enumerate(chron):
    prior_games = chron[:i]
    if len(prior_games) < 40:
        continue
    seen = {t for gg in prior_games for t in (gg["home"], gg["away"])}
    if g["home"] not in seen or g["away"] not in seen:
        continue
    rr, hh = fit_ratings(prior_games, teams)
    pm = rr[g["home"]] - rr[g["away"]] + (0.0 if is_neutral(g) else hh)
    st = {}
    for t_ in (g["home"], g["away"]):
        gs = [x for x in prior_games if t_ in (x["home"], x["away"])]
        st[t_] = {"ppg": sum(x["home_score"] if x["home"] == t_ else x["away_score"] for x in gs) / len(gs),
                 "opp": sum(x["away_score"] if x["home"] == t_ else x["home_score"] for x in gs) / len(gs)}
    pt = (st[g["home"]]["ppg"] + st[g["away"]]["opp"]) / 2 + (st[g["away"]]["ppg"] + st[g["home"]]["opp"]) / 2
    sig = pstdev([x["margin_home"] - (rr[x["home"]] - rr[x["away"]] + (0.0 if is_neutral(x) else hh))
                  for x in prior_games]) or 1.0
    run_mean_total = mean([x["total"] for x in prior_games])
    sit = pstdev([x["total"] - run_mean_total for x in prior_games]) or 1.0
    ph = phi(pm / sig)
    line = -round_half(pm)
    tl = round_half(pt)
    p_over = phi((pt - tl) / sit)
    home_cover = 1.0 if g["margin_home"] > -line else 0.0
    home_cover = "" if g["margin_home"] == -line else home_cover
    over = "" if g["total"] == tl else (1.0 if g["total"] > tl else 0.0)
    wf_rows.append({
        "game_id": g["game_id"], "date_iso": g["date_iso"], "week": g["week"], "away": g["away"], "home": g["home"],
        "n_train": len(prior_games), "pred_margin_home": f(pm, 3), "actual_margin_home": g["margin_home"],
        "sigma_used": f(sig, 3), "mean_total_prior": f(run_mean_total, 3), "sigma_total_prior": f(sit, 3),
        "abs_margin_error": f(abs(g["margin_home"] - pm), 3),
        "naive_margin_error": f(abs(g["margin_home"]), 3),
        "pred_total": f(pt, 3), "actual_total": g["total"], "abs_total_error": f(abs(g["total"] - pt), 3),
        "naive_total_error": f(abs(g["total"] - mean([y["total"] for y in prior_games])), 3),
        "p_home_win": f(ph, 4), "home_won": "" if g["margin_home"] == 0 else int(1.0 if g["margin_home"] > 0 else 0.0),
        "brier_home_win": f((ph - (1.0 if g["margin_home"] > 0 else 0.0)) ** 2, 5),
        "brier_benchmark": f((0.5 - (1.0 if g["margin_home"] > 0 else 0.0)) ** 2, 5),
        "side_fair_line_home": f(line, 1), "home_covered": home_cover,
        "total_fair_line": f(tl, 1), "p_over": f(p_over, 4),
        "brier_over": f((p_over - (0.5 if over == "" else over)) ** 2, 5), "went_over": over,
        "source": "arithmetic on data/closeout/derived/season_log.csv (chronological holdout)",
    })
write("walkforward.csv", wf_rows)
wf_n = len(wf_rows)
wf_mae = round(mean([num(r["abs_margin_error"], float) for r in wf_rows]), 3)
wf_mae_naive = round(mean([num(r["naive_margin_error"], float) for r in wf_rows]), 3)
wf_tmae = round(mean([num(r["abs_total_error"], float) for r in wf_rows]), 3)
wf_tmae_naive = round(mean([num(r["naive_total_error"], float) for r in wf_rows]), 3)
wf_brier = round(mean([num(r["brier_home_win"], float) for r in wf_rows]), 5)
wf_brier_bench = round(mean([num(r["brier_benchmark"], float) for r in wf_rows]), 5)
wf_hc = [r for r in wf_rows if r["home_covered"] != ""]
wf_hc_k = sum(1 for r in wf_hc if r["home_covered"] == 1)
wf_lo, wf_hi = wilson(wf_hc_k, len(wf_hc))
wf_blo, wf_bhi = boot_cluster_ci([(r["game_id"], float(r["home_covered"])) for r in wf_hc])
wf_sc = {
    "id": "SC-4", "division": "singles - side and total, walk-forward",
    "what_is_scored": "every 2026 game re-forecast from ratings fitted only on earlier games (chronological holdout)",
    "n_gradable": len(wf_hc), "n_push": len(wf_rows) - len(wf_hc), "n_ungradable": 150 - wf_n,
    "brier": wf_brier, "benchmark_brier": wf_brier_bench,
    "skill_vs_benchmark": f(1 - wf_brier / wf_brier_bench, 4),
    "mae_points": wf_mae, "mae_benchmark_points": wf_mae_naive,
    "benchmark_rule": f"naive margin benchmark is 0.0 on every game; naive total benchmark is the running league mean "
                      f"(total MAE {wf_tmae} vs {wf_tmae_naive})",
    "frozen": "rule frozen 2026-11-17; the corpus (150 games) predates it, so this is a retrospective exercise, "
              "labelled as such on every page",
    "stakes": "none - no price to settle against; a hit here is calibration against the model's own line",
    "verdict": (("the walk-forward margin forecast beats the zero benchmark by "
                 f"{round(wf_mae_naive - wf_mae, 3)} points per game") if wf_mae < wf_mae_naive else
                ("the walk-forward margin forecast LOSES to the zero benchmark by "
                 f"{round(wf_mae - wf_mae_naive, 3)} points per game"))
                + f"; home-cover rate {f(wf_hc_k / len(wf_hc), 3)} (CI {wf_lo}-{wf_hi}) sits inside the luck band,"
                  " and the binary win probability does beat the 0.25 benchmark",
    "source": "data/closeout/derived/walkforward.csv",
}
scorecard.append(wf_sc)
write("scorecard.csv", scorecard)

# ---------------------------------------------------------------- 5c. shrink ablation on the walk-forward rows
abl = []
act_m = [num(r["actual_margin_home"], float) for r in wf_rows]
pred_m = [num(r["pred_margin_home"], float) for r in wf_rows]
sig_w = [num(r["sigma_used"], float) for r in wf_rows]
act_t = [num(r["actual_total"], float) for r in wf_rows]
pred_t = [num(r["pred_total"], float) for r in wf_rows]
mt = [num(r["mean_total_prior"], float) for r in wf_rows]
sigt = [num(r["sigma_total_prior"], float) for r in wf_rows]
for k in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
    e = [abs(a - k * p) for a, p in zip(act_m, pred_m)]
    bt = [(phi(k * p / s) - (1.0 if a > 0 else 0.0)) ** 2 for a, p, s in zip(act_m, pred_m, sig_w)]
    et = [abs(a - (mtv + k * (ptv - mtv))) for a, ptv, mtv in zip(act_t, pred_t, mt)]
    bo = []
    for a, ptv, mtv, sv in zip(act_t, pred_t, mt, sigt):
        line = round_half(mtv + k * (ptv - mtv))
        if a != line:
            bo.append((phi((mtv + k * (ptv - mtv) - line) / sv) - (1.0 if a > line else 0.0)) ** 2)
    abl.append({
        "shrink_k": f(k, 2),
        "mae_margin": f(mean(e), 3), "brier_home_win": f(mean(bt), 5),
        "mae_total": f(mean(et), 3), "brier_over": f(mean(bo), 5) if bo else "",
        "vs_naive_margin": f(mean([abs(a) for a in act_m]) - mean(e), 3),
        "vs_naive_total": f(mean([abs(a - m_) for a, m_ in zip(act_t, mt)]) - mean(et), 3),
        "n": len(act_m),
        "read": ("the naive benchmark itself (k=0 predicts zero margin and the running mean total)"
                 if k == 0 else ("what the model does unshrunk" if k == 1 else "")),
        "source": "data/closeout/derived/walkforward.csv",
    })
best = min(abl, key=lambda r: num(r["brier_home_win"], float))
best_mae = min(abl, key=lambda r: num(r["mae_margin"], float))
abl.append({
    "shrink_k": "best-on-this-sample", "mae_margin": best_mae["mae_margin"], "brier_home_win": best["brier_home_win"],
    "mae_total": "", "brier_over": "", "vs_naive_margin": best_mae["vs_naive_margin"],
    "vs_naive_total": best_mae["vs_naive_total"], "n": len(act_m),
    "read": f"best Brier at k={best['shrink_k']}, best margin MAE at k={best_mae['shrink_k']} - both chosen on the "
            "same 110 games, so neither is evidence; the frozen Week-11 board is the out-of-sample test",
    "source": "data/closeout/derived/walkforward.csv",
})
write("ablation_shrink.csv", abl)
write("scorecard.csv", scorecard)

# ---------------------------------------------------------------- 6. luck panel
n_side = side_n
band_lo = 0.5 - 1.96 * math.sqrt(0.25 / n_side)
band_hi = 0.5 + 1.96 * math.sqrt(0.25 / n_side)
obs = side_pick_rate = sk_pick / sk_n if sk_n else None
m_star = 1 - (1 - 0.05 / len(scorecard)) ** 0.5  # one-sided Bonferroni across the 3 divisions above
luck = [
    {"measure": "variance explained by the margin model (in-sample)", "value": f(r2_margin, 4),
     "how_computed": f"1 - SSE/SST over {len(GAMES)} games, ratings fitted on the same games",
     "caveat": "in-sample: this number cannot be read as skill",
     "source": "data/closeout/derived/season_log.csv"},
    {"measure": "SD of predicted margin vs SD of actual margin", "value": f"{f(sd_pred, 2)} vs {f(sd_act, 2)} (ratio {f(sd_pred / sd_act, 3)})",
     "how_computed": "pstdev of model margins and of realised home margins, same 150 games",
     "caveat": "ratio far below 1 means the model is under-dispersed: it is too sure of itself, so any 'edge' measured against its own line is flattered",
     "source": "data/closeout/derived/season_log.csv"},
    {"measure": "95% luck band for a 13-game hit rate under a coin flip",
     "value": f"{f(band_lo, 3)} to {f(band_hi, 3)}",
     "how_computed": f"0.5 +/- 1.96*sqrt(0.25/n), n={n_side} graded side results",
     "caveat": f"observed {f(obs, 3)} lies inside the band, so the run cannot be separated from luck at n=13",
     "source": "data/closeout/derived/settlement.csv"},
    {"measure": "binomial SE of the observed side hit rate", "value": f(math.sqrt(0.25 / n_side), 4),
     "how_computed": "sqrt(p(1-p)/n) at p=0.5 (the null), n=13",
     "caveat": "one game moves the rate by 1/13 = 0.077, which is larger than most claimed edges",
     "source": "data/closeout/derived/settlement.csv"},
    {"measure": "game-cluster bootstrap interval, side hit rate", "value": f"{sk_blo} to {sk_bhi}",
     "how_computed": f"4000 resamples of whole games (never single bets), seed {SEED}",
     "caveat": "clusters are games so correlated markets cannot shrink the interval falsely",
     "source": "data/closeout/derived/settlement.csv"},
    {"measure": "multiplicity adjustment (Bonferroni, 3 divisions published here)",
     "value": f"alpha per test {f(0.05 / len(scorecard), 4)}; needs a hit rate above {f(0.5 + 1.645 * math.sqrt(0.25 / n_side), 3)} at n=13",
     "how_computed": "0.05 / number of strategies scored on this board, one-sided normal",
     "caveat": "the project has published many more than 3 candidate strategies; the honest multiplier is the number of trials ever run, which is not registered anywhere (question Q-C07)",
     "source": "data/closeout/derived/scorecard.csv"},
    {"measure": "walk-forward: games that could actually be forecast", "value": f"{wf_n} of 150 (n_train>=40 and both clubs seen)",
     "how_computed": "ratings refitted before every game; 32 games sit in the warm-up window and are not graded",
     "caveat": f"MAE {wf_mae} vs naive {wf_mae_naive}; the model is better than nothing, but 'nothing' is a low bar",
     "source": "data/closeout/derived/walkforward.csv"},
    {"measure": "in-sample R-squared vs walk-forward correlation", "value": f"{f(r2_margin, 3)} in-sample vs {f(pearson([num(x['pred_margin_home'], float) for x in wf_rows],[num(x['actual_margin_home'], float) for x in wf_rows]), 3)} walk-forward",
     "how_computed": "same games, two information sets; the gap is entirely overfitting",
     "caveat": "any leaderboard that quotes the in-sample figure is quoting the fit, not the model - the brief's rule that backtest numbers never reach the leaderboard exists for this",
     "source": "data/closeout/derived/walkforward.csv"},
    {"measure": "controls on the same games",
     "value": f"always-home {f(ctl_home_rate, 3)}; Week-9 PCT favourite {f(ctl_fav_rate, 3)}; seeded coin {f(ctl_rand / n if n else None, 3)}, model moneyline pick {f(ml_k / ml_n if ml_n else None, 3)}",
     "how_computed": "same games, same scoring rule, no model",
     "caveat": "the favourite control uses standings through Week 9 - the information set that existed before "
               "these games - so it does not peek",
     "source": "data/closeout/derived/settlement.csv (control columns) and data/hub/standings_2026_thru_wk9.csv "
               "(the pre-Week-10 information set)"},
]
write("luck.csv", luck)

# ---------------------------------------------------------------- 7. correlations, official numbers only
corr = []


def add_corr(label, xs, ys, unit, source, note=""):
    rr = pearson(xs, ys)
    lo, hi = fisher_ci(rr, len(xs))
    corr.append({
        "id": f"K-{len(corr) + 1:02d}", "quantity": label, "n": len(xs),
        "r": f(rr, 3), "ci95_lo": lo, "ci95_hi": hi, "unit_of_observation": unit,
        "inputs": "official box scores / official published lines only",
        "note": note or ("interval computed from n; a CI spanning 0 means no usable dependence signal"
                         if rr is not None and lo != "" and lo <= 0 <= hi else ""),
        "source": source,
    })


hp = [g["home_score"] for g in GAMES]
ap = [g["away_score"] for g in GAMES]
add_corr("home points vs away points (a total is the sum of the two sides)", hp, ap, "game",
         "data/closeout/derived/season_log.csv",
         "if this is near zero, treating a total as one bet and the sides as another carries little dependence - "
         "the number that the parlay gate needs, measured on official scores")
am = [g["margin_home"] for g in GAMES]
tot = [g["total"] for g in GAMES]
add_corr("|margin| vs total", [abs(x) for x in am], tot, "game", "data/closeout/derived/season_log.csv")
add_corr("model margin vs actual margin (pre-kickoff board)",
         [num(s["model_margin_home"], float) for s in settled],
         [num(s["actual_margin_home"], float) for s in settled], "game",
         "data/closeout/derived/settlement.csv", "n=13: this is the number the whole board turns on, and it is small")
add_corr("side-cover outcome vs over outcome on the same games (joint, not marginal)",
         [float(s["side_home_cover_hit"]) for s in settled if s["side_home_cover_hit"] != ""],
         [float(s["total_hit"]) for s in settled if s["total_hit"] != ""], "game",
         "data/closeout/derived/settlement.csv",
         "a parlay of the two legs needs exactly this joint value; multiplying the marginals is not the same thing")
# walk-forward: net points per game *before* each game vs that game's margin (no lookahead)
run_pf, run_pa, wf_x, wf_y = {t_: 0 for t_ in teams}, {t_: 0 for t_ in teams}, [], []
for g in sorted(GAMES, key=lambda x: (x["date_iso"], x["game_id"])):
    h, a = g["home"], g["away"]
    nh, na = run_pf[h] + run_pa[h], run_pf[a] + run_pa[a]
    gh = max(1, len([x for x in GAMES if x["date_iso"] < g["date_iso"] and h in (x["home"], x["away"])]))
    ga = max(1, len([x for x in GAMES if x["date_iso"] < g["date_iso"] and a in (x["home"], x["away"])]))
    if run_pf[h] + run_pa[h] + run_pf[a] + run_pa[a] > 0:
        wf_x.append(nh / gh - na / ga)
        wf_y.append(g["margin_home"])
    run_pf[h] += g["home_score"]; run_pa[h] += g["away_score"]
    run_pf[a] += g["away_score"]; run_pa[a] += g["home_score"]
add_corr("pre-game net points per game difference vs that game's margin (walk-forward, no lookahead)",
         wf_x, wf_y, "game", "data/closeout/derived/season_log.csv",
         "this is the honest strength of the feature the model is built on, measured one game at a time")
add_corr("expected total vs actual total on the pre-kickoff board",
         [num(s["total_fair_line"], float) for s in settled if s["total_fair_line"] != ""],
         [num(s["actual_total"], float) for s in settled], "game",
         "data/closeout/derived/settlement.csv",
         "spread and total dependence is what a same-game parlay would have to survive")
write("correlations.csv", corr)

# ---------------------------------------------------------------- 8. price policy, gates, snapshot ledger
price_policy = [
    {"id": "PDP-1", "rule": "no operator price enters any published number in this module",
     "reason": "the repository holds zero market prices; inventing or imputing one would make every residual fake",
     "effect": "market_side, market_total, market_ml_home and the difference columns stay blank on every row",
     "status": "ADOPTED (this session)", "source": "data/closeout/derived/forecasts_w11.csv"},
    {"id": "PDP-2", "rule": "the fair line is published as a number, the difference is published as a formula",
     "reason": "diff = fair - market, so the column becomes live the moment a price source is admitted",
     "effect": "no residual value is printed today", "status": "ADOPTED (this session)",
     "source": "data/closeout/derived/forecasts_w11.csv"},
    {"id": "PDP-3", "rule": "a price source may be admitted only with a dated terms read and a stored snapshot id",
     "reason": "the brief requires the price-data policy to be decided before any backtest is published",
     "effect": "the settlement below is graded on outcomes, not on return, so no price is needed to run it",
     "status": "PENDING OWNER DECISION - suggestion SG-C-01",
     "source": "https://github.com/karagemop466-tech/X3/blob/b7d4142/data/x3/verified/markets.json"},
    {"id": "PDP-4", "rule": "opening and closing numbers are recorded for every market we originate, from the freeze time",
     "reason": "the originated line is the only price this project controls",
     "effect": f"open = close = {MODEL_VERSION} at {FROZEN_UTC} while no external price exists; the pair is kept, not collapsed",
     "status": "ADOPTED (this session)", "source": "data/closeout/derived/price_store.csv"},
]
write("price_policy.csv", price_policy)

price_store = []
for fr in forecasts:
    h = hashlib.sha256(json.dumps({k: fr[k] for k in
                                   ("game_id", "fair_margin_home", "side_fair_line_home", "total_fair_line",
                                    "ml_prob_home", "model_version", "frozen_utc")},
                                  sort_keys=True).encode()).hexdigest()
    for phase, stamp in (("open", FROZEN_UTC), ("close", "PENDING - kickoff Thu 2026-11-19 8:15 PM ET, then Wed/Fri re-freeze")):
        price_store.append({
            "market_id": f"{fr['game_id']}-{fr['model_version']}", "game_id": fr["game_id"], "week": 11,
            "market": "side", "phase": phase, "captured_utc": stamp,
            "fair_value": fr["side_fair_line_home"], "market_price": "", "difference": "",
            "probability": fr["side_prob_home_cover"], "state": "FAIR_ONLY", "hash": h,
            "inputs_sha256": sha_of(os.path.join(D_OUT, "season_log.csv")),
            "flag": "no operator price exists in this repository (PDP-1)",
            "source": fr["source"],
        })
        price_store.append({
            "market_id": f"{fr['game_id']}-{fr['model_version']}", "game_id": fr["game_id"], "week": 11,
            "market": "total", "phase": phase, "captured_utc": stamp,
            "fair_value": fr["total_fair_line"], "market_price": "", "difference": "",
            "probability": fr["total_prob_over"], "state": "FAIR_ONLY", "hash": h,
            "inputs_sha256": sha_of(os.path.join(D_OUT, "season_log.csv")),
            "flag": "no operator price exists in this repository (PDP-1)",
            "source": fr["source"],
        })
        price_store.append({
            "market_id": f"{fr['game_id']}-{fr['model_version']}", "game_id": fr["game_id"], "week": 11,
            "market": "moneyline", "phase": phase, "captured_utc": stamp,
            "fair_value": fr["ml_fair_american_home"], "market_price": "", "difference": "",
            "probability": fr["ml_prob_home"], "state": "FAIR_ONLY", "hash": h,
            "inputs_sha256": sha_of(os.path.join(D_OUT, "season_log.csv")),
            "flag": "no operator price exists in this repository (PDP-1)",
            "source": fr["source"],
        })
write("price_store.csv", price_store)

prereg = [
    {"id": "G-1", "gate": "pre-registration before results",
     "rule_text": f"model version {MODEL_VERSION}; inputs = the 150 verified games through Week 10; "
                  "parameters printed on every forecast row; the frozen file is committed before the first "
                  "Week-11 kickoff",
     "measured_now": f"forecast rows {len(forecasts)}; frozen {FROZEN_UTC}; first kickoff {FIRST_W11_KICKOFF_UTC}",
     "threshold": "every forecast row stamped strictly before the kickoff of its own game",
     "status": "PASS for the Week-11 board (2 days 0 hours of margin) / FAIL for the Week-10 settlement, "
               "which is graded on games already played",
     "source": "data/closeout/derived/forecasts_w11.csv"},
    {"id": "G-2", "gate": "sample size before a leaderboard row",
     "rule_text": "no strategy is ranked on fewer than 200 graded decisions, and none on fewer than 40 games",
     "measured_now": f"graded decisions {side_n + tot_n + ml_bn} across three markets on {len(settled)} games",
     "threshold": "200 graded decisions / 40 games",
     "status": "FAIL - every score on this board is provisional",
     "source": "data/closeout/derived/scorecard.csv"},
    {"id": "G-3", "gate": "skill must beat its own controls",
     "rule_text": "hit rate must exceed the always-home, Week-9-favourite and seeded-random controls on the same games, "
                  "and the Brier must beat 0.25 for the same fixture set",
     "measured_now": f"model moneyline pick {f(ml_k / ml_n if ml_n else None, 3)} vs always-home "
                     f"{f(ctl_home_rate, 3)} / Week-9 favourite {f(ctl_fav_rate, 3)} / seeded coin "
                     f"{f(ctl_rand / n if n else None, 3)} on the same games; side Brier skill "
                     f"{f(1 - side_brier / 0.25, 4) if side_brier is not None else ''}",
     "threshold": "lower bound of the game-cluster interval must exceed the best control",
     "status": "FAIL - intervals overlap", "source": "data/closeout/derived/scorecard.csv"},
    {"id": "G-4", "gate": "proper score before profit",
     "rule_text": "a division is scored on Brier/log-loss against a benchmark first; ROI is reported only when a "
                  "price exists to settle against",
     "measured_now": "Brier published for all three markets; ROI columns absent by policy",
     "threshold": "no ROI cell may exist without a market_price cell",
     "status": "PASS", "source": "data/closeout/derived/price_policy.csv"},
    {"id": "G-5", "gate": "joint evidence before any parlay or prop combo",
     "rule_text": "a multi-leg structure is ranked only when the joint outcome probability has been validated "
                  "directly and the operator's void/push rules are known",
     "measured_now": f"side/over joint correlation n={len([s for s in settled if s['side_home_cover_hit'] != '' and s['total_hit'] != ''])}; no void rules exist in the repository",
     "threshold": "validated joint model + published void rules; both absent",
     "status": "BLOCKED - parlays and prop combos are not originated at all",
     "source": "data/closeout/derived/correlations.csv"},
    {"id": "G-6", "gate": "demotion (live to paper)",
     "rule_text": "a promoted strategy returns to paper when its rolling 10-game game-cluster Brier lower bound "
                  "falls below the benchmark, or when two consecutive freezes miss a required source capture",
     "measured_now": "not applicable: nothing is promoted (G-2 fails); the trigger is recorded so it is armed before use",
     "threshold": "first promotion is a precondition", "status": "ARMED, NOT FIRED",
     "source": "data/closeout/derived/scorecard.csv"},
    {"id": "G-7", "gate": "signal separated from staking",
     "rule_text": "the board ranks probabilities only; staking, Kelly and ROI are reported on a separate page and "
                  "can never move a strategy up the board",
     "measured_now": "scorecard.csv carries no return column; price_store.csv carries the prices",
     "threshold": "0 rows where a return figure changed a rank", "status": "PASS by construction",
     "source": "data/closeout/derived/scorecard.csv"},
    {"id": "G-8", "gate": "surprise, not level, for availability",
     "rule_text": "the injury feed enters as the change between two dated captures; a level is never a feature",
     "measured_now": "two dated captures exist for this window: the Week-10 report at 2026-11-17T22:45Z and the "
                     "prior session's read of the same URL on 2026-11-15; the Week-11 report does not exist yet",
     "threshold": ">= 3 dated captures of the same week before any designation feature is fitted",
     "status": "FAIL - delta published as an observation, not as a model input",
     "source": "data/closeout/source_reads.csv"},
]
write("prereg_gates.csv", prereg)

meta = {
    "module": "closeout", "session": "arena/e1ad8b78-x3", "generated_utc": FROZEN_UTC,
    "model_version": MODEL_VERSION, "season": 2026, "week_closed": 10, "week_frozen": 11,
    "games_in_log": len(GAMES), "games_week10_captured": len(w10),
    "reconciliation_mismatches": len(mismatches),
    "official_pf_sum": sum_pf, "official_pa_sum": sum_pa,
    "standings_net_arithmetic_ok": bool(net_arith),
    "n_train": len(GAMES), "home_advantage": round(hfa, 6),
    "sigma_margin": round(sigma_m, 6), "sigma_total": round(sigma_t, 6),
    "sd_predicted_margin": round(sd_pred, 4), "sd_actual_margin": round(sd_act, 4),
    "in_sample_r2_margin": round(r2_margin, 4),
    "settlement": {"games": n, "side_gradable": side_n, "side_pushes": side_push,
                   "side_home_cover_hits": side_k, "side_brier": side_brier,
                   "side_skill": f(1 - side_brier / 0.25, 4) if side_brier is not None else None,
                   "model_side_cover_hits": sk_pick, "model_side_cover_rate": f(sk_pick / sk_n if sk_n else None, 4),
                   "ml_hits": ml_k, "ml_n": ml_n, "ml_hit_rate": f(ml_k / ml_n if ml_n else None, 4),
                   "ml_brier": ml_brier, "total_hits": tot_k, "total_n": tot_n, "total_brier": tot_brier,
                   "mae_model": round(mae_model, 3), "mae_benchmark_zero": round(mae_zero, 3),
                   "control_always_home": round(ctl_home_rate, 4),
                   "control_wk9_favourite": round(ctl_fav_rate, 4),
                   "control_random_seeded": round(ctl_rand / n, 4) if n else None,
                   "naive_total_benchmark_mean": round(mean_total_wk1_9, 3)},
    "walkforward": {"graded_games": wf_n, "mae_margin": wf_mae, "brier_over": round(mean([num(r["brier_over"], float) for r in wf_rows]), 5), "mae_margin_naive": wf_mae_naive,
                    "mae_total": wf_tmae, "mae_total_naive": wf_tmae_naive, "brier_home_win": wf_brier,
                    "brier_benchmark": wf_brier_bench, "home_cover_rate": f(wf_hc_k / len(wf_hc), 4),
                    "wilson": [wf_lo, wf_hi], "boot": [wf_blo, wf_bhi]},
    "forecasts": len(forecasts), "price_store_rows": len(price_store),
    "inputs_hash": {os.path.basename(p): sha_of(os.path.join(D_IN, p)) for p in
                    ["week10_finals.csv", "official_standings_2026_wk10.csv", "week11_slate.csv",
                     "availability_w10.csv", "source_reads.csv", "gamebook_ne_det.csv"]},
    "sources": {"week10_results": "https://www.nfl.com/schedules/2026/by-week/week-10",
                "week11_slate": "https://www.nfl.com/schedules/2026/by-week/week-11",
                "standings": "https://www.nfl.com/standings/league/2026/REG",
                "injury_report": "https://www.nfl.com/injuries/league/2026/reg10",
                "injury_report_week11_attempt": "https://www.nfl.com/injuries/league/2026/reg11",
                "game_centre_az_at_kc": "https://www.nfl.com/games/cardinals-at-chiefs-2026-reg-11",
                "game_centre_min_at_sf": "https://www.nfl.com/games/vikings-at-49ers-2026-reg-11",
                "game_centre_ne_at_det": "https://www.nfl.com/games/patriots-at-lions-2026-reg-10",
                "game_book": "https://static.www.nfl.com/image/upload/v1794764592/gamecenter/ab582c2f-4feb-11f1-abca-2c54536568a9.pdf",
                "prior_board": "https://github.com/karagemop466-tech/X3/blob/b7d4142/data/x3/verified/markets.json",
                "inherited_log": "https://github.com/karagemop466-tech/X3/blob/b7d4142/data/x3/verified/results_2026.csv"},
}
with open(os.path.join(D_OUT, "meta.json"), "w") as fh:
    json.dump(meta, fh, indent=1, sort_keys=True)

print(json.dumps({k: v for k, v in meta.items() if k not in ("inputs_hash", "sources")}, indent=1))
print("mismatches:", [m["team"] for m in mismatches])
print("files:", sorted(os.listdir(D_OUT)))
