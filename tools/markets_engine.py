#!/usr/bin/env python3
"""
X3 / market engine: originate the side, then the total, then the moneyline; keep an
append-only price snapshot store with an opening and a closing number for every market
we originate; and publish fair line, market line and difference as three separate
fields.

Origination order is the requirement, and it is also the order the arithmetic allows:

  1. SIDE      -- a margin model on final scores (walk-forward) gives our handicap.
  2. TOTAL     -- a separate pace model on the same finals gives our total. It is fitted
                  second because it is the weaker model: r(margin, total) is small
                  (published on the correlation page with its n), so the total cannot
                  borrow evidence from the side.
  3. MONEYLINE -- derived last, from the SIDE model's margin distribution:
                  P(home win) = Phi(margin / sigma), sigma = walk-forward residual sd.
                  A moneyline is a side with the handicap removed, so it inherits the
                  side's error; it is never priced from an independent guess.

Price snapshot store (requirement 2 of the brief):

  data/x3/verified/snapshots/<date>.json   one file per capture run, append-only
  data/x3/verified/price_store.csv         the flattened store: one row per market per snapshot

Definitions, fixed here and used everywhere:

  OPEN  for a played game   = our number fitted on finals from WEEKS BEFORE the game's
                              week (what we would have published on the Tuesday).
  CLOSE for a played game   = our number fitted on every final whose date is strictly
                              before that game's kickoff date (i.e. the last number we
                              could have published before kickoff). Identical to OPEN
                              unless an earlier game in the same week moved the ratings.
  OPEN  for an unplayed game = our number fitted on all finals available now.
  CLOSE for an unplayed game = PENDING. It does not exist yet and is never imputed.

  MARKET open/close         = BLANK. NFL.com publishes no prices anywhere: the game
                              centre for LAC@BAL week 10 (checked 2026-11-14) carries
                              participation, team stats and standings, and no odds. Every
                              market cell is therefore blank and flagged, and the
                              difference column says so instead of inventing a number.

Run: python3 tools/markets_engine.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from results_feed import norm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import x3_model as M  # noqa: E402

OUT = os.path.join(ROOT, "data", "x3", "verified")
AS_OF = "2026-11-14"
WEEK = 10
SIGMA_FLOOR = 10.0          # never price a market with an unrealistically tight sigma
MIN_TRAIN = 32              # two complete weeks of finals before a game may be scored

SRC_RESULTS = "https://www.nfl.com/schedules/2026/by-week/week-{w}"
SRC_STANDINGS = "https://www.nfl.com/standings/league/2026/REG"
SRC_INJ = "https://www.nfl.com/injuries/league/2026/reg{w}"
SRC_GAME = "https://www.nfl.com/games/{slug}-2026-reg-{w}"

# Total weight applied to a designation when counting how much of a lineup is missing.
# A PRIOR, stated in the open, not a measurement (no market or fitted cost exists yet).
DESIG_W = {"Out": 1.0, "Doubtful": 0.75, "Questionable": 0.25, "": 0.0}

SLUG = {"AZ": "cardinals", "ATL": "falcons", "BAL": "ravens", "BUF": "bills", "CAR": "panthers",
        "CHI": "bears", "CIN": "bengals", "CLE": "browns", "DAL": "cowboys", "DEN": "broncos",
        "DET": "lions", "GB": "packers", "HOU": "texans", "IND": "colts", "JAX": "jaguars",
        "KC": "chiefs", "LAC": "chargers", "LAR": "rams", "LV": "raiders", "MIA": "dolphins",
        "MIN": "vikings", "NE": "patriots", "NO": "saints", "NYG": "giants", "NYJ": "jets",
        "PHI": "eagles", "PIT": "steelers", "SEA": "seahawks", "SF": "49ers", "TB": "buccaneers",
        "TEN": "titans", "WAS": "commanders"}


def r2(x):
    return None if x is None else round(x, 2)


def games_from_feed():
    d = json.load(open(os.path.join(OUT, "results.json"), encoding="utf-8"))
    # This vintage is a fixed historical experiment, not the settlement feed.
    # Preserve the actual original capture state (including the early Week 10 final).
    with open(os.path.join(ROOT, "data", "desk", "games.json"), encoding="utf-8") as f:
        vintage = {(r["week"], r["date_iso"], norm(r["away"]),
                    norm(r["home"])): r["status"]
                   for r in json.load(f)["games"]}
    out = []
    for r in d["rows"]:
        status = vintage[(r["week"], r["date_iso"], r["away"], r["home"])]
        out.append({"game_id": r["game_id"], "week": r["week"], "date_iso": r["date_iso"],
                    "home": r["home"], "away": r["away"], "neutral_site": r["neutral_site"],
                    "status": status, "home_score": r["home_score"] if status == "FINAL" else "",
                    "away_score": r["away_score"] if status == "FINAL" else "", "venue": r["venue"]})
    return out


def walk_forward(games):
    """Fit on every final before each game's week; score only games not yet fitted on."""
    finals = [g for g in games if g["status"] == "FINAL"]
    by_week = {}
    for g in finals:
        by_week.setdefault(g["week"], []).append(g)
    preds, residuals, errs_m, errs_t = [], [], [], []
    for w in sorted(by_week):
        train = [g for g in finals if g["week"] < w]
        if len(train) < MIN_TRAIN:
            continue  # fewer than two complete weeks of finals: no number is published
        R = M.fit(train)
        for g in by_week[w]:
            if g["home"] not in R["net"] or g["away"] not in R["net"]:
                continue  # club absent from the training window (cannot happen mid-season)
            pm, pt = M.predict(R, g["home"], g["away"], g["neutral_site"])
            actual_m = g["home_score"] - g["away_score"]
            actual_t = g["home_score"] + g["away_score"]
            preds.append({"game_id": g["game_id"], "week": w, "date_iso": g["date_iso"],
                          "home": g["home"], "away": g["away"],
                          "pred_margin": round(pm, 2), "pred_total": round(pt, 2),
                          "actual_margin": actual_m, "actual_total": actual_t,
                          "err_margin": round(pm - actual_m, 2), "err_total": round(pt - actual_t, 2),
                          "source": SRC_RESULTS.format(w=w)})
            residuals.append(pm - actual_m)
            errs_m.append(abs(pm - actual_m))
            errs_t.append(abs(pt - actual_t))
    return preds, residuals, errs_m, errs_t


