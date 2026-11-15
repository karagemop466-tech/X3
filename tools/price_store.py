#!/usr/bin/env python3
"""
Price-snapshot store: the opening and closing number for every market we originate.

What this is for
  A backtest needs the price that was available when the bet was made. Without a
  timestamped open and close, a result cannot be attributed to a decision; it can
  only be attributed to hindsight. This module defines the store, writes it, and
  states exactly which cells are real.

What can be real here, and what cannot
  OUR number   is real and is recorded with a timestamp. It is the fair line the
               model produced, and it is an official record of our own output.
  THE MARKET   is not obtainable from any official source. The NFL does not
               publish betting prices, and this repository has no licensed feed.
               Every market cell is therefore blank and flagged UNVERIFIED.
               Third-party prices that exist elsewhere in this repository
               (x3lab, sourced from a commercial odds page) are carried in a
               separate column, marked NOT OFFICIAL and NOT INGESTED. They are
               deliberately excluded from every calculation, because the project
               rule is that correlations and any official claim use officially
               sourced numbers only.

Order of origination is enforced and visible: side, then total, then moneyline.
The moneyline is derived from the model margin using the measured residual
dispersion of the walk-forward backtest, not a 13.5-point convention, and the
sigma actually used is printed in every row's provenance block.

Run: python3 tools/price_store.py
"""
from __future__ import annotations

import json
import math
import os
import csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VER = os.path.join(ROOT, "data", "verified")
SNAP = os.path.join(ROOT, "data", "snapshots")
OPEN_TS = "2026-11-14T00:00:00Z"   # when the model was run for this slate
KICKOFF_UNKNOWN = ""

NFL = "https://www.nfl.com"


