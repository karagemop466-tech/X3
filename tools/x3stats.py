#!/usr/bin/env python3
"""
Small, validated statistics kernel shared by the X3 gates.

Everything here is checked against exact enumeration in tools/selftest_stats.py,
so a gate can cite a number without the number being a guess. No third-party
dependencies: this is a static site with no build step.

Contents
  phi, american_to_prob, prob_to_american   pricing conversions
  betacf, betai, binom_tail, k_crit, exact_power, min_n
                                            exact binomial machinery
  sign_test                                 exact two-sided sign test
  wilson_interval                           interval for a proportion
"""
from __future__ import annotations

import math


# ------------------------------------------------------------------ pricing
def prob_to_american(p: float) -> int:
    """Win probability -> American price. p=0.5 is +100 by convention."""
    if not (0 < p < 1):
        raise ValueError("probability outside (0,1)")
    if p == 0.5:
        return 100
    if p > 0.5:
        return int(round(-100 * p / (1 - p)))
    return int(round(100 * (1 - p) / p))


def american_to_prob(a: int) -> float:
    """American price -> implied win probability (no vig removed)."""
    if a < 0:
        return -a / (-a + 100)
    return 100 / (a + 100)


def break_even_from_american(a: int) -> float:
    return american_to_prob(a)


# A -110 price means risking 1.10 to win 1.00. Taking the amount risked as the
# unit, a win returns 100/110 of it and a loss costs all of it. Kept here so the
# gates and the staking demo cannot drift apart on the payout convention.
WIN_PER_UNIT_RISKED = 100 / 110


# ------------------------------------------------------------------ binomial
def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 400, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
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


def betai(a, b, x):
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


def binom_tail(n: int, k: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return min(1.0, max(0.0, 1.0 - betai(n - k + 1, k, 1.0 - p)))


def k_crit(n: int, p0: float, alpha: float = 0.05) -> int:
    """Smallest k with P(X >= k | n, p0) <= alpha."""
    lo, hi = 0, n + 1
    while lo < hi:
        mid = (lo + hi) // 2
        if binom_tail(n, mid, p0) <= alpha:
            hi = mid
        else:
            lo = mid + 1
    return lo


def exact_power(p1: float, p0: float, n: int, alpha: float = 0.05) -> float:
    return binom_tail(n, k_crit(n, p0, alpha), p1)


def min_n(p1: float, p0: float, alpha: float = 0.05, power: float = 0.80):
    """Smallest n with exact one-sided power >= power. Bisection on n."""
    z_a, z_b = 1.6448536, 0.8416212
    if p1 <= p0:
        return None
    start = max(4, math.ceil(((z_a * math.sqrt(p0 * (1 - p0)) + z_b * math.sqrt(p1 * (1 - p1)))
                              / (p1 - p0)) ** 2))
    if exact_power(p1, p0, start) >= power:
        n = start
        while n > 4 and exact_power(p1, p0, n - 1) >= power:
            n -= 1
        return n

    def ok(nn):
        return exact_power(p1, p0, nn) >= power

    hi = start
    while hi < 500000 and not ok(hi):
        hi *= 2
    if hi >= 500000:
        return None
    lo = hi // 2
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


# ------------------------------------------------------------------ tests
def sign_test(pos: int, neg: int) -> float:
    """Exact two-sided sign test (binom with p=0.5)."""
    n = pos + neg
    if n == 0:
        return 1.0
    k = min(pos, neg)
    pmf = [math.comb(n, i) / 2 ** n for i in range(n + 1)]
    return min(1.0, 2 * sum(pmf[: k + 1]))


def wilson_interval(k: int, n: int, z: float = 1.959963985):
    """Wilson score interval for a proportion; honest at small n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = (z / den) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    # Clamp so a degenerate sample (all successes) still brackets its point estimate.
    lo = max(0.0, min(p, centre - half))
    hi = min(1.0, max(p, centre + half))
    return (lo, hi)
