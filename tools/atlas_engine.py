#!/usr/bin/env python3
"""Compute the atlas/ datasets from the verified inputs in atlas_data.py.

Everything produced here is either (a) transcribed from an official page, or
(b) arithmetic on those transcriptions. Anything else is emitted as blank with
an UNVERIFIED / BLOCKED marker. No value is inferred.
"""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path

import atlas_data as D

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "atlas"
COMMITTED_INJURY = ROOT / "data" / "hub" / "injuries_2026_wk10.csv"


# ---------------------------------------------------------------- statistics
def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None, n
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None, n
    return sxy / math.sqrt(sxx * syy), n


def r_ci(r, n):
    """95% interval for a Pearson r via Fisher's z."""
    if r is None or n < 4:
        return (None, None)
    z = math.atanh(max(-0.999999, min(0.999999, r)))
    se = 1.0 / math.sqrt(n - 3)
    return (math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se))


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def american(prob):
    """Fair American price for a probability, no margin applied."""
    if prob <= 0 or prob >= 1:
        return ""
    if prob >= 0.5:
        return str(int(round(-100.0 * prob / (1.0 - prob))))
    return "+" + str(int(round(100.0 * (1.0 - prob) / prob)))


def sd(vals):
    n = len(vals)
    if n < 2:
        return 0.0
    m = sum(vals) / n
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1))


def fmt(v, nd=2):
    return "" if v is None else f"{v:.{nd}f}"


# ------------------------------------------------------------------- loading
def team_rates():
    """PPG / PAPG / win pct per club from the official standings."""
    out = {}
    for row in D.STANDINGS:
        team, name, w, l, t = row[0], row[1], row[2], row[3], row[4]
        pf, pa = row[6], row[7]
        games = w + l + t
        ppg = pf / games
        papg = pa / games
        winpct = (w + 0.5 * t) / games
        out[team] = {
            "team": team, "name": name, "w": w, "l": l, "t": t, "games": games,
            "pf": pf, "pa": pa, "ppg": ppg, "papg": papg, "winpct": winpct,
            "net_ppg": ppg - papg,
        }
    return out


def injury_out_counts():
    """Out designations per club in the committed Week 10 capture."""
    counts = {}
    if COMMITTED_INJURY.exists():
        with COMMITTED_INJURY.open() as fh:
            for row in csv.DictReader(fh):
                team = (row.get("team") or "").strip()
                status = (row.get("status") or "").strip()
                counts.setdefault(team, {"Out": 0, "Doubtful": 0, "Questionable": 0, "": 0})
                if status in counts[team]:
                    counts[team][status] += 1
    return counts


# --------------------------------------------------------------------- model
def originate(rates, outs):
    """Side, then total, then moneyline - in that order, as pre-registered."""
    M = D.MODEL
    hfa = M["hfa_points"]
    sigma = M["sigma_points"]
    k = M["personnel_points_per_out"]
    expo = M["pythagorean_exponent"]

    # league anchors, declared from the same official table
    total_team_games = sum(r["games"] for r in rates.values())
    total_points = sum(r["pf"] for r in rates.values())
    league_ppg = total_points / total_team_games
    league_combined = 2.0 * league_ppg

    rows = []
    for (date, time_et, net, away, home, slug, loc, stadium, sched) in D.WEEK11_FIXTURES:
        a, h = rates[away], rates[home]
        # 1. side
        base = hfa + ((h["ppg"] + a["papg"]) - (a["ppg"] + h["papg"])) / 2.0
        a_out = outs.get(away, {}).get("Out", 0)
        h_out = outs.get(home, {}).get("Out", 0)
        pers = k * (h_out - a_out)
        side_b = base + pers
        # 2. total - two declared estimators, both published
        tot_1 = (h["ppg"] + a["ppg"] + h["papg"] + a["papg"]) / 2.0
        tot_2 = league_combined + 0.5 * ((h["ppg"] - h["papg"]) + (a["ppg"] - a["papg"]))
        # 3. moneyline, derived from the side model only
        p_home = norm_cdf(side_b / sigma)
        rows.append({
            "date": date, "time_et": time_et, "network": net, "away": away, "home": home,
            "slug": slug, "location": loc, "stadium": stadium, "sched_venue": sched,
            "away_ppg": a["ppg"], "away_papg": a["papg"], "home_ppg": h["ppg"],
            "home_papg": h["papg"],
            "side_base": base, "side_personnel": side_b, "side_delta": pers,
            "away_outs": a_out, "home_outs": h_out,
            "total_1": tot_1, "total_2": tot_2, "total_gap": tot_1 - tot_2,
            "p_home": p_home, "price_home": american(p_home),
            "price_away": american(1.0 - p_home),
            "market_side": "", "market_total": "", "market_ml": "",
            "diff_side": "", "diff_total": "", "diff_ml": "",
        })
    return rows, league_ppg, league_combined