def metrics(preds):
    if not preds:
        return {}
    em = [p["err_margin"] for p in preds]
    et = [p["err_total"] for p in preds]
    am = [p["actual_margin"] for p in preds]
    pm = [p["pred_margin"] for p in preds]
    r_m, n = M.pearson(pm, am)
    lo, hi = M.fisher_ci(r_m, n)
    # naive baselines named in gate G-4: a fixed home -2.5 and a fixed total of 45.0
    base_m = [-2.5] * n
    base_t = [45.0] * n
    # moneyline: model probability vs the base rate of home wins in this sample
    hit = sum(1 for p in preds if (p["pred_margin"] > 0) == (p["actual_margin"] > 0))
    ties = sum(1 for p in preds if p["actual_margin"] == 0)
    home_rate = (sum(1 for a in am if a > 0) + 0.5 * sum(1 for a in am if a == 0)) / n
    return {
        "n": n,
        "mae_margin": round(M.mean([abs(x) for x in em]), 2),
        "rmse_margin": round(math.sqrt(M.mean([x * x for x in em])), 2),
        "bias_margin": round(M.mean(em), 2),
        "mae_total": round(M.mean([abs(x) for x in et]), 2),
        "rmse_total": round(math.sqrt(M.mean([x * x for x in et])), 2),
        "bias_total": round(M.mean(et), 2),
        "r_pred_actual_margin": None if r_m is None else round(r_m, 4),
        "r_ci95": [None if lo is None else round(lo, 4), None if hi is None else round(hi, 4)],
        "mae_margin_naive_-2.5": round(M.mean([abs(b - a) for b, a in zip(base_m, am)]), 2),
        "mae_total_naive_45.0": round(M.mean([abs(b - a) for b, a in zip(base_t,
                                                                        [p["actual_total"] for p in preds])]), 2),
        "side_direction_hit": hit, "side_direction_rate": round(hit / n, 4),
        "ties": ties, "home_win_rate_in_sample": round(home_rate, 4),
    }


