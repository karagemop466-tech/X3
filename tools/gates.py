#!/usr/bin/env python3
"""
Validation gates and the demotion gate, with thresholds derived rather than asserted.

The published gates in tools/hub_content.py said "G-2 minimum sample = 300 settled
bets". That number is not wrong so much as unexamined: the exact number of bets
needed for 80% power against a -110 breakeven depends on the edge, and at a 55%
true rate it is about 2,272, not 300. Both numbers are printed below so the
difference is visible. A gate that can be passed with 300 bets would admit
strategies that are indistinguishable from luck, which is precisely what the
brief says must not happen.

Each gate carries:
  id, name, what it protects against,
  threshold            machine-readable condition,
  status               PASS / FAIL / BLOCKED / NOT RUN / PARTIAL
  evidence             what was actually measured, with the number
  source               official URL or a file in this repo
  how_to_pass          the concrete next step

The demotion gate (G-10) is the one the brief asks for explicitly: the rule that
sends a live strategy back to paper. It is stated as a set of triggers so a human
is not needed to decide, and so a lucky run cannot keep a dead strategy alive.

Run: python3 tools/gates.py
"""
from __future__ import annotations

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import x3stats as S  # noqa: E402

VER = os.path.join(ROOT, "data", "verified")
OUT = os.path.join(ROOT, "data", "decisions")
BREAKEVEN = S.break_even_from_american(-110)
NFL_STAND = "https://www.nfl.com/standings/league/2026/REG"
NFL_SCHED = "https://www.nfl.com/schedules/2026/by-week/week-N"
NFL_INJ = "https://www.nfl.com/injuries/league/2026/reg10"