def pythagorean(rates, expo):
    rows = []
    for team, r in sorted(rates.items()):
        pf = max(r["pf"], 1e-9)
        pa = max(r["pa"], 1e-9)
        exp_pct = pf ** expo / (pf ** expo + pa ** expo)
        exp_wins = exp_pct * r["games"]
        actual = r["w"] + 0.5 * r["t"]
        rows.append({
            "team": team, "name": r["name"], "games": r["games"], "pf": r["pf"], "pa": r["pa"],
            "net_ppg": r["net_ppg"], "actual_winpct": r["winpct"], "pyth_winpct": exp_pct,
            "expected_wins": exp_wins, "actual_wins": actual,
            "residual_wins": actual - exp_wins,
        })
    return rows


# -------------------------------------------------------------------- output
def write_csv(name, header, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(header)
        wr.writerows(rows)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    rates = team_rates()
    outs = injury_out_counts()
    expo = D.MODEL["pythagorean_exponent"]

    # 1. standings
    write_csv("standings_2026_thru_wk10.csv",
              ["team", "name", "w", "l", "t", "pct", "pf", "pa", "net", "home", "road",
               "div", "div_pct", "conf", "conf_pct", "nonconf", "streak", "last5",
               "games", "ppg", "papg", "win_pct", "source"],
              [list(r) + [r[2] + r[3] + r[4], round(r[6] / (r[2] + r[3] + r[4]), 3),
                          round(r[7] / (r[2] + r[3] + r[4]), 3),
                          round((r[2] + 0.5 * r[4]) / (r[2] + r[3] + r[4]), 4),
                          D.SOURCES["standings"]["url"]]
               for r in D.STANDINGS])

    # 2. week 10 results
    res_rows = []
    for date, away, home, ap, hp, slot in D.WEEK10_RESULTS:
        res_rows.append([f"{away}@{home}", date, away, home, ap, hp,
                         D.STANDINGS and rates[home]["name"], rates[away]["name"],
                         hp - ap, home if hp > ap else (away if ap > hp else ""),
                         abs(hp - ap), slot, D.SOURCES["wk10"]["url"]])
    write_csv("results_2026_wk10.csv",
              ["game", "date", "away", "home", "away_pts", "home_pts", "home_name",
               "away_name", "home_margin", "winner", "abs_margin", "slot", "source"],
              res_rows)

    # 3. week 11 fixtures with venues
    fx = []
    for (date, time_et, net, away, home, slug, loc, stadium, sched) in D.WEEK11_FIXTURES:
        conflict = "CONFLICT" if stadium.replace("AT&T", "AT&T").split()[0].upper() not in sched.upper() else ""
        fx.append([f"{away}@{home}", date, time_et, net, away, home, loc, stadium, sched,
                   conflict, D.GAME_CENTRE % slug, D.SOURCES["wk11"]["url"]])
    write_csv("fixtures_2026_wk11.csv",
              ["game", "date", "time_et", "network", "away", "home", "location",
               "stadium_game_centre", "stadium_schedule_page", "venue_flag", "source_gc",
               "source_sched"], fx)

    # 4. official team stats
    write_csv("team_stats_2026_thru_wk10.csv",
              ["team", "name", "ppg", "ypg", "top_per_game", "def_sacks", "def_ints",
               "turnover_diff", "source"],
              [[t, rates[t]["name"], ppg, ypg, top, sk, it, td, D.GAME_CENTRE % slug]
               for (t, ppg, ypg, top, sk, it, td) in D.TEAM_STATS
               for slug in [next(s for (d, tm, nw, a, h, s, l, st, sv) in D.WEEK11_FIXTURES
                                if a == t or h == t)]])

    # 5. injury report counts (live recount vs committed capture)
    inj = []
    for team, live, comm, live_des, comm_des in D.INJURY_TEAM_COUNTS:
        flag = "MISMATCH" if live != comm or live_des != comm_des else "match"
        inj.append([team, rates[team]["name"], live, comm, live_des, comm_des, flag,
                    D.SOURCES["injuries"]["url"]])
    write_csv("injury_counts_2026_wk10.csv",
              ["team", "name", "rows_live_2026_11_17", "rows_committed_2026_11_14",
               "designated_live", "designated_committed", "flag", "source"], inj)

    # 6. roster / availability events
    write_csv("roster_events_2026.csv",
              ["date", "club", "kind", "player", "detail", "source"],
              [[d, c, k, p, det, D.SOURCES[s]["url"]] for (d, c, k, p, det, s) in D.ROSTER_EVENTS])

    # 7. origination
    orig, league_ppg, league_combined = originate(rates, outs)
    write_csv("origination_2026_wk11.csv",
              ["game", "date_et", "time_et", "network", "away", "home", "venue",
               "fair_side_home", "fair_side_personnel", "personnel_delta",
               "fair_total_points_model", "fair_total_league_anchored", "total_gap",
               "p_home_win", "fair_price_home", "fair_price_away",
               "market_side", "market_total", "market_ml",
               "diff_side", "diff_total", "diff_ml", "source_inputs"],
              [[r["away"] + "@" + r["home"], r["date"], r["time_et"], r["network"],
                r["away"], r["home"], r["stadium"],
                fmt(r["side_base"], 2), fmt(r["side_personnel"], 2), fmt(r["side_delta"], 2),
                fmt(r["total_1"], 2), fmt(r["total_2"], 2), fmt(r["total_gap"], 2),
                fmt(r["p_home"], 4), r["price_home"], r["price_away"],
                "", "", "", "", "", "",
                D.SOURCES["standings"]["url"]]
               for r in orig])

    # 8. luck panel
    pyth = pythagorean(rates, expo)
    write_csv("luck_panel_2026.csv",
              ["team", "name", "games", "pf", "pa", "net_ppg", "actual_win_pct",
               "pythagorean_win_pct", "expected_wins", "actual_wins", "residual_wins",
               "source"],
              [[p["team"], p["name"], p["games"], p["pf"], p["pa"], fmt(p["net_ppg"], 3),
                fmt(p["actual_winpct"], 4), fmt(p["pyth_winpct"], 4),
                fmt(p["expected_wins"], 2), fmt(p["actual_wins"], 2),
                fmt(p["residual_wins"], 2), D.SOURCES["standings"]["url"]]
               for p in pyth])

    # 9. correlations
    stats = {t: s for (t, *s) in [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in D.TEAM_STATS]}
    teams26 = [t for (t, *_rest) in D.TEAM_STATS]

    def pair(fn_a, fn_b, teams, label_a, label_b, src):
        xs, ys = [], []
        for t in teams:
            a, b = fn_a(t), fn_b(t)
            if a is None or b is None:
                continue
            xs.append(a)
            ys.append(b)
        r, n = pearson(xs, ys)
        lo, hi = r_ci(r, n)
        return [label_a, label_b, n, fmt(r, 4), fmt(lo, 4), fmt(hi, 4), src]

    pyth_pct = {p["team"]: p["pyth_winpct"] for p in pyth}

    def home_wp(t):
        for row in D.STANDINGS:
            if row[0] == t:
                w, l, tt = (int(x) for x in row[9].split("-"))
                g = w + l + tt
                return (w + 0.5 * tt) / g if g else None
        return None

    def road_wp(t):
        for row in D.STANDINGS:
            if row[0] == t:
                w, l, tt = (int(x) for x in row[10].split("-"))
                g = w + l + tt
                return (w + 0.5 * tt) / g if g else None
        return None

    su = D.SOURCES["standings"]["url"]
    gc = D.SOURCES["wk11"]["url"]
    corr = [
        pair(lambda t: rates[t]["net_ppg"], lambda t: rates[t]["winpct"],
             list(rates), "Net points per game", "Win percentage", su),
        pair(lambda t: rates[t]["ppg"], lambda t: rates[t]["winpct"],
             list(rates), "Points scored per game", "Win percentage", su),
        pair(lambda t: rates[t]["papg"], lambda t: rates[t]["winpct"],
             list(rates), "Points allowed per game", "Win percentage", su),
        pair(lambda t: pyth_pct[t], lambda t: rates[t]["winpct"],
             list(rates), "Pythagorean expected win %", "Actual win %", su),
        pair(home_wp, road_wp, list(rates), "Home win %", "Road win %", su),
        pair(lambda t: stats[t][5], lambda t: rates[t]["winpct"], teams26,
             "Turnover differential", "Win percentage", gc),
        pair(lambda t: stats[t][1], lambda t: stats[t][0], teams26,
             "Yards per game", "Points per game", gc),
        pair(lambda t: stats[t][3], lambda t: rates[t]["papg"], teams26,
             "Defensive sacks", "Points allowed per game", gc),
        pair(lambda t: stats[t][4], lambda t: stats[t][5], teams26,
             "Defensive interceptions", "Turnover differential", gc),
        pair(lambda t: stats[t][3], lambda t: rates[t]["winpct"], teams26,
             "Defensive sacks", "Win percentage", gc),
    ]
    write_csv("correlations_2026.csv",
              ["quantity_a", "quantity_b", "n", "pearson_r", "ci95_low", "ci95_high", "source"],
              corr)

    # 10. requirements and gates
    write_csv("requirements.csv",
              ["id", "requirement", "status", "blocking_gate", "number_that_clears_it"],
              [list(r) for r in D.REQUIREMENTS])
    write_csv("gates.csv", ["id", "gate", "rule", "blocks", "current_reading"],
              [list(g) for g in D.GATES])

    # 11. sources
    write_csv("sources.csv", ["key", "label", "url", "read_on", "kind", "note"],
              [[k, v["label"], v["url"], v["read"], v["kind"], v["note"]]
               for k, v in D.SOURCES.items()])

    summary = {
        "standings_rows": len(D.STANDINGS),
        "team_games": sum(r["games"] for r in rates.values()),
        "games_implied": sum(r["games"] for r in rates.values()) // 2,
        "league_ppg": league_ppg,
        "league_combined": league_combined,
        "wk10_games": len(D.WEEK10_RESULTS),
        "wk10_byes": len(D.WEEK10_BYES),
        "wk11_games": len(D.WEEK11_FIXTURES),
        "wk11_byes": len(D.WEEK11_BYES),
        "venue_conflicts": sum(1 for r in fx if r[9]),
        "luck_sd": sd([p["residual_wins"] for p in pyth]),
        "luck_r": pearson([p["pyth_winpct"] for p in pyth],
                          [p["actual_winpct"] for p in pyth])[0],
        "luck_r2": (pearson([p["pyth_winpct"] for p in pyth],
                            [p["actual_winpct"] for p in pyth])[0] or 0) ** 2,
        "wk10_margin_sd": sd([abs(hp - ap) for (_d, _a, _h, ap, hp, _s)
                              in [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in D.WEEK10_RESULTS]]),
        "corr_rows": len(corr),
        "injury_rows_committed": D.COMMITTED_TOTALS["rows"],
        "injury_rows_live": D.LIVE_TOTALS["rows"],
        "injury_team_mismatches": sum(1 for r in inj if r[6] != "match"),
        "origination_rows": len(orig),
        "roster_events": len(D.ROSTER_EVENTS),
    }
    return rates, outs, orig, pyth, corr, summary


if __name__ == "__main__":
    rates, outs, orig, pyth, corr, summary = build()
    for k, v in summary.items():
        print(f"{k:26s} {v}")
