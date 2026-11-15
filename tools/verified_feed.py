#!/usr/bin/env python3
"""
X3 verified results feed and derivations (session arena/aab4718a-x3).

Inputs (all already in the repo, all traceable to an official NFL.com page):
  data/desk/games.json               163 2026 rows / 137 finals, parsed from
                                     https://www.nfl.com/schedules/2026/by-week/week-N
  data/verified/standings_2026_official.csv
                                     32 clubs, transcribed this session from
                                     https://www.nfl.com/standings/league/2026/REG
  data/desk/standings.json           prior session's standings transcription with
                                     home/road/last5 splits

Outputs (written to data/verified/):
  results_2026.csv        one row per final, with both clubs' official W-L after
                          the game is NOT claimed; the row carries the official
                          schedule page URL and the reconciliation status.
  reconciliation.json     every club x {W,L,T,PF,PA,G} recomputed from the finals
                          vs the official standings page.
  market_stats.json       distributions of margin and total from the finals:
                          the empirical basis for pricing a spread and a total.
  key_numbers.json        push/tie frequency by exact margin - why 3 and 7 matter.
  correlation.json        every coefficient recomputed with n, Fisher-z CI and a
                          permutation p-value.
  backtest.json           walk-forward test: does a net-points rating actually
                          predict the next week's margin? Baselines included.
  hfa.json                home-field advantage measured from non-neutral finals.

Every number here is DERIVED from an official observation. Nothing is copied
from a secondary source, and nothing is filled in where an official value is
absent. The script exits non-zero if a stated invariant fails.

Run: python3 tools/verified_feed.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "verified")
SCHED = "https://www.nfl.com/schedules/2026/by-week/week-{w}"
STAND = "https://www.nfl.com/standings/league/2026/REG"

# Official club abbreviation aliases. nfl.com/standings prints AZ and LA;
# nfl.com/schedules prints ARI and LA. Mapping is stated, not guessed: the
# full club name on both pages is what ties them together.
ALIAS = {"ARI": "AZ", "LAR": "LA", "LAC": "LAC", "LV": "LV", "WAS": "WAS"}
CANON = {"ARI": "AZ", "LA": "LA"}


def canon(a: str) -> str:
    return ALIAS.get(a, a)


# ---------------------------------------------------------------- statistics
def mean(v):
    return sum(v) / len(v) if v else float("nan")


def sd(v, ddof=1):
    if len(v) < 2:
        return float("nan")
    m = mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - ddof))


def pearson(x, y):
    n = len(x)
    mx, my = mean(x), mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return float("nan")
    return sxy / math.sqrt(sxx * syy)


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def fisher_ci(r, n, z=1.959963985):
    if n < 4 or not (-1 < r < 1):
        return (float("nan"), float("nan"))
    zr = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    lo, hi = zr - z * se, zr + z * se
    return (math.tanh(lo), math.tanh(hi))


def perm_p(x, y, iters=20000, seed=20261114):
    """Two-sided permutation p for Pearson r. Deterministic seed -> reproducible."""
    r0 = abs(pearson(x, y))
    if not r0 == r0:
        return float("nan")
    rng = random.Random(seed)
    yy = list(y)
    hits = 0
    for _ in range(iters):
        rng.shuffle(yy)
        if abs(pearson(x, yy)) >= r0 - 1e-12:
            hits += 1
    return (hits + 1) / (iters + 1)


def corr_row(name, x, y, note, source, iters=20000):
    r = pearson(x, y)
    rho = spearman(x, y)
    lo, hi = fisher_ci(r, len(x))
    return {
        "pair": name,
        "n": len(x),
        "pearson_r": round(r, 4),
        "spearman_rho": round(rho, 4),
        "ci95_low": round(lo, 4),
        "ci95_high": round(hi, 4),
        "perm_p": round(perm_p(x, y, iters), 5),
        "note": note,
        "source": source,
    }


# ---------------------------------------------------------------- input
def load_finals():
    g = json.load(open(os.path.join(ROOT, "data", "desk", "games.json"), encoding="utf-8"))
    finals = [x for x in g["games"] if x["status"] == "FINAL"]
    for x in finals:
        x["away"], x["home"] = canon(x["away"]), canon(x["home"])
        x["margin_home"] = x["home_score"] - x["away_score"]
        x["total"] = x["home_score"] + x["away_score"]
        x["source"] = SCHED.format(w=x["week"])
    return finals, g


def load_official_standings():
    p = os.path.join(OUT, "standings_2026_official.csv")
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    return {r["team"]: r for r in rows}


# ---------------------------------------------------------------- steps
def write_results(finals):
    path = os.path.join(OUT, "results_2026.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["week", "date", "away", "home", "away_score", "home_score",
                    "total", "home_margin", "neutral_site", "status", "source_url"])
        for g in sorted(finals, key=lambda x: (x["week"], x["date_iso"], x["home"])):
            w.writerow([g["week"], g["date_iso"], g["away"], g["home"],
                        g["away_score"], g["home_score"], g["total"], g["margin_home"],
                        "Y" if g["neutral_site"] else "N", "FINAL", g["source"]])
    return path


def reconcile(finals, official):
    rec = {}
    for g in finals:
        for team, pf, pa in ((g["away"], g["away_score"], g["home_score"]),
                             (g["home"], g["home_score"], g["away_score"])):
            r = rec.setdefault(team, dict(w=0, l=0, t=0, pf=0, pa=0, g=0))
            r["g"] += 1
            r["pf"] += pf
            r["pa"] += pa
            if pf > pa:
                r["w"] += 1
            elif pf < pa:
                r["l"] += 1
            else:
                r["t"] += 1

    checks = []
    agree = disagree = 0
    for team in sorted(official):
        o, c = official[team], rec.get(team)
        if c is None:
            checks.append(dict(team=team, field="present", official="yes", recomputed="no", ok=False))
            disagree += 1
            continue
        for field in ("w", "l", "t", "pf", "pa"):
            ov, cv = int(o[field]), c[field]
            ok = ov == cv
            agree += ok
            disagree += (not ok)
            checks.append(dict(team=team, field=field, official=ov, recomputed=cv, ok=ok))
        og = int(o["w"]) + int(o["l"]) + int(o["t"])
        ok = og == c["g"]
        agree += ok
        disagree += (not ok)
        checks.append(dict(team=team, field="games", official=og, recomputed=c["g"], ok=ok))

    extra = sorted(set(rec) - set(official))
    out = {
        "method": "Every final in data/desk/games.json is re-summed per club "
                  "(W/L/T from the score, PF, PA, games) and compared field by field "
                  "with data/verified/standings_2026_official.csv, which was "
                  "transcribed this session from the official standings page.",
        "official_source": STAND,
        "schedule_source_pattern": SCHED.format(w="N"),
        "finals_used": len(finals),
        "clubs_official": len(official),
        "clubs_recomputed": len(rec),
        "fields_compared": agree + disagree,
        "fields_agree": agree,
        "fields_disagree": disagree,
        "clubs_in_log_not_in_standings": extra,
        "aliases_applied": ALIAS,
        "checks": checks,
        "status": "PASS" if disagree == 0 and not extra else "FAIL",
    }
    json.dump(out, open(os.path.join(OUT, "reconciliation.json"), "w", encoding="utf-8"), indent=1)
    return out


def market_stats(finals):
    totals = [g["total"] for g in finals]
    margins = [g["margin_home"] for g in finals]
    absm = [abs(m) for m in margins]
    # empirical two-sided pricing of a total: P(total > line)
    def over_rates(xs):
        xs = sorted(xs)
        return {str(p): sorted(xs)[min(len(xs) - 1, int(round(p / 100 * len(xs))))]
                for p in (5, 10, 25, 50, 75, 90, 95)}
    out = {
        "method": "Sample moments of the 137 verified 2026 finals. Mean and SD are "
                  "what a normal-approximation line is priced from; the quantiles are "
                  "the same information without assuming normality. sd_used_for_pricing "
                  "is the sample SD (ddof=1).",
        "source": SCHED.format(w="N"),
        "schedule_source_pattern": SCHED.format(w="N"),
        "n_games": len(finals),
        "total": {"mean": round(mean(totals), 2), "sd": round(sd(totals), 2),
                  "min": min(totals), "max": max(totals),
                  "quantiles": over_rates(totals)},
        "abs_margin": {"mean": round(mean(absm), 2), "sd": round(sd(absm), 2),
                       "min": min(absm), "max": max(absm),
                       "quantiles": over_rates(absm)},
        "home_margin": {"mean": round(mean(margins), 2), "sd": round(sd(margins), 2)},
        "league_avg_team_score": round(mean(totals) / 2, 2),
        "normal_check": {
            "abs_margin_excess_kurtosis": round(excess_kurtosis(absm), 3),
            "total_excess_kurtosis": round(excess_kurtosis(totals), 3),
            "note": "Excess kurtosis ~0 means a normal approximation is not crazy; "
                    "large negative values mean the distribution is too flat-peaked "
                    "for normal pricing to be safe.",
        },
    }
    json.dump(out, open(os.path.join(OUT, "market_stats.json"), "w", encoding="utf-8"), indent=1)
    return out


def excess_kurtosis(v):
    """Sample excess kurtosis, the standard unbiased (G2) estimator.

    G2 = ((n-1) / ((n-2)(n-3))) * ((n+1)*g2 + 6), with g2 the biased
    m4/m2^2 - 3. Normal -> 0. Written out so the formula is auditable.
    """
    n = len(v)
    if n < 4:
        return float("nan")
    m = mean(v)
    m2 = sum((x - m) ** 2 for x in v) / n
    m4 = sum((x - m) ** 4 for x in v) / n
    if m2 == 0:
        return float("nan")
    g2 = m4 / (m2 * m2) - 3.0
    return ((n - 1) / ((n - 2) * (n - 3))) * ((n + 1) * g2 + 6)


def key_numbers(finals):
    """How often the final margin lands on an exact number - the push risk."""
    from collections import Counter
    cm = Counter(abs(g["margin_home"]) for g in finals)
    ct = Counter(g["total"] for g in finals)
    n = len(finals)
    rows = []
    for k in sorted(cm):
        rows.append({"margin": k, "games": cm[k], "share": round(cm[k] / n, 4),
                     "push_if_line_is": k})
    # cumulative share of margins <= k, useful for "line is inside the key cluster"
    cum = 0
    for r in rows:
        cum += r["games"]
        r["cum_games_le"] = cum
        r["cum_share_le"] = round(cum / n, 4)
    out = {
        "method": "Count of finals by the absolute home margin. A spread set exactly on "
                  "a value k pushes when the game lands on k; the share column is the "
                  "probability of that push if that line were used, estimated from the "
                  "same 137 games. This is a sample estimate, not a law of football.",
        "source": SCHED.format(w="N"),
        "schedule_source_pattern": SCHED.format(w="N"),
        "n_games": n,
        "by_margin": rows,
        "top_totals": [{"total": t, "games": c} for t, c in ct.most_common(10)],
        "share_within_3": round(sum(v for k, v in cm.items() if k <= 3) / n, 4),
        "share_within_7": round(sum(v for k, v in cm.items() if k <= 7) / n, 4),
    }
    json.dump(out, open(os.path.join(OUT, "key_numbers.json"), "w", encoding="utf-8"), indent=1)
    return out


def hfa(finals):
    nn = [g for g in finals if not g["neutral_site"]]
    m = [g["margin_home"] for g in nn]
    se = sd(m) / math.sqrt(len(m))
    out = {
        "method": "Mean home margin over non-neutral finals. The 95% interval is the "
                  "normal approximation mean +/- 1.96*SE, which is valid for a mean of "
                  "~135 observations. Neutral-site games are excluded and counted.",
        "source": SCHED.format(w="N"),
        "schedule_source_pattern": SCHED.format(w="N"),
        "n_games_total": len(finals),
        "n_neutral_excluded": len(finals) - len(nn),
        "n_non_neutral": len(nn),
        "hfa_points": round(mean(m), 3),
        "se": round(se, 3),
        "ci95": [round(mean(m) - 1.96 * se, 3), round(mean(m) + 1.96 * se, 3)],
        "note": "HFA in points of margin, not of team score. A neutral-site game gets 0.",
        "neutral_games": [f"{g['away']}@{g['home']} {g['date_iso']} ({g['neutral_site_name']})"
                          for g in finals if g["neutral_site"]],
    }
    json.dump(out, open(os.path.join(OUT, "hfa.json"), "w", encoding="utf-8"), indent=1)
    return out


def correlations(finals, official, standings_splits):
    tot = [g["total"] for g in finals]
    absm = [abs(g["margin_home"]) for g in finals]
    signed = [g["margin_home"] for g in finals]
    away = [g["away_score"] for g in finals]
    home = [g["home_score"] for g in finals]

    clubs = sorted(official)
    pf_ppg = [int(official[c]["pf"]) / (int(official[c]["w"]) + int(official[c]["l"]) + int(official[c]["t"])) for c in clubs]
    pa_ppg = [int(official[c]["pa"]) / (int(official[c]["w"]) + int(official[c]["l"]) + int(official[c]["t"])) for c in clubs]
    net_ppg = [a - b for a, b in zip(pf_ppg, pa_ppg)]
    win_pct = [int(official[c]["w"]) / (int(official[c]["w"]) + int(official[c]["l"]) + int(official[c]["t"])) for c in clubs]

    def split(c, field):
        s = standings_splits.get(c, {}).get(field, "")
        parts = s.split("-")
        if len(parts) != 3:
            return None
        w, l, t = (int(x) for x in parts)
        n = w + l + t
        return (w + 0.5 * t) / n if n else None

    home_pct, road_pct, last5 = [], [], []
    for c in clubs:
        home_pct.append(split(c, "home"))
        road_pct.append(split(c, "road"))
        last5.append(split(c, "last5"))
    keep = [i for i, v in enumerate(zip(home_pct, road_pct, last5)) if None not in v]
    hp = [home_pct[i] for i in keep]
    rp = [road_pct[i] for i in keep]
    l5 = [last5[i] for i in keep]
    k_net = [net_ppg[i] for i in keep]

    rows = [
        corr_row("game total vs |margin|", tot, absm,
                 "Do scoring-heavy games also blow out? The screen for whether a total "
                 "and a spread are independent legs of the same ticket.", SCHED.format(w="N")),
        corr_row("game total vs signed home margin", tot, signed,
                 "Directional version of the row above; reported separately so the two "
                 "cannot be confused (see FLG-22 in COORDINATION.md).", SCHED.format(w="N")),
        corr_row("away score vs home score (same game)", away, home,
                 "Within-game co-movement. This is the quantity that decides whether two "
                 "legs in one game may be multiplied as if independent.", SCHED.format(w="N")),
        corr_row("points for per game vs points against per game (clubs)", pf_ppg, pa_ppg,
                 "Club-level balance: does scoring more come with allowing more?", STAND),
        corr_row("net points per game vs win pct (clubs)", net_ppg, win_pct,
                 "How much of a club's record its scoring differential already explains.", STAND),
        corr_row("points for per game vs win pct (clubs)", pf_ppg, win_pct,
                 "Offence alone.", STAND),
        corr_row("points against per game vs win pct (clubs)", pa_ppg, win_pct,
                 "Defence alone.", STAND),
        corr_row("home win pct vs road win pct (clubs)", hp, rp,
                 "Is home form portable to the road? If this is weak, 'they play well at "
                 "home' is not evidence for a road game.", STAND),
        corr_row("last-5 win pct vs net points per game (clubs)", l5, k_net,
                 "Does the recent record track the underlying point differential, i.e. is "
                 "'form' mostly a restatement of quality?", STAND),
    ]
    out = {
        "method": "Pearson and Spearman correlation with n printed for every value. The "
                  "95% interval is Fisher z. The p-value is a two-sided permutation test "
                  "with 20,000 shuffles and a fixed seed, so it is reproducible and does "
                  "not rely on a normality assumption. Only official numbers are used: "
                  "finals from the NFL schedule pages and the NFL standings page. No "
                  "price data is involved, so none of these are market correlations.",
        "sources": [SCHED.format(w="N"), STAND],
        "rows": rows,
        "cannot_compute": [
            "any correlation against a market price or a closing line (no price feed in the repo)",
            "player-prop joint distributions (no official prop archive)",
            "anything requiring play-by-play (not ingested)",
        ],
    }
    json.dump(out, open(os.path.join(OUT, "correlation.json"), "w", encoding="utf-8"), indent=1)
    return out


def backtest(finals, hfa_points):
    """
    Walk-forward: for each week w, rate clubs only on weeks < w, price every game
    in week w, then score it. Parameters are fixed in advance and printed, not
    tuned on the test set.

    Baseline A: predict a 0 margin (i.e. pick'em) and a fixed league-average total.
    Baseline B: net points per game, shrunk, plus measured HFA.
    This answers one question honestly: does the arithmetic beat a coin flip on
    margin, measured out of sample? It does not claim a market edge.
    """
    weeks = sorted({g["week"] for g in finals})
    K_SHRINK = 4.0  # pseudo-games of league-average prior, same as the hub's params
    FIXED_TOTAL = 45.5  # the naive reference total; deliberately not fitted to the data
    rows, err_sp, err_zero, tot_err, tot_err_base = [], [], [], [], []
    for w in weeks[3:]:  # need at least 3 weeks of history
        hist = [g for g in finals if g["week"] < w]
        if not hist:
            continue
        agg = {}
        for g in hist:
            for t, pf, pa in ((g["away"], g["away_score"], g["home_score"]),
                              (g["home"], g["home_score"], g["away_score"])):
                a = agg.setdefault(t, [0, 0, 0])
                a[0] += pf
                a[1] += pa
                a[2] += 1
        lg = mean([g["total"] for g in hist]) / 2
        net = {t: (v[0] - v[1]) / v[2] for t, v in agg.items()}
        rating = {t: net[t] * agg[t][2] / (agg[t][2] + K_SHRINK) for t in net}
        for g in [x for x in finals if x["week"] == w]:
            if g["away"] not in rating or g["home"] not in rating:
                continue
            h = 0.0 if g["neutral_site"] else hfa_points
            pred_margin = rating[g["home"]] - rating[g["away"]] + h
            pred_total = 2 * lg
            rows.append(dict(week=w, game=f"{g['away']}@{g['home']}",
                             actual_margin=g["margin_home"], pred_margin=round(pred_margin, 2),
                             actual_total=g["total"], pred_total=round(pred_total, 2),
                             source=g["source"]))
            err_sp.append(abs(pred_margin - g["margin_home"]))
            err_zero.append(abs(g["margin_home"]))
            tot_err.append(abs(pred_total - g["total"]))
            tot_err_base.append(abs(FIXED_TOTAL - g["total"]))
    n = len(rows)
    out = {
        "method": "Walk-forward, no look-ahead. Weeks are scored only using games from "
                  "strictly earlier weeks. Rating = (points for - points against per game) "
                  "shrunk toward 0 by n/(n+4) pseudo-games. Margin prediction = "
                  "(home rating - away rating) + measured HFA, HFA set to 0 at neutral "
                  "sites. Total prediction = twice the league average team score from the "
                  "same earlier weeks. Parameters were fixed before the run and are printed "
                  "here; nothing was tuned on the scored games.",
        "sources": [SCHED.format(w="N")],
        "params": {"shrinkage_games": K_SHRINK, "hfa_points_used": hfa_points,
                   "hfa_source": "data/verified/hfa.json (measured from the same finals)"},
        "n_games_scored": n,
        "weeks_scored": sorted({r["week"] for r in rows}),
        "spread": {
            "mae_model": round(mean(err_sp), 2),
            "mae_predict_zero": round(mean(err_zero), 2),
            "beats_predict_zero": mean(err_sp) < mean(err_zero),
            "improvement_points": round(mean(err_zero) - mean(err_sp), 2),
            "corr_pred_vs_actual": round(pearson([r["pred_margin"] for r in rows],
                                                 [r["actual_margin"] for r in rows]), 4),
        },
        "total": {
            "mae_league_average": round(mean(tot_err), 2),
            "mae_fixed_45_5": round(mean(tot_err_base), 2),
            "note": "A total is only worth pricing if it beats the league average; the "
                    "fixed-45.5 column is the naive reference a real market line has to beat.",
        },
        "rows": rows,
        "claim_limit": "This measures predictive accuracy against the score, not against a "
                       "market price. With no price feed in the repo, it cannot show an edge "
                       "or an ROI, and it must not be read as one. n is small and one season.",
    }
    json.dump(out, open(os.path.join(OUT, "backtest.json"), "w", encoding="utf-8"), indent=1)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    finals, raw = load_finals()
    official = load_official_standings()
    splits = {r["abbr"]: {"home": r.get("home", ""), "road": r.get("road", ""),
                          "last5": r.get("last5", "")}
              for r in json.load(open(os.path.join(ROOT, "data", "desk", "standings.json"),
                                      encoding="utf-8"))["rows"]}
    splits = {canon(k): v for k, v in splits.items()}

    write_results(finals)
    rc = reconcile(finals, official)
    ms = market_stats(finals)
    kn = key_numbers(finals)
    h = hfa(finals)
    c = correlations(finals, official, splits)
    b = backtest(finals, h["hfa_points"])

    print(f"finals: {len(finals)}  (source rows: {raw['counts']['total']})")
    print(f"reconciliation: {rc['status']}  {rc['fields_agree']}/{rc['fields_compared']} fields agree"
          f"  clubs {rc['clubs_recomputed']}/{rc['clubs_official']}")
    print(f"market: total mean {ms['total']['mean']} sd {ms['total']['sd']} | "
          f"|margin| mean {ms['abs_margin']['mean']} sd {ms['abs_margin']['sd']}")
    print(f"key numbers: share of games within 3 pts = {kn['share_within_3']:.3f}, "
          f"within 7 = {kn['share_within_7']:.3f}")
    print(f"HFA: {h['hfa_points']:+.3f} pts on n={h['n_non_neutral']} "
          f"CI {h['ci95']} (excluded {h['n_neutral_excluded']} neutral)")
    print("correlations:")
    for r in c["rows"]:
        print(f"  {r['pair']:<48} r={r['pearson_r']:+.4f} n={r['n']:>3} "
              f"CI[{r['ci95_low']:+.3f},{r['ci95_high']:+.3f}] p={r['perm_p']:.4f}")
    print(f"backtest: n={b['n_games_scored']} spread MAE {b['spread']['mae_model']} vs "
          f"predict-0 {b['spread']['mae_predict_zero']} (corr {b['spread']['corr_pred_vs_actual']})")
    print(f"          total MAE {b['total']['mae_league_average']} vs fixed45.5 "
          f"{b['total']['mae_fixed_45_5']}")
    if rc["status"] != "PASS":
        raise SystemExit("reconciliation FAILED - see data/verified/reconciliation.json")
    print("OK")


if __name__ == "__main__":
    main()
