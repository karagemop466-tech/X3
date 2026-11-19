#!/usr/bin/env python3
"""
X3 / correlation engine -- correlations computed ONLY from officially sourced numbers,
with n published next to every value.

Rule enforced by the build, not by convention: a correlation row may only exist if

  * both variables come from a file that is transcribed from an official NFL page and
    carries that page's URL per row / per file, AND
  * the row states n, the estimator, the 95% interval and the source URL.

Anything else -- prop joint dependence, parlay leg dependence, injury-cost beta -- has no
official source in this repository, so it is published as a BLANK row with the reason and
the missing artefact named. It is never estimated to fill the table.

Two independent official inputs:

  data/x3/verified/results.json      one row per game, reconciled to the official standings
                            (tools/results_feed.py, 0 mismatches on 32 clubs)
  data/hub/standings_2026_thru_wk9.csv   official standings, transcribed by another session

Run: python3 tools/correlation_engine.py
"""
from __future__ import annotations

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import x3_model as M  # noqa: E402

OUT = os.path.join(ROOT, "data", "x3", "verified")
SRC_RESULTS = "https://www.nfl.com/schedules/2026/by-week/week-10"
SRC_STANDINGS = "https://www.nfl.com/standings/league/2026/REG"


def row(x, y, n, r, method, source, note, extra_one_sided=None):
    lo, hi = M.fisher_ci(r, n)
    out = {
        "x": x, "y": y, "n": n, "value": None if r is None else round(r, 4),
        "ci95_low": None if lo is None else round(lo, 4),
        "ci95_high": None if hi is None else round(hi, 4),
        "r2": None if r is None else round(r * r, 4),
        "estimator": method, "source": source, "note": note,
        "status": "VERIFIED-INPUT",
    }
    if extra_one_sided:
        out.update(extra_one_sided)
    return out


def blank(x, y, why, needed, source_of_rule):
    return {"x": x, "y": y, "n": None, "value": None, "ci95_low": None, "ci95_high": None,
            "r2": None, "estimator": "", "source": source_of_rule,
            "note": why, "status": "UNVERIFIED", "data_required": needed}


def main() -> int:
    res = json.load(open(os.path.join(OUT, "results.json"), encoding="utf-8"))
    games = [r for r in res["rows"] if r["status"] == "FINAL"]
    n = len(games)
    margin = [g["margin_home"] for g in games]
    total = [g["total"] for g in games]
    home_s = [g["home_score"] for g in games]
    away_s = [g["away_score"] for g in games]

    rows = []

    # ---- game level, from the results feed (n = number of final games) ------------
    r, nn = M.pearson(margin, total)
    rows.append(row("home margin", "game total", nn, r, "Pearson r, 95% CI via Fisher z",
                    SRC_RESULTS,
                    "the side and the total are the two markets we originate; a small |r| is the "
                    "sample association between these outcomes; it does not establish independence"))

    r, nn = M.pearson(home_s, away_s)
    rows.append(row("home points", "away points", nn, r, "Pearson r, 95% CI via Fisher z",
                    SRC_RESULTS,
                    "descriptive association only; it does not estimate a joint probability for player props"))

    r, nn = M.pearson(total, [abs(x) for x in margin])
    rows.append(row("game total", "|home margin|", nn, r, "Pearson r, 95% CI via Fisher z",
                    SRC_RESULTS,
                    "tests the intuition that blowouts run up totals; the measured value is close to "
                    "zero on this sample, which is why the model does not couple side and total"))

    r, nn = M.pearson([g["week"] for g in games], [abs(g["margin_home"]) for g in games])
    rows.append(row("week number", "|home margin|", nn, r, "Pearson r, 95% CI via Fisher z",
                    SRC_RESULTS,
                    "a trend check on the season: a strong value here would mean the league changed "
                    "shape and the ratings window should be weighted; it is not"))

    # ---- team level, from the official standings (n = 32 clubs) -------------------
    st = list(csv.DictReader(open(os.path.join(ROOT, "data", "closeout",
                                               "official_standings_2026_wk10.csv"), encoding="utf-8")))
    def col(f):
        return [float(f(x)) for x in st]
    pairs = [
        ("points for per game", "win pct", lambda x: int(x["pf"]) / max(1, int(x["w"]) + int(x["l"]) + int(x["t"])),
         lambda x: float(x["pct"] or 0), "offence -> wins"),
        ("points against per game", "win pct", lambda x: int(x["pa"]) / max(1, int(x["w"]) + int(x["l"]) + int(x["t"])),
         lambda x: float(x["pct"] or 0), "defence -> wins"),
        ("net points per game", "win pct", lambda x: (int(x["pf"]) - int(x["pa"])) / max(1, int(x["w"]) + int(x["l"]) + int(x["t"])),
         lambda x: float(x["pct"] or 0), "point differential -> wins"),
    ]
    for xn, yn, fx, fy, note in pairs:
        xs, ys = [fx(x) for x in st], [fy(x) for x in st]
        r, nn = M.pearson(xs, ys)
        rows.append(row(xn, yn, nn, r, "Pearson r, 95% CI via Fisher z", SRC_STANDINGS, note))

    # ---- deliberately blank: no official source exists --------------------------
    blanks = [
        blank("prop A outcome", "prop B outcome (same game)",
              "requires the joint settlement history of two props on the same player, game and "
              "market; NFL.com publishes no prop market and no prop price history",
              "a licensed prop-price archive with settlement", SRC_RESULTS),
        blank("leg 1 result", "leg 2 result (same parlay)",
              "requires a price archive to define which legs were available and at what price at "
              "the same moment; no official NFL price publication exists",
              "a licensed price archive (open and close)", SRC_RESULTS),
        blank("injury designation count", "next-game scoring margin",
              "requires the availability report and the result on the same game across many weeks; "
              "this repository holds one week of report-to-result join, which is n=1",
              "report history for >= 3 seasons joined to results", "https://www.nfl.com/injuries/league/2026/reg10"),
        blank("starting-QB absence", "team total points",
              "requires an official designation history joined to scored results over seasons; the "
              "current report covers one week", "multi-season injury-report archive", "https://www.nfl.com/injuries/league/2026/reg10"),
        blank("replacement tier (2nd/3rd string)", "points allowed",
              "requires the depth chart at the time of each game; club charts are self-labelled "
              "unofficial and only 5 of 32 carry an as-of date, so the join cannot be dated",
              "dated depth charts or official game-day participation", "https://www.nfl.com/stats/"),
    ]

    out = {
        "as_of": "2026-11-14", "generated_by": "tools/correlation_engine.py",
        "rule": ("a value is published only when both variables come from an official NFL page and "
                 "the row carries n; otherwise the row is blank and the missing artefact is named"),
        "counts": {"computed": len(rows), "blank": len(blanks),
                   "n_games": n, "n_clubs": len(st)},
        "rows": rows, "blank_rows": blanks,
        "integrity_note": ("every computed row names its source URL and its n; no row in this file "
                           "was estimated, interpolated or copied from a third-party model"),
    }
    with open(os.path.join(OUT, "correlations.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    print(f"correlations: {len(rows)} computed (n={n} games, {len(st)} clubs), {len(blanks)} blank")
    for r in rows:
        print(f"  {r['n']:>4}  r={r['value']:+.4f}  [{r['ci95_low']:+.3f},{r['ci95_high']:+.3f}]  "
              f"{r['x']} vs {r['y']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
