#!/usr/bin/env python3
"""
The Week-10 board, originated in the required order: side, then total, then moneyline.

Everything on this sheet is DERIVED from verified inputs by arithmetic that is
printed beside it. Nothing is a recommendation to bet, and no market price exists
to compare against, so the "market" and "difference" columns are blank by design.

Two things this file adds that the existing hub board does not have:

  a key-number check
      A spread that sits on 3 or 7 pushes far more often than one that does not.
      The frequency is measured from the 137 verified finals, and every originated
      spread is checked against it. A line is flagged KEY if it lands on a margin
      that recurs, and the empirical push share is printed next to it.

  a pick sheet in the order the brief asks for
      SIDE first, because it is the market with the most information in the
      verified data; TOTAL second, because the model total cannot currently beat a
      constant; MONEYLINE last, because it is a monotone function of the side and
      adds no independent information - which is itself the finding.

Run: python3 tools/picks.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VER = os.path.join(ROOT, "data", "verified")
OUT = os.path.join(ROOT, "data", "picks")
SNAP = os.path.join(ROOT, "data", "snapshots")


def main():
    os.makedirs(OUT, exist_ok=True)
    lines = json.load(open(os.path.join(ROOT, "hub", "data", "lines.json"), encoding="utf-8"))
    kn = json.load(open(os.path.join(VER, "key_numbers.json"), encoding="utf-8"))
    snap_meta = json.load(open(os.path.join(SNAP, "store_meta.json"), encoding="utf-8"))
    sigma = snap_meta["moneyline_method"]["sigma_used"]
    by_margin = {r["margin"]: r for r in kn["by_margin"]}

    import math
    phi = lambda z: 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

    def ml_from_spread(spread_home):
        p = phi(-spread_home / sigma)
        return int(round(-100 * p / (1 - p))) if p >= 0.5 else int(round(100 * (1 - p) / p))

    picks = []
    for g in lines["rows"]:
        sp = g["model_spread_home"]
        abs_sp = abs(sp)
        key = abs_sp == round(abs_sp) and abs_sp in by_margin
        push_share = by_margin[int(abs_sp)]["share"] if key else 0.0
        if abs_sp in (3.0, 7.0):
            key_flag = "KEY NUMBER (3 or 7)"
        elif abs_sp <= 3:
            key_flag = "inside the 3-point cluster"
        elif key in by_margin and push_share > 0.01:
            key_flag = "elevated push share"
        else:
            key_flag = "not a key number"

        ml = ml_from_spread(sp)
        picks.append({
            "game": g["game"],
            "kickoff": g["date"] + " " + g["slot"],
            "neutral_site": bool(g["neutral_site"]),
            "order": ["SIDE", "TOTAL", "MONEYLINE"],
            "side": {
                "our_line": f"{g['home']} {sp:+.1f}" if sp != 0 else "pick'em",
                "number_home": sp,
                "favourite": g["home"] if sp < 0 else g["away"] if sp > 0 else "level",
                "key_number": key_flag,
                "empirical_push_share": round(push_share, 4),
                "basis": f"base {g['base_margin_home']:+.2f} + injury adj "
                         f"{g['injury_delta']:+.2f} = {g['adj_margin_home']:+.2f}",
            },
            "total": {
                "our_line": g["model_total"],
                "basis": "club scoring rates shrunk to the league mean; NOT better than a "
                         "constant on the backtest (Q-03)",
            },
            "moneyline": {
                "home": ml,
                "away": ml_from_spread(-sp),
                "basis": f"Phi(-spread / {sigma}); monotone in the spread, so it carries no "
                         f"independent signal",
            },
            "market_side": "", "market_total": "", "market_ml": "",
            "diff_side": "", "diff_total": "", "diff_ml": "",
            "market_status": "UNVERIFIED - no official price source exists",
            "signal_used": g["signal"],
        })

    key_count = sum(1 for p in picks if "KEY" in p["side"]["key_number"])
    out = {
        "as_of": "2026-11-14",
        "season": 2026,
        "week": 10,
        "source": ["https://www.nfl.com/schedules/2026/by-week/week-10",
                   "https://www.nfl.com/standings/league/2026/REG",
                   "https://www.nfl.com/injuries/league/2026/reg10"],
        "order_of_origination": ["SIDE", "TOTAL", "MONEYLINE"],
        "n_games": len(picks),
        "key_number_lines": key_count,
        "sigma_used_for_ml": sigma,
        "picks": picks,
        "columns_explained": {
            "our_line": "DERIVED - arithmetic on verified inputs, parameters printed in hub/data/meta.json",
            "market": "blank - no official NFL price publication and no licensed feed",
            "difference": "blank - a difference against a blank market would be a fabrication",
        },
        "disclaimer": "This is a research board, not a tip sheet. It originates numbers and "
                      "compares them to nothing, because no priced market exists in this "
                      "repository. No bet is placed and no reward is paid.",
    }
    json.dump(out, open(os.path.join(OUT, "picks_2026_wk10.json"), "w", encoding="utf-8"), indent=1)

    print(f"board: {len(picks)} games, side -> total -> moneyline")
    print(f"lines landing on a 3 or 7: {key_count}")
    for p in picks[:4]:
        print(f"  {p['game']:9} side {p['side']['our_line']:<12} "
              f"total {p['total']['our_line']:<5} ml {p['moneyline']['home']:+5d} "
              f"| {p['side']['key_number']}")
    print("OK")


if __name__ == "__main__":
    main()