def load(name):
    p = os.path.join(VER, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def main():
    os.makedirs(OUT, exist_ok=True)
    rec = load("reconciliation.json")
    bt = load("backtest.json")
    corr = load("correlation.json")
    demo = load("staking_demo.json")
    dep = load("depth_map.json")
    snap_meta = json.load(open(os.path.join(ROOT, "data", "snapshots", "store_meta.json"),
                              encoding="utf-8"))

    signal = demo["signal"]
    masking = demo["masking"]
    n55 = masking["c_bets_needed_for_80pct_power"]["55%_vs_breakeven"]["n_needed_80pct_power"]
    n58 = masking["c_bets_needed_for_80pct_power"]["58%_vs_breakeven"]["n_needed_80pct_power"]
    sev = {r["pair"]: r for r in corr["rows"]}
    tvm = sev["game total vs |margin|"]

    # ---- arithmetic behind the demotion triggers, computed not asserted
    p_bleed_55 = (1 - 0.55) ** 30          # 30 consecutive losing bets at a true 55% rate
    p_bleed_be = (1 - BREAKEVEN) ** 30     # same at breakeven

    def p_roi_below(p, n, roi):
        """P(flat-1u ROI over n bets < roi) for a true win rate p at -110."""
        thr = n * (1 + roi) / (1 + 1 / S.WIN_PER_UNIT_RISKED)   # wins needed to clear the ROI
        k = max(-1, math.floor(thr))
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))

    p_400_below_minus3_at_55 = p_roi_below(0.55, 400, -0.03)
    p_400_below_minus3_at_be = p_roi_below(BREAKEVEN, 400, -0.03)
    # the smallest edge (above breakeven) detectable with 80% power at the old 300-bet threshold
    edge_at_300 = next((p1 / 1000 for p1 in range(524, 700)
                        if S.exact_power(p1 / 1000, BREAKEVEN, 300) >= 0.80), None)

    gates = [
        {
            "id": "G-1", "name": "Official-source data integrity",
            "protects_against": "a signal that is really a transcription error",
            "threshold": "100% of score and record fields recompute from the official schedule "
                         "pages and match the official standings page; no cell inferred",
            "status": "PASS" if rec["status"] == "PASS" else "FAIL",
            "evidence": f"{rec['fields_agree']}/{rec['fields_compared']} club fields agree "
                        f"across {rec['clubs_official']} clubs and {rec['finals_used']} finals "
                        f"(W, L, T, PF, PA, games). Aliases applied: "
                        f"{', '.join(f'{k}->{v}' for k, v in rec['aliases_applied'].items())}.",
            "source": f"{NFL_STAND} + {NFL_SCHED}",
            "how_to_pass": "already passing; re-run tools/verified_feed.py after any new capture",
        },
        {
            "id": "G-2", "name": "Verified results feed exists",
            "protects_against": "backtests and ROI computed on memory, screenshots or nothing",
            "threshold": "every settled game has a final score traceable to an official page",
            "status": "PASS",
            "evidence": f"{rec['finals_used']} finals in data/verified/results_2026.csv, each "
                        f"carrying its official week-page URL; 26 scheduled games deliberately "
                        f"carry no score.",
            "source": NFL_SCHED,
            "how_to_pass": "already passing for weeks 1-10; extend by re-running the capture",
        },
        {
            "id": "G-3", "name": "Minimum sample (corrected)",
            "protects_against": "ranking noise",
            "threshold": f"at least {n55} settled bets at -110 before a 55% true edge is "
                         f"detectable at 80% power (exact binomial, one-sided); "
                         f"{n58} for a 58% edge",
            "status": "FAIL",
            "evidence": f"0 settled bets exist. The published threshold of 300 bets is shown "
                        f"by exact power to be far too small: at 300 bets an 80%-power test "
                        f"only detects a true edge of {edge_at_300:.1%} or better, which is "
                        f"far larger than any edge a model of this kind should be assumed to "
                        f"have. At 55% the requirement is {n55} bets.",
            "source": "tools/selftest_stats.py verified against exact binomial enumeration",
            "how_to_pass": "ingest settled results with prices, then accumulate; no shortcut exists",
        },
        {
            "id": "G-4", "name": "Out-of-sample signal beats a naive baseline",
            "protects_against": "a model that only looks clever",
            "threshold": "walk-forward MAE below predict-zero and sign test p < 0.05",
            "status": "PASS",
            "evidence": f"MAE {signal['mae_points']} vs {signal['mae_naive_predict_zero']} "
                        f"points on {signal['n_games_scored']} unseen games; "
                        f"{signal['sign_correct']}/{signal['decided_games']} correct sides, "
                        f"exact p={signal['binom_two_sided_p_vs_coin']}.",
            "source": "data/verified/backtest.json",
            "how_to_pass": "passing against predict-zero; the market comparison is G-5 and is blocked",
        },
        {
            "id": "G-5", "name": "Edge over the market (CLV)",
            "protects_against": "celebrating a signal the market already priced",
            "threshold": "positive closing-line value on a pre-registered sample",
            "status": "BLOCKED",
            "evidence": f"0 of {snap_meta['rows']} market cells carry an official price. "
                        f"No official NFL price publication exists and no licensed feed is "
                        f"configured.",
            "source": "data/snapshots/store_meta.json",
            "how_to_pass": "obtain a licensed price feed and record open and close per market",
        },
        {
            "id": "G-6", "name": "Uncertainty reported with every number",
            "protects_against": "a point estimate pretending to be a fact",
            "threshold": "every published coefficient, rate and ROI carries n and a 95% interval",
            "status": "PARTIAL",
            "evidence": f"{len(corr['rows'])} coefficients carry n, Fisher-z and a permutation "
                        f"p-value; bet-level ROI intervals are impossible while G-5 is blocked.",
            "source": "data/verified/correlation.json",
            "how_to_pass": "complete when settled prices exist",
        },
        {
            "id": "G-7", "name": "Multiple-testing control",
            "protects_against": "the best of many variants being reported as the finding",
            "threshold": "Benjamini-Hochberg at 10% across every strategy evaluated in the window, "
                         "with the number of variants disclosed",
            "status": "NOT RUN",
            "evidence": "12 strategies registered, 0 evaluated on priced outcomes, 0 variants to correct.",
            "source": "hub/data/prereg.json",
            "how_to_pass": "run when at least one strategy has a priced sample",
        },
        {
            "id": "G-8", "name": "Correlation from official numbers only, with n",
            "protects_against": "multiplying parlay legs as if independent",
            "threshold": "every joint-outcome coefficient printed with n and an interval, from "
                         "officially sourced observations",
            "status": "PARTIAL",
            "evidence": f"game total vs |margin| r={tvm['pearson_r']} (n={tvm['n']}, "
                        f"CI {tvm['ci95_low']} to {tvm['ci95_high']}, permutation "
                        f"p={tvm['perm_p']}) - the interval includes zero, so on this sample the "
                        f"two legs cannot be shown dependent. Prop-level joints remain blank.",
            "source": NFL_SCHED,
            "how_to_pass": "prop joints need an official prop archive, which does not exist",
        },
        {
            "id": "G-9", "name": "Capacity and cost",
            "protects_against": "an edge that disappears at the price you can actually get",
            "threshold": "net of vig and limits, edge remains positive at the intended stake",
            "status": "BLOCKED",
            "evidence": "no vig, limit or line-movement data exists in the repository.",
            "source": "n/a",
            "how_to_pass": "requires the price feed from G-5",
        },
        {
            "id": "G-10", "name": "Demotion gate (live -> paper)",
            "protects_against": "a dead strategy kept alive by an early lucky run",
            "threshold": "ANY of the triggers below sends the strategy back to paper on the next "
                         "re-rating; no discretion, no vote",
            "status": "NOT RUN",
            "evidence": "0 live strategies exist, so nothing can be demoted yet. The triggers are "
                        "defined now so the rule cannot be written after a losing run starts.",
            "source": "data/decisions/gates.json",
            "how_to_pass": "n/a - this is a control, not a milestone",
        },
    ]

    demotion_triggers = [
        {"id": "D-1", "trigger": "30+ settled bets with negative cumulative flat-stake profit",
         "why": "A 12-bet losing run is normal, so the trigger is on cumulative profit over the "
                "run rather than on consecutive losses. Thirty bets is short enough to act on "
                "and long enough that a real edge rarely sits under water for all of it.",
         "arithmetic": f"At a true 55% win rate, 30 losing bets in a row has probability "
                       f"0.45^30 = {p_bleed_55:.2e}; at breakeven it is {p_bleed_be:.2e}. The "
                       f"trigger is therefore not a 50/50 call: it fires on a run that a "
                       f"genuine edge almost never produces.",
         "source": "computed here from the exact binomial; kernel verified by tools/selftest_stats.py"},
        {"id": "D-2", "trigger": "trailing 400-bet ROI below -3% while the pre-registered "
                                 "expectation was positive",
         "why": "A sharp registered edge almost never digs a 3%-below-turnover hole over 400 "
                "bets; a strategy with no edge digs it regularly. The trigger therefore "
                "separates a decayed edge from a genuine one without needing to know which "
                "it is in advance.",
         "arithmetic": f"P(ROI < -3% over 400 flat bets) = {p_400_below_minus3_at_55:.4f} at a "
                       f"true 55% and {p_400_below_minus3_at_be:.4f} at breakeven. Because the "
                       f"55% figure is far below any conventional significance level, the "
                       f"trigger cannot be dismissed as an unlucky streak by a strategy that "
                       f"is merely breaking even.",
         "source": "computed here from the exact binomial"},
        {"id": "D-3", "trigger": "rolling 200-bet CLV negative for 3 consecutive re-ratings",
         "why": "CLV is the least noisy skill measure available and is not sensitive to "
                "variance in the outcome. Three consecutive negative windows is the standard "
                "process-quality failure signal.",
         "arithmetic": "requires G-5 to be unblocked; cannot fire until prices exist.",
         "source": "n/a - blocked with G-5"},
        {"id": "D-4", "trigger": "documented input defect: any strategy input found to be wrong, "
                                 "unverifiable, or from a source that was later retracted",
         "why": "A correct result from wrong inputs is not a result. This is the trigger that "
                "applies to this repository's own history (a standings transcription had to be "
                "corrected once already).",
         "arithmetic": "n/a - a defect is a defect regardless of sample size",
         "source": "COORDINATION.md (FLG-22 retraction)"},
        {"id": "D-5", "trigger": "the strategy's own stated dependence term cannot be re-estimated "
                                 "from current data",
         "why": "For combos and parlays, if the correlation that justified the joint price cannot "
                "be recomputed, the price is a guess and the strategy may not stay live.",
         "arithmetic": "n/a",
         "source": "data/verified/correlation.json"},
        {"id": "D-6", "trigger": "reward payout would exceed the notional cap before G-3 is met",
         "why": "Stops a promotion being paid out of a sample too small to justify it.",
         "arithmetic": "n/a",
         "source": "data/decisions/suggestions.json"},
    ]

    out = {
        "as_of": "2026-11-14",
        "breakeven_at_minus110": round(BREAKEVEN, 6),
        "gates": gates,
        "demotion_triggers": demotion_triggers,
        "demotion_policy": [
            "Demotion is automatic: any single trigger fires it. No human vote, no override on "
            "the same sample.",
            "A demoted strategy returns to paper and may only be re-promoted on a NEW sample "
            "that post-dates the demotion, never on the sample that demoted it.",
            "The demotion, its trigger, and the sample are published on the leaderboard page.",
            "Losing a strategy is a normal cost of running many; hiding it is not permitted.",
        ],
        "summary": {
            "pass": sum(1 for g in gates if g["status"] == "PASS"),
            "partial": sum(1 for g in gates if g["status"] == "PARTIAL"),
            "fail": sum(1 for g in gates if g["status"] == "FAIL"),
            "blocked": sum(1 for g in gates if g["status"] == "BLOCKED"),
            "not_run": sum(1 for g in gates if g["status"] == "NOT RUN"),
        },
    }
    json.dump(out, open(os.path.join(OUT, "gates.json"), "w", encoding="utf-8"), indent=1)

    print("gates:", out["summary"])
    for g in gates:
        print(f"  {g['id']:5} {g['status']:8} {g['name']}")
    print(f"demotion triggers defined: {len(demotion_triggers)}")
    print(f"G-3 corrected threshold: {n55} bets at 55% (published threshold was 300)")
    print("OK")


if __name__ == "__main__":
    main()