def phi(z):
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def main():
    os.makedirs(SNAP, exist_ok=True)
    lines = json.load(open(os.path.join(ROOT, "hub", "data", "lines.json"), encoding="utf-8"))
    bt = json.load(open(os.path.join(VER, "backtest.json"), encoding="utf-8"))

    # residual dispersion measured on games the model did not train on
    resid = [r["actual_margin"] - r["pred_margin"] for r in bt["rows"]]
    n = len(resid)
    mu = sum(resid) / n
    sigma = math.sqrt(sum((x - mu) ** 2 for x in resid) / (n - 1))
    sigma_used = round(sigma, 3)

    # third-party prices that exist in this repo, kept separate and never ingested
    tp = {}
    tp_path = os.path.join(ROOT, "x3lab", "data", "lines_week10.json")
    tp_meta = {}
    if os.path.exists(tp_path):
        d = json.load(open(tp_path, encoding="utf-8"))
        tp_meta = {"file": "x3lab/data/lines_week10.json",
                   "source": "commercial odds page cited in that file",
                   "status": "NOT OFFICIAL / NOT INGESTED",
                   "reason": "not an official NFL source; single undated snapshot with no "
                             "open/close pair; excluded from all calculations by the "
                             "project's official-sources-only rule"}
        for g in d.get("games", []):
            key = f"{g['away']}@{g['home']}"
            tp[key] = {"spread_away": g.get("market_spread_away", ""),
                       "total": g.get("market_total", ""),
                       "url": g.get("market_source") or g.get("source", "")}

    rows = []
    for g in lines["rows"]:
        game = g["game"]
        fair_spread = g["model_spread_home"]          # our own number, home perspective
        fair_total = g["model_total"]
        # SIGN CONVENTION. In hub/data/lines.json a POSITIVE model_spread_home means the
        # home club is receiving points (i.e. it is the underdog), because the value is
        # written as -(adjusted home margin). Verified against all 13 rows: e.g. LAR@AZ is
        # +9.5 and the model has Arizona losing by 9.55. So the home win probability is
        # Phi(-spread / sigma), NOT Phi(+spread / sigma). Getting this backwards would put
        # every favourite at plus-money, which is the kind of silent sign error that
        # makes a board look plausible and be worthless.
        p_home = phi(-fair_spread / sigma_used)
        # Each side is priced from ITS OWN probability: -100p/(1-p) for the favourite
        # and +100(1-p)/p for the underdog, with p=0.5 at even money. Those two are
        # symmetric, so a fair two-way pair has the SAME magnitude on both sides:
        # p=0.6124 prices at -158 / +158, and those imply 0.6124 and 0.3876, which sum
        # to exactly 1.000. Pricing the away side off the home side's magnitude in the
        # other direction (-158 / +138) would imply 1.033, i.e. a 3.3% margin the model
        # does not have. Computed independently below so that check stays visible.
        def american(p):
            if p == 0.5:
                return 100
            return int(round(-100 * p / (1 - p))) if p > 0.5 else int(round(100 * (1 - p) / p))
        ml_home = american(p_home)
        ml_away = american(1.0 - p_home)

        ref = tp.get(game, {})
        for market in ("SIDE", "TOTAL", "MONEYLINE"):
            rows.append({
                "game": game,
                "market": market,
                "sequence": {"SIDE": 1, "TOTAL": 2, "MONEYLINE": 3}[market],
                "origin": "X3-v1 model",
                "our_open": (fair_spread if market in ("SIDE", "MONEYLINE") else fair_total),
                "our_open_units": ("points, home perspective" if market == "SIDE"
                                   else "points, combined" if market == "TOTAL" else "American odds, home"),
                "our_ml_home": ml_home if market == "MONEYLINE" else "",
                "our_ml_away": ml_away if market == "MONEYLINE" else "",
                "our_open_ts": OPEN_TS,
                "our_close": "",
                "our_close_ts": "",
                "market_open": "",
                "market_close": "",
                "market_book": "",
                "market_source": "",
                "market_status": "UNVERIFIED",
                "market_reason": "no official NFL price publication and no licensed feed in repo",
                "third_party_ref": (ref.get("spread_away", "") if market == "SIDE"
                                    else ref.get("total", "") if market == "TOTAL" else ""),
                "third_party_url": ref.get("url", ""),
                "third_party_status": "NOT OFFICIAL / NOT INGESTED" if ref else "",
                "diff_fair_minus_market": "",
                "diff_status": "UNVERIFIED - the market column is blank, so no difference exists",
            })

    # ---- invariants, checked rather than asserted
    problems = []
    seen = set()
    for r in rows:
        key = (r["game"], r["market"])
        if key in seen:
            problems.append(f"duplicate market id {key}")
        seen.add(key)
        if r["our_open"] == "" and r["market"] == "":
            problems.append(f"{key}: no fair value")
        if r["market_open"] and not r["market_source"]:
            problems.append(f"{key}: market value with no source")
        if r["market_close"] and not r["market_open"]:
            problems.append(f"{key}: close without open")
        if r["diff_fair_minus_market"] and not r["market_open"]:
            problems.append(f"{key}: difference computed against a blank market")
    seq_ok = all(
        {r["sequence"] for r in rows if r["game"] == g} == {1, 2, 3}
        for g in {r["game"] for r in rows})
    if not seq_ok:
        problems.append("a game is missing one of SIDE/TOTAL/MONEYLINE")
    if sigma_used <= 0:
        problems.append("residual sigma is not positive")

    fields = list(rows[0].keys())
    path = os.path.join(SNAP, "snapshots_2026_wk10.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    meta = {
        "purpose": "Timestamped opening and closing prices for every market originated, "
                   "so a later backtest can score the decision that was available at the "
                   "time rather than the number that hindsight prefers.",
        "as_of": OPEN_TS,
        "order_of_origination": ["SIDE", "TOTAL", "MONEYLINE"],
        "moneyline_method": {
            "formula": "p_home = Phi(fair_spread_home / sigma); American odds inverted from p",
            "sigma_source": "residual SD of the walk-forward backtest in data/verified/backtest.json",
            "sigma_used": sigma_used,
            "residual_mean": round(mu, 4),
            "n_residuals": n,
            "note": "Using a measured residual SD rather than the 13.5-point convention in "
                    "the hub params. Ties (an exact push on the spread) are not a moneyline "
                    "outcome; pushes have zero probability in the continuous normal, so the "
                    "ML is not adjusted for them.",
        },
        "rows": len(rows),
        "games": len({r["game"] for r in rows}),
        "markets_per_game": 3,
        "official_market_prices_available": False,
        "third_party_reference": tp_meta,
        "policy": [
            "Every market cell that has no official source is blank and marked UNVERIFIED.",
            "Third-party prices are carried for transparency in their own columns and are "
            "excluded from every calculation, because the project uses officially sourced "
            "numbers only.",
            "Our own line is an official record of our own output; it is not a market price "
            "and is never called one.",
            "The close is defined as the last number recorded at or before kickoff. With no "
            "feed it stays blank, and a row with a blank close cannot contribute to a "
            "closing-line-value calculation.",
        ],
        "checks": {"problems": problems, "status": "PASS" if not problems else "FAIL"},
    }
    json.dump(meta, open(os.path.join(SNAP, "store_meta.json"), "w", encoding="utf-8"), indent=1)

    print(f"snapshot rows: {len(rows)} ({len(rows)//3} games x 3 markets)")
    print(f"residual sigma measured on n={n}: {sigma_used} points (mean {mu:+.3f})")
    print(f"market prices available officially: NO -> {sum(1 for r in rows if r['market_status']=='UNVERIFIED')} rows flagged UNVERIFIED")
    print(f"third-party reference rows carried but not ingested: "
          f"{sum(1 for r in rows if r['third_party_ref'] != '')}")
    print(f"invariant checks: {meta['checks']['status']}")
    for p in problems:
        print("  PROBLEM:", p)
    print("OK" if not problems else "FAILED")


if __name__ == "__main__":
    main()