def build():
    games = games_from_feed()
    finals = [g for g in games if g["status"] == "FINAL"]
    unplayed = [g for g in games if g["status"] != "FINAL"]
    preds, residuals, _, _ = walk_forward(games)
    mets = metrics(preds)

    sigma = M.sd(residuals) if len(residuals) > 2 else None
    if sigma is None:
        raise SystemExit("cannot price: not enough walk-forward residuals to estimate sigma")
    sigma = max(sigma, SIGMA_FLOOR)
    mets["sigma_margin"] = round(sigma, 3)
    mets["sigma_note"] = ("sd of walk-forward margin residuals; used only to turn a margin into a "
                          "win probability and a cover probability")

    # workbook for the price store
    store_rows = []

    def push(game_id, week, market, side, lo, po, lc, pc, status, source, note=""):
        store_rows.append({
            "market_id": f"{game_id}:{market}:{side}",
            "game_id": game_id, "week": week, "market": market, "side": side,
            "open_line": "" if lo is None else lo,
            "open_price_decimal": "" if po is None else po,
            "open_price_american": "" if po is None else M.american_from_decimal(po),
            "close_line": "" if lc is None else lc,
            "close_price_decimal": "" if pc is None else pc,
            "close_price_american": "" if pc is None else M.american_from_decimal(pc),
            "movement_points": (round(lc - lo, 2)
                                if isinstance(lc, (int, float)) and isinstance(lo, (int, float))
                                else ""),
            "close_status": status,
            "market_open": "", "market_close": "", "market_source": "",
            "verification": "DERIVED (our own number, no market price exists - F-01)",
            "source": source, "note": note,
        })

    # ---------------------------------------------------------------- played games
    # open/close pairs computed from two chronological fits, as defined in the header.
    chronology = []
    for w in sorted({g["week"] for g in finals}):
        for g in sorted([x for x in finals if x["week"] == w], key=lambda x: x["date_iso"]):
            train_open = [x for x in finals if x["week"] < w]
            train_close = [x for x in finals if x["date_iso"] < g["date_iso"]]
            rec = {"game": g, "open": None, "close": None}
            if len(train_open) >= MIN_TRAIN:
                rec["open"] = M.fit(train_open)
            if len(train_close) >= MIN_TRAIN:
                rec["close"] = M.fit(train_close)
            chronology.append(rec)

    backtest_market_rows = []
    for rec in chronology:
        g = rec["game"]
        if rec["open"] is None:
            continue
        o = rec["open"]
        c = rec["close"] or o
        om, ot = M.predict(o, g["home"], g["away"], g["neutral_site"])
        cm, ct = M.predict(c, g["home"], g["away"], g["neutral_site"])
        # SIDE: we publish the home handicap as a half-point number
        o_line = round(-om * 2) / 2
        c_line = round(-cm * 2) / 2
        o_p = M.norm_cdf((om - (-o_line)) / sigma)
        c_p = M.norm_cdf((cm - (-c_line)) / sigma)
        push(g["game_id"], g["week"], "side", "home", o_line, r4(M.fair_price_decimal(o_p)),
             c_line, r4(M.fair_price_decimal(c_p)), "RECORDED", SRC_RESULTS.format(w=g["week"]),
             "handicap, home side; price is the fair (zero-hold) price at that handicap")
        push(g["game_id"], g["week"], "side", "away", -o_line, r4(M.fair_price_decimal(1 - o_p)),
             -c_line, r4(M.fair_price_decimal(1 - c_p)), "RECORDED",
             SRC_RESULTS.format(w=g["week"]), "handicap, away side")
        # TOTAL
        o_t = round(ot * 2) / 2
        c_t = round(ct * 2) / 2
        o_po = M.norm_cdf((ot - o_t) / sigma)
        c_po = M.norm_cdf((ct - c_t) / sigma)
        push(g["game_id"], g["week"], "total", "over", o_t, r4(M.fair_price_decimal(o_po)),
             c_t, r4(M.fair_price_decimal(c_po)), "RECORDED", SRC_RESULTS.format(w=g["week"]),
             "total, over side")
        push(g["game_id"], g["week"], "total", "under", o_t, r4(M.fair_price_decimal(1 - o_po)),
             c_t, r4(M.fair_price_decimal(1 - c_po)), "RECORDED", SRC_RESULTS.format(w=g["week"]),
             "total, under side")
        # MONEYLINE (priced last, from the side model)
        op_h = M.fair_probability(om, sigma)
        cp_h = M.fair_probability(cm, sigma)
        push(g["game_id"], g["week"], "moneyline", "home", "", r4(M.fair_price_decimal(op_h)),
             "", r4(M.fair_price_decimal(cp_h)), "RECORDED", SRC_RESULTS.format(w=g["week"]),
             "no handicap on a moneyline; price from the same margin model, opposite sign")
        push(g["game_id"], g["week"], "moneyline", "away", "", r4(M.fair_price_decimal(1 - op_h)),
             "", r4(M.fair_price_decimal(1 - cp_h)), "RECORDED", SRC_RESULTS.format(w=g["week"]),
             "no handicap on a moneyline")
        backtest_market_rows.append({
            "game_id": g["game_id"], "week": g["week"], "home": g["home"], "away": g["away"],
            "pred_margin": round(om, 2), "actual_margin": g["home_score"] - g["away_score"],
            "side_open": o_line, "side_close": c_line,
            "total_open": o_t, "total_close": c_t,
            "covered": ("home" if (g["home_score"] - g["away_score"]) + o_line > 0 else
                        ("away" if (g["home_score"] - g["away_score"]) + o_line < 0 else "push")),
            "total_landed": ("over" if (g["home_score"] + g["away_score"]) > o_t else
                             ("under" if (g["home_score"] + g["away_score"]) < o_t else "push")),
            "source": SRC_RESULTS.format(w=g["week"]),
        })

    # ---------------------------------------------------------------- the live slate
    R_now = M.fit(finals)
    live_rows = []
    for g in sorted(unplayed, key=lambda x: (x["date_iso"], x["game_id"])):
        if g["home"] not in R_now["net"] or g["away"] not in R_now["net"]:
            continue
        margin, total = M.predict(R_now, g["home"], g["away"], g["neutral_site"])
        # 1. SIDE
        side_line = round(-margin * 2) / 2
        p_home_cover = M.norm_cdf((margin - (-side_line)) / sigma)
        # 2. TOTAL
        tot_line = round(total * 2) / 2
        p_over = M.norm_cdf((total - tot_line) / sigma)
        # 3. MONEYLINE
        p_home_win = M.fair_probability(margin, sigma)
        live_rows.append({
            "game_id": g["game_id"], "week": g["week"], "date_iso": g["date_iso"],
            "home": g["home"], "away": g["away"], "neutral_site": g["neutral_site"],
            "margin_model": round(margin, 2), "total_model": round(total, 2),
            "side_fair_line": side_line,
            "side_fair_price_home": r4(M.fair_price_decimal(p_home_cover)),
            "side_fair_price_away": r4(M.fair_price_decimal(1 - p_home_cover)),
            "side_cover_prob_home": round(p_home_cover, 4),
            "total_fair_line": tot_line,
            "total_fair_price_over": r4(M.fair_price_decimal(p_over)),
            "total_fair_price_under": r4(M.fair_price_decimal(1 - p_over)),
            "total_over_prob": round(p_over, 4),
            "ml_fair_home": r4(M.fair_price_decimal(p_home_win)),
            "ml_fair_away": r4(M.fair_price_decimal(1 - p_home_win)),
            "ml_home_prob": round(p_home_win, 4),
            "ml_fair_american_home": M.american_from_decimal(M.fair_price_decimal(p_home_win)),
            "ml_fair_american_away": M.american_from_decimal(M.fair_price_decimal(1 - p_home_win)),
            "market_side": "", "market_total": "", "market_ml_home": "", "market_ml_away": "",
            "market_source": "",
            "diff_side_points": "", "diff_total_points": "", "diff_ml_prob_home": "",
            "source_results": SRC_RESULTS.format(w=g["week"]),
            "source_game_page": SRC_GAME.format(
                slug=f"{SLUG.get(g['away'], '').lower()}-at-{SLUG.get(g['home'], '').lower()}",
                w=g["week"]),
            "origination_order": "1 side, 2 total, 3 moneyline",
        })
        push(g["game_id"], g["week"], "side", "home", side_line,
             r4(M.fair_price_decimal(p_home_cover)), None, None, "PENDING",
             SRC_RESULTS.format(w=g["week"]), "closing number does not exist yet; never imputed")
        push(g["game_id"], g["week"], "side", "away", -side_line,
             r4(M.fair_price_decimal(1 - p_home_cover)), None, None, "PENDING",
             SRC_RESULTS.format(w=g["week"]), "closing number does not exist yet")
        push(g["game_id"], g["week"], "total", "over", tot_line,
             r4(M.fair_price_decimal(p_over)), None, None, "PENDING",
             SRC_RESULTS.format(w=g["week"]), "closing number does not exist yet")
        push(g["game_id"], g["week"], "total", "under", tot_line,
             r4(M.fair_price_decimal(1 - p_over)), None, None, "PENDING",
             SRC_RESULTS.format(w=g["week"]), "closing number does not exist yet")
        push(g["game_id"], g["week"], "moneyline", "home", "",
             r4(M.fair_price_decimal(p_home_win)), None, None, "PENDING",
             SRC_RESULTS.format(w=g["week"]), "closing number does not exist yet")
        push(g["game_id"], g["week"], "moneyline", "away", "",
             r4(M.fair_price_decimal(1 - p_home_win)), None, None, "PENDING",
             SRC_RESULTS.format(w=g["week"]), "closing number does not exist yet")

    # market line / difference: one row per live game per market, three separate columns
    market_rows = []
    for r in live_rows:
        for market, fair, mkt, diff, unit in (
                ("side (home handicap)", r["side_fair_line"], "", "", "points"),
                ("total", r["total_fair_line"], "", "", "points"),
                ("moneyline (home)", r["ml_fair_american_home"], "", "", "American odds")):
            market_rows.append({
                "game_id": r["game_id"], "market": market,
                "fair_line": fair, "market_line": mkt, "difference": diff,
                "unit": unit,
                "market_status": "UNVERIFIED - no official market price exists (F-01)",
                "source_fair": r["source_results"],
            })

    # ---------------------------------------------------------------- the snapshot file
    snap_dir = os.path.join(OUT, "snapshots")
    os.makedirs(snap_dir, exist_ok=True)
    snapshot = {
        "snapshot_date": AS_OF,
        "model": "X3-v2 (walk-forward net/pace on 2026 finals, sigma from residuals)",
        "sigma_margin": round(sigma, 3),
        "markets_recorded": len(store_rows),
        "closing_pending": sum(1 for r in store_rows if r["close_status"] == "PENDING"),
        "closing_recorded": sum(1 for r in store_rows if r["close_status"] == "RECORDED"),
        "rows": store_rows,
    }
    snap_path = os.path.join(snap_dir, f"{AS_OF}.json")
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=1)

    cols = ["market_id", "game_id", "week", "market", "side", "open_line", "open_price_decimal",
            "open_price_american", "close_line", "close_price_decimal", "close_price_american",
            "movement_points", "close_status", "market_open", "market_close", "market_source",
            "verification", "source", "note"]
    with open(os.path.join(OUT, "price_store.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(store_rows)

    # movement statistics on the markets we can see both ends of (our own number only)
    mov = [r["movement_points"] for r in store_rows
           if isinstance(r["movement_points"], (int, float)) and r["market"] != "moneyline"]
    movement_summary = {
        "pairs_recorded": len(mov),
        "mean_abs_movement_points": r4(M.mean([abs(x) for x in mov])) if mov else None,
        "max_abs_movement_points": max((abs(x) for x in mov), default=None),
        "moved": sum(1 for x in mov if abs(x) > 1e-9),
        "note": ("our own number's open->close movement. It is not market movement: no market "
                 "price exists in this repository. Every market_* column is blank and flagged."),
    }

    out = {
        "as_of": AS_OF, "week": WEEK, "generated_by": "tools/markets_engine.py",
        "origination_order": ["side", "total", "moneyline"],
        "model": {"name": "X3-v2", "fitted_on": "2026 finals from the verified results feed",
                  "hfa_points": round(R_now["hfa"], 3),
                  "league_avg_team_score": round(R_now["base_total"] / 2, 3),
                  "n_games": R_now["n_games"],
                  "identified": "the margin model identifies net[home]-net[away] only"},
        "sigma_margin": round(sigma, 3),
        "backtest": mets,
        "live": live_rows,
        "market_rows": market_rows,
        "store": {
            "snapshot_files": [f"{AS_OF}.json"],
            "snapshots_written": 1,
            "markets": len(store_rows),
            "closing_pending": snapshot["closing_pending"],
            "closing_recorded": snapshot["closing_recorded"],
            "movement": movement_summary,
            "definition": ("open = fit on weeks before the game's week; close = fit on every final "
                           "dated before that game's kickoff. For a played game both exist; for an "
                           "unplayed game the close is PENDING and stays blank."),
        },
        "backtest_markets": backtest_market_rows,
        "sources": {"results": "https://www.nfl.com/schedules/2026/by-week/week-N",
                    "standings": SRC_STANDINGS,
                    "market_probe": SRC_GAME.format(slug="chargers-at-ravens", w=10),
                    "market_probe_finding": ("the official game centre for LAC@BAL week 10 shows "
                                             "participation, team stats and standings; it publishes "
                                             "no odds, spread, total or moneyline")},
        "limits": [
            "Every market column is blank: no official NFL price publication exists (verified "
            "2026-11-14 on the LAC@BAL game centre).",
            "One season of results, so sigma and the ratings are fitted on at most 137 games.",
            "The moneyline inherits the side model's error by construction.",
        ],
    }
    with open(os.path.join(OUT, "markets.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(OUT, "backtest_games.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["game_id", "week", "home", "away", "pred_margin",
                                          "actual_margin", "side_open", "side_close", "total_open",
                                          "total_close", "covered", "total_landed", "source"])
        w.writeheader()
        w.writerows(backtest_market_rows)

    print(f"live slate: {len(live_rows)} games x 3 markets; store rows {len(store_rows)} "
          f"({snapshot['closing_recorded']} with a close, {snapshot['closing_pending']} pending)")
    print(f"walk-forward: n={mets['n']} MAE(margin)={mets['mae_margin']} vs naive "
          f"{mets['mae_margin_naive_-2.5']}; MAE(total)={mets['mae_total']} vs naive "
          f"{mets['mae_total_naive_45.0']}; sigma={mets['sigma_margin']}")
    return out


def r4(x):
    return None if x is None else round(x, 4)


if __name__ == "__main__":
    build()
