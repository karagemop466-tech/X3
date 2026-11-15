#!/usr/bin/env python3
"""
Signal vs staking, measured (session arena/aab4718a-x3).

The brief asks that a lucky staking run must not be able to mask a bad signal.
That is a claim about measurement, so this script measures it.

Three quantities are kept apart on purpose:

  SIGNAL    out-of-sample discrimination of the model, scored against the final
            score. Involves no money and no price, so it cannot be an ROI and is
            never presented as one.

  STAKING   what a staking rule does to a bankroll given some true win rate.
            Depends on unit size, price, ordering and luck, and not on whether
            the signal is any good.

  MASKING   how often a worse strategy outranks a better one purely because the
            sample is short, and how many settled bets are needed before a real
            edge is detectable at all. Those answers set the minimum-sample gate
            with arithmetic instead of opinion.

Price convention: -110 means you risk 1.10 to win 1.00, so a win returns
100/110 = 0.9091 of the amount risked and breakeven is 52.38%. This repository
has no price feed; -110 is used only to illustrate variance and is never
reported as a return.

Run: python3 tools/signal_vs_staking.py
"""
from __future__ import annotations

import json
import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "verified")

WIN_PER_UNIT_RISKED = 100 / 110                     # 0.909090...
BREAKEVEN = 1 / (1 + WIN_PER_UNIT_RISKED)           # 0.5238095...
SEED = 20261114
TRIALS = 20000


def q(sorted_v, p):
    i = min(len(sorted_v) - 1, max(0, int(round(p * (len(sorted_v) - 1)))))
    return sorted_v[i]


def simulate(p_true, n_bets, rule, trials, rng):
    """Bankroll distribution starting at 100 over n_bets at a fixed true rate."""
    out = []
    for _ in range(trials):
        bank = 100.0
        for _ in range(n_bets):
            stake = min(rule(bank), bank)
            if stake <= 0:
                bank = 0.0
                break
            bank += stake * WIN_PER_UNIT_RISKED if rng.random() < p_true else -stake
            if bank <= 0:
                bank = 0.0
                break
        out.append(bank)
    out.sort()
    return out


def p_positive_flat(p_true, n_bets, trials, rng):
    """Flat 1 unit risked: probability the bankroll ends above its 100 start."""
    pos = 0
    for _ in range(trials):
        w = 0
        for _ in range(n_bets):
            if rng.random() < p_true:
                w += 1
        pos += (w * WIN_PER_UNIT_RISKED - (n_bets - w)) > 0
    return pos / trials


def p_a_beats_b(pa, pb, n_bets, trials, rng):
    """Flat 1 unit: P(strategy A finishes above strategy B) over the same n bets."""
    wins = 0
    for _ in range(trials):
        wa = sum(1 for _ in range(n_bets) if rng.random() < pa)
        wb = sum(1 for _ in range(n_bets) if rng.random() < pb)
        wins += (wa > wb)
    return wins / trials


def _betacf(a, b, x):
    """Continued fraction for the incomplete beta function (Lentz's method).

    Straight from the standard treatment; convergence is rapid and the result is
    accurate to double precision, which a direct binomial sum is not once n gets
    large enough for p**n to underflow.
    """
    MAXIT, EPS, FPMIN = 300, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a, b, x):
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def binom_tail_at_least(n, k, p):
    """P(X >= k) for X ~ Binomial(n, p), via the incomplete beta identity.

    P(X <= k-1) = I_{1-p}(n-k+1, k), so the tail is 1 minus that.
    """
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return min(1.0, max(0.0, 1.0 - _betai(n - k + 1, k, 1.0 - p)))


def _k_crit(n, p0, alpha=0.05):
    """Smallest k with P(X >= k | n, p0) <= alpha. Bisection; tail is monotone in k."""
    lo, hi = 0, n + 1
    while lo < hi:
        mid = (lo + hi) // 2
        if binom_tail_at_least(n, mid, p0) <= alpha:
            hi = mid
        else:
            lo = mid + 1
    return lo


def exact_power(p1, p0, n, alpha=0.05):
    """Exact one-sided binomial power: P(reject breakeven | true rate p1)."""
    return binom_tail_at_least(n, _k_crit(n, p0, alpha), p1)


