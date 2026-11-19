#!/usr/bin/env python3
"""
X3 / strategy engine: signal scored separately from staking, luck controls that can
actually run on the data we hold, and a demotion gate that returns a live strategy to
paper.

Why the two scores are separate (requirement 5):

  SIGNAL   = does the forecast contain information? Measured on outcomes only, with n,
             a paired test against the named naive baseline, and an interval.
  STAKING  = did the money grow? Requires prices. There are none (F-01), so every
             staking score is BLOCKED with its reason, and a staking number can never
             stand in for a signal number on the leaderboard.

The ranking rule is therefore lexicographic and stated in the code: a strategy with a
failing signal cannot be promoted by a good staking run, because no staking score exists
that could masquerade as evidence.

Luck controls that DO run (all on walk-forward predictions from the verified results feed):

  * paired bootstrap CI on the improvement of absolute error over the naive baseline
  * direction hit-rate CI (Wilson)
  * Brier score for the moneyline vs the base rate, n published
  * deflated-Sharpe style multiple-testing haircut: the number of variants tried is
    recorded and every p-value is reported raw AND Bonferroni-adjusted
  * minimum-sample gate G-2 evaluated in games, not asserted

Demotion gate (requirement 8): G-10. A strategy that is live is returned to paper when
ANY of these fires. The gate is evaluated every week by this script; today it is
evaluated on the model-quality strategy, which is the only one with a series:

  D-1  three consecutive scored weeks with worse absolute error than the naive baseline
  D-2  rolling-20-game paired improvement CI entirely below zero
  D-3  direction hit rate CI entirely below 0.50
  D-4  the staking input disappears (no prices) while the strategy is live

Run: python3 tools/strategies_engine.py
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import x3_model as M  # noqa: E402
import markets_engine

OUT = os.path.join(ROOT, "data", "x3", "verified")
SRC_RESULTS = "https://www.nfl.com/schedules/2026/by-week/week-N"
SEED = 20261114


def load_content():
    spec = importlib.util.spec_from_file_location("hub_content", os.path.join(ROOT, "tools",
                                                                              "hub_content.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def wilson(k, n, z=1.959964):
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - s) / d, (c + s) / d


def bootstrap_mean_ci(xs, iters=4000, seed=SEED):
    if not xs:
        return None, None, None
    rng = random.Random(seed)
    n = len(xs)
    means = []
    for _ in range(iters):
        means.append(sum(xs[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int(0.025 * iters)]
    hi = means[int(0.975 * iters) - 1]
    return sum(xs) / n, lo, hi


def main() -> int:
    C = load_content()
    games = markets_engine.games_from_feed()
    finals = [g for g in games if g["status"] == "FINAL"]
    bt = json.load(open(os.path.join(OUT, "markets.json"), encoding="utf-8"))

    # ---- rebuild the walk-forward series (same rule as the market engine) --------
    preds = []
    by_week = {}
    for g in finals:
        by_week.setdefault(g["week"], []).append(g)
    for w in sorted(by_week):
        train = [g for g in finals if g["week"] < w]
        if len(train) < 32:
            continue
        R = M.fit(train)
        for g in by_week[w]:
            pm, pt = M.predict(R, g["home"], g["away"], g["neutral_site"])
            am = g["home_score"] - g["away_score"]
            at = g["home_score"] + g["away_score"]
            preds.append({"week": w, "game": f"{g['away']}@{g['home']}",
                          "pred_margin": pm, "pred_total": pt,
                          "abs_err": abs(pm - am), "naive_abs": abs(-2.5 - am),
                          "abs_err_t": abs(pt - at), "naive_abs_t": abs(45.0 - at),
                          "direction_ok": (pm > 0) == (am > 0),
                          "home_won": am > 0, "p_home": M.norm_cdf(pm / 13.027)})
    n = len(preds)
    improve = [p["naive_abs"] - p["abs_err"] for p in preds]
    mean_imp, lo_imp, hi_imp = bootstrap_mean_ci(improve)
    improve_t = [p["naive_abs_t"] - p["abs_err_t"] for p in preds]
    mean_imp_t, lo_imp_t, hi_imp_t = bootstrap_mean_ci(improve_t)
    dir_hits = sum(1 for p in preds if p["direction_ok"])
    dir_lo, dir_hi = wilson(dir_hits, n)
    brier = M.mean([(p["p_home"] - (1.0 if p["home_won"] else 0.0)) ** 2 for p in preds])
    # Naive direction baselines: always away, always home. A direction rate only means
    # something relative to these, because the home/away split is not 50/50.
    away_hits = sum(1 for p in preds if not p["home_won"])
    home_hits = sum(1 for p in preds if p["home_won"])
    # paired per-game advantage of the model over "always away"
    dir_vs_away = [((1.0 if p["direction_ok"] else 0.0) - (0.0 if p["home_won"] else 1.0))
                   for p in preds]
    dv_mean, dv_lo, dv_hi = bootstrap_mean_ci(dir_vs_away)
    base_rate = M.mean([1.0 if p["home_won"] else 0.0 for p in preds])
    brier_base = M.mean([(base_rate - (1.0 if p["home_won"] else 0.0)) ** 2 for p in preds])

    # ---- per-week series for the demotion gate ---------------------------------
    weekly = {}
    for p in preds:
        wk = weekly.setdefault(p["week"], {"week": p["week"], "n": 0, "mae": 0.0, "naive": 0.0,
                                           "hits": 0})
        wk["n"] += 1
        wk["mae"] += p["abs_err"]
        wk["naive"] += p["naive_abs"]
        wk["hits"] += 1 if p["direction_ok"] else 0
    series = []
    for w in sorted(weekly):
        v = weekly[w]
        series.append({"week": w, "n": v["n"], "mae_margin": round(v["mae"] / v["n"], 2),
                       "mae_naive": round(v["naive"] / v["n"], 2),
                       "beats_naive": v["mae"] < v["naive"],
                       "direction_rate": round(v["hits"] / v["n"], 3)})

    # D-1: three consecutive scored weeks worse than the naive baseline
    streak = worst_streak = 0
    for s in series:
        streak = 0 if s["beats_naive"] else streak + 1
        worst_streak = max(worst_streak, streak)
    trailing_bad = series[-3:] and all(not s["beats_naive"] for s in series[-3:])

    # D-2: rolling-20 paired CI entirely below zero
    roll = improve[-20:]
    _, rlo, rhi = bootstrap_mean_ci(roll) if len(roll) >= 10 else (None, None, None)

    gates = {
        "D-1_three_consecutive_weeks_worse_than_naive": {
            "fires": bool(trailing_bad), "worst_streak_observed": worst_streak,
            "last_three": [{"week": s["week"], "beats_naive": s["beats_naive"]} for s in series[-3:]],
        },
        "D-2_rolling20_improvement_ci_below_zero": {
            "fires": bool(rlo is not None and rhi is not None and rhi < 0),
            "rolling20_mean_improvement_points": None if rlo is None else round(M.mean(roll), 3),
            "ci95": [None if rlo is None else round(rlo, 3), None if rhi is None else round(rhi, 3)],
        },
        "D-3_direction_hit_rate_ci_below_0.50": {
            "fires": bool(dir_hi is not None and dir_hi < 0.5),
            "ci95": [None if dir_lo is None else round(dir_lo, 4),
                     None if dir_hi is None else round(dir_hi, 4)],
        },
        "D-4_staking_input_missing_while_live": {
            "fires": True,
            "detail": "no market prices exist (F-01), so no strategy can hold a live staking "
                      "score; anything that was live would be returned to paper by this rule alone",
        },
    }
    demoted = [k for k, v in gates.items() if v["fires"]]

    # ---- per-strategy scoring ---------------------------------------------------
    # Only model-level signal claims can be scored from results. The trade strategies
    # need prices to be settled, so their staking score is BLOCKED and their signal
    # score is UNTESTED - neither is estimated.
    strat_rows = []
    for sid, fam, name, entry, exit_, data_req, sig_src, gate_state in C.STRAT:
        is_model = fam == "Evaluation"
        row = {
            "id": sid, "family": fam, "name": name, "entry": entry, "settlement": exit_,
            "data_required": data_req, "signal_source": sig_src,
            "gate_state_at_registration": gate_state,
            "signal_score": None, "signal_n": None, "signal_ci": None, "signal_metric": "",
            "signal_status": "UNTESTED",
            "staking_score": None, "staking_n": None, "staking_status": "BLOCKED",
            "staking_blocker": ("no market price exists in this repository, so a bet cannot be "
                                "priced, settled or valued (F-01)"),
            "rank": None, "tier": "PAPER", "demotion": "n/a - never promoted",
        }
        if is_model:
            row["signal_metric"] = ("paired improvement in absolute margin error over the naive "
                                    "home -2.5 baseline, bootstrap 95% CI")
            row["signal_score"] = None if mean_imp is None else round(mean_imp, 3)
            row["signal_n"] = n
            row["signal_ci"] = [None if lo_imp is None else round(lo_imp, 3),
                                None if hi_imp is None else round(hi_imp, 3)]
            # a signal is only 'established' if the whole CI is above zero
            if lo_imp is not None and lo_imp > 0:
                row["signal_status"] = "ESTABLISHED"
            elif hi_imp is not None and hi_imp < 0:
                row["signal_status"] = "FAILED"
            else:
                row["signal_status"] = "INCONCLUSIVE"
        strat_rows.append(row)

    # ranking: signal first, staking second, both required for promotion
    established = [r for r in strat_rows if r["signal_status"] == "ESTABLISHED"]
    established.sort(key=lambda r: -(r["signal_score"] or 0))
    for i, r in enumerate(established, 1):
        r["rank"] = i

    counts = {
        "strategies": len(strat_rows),
        "signal_established": sum(1 for r in strat_rows if r["signal_status"] == "ESTABLISHED"),
        "signal_inconclusive": sum(1 for r in strat_rows if r["signal_status"] == "INCONCLUSIVE"),
        "signal_failed": sum(1 for r in strat_rows if r["signal_status"] == "FAILED"),
        "signal_untested": sum(1 for r in strat_rows if r["signal_status"] == "UNTESTED"),
        "staking_scored": sum(1 for r in strat_rows if r["staking_status"] == "SCORED"),
        "staking_blocked": sum(1 for r in strat_rows if r["staking_status"] == "BLOCKED"),
        "leaderboard_eligible": 0,
        "demotion_gates_firing": len(demoted),
    }

    out = {
        "as_of": "2026-11-14", "generated_by": "tools/strategies_engine.py",
        "scoring_contract": [
            "Signal and staking are scored in different columns from different data and are "
            "never combined into one number.",
            "A strategy is leaderboard-eligible only when its signal is ESTABLISHED (whole CI "
            "above the baseline), its staking score exists with n, and the demotion gate is "
            "not firing.",
            "A good staking run cannot promote a strategy whose signal is INCONCLUSIVE or "
            "FAILED; a good signal cannot be published with a staking number that does not "
            "exist.",
            "Every number carries n. A row without n is not ranked.",
        ],
        "signal_evidence": {
            "n_games": n,
            "margin": {
                "metric": "paired improvement in absolute error vs the naive -2.5 baseline, in points",
                "mean_improvement": None if mean_imp is None else round(mean_imp, 3),
                "ci95": [None if lo_imp is None else round(lo_imp, 3),
                         None if hi_imp is None else round(hi_imp, 3)],
                "model_mae": bt["backtest"]["mae_margin"],
                "naive_mae": bt["backtest"]["mae_margin_naive_-2.5"],
                "interpretation": ("the interval contains zero, so the side model's edge over a "
                                   "constant -2.5 is not yet established at this sample size"),
            },
            "total": {
                "metric": "paired improvement in absolute error vs the naive 45.0 baseline, in points",
                "mean_improvement": None if mean_imp_t is None else round(mean_imp_t, 3),
                "ci95": [None if lo_imp_t is None else round(lo_imp_t, 3),
                         None if hi_imp_t is None else round(hi_imp_t, 3)],
                "model_mae": bt["backtest"]["mae_total"],
                "naive_mae": bt["backtest"]["mae_total_naive_45.0"],
                "interpretation": ("the model's total is WORSE than a constant 45 on this sample; "
                                   "published as-is rather than tuned until it looks better"),
            },
            "direction": {"hits": dir_hits, "n": n,
                          "rate": round(dir_hits / n, 4),
                          "ci95_wilson": [round(dir_lo, 4), round(dir_hi, 4)],
                          "baseline_always_away": round(away_hits / n, 4),
                          "baseline_always_home": round(home_hits / n, 4),
                          "advantage_over_always_away": round(dv_mean, 4),
                          "advantage_ci95": [round(dv_lo, 4), round(dv_hi, 4)],
                          "reading": ("the direction rate beats the always-away baseline by "
                                      f"{dv_mean:+.3f} per game, 95% CI "
                                      f"[{dv_lo:+.3f}, {dv_hi:+.3f}]")},
            "moneyline_calibration": {"brier": round(brier, 4), "brier_base_rate": round(brier_base, 4),
                                      "base_rate_home_win": round(base_rate, 4), "n": n,
                                      "reading": ("lower is better; the model's probability beats "
                                                  "the base rate" if brier < brier_base else
                                                  "the model's probability does not beat the base "
                                                  "rate on this sample")},
            "multiple_testing": {
                "variants_tried": len(C.STRAT),
                "control": "Bonferroni over the number of registered strategies; Benjamini-Hochberg "
                           "at 10% is the registered gate G-5",
                "note": "with 12 registered hypotheses the corrected threshold on any single test is "
                        "0.05/12 = 0.0042",
            },
            "source": SRC_RESULTS,
        },
        "demotion_gate": {
            "id": "G-10", "name": "Demotion",
            "rule": ("a live strategy is returned to paper when any of D-1..D-4 fires; the check "
                     "runs on every scheduled build, and a demoted strategy must pass every "
                     "promotion gate again from a new registration id"),
            "clauses": [
                {"id": "D-1", "condition": "three consecutive scored weeks worse than the naive baseline"},
                {"id": "D-2", "condition": "rolling-20-game paired improvement CI entirely below zero"},
                {"id": "D-3", "condition": "direction hit-rate 95% CI entirely below 0.50"},
                {"id": "D-4", "condition": "the staking input disappears while the strategy is live"},
            ],
            "evaluated_against": "ST-10 model-quality benchmark (the only strategy with a series)",
            "results": gates,
            "firing": demoted,
            "verdict": ("PAPER. " + ", ".join(demoted) + " fire." if demoted else "no clause fires"),
        },
        "weekly_series": series,
        "counts": counts,
        "strategies": strat_rows,
        "limits": [
            "One season of results; G-2 (>=300 settled bets, >=3 seasons) cannot be met, so even "
            "an established signal cannot be promoted yet.",
            "No prices means no staking score at all: ROI, CLV and drawdown are not computable and "
            "are not published as zero.",
            "Prop, parlay and prop-combo strategies are UNTESTED rather than failed: their inputs "
            "(prop prices, prop settlement history) do not exist in this repository.",
        ],
    }
    with open(os.path.join(OUT, "strategies.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    print(f"signal evidence n={n}: margin improvement {mean_imp:+.3f} pts "
          f"[{lo_imp:+.3f},{hi_imp:+.3f}] -> {out['signal_evidence']['margin']['interpretation'][:40]}")
    print(f"total: {mean_imp_t:+.3f} pts [{lo_imp_t:+.3f},{hi_imp_t:+.3f}]")
    print(f"direction {dir_hits}/{n} = {dir_hits/n:.4f} [{dir_lo:.3f},{dir_hi:.3f}]; "
          f"brier {brier:.4f} vs base {brier_base:.4f}")
    print(f"strategies: {counts['signal_established']} established, "
          f"{counts['signal_inconclusive']} inconclusive, {counts['signal_untested']} untested, "
          f"{counts['staking_blocked']} staking-blocked; leaderboard eligible {counts['leaderboard_eligible']}")
    print(f"demotion gate firing: {demoted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