def min_n_for_power(p1, p0, alpha=0.05, power=0.80):
    """Smallest n where a one-sided exact binomial test separates p1 from p0.

    Closed form first (two-proportion sample size), then verified with exact power
    by bisection on n, because exact power is a sawtooth in n: the critical count
    k moves in integer steps, so the closed form can land just short.
    """
    z_a, z_b = 1.6448536, 0.8416212
    spread = p1 - p0
    if spread <= 0:
        return None
    x = z_a * math.sqrt(p0 * (1 - p0)) + z_b * math.sqrt(p1 * (1 - p1))
    start = max(4, math.ceil((x / spread) ** 2))

    def ok(n):
        return exact_power(p1, p0, n) >= power

    if ok(start):
        n = start
        while n > 4 and ok(n - 1):
            n -= 1
        return n
    hi = start
    while hi < 200000 and not ok(hi):
        hi *= 2
    if hi >= 200000:
        return None
    lo = hi // 2
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


def binom_two_sided(k, nn, p=0.5):
    pmf = [math.comb(nn, i) * p ** i * (1 - p) ** (nn - i) for i in range(nn + 1)]
    return min(1.0, sum(x for x in pmf if x <= pmf[k] + 1e-15))


def main():
    bt = json.load(open(os.path.join(OUT, "backtest.json"), encoding="utf-8"))
    rows = bt["rows"]
    n = len(rows)

    # ---------------- SIGNAL (no money, no price)
    decided_rows = [r for r in rows if r["actual_margin"] != 0]
    correct = sum(1 for r in decided_rows
                  if (r["pred_margin"] > 0) == (r["actual_margin"] > 0))
    pushes = n - len(decided_rows)
    decided = len(decided_rows)
    sign_acc = correct / decided
    p_sign = binom_two_sided(correct, decided)

    signal = {
        "n_games_scored": n,
        "decided_games": decided,
        "pushes_excluded": pushes,
        "sign_correct": correct,
        "sign_accuracy": round(sign_acc, 4),
        "binom_two_sided_p_vs_coin": round(p_sign, 5),
        "mae_points": bt["spread"]["mae_model"],
        "mae_naive_predict_zero": bt["spread"]["mae_predict_zero"],
        "improvement_points": bt["spread"]["improvement_points"],
        "corr_pred_vs_actual": bt["spread"]["corr_pred_vs_actual"],
        "what_this_proves": (
            f"On {n} games the model never saw, it beats predicting a zero margin on MAE "
            f"({bt['spread']['mae_model']} vs {bt['spread']['mae_predict_zero']} points) and "
            f"gets the winner's side of the final score {correct} of {decided} times "
            f"(p={p_sign:.4f}). The pipeline carries real information about the score."),
        "what_this_does_not_prove": (
            "It is NOT an edge over a market. A closing line is far better than "
            "predict-zero, and this repository has no prices, so the only comparison that "
            "would matter has not been made. Sign accuracy against the final score is not "
            "a win rate at a price, and no bankroll, ROI or reward may be derived from it."),
    }

    # ---------------- STAKING (variance at stated true rates)
    rules = {
        "flat_1_unit": lambda bank: 1.0,
        "flat_5_units": lambda bank: 5.0,
        "fixed_pct_2": lambda bank: 0.02 * bank,
        "fixed_pct_10": lambda bank: 0.10 * bank,
        "fixed_pct_25": lambda bank: 0.25 * bank,
        "all_in": lambda bank: bank,
    }
    staking = {}
    for p_true, label in ((BREAKEVEN, "breakeven_52_38pct"), (0.55, "modest_edge_55pct")):
        block = {}
        for name, rule in rules.items():
            d = simulate(p_true, 200, rule, 4000, random.Random(SEED))
            block[name] = {
                "p05": round(q(d, 0.05), 2),
                "p50": round(q(d, 0.50), 2),
                "p95": round(q(d, 0.95), 2),
                "share_below_start": round(sum(1 for x in d if x < 100) / len(d), 4),
                "share_ruined": round(sum(1 for x in d if x <= 0) / len(d), 4),
            }
        staking[label] = {"true_win_rate": round(p_true, 4), "price": "-110",
                          "n_bets": 200, "rules": block}

    # ---------------- MASKING (the answer to the brief)
    ks = (20, 50, 100, 200, 500, 1000, 2000)
    look = {}
    for p_true, tag in ((0.45, "bad_45pct"), (0.50, "coin_50pct"),
                        (round(BREAKEVEN, 4), "breakeven_52_38pct")):
        look[tag] = {str(k): round(p_positive_flat(p_true, k, TRIALS, random.Random(SEED + k)), 4)
                     for k in ks}
    rank = {str(k): round(p_a_beats_b(0.47, 0.55, k, TRIALS, random.Random(SEED + 7 * k)), 4)
            for k in ks}
    power = {}
    for rate in (0.55, 0.56, 0.58):
        power[f"{rate:.0%}_vs_breakeven"] = {
            "n_needed_80pct_power": min_n_for_power(rate, BREAKEVEN),
            "power_at_that_n": round(exact_power(rate, BREAKEVEN, min_n_for_power(rate, BREAKEVEN)), 4),
        }

    bad100 = look["bad_45pct"]["100"]
    worse20 = rank["20"]
    worse200 = rank["200"]
    n55 = power["55%_vs_breakeven"]["n_needed_80pct_power"]

    masking = {
        "price": "-110",
        "breakeven_win_rate": round(BREAKEVEN, 6),
        "a_share_finishing_above_start_flat_1u": look,
        "a_reading": (
            f"A strategy whose TRUE win rate is 45% - far below the {BREAKEVEN:.1%} "
            f"breakeven - still finishes above its starting bankroll {bad100:.1%} of the "
            f"time after 100 bets. A bankroll column is therefore not evidence of skill and "
            f"cannot be a ranking key."),
        "b_share_worse_47_outranks_better_55": rank,
        "b_reading": (
            f"With only 20 bets, a strategy whose true rate is 47% finishes ahead of one "
            f"whose true rate is 55% {worse20:.1%} of the time. At 200 bets that falls to "
            f"{worse200:.1%}. A leaderboard read at a short sample is mostly noise."),
        "c_bets_needed_for_80pct_power": power,
        "c_reading": (
            f"At -110, a true 55% bettor needs about {n55} settled bets before a one-sided "
            f"exact binomial test rejects breakeven 80% of the time. That is the arithmetic "
            f"behind the minimum-sample gate, not a preference."),
        "trials": TRIALS,
        "seed": SEED,
    }

    out = {
        "method": "Signal is measured out of sample from data/verified/backtest.json and "
                  "involves no money. Staking and masking are binomial samplings with a "
                  "fixed seed, so every number is reproducible by re-running the script. "
                  "No market price exists in the repository.",
        "sources": ["https://www.nfl.com/schedules/2026/by-week/week-N"],
        "signal": signal,
        "staking": staking,
        "masking": masking,
        "limits": [
            "One season. The signal itself has a wide interval; 137 games cannot establish "
            "a durable edge.",
            "Independent identically distributed bets are assumed, which understates real "
            "slate variance where same-week bets are correlated.",
            "No commission, limit, line movement or push handling is modelled.",
            "The staking block illustrates variance; it is not a performance record and must "
            "never be quoted as an ROI.",
        ],
    }
    json.dump(out, open(os.path.join(OUT, "staking_demo.json"), "w", encoding="utf-8"), indent=1)

    print(f"SIGNAL  sign {sign_acc:.4f} ({correct}/{decided}) p={p_sign:.4f} "
          f"MAE {signal['mae_points']} vs {signal['mae_naive_predict_zero']} "
          f"corr {signal['corr_pred_vs_actual']}")
    print("MASKING (a) share finishing above start, flat 1u:")
    for tag, v in look.items():
        print(f"  {tag:<22}", "  ".join(f"{k:>4}:{p:.3f}" for k, p in v.items()))
    print("MASKING (b) P(worse 47% outranks better 55%):")
    print("  ", "  ".join(f"{k:>4}:{p:.3f}" for k, p in rank.items()))
    print("MASKING (c) n for 80% power vs breakeven:")
    for k, v in power.items():
        print(f"  {k:<22} n={v['n_needed_80pct_power']} power={v['power_at_that_n']}")
    print("OK")


if __name__ == "__main__":
    main()
